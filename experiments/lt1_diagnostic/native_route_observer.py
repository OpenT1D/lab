"""Fixed C18 owner-loss observation using genuine live Popen ownership only."""

import copy
import json
import os
import select
import shutil
import stat
import subprocess
import sys
import tempfile
import time
from pathlib import Path

from experiments.gui.ownership import Ownership, ProcessTable
from experiments.lt1_diagnostic import native_route as route
from experiments.platform_process import spawn

_STARTED = {}
_FIELDS = (
    "schema kind action observer_pid observer_start coordinator_pid "
    "coordinator_start entry_sha256 observation_sha256 starter_sha256 "
    "setup_sha256 entry_sources nonce_sha256 cleanup_seconds"
)


def _code_context(source):
    # A start permit precedes child-PID review and publication of entry grants.
    # Its complete original audit is retained; only three authority data hashes
    # may differ from the fully pinned current context used for every new action.
    source = copy.deepcopy(source)
    for name in route.prior.AUTHORITY_SOURCES:
        route.need(
            route.prior.base.preflight.host_context.sha(source["implementation"][name]),
            "typed authority snapshot",
        )
        del source["implementation"][name]
    return source


def _drain(stream, limit):
    raw, eof = bytearray(), False
    until = time.monotonic() + 3
    while len(raw) <= limit and time.monotonic() < until:
        if not select.select([stream], [], [], max(0, until - time.monotonic()))[0]:
            break
        part = os.read(stream.fileno(), min(8192, limit + 1 - len(raw)))
        if not part:
            eof = True
            break
        raw.extend(part)
    route.need(len(raw) <= limit, "bounded observer retained stream")
    return bytes(raw), eof


def _prefix(entry, live, process):
    # The entry witness is produced by the shared owner after real Popen. No
    # saved PID is adopted; it must match the already observed owned live tree.
    with route.ExitStack() as stack:
        roots = {k: Path(v) for k, v in route.prior.base._roots(entry["roots"]).items()}
        evidence = route.storage._private_directory(roots["evidence"])
        stack.callback(os.close, evidence)
        witness = json.loads(
            route.storage._read_at(evidence, "live-entry.json", 65536),
            object_pairs_hook=route.storage.unique_object,
        )
        route.storage.fields(witness, "schema entry_sha256 nonce_sha256 identity")
        identity = witness["identity"]
        route.need(
            witness["schema"] == "opent1d.lt1-live-route-entry/2"
            and witness["entry_sha256"] == route.storage.digest(route.encoded(entry))
            and witness["nonce_sha256"] == entry["nonce_sha256"]
            and type(identity["pid"]) is int
            and identity["pid"] in live
            and identity["ppid"] == process.pid
            and identity["pgid"] == identity["pid"]
            and all(
                live[identity["pid"]][key] == identity[key]
                for key in ("pid", "ppid", "pgid", "start")
            ),
            "actual owned entry witness",
        )
        output = route.storage._private_directory(roots["output"])
        stack.callback(os.close, output)
        session = os.open(
            "session-0000", os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=output
        )
        stack.callback(os.close, session)
        info = os.fstat(session)
        route.need(
            stat.S_ISDIR(info.st_mode)
            and info.st_uid == os.getuid()
            and stat.S_IMODE(info.st_mode) == 0o700,
            "private owned session",
        )

        def token(info):
            return (
                info.st_dev,
                info.st_ino,
                info.st_size,
                info.st_mtime_ns,
                info.st_ctime_ns,
                info.st_mode,
                info.st_nlink,
            )

        member = os.stat("events.jsonl", dir_fd=session, follow_symlinks=False)
        raw = route.storage._read_at(session, "events.jsonl", 65536)
        route.need(
            token(member) == token(os.stat("events.jsonl", dir_fd=session, follow_symlinks=False)),
            "observer prefix member replaced",
        )
        route.need(
            route.legacy._signature(os.stat("session-0000", dir_fd=output, follow_symlinks=False))
            == route.legacy._signature(os.fstat(session)),
            "observer session rebound",
        )
        for key, fd in (("output", output), ("evidence", evidence)):
            route.need(
                route.legacy._signature(roots[key].lstat())
                == route.legacy._signature(os.fstat(fd)),
                "observer root rebound",
            )
        return raw, identity


