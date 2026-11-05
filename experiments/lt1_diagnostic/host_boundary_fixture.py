"""Fixed invented Python host-boundary fixture; no native engine or user command."""

import argparse
import errno
import json
import os
import signal
import socket
import subprocess
import sys
import time
from pathlib import Path

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


def save(path, value):
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    with os.fdopen(fd, "w") as stream:
        json.dump(value, stream, sort_keys=True)
        stream.flush()
        os.fsync(stream.fileno())


def observe(operation):
    try:
        operation()
        return {"denied": False}
    except OSError as error:
        return {"denied": error.errno in {errno.EPERM, errno.EACCES}, "errno": error.errno}


def fixed_shell():
    # Inherit existing descriptors: opening DEVNULL under confinement could fail
    # before exec and falsely look like an executable denial.
    subprocess.run(["/bin/sh", "-c", "exit 0"], check=True, timeout=1)


def boundaries(args, child):
    role = "child" if child else "parent"
    staging = args.input / "readonly-staging"

    def network():
        with socket.create_connection(("127.0.0.1", args.port), timeout=1):
            pass

    operations = {
        "outside_read": lambda: (args.outside / "secret.txt").read_bytes(),
        "outside_write": lambda: (args.outside / "new.txt").write_bytes(b"escape"),
        "network": network,
        "readonly_staging_write": lambda: (staging / (role + "-write.txt")).write_bytes(b"escape"),
        "readonly_staging_unlink": lambda: (staging / (role + "-unlink.txt")).unlink(),
        "readonly_staging_chmod": lambda: (staging / (role + "-chmod.txt")).chmod(0o640),
        "nonallowlisted_exec": fixed_shell,
        "scratch_alias_read": lambda: (args.output / "outside-alias").read_bytes(),
        "data_alias_read": lambda: args.data_alias.read_bytes(),
    }
    observed = {name: observe(operation) for name, operation in operations.items()}
    observed["allowed_input"] = (args.input / "invented.txt").read_bytes() == b"invented-only\n"
    allowed_output = args.output / (role + "-allowed.txt")
    fd = os.open(allowed_output, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    with os.fdopen(fd, "wb") as stream:
        stream.write(b"invented scratch\n")
        stream.flush()
        os.fsync(stream.fileno())
    observed["allowed_scratch"] = allowed_output.read_bytes() == b"invented scratch\n"
    observed["isolated_start"] = sys.flags.isolated == 1 and sys.flags.no_site == 1
    allowed = {"LANG", "LC_ALL", "PATH", "__CF_USER_TEXT_ENCODING"}
    observed["clean_environment"] = set(os.environ) <= allowed and all(
        os.environ.get(name) == value
        for name, value in {"LANG": "C", "LC_ALL": "C", "PATH": "/usr/bin:/bin"}.items()
    )
    observed["environment_keys"] = sorted(os.environ)
    return observed


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("complete", "cancel", "child"))
    parser.add_argument("--case", choices=("complete", "cancel"))
    for name in ("input", "output", "outside", "data-alias"):
        parser.add_argument("--" + name, type=Path, required=True)
    parser.add_argument("--port", type=int, required=True)
    args = parser.parse_args()
    child = args.mode == "child"
    if child and args.case is None:
        parser.error("Child needs its fixed parent case")
    if child and args.case == "cancel":
        signal.signal(signal.SIGTERM, signal.SIG_IGN)
    checks = boundaries(args, child)
    save(args.output / ("child-boundary.json" if child else "boundary.json"), checks)
    if not (
        all(checks[name]["denied"] is True for name in DENIALS)
        and all(
            checks[name] is True
            for name in ("allowed_input", "allowed_scratch", "isolated_start", "clean_environment")
        )
    ):
        return 17
    if child:
        save(args.output / "child-ready.json", {"pid": os.getpid()})
        until = time.monotonic() + 0.3
        while args.case == "cancel" or time.monotonic() < until:
            fd = os.open(
                args.output / "heartbeat.txt",
                os.O_WRONLY | os.O_CREAT | os.O_TRUNC | os.O_NOFOLLOW,
                0o600,
            )
            with os.fdopen(fd, "w") as stream:
                stream.write(str(time.monotonic_ns()))
            time.sleep(0.02)
        return 0
    fd = os.open(
        args.output / "prefix.jsonl", os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600
    )
    with os.fdopen(fd, "w") as stream:
        for ordinal, time_ms in enumerate((0, 60000, 150000)):
            stream.write(
                json.dumps({"kind": "invented", "ordinal": ordinal, "time_ms": time_ms}) + "\n"
            )
            stream.flush()
            os.fsync(stream.fileno())
    command = [
        sys.executable,
        "-I",
        "-S",
        "-B",
        __file__,
        "child",
        "--case",
        args.mode,
        *sys.argv[2:],
    ]
    worker = subprocess.Popen(command, close_fds=True)
    until = time.monotonic() + 3
    while not (args.output / "child-ready.json").exists():
        if worker.poll() is not None or time.monotonic() >= until:
            raise RuntimeError("Invented child did not become ready")
        time.sleep(0.01)
    if args.mode == "complete":
        if worker.wait(timeout=3) != 0:
            raise RuntimeError("Invented complete child failed")
        save(args.output / "completed.json", {"kind": "invented", "status": "completed"})
        return 0
    while True:
        time.sleep(0.02)


if __name__ == "__main__":
    raise SystemExit(main())
