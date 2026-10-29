"""Absolute isolated worker entrypoint, selected by the installed facade only."""

import hashlib
import json
import os
import runpy
import signal
import stat
import sys
import threading
from pathlib import Path


def read_bootstrap_file(path, limit):
    if any(parent.is_symlink() for parent in (path, *path.parents)):
        raise ValueError("Linked installed bootstrap input refused")
    if not stat.S_ISREG(path.stat(follow_symlinks=False).st_mode):
        raise ValueError("Nonregular installed bootstrap input refused")
    descriptor = os.open(path, os.O_RDONLY | os.O_NONBLOCK | getattr(os, "O_NOFOLLOW", 0))
    try:
        before = os.fstat(descriptor)
        if not stat.S_ISREG(before.st_mode) or before.st_nlink != 1 or before.st_size > limit:
            raise ValueError("Bootstrap input exceeds regular-file boundary")
        with os.fdopen(descriptor, "rb", closefd=False) as stream:
            raw = stream.read(limit + 1)
        after = os.fstat(descriptor)
        if (
            before.st_dev,
            before.st_ino,
            before.st_size,
            before.st_mtime_ns,
            before.st_ctime_ns,
        ) != (
            after.st_dev,
            after.st_ino,
            after.st_size,
            after.st_mtime_ns,
            after.st_ctime_ns,
        ) or len(raw) > limit:
            raise ValueError("Bootstrap input changed while reading")
        return raw
    finally:
        os.close(descriptor)


def main():
    if (
        os.name != "posix"
        or sys.implementation.name != "cpython"
        or sys.version_info[:2] != (3, 12)
    ):
        raise ValueError("This internal SDK requires POSIX CPython 3.12")
    package = Path(__file__).absolute().parent
    # Verify the validator's exact regular source bytes before executing it.
    manifest = json.loads(read_bootstrap_file(package / "_manifest.json", 4 * 1024 * 1024))
    validator = package / "_integrity.py"
    raw = read_bootstrap_file(validator, 1024 * 1024)
    if manifest["files"].get("_integrity.py") != {
        "sha256": hashlib.sha256(raw).hexdigest(),
        "bytes": len(raw),
    }:
        raise ValueError("Installed validator changed")
    namespace = {"__file__": str(validator), "__name__": "_opent1d_sdk_integrity"}
    exec(compile(raw, str(validator), "exec"), namespace)
    checked = namespace["verify"](package)
    payload = package / "_payload/app"
    sys.path.insert(0, str(payload))
    os.chdir(payload)
    if len(sys.argv) > 1 and sys.argv[1] == "--native":
        if len(sys.argv) < 4:
            raise ValueError("Native worker selection missing")
        task, operation = sys.argv[2:4]
        modules = {
            "mmtt-sensitivity": "experiments.observation_analysis",
            "m4-study-secure": "experiments.m4.secure_study",
            "m4-study-installed": "experiments.m4.installed_study",
        }
        if (
            task not in modules
            or task not in checked["tasks"]
            or operation not in {"run", "reconstruct"}
            or (task == "m4-study-secure" and operation == "run")
        ):
            raise ValueError("Native execution is not an admitted installed capability")
        sys.argv = [modules[task], operation, *sys.argv[4:]]
        runpy.run_module(modules[task], run_name="__main__")
        return
    from experiments.shared_services.installed import dispatch

    request = json.loads(sys.stdin.buffer.read(4 * 1024 * 1024 + 1))
    cancel, previous = threading.Event(), {}

    def stop(_number, _frame):
        cancel.set()

    try:
        if isinstance(request, dict) and request.get("action") == "run":
            # Keep ledger publication and terminal sealing intact when a
            # request is cancelled before/after the inner worker supervisor.
            for number in (signal.SIGINT, signal.SIGTERM, signal.SIGHUP):
                previous[number] = signal.signal(number, stop)
        response = dispatch(request, Path(__file__).absolute(), checked, cancel=cancel)
        print(json.dumps({"ok": True, "result": response}, sort_keys=True, allow_nan=False))
    finally:
        for number, handler in previous.items():
            signal.signal(number, handler)


if __name__ == "__main__":
    try:
        main()
    except (ValueError, OSError, KeyError, TypeError) as error:
        print(json.dumps({"ok": False, "error": type(error).__name__ + ": " + str(error)[:1000]}))
        raise SystemExit(2)
