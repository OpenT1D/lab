"""Fixed version-2 executable route. Closed admissions precede private resources.

The startup carrier is private control data, never an argument or a native
qualification. This API has no runtime, command, policy or delegate selector.
"""

import base64
import copy
import json
import math
import os
import platform
import stat
import threading
from contextlib import ExitStack
from pathlib import Path

from experiments.gui.ownership import ProcessTable
from experiments.lt1_diagnostic import native_entry as prior
from experiments.lt1_diagnostic import native_route_transport as transport
from experiments.lt1_diagnostic.control_identity import ROOT, identity

legacy, storage = prior.base.launcher, prior.base.launcher.storage
HERE = ROOT / "experiments/lt1_diagnostic"
CARRIER = "OPENT1D_LT1_ROUTE_CONTROL"
CARRIER_LIMIT = 65536
ENTRY = HERE / "native_route_cli.mjs"
FIXTURE = ROOT / "tests/lt1_native_route_fixture.mjs"
SOURCES = "experiments/lt1_diagnostic/native_route_sources.json"
FILES = (
    "plan.json",
    "native_route.py",
    "native_route_exec.py",
    "native_route_transport.py",
    "native_route_reader.py",
    "native_route_contract.mjs",
    "native_route_cli.mjs",
    "native_route_worker.mjs",
    "native_route_descendant.mjs",
    "native_route_observation.mjs",
    "native_route_handoff.mjs",
    "native_route_cases.py",
    "native_route_cases.json",
    "native_route_observer.py",
    "native_route_coordinator.py",
    "native_route_sentinel.py",
    "native_route_host.py",
    "native_route_host.mjs",
    "native_route_host_tooling.py",
    "native_route_host_tooling.mjs",
    "native_attempt_namespace.json",
)
TEST_SOURCES = (
    "tests/lt1_native_route_fixture.mjs",
    "tests/lt1_native_route_fixture.py",
    "tests/lt1_native_route_exec.py",
    "tests/lt1_diagnostic_fixture.mjs",
    "tests/lt1_native_route_coordinator.py",
    "tests/lt1_native_route_models.mjs",
)
PACKET = prior.PACKET
FIELDS = (
    "schema kind observation_sha256 engine_sha256 integration_sha256 "
    "setup_sha256 entry_sources roots "
    "profile_sha256 owner_pid owner_start attempt nonce_sha256 process_argv case_id slot"
)
AUTHORITY = {k: v for k, v in prior.AUTHORITY.items() if k != "candidate_started"}


def need(ok, reason):
    if not ok:
        raise ValueError("LT1 native route refused: " + reason)


def encoded(value):
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"), allow_nan=False).encode()


def decode(raw):
    need(type(raw) is bytes and 0 < len(raw) <= 1024 * 1024, "bounded raw control")
    value = json.loads(raw, object_pairs_hook=storage.unique_object)
    need(encoded(value) == raw, "canonical control bytes")
    return value


def source_identity():
    value = identity(__file__)
    value["implementation"].update(prior.source_identity()["implementation"])
    for name in FILES:
        value["implementation"]["experiments/lt1_diagnostic/" + name] = storage.digest(
            legacy._source(HERE / name)
        )
    for name in TEST_SOURCES:
        value["implementation"][name] = storage.digest(legacy._source(ROOT / name))
    raw = legacy._source(ROOT / SOURCES)
    value["implementation"][SOURCES] = storage.digest(raw)
    keys = json.loads(raw, object_pairs_hook=storage.unique_object)
    storage.fields(keys, "schema sources")
    need(
        keys["schema"] == "opent1d.lt1-native-route-sources/2"
        and keys["sources"] == sorted(value["implementation"]),
        "complete version2 roster",
    )
    return value


def profile(roots, source, *, case_id=None, slot=None):
    parsed = prior.base._roots(roots)
    result = (
        legacy.profile(*(parsed[k] for k in ("staging", "packet", "output")))
        + "(allow file-read* "
        + " ".join(
            "(literal " + json.dumps(str(ROOT / n)) + ")" for n in sorted(source["implementation"])
        )
        + ")\n"
    )
    if case_id == "C19":
        from experiments.lt1_diagnostic.native_route_host import profile_delta

        result += profile_delta(roots, slot)
    return result


