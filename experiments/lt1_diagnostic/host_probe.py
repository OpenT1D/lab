"""Explicit macOS fixture qualification; never dispatch or admit native LT1."""

import argparse
import errno
import hashlib
import json
import platform
import socket
import subprocess
import sys
import threading
import time
from pathlib import Path

from experiments.gui.ownership import ProcessTable
from experiments.m4.initial_load.common import source_closure
from experiments.shared_services.execution import supervise

HERE = Path(__file__).resolve().parent
MODES = ("complete", "failure", "deadline", "cancel")
SANDBOX = Path("/usr/bin/sandbox-exec")
DYLD_PROFILE = Path("/System/Library/Sandbox/Profiles/dyld-support.sb")
ROOT = HERE.parents[1]


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def sources():
    return {
        name: digest(ROOT / name)
        for name in source_closure(
            (
                "experiments/lt1_diagnostic/host_probe.py",
                "experiments/lt1_diagnostic/host_fixture.py",
            )
        )
    }


def check_final_sources(report):
    try:
        if report["implementation"] != sources():
            report.update(status="failed", source_change=True)
    except (OSError, SyntaxError, ValueError) as error:
        report.update(status="failed", source_change=True, source_error=str(error))


def quoted(path):
    # SBPL strings use quoted, escaped paths; no caller-supplied policy text.
    return json.dumps(str(path))


def profile(interpreter, python_root, fixture, inputs, output):
    """Fixture-only profile: no default network or arbitrary user-file access."""
    return (
        "\n".join(
            [
                "(version 1)",
                "(deny default)",
                f"(import {quoted(DYLD_PROFILE)})",
                "(allow process-fork)",
                f"(allow process-exec (literal {quoted(interpreter)}))",
                "(allow sysctl-read)",
                "(allow mach-lookup)",
                "(allow file-read-metadata)",
                '(allow file-read* (subpath "/System") (subpath "/usr/lib") '
                '(subpath "/Library/Apple"))',
                '(allow file-read* (literal "/dev/null") (literal "/dev/urandom") '
                '(literal "/dev/random"))',
                f"(allow file-read* (subpath {quoted(python_root)}) (literal {quoted(fixture)}))",
                f'(allow file-map-executable (subpath "/System") (subpath "/usr/lib") '
                f"(subpath {quoted(python_root)}))",
                f"(allow file-read* (subpath {quoted(inputs)}) (subpath {quoted(output)}))",
                f"(allow file-write* (subpath {quoted(output)}))",
            ]
        )
        + "\n"
    )


def validate_case(mode, receipt, output, unrelated_alive):
    """A missing observation never becomes a passing confinement result."""
    if mode not in MODES or receipt.get("received_signals") != []:
        raise ValueError("Unknown case or external interruption")
    expected = (
        "completed" if mode == "complete" else "interrupted" if mode == "cancel" else "failed"
    )
    if (
        receipt["status"] != expected
        or receipt["remaining_owned_processes"] != []
        or not unrelated_alive
    ):
        raise ValueError("Status, cleanup or unrelated-process observation differs")
    if mode == "complete" and receipt["exit_code"] != 0:
        raise ValueError("Completion needs zero exit")
    if mode == "failure" and receipt["exit_code"] != 23:
        raise ValueError("Primary fixture exit not retained")
    if mode in {"deadline", "cancel"} and receipt["error"] != (
        "WorkerDeadline" if mode == "deadline" else "Cancelled"
    ):
        raise ValueError("Deadline/cancellation cause differs")
    checks = json.loads((output / "boundary.json").read_bytes())
    groups = [checks]
    if mode != "complete":
        child = json.loads((output / "child-ready.json").read_bytes())["pid"]
        if child not in [row["pid"] for row in receipt["owned_processes"]]:
            raise ValueError("Child was not observed under live ownership")
        actual = ProcessTable().one(child)
        if actual is not None and actual["alive"]:
            raise ValueError("Fixture child remains alive")
        groups.append(json.loads((output / "child-boundary.json").read_bytes()))
        first = (output / "heartbeat.txt").read_bytes()
        time.sleep(0.08)
        if (output / "heartbeat.txt").read_bytes() != first:
            raise ValueError("Descendant sentinel still changes")
    for group in groups:
        if not (
            all(
                group[name]["denied"] is True
                and group[name]["errno"] in {errno.EPERM, errno.EACCES}
                for name in ("outside_read", "outside_write", "network")
            )
            and all(
                group[name] is True
                for name in ("allowed_input", "isolated_start", "clean_environment")
            )
        ):
            raise ValueError("Confinement/startup observation missing or failed")
    prefix = [json.loads(line) for line in (output / "prefix.jsonl").read_bytes().splitlines()]
    if not all(
        type(row.get("ordinal")) is int and type(row.get("time_ms")) is int for row in prefix
    ) or prefix != [
        {"kind": "invented", "ordinal": i, "time_ms": t} for i, t in enumerate((0, 60000, 150000))
    ]:
        raise ValueError("Durable invented prefix differs")
    if mode != "complete" and (output / "completed.json").exists():
        raise ValueError("Failure promoted to completed")
    if mode == "complete" and json.loads((output / "completed.json").read_bytes()) != {
        "kind": "invented",
        "status": "completed",
    }:
        raise ValueError("Explicit completion marker differs")
    return {"status": "passed", "durable_rows": len(prefix), "boundary_groups": len(groups)}


