"""Observe native calls and retain completed steps without changing their results."""

import contextlib
import json
import math
import os
import shutil
import signal
import time
import traceback


def atomic_text(path, text):
    if os.name == "nt":
        from experiments.platform_files import atomic_write_text

        atomic_write_text(path, text)
        return
    temporary = path.with_name(path.name + ".tmp")
    temporary.write_text(text)
    temporary.replace(path)


def write_json(path, value):
    atomic_text(path, json.dumps(value, indent=2, allow_nan=False) + "\n")


class RunInterrupted(BaseException):
    """Do not let upstream exception handlers swallow cancellation or timeout."""


@contextlib.contextmanager
def interruption(timeout_seconds, *, arm_timer=True):
    """Handle cancellation; let subprocess.wait own worker deadlines without an alarm."""
    if not math.isfinite(timeout_seconds) or timeout_seconds <= 0:
        raise ValueError("timeout_seconds must be finite and positive")
    if os.name == "nt" and arm_timer:
        raise ValueError("Windows in-process execution requires an owning worker deadline")
    if os.name != "nt" and signal.getitimer(signal.ITIMER_REAL) != (0.0, 0.0):
        raise RuntimeError("An existing real-time alarm must not be replaced")

    def stop(signum, _frame):
        reason = (
            "timeout"
            if os.name != "nt" and signum == signal.SIGALRM
            else signal.Signals(signum).name
        )
        raise RunInterrupted(reason)

    signals = [signal.SIGTERM, signal.SIGINT]
    if os.name != "nt":
        signals.append(signal.SIGALRM)
    previous = {s: signal.getsignal(s) for s in signals}
    try:
        for s in signals:
            signal.signal(s, stop)
        if arm_timer:
            signal.setitimer(signal.ITIMER_REAL, timeout_seconds)
        yield
    finally:
        if arm_timer:
            signal.setitimer(signal.ITIMER_REAL, 0)
        for s, handler in previous.items():
            signal.signal(s, handler)


def failure_status(error):
    return "interrupted" if isinstance(error, (RunInterrupted, KeyboardInterrupt)) else "failed"


def record_native(obj):
    """Wrap reset/step for checkpoints; the native SimObj still owns execution."""
    from pathlib import Path

    from simglucose.simulation.sim_engine import sim

    output = Path(obj.path)
    output.mkdir(parents=True, exist_ok=False)
    manifest = {"status": "started", "profile": obj.env.patient.name, "completed_rows": 0}
    write_json(output / "recording.json", manifest)
    reset, step = obj.env.reset, obj.env.step
    started = time.monotonic()

    def checkpoint():
        frame = obj.results()
        atomic_text(output / "progress.csv", frame.to_csv())
        manifest["completed_rows"] = len(frame)
        write_json(output / "recording.json", manifest)

    def observed_reset(*args, **kwargs):
        value = reset(*args, **kwargs)
        checkpoint()
        return value

    def observed_step(*args, **kwargs):
        value = step(*args, **kwargs)
        checkpoint()
        return value

    obj.env.reset, obj.env.step = observed_reset, observed_step
    try:
        result = sim(obj)
        manifest["status"] = "completed"
        return result
    except BaseException as error:
        manifest.update(status=failure_status(error), error=f"{type(error).__name__}: {error}")
        atomic_text(output / "failure.log", traceback.format_exc())
        # Only the last fully completed interval is attributable to this attempt.
        if (output / "progress.csv").exists():
            shutil.copyfile(output / "progress.csv", output / "partial.csv")
        raise
    finally:
        obj.env.reset, obj.env.step = reset, step
        manifest["elapsed_seconds"] = time.monotonic() - started
        write_json(output / "recording.json", manifest)
