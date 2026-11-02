"""Explicit versioned Python boundary fixtures; never native host admission.

Copies outside canonical source paths cannot be qualified.
"""

import argparse
import errno
import json
import os
import platform
import socket
import stat
import subprocess
import sys
import threading
import time
from pathlib import Path

from experiments.lt1_diagnostic import host_probe as legacy

HERE = Path(__file__).resolve().parent
ROOT = legacy.ROOT
MODES = ("complete", "cancel")
DATA_ROOT = Path("/System/Volumes/Data")
DENIALS = (
    "outside_read",
    "outside_write",
    "network",
    "readonly_staging_write",
    "readonly_staging_unlink",
    "readonly_staging_chmod",
    "nonallowlisted_exec",
    "scratch_alias_read",
    "data_alias_read",
)
SENTINEL = b"invented sentinel\n"


class Unsupported(ValueError):
    """A missing or unverified prerequisite is never a denial pass."""


def sources():
    if HERE != ROOT / "experiments/lt1_diagnostic":
        raise ValueError("Integrate reviewed canonical boundary sources before qualification")
    names = {
        "experiments/lt1_diagnostic/host_boundary_probe.py",
        "experiments/lt1_diagnostic/host_boundary_fixture.py",
    }
    while True:
        closed = set(legacy.source_closure(names))
        initializers = {
            Path(*Path(name).parts[:length], "__init__.py").as_posix()
            for name in closed
            for length in range(1, len(Path(name).parts))
        }
        expanded = closed | {name for name in initializers if (ROOT / name).is_file()}
        if expanded == names:
            return {name: legacy.digest(ROOT / name) for name in sorted(names)}
        names = expanded


def check_final_sources(report):
    try:
        if report["implementation"] != sources():
            report.update(status="failed", source_change=True)
    except (OSError, ValueError, SyntaxError) as error:
        report.update(status="failed", source_change=True, source_error=str(error))


def profile(interpreter, python_root, fixture, inputs, output):
    policy = legacy.profile(interpreter, python_root, fixture, inputs, output)
    old = '(subpath "/System")'
    if policy.count(old) != 2:
        raise ValueError("Legacy system profile changed; review boundary successor")
    return policy.replace(old, '(subpath "/System/Library")')


def private_bytes(path, raw):
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    with os.fdopen(fd, "wb") as stream:
        stream.write(raw)
        stream.flush()
        os.fsync(stream.fileno())


def save(path, value):
    private_bytes(path, (json.dumps(value, indent=2) + "\n").encode())


def alias_control(alias, secret):
    try:
        # Firmlink aliases can keep distinct resolved path strings. Require the
        # same canonical filesystem object, not equality of those strings.
        if not (
            alias.is_file()
            and alias.resolve(strict=True).samefile(secret.resolve(strict=True))
            and alias.samefile(secret)
            and alias.read_bytes() == SENTINEL
        ):
            raise Unsupported("Invented alias missing or canonical target differs")
    except OSError as error:
        raise Unsupported("Invented alias has no successful unconfined control") from error
    return True


def data_alias(secret):
    alias = DATA_ROOT / secret.relative_to("/")
    alias_control(alias, secret)
    return alias


def require_controls(controls):
    if set(controls) != set(DENIALS) or not all(value is True for value in controls.values()):
        raise ValueError("Every denial needs a successful unconfined control")


def unconfined_controls(folder, secret, scratch_alias, data_path, port):
    """Operate exclusively on new invented control twins and fixed no-op shell."""
    folder.mkdir(mode=0o700)
    checks = {"outside_read": secret.read_bytes() == SENTINEL}
    target = folder / "outside-write.txt"
    private_bytes(target, b"invented write control\n")
    checks["outside_write"] = target.read_bytes() == b"invented write control\n"
    with socket.create_connection(("127.0.0.1", port), timeout=1):
        checks["network"] = True
    target = folder / "write.txt"
    private_bytes(target, SENTINEL)
    target.write_bytes(b"invented changed control\n")
    checks["readonly_staging_write"] = target.read_bytes() == b"invented changed control\n"
    target = folder / "unlink.txt"
    private_bytes(target, SENTINEL)
    target.unlink()
    checks["readonly_staging_unlink"] = not target.exists()
    target = folder / "chmod.txt"
    private_bytes(target, SENTINEL)
    target.chmod(0o640)
    checks["readonly_staging_chmod"] = stat.S_IMODE(target.stat().st_mode) == 0o640
    result = subprocess.run(
        ["/bin/sh", "-c", "exit 0"],
        timeout=1,
        check=False,
        env={"LANG": "C", "LC_ALL": "C", "PATH": "/usr/bin:/bin"},
    )
    checks["nonallowlisted_exec"] = result.returncode == 0
    checks["scratch_alias_read"] = alias_control(scratch_alias, secret)
    checks["data_alias_read"] = alias_control(data_path, secret)
    require_controls(checks)
    return checks


