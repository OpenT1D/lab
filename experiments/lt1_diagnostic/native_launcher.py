"""Fixed owned qualification launch, closed before intake without both grants.

The existing source-local setup/execution authority owns admission. No CLI,
caller command, registry, policy text or automatic setup is accepted. Quiet
trusted ownership is required; final byte checks are not atomic expected-byte exec.
"""

import json
import math
import os
import re
import stat
import subprocess
import threading
from contextlib import ExitStack
from datetime import UTC, datetime
from pathlib import Path

from experiments.lt1_diagnostic import frozen_setup as storage
from experiments.lt1_diagnostic import host_context, journal_reader, native_preflight, reader
from experiments.lt1_diagnostic.control_identity import ROOT, identity
from experiments.shared_services.execution import supervise

HERE = ROOT / "experiments/lt1_diagnostic"
SANDBOX = Path("/usr/bin/sandbox-exec")
DYLD = Path("/System/Library/Sandbox/Profiles/dyld-support.sb")
WORKER = (
    "native_worker.mjs",
    "native_loader.mjs",
    "direct.mjs",
    "wrapped.mjs",
    "protocol.mjs",
    "../adapter_audit/lt1_sampled.mjs",
    "../m0/lt1/record.mjs",
)
INTEGRATION = tuple(p for p in WORKER if p != "native_worker.mjs") + (
    "attempt_journal.mjs",
    "integration_gate.mjs",
    "integration_worker.mjs",
)
RECEIPTS = ("plan", "setup_receipt", "host_receipt", "rights_receipt", "security_receipt")
PACKET = {name + ".json" for name in RECEIPTS} | {
    "grant.json",
    "integration-grant.json",
    "integration_host_receipt.json",
}
ENTRIES = (
    "source/src/core/Simulator.ts",
    "source/src/core/models/Cambridge.ts",
    "source/src/core/sensors/IdealCGM.ts",
    "source/src/core/actuators/StaticInsulinPump.ts",
    "source/LICENSE.md",
    "runtime/bin/node",
    "runtime/LICENSE",
    "toolchain/node_modules/ts-node/esm.mjs",
    "toolchain/tsconfig.json",
    "toolchain/package.json",
    "toolchain/package-lock.json",
)
AUTHORITY = {
    "native_host_qualified": False,
    "native_acceptance": False,
    "setup_admitted": False,
    "new_authority_granted": False,
}


def need(ok, reason):
    if not ok:
        raise ValueError("LT1 pre-start refused: " + reason)


def decoded(raw):
    need(isinstance(raw, bytes) and 0 < len(raw) <= storage.REQUEST_LIMIT, "byte bound")
    return json.loads(raw, object_pairs_hook=storage.unique_object)


def _admissions():
    return decoded((HERE / "native-admissions.json").read_bytes())


def authority(engine_raw, integration_raw):
    """Only canonical application authority; no supplied path is touched here."""
    registry = _admissions()
    storage.fields(registry, "schema setup execution")
    need(registry["schema"] == "opent1d.lt1-native-admissions/1", "authority schema")
    need(
        all(
            isinstance(registry[k], list) and all(host_context.sha(v) for v in registry[k])
            for k in ("setup", "execution")
        ),
        "authority identities",
    )
    for raw in (engine_raw, integration_raw):
        need(
            isinstance(raw, bytes)
            and len(raw) <= storage.REQUEST_LIMIT
            and storage.digest(raw) in registry["execution"],
            "no reviewed execution grants",
        )
    return registry


def _signature(s):
    return s.st_dev, s.st_ino, s.st_uid, stat.S_IMODE(s.st_mode)


def _overlap(left, right):
    """Physical ancestry also covers case aliases on case-insensitive volumes."""

    def token(path):
        info = path.stat()
        return info.st_dev, info.st_ino

    return token(left) in {token(p) for p in (right, *right.parents)} or token(right) in {
        token(p) for p in (left, *left.parents)
    }