def admit(entry_raw, observation_raw, registry, invented=False):
    registry = prior._registry(copy.deepcopy(registry))
    need(registry["setup"] and registry["execution"], "no reviewed route authority")
    for raw in (entry_raw, observation_raw):
        need(
            type(raw) is bytes and storage.digest(raw) in registry["execution"],
            "exact entry/observation membership",
        )
    entry, observation = decode(entry_raw), decode(observation_raw)
    storage.fields(entry, FIELDS)
    need(
        entry["schema"] == "opent1d.lt1-native-route-grant/2"
        and entry["kind"] == ("invented" if invented else "native-unadmitted"),
        "version2 purpose",
    )
    need(
        entry["observation_sha256"] == storage.digest(observation_raw)
        and entry["engine_sha256"] in registry["execution"]
        and entry["integration_sha256"] in registry["execution"]
        and entry["setup_sha256"] in registry["setup"],
        "exact declared memberships",
    )
    need(
        entry["case_id"] in ("attempt", "C15", "C16", "C17", "C18", "C19")
        and isinstance(entry["slot"], str)
        and len(entry["slot"]) <= 64,
        "fixed case",
    )
    return entry, observation, registry


def carrier(entry_raw, observation_raw, audit, argv):
    value = {
        "schema": "opent1d.lt1-route-carrier/2",
        "entry": entry_raw.decode("utf8"),
        "observation": observation_raw.decode("utf8"),
        "audit": audit,
        "bootstrap": None,
    }
    raw = encoded(value)
    maximum_bootstrap = {
        "supplied_environment_keys": sorted([*transport.owner.ENVIRONMENT, CARRIER]),
        "observed_environment_keys": sorted(
            [*transport.owner.ENVIRONMENT, CARRIER, "__CF_USER_TEXT_ENCODING"]
        ),
        "runtime_added_environment_keys": ["__CF_USER_TEXT_ENCODING"],
    }
    largest = encoded({**value, "bootstrap": maximum_bootstrap})
    need(
        len(largest) <= CARRIER_LIMIT and b"\0" not in raw,
        "64KiB complete bootstrap carrier ceiling",
    )
    env = {**transport.owner.ENVIRONMENT, CARRIER: largest.decode()}
    need(
        all(
            len(os.fsencode(v)) + 1 <= 128 * 1024
            for v in [*argv, *(k + "=" + v for k, v in env.items())]
        ),
        "bounded individual exec strings",
    )
    total = (
        sum(len(os.fsencode(v)) + 1 for v in argv)
        + sum(len(os.fsencode(k + "=" + v)) + 1 for k, v in env.items())
        + 8 * (len(argv) + len(env) + 2)
    )
    maximum = os.sysconf("SC_ARG_MAX")
    need(
        type(maximum) is int and maximum > 0 and total + 4096 <= maximum,
        "actual exec argument/environment budget",
    )
    return raw.decode()


def _packet(fd):
    need(set(os.listdir(fd)) == set(PACKET), "closed packet inventory")
    result = {}
    for name in PACKET:
        info = os.stat(name, dir_fd=fd, follow_symlinks=False)
        need(
            stat.S_ISREG(info.st_mode)
            and info.st_uid == os.getuid()
            and info.st_nlink == 1
            and stat.S_IMODE(info.st_mode) in (0o400, 0o600),
            "private packet member",
        )
        result[name] = storage._read_at(fd, name, 4 * 1024 * 1024)
    return result


def packet_binding(entry, observation, packet):
    need(set(packet) == set(PACKET), "packet members")
    hashes = {n: storage.digest(raw) for n, raw in packet.items()}
    need(
        observation["packet_sha256"] == hashes
        and entry["engine_sha256"] == hashes["grant.json"]
        and entry["integration_sha256"] == hashes["integration-grant.json"]
        and entry["setup_sha256"] == hashes["setup_receipt.json"],
        "actual packet bytes",
    )
    return hashes


