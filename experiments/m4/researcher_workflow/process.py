"""Own numerical worker processes until exit, including interrupted orchestration."""

import subprocess
from contextlib import contextmanager

from experiments.m4.causal_secretion import run as causal_run
from experiments.platform_process import close_tree, force_tree, spawn

from .common import ROOT


def command(args, output, log_name, timeout):
    """Preserve the inherited log/exit contract and reap interrupted worker groups."""
    with (output / log_name).open("x") as log:
        process = spawn(
            args, cwd=ROOT, stdout=log, stderr=subprocess.STDOUT, start_new_session=True
        )
        try:
            code = process.wait(timeout=timeout)
            if code:
                raise RuntimeError(f"Causal worker exited {code}; inspect {log_name}")
        except BaseException as exc:
            # The worker and children sharing its session must stop before the
            # parent seals a failure archive. Reap even when wait was interrupted.
            force_tree(process)
            process.wait()
            if isinstance(exc, subprocess.TimeoutExpired):
                raise TimeoutError(f"Causal worker exceeded {timeout} seconds") from exc
            raise
        finally:
            close_tree(process)


@contextmanager
def causal_commands():
    """Use this supervisor only during the serial inherited causal execution.

    Numerical execution and historical source files stay unchanged. Restore
    the original binding even when execution fails, interrupts or is nested.
    """
    previous = causal_run.command
    causal_run.command = command
    try:
        yield
    finally:
        causal_run.command = previous
