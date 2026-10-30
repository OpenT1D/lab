"""Supervise the isolated installed service process, retaining live ancestry."""

import hashlib
import json
import os
import signal
import subprocess
import sys
import tempfile
import threading
import time
import types
from pathlib import Path

from ._integrity import regular_bytes, verify


def force_live_process(process, owner):
    """Best effort on live ownership, with the direct new session as backstop."""
    try:
        if owner is not None:
            try:
                owner.signal(signal.SIGKILL)
            except (OSError, ValueError):
                for pid, observed in tuple(owner.observed.items()):
                    try:
                        actual = owner.table.one(pid)
                        if actual and actual["alive"] and actual["start"] == observed["start"]:
                            os.kill(pid, signal.SIGKILL)
                    except (OSError, ValueError):
                        continue
    finally:
        # A reaped leader's numeric PGID is no longer fallback authority.
        # Observed descendants above retain only their checked start identities.
        if process.poll() is None:
            try:
                os.killpg(process.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass


def invoke(request, *, cancel=None):
    if (
        os.name != "posix"
        or sys.implementation.name != "cpython"
        or sys.version_info[:2] != (3, 12)
    ):
        raise ValueError("Installed SDK requires POSIX CPython 3.12")
    package = Path(__file__).absolute().parent
    metadata = verify(package)
    ownership_source = package / "_payload/app/experiments/gui/ownership.py"
    module = types.ModuleType("_opent1d_sdk_owned_process")
    raw = regular_bytes(ownership_source)
    if (
        hashlib.sha256(raw).hexdigest()
        != metadata["files"][ownership_source.relative_to(package).as_posix()]["sha256"]
    ):
        raise ValueError("Installed ownership source changed before use")
    exec(compile(raw, str(ownership_source), "exec"), module.__dict__)
    cancelled = cancel or threading.Event()
    previous = {}
    process = owner = None
    stopped = None
    remaining = None

    def stop(_number, _frame):
        cancelled.set()

    environment = {
        key: value
        for key, value in os.environ.items()
        if not key.startswith(("PYTHON", "UV_"))
        and key not in {"VIRTUAL_ENV", "__PYVENV_LAUNCHER__"}
    }
    environment.update(PYTHONDONTWRITEBYTECODE="1", PYTHONNOUSERSITE="1")
    with tempfile.TemporaryDirectory(prefix="opent1d-sdk-call-") as temporary:
        output = Path(temporary) / "response.json"
        errors = Path(temporary) / "stderr.log"
        try:
            if threading.current_thread() is threading.main_thread():
                for number in (signal.SIGINT, signal.SIGTERM, signal.SIGHUP):
                    previous[number] = signal.signal(number, stop)
            with output.open("xb") as stdout, errors.open("xb") as stderr:
                process = subprocess.Popen(
                    [sys.executable, "-I", "-B", "-S", str(package / "_bootstrap.py")],
                    cwd=package,
                    env=environment,
                    stdin=subprocess.PIPE,
                    stdout=stdout,
                    stderr=stderr,
                    start_new_session=True,
                )
                owner = module.Ownership(process)
                try:
                    process.stdin.write(json.dumps(request, allow_nan=False).encode())
                    process.stdin.close()
                    while process.poll() is None:
                        owner.observe()
                        if cancelled.is_set() and stopped is None:
                            process.terminate()
                            stopped = time.monotonic()
                        if stopped is not None and time.monotonic() - stopped > 40:
                            owner.signal(signal.SIGKILL)
                        time.sleep(0.02)
                    process.wait()
                finally:
                    try:
                        _, remaining = owner.cleanup(
                            0 if stopped is None else max(0, stopped + 40 - time.monotonic())
                        )
                    except (OSError, ValueError):
                        owner.signal(signal.SIGKILL)
                        raise
        finally:
            try:
                if process is not None:
                    # This live Popen owns its newly created session even if
                    # metadata construction failed before an Ownership exists.
                    try:
                        if owner is None or remaining != []:
                            force_live_process(process, owner)
                    finally:
                        try:
                            if process.stdin is not None and not process.stdin.closed:
                                try:
                                    process.stdin.close()
                                except OSError:
                                    pass
                            if process.poll() is None:
                                process.kill()
                        finally:
                            process.wait(timeout=2)
            finally:
                for number, handler in previous.items():
                    signal.signal(number, handler)
        if remaining != []:
            raise RuntimeError("Installed service process cleanup remains unresolved")
        if output.stat().st_size > 8 * 1024 * 1024:
            raise ValueError("Installed response exceeds byte limit")
        try:
            result = json.loads(output.read_bytes())
        except (ValueError, OSError) as error:
            raise RuntimeError(
                "Installed service returned no valid response; inspect the retained project"
            ) from error
        if process.returncode != 0 or result.get("ok") is not True:
            raise ValueError(
                result.get("error", "Installed service failed; project evidence is retained")
            )
        return result["result"]
