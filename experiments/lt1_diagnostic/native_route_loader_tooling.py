"""Explicit ordinary-tooling loader controls, never native setup or qualification.

Imports and automatic checks never compile or invoke a Mac sandbox. The only
preparation/experiment API fixes all commands, tools, targets and policies.
"""

import base64
import copy
import hashlib
import json
import os
import platform
import re
import secrets
import shlex
import shutil
import stat
import subprocess
import sys
from pathlib import Path, PurePosixPath

from experiments.lt1_diagnostic import native_supervisor as owner
from experiments.lt1_diagnostic.control_identity import ROOT, identity
from experiments.lt1_diagnostic.native_preflight import RUNTIME

HERE = Path(__file__).resolve().parent
SCRIPT = HERE / "native_route_loader_tooling.mjs"
MODULE = HERE / "native_route_loader_module.mjs"
ADDON = HERE / "native_route_loader_addon.c"
CLANG = PurePosixPath("/Library/Developer/CommandLineTools/usr/bin/clang")
LINKER = CLANG.parent / "ld"
SDK = PurePosixPath("/Library/Developer/CommandLineTools/SDKs/MacOSX.sdk")
HEADERS = PurePosixPath("/usr/local/include/node")
RESOURCES = CLANG.parent.parent / "lib/clang"
SANDBOX = PurePosixPath("/usr/bin/sandbox-exec")
DYLD = PurePosixPath("/System/Library/Sandbox/Profiles/dyld-support.sb")
CONTROL = "OPENT1D_C20_TOOLING"
SLOTS = ("validity-control", "base", "allow-twin")
OPS = ("module_read", "module_import", "addon_read", "addon_load")
AUTHORITY = {
    "native_host_qualified": False,
    "native_execution_authorized": False,
    "setup_admitted": False,
    "effective_erasure_verified": False,
    "new_authority_granted": False,
}
AUTHORITY_FILES = {
    "experiments/lt1_diagnostic/" + name
    for name in (
        "native-admissions.json",
        "setup-request-admissions.json",
        "removal-admissions.json",
    )
}
SOURCE_FILES = tuple(p.relative_to(ROOT).as_posix() for p in (SCRIPT, MODULE, ADDON))
SYSTEM_READ = (
    "/System/Library",
    "/usr/lib",
    "/Library/Apple",
    "/System/Volumes/Preboot/Cryptexes/App/System",
    "/System/Volumes/Preboot/Cryptexes/Incoming/OS",
    "/System/Volumes/Preboot/Cryptexes/OS",
    "/System/Cryptexes/App",
    "/System/Cryptexes/OS",
)


def need(ok, why):
    if not ok:
        raise ValueError("LT1 C20 tooling refused: " + why)


def encoded(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def _unique(pairs):
    result = {}
    for key, value in pairs:
        need(key not in result, "duplicate JSON field")
        result[key] = value
    return result


def _fields(value, names):
    need(type(value) is dict and set(value) == set(names.split()), "closed fields")


def _sha(value):
    return type(value) is str and len(value) == 64 and all(c in "0123456789abcdef" for c in value)


def source_identity():
    value = identity(__file__)
    value["implementation"].update(
        {name: digest((ROOT / name).read_bytes()) for name in SOURCE_FILES}
    )
    return value


def _snapshot(path, *, private=False, maximum=512 * 1024 * 1024):
    path = Path(path)
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK | os.O_CLOEXEC)
    try:
        before = os.fstat(fd)

        def sig(info):
            return [
                info.st_dev,
                info.st_ino,
                info.st_uid,
                stat.S_IMODE(info.st_mode),
                info.st_nlink,
                info.st_size,
                info.st_mtime_ns,
                info.st_ctime_ns,
            ]

        need(
            stat.S_ISREG(before.st_mode) and 0 <= before.st_size <= maximum, "bounded regular file"
        )
        if private:
            need(
                before.st_uid == os.getuid()
                and before.st_nlink == 1
                and stat.S_IMODE(before.st_mode) == 0o400,
                "immutable private target",
            )
        h, count = hashlib.sha256(), 0
        while raw := os.read(fd, 65536):
            count += len(raw)
            need(count <= maximum, "file grew beyond bound")
            h.update(raw)
        need(
            sig(before) == sig(os.fstat(fd)) == sig(path.lstat()) and count == before.st_size,
            "file rebound or changed",
        )
        return {"identity": sig(before), "sha256": h.hexdigest()}
    finally:
        os.close(fd)


