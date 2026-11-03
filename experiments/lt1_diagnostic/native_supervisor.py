"""Task-local launch controls using the unchanged canonical supervisor code.

No global patch, source rewrite, alternate ownership loop or caller command
registration. Only trusted in-process task code supplies before_spawn/spawn.
Canonical shared source and historical reader identities stay unchanged.
"""

import inspect
import math
import os
import stat
import subprocess
import threading
import types
from pathlib import Path

from experiments.lt1_diagnostic.control_identity import ROOT
from experiments.shared_services import execution as canonical

ENVIRONMENT = {"LANG": "C", "LC_ALL": "C", "PATH": "/usr/bin:/bin"}
LEGACY_ARGUMENTS = ("argv", "log_path", "timeout", "cancel", "grace", "header", "environment")


class _NotStartedCancel(ValueError):
    """Private typed signal caught by canonical ValueError handling."""


CANCEL_MESSAGE = "controlled cancellation before process spawn"


def need(ok, reason):
    if not ok:
        raise ValueError("LT1 supervisor view refused: " + reason)


def _supervisor_view(spawn):
    """Same canonical code/defaults/closure, with one per-call global binding.

    The callable is a trusted local closure, never supplied by packet metadata.
    The copied globals are a separate dictionary; module globals are untouched.
    """
    base = canonical.supervise
    filename = str(ROOT / "experiments/shared_services/execution.py")
    need(isinstance(base, types.FunctionType) and callable(spawn), "trusted Python functions")
    need(
        canonical.__name__ == "experiments.shared_services.execution"
        and str(Path(canonical.__file__)) == filename
        and base.__module__ == canonical.__name__
        and base.__name__ == base.__qualname__ == "supervise"
        and base.__globals__ is canonical.__dict__
        and base.__code__.co_filename == filename,
        "canonical module/globals/code provenance",
    )
    code = base.__code__
    need(
        code.co_argcount == 2
        and code.co_posonlyargcount == 0
        and code.co_kwonlyargcount == 5
        and code.co_varnames[:7] == LEGACY_ARGUMENTS
        and not code.co_flags & (inspect.CO_VARARGS | inspect.CO_VARKEYWORDS),
        "restored legacy supervisor signature",
    )
    original = dict(base.__globals__)
    namespace = dict(original)
    namespace["spawn"] = spawn
    need(
        namespace.keys() == original.keys()
        and all(namespace[k] is original[k] for k in original if k != "spawn"),
        "only spawn may differ",
    )
    view = types.FunctionType(code, namespace, base.__name__, base.__defaults__, base.__closure__)
    view.__kwdefaults__ = None if base.__kwdefaults__ is None else dict(base.__kwdefaults__)
    view.__annotations__ = dict(base.__annotations__)
    view.__dict__.update(base.__dict__)
    view.__module__, view.__qualname__, view.__doc__ = (
        base.__module__,
        base.__qualname__,
        base.__doc__,
    )
    return view


def _log_token(log, path, *, private):
    opened = os.fstat(log.fileno())
    named = os.stat(path, follow_symlinks=False)
    need(
        stat.S_ISREG(opened.st_mode)
        and stat.S_ISREG(named.st_mode)
        and opened.st_nlink == named.st_nlink == 1
        and opened.st_uid == named.st_uid == os.getuid()
        and (opened.st_dev, opened.st_ino) == (named.st_dev, named.st_ino),
        "opened log binding",
    )
    if private:
        need(
            stat.S_IMODE(opened.st_mode) == stat.S_IMODE(named.st_mode) == 0o600, "private log mode"
        )
    return opened.st_dev, opened.st_ino


def _not_started(argv):
    return {
        "argv": list(argv),
        "status": "interrupted",
        "exit_code": None,
        "error": "Cancelled",
        "cleanup_forced": False,
        "owned_processes": [],
        "remaining_owned_processes": [],
        "received_signals": [],
    }