def _read_line(process, timeout):
    until = time.monotonic() + timeout
    raw = bytearray()
    while b"\n" not in raw:
        route.need(
            time.monotonic() < until
            and select.select([process.stdout], [], [], max(0, until - time.monotonic()))[0],
            "coordinator response deadline",
        )
        part = os.read(process.stdout.fileno(), min(8192, route.CARRIER_LIMIT + 2 - len(raw)))
        route.need(
            part and len(raw) + len(part) <= route.CARRIER_LIMIT + 1, "bounded coordinator response"
        )
        raw.extend(part)
    route.need(raw.endswith(b"\n") and raw.count(b"\n") == 1, "single coordinator response")
    return json.loads(raw, object_pairs_hook=route.storage.unique_object)


def _start(start_raw, expected_identity, *, invented=False):
    registry = route.legacy._admissions()
    if not invented:
        route.need(registry["setup"] and registry["execution"], "no reviewed coordinator authority")
        route.need(
            type(start_raw) is bytes and route.storage.digest(start_raw) in registry["execution"],
            "no reviewed limited coordinator start permit",
        )
    start = route.decode(start_raw)
    if not invented:
        route.need(
            start["setup_sha256"] in registry["setup"], "no reviewed coordinator setup receipt"
        )
    route.storage.fields(
        start,
        "schema kind action observer_pid observer_start setup_sha256 entry_sources nonce_sha256",
    )
    source = route.source_identity()
    route.need(
        source == expected_identity and start["entry_sources"] == route.prior.grant_sources(source),
        "fixed coordinator source",
    )
    route.need(
        start["schema"] == "opent1d.lt1-coordinator-start/2"
        and start["kind"] == ("invented" if invented else "native-unadmitted")
        and start["action"] == "wait-for-reviewed-C18-grants",
        "limited start purpose",
    )
    own = ProcessTable().one(os.getpid())
    route.need(
        own and start["observer_pid"] == os.getpid() and start["observer_start"] == own["start"],
        "actual observer identity",
    )
    script = route.ROOT / (
        "tests/lt1_native_route_coordinator.py"
        if invented
        else "experiments/lt1_diagnostic/native_route_coordinator.py"
    )
    argv = [sys.executable, "-I", "-S", "-B", str(script)]
    text = route.encoded(
        {
            "schema": "opent1d.lt1-coordinator-start-carrier/2",
            "grant": start_raw.decode(),
            "audit": source,
        }
    ).decode()
    route.need(len(text.encode()) <= route.CARRIER_LIMIT, "limited coordinator carrier bound")
    total = (
        sum(len(os.fsencode(v)) + 1 for v in argv)
        + sum(
            len(os.fsencode(k + "=" + v)) + 1
            for k, v in {**route.transport.owner.ENVIRONMENT, route.CARRIER: text}.items()
        )
        + 4096
    )
    route.need(total < os.sysconf("SC_ARG_MAX"), "coordinator exec budget")
    process = spawn(
        argv,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env={**route.transport.owner.ENVIRONMENT, route.CARRIER: text},
    )
    try:
        ownership = Ownership(process)
        ready = _read_line(process, 10)
        actual = ProcessTable().one(process.pid)
        route.need(
            ready["schema"] == "opent1d.lt1-coordinator-ready/2"
            and actual
            and ready["identity"] == actual,
            "genuine coordinator start identity",
        )
        _STARTED[process] = {
            "ownership": ownership,
            "source": source,
            "starter": start_raw,
            "identity": actual,
            "argv": argv,
            "invented": invented,
        }
        return process, ready
    except BaseException:
        process.kill()
        process.wait(timeout=3)
        for stream in (process.stdin, process.stdout, process.stderr):
            stream.close()
        raise


def start(start_raw, *, expected_identity):
    """Admitted non-native wait stage only. Review child PID before entry grants."""
    return _start(start_raw, expected_identity)


def submit(process, entry_raw, observation_raw, *, expected_identity):
    registry = route.legacy._admissions()
    entry, _, _ = route.admit(entry_raw, observation_raw, registry)
    route.need(
        type(process) is subprocess.Popen and process in _STARTED, "no adopted/saved coordinator"
    )
    record = _STARTED[process]
    route.need(
        not record["invented"]
        and expected_identity == route.source_identity()
        and _code_context(record["source"]) == _code_context(expected_identity)
        and entry["owner_pid"] == process.pid
        and entry["owner_start"] == record["identity"]["start"],
        "exact live coordinator entry",
    )
    text = route.carrier(entry_raw, observation_raw, expected_identity, record["argv"])
    process.stdin.write(text.encode() + b"\n")
    process.stdin.flush()