def qualify(target):
    if sys.platform != "darwin" or platform.machine() != "arm64" or not SANDBOX.is_file():
        raise ValueError("Explicit Darwin arm64 fixture host with sandbox-exec required")
    target = Path(target).absolute()
    if target.parent.resolve() != target.parent or target.exists() or target.is_symlink():
        raise ValueError("New output under a canonical existing private parent required")
    interpreter, python_root = Path(sys.executable).resolve(), Path(sys.base_prefix).resolve()
    environment = {"LANG": "C", "LC_ALL": "C", "PATH": "/usr/bin:/bin"}
    report = {
        "schema": "opent1d.lt1-host-fixture-qualification/1",
        "kind": "invented",
        "host": {
            "name": platform.node(),
            "platform": sys.platform,
            "arch": platform.machine(),
            "os": platform.mac_ver()[0],
        },
        "implementation": sources(),
        "runtime": {
            "python": sys.version,
            "executable_sha256": digest(interpreter),
            "sandbox_sha256": digest(SANDBOX),
            "dyld_profile_sha256": digest(DYLD_PROFILE),
        },
        "authorizations": {"setup": False, "native_execution": False},
        "status": "failed",
        "cases": {mode: {"status": "not_run"} for mode in MODES},
    }
    target.mkdir(mode=0o700)
    outside, inputs = target / "outside", target / "input"
    outside.mkdir()
    inputs.mkdir()
    (outside / "secret.txt").write_bytes(b"invented sentinel\n")
    (inputs / "invented.txt").write_bytes(b"invented-only\n")
    unrelated = None
    try:
        unrelated = subprocess.Popen(
            [str(interpreter), "-I", "-S", "-B", "-c", "import time; time.sleep(120)"],
            env=environment,
            start_new_session=True,
        )
        with socket.socket() as server:
            server.bind(("127.0.0.1", 0))
            server.listen(16)
            port = server.getsockname()[1]
            with socket.create_connection(("127.0.0.1", port), timeout=1):
                pass
            report["unconfined_network_control"] = True
            for mode in MODES:
                output = target / mode
                output.mkdir()
                policy = profile(interpreter, python_root, HERE / "host_fixture.py", inputs, output)
                (target / (mode + ".sb")).write_text(policy)
                cancel, stop = threading.Event(), threading.Event()
                receipt = {}

                def cancel_ready(folder=output):
                    while not stop.wait(0.01):
                        if (folder / "child-ready.json").exists():
                            # Observation loop must see the child before cancellation.
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
                        str(SANDBOX),
                        "-p",
                        policy,
                        str(interpreter),
                        "-I",
                        "-S",
                        "-B",
                        str(HERE / "host_fixture.py"),
                        mode,
                        "--input",
                        str(inputs),
                        "--output",
                        str(output),
                        "--outside",
                        str(outside),
                        "--port",
                        str(port),
                    ]
                    receipt = supervise(
                        argv,
                        output / "process.log",
                        timeout=2,
                        grace=0.2,
                        cancel=cancel,
                        environment=environment,
                    )
                    (output / "process-receipt.json").write_text(
                        json.dumps(receipt, indent=2) + "\n"
                    )
                    observed = validate_case(mode, receipt, output, unrelated.poll() is None)
                    if (outside / "secret.txt").read_bytes() != b"invented sentinel\n" or (
                        outside / "new.txt"
                    ).exists():
                        raise ValueError("Outside sentinel changed")
                    report["cases"][mode] = observed
                except (OSError, ValueError, KeyError) as error:
                    report["cases"][mode] = {"status": "failed", "error": str(error)}
                finally:
                    stop.set()
                    if thread:
                        thread.join(timeout=1)
                if receipt.get("received_signals"):
                    report["external_interruption"] = receipt["received_signals"]
                    break
        if all(case["status"] == "passed" for case in report["cases"].values()):
            report["status"] = "passed"
    except (OSError, ValueError, subprocess.SubprocessError) as error:
        report.update(status="failed", error=str(error))
    finally:
        if unrelated is not None:
            try:
                unrelated.terminate()
                unrelated.wait(timeout=5)
                report["unrelated_cleanup_exit"] = unrelated.returncode
            except (OSError, subprocess.SubprocessError) as error:
                report["status"] = "failed"
                report["unrelated_cleanup_error"] = str(error)
                if unrelated.poll() is None:
                    try:
                        unrelated.kill()
                        unrelated.wait(timeout=2)
                    except (OSError, subprocess.SubprocessError) as final_error:
                        report["unrelated_cleanup_final_error"] = str(final_error)
        check_final_sources(report)
        report["files"] = {
            p.relative_to(target).as_posix(): digest(p)
            for p in sorted(target.rglob("*"))
            if p.is_file()
        }
        (target / "qualification.json").write_text(json.dumps(report, indent=2) + "\n")
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    report = qualify(args.output)
    print(
        json.dumps(
            {
                "status": report["status"],
                "kind": report["kind"],
                "authorizations": report["authorizations"],
            }
        )
    )
    return 0 if report["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