def validate_group(group):
    if not (
        all(
            isinstance(group.get(name), dict)
            and group[name].get("denied") is True
            and type(group[name].get("errno")) is int
            and group[name]["errno"] in {errno.EPERM, errno.EACCES}
            for name in DENIALS
        )
        and all(
            group.get(name) is True
            for name in ("allowed_input", "allowed_scratch", "isolated_start", "clean_environment")
        )
    ):
        raise ValueError("Required boundary observation missing or failed")


def validate_case(mode, receipt, output, unrelated_alive, controls):
    if mode not in MODES:
        raise ValueError("Unknown versioned boundary case")
    require_controls(controls)
    if type(receipt.get("exit_code")) is not int or receipt.get("cleanup_error") is not None:
        raise ValueError("Exact process exit and successful cleanup required")
    if mode == "complete" and (receipt["exit_code"] != 0 or receipt.get("error") is not None):
        raise ValueError("Completion requires exact zero exit and no primary error")
    result = legacy.validate_case(mode, receipt, output, unrelated_alive)
    child = json.loads((output / "child-ready.json").read_bytes())["pid"]
    if (
        type(child) is not int
        or child <= 0
        or not any(
            row.get("pid") == child and isinstance(row.get("start"), str) and row["start"]
            for row in receipt["owned_processes"]
        )
    ):
        raise ValueError("Child live start identity was not observed")
    actual = legacy.ProcessTable().one(child)
    if actual is not None and actual["alive"]:
        raise ValueError("Boundary child remains alive")
    first = (output / "heartbeat.txt").read_bytes()
    time.sleep(0.08)
    if not first or (output / "heartbeat.txt").read_bytes() != first:
        raise ValueError("Boundary child heartbeat did not stop")
    for name in ("boundary.json", "child-boundary.json"):
        validate_group(json.loads((output / name).read_bytes()))
    return {**result, "boundary_groups": 2, "denials_per_group": len(DENIALS)}


def unchanged(inputs, outside, output, data_path):
    if (outside / "secret.txt").read_bytes() != SENTINEL or (outside / "new.txt").exists():
        raise ValueError("Invented outside sentinel changed")
    for role in ("parent", "child"):
        for operation in ("write", "unlink", "chmod"):
            path = inputs / "readonly-staging" / (role + "-" + operation + ".txt")
            if path.read_bytes() != SENTINEL or stat.S_IMODE(path.stat().st_mode) != 0o600:
                raise ValueError("Invented read-only staging changed")
    alias_control(output / "outside-alias", outside / "secret.txt")
    alias_control(data_path, outside / "secret.txt")