def _launch(
    entry_raw,
    observation_raw,
    expected_identity,
    cancel,
    *,
    invented=False,
    _captured=None,
    _pair=None,
    _preflight_only=False,
):
    # Production membership comes only from the compiled-in canonical authority.
    if invented:
        entry0 = decode(entry_raw)
        registry = {
            "schema": "opent1d.lt1-native-admissions/1",
            "setup": [entry0["setup_sha256"]],
            "execution": [
                storage.digest(entry_raw),
                storage.digest(observation_raw),
                entry0["engine_sha256"],
                entry0["integration_sha256"],
            ],
        }
    else:
        registry = legacy._admissions()
    entry, observation, registry = admit(entry_raw, observation_raw, registry, invented)
    expected_original = expected_identity
    expected_identity = copy.deepcopy(expected_identity)
    source = source_identity()
    need(
        source == expected_identity and entry["entry_sources"] == prior.grant_sources(source),
        "reviewed version2 source context",
    )
    roots = prior.base._roots(entry["roots"])
    policy = profile(entry["roots"], source, case_id=entry["case_id"], slot=entry["slot"])
    if entry["case_id"] == "C19":
        from experiments.lt1_diagnostic.native_route_host import _PairContext

        need(type(_pair) is _PairContext and _pair.contains(entry_raw), "owned C19 pair only")
    else:
        need(_pair is None and not _preflight_only, "ordinary route context")
    need(entry["profile_sha256"] == storage.digest(policy.encode()), "version2 profile")
    owner = ProcessTable().one(os.getpid())
    need(
        owner and entry["owner_pid"] == os.getpid() and entry["owner_start"] == owner["start"],
        "same live owner",
    )
    runtime = (
        observation["entry_executable"] if invented else str(roots["staging"] / "runtime/bin/node")
    )
    if invented:
        executable = Path(runtime)
        need(
            executable.is_absolute()
            and executable.name == "node"
            and executable.resolve() == executable
            and storage.digest(executable.read_bytes())
            == observation["runtime"]["executable_sha256"],
            "parent-observed ordinary tooling Node",
        )
    else:
        need(
            os.sys.platform == "darwin"
            and platform.machine() == "arm64"
            and os.sys.flags.isolated
            and os.sys.flags.no_site,
            "isolated selected native owner",
        )
    argv = [
        runtime,
        str(FIXTURE if invented else ENTRY),
        *(str(roots[k]) for k in ("staging", "packet", "output")),
    ]
    need(
        entry["process_argv"] == argv
        and observation["process_argv"] == argv
        and observation["owner_pid"] == os.getpid()
        and observation["owner_start"] == owner["start"],
        "fixed grant-free Node argv",
    )
    shim = ROOT / "tests/lt1_native_route_exec.py" if invented else HERE / "native_route_exec.py"
    parent_argv = [
        os.sys.executable,
        "-I",
        "-S",
        "-B",
        str(shim),
        "2147483647",
        "2147483646",
        *argv,
    ]
    control = carrier(entry_raw, observation_raw, source, parent_argv)
    carrier(entry_raw, observation_raw, source, argv)
    if not invented:
        carrier(entry_raw, observation_raw, source, [str(legacy.SANDBOX), "-p", policy, *argv])
    roots = dict(zip(prior.base.ROOTS, legacy._roots(tuple(roots.values()))))
    with ExitStack() as stack:
        bound = {}
        for key, path in roots.items():
            fd = storage._private_directory(path)
            stack.callback(os.close, fd)
            mode = 0o500 if key in ("staging", "packet") else 0o700
            need(stat.S_IMODE(os.fstat(fd).st_mode) == mode, "root mode")
            bound[key] = (fd, legacy._signature(os.fstat(fd)))
        if _pair is None:
            need(
                not os.listdir(bound["output"][0]) and not os.listdir(bound["evidence"][0]),
                "empty fresh outputs",
            )
        else:
            _pair.check(entry, roots)
        packet = _packet(bound["packet"][0])
        hashes = packet_binding(entry, observation, packet)
        from experiments.lt1_diagnostic.native_route_cases import validate_plan

        validate_plan(
            entry["case_id"],
            entry["slot"],
            legacy.decoded(packet["plan.json"]),
            legacy.decoded(packet["grant.json"])["mode"],
        )
        if _captured is not None:
            _captured["packet"] = dict(packet)
        host = decode(packet["integration_host_receipt.json"])
        storage.fields(
            host,
            "schema kind purpose entry_sources roots profile_sha256 owner_context "
            "timeout_seconds grace_seconds max_context_age_seconds sandbox_sha256 "
            "dyld_sha256 materialization_request_sha256 "
            "materialization_manifest_sha256 runtime_environment",
        )
        need(
            host["schema"] == "opent1d.lt1-native-route-host/2"
            and host["kind"] == ("invented" if invented else "observed")
            and host["purpose"] == "qualification-only"
            and host["entry_sources"] == entry["entry_sources"]
            and host["profile_sha256"] == entry["profile_sha256"],
            "new host namespace",
        )
        need(
            host["roots"]
            == {k: {"path": str(roots[k]), "identity": list(v[1])} for k, v in bound.items()},
            "reviewed physical roots",
        )
        for key, maximum in [
            ("timeout_seconds", 300),
            ("grace_seconds", 30),
            ("max_context_age_seconds", 3600),
        ]:
            value = host[key]
            need(
                type(value) in (int, float)
                and math.isfinite(value)
                and 0 <= value <= maximum
                and (key == "grace_seconds" or value > 0),
                "bounded owner clocks",
            )

        def check(log=None):
            need(
                source_identity() == source and expected_original == expected_identity,
                "source/context changed",
            )
            live = ProcessTable().one(os.getpid())
            need(live and live["start"] == owner["start"], "owner replaced")
            if not invented:
                need(legacy._admissions() == registry, "authority changed")
                legacy._owner(host["owner_context"], host["max_context_age_seconds"])
                need(
                    host["sandbox_sha256"] == storage.digest(legacy._source(legacy.SANDBOX))
                    and host["dyld_sha256"] == storage.digest(legacy._source(legacy.DYLD)),
                    "host mechanism bytes",
                )
                need(roots["staging"].name == "payload", "materialized payload")
                material = storage.inspect_materialized(
                    roots["staging"].parent,
                    host["materialization_request_sha256"],
                    host["materialization_manifest_sha256"],
                )
                need(material["kind"] == "native", "actual materialization")
                with ExitStack() as reads:
                    files, namespaces = legacy._inventory(roots["staging"], reads)
                    legacy.validate_grants(
                        packet["grant.json"],
                        packet["integration-grant.json"],
                        registry,
                        packet,
                        roots["staging"],
                        roots["output"],
                        files,
                    )
                    need(
                        {n: v["sha256"] for n, v in material["files"].items()} == files,
                        "materialization inventory",
                    )
                    namespaces()
            for key, (fd, sig) in bound.items():
                need(
                    roots[key].resolve() == roots[key]
                    and legacy._signature(roots[key].lstat()) == sig
                    and legacy._signature(os.fstat(fd)) == sig,
                    "root rebound",
                )
            need(_packet(bound["packet"][0]) == packet, "packet replaced before spawn")
            if _pair is None:
                need(not os.listdir(bound["output"][0]), "output adopted")
                need(
                    set(os.listdir(bound["evidence"][0]))
                    == (set() if log is None else {"launch.log"}),
                    "evidence adopted",
                )
            else:
                _pair.check(entry, roots, log=log is not None)

        check()
        from experiments.lt1_diagnostic.native_route_reader import _control, acknowledge

        if _preflight_only:
            _control(
                entry, observation, packet, source, {"root": str(ROOT), "python": os.sys.executable}
            )
            return {"packet": dict(packet), "host": host}

        from experiments.lt1_diagnostic.native_route_host import log_name

        verified = {}

        def verify(raw):
            ack, child = acknowledge(raw, entry_raw, observation_raw, packet, invented=invented)
            verified.update(child)
            return ack

        # This fixed qualification action is source-bound, not a caller callback.
        # Its reader starts only after all grant, packet and physical-root checks.
        case_stop, watch_done = threading.Event(), threading.Event()

        class CaseCancel:
            def is_set(self):
                return case_stop.is_set() or (cancel is not None and cancel.is_set())

        watcher = None
        if entry["case_id"] in ("C17", "C18") and entry["slot"] == "before-init-block":

            def watch_header():
                path = roots["output"] / "session-0000/events.jsonl"
                while not watch_done.wait(0.01):
                    try:
                        info = path.lstat()
                        if (
                            stat.S_ISREG(info.st_mode)
                            and info.st_uid == os.getuid()
                            and info.st_nlink == 1
                        ):
                            case_stop.set()
                            return
                    except FileNotFoundError:
                        continue

            watcher = threading.Thread(target=watch_header, daemon=True)
            watcher.start()
        try:
            receipt = transport._supervise(
                argv,
                roots["evidence"] / log_name(entry),
                expected_identity=transport.source_identity(),
                carrier=control,
                invented=invented,
                _live_name=("c19-" + entry["slot"] + "-live-entry.json")
                if _pair
                else "live-entry.json",
                live_binding={
                    "entry_sha256": storage.digest(entry_raw),
                    "nonce_sha256": entry["nonce_sha256"],
                },
                verify_frame=verify,
                timeout=host["timeout_seconds"],
                handoff_timeout=min(30, host["timeout_seconds"]),
                grace=host["grace_seconds"],
                cancel=CaseCancel() if watcher else cancel,
                before_spawn=check,
            )
        finally:
            watch_done.set()
            if watcher:
                watcher.join(timeout=1)
                need(not watcher.is_alive(), "case cancellation watcher stopped")
        post_error = None
        try:
            stable = source_identity() == source and _packet(bound["packet"][0]) == packet
        except (ValueError, OSError) as error:
            stable = False
            post_error = str(error)
    for name in ("frame_raw", "ack_raw", "ack_sent_raw"):
        receipt["exchange"][name + "_b64"] = base64.b64encode(
            receipt["exchange"].pop(name)
        ).decode()
    snapshot_error = None
    try:
        output_files = snapshot_output(roots["output"])
    except (ValueError, OSError) as error:
        output_files = {}
        snapshot_error = str(error)
    if _captured is not None:
        _captured["output_files"] = dict(output_files)
    return {
        "schema": "opent1d.lt1-native-route-receipt/2",
        "kind": entry["kind"],
        "entry_sha256": storage.digest(entry_raw),
        "observation_sha256": storage.digest(observation_raw),
        "packet_sha256": hashes,
        "source_identity": source,
        "producer_paths": {"root": str(ROOT), "python": os.sys.executable},
        "roots": entry["roots"],
        "entry_identity": verified,
        "transport": receipt,
        "source_and_packet_stable": stable,
        "postcheck_error": post_error,
        "output_snapshot_error": snapshot_error,
        "output_sha256": {n: storage.digest(raw) for n, raw in output_files.items()},
        "startup_environment_keys": sorted([*transport.owner.ENVIRONMENT, CARRIER]),
        "post_clear_environment_keys": sorted(observation["runtime_environment"]),
        "startup_confinement_qualified": False,
        "case_id": entry["case_id"],
        "slot": entry["slot"],
        **AUTHORITY,
    }