def _observe(
    process, observer_raw, entry_raw, observation_raw, expected_identity, *, invented=False
):
    registry = route.legacy._admissions()
    if not invented:
        route.need(registry["setup"] and registry["execution"], "no reviewed observer authority")
        route.need(
            type(observer_raw) is bytes
            and route.storage.digest(observer_raw) in registry["execution"],
            "no reviewed C18 observer grant",
        )
        entry, _, _ = route.admit(entry_raw, observation_raw, registry)
    else:
        entry = route.decode(entry_raw)
    grant = route.decode(observer_raw)
    route.storage.fields(grant, _FIELDS)
    route.need(
        grant["schema"] == "opent1d.lt1-C18-observer/2"
        and grant["kind"] == ("invented" if invented else "native-unadmitted")
        and grant["action"] == "stop-exact-coordinator-and-owned-tree"
        and grant["cleanup_seconds"] == 30,
        "fixed C18 observer scope",
    )
    route.need(
        type(process) is subprocess.Popen and process in _STARTED,
        "genuine registered Popen required",
    )
    record = _STARTED[process]
    source = route.source_identity()
    route.need(
        record["invented"] is invented
        and source == expected_identity
        and _code_context(source) == _code_context(record["source"])
        and grant["entry_sources"] == route.prior.grant_sources(source),
        "current observer/coordinator source",
    )
    route.need(
        grant["starter_sha256"] == route.storage.digest(record["starter"])
        and grant["entry_sha256"] == route.storage.digest(entry_raw)
        and grant["observation_sha256"] == route.storage.digest(observation_raw)
        and grant["setup_sha256"] == entry["setup_sha256"]
        and grant["nonce_sha256"] == entry["nonce_sha256"]
        and entry["case_id"] == "C18"
        and entry["slot"] == "blocked",
        "linked exact observer action",
    )
    if not invented:
        route.need(
            grant["starter_sha256"] in registry["execution"]
            and grant["setup_sha256"] in registry["setup"],
            "observer linked setup/start memberships",
        )
    own = ProcessTable().one(os.getpid())
    coordinator = ProcessTable().one(process.pid)
    route.need(
        own
        and own["pid"] == grant["observer_pid"]
        and own["start"] == grant["observer_start"]
        and coordinator
        and coordinator["pid"] == grant["coordinator_pid"] == entry["owner_pid"]
        and coordinator["start"]
        == grant["coordinator_start"]
        == entry["owner_start"]
        == record["identity"]["start"]
        and coordinator["ppid"] == os.getpid(),
        "actual reviewed observer/coordinator identities",
    )
    route.need(list(process.args) == record["argv"], "fixed coordinator command")
    ownership = record["ownership"]
    until = time.monotonic() + 30
    prefix, entry_identity = None, None
    while True:
        live = ownership.observe()
        if len(live) >= 4:
            try:
                prefix, entry_identity = _prefix(entry, live, process)
            except FileNotFoundError:
                pass
            if prefix and prefix.count(b"\n") >= 4:
                break
        route.need(
            time.monotonic() < until and process.poll() is None, "C18 live owned-prefix deadline"
        )
        time.sleep(0.02)
    before = ownership.receipt()
    scope = [p for p in before if p["pid"] != process.pid]
    # Real Popen and its reviewed start identity are checked immediately before stop.
    actual = ProcessTable().one(process.pid)
    route.need(
        actual and actual["start"] == coordinator["start"] and actual["ppid"] == os.getpid(),
        "late coordinator identity changed",
    )
    route.need(route.source_identity() == source, "observer source changed before stop")
    if not invented:
        route.need(route.legacy._admissions() == registry, "observer authority changed before stop")
    process.kill()
    process.wait(timeout=3)
    forced, remaining = ownership.cleanup(30)
    stdout, stdout_eof = _drain(process.stdout, 4 * 1024 * 1024)
    stderr, stderr_eof = _drain(process.stderr, 1024 * 1024)
    route.need(
        len(stdout) <= 4 * 1024 * 1024 and len(stderr) <= 1024 * 1024, "observer output bound"
    )
    route.need(route.source_identity() == source, "observer source changed")
    for stream in (process.stdin, process.stdout, process.stderr):
        stream.close()
    del _STARTED[process]
    return {
        "schema": "opent1d.lt1-C18-observer-receipt/2",
        "kind": grant["kind"],
        "observer_grant_sha256": route.storage.digest(observer_raw),
        "coordinator_identity": coordinator,
        "before_stop_owned": before,
        "actual_entry_identity": entry_identity,
        "retained_prefix_sha256": route.storage.digest(prefix),
        "retained_prefix_events": prefix.count(b"\n"),
        "prefix_is_not_strict_scientific_readback": True,
        "stdout_eof": stdout_eof,
        "stderr_eof": stderr_eof,
        "historical_start_source_identity": record["source"],
        "observed_entry_tree": scope,
        "coordinator_exit_code": process.returncode,
        "actual_route_outer_receipt": None,
        "actual_route_outer_missing": True,
        "completion": "incomplete",
        "forced_cleanup": forced,
        "remaining_owned_processes": remaining,
        "source_identity": source,
        "stdout_sha256": route.storage.digest(stdout),
        "stderr_sha256": route.storage.digest(stderr),
        **route.AUTHORITY,
    }