def qualify(target):
    if sys.platform != "darwin" or platform.machine() != "arm64" or not legacy.SANDBOX.is_file():
        raise Unsupported("Explicit Darwin arm64 fixture host with sandbox-exec required")
    target = Path(target).absolute()
    if (
        target.parent.resolve() != target.parent
        or target.exists()
        or target.is_symlink()
        or target.parent.stat().st_uid != os.getuid()
        or stat.S_IMODE(target.parent.stat().st_mode) != 0o700
    ):
        raise ValueError("Fresh output beneath a canonical owner-only parent required")
    implementation = sources()  # Refuses private drafts before any output or process.
    interpreter, python_root = Path(sys.executable).resolve(), Path(sys.base_prefix).resolve()
    environment = {"LANG": "C", "LC_ALL": "C", "PATH": "/usr/bin:/bin"}
    report = {
        "schema": "opent1d.lt1-host-boundary-fixture/1",
        "kind": "invented",
        "host": {"platform": sys.platform, "arch": platform.machine(), "os": platform.mac_ver()[0]},
        "implementation": implementation,
        "runtime": {
            "python": sys.version,
            "executable_sha256": legacy.digest(interpreter),
            "sandbox_sha256": legacy.digest(legacy.SANDBOX),
            "dyld_profile_sha256": legacy.digest(legacy.DYLD_PROFILE),
            "fixed_shell_sha256": legacy.digest(Path("/bin/sh").resolve()),
        },
        "authorizations": {"setup": False, "native_execution": False},
        "limits": [
            "Python fixture only",
            "Broad mach-lookup remains allowed",
            "No hostile-owner/IPC/native/bootstrap or erasure qualification",
        ],
        "status": "failed",
        "cases": {mode: {"status": "not_run"} for mode in MODES},
    }
    target.mkdir(mode=0o700)
    unrelated = None
    old_umask = os.umask(0o077)
    try:
        outside, inputs = target / "outside", target / "input"
        outside.mkdir(mode=0o700)
        inputs.mkdir(mode=0o700)
        private_bytes(outside / "secret.txt", SENTINEL)
        private_bytes(inputs / "invented.txt", b"invented-only\n")
        staging = inputs / "readonly-staging"
        staging.mkdir(mode=0o700)
        for role in ("parent", "child"):
            for operation in ("write", "unlink", "chmod"):
                private_bytes(staging / (role + "-" + operation + ".txt"), SENTINEL)
        data_path = data_alias(outside / "secret.txt")
        unrelated = subprocess.Popen(
            [str(interpreter), "-I", "-S", "-B", "-c", "import time; time.sleep(120)"],
            env=environment,
            start_new_session=True,
        )
        with socket.socket() as server:
            server.bind(("127.0.0.1", 0))
            server.listen(16)
            port = server.getsockname()[1]
            for mode in MODES:
                output = target / mode
                output.mkdir(mode=0o700)
                (output / "outside-alias").symlink_to(outside / "secret.txt")
                controls = unconfined_controls(
                    target / (mode + "-controls"),
                    outside / "secret.txt",
                    output / "outside-alias",
                    data_path,
                    port,
                )
                policy = profile(
                    interpreter, python_root, HERE / "host_boundary_fixture.py", inputs, output
                )
                private_bytes(target / (mode + ".sb"), policy.encode())
                cancel, stop = threading.Event(), threading.Event()
                receipt = {}

                def cancel_ready(folder=output):
                    while not stop.wait(0.01):
                        if (folder / "child-ready.json").exists():
                            if not stop.wait(0.2):
                                cancel.set()
                            return

                thread = (
                    threading.Thread(target=cancel_ready, daemon=True) if mode == "cancel" else None
                )
                if thread:
                    thread.start()
                try:
                    argv = [
                        str(legacy.SANDBOX),
                        "-p",
                        policy,
                        str(interpreter),
                        "-I",
                        "-S",
                        "-B",
                        str(HERE / "host_boundary_fixture.py"),
                        mode,
                        "--input",
                        str(inputs),
                        "--output",
                        str(output),
                        "--outside",
                        str(outside),
                        "--data-alias",
                        str(data_path),
                        "--port",
                        str(port),
                    ]
                    receipt = legacy.supervise(
                        argv,
                        output / "process.log",
                        timeout=4,
                        grace=0.2,
                        cancel=cancel,
                        environment=environment,
                    )
                    save(output / "process-receipt.json", receipt)
                    observed = validate_case(
                        mode, receipt, output, unrelated.poll() is None, controls
                    )
                    unchanged(inputs, outside, output, data_path)
                    report["cases"][mode] = {**observed, "unconfined_controls": controls}
                except (OSError, ValueError, KeyError, subprocess.SubprocessError) as error:
                    report["cases"][mode] = {
                        "status": "failed",
                        "error": str(error),
                        "unconfined_controls": controls,
                    }
                finally:
                    stop.set()
                    if thread:
                        thread.join(timeout=1)
                        if thread.is_alive():
                            report["cases"][mode] = {
                                "status": "failed",
                                "error": "Cancel observer remains",
                            }
                if receipt.get("received_signals"):
                    report["external_interruption"] = receipt["received_signals"]
                    break
        if all(case["status"] == "passed" for case in report["cases"].values()):
            report["status"] = "passed"
    except Unsupported as error:
        report.update(status="unsupported", error=str(error))
    except (OSError, ValueError, subprocess.SubprocessError) as error:
        report.update(status="failed", error=str(error))
    finally:
        if unrelated is not None:
            if unrelated.poll() is not None:
                report.update(status="failed", unrelated_died_before_cleanup=True)
            try:
                unrelated.terminate()
                unrelated.wait(timeout=5)
                report["unrelated_reaped"] = True
            except (OSError, subprocess.SubprocessError) as error:
                report.update(status="failed", unrelated_cleanup_error=str(error))
                try:
                    if unrelated.poll() is None:
                        unrelated.kill()
                    unrelated.wait(timeout=2)
                    report["unrelated_reaped"] = True
                except (OSError, subprocess.SubprocessError) as final_error:
                    report["unrelated_cleanup_final_error"] = str(final_error)
        check_final_sources(report)
        try:
            report["files"] = {
                p.relative_to(target).as_posix(): legacy.digest(p)
                for p in sorted(target.rglob("*"))
                if p.is_file() and not p.is_symlink()
            }
            save(target / "qualification.json", report)
        finally:
            os.umask(old_umask)
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    report = qualify(args.output)
    print(json.dumps({key: report[key] for key in ("status", "kind", "authorizations")}))
    return 0 if report["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