def _create(path, raw):
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW | os.O_CLOEXEC, 0o600)
    with os.fdopen(fd, "wb") as stream:
        stream.write(raw)
        stream.flush()
        os.fsync(stream.fileno())
    directory = os.open(Path(path).parent, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        os.fsync(directory)
    finally:
        os.close(directory)


def toolchain_identity():
    """Observe fixed installed tools/headers only; this starts no process."""
    node = shutil.which("node")
    need(node is not None, "ordinary Node unavailable")
    node = Path(node).resolve(strict=True)
    need(node.name == "node", "fixed ordinary Node leaf")
    sdk = Path(SDK).resolve(strict=True)
    paths = (CLANG, LINKER, SANDBOX, DYLD, sdk / "SDKSettings.json", node)
    files = {str(path): _snapshot(path) for path in paths}
    need(files[str(node)]["sha256"] != RUNTIME["executable_sha256"], "selected candidate excluded")
    headers = {
        str(HEADERS / name): _snapshot(HEADERS / name)
        for name in (
            "node_api.h",
            "node_api_types.h",
            "js_native_api.h",
            "js_native_api_types.h",
            "node_version.h",
        )
    }
    return {
        "schema": "opent1d.lt1-c20-installed-toolchain/1",
        "node": str(node),
        "sdk": str(sdk),
        "files": files,
        "headers": headers,
    }


def _profile(node, targets, slot, log, *, source_root=ROOT):
    need(slot in ("base", "allow-twin"), "fixed profiled slot")

    def q(value):
        return json.dumps(str(value))

    script = PurePosixPath(source_root) / SCRIPT.relative_to(ROOT).as_posix()
    base = "\n".join(
        [
            "(version 1)",
            "(deny default)",
            f"(import {q(DYLD)})",
            "(allow process-fork)",
            f"(allow process-exec (literal {q(node)}))",
            "(allow sysctl-read)",
            "(allow mach-lookup)",
            "(allow file-read-metadata)",
            '(allow file-read* (subpath "/System/Library") (subpath "/usr/lib") '
            '(subpath "/Library/Apple") (literal "/dev/null") '
            '(literal "/dev/random") (literal "/dev/urandom"))',
            '(allow file-map-executable (subpath "/System/Library") (subpath "/usr/lib"))',
            f"(allow file-map-executable (literal {q(node)}))",
            f"(allow file-read-data (literal {q(node)}) (literal {q(script)}) "
            f"(literal {q(PurePosixPath(targets) / 'addon.node')}))",
            f"(allow file-write* (literal {q(log)}))",
            "",
        ]
    )
    if slot == "allow-twin":
        base += f"(allow file-read-data (literal {q(PurePosixPath(targets) / 'module.mjs')}))\n"
        base += (
            f"(allow file-map-executable (literal {q(PurePosixPath(targets) / 'addon.node')}))\n"
        )
    return base


def _compile_argv(sdk, targets, build, *, scan, source_root=ROOT):
    addon = PurePosixPath(source_root) / ADDON.relative_to(ROOT).as_posix()
    common = [
        str(CLANG),
        "-std=c11",
        "-DNAPI_VERSION=8",
        "-arch",
        "arm64",
        "-isysroot",
        str(sdk),
        "-I",
        str(HEADERS),
    ]
    if scan:
        return [
            *common,
            "-M",
            "-MT",
            "c20-addon",
            "-MF",
            str(build / "dependencies.mk"),
            str(addon),
        ]
    return [
        *common,
        "-bundle",
        "-undefined",
        "dynamic_lookup",
        "-nostdlib",
        "-fno-stack-protector",
        "-fuse-ld=" + str(LINKER),
        "-MD",
        "-MF",
        str(build / "compiled-dependencies.mk"),
        "-o",
        str(targets / "addon.node"),
        str(addon),
    ]


def _dependencies(raw, sdk):
    need(type(raw) is bytes and 0 < len(raw) <= 65536, "bounded dependency bytes")
    text = raw.decode("utf-8").replace("\\\n", " ")
    need(":" in text and "\0" not in text, "dependency grammar")
    target, names = text.split(":", 1)
    need(target.strip() != "" and len(target) <= 4096, "dependency target")
    paths = [Path(name).resolve(strict=True) for name in shlex.split(names)]
    need(0 < len(paths) <= 256 and len(paths) == len(set(paths)), "dependency denominator")
    roots = (Path(sdk), Path(HEADERS).resolve(), Path(RESOURCES).resolve())
    need(
        all(p == ADDON or any(p.is_relative_to(r) for r in roots) for p in paths),
        "fixed header/source closure only",
    )
    need(ADDON in paths and HEADERS / "node_api.h" in paths, "actual source and N-API closure")
    return {str(path): _snapshot(path, maximum=16 * 1024 * 1024) for path in sorted(paths)}


def _ownership_complete(owned):
    if not (type(owned) is list and 0 < len(owned) <= 256):
        return False
    for process in owned:
        if not (
            type(process) is dict
            and set(process) == {"pid", "ppid", "pgid", "start", "alive"}
            and all(type(process[k]) is int and process[k] > 0 for k in ("pid", "ppid", "pgid"))
            and process["pid"] > 1
            and process["pid"] != process["ppid"]
            and type(process["start"]) is str
            and 0 < len(process["start"]) <= 512
            and type(process["alive"]) is bool
        ):
            return False
    pids = {p["pid"] for p in owned}
    roots = [p for p in owned if p["ppid"] not in pids]
    if len(pids) != len(owned) or len(roots) != 1 or roots[0]["pid"] != roots[0]["pgid"]:
        return False
    connected = {roots[0]["pid"]}
    while True:
        expanded = connected | {p["pid"] for p in owned if p["ppid"] in connected}
        if expanded == connected:
            return connected == pids
        connected = expanded


def _complete(outer):
    # Canonical owned_processes are historical first-observed start identities,
    # whose alive flag may remain True after exit. Only remaining_owned_processes
    # records final cleanup; do not rewrite historical observations into exits.
    owned = outer.get("owned_processes") if type(outer) is dict else None
    return (
        type(outer) is dict
        and _ownership_complete(owned)
        and outer.get("status") == "completed"
        and outer.get("exit_code") == 0
        and outer.get("error") is None
        and outer.get("cleanup_error") is None
        and outer.get("signal_error") is None
        and outer.get("cleanup_forced") is False
        and outer.get("remaining_owned_processes") == []
        and outer.get("received_signals") == []
    )


def _fresh_process(outer, observed):
    need(_ownership_complete(outer["owned_processes"]), "actual rooted process identity")
    pids = {p["pid"] for p in outer["owned_processes"]}
    root = next(p for p in outer["owned_processes"] if p["ppid"] not in pids)
    key = (root["pid"], root["start"])
    need(key not in observed, "fresh owned process per preparation/loader slot")
    observed.add(key)


def _owned(argv, log, guard, *, control=None, timeout=15):
    expected = tuple(argv)
    environment = dict(owner.ENVIRONMENT)
    if control is not None:
        environment[CONTROL] = encoded(control).decode()
    original_spawn = owner.canonical.spawn

    def fixed_spawn(actual, **kwargs):
        need(
            tuple(actual) == expected
            and set(kwargs) == {"cwd", "env", "stdout", "stderr"}
            and kwargs["cwd"] == owner.canonical.ROOT
            and kwargs["env"] == owner.ENVIRONMENT
            and kwargs["stderr"] == subprocess.STDOUT,
            "actual fixed spawn fields",
        )
        stream = kwargs["stdout"]
        token = owner._log_token(stream, log, private=False)
        os.fchmod(stream.fileno(), 0o600)
        guard()
        need(owner._log_token(stream, log, private=True) == token, "log rebound")
        kwargs.update(env=dict(environment), stdin=subprocess.DEVNULL, close_fds=True)
        return original_spawn(list(expected), **kwargs)

    return owner._supervisor_view(fixed_spawn)(
        list(expected), log, timeout=timeout, grace=0.2, environment=dict(owner.ENVIRONMENT)
    )


def _validate_probe(report, entry, node):
    _fields(
        report,
        "schema kind slot nonce_sha256 completed runtime operations "
        "native_host_qualified native_execution_authorized",
    )
    need(
        report["schema"] == "opent1d.lt1-c20-loader-operations/1"
        and all(report[k] == entry[k] for k in ("kind", "slot", "nonce_sha256"))
        and report["completed"] is True
        and report["native_host_qualified"] is False
        and report["native_execution_authorized"] is False,
        "loader report context",
    )
    runtime = report["runtime"]
    _fields(runtime, "pid ppid exec_path node platform arch napi")
    need(
        type(runtime["pid"]) is int
        and runtime["pid"] > 1
        and runtime["pid"] != runtime["ppid"]
        and runtime["ppid"] == entry["owner_pid"]
        and runtime["exec_path"] == node
        and all(
            type(runtime[k]) is str and 0 < len(runtime[k]) <= 128
            for k in ("node", "platform", "arch", "napi")
        ),
        "loader runtime context",
    )
    _fields(report["operations"], " ".join(OPS))
    for name, operation in report["operations"].items():
        _fields(operation, "status sha256 value error_code error_message")
        if operation["status"] == "ok":
            need(
                operation["error_code"] is None
                and operation["error_message"] is None
                and (
                    (_sha(operation["sha256"]) and operation["value"] is None)
                    if name.endswith("read")
                    else operation["sha256"] is None and type(operation["value"]) in (str, int)
                ),
                "typed loader success",
            )
        else:
            need(
                operation["status"] == "error"
                and operation["sha256"] is None
                and operation["value"] is None
                and type(operation["error_code"]) is str
                and 0 < len(operation["error_code"]) <= 64
                and type(operation["error_message"]) is str
                and len(operation["error_message"]) <= 1024,
                "typed loader error",
            )
    return report


def _mac_runtime(report, previous=None):
    """The explicit Mac experiment has no caller-selected runtime platform."""
    runtime = report["runtime"]
    need(
        runtime["platform"] == "darwin"
        and runtime["arch"] == "arm64"
        and re.fullmatch(
            r"v(?:0|[1-9][0-9]*)\.(?:0|[1-9][0-9]*)\.(?:0|[1-9][0-9]*)", runtime["node"]
        )
        is not None
        and runtime["napi"].isascii()
        and runtime["napi"].isdigit()
        and str(int(runtime["napi"])) == runtime["napi"]
        and int(runtime["napi"]) >= 8,
        "fixed Mac platform/architecture, canonical stable Node and N-API-8 minimum",
    )
    current = tuple(runtime[k] for k in ("exec_path", "node", "platform", "arch", "napi"))
    need(previous is None or current == previous, "same runtime across loader slots")
    return current


def _assess(records, initial, final, error):
    result = {"state": "inconclusive", "checks": {}, **AUTHORITY}
    if len(records) != 3 or any(r.get("probe") is None for r in records):
        return result
    complete = all(_complete(r["outer"]) and r["error"] is None for r in records)
    valid, base, twin = [r["probe"]["operations"] for r in records]

    def positive(operations):
        return (
            operations["module_read"]["status"] == operations["addon_read"]["status"] == "ok"
            and operations["module_read"]["sha256"] == initial.get("module.mjs", {}).get("sha256")
            and operations["addon_read"]["sha256"] == initial.get("addon.node", {}).get("sha256")
            and operations["module_import"]["status"] == "ok"
            and operations["module_import"]["value"] == "opent1d-c20-module/1"
            and operations["addon_load"]["status"] == "ok"
            and type(operations["addon_load"]["value"]) is int
            and operations["addon_load"]["value"] == 51020
        )

    checks = {
        "all_owned_slots_complete": complete,
        "parent_context_clean": error is None,
        "same_immutable_artifacts": set(initial) == {"module.mjs", "addon.node"}
        and initial == final,
        "validity_control_positive": positive(valid),
        "twin_positive": positive(twin),
        "base_module_read_permission_error": base["module_read"]["status"] == "error"
        and base["module_read"]["error_code"] in ("EPERM", "EACCES"),
        "base_module_import_failed": base["module_import"]["status"] == "error",
        "base_addon_read_positive": base["addon_read"]["status"] == "ok"
        and base["addon_read"]["sha256"] == initial.get("addon.node", {}).get("sha256"),
        "base_addon_load_failed": base["addon_load"]["status"] == "error",
    }
    result["checks"] = checks
    if all(checks.values()):
        result["state"] = "matched-policy-effect"
    elif all(
        checks[k]
        for k in (
            "all_owned_slots_complete",
            "parent_context_clean",
            "same_immutable_artifacts",
            "validity_control_positive",
            "twin_positive",
        )
    ) and any(base[n]["status"] == "ok" for n in ("module_read", "module_import", "addon_load")):
        result["state"] = "base-unconfined"
    return result


def _read_log(path):
    snapshot = _snapshot(path, maximum=65536)
    need(snapshot["identity"][2:5] == [os.getuid(), 0o600, 1], "private parent-owned actual log")
    raw = Path(path).read_bytes()
    need(digest(raw) == snapshot["sha256"], "actual bounded log bytes")
    return {"snapshot": snapshot, "raw_b64": base64.b64encode(raw).decode()}


def _directory(path):
    info = Path(path).lstat()
    need(
        stat.S_ISDIR(info.st_mode)
        and info.st_uid == os.getuid()
        and Path(path).resolve() == Path(path),
        "physical private directory",
    )
    return [info.st_dev, info.st_ino, info.st_uid, stat.S_IMODE(info.st_mode)]


def capture(parent, *, expected_identity, expected_toolchain):
    """Explicit reviewed Mac experiment only, including bounded compilation.

    All partial preparation/loader records are retained. A failed witness write
    returns no pin, including a write which created incomplete physical bytes.
    """
    source = source_identity()
    records = [
        {
            "slot": slot,
            "entry": None,
            "profile": None,
            "outer": None,
            "log": None,
            "probe": None,
            "error": None,
            "status": "not-run",
        }
        for slot in SLOTS
    ]
    report = {
        "schema": "opent1d.lt1-c20-loader-witness/1",
        "kind": "invented",
        "scope": "ordinary-tooling-fixed-module-addon-only",
        "source_identity": source,
        "producer_root": str(ROOT),
        "toolchain": None,
        "context": None,
        "preparation": [],
        "header_closure": {},
        "initial_artifacts": {},
        "final_artifacts": {},
        "records": records,
        "error": None,
        "all_slots_accounted": True,
        "scientific_sessions_run": False,
        "selected_candidate_started": False,
        **AUTHORITY,
    }
    ready = False
    try:
        need(source == expected_identity, "reviewed exact tooling source")
        need(sys.platform == "darwin" and platform.machine() == "arm64", "explicit arm64 Mac only")
        tools = toolchain_identity()
        need(tools == expected_toolchain, "reviewed fixed installed toolchain")
        report["toolchain"] = tools
        parent = Path(parent)
        info = parent.lstat()
        need(
            parent.is_absolute()
            and parent.resolve() == parent
            and stat.S_ISDIR(info.st_mode)
            and info.st_uid == os.getuid()
            and stat.S_IMODE(info.st_mode) == 0o700
            and not any(parent.iterdir())
            and not parent.is_relative_to(ROOT)
            and not ROOT.is_relative_to(parent)
            and not any(parent.is_relative_to(Path(p)) for p in SYSTEM_READ),
            "fresh private parent outside checkout/system read roots",
        )
        ready = True
        targets, build, logs = (parent / name for name in ("targets", "build", "records"))
        parent_sig = [info.st_dev, info.st_ino, info.st_uid, stat.S_IMODE(info.st_mode)]
        report["context"] = {
            "parent": str(parent),
            "parent_identity": parent_sig,
            "targets": str(targets),
            "build": str(build),
            "records": str(logs),
            "directories": {},
            "owner_pid": os.getpid(),
        }
        directories = report["context"]["directories"]
        for path in (targets, build, logs):
            path.mkdir(mode=0o700)
            directories[str(path)] = _directory(path)

        def guard():
            now = parent.lstat()
            need(
                [now.st_dev, now.st_ino, now.st_uid, stat.S_IMODE(now.st_mode)] == parent_sig
                and parent.resolve() == parent,
                "parent rebound",
            )
            need(
                source_identity() == source and toolchain_identity() == tools,
                "source/toolchain drift",
            )
            for path, signature in directories.items():
                need(_directory(path) == signature, "preparation directory rebound")
            for path, expected in report["header_closure"].items():
                need(_snapshot(path, maximum=16 * 1024 * 1024) == expected, "header closure drift")
            for item in [*report["preparation"], *records]:
                if item.get("log") is not None:
                    name = item["phase"] if "phase" in item else item["slot"]
                    need(
                        _snapshot(logs / (name + ".log"), maximum=65536) == item["log"]["snapshot"],
                        "retained actual log changed",
                    )

        _create(targets / "module.mjs", MODULE.read_bytes())
        (targets / "module.mjs").chmod(0o400)
        observed_processes = set()
        for scan in (True, False):
            name = "dependency-scan" if scan else "compile"
            log = logs / (name + ".log")
            item = {"phase": name, "outer": None, "log": None}
            report["preparation"].append(item)
            guard()
            item["outer"] = _owned(
                _compile_argv(tools["sdk"], targets, build, scan=scan), log, guard
            )
            if item["outer"]["owned_processes"]:
                _fresh_process(item["outer"], observed_processes)
            item["log"] = _read_log(log)
            need(_complete(item["outer"]), "actual " + name + " owner incomplete")
            dependencies = _dependencies(
                (build / ("dependencies.mk" if scan else "compiled-dependencies.mk")).read_bytes(),
                tools["sdk"],
            )
            if scan:
                report["header_closure"] = dependencies
            else:
                need(dependencies == report["header_closure"], "emitted header closure changed")
            guard()
        (targets / "addon.node").chmod(0o400)
        targets.chmod(0o500)
        directories[str(targets)] = _directory(targets)

        def artifacts():
            need(
                set(os.listdir(targets)) == {"module.mjs", "addon.node"}
                and stat.S_IMODE(targets.lstat().st_mode) == 0o500,
                "closed immutable artifacts",
            )
            return {
                name: _snapshot(targets / name, private=True, maximum=16 * 1024 * 1024)
                for name in ("module.mjs", "addon.node")
            }

        report["initial_artifacts"] = artifacts()
        observed_runtime = None
        for record in records:
            slot = record["slot"]
            entry = {
                "kind": "invented",
                "slot": slot,
                "nonce_sha256": secrets.token_hex(32),
                "owner_pid": os.getpid(),
                "targets": str(targets),
            }
            record["entry"] = entry
            log = logs / (slot + ".log")
            command = [tools["node"], str(SCRIPT)]
            if slot != "validity-control":
                record["profile"] = _profile(tools["node"], targets, slot, log)
                command = [str(SANDBOX), "-p", record["profile"], *command]

            def slot_guard():
                guard()
                need(artifacts() == report["initial_artifacts"], "artifact changed before loader")

            record["outer"] = _owned(command, log, slot_guard, control=entry)
            if record["outer"]["owned_processes"]:
                _fresh_process(record["outer"], observed_processes)
            record["log"] = _read_log(log)
            raw = base64.b64decode(record["log"]["raw_b64"], validate=True)
            need(raw.endswith(b"\n") and raw.count(b"\n") == 1, "one actual loader report")
            probe = _validate_probe(
                json.loads(raw, object_pairs_hook=_unique), entry, tools["node"]
            )
            observed_runtime = _mac_runtime(probe, observed_runtime)
            record["probe"] = probe
            need(_complete(record["outer"]), "actual loader owner incomplete")
            need(artifacts() == report["initial_artifacts"], "artifact changed after loader")
            record["status"] = "completed"
            if slot == "validity-control":
                operations = record["probe"]["operations"]
                need(
                    all(op["status"] == "ok" for op in operations.values())
                    and operations["module_import"]["value"] == "opent1d-c20-module/1"
                    and operations["addon_load"]["value"] == 51020,
                    "valid module/addon positive control unavailable",
                )
        guard()
        report["final_artifacts"] = artifacts()
    except (ValueError, OSError, UnicodeError, KeyboardInterrupt) as error:
        report["error"] = type(error).__name__ + ": " + str(error)
        for record in records:
            if record["status"] != "completed":
                record["error"] = report["error"]
                record["status"] = "incomplete" if record["outer"] is not None else "not-run"
    report["assessment"] = _assess(
        records, report["initial_artifacts"], report["final_artifacts"], report["error"]
    )
    pin, write_error = None, None
    if ready:
        try:
            raw = encoded(report)
            _create(parent / "loader-result.json", raw)
            pin = digest(raw)
        except OSError as error:
            write_error = type(error).__name__ + ": " + str(error)
    else:
        write_error = "private parent not prepared; no witness persisted"
    if write_error is not None and report["assessment"]["state"] == "matched-policy-effect":
        report["assessment"] = {**report["assessment"], "state": "inconclusive"}
    return {
        **report,
        "parent_witness_sha256": pin,
        "parent_witness_error": write_error,
        "private_evidence_may_remain": ready,
    }


def _snapshot_data(value):
    _fields(value, "identity sha256")
    need(
        type(value["identity"]) is list
        and len(value["identity"]) == 8
        and all(type(v) is int and v >= 0 for v in value["identity"])
        and _sha(value["sha256"]),
        "typed historical file snapshot",
    )


def _path_data(value):
    need(
        type(value) is str
        and 0 < len(value) <= 4096
        and "\0" not in value
        and PurePosixPath(value).is_absolute()
        and str(PurePosixPath(value)) == value
        and ".." not in PurePosixPath(value).parts,
        "canonical historical absolute path",
    )
    return PurePosixPath(value)


def _log_data(value, uid):
    _fields(value, "snapshot raw_b64")
    _snapshot_data(value["snapshot"])
    need(
        type(value["raw_b64"]) is str and len(value["raw_b64"]) <= 87384,
        "bounded historical log bytes",
    )
    raw = base64.b64decode(value["raw_b64"], validate=True)
    need(
        len(raw) <= 65536
        and base64.b64encode(raw).decode() == value["raw_b64"]
        and value["snapshot"]["identity"][3:5] == [0o600, 1]
        and value["snapshot"]["identity"][2] == uid
        and value["snapshot"]["identity"][5] == len(raw)
        and digest(raw) == value["snapshot"]["sha256"],
        "actual retained log binding",
    )
    return raw


def _outer_data(outer, argv, owner_pid):
    required = {
        "argv",
        "status",
        "exit_code",
        "error",
        "cleanup_forced",
        "owned_processes",
        "remaining_owned_processes",
        "received_signals",
    }
    need(
        type(outer) is dict
        and required <= outer.keys()
        and outer.keys() <= required | {"cleanup_error", "signal_error"}
        and outer["argv"] == argv
        and outer["status"] in ("completed", "failed", "interrupted")
        and type(outer["exit_code"]) in (int, type(None))
        and type(outer["cleanup_forced"]) is bool
        and type(outer["received_signals"]) is list
        and len(outer["received_signals"]) <= 128
        and all(type(v) is int for v in outer["received_signals"]),
        "actual typed fixed outer",
    )
    for name in ("error", "cleanup_error", "signal_error"):
        need(
            outer.get(name) is None or type(outer[name]) is str and len(outer[name]) <= 4096,
            "bounded actual outer error",
        )
    for name in ("owned_processes", "remaining_owned_processes"):
        values = outer[name]
        if values is None:
            need(name == "remaining_owned_processes", "owned observation denominator")
            continue
        need(type(values) is list and len(values) <= 256, "bounded actual ownership")
        for value in values:
            _fields(value, "pid ppid pgid start alive")
            need(
                all(type(value[k]) is int and value[k] > 0 for k in ("pid", "ppid", "pgid"))
                and type(value["start"]) is str
                and 0 < len(value["start"]) <= 512
                and type(value["alive"]) is bool,
                "actual owned start identity",
            )
        need(len({v["pid"] for v in values}) == len(values), "unique historical owned PIDs")
    if outer["owned_processes"]:
        need(_ownership_complete(outer["owned_processes"]), "actual rooted ownership ancestry")
        pids = {p["pid"] for p in outer["owned_processes"]}
        root = next(p for p in outer["owned_processes"] if p["ppid"] not in pids)
        need(root["ppid"] == owner_pid, "actual live parent/root session identity")


def _toolchain_data(tools):
    _fields(tools, "schema node sdk files headers")
    node, sdk = _path_data(tools["node"]), _path_data(tools["sdk"])
    need(
        tools["schema"] == "opent1d.lt1-c20-installed-toolchain/1"
        and node.name == "node"
        and sdk.parent == SDK.parent,
        "fixed historical installed toolchain",
    )
    expected_files = {
        str(p) for p in (CLANG, LINKER, SANDBOX, DYLD, sdk / "SDKSettings.json", node)
    }
    expected_headers = {
        str(HEADERS / n)
        for n in (
            "node_api.h",
            "node_api_types.h",
            "js_native_api.h",
            "js_native_api_types.h",
            "node_version.h",
        )
    }
    need(
        type(tools["files"]) is dict
        and set(tools["files"]) == expected_files
        and type(tools["headers"]) is dict
        and set(tools["headers"]) == expected_headers,
        "complete historical compiler/linker/runtime/header audit",
    )
    for snapshot in [*tools["files"].values(), *tools["headers"].values()]:
        _snapshot_data(snapshot)
        need(snapshot["identity"][5] <= 512 * 1024 * 1024, "bounded installed tool")
    need(
        tools["files"][str(node)]["sha256"] != RUNTIME["executable_sha256"],
        "historical selected candidate excluded",
    )
    return node, sdk


def inspect(raw, expected_sha256, *, expected_identity):
    """Read retained bytes only: never reopen historical tools or artifact paths."""
    need(
        type(raw) is bytes and 0 < len(raw) <= 2 * 1024 * 1024 and digest(raw) == expected_sha256,
        "externally pinned parent witness",
    )
    report = json.loads(raw, object_pairs_hook=_unique)
    _fields(
        report,
        "schema kind scope source_identity producer_root toolchain context preparation "
        "header_closure initial_artifacts final_artifacts records error all_slots_accounted "
        "scientific_sessions_run selected_candidate_started assessment " + " ".join(AUTHORITY),
    )
    need(
        report["schema"] == "opent1d.lt1-c20-loader-witness/1"
        and report["kind"] == "invented"
        and report["scope"] == "ordinary-tooling-fixed-module-addon-only"
        and report["all_slots_accounted"] is True
        and report["scientific_sessions_run"] is False
        and report["selected_candidate_started"] is False
        and all(report[k] is False for k in AUTHORITY),
        "unqualified ordinary-tooling witness",
    )
    current = source_identity()
    need(current == expected_identity, "current reader source")
    producer = report["source_identity"]
    _fields(producer, "implementation python executable_sha256")
    need(
        type(producer["implementation"]) is dict
        and producer["implementation"].keys() == current["implementation"].keys()
        and all(_sha(v) for v in producer["implementation"].values()),
        "complete producer audit",
    )
    old, new = copy.deepcopy(producer), copy.deepcopy(current)
    for name in AUTHORITY_FILES:
        old["implementation"].pop(name, None)
        new["implementation"].pop(name, None)
    need(old == new, "unchanged reader code/Python projection")
    producer_root = _path_data(report["producer_root"])
    for label in ("initial_artifacts", "final_artifacts"):
        values = report[label]
        need(
            type(values) is dict and set(values) <= {"module.mjs", "addon.node"},
            "fixed artifact set",
        )
        for snapshot in values.values():
            _snapshot_data(snapshot)
            need(
                snapshot["identity"][3:5] == [0o400, 1]
                and snapshot["identity"][5] <= 16 * 1024 * 1024,
                "immutable artifact snapshot",
            )
    tools = report["toolchain"]
    if tools is not None:
        node, sdk = _toolchain_data(tools)
    need(
        type(report["header_closure"]) is dict and len(report["header_closure"]) <= 256,
        "bounded header closure",
    )
    for snapshot in report["header_closure"].values():
        _snapshot_data(snapshot)
        need(snapshot["identity"][5] <= 16 * 1024 * 1024, "bounded historical header")
    context = report["context"]
    if context is not None:
        _fields(context, "parent parent_identity targets build records directories owner_pid")
        parent = _path_data(context["parent"])
        signature = context["parent_identity"]
        need(
            type(signature) is list
            and len(signature) == 4
            and all(type(v) is int and v >= 0 for v in signature)
            and signature[3] == 0o700
            and not parent.is_relative_to(producer_root)
            and not producer_root.is_relative_to(parent)
            and not any(parent.is_relative_to(PurePosixPath(p)) for p in SYSTEM_READ),
            "private historical parent binding",
        )
        need(
            type(context["owner_pid"]) is int and context["owner_pid"] > 1,
            "historical experiment owner PID",
        )
        for name in ("targets", "build", "records"):
            need(_path_data(context[name]) == parent / name, "fixed historical preparation role")
        need(
            type(context["directories"]) is dict
            and set(context["directories"])
            <= {context[n] for n in ("targets", "build", "records")},
            "fixed partial directory bindings",
        )
        directory_roles = [context[name] for name in ("targets", "build", "records")]
        need(
            set(context["directories"]) in [set(directory_roles[:i]) for i in range(4)],
            "actual directory creation prefix",
        )
        for path, sig in context["directories"].items():
            need(
                type(sig) is list
                and len(sig) == 4
                and all(type(v) is int and v >= 0 for v in sig)
                and sig[2] == signature[2]
                and sig[3] in ((0o500, 0o700) if path == context["targets"] else (0o700,)),
                "typed preparation directory",
            )
        physical = [tuple(sig[:2]) for sig in context["directories"].values()]
        need(
            len(physical) == len(set(physical)) and tuple(signature[:2]) not in physical,
            "distinct physical preparation directories",
        )
    need(
        type(report["preparation"]) is list
        and len(report["preparation"]) <= 2
        and [p.get("phase") for p in report["preparation"]]
        == ["dependency-scan", "compile"][: len(report["preparation"])],
        "planned preparation prefix",
    )
    observed_processes = set()
    for preparation in report["preparation"]:
        _fields(preparation, "phase outer log")
        need(
            tools is not None
            and context is not None
            and set(context["directories"])
            == {context[n] for n in ("targets", "build", "records")},
            "actual complete preparation directory context",
        )
        if preparation["outer"] is not None:
            argv = _compile_argv(
                sdk,
                PurePosixPath(context["targets"]),
                PurePosixPath(context["build"]),
                scan=preparation["phase"] == "dependency-scan",
                source_root=producer_root,
            )
            _outer_data(preparation["outer"], argv, context["owner_pid"])
            if preparation["outer"]["owned_processes"]:
                _fresh_process(preparation["outer"], observed_processes)
        if preparation["log"] is not None:
            need(preparation["outer"] is not None, "actual preparation log")
            _log_data(preparation["log"], context["parent_identity"][2])
    if report["initial_artifacts"]:
        need(
            tools is not None
            and context is not None
            and len(report["preparation"]) == 2
            and all(_complete(p["outer"]) and p["log"] is not None for p in report["preparation"])
            and context["directories"].get(context["targets"], [None] * 4)[3] == 0o500,
            "completed compilation before immutable artifacts",
        )
        addon = producer_root / ADDON.relative_to(ROOT).as_posix()
        closure = report["header_closure"]
        napi_headers = {
            str(HEADERS / name)
            for name in (
                "node_api.h",
                "node_api_types.h",
                "js_native_api.h",
                "js_native_api_types.h",
            )
        }
        need(
            str(addon) in closure
            and napi_headers <= closure.keys()
            and all(closure[name] == tools["headers"][name] for name in napi_headers)
            and closure[str(addon)]["sha256"]
            == producer["implementation"][ADDON.relative_to(ROOT).as_posix()]
            and all(
                _path_data(p) == addon
                or any(PurePosixPath(p).is_relative_to(r) for r in (sdk, HEADERS, RESOURCES))
                for p in closure
            ),
            "fixed complete historical header/source closure",
        )
        for name, snapshot in report["initial_artifacts"].items():
            need(snapshot["identity"][2] == context["parent_identity"][2], "parent-owned artifact")
            if name == "module.mjs":
                need(
                    snapshot["sha256"]
                    == producer["implementation"][MODULE.relative_to(ROOT).as_posix()],
                    "source-owned module bytes",
                )
    need(
        (report["error"] is None or type(report["error"]) is str and len(report["error"]) <= 16384)
        and type(report["records"]) is list
        and [r.get("slot") for r in report["records"]] == list(SLOTS),
        "all planned slots",
    )
    nonces = []
    observed_runtime = None
    for record in report["records"]:
        _fields(record, "slot entry profile outer log probe error status")
        need(
            record["status"] in ("completed", "incomplete", "not-run")
            and type(record["error"]) in (str, type(None)),
            "typed slot outcome",
        )
        entry = record["entry"]
        if entry is not None:
            need(tools is not None and context is not None, "actual slot context")
            _fields(entry, "kind slot nonce_sha256 owner_pid targets")
            need(
                entry["kind"] == "invented"
                and entry["slot"] == record["slot"]
                and _sha(entry["nonce_sha256"])
                and type(entry["owner_pid"]) is int
                and entry["owner_pid"] > 1
                and entry["owner_pid"] == context["owner_pid"]
                and entry["targets"] == context["targets"],
                "slot identity",
            )
            nonces.append(entry["nonce_sha256"])
            log = PurePosixPath(context["records"]) / (record["slot"] + ".log")
            command = [str(node), str(producer_root / SCRIPT.relative_to(ROOT).as_posix())]
            if record["slot"] == "validity-control":
                need(record["profile"] is None, "unprofiled validity control")
            else:
                policy = _profile(
                    node, context["targets"], record["slot"], log, source_root=producer_root
                )
                need(record["profile"] == policy, "fixed matched historical profile")
                command = [str(SANDBOX), "-p", policy, *command]
            if record["outer"] is not None:
                _outer_data(record["outer"], command, context["owner_pid"])
                if record["outer"]["owned_processes"]:
                    _fresh_process(record["outer"], observed_processes)
        else:
            need(
                all(record[k] is None for k in ("profile", "outer", "log", "probe"))
                and record["status"] == "not-run",
                "unattempted slot stays missing",
            )
        if record["log"] is not None:
            need(record["outer"] is not None, "actual slot log requires outer")
            data = _log_data(record["log"], context["parent_identity"][2])
        if record["probe"] is not None:
            need(
                tools is not None
                and record["entry"] is not None
                and record["log"] is not None
                and record["outer"] is not None,
                "actual probe bindings",
            )
            _validate_probe(record["probe"], record["entry"], tools["node"])
            observed_runtime = _mac_runtime(record["probe"], observed_runtime)
            need(
                data.endswith(b"\n")
                and data.count(b"\n") == 1
                and json.loads(data, object_pairs_hook=_unique) == record["probe"]
                and any(
                    p["pid"] == record["probe"]["runtime"]["pid"]
                    and p["ppid"] == entry["owner_pid"]
                    and p["pgid"] == p["pid"]
                    for p in record["outer"]["owned_processes"]
                ),
                "actual owned report bytes",
            )
        if record["status"] == "completed":
            need(
                record["probe"] is not None
                and _complete(record["outer"])
                and record["error"] is None,
                "actual complete slot",
            )
    need(len(nonces) == len(set(nonces)), "fresh per-slot nonces")
    result = _assess(
        report["records"], report["initial_artifacts"], report["final_artifacts"], report["error"]
    )
    need(
        report["assessment"] == result and source_identity() == current, "stable strict assessment"
    )
    return result