def observe(process, observer_raw, entry_raw, observation_raw, *, expected_identity):
    return _observe(process, observer_raw, entry_raw, observation_raw, expected_identity)


def invented_coordinator_loss():
    """Self-created fixed fresh fixture only: no caller PID, command or private path."""
    source = route.source_identity()
    own = ProcessTable().one(os.getpid())
    nonce = "b" * 64
    start = route.encoded(
        {
            "schema": "opent1d.lt1-coordinator-start/2",
            "kind": "invented",
            "action": "wait-for-reviewed-C18-grants",
            "observer_pid": os.getpid(),
            "observer_start": own["start"],
            "setup_sha256": "a" * 64,
            "entry_sources": route.prior.grant_sources(source),
            "nonce_sha256": nonce,
        }
    )
    with tempfile.TemporaryDirectory() as name:
        root = Path(name).resolve()
        root.chmod(0o700)
        process, ready = _start(start, source, invented=True)
        try:
            node = str(Path(shutil.which("node")).resolve())
            process.stdin.write(
                route.encoded(
                    {
                        "invented_root": str(root),
                        "observed_tooling": {
                            "path": node,
                            "sha256": route.storage.digest(Path(node).read_bytes()),
                        },
                    }
                )
                + b"\n"
            )
            process.stdin.flush()
            control = _read_line(process, 20)["control"]
            entry_raw = control["entry"].encode()
            observation_raw = control["observation"].encode()
            entry = route.decode(entry_raw)
            grant = route.encoded(
                {
                    "schema": "opent1d.lt1-C18-observer/2",
                    "kind": "invented",
                    "action": "stop-exact-coordinator-and-owned-tree",
                    "observer_pid": os.getpid(),
                    "observer_start": own["start"],
                    "coordinator_pid": process.pid,
                    "coordinator_start": ready["identity"]["start"],
                    "entry_sha256": route.storage.digest(entry_raw),
                    "observation_sha256": route.storage.digest(observation_raw),
                    "starter_sha256": route.storage.digest(start),
                    "setup_sha256": entry["setup_sha256"],
                    "entry_sources": route.prior.grant_sources(source),
                    "nonce_sha256": entry["nonce_sha256"],
                    "cleanup_seconds": 30,
                }
            )
            return _observe(process, grant, entry_raw, observation_raw, source, invented=True)
        finally:
            if process in _STARTED:
                ownership = _STARTED[process]["ownership"]
                ownership.cleanup(0.2)
                if process.poll() is None:
                    process.kill()
                    process.wait(timeout=3)
                for stream in (process.stdin, process.stdout, process.stderr):
                    stream.close()
                del _STARTED[process]


def close(process):
    route.need(
        type(process) is subprocess.Popen and process in _STARTED, "genuine owned coordinator only"
    )
    record = _STARTED[process]
    forced, remaining = record["ownership"].cleanup(0.2)
    if process.poll() is None:
        process.kill()
        process.wait(timeout=3)
    for stream in (process.stdin, process.stdout, process.stderr):
        stream.close()
    del _STARTED[process]
    return {"forced": forced, "remaining_owned_processes": remaining}