def _roots(values):
    roots = [Path(p) for p in values]
    need(
        all(
            p.is_absolute()
            and p.resolve() == p
            and not p.is_relative_to(ROOT)
            and not ROOT.is_relative_to(p)
            and not _overlap(p, ROOT)
            for p in roots
        ),
        "canonical private roots outside checkout",
    )
    need(
        all(
            not a.is_relative_to(b) and not b.is_relative_to(a) and not _overlap(a, b)
            for i, a in enumerate(roots)
            for b in roots[i + 1 :]
        ),
        "separate roots",
    )
    return roots


def _source(path):
    need(path.resolve(strict=True) == path, "canonical source")
    with ExitStack() as stack:
        fd = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC)
        stack.callback(os.close, fd)
        return storage._read_at(fd, path.name, storage.REQUEST_LIMIT)


def _worker(names):
    return {name: storage.digest(_source(Path(os.path.normpath(HERE / name)))) for name in names}


def profile(stage, packet, output):
    """Fixed provisional native profile; actual native boundaries remain unrun."""

    def q(value):
        return json.dumps(str(value))

    sources = {
        Path(os.path.normpath(HERE / p)) for p in (*WORKER, *INTEGRATION, "native-admissions.json")
    }
    # This source path closure is independent of plan bytes. Empty bytes never
    # become an execution plan; the actual plan and all reader bytes are checked.
    current_reader = journal_reader.identity(b"")
    for mapping in (
        current_reader["implementation"],
        current_reader["protocol"]["implementation_sha256"],
    ):
        sources.update(ROOT / name for name in mapping)
    sources = sorted(sources)
    return "\n".join(
        [
            "(version 1)",
            "(deny default)",
            f"(import {q(DYLD)})",
            "(allow process-fork)",
            f"(allow process-exec (literal {q(stage / 'runtime/bin/node')}))",
            "(allow sysctl-read)",
            "(allow mach-lookup)",
            "(allow file-read-metadata)",
            '(allow file-read* (subpath "/System/Library") (subpath "/usr/lib") '
            '(subpath "/Library/Apple") (literal "/dev/null") '
            '(literal "/dev/urandom") (literal "/dev/random"))',
            '(allow file-map-executable (subpath "/System/Library") (subpath "/usr/lib"))',
            f"(allow file-map-executable (literal {q(stage / 'runtime/bin/node')}))",
            f"(allow file-read* (subpath {q(stage)}) (subpath {q(packet)}) (subpath {q(output)}) "
            + " ".join(f"(literal {q(p)})" for p in sources)
            + ")",
            f"(allow file-write* (subpath {q(output)}))",
            "",
        ]
    )


def _inventory(stage, stack):
    directories, found, total = {}, {}, 0

    def visit(path, relative=""):
        nonlocal total
        need(len(directories) < storage.MAX_DIRECTORIES, "directory bound")
        fd = storage._private_directory(path)
        stack.callback(os.close, fd)
        directories[relative] = (path, fd, _signature(os.fstat(fd)), set(os.listdir(fd)))
        need(stat.S_IMODE(os.fstat(fd).st_mode) == 0o500, "frozen staging directory")
        for name in sorted(os.listdir(fd)):
            label = relative + "/" + name if relative else name
            need(len(label.split("/")) <= storage.MAX_DEPTH, "staging depth")
            current = os.stat(name, dir_fd=fd, follow_symlinks=False)
            if stat.S_ISDIR(current.st_mode):
                visit(path / name, label)
            else:
                need(
                    stat.S_ISREG(current.st_mode)
                    and current.st_uid == os.getuid()
                    and stat.S_IMODE(current.st_mode) in {0o400, 0o500},
                    "frozen staging file",
                )
                remaining = min(storage.FILE_LIMIT, storage.TOTAL_LIMIT - total)
                need(
                    len(found) < storage.MAX_FILES and current.st_size <= remaining, "staging bound"
                )
                raw = storage._read_at(fd, name, remaining)
                total += len(raw)
                need(
                    total <= storage.TOTAL_LIMIT and len(found) < storage.MAX_FILES, "staging bound"
                )
                found[label] = storage.digest(raw)

    visit(stage)
    storage._path_inventory(found)

    def check():
        for path, fd, signature, names in directories.values():
            need(
                path.resolve() == path
                and _signature(path.lstat()) == signature
                and _signature(os.fstat(fd)) == signature
                and set(os.listdir(fd)) == names,
                "staging namespace changed",
            )

    check()
    return found, check