def launch(entry_raw, observation_raw, *, expected_identity, cancel=None):
    return _launch(entry_raw, observation_raw, expected_identity, cancel)


def _launch_invented(entry_raw, observation_raw, *, expected_identity, cancel=None):
    """Fixed fresh tooling fixture only; never a native admission substitute."""
    return _launch(entry_raw, observation_raw, expected_identity, cancel, invented=True)


def snapshot_output(path):
    """Trusted caller snapshot of the fixed output tree; no archived code loading."""
    path = Path(path)
    result = {}
    with ExitStack() as stack:
        root = storage._private_directory(path)
        stack.callback(os.close, root)

        def read(fd, name, label):
            info = os.stat(name, dir_fd=fd, follow_symlinks=False)
            need(
                stat.S_ISREG(info.st_mode)
                and info.st_nlink == 1
                and stat.S_IMODE(info.st_mode) == 0o600,
                "private output member",
            )
            result[label] = storage._read_at(fd, name, 16 * 1024 * 1024)

        for name in os.listdir(root):
            info = os.stat(name, dir_fd=root, follow_symlinks=False)
            if stat.S_ISDIR(info.st_mode):
                need(
                    name in ("session-0000", "session-0001")
                    and stat.S_IMODE(info.st_mode) == 0o700,
                    "fixed private session",
                )
                fd = storage._private_directory(path / name)
                stack.callback(os.close, fd)
                need(set(os.listdir(fd)) == {"events.jsonl"}, "closed session")
                read(fd, "events.jsonl", name + "/events.jsonl")
            else:
                need(
                    name
                    in (
                        "route.json",
                        "descendant-root.json",
                        "grandchild.json",
                        "descendant-stop",
                        "c19-allowed-read.txt",
                        "c19-allowed-write.txt",
                    ),
                    "fixed output leaf",
                )
                read(root, name, name)
        need(
            len(result) <= 16 and sum(map(len, result.values())) <= 32 * 1024 * 1024, "output bound"
        )
    return result
