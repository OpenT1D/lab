"""Bounded outer supervision lets native owners finish their shorter cleanup."""

import json
import os
import signal
import subprocess
import time

from experiments.m4.comparison.run import worker_environment

from .common import ROOT

OUTER_GRACE_SECONDS = 20


def group_exists(pid):
    try:
        os.killpg(pid, 0)
        return True
    except ProcessLookupError:
        return False


class Control:
    def __init__(self):
        self.signal = None
        self.cancelled_at = None
        self.active = None

    def stop(self, signum, _frame=None):
        if self.signal is None:
            self.signal, self.cancelled_at = int(signum), time.monotonic()
        self.send(signum)

    def send(self, signum):
        # A leader may exit before a same-group descendant; its exit does not
        # relinquish our ownership of the process group.
        if self.active is not None:
            try:
                os.killpg(self.active.pid, signum)
            except ProcessLookupError:
                pass


def supervise(args, log_path, timeout, control, *, grace_seconds=OUTER_GRACE_SECONDS):
    """Keep the native budget; allow 20s cleanup beyond its inner 10s grace."""
    deadline = time.monotonic() + timeout
    expired_at = None
    code, error = None, None
    with log_path.open("x") as log:
        log.write(json.dumps({"argv": args, "timeout_seconds": timeout}, sort_keys=True) + "\n")
        log.flush()
        control.active = subprocess.Popen(
            args,
            cwd=ROOT,
            stdout=log,
            stderr=subprocess.STDOUT,
            start_new_session=True,
            env=worker_environment(),
        )
        try:
            if control.signal is not None:
                control.send(control.signal)
            while control.active.poll() is None:
                now = time.monotonic()
                if control.signal is None and expired_at is None and now >= deadline:
                    expired_at, error = now, "WorkerDeadline"
                    control.send(signal.SIGTERM)
                stopped_at = control.cancelled_at if control.signal is not None else expired_at
                if stopped_at is not None and now - stopped_at >= grace_seconds:
                    control.send(signal.SIGKILL)
                time.sleep(0.02)
            code = control.active.wait()
            if control.signal is not None:
                error = "GlobalInterruption"
            elif code and error is None:
                error = "WorkerExit"
        finally:
            process = control.active
            if group_exists(process.pid):
                if error is None:
                    error = "UnreapedWorkerGroup"
                control.send(signal.SIGTERM)
                stopped_at = (
                    control.cancelled_at
                    if control.signal is not None
                    else expired_at
                    if expired_at is not None
                    else time.monotonic()
                )
                while group_exists(process.pid) and time.monotonic() - stopped_at < grace_seconds:
                    process.poll()
                    time.sleep(0.02)
                if group_exists(process.pid):
                    control.send(signal.SIGKILL)
            process.wait()
            control.active = None
    return code, error