def supervise(
    argv,
    log_path,
    *,
    timeout,
    cancel=None,
    grace=30,
    header=None,
    environment=None,
    stdin=None,
    before_spawn=None,
):
    """LT1 facade: existing lifecycle with fixed guarded spawn controls.

    A completely ordinary call delegates directly and leaves canonical defaults
    intact. Hooked LT1 calls accept only DEVNULL and the exact clean environment.
    Cancellation classification uses private control flow, never error wording
    alone. Existing signal observations and ordinary failures are preserved.
    """
    if before_spawn is None and stdin is None:
        return canonical.supervise(
            argv,
            log_path,
            timeout=timeout,
            cancel=cancel,
            grace=grace,
            header=header,
            environment=environment,
        )
    need(callable(before_spawn), "trusted last guard required")
    need(stdin == subprocess.DEVNULL, "fixed DEVNULL required")
    expected_environment = dict(ENVIRONMENT)
    need(
        isinstance(environment, dict) and environment == expected_environment,
        "exact clean environment required",
    )
    need(
        isinstance(argv, (list, tuple))
        and len(argv) > 0
        and all(isinstance(item, str) for item in argv),
        "fixed string argv",
    )
    need(
        type(timeout) in (int, float) and math.isfinite(timeout) and timeout > 0,
        "finite positive deadline",
    )
    need(
        type(grace) in (int, float) and math.isfinite(grace) and grace >= 0,
        "finite nonnegative grace",
    )
    expected_argv = tuple(argv)
    stopped = cancel if cancel is not None else threading.Event()
    need(callable(getattr(stopped, "is_set", None)), "cancellation observation")
    if stopped.is_set():
        return _not_started(expected_argv)

    original_spawn = canonical.spawn
    expected_root = canonical.ROOT
    cancelled_before_spawn, spawn_entered = False, False

    def check_cancelled():
        nonlocal cancelled_before_spawn
        if stopped.is_set():
            cancelled_before_spawn = True
            raise _NotStartedCancel(CANCEL_MESSAGE)

    def controlled_spawn(actual_argv, **kwargs):
        nonlocal spawn_entered
        need(set(kwargs) == {"cwd", "env", "stdout", "stderr"}, "legacy spawn fields")
        need(
            tuple(actual_argv) == expected_argv
            and kwargs["cwd"] == expected_root
            and kwargs["env"] == expected_environment
            and kwargs["stderr"] == subprocess.STDOUT,
            "actual argv/cwd/environment",
        )
        log = kwargs["stdout"]
        token = _log_token(log, log_path, private=False)
        check_cancelled()
        # The existing launch._run guard first sets this log to 0600, then binds
        # owner/source/staging state. Its ordinary ValueError/OSError must win.
        before_spawn(log)
        need(_log_token(log, log_path, private=True) == token, "last log descriptor changed")
        need(
            tuple(actual_argv) == expected_argv
            and kwargs["cwd"] == expected_root
            and kwargs["env"] == expected_environment
            and kwargs["stdout"] is log
            and kwargs["stderr"] == subprocess.STDOUT,
            "late actual spawn fields",
        )
        check_cancelled()
        kwargs["stdin"] = subprocess.DEVNULL
        kwargs["close_fds"] = True
        spawn_entered = True
        return original_spawn(list(expected_argv), **kwargs)

    view = _supervisor_view(controlled_spawn)
    need(view.__globals__["ROOT"] == expected_root, "supervisor root changed")
    result = view(
        list(expected_argv),
        log_path,
        timeout=timeout,
        cancel=stopped,
        grace=grace,
        header=header,
        environment=dict(expected_environment),
    )
    if cancelled_before_spawn:
        need(
            not spawn_entered
            and result.get("exit_code") is None
            and result.get("owned_processes") == []
            and result.get("remaining_owned_processes") == []
            and not result.get("cleanup_error")
            and not result.get("signal_error")
            and result.get("error") == f"{_NotStartedCancel.__name__}: {CANCEL_MESSAGE}"
            and isinstance(result.get("received_signals"), list),
            "cancelled-before-spawn receipt inconsistent",
        )
        result = {**result, "status": "interrupted", "error": "Cancelled"}
    return result