def validate_grants(engine_raw, integration_raw, registry, blobs, stage, output, inventory):
    """Bound pre-start counterpart; the original worker verifiers still run."""
    engine, integration = decoded(engine_raw), decoded(integration_raw)
    storage.fields(
        engine,
        "schema source_revision node platform arch host staging_root mode "
        "plan_sha256 setup_receipt_sha256 host_receipt_sha256 rights_receipt_sha256 "
        "security_receipt_sha256 files worker_files",
    )
    need(
        engine["schema"] == "opent1d.lt1-native-grant/1"
        and engine["source_revision"] == native_preflight.REVISION
        and all(engine[k] == native_preflight.RUNTIME[k] for k in ("node", "platform", "arch"))
        and engine["host"] == host_context.socket.gethostname()
        and engine["staging_root"] == str(stage)
        and isinstance(engine["mode"], str)
        and engine["mode"] in {"direct", "wrapped"},
        "engine identity",
    )
    for name in RECEIPTS:
        need(
            host_context.sha(engine[name + "_sha256"])
            and engine[name + "_sha256"] == storage.digest(blobs[name + ".json"]),
            name + " bytes",
        )
    need(engine["setup_receipt_sha256"] in registry["setup"], "no reviewed actual setup receipt")
    need(
        engine["files"] == inventory
        and set(ENTRIES) <= inventory.keys()
        and inventory["runtime/bin/node"] == native_preflight.RUNTIME["executable_sha256"],
        "complete selected staging bytes",
    )
    need(engine["worker_files"] == _worker(WORKER), "engine worker bytes")
    reader.validate_plan(decoded(blobs["plan.json"]))
    storage.fields(
        integration,
        "schema engine_grant_sha256 host_receipt_sha256 output_root attempt "
        "owner_pid reader_identity implementation",
    )
    need(
        integration["schema"] == "opent1d.lt1-integration-grant/1"
        and integration["engine_grant_sha256"] == storage.digest(engine_raw)
        and integration["host_receipt_sha256"]
        == storage.digest(blobs["integration_host_receipt.json"])
        and integration["output_root"] == str(output)
        and type(integration["owner_pid"]) is int
        and integration["owner_pid"] == os.getpid()
        and isinstance(integration["attempt"], str)
        and re.fullmatch("[a-z0-9][a-z0-9-]{0,63}", integration["attempt"]),
        "integration owner/bindings",
    )
    current_reader = journal_reader.identity(blobs["plan.json"])
    need(
        integration["reader_identity"] == current_reader
        and integration["implementation"] == _worker(INTEGRATION),
        "current integration/reader bytes",
    )
    for mapping in (
        current_reader["implementation"],
        current_reader["protocol"]["implementation_sha256"],
    ):
        need(
            all(
                storage.digest(_source(ROOT / name)) == expected
                for name, expected in mapping.items()
            ),
            "canonical reader source bytes",
        )
    return integration


def _fresh(expected, maximum_age):
    now = datetime.now(UTC)
    need(
        expected["status"] == "observed"
        and not expected["unknown"]
        and host_context.stamp(expected["observed_to"]) <= now
        and (now - host_context.stamp(expected["observed_from"])).total_seconds() <= maximum_age,
        "reviewed owner context stale or unknown",
    )


