"""Own each scientific worker tree using a session or a live Windows Job.

Windows modules are admitted only after Job assignment. Their ordinary child
processes inherit that Job, including predictors that use stdin for JSON data.
"""

import os
import signal
import subprocess

SOURCE_FILES = (
    "experiments/platform_process.py",
    "experiments/gui/windows_process.py",
    "experiments/gui/windows_worker.py",
)
FORCE_SIGNAL = 9


def handled_signals():
    """Cancellation signals supported by the host, without inventing SIGHUP."""
    values = [signal.SIGINT, signal.SIGTERM]
    if os.name != "nt":
        values.append(signal.SIGHUP)
    return tuple(values)


def spawn(args, **kwargs):
    """Start a trusted Python module with authority over its complete child tree."""
    if os.name == "nt":
        from experiments.gui.windows_process import spawn_owned

        process, ownership = spawn_owned(args, **kwargs)
        process._opent1d_ownership = ownership
        return process
    kwargs["start_new_session"] = True
    return subprocess.Popen(args, **kwargs)


def signal_tree(process, signum):
    """Act only on current ownership; persisted PIDs never authorize Windows control."""
    if os.name == "nt":
        process._opent1d_ownership.signal(signum)
    else:
        try:
            os.killpg(process.pid, signum)
        except ProcessLookupError:
            pass


def force_tree(process):
    signal_tree(process, FORCE_SIGNAL)


def tree_exists(process):
    if os.name == "nt":
        return bool(process._opent1d_ownership.observe())
    try:
        os.killpg(process.pid, 0)
        return True
    except ProcessLookupError:
        return False


def close_tree(process):
    """Reap remaining Windows descendants before releasing the live Job handle."""
    if os.name == "nt":
        _forced, remaining = process._opent1d_ownership.cleanup(0)
        if remaining:
            raise RuntimeError("Owned Windows descendants did not terminate")
