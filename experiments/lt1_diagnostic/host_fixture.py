"""Invented confinement/lifecycle fixture. Contains no engine or model code."""

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


def save(path, value):
    with path.open("x") as stream:
        json.dump(value, stream, sort_keys=True)
        stream.flush()
        os.fsync(stream.fileno())


def boundaries(args):
    observed = {}
    for name, operation in {
        "outside_read": lambda: (args.outside / "secret.txt").read_bytes(),
        "outside_write": lambda: (args.outside / "new.txt").write_bytes(b"escape"),
        "network": lambda: socket.create_connection(("127.0.0.1", args.port), timeout=1),
    }.items():
        try:
            result = operation()
            if name == "network":
                result.close()
            observed[name] = {"denied": False}
        except OSError as error:
            observed[name] = {
                "denied": error.errno in {errno.EPERM, errno.EACCES},
                "errno": error.errno,
            }
    observed["allowed_input"] = (args.input / "invented.txt").read_bytes() == b"invented-only\n"
    observed["isolated_start"] = sys.flags.isolated == 1 and sys.flags.no_site == 1
    # CoreFoundation adds this encoding key after an explicitly three-key spawn.
    allowed = {"LANG", "LC_ALL", "PATH", "__CF_USER_TEXT_ENCODING"}
    observed["clean_environment"] = set(os.environ) <= allowed and all(
        os.environ.get(name) == value
        for name, value in {"LANG": "C", "LC_ALL": "C", "PATH": "/usr/bin:/bin"}.items()
    )
    observed["environment_keys"] = sorted(os.environ)
    return observed


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("complete", "failure", "deadline", "cancel", "child"))
    for name in ("input", "output", "outside"):
        parser.add_argument("--" + name, type=Path, required=True)
    parser.add_argument("--port", type=int, required=True)
    args = parser.parse_args()
    child = args.mode == "child"
    if child:
        signal.signal(signal.SIGTERM, signal.SIG_IGN)
    checks = boundaries(args)
    save(args.output / ("child-boundary.json" if child else "boundary.json"), checks)
    if not (
        all(checks[name]["denied"] for name in ("outside_read", "outside_write", "network"))
        and all(checks[name] for name in ("allowed_input", "isolated_start", "clean_environment"))
    ):
        return 17
    if child:
        save(args.output / "child-ready.json", {"pid": os.getpid()})
        while True:
            (args.output / "heartbeat.txt").write_text(str(time.monotonic_ns()))
            time.sleep(0.02)
    with (args.output / "prefix.jsonl").open("x") as stream:
        for ordinal, time_ms in enumerate((0, 60000, 150000)):
            stream.write(
                json.dumps({"kind": "invented", "ordinal": ordinal, "time_ms": time_ms}) + "\n"
            )
            stream.flush()
            os.fsync(stream.fileno())
    if args.mode == "complete":
        save(args.output / "completed.json", {"kind": "invented", "status": "completed"})
        return 0
    command = [sys.executable, "-I", "-S", "-B", __file__, "child", *sys.argv[2:]]
    subprocess.Popen(command, close_fds=True)
    until = time.monotonic() + 5
    while not (args.output / "child-ready.json").exists():
        if time.monotonic() >= until:
            raise RuntimeError("Fixture child did not become ready")
        time.sleep(0.01)
    # Let the external supervisor observe the live child before this entry exits.
    time.sleep(0.15)
    if args.mode == "failure":
        return 23
    while True:
        time.sleep(0.02)


if __name__ == "__main__":
    raise SystemExit(main())