def _owner(expected, maximum_age):
    host_context.validate(expected)
    _fresh(expected, maximum_age)
    actual = host_context.capture()
    need(
        actual["status"] == "observed"
        and not actual["unknown"]
        and all(
            actual[k] == expected[k]
            for k in ("host", "observer", "collector_identity", "sysctl_sha256", "queries")
        )
        and expected["observer"]["pid"] == os.getpid()
        and expected["host"]["uid"] == os.getuid()
        and expected["observer"]["posix_session"] == os.getsid(0),
        "live owner/boot/source changed",
    )
    _fresh(expected, maximum_age)


def _run(argv, log_path, timeout, grace, guard, cancel):
    def before(log):
        os.fchmod(log.fileno(), 0o600)
        guard(log)

    result = supervise(
        argv,
        log_path,
        timeout=timeout,
        grace=grace,
        cancel=cancel,
        environment=dict(host_context.ENVIRONMENT),
        stdin=subprocess.DEVNULL,
        before_spawn=before,
    )
    if result["status"] == "completed" and not (
        type(result["exit_code"]) is int
        and result["exit_code"] == 0
        and result["error"] is None
        and result["received_signals"] == []
        and result["remaining_owned_processes"] == []
        and not any(result.get(k) for k in ("cleanup_error", "signal_error"))
    ):
        result.update(status="failed", error="Inconsistent owned completion")
    return {**result, "kind": "qualification-only", **AUTHORITY}


