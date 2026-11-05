"""Fixed isolated Python process fixture; no Node, model or supplied command."""

import errno
import json
import os
import signal
import subprocess
import sys
import time
from pathlib import Path


def observation(folder, role):
    config = json.loads((folder / "fixture.json").read_bytes())
    try:
        value = os.fstat(config["fd"])
        inherited = [value.st_dev, value.st_ino] == config["identity"]
    except OSError as error:
        if error.errno != errno.EBADF:
            raise
        inherited = False
    result = {
        "pid": os.getpid(),
        "ppid": os.getppid(),
        "sid": os.getsid(0),
        "environment": dict(os.environ),
        "stdin_eof": sys.stdin.buffer.read(1) == b"",
        "fixture_fd_inherited": inherited,
        "isolated": bool(sys.flags.isolated),
        "no_site": bool(sys.flags.no_site),
    }
    (folder / (role + ".json")).write_text(json.dumps(result))
    return result


def main():
    role, mode, directory = sys.argv[1:]
    folder = Path(directory)
    observation(folder, role)
    if role == "child":
        if mode in {"deadline", "cancel"}:
            signal.signal(signal.SIGTERM, signal.SIG_IGN)
        (folder / "child-ready").write_text("invented")
        while True:
            (folder / "heartbeat").write_text(str(time.monotonic_ns()))
            time.sleep(0.02)
    child = subprocess.Popen(
        [
            sys.executable,
            "-I",
            "-S",
            "-B",
            str(Path(__file__).resolve()),
            "child",
            mode,
            str(folder),
        ]
    )
    until = time.monotonic() + 3
    while not (folder / "child-ready").exists():
        if child.poll() is not None or time.monotonic() > until:
            raise RuntimeError("Invented child did not become ready")
        time.sleep(0.01)
    (folder / "ready").write_text("invented")
    if mode in {"deadline", "cancel"}:
        while True:
            time.sleep(0.05)
    time.sleep(0.2)
    child.terminate()
    child.wait(timeout=2)
    if mode == "failure":
        raise SystemExit(23)
    (folder / "finished").write_text("invented")


if __name__ == "__main__":
    main()