def launch_native(engine_raw, integration_raw, staging, packet, output, evidence, *, cancel=None):
    """Only existing exact execution/setup admissions may reach native spawn."""
    registry = authority(engine_raw, integration_raw)
    proposed = decoded(engine_raw)
    need(
        isinstance(proposed, dict)
        and host_context.sha(proposed.get("setup_receipt_sha256"))
        and proposed["setup_receipt_sha256"] in registry["setup"],
        "no reviewed actual setup receipt",
    )
    need(threading.current_thread() is threading.main_thread(), "main-thread owner required")
    need(Path(__file__).resolve() == HERE / "native_launcher.py", "canonical launcher")
    need(
        host_context.sys.platform == "darwin"
        and host_context.platform.machine() == "arm64"
        and host_context.sys.flags.isolated
        and host_context.sys.flags.no_site,
        "isolated native owner",
    )
    roots = _roots((staging, packet, output, evidence))
    stage, packet, output, evidence = roots
    with ExitStack() as stack:
        bound = {}
        for role, path, mode in zip(
            ("stage", "packet", "output", "evidence"), roots, (0o500, 0o500, 0o700, 0o700)
        ):
            fd = storage._private_directory(path)
            stack.callback(os.close, fd)
            need(stat.S_IMODE(os.fstat(fd).st_mode) == mode, "root mode")
            bound[role] = (fd, _signature(os.fstat(fd)))
        need(set(os.listdir(bound["packet"][0])) == PACKET, "closed packet")
        need(
            not os.listdir(bound["output"][0]) and not os.listdir(bound["evidence"][0]),
            "fresh empty outputs",
        )
        blobs = {
            name: storage._read_at(bound["packet"][0], name, storage.REQUEST_LIMIT)
            for name in PACKET
        }
        need(
            blobs["grant.json"] == engine_raw
            and blobs["integration-grant.json"] == integration_raw,
            "packet grant bytes",
        )
        host = decoded(blobs["integration_host_receipt.json"])
        storage.fields(
            host,
            "schema purpose owner_context launcher_identity roots profile_sha256 "
            "sandbox_sha256 dyld_sha256 timeout_seconds grace_seconds max_context_age_seconds "
            "materialization_request_sha256 materialization_manifest_sha256",
        )
        need(
            host["schema"] == "opent1d.lt1-prestart-host/1"
            and host["purpose"] == "qualification-only"
            and host["launcher_identity"] == identity(__file__),
            "reviewed launcher identity/purpose",
        )
        need(
            host["roots"]
            == {
                role: {"path": str(path), "identity": list(bound[role][1])}
                for role, path in zip(bound, roots)
            },
            "reviewed root identities",
        )
        for key, maximum in (
            ("timeout_seconds", 3600),
            ("grace_seconds", 60),
            ("max_context_age_seconds", 3600),
        ):
            value = host[key]
            need(
                type(value) in (int, float)
                and math.isfinite(value)
                and 0 <= value <= maximum
                and (key == "grace_seconds" or value > 0),
                "bounded clock",
            )
        policy = profile(stage, packet, output)
        need(
            host["profile_sha256"] == storage.digest(policy.encode())
            and host["sandbox_sha256"] == storage.digest(_source(SANDBOX))
            and host["dyld_sha256"] == storage.digest(_source(DYLD)),
            "fixed host mechanism bytes",
        )

        def boundaries(log):
            for role, path in zip(bound, roots):
                fd, signature = bound[role]
                need(
                    path.resolve() == path
                    and _signature(path.lstat()) == signature
                    and _signature(os.fstat(fd)) == signature,
                    "root namespace changed",
                )
            need(not os.listdir(bound["output"][0]), "output adopted")
            for name in PACKET:
                current = os.stat(name, dir_fd=bound["packet"][0], follow_symlinks=False)
                need(
                    stat.S_ISREG(current.st_mode)
                    and current.st_uid == os.getuid()
                    and current.st_nlink == 1
                    and stat.S_IMODE(current.st_mode) in {0o400, 0o600},
                    "private packet file",
                )
            need(
                set(os.listdir(bound["evidence"][0])) == (set() if log is None else {"launch.log"}),
                "evidence adopted",
            )
            if log is not None:
                current = os.stat("launch.log", dir_fd=bound["evidence"][0], follow_symlinks=False)
                need(
                    _signature(os.fstat(log.fileno())) == _signature(current)
                    and current.st_nlink == 1
                    and stat.S_IMODE(current.st_mode) == 0o600,
                    "private bound log",
                )

        def check(log=None):
            _owner(host["owner_context"], host["max_context_age_seconds"])
            boundaries(log)
            need(authority(engine_raw, integration_raw) == registry, "authority changed")
            need(
                set(os.listdir(bound["packet"][0])) == PACKET
                and all(
                    storage._read_at(bound["packet"][0], n, storage.REQUEST_LIMIT) == raw
                    for n, raw in blobs.items()
                ),
                "packet changed",
            )
            need(host["launcher_identity"] == identity(__file__), "launcher source changed")
            need(stage.name == "payload", "materialized payload required")
            materialized = storage.inspect_materialized(
                stage.parent,
                host["materialization_request_sha256"],
                host["materialization_manifest_sha256"],
            )
            need(materialized["kind"] == "native", "actual materialization required")
            with ExitStack() as reads:
                files, namespaces = _inventory(stage, reads)
                validate_grants(engine_raw, integration_raw, registry, blobs, stage, output, files)
                need(
                    {n: v["sha256"] for n, v in materialized["files"].items()} == files,
                    "materialization/grant inventory",
                )
                need(
                    stat.S_IMODE((stage / "runtime/bin/node").stat().st_mode) == 0o500,
                    "selected executable mode",
                )
                namespaces()
            need(
                host["launcher_identity"] == identity(__file__)
                and host["profile_sha256"]
                == storage.digest(profile(stage, packet, output).encode())
                and host["sandbox_sha256"] == storage.digest(_source(SANDBOX))
                and host["dyld_sha256"] == storage.digest(_source(DYLD)),
                "late source or host mechanism changed",
            )
            need(authority(engine_raw, integration_raw) == registry, "late authority changed")
            boundaries(log)
            _fresh(host["owner_context"], host["max_context_age_seconds"])

        check()
        argv = [
            str(SANDBOX),
            "-p",
            policy,
            str(stage / "runtime/bin/node"),
            str(HERE / "integration_worker.mjs"),
            str(stage),
            str(packet),
            str(output),
        ]
        return _run(
            argv,
            evidence / "launch.log",
            host["timeout_seconds"],
            host["grace_seconds"],
            check,
            cancel,
        )
