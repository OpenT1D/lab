"""Live Windows Job ownership; saved process IDs never grant control authority."""

import ctypes
import os
import signal
import stat
import subprocess
import sys
import time
from ctypes import wintypes

from .windows_worker import CANCEL, START

FORCE_SIGNAL = 9
MAX_OWNED = 512


class BasicLimits(ctypes.Structure):
    _fields_ = [
        ("process_time", ctypes.c_int64),
        ("job_time", ctypes.c_int64),
        ("flags", wintypes.DWORD),
        ("minimum_working_set", ctypes.c_size_t),
        ("maximum_working_set", ctypes.c_size_t),
        ("active_process_limit", wintypes.DWORD),
        ("affinity", ctypes.c_size_t),
        ("priority", wintypes.DWORD),
        ("scheduling", wintypes.DWORD),
    ]


class ExtendedLimits(ctypes.Structure):
    _fields_ = [
        ("basic", BasicLimits),
        ("io_counters", ctypes.c_uint64 * 6),
        ("process_memory", ctypes.c_size_t),
        ("job_memory", ctypes.c_size_t),
        ("peak_process_memory", ctypes.c_size_t),
        ("peak_job_memory", ctypes.c_size_t),
    ]


class ProcessList(ctypes.Structure):
    _fields_ = [
        ("assigned", wintypes.DWORD),
        ("count", wintypes.DWORD),
        ("pids", ctypes.c_size_t * MAX_OWNED),
    ]


class Job:
    """An unnamed, non-inherited kernel object owns all admitted descendants."""

    def __init__(self):
        if os.name != "nt":
            raise ValueError("Windows Job ownership requires Windows")
        self.kernel = ctypes.WinDLL("kernel32", use_last_error=True)
        for name, arguments, result in (
            ("CreateJobObjectW", (ctypes.c_void_p, wintypes.LPCWSTR), wintypes.HANDLE),
            (
                "SetInformationJobObject",
                (wintypes.HANDLE, ctypes.c_int, ctypes.c_void_p, wintypes.DWORD),
                wintypes.BOOL,
            ),
            (
                "QueryInformationJobObject",
                (
                    wintypes.HANDLE,
                    ctypes.c_int,
                    ctypes.c_void_p,
                    wintypes.DWORD,
                    ctypes.c_void_p,
                ),
                wintypes.BOOL,
            ),
            ("AssignProcessToJobObject", (wintypes.HANDLE, wintypes.HANDLE), wintypes.BOOL),
            ("TerminateJobObject", (wintypes.HANDLE, wintypes.UINT), wintypes.BOOL),
            ("CloseHandle", (wintypes.HANDLE,), wintypes.BOOL),
        ):
            function = getattr(self.kernel, name)
            function.argtypes, function.restype = arguments, result
        self.handle = self.kernel.CreateJobObjectW(None, None)
        if not self.handle:
            raise ctypes.WinError(ctypes.get_last_error())
        try:
            limits = ExtendedLimits()
            # KILL_ON_JOB_CLOSE, ACTIVE_PROCESS. Neither breakaway flag is enabled.
            limits.basic.flags = 0x2000 | 0x8
            limits.basic.active_process_limit = MAX_OWNED
            if not self.kernel.SetInformationJobObject(
                self.handle, 9, ctypes.byref(limits), ctypes.sizeof(limits)
            ):
                raise ctypes.WinError(ctypes.get_last_error())
        except BaseException:
            self.close()
            raise

    def assign(self, process):
        # CPython's live Popen owns this handle until its process is reaped. The
        # installer pins CPython; no PID-based OpenProcess lookup is performed.
        if not self.kernel.AssignProcessToJobObject(self.handle, int(process._handle)):
            raise ctypes.WinError(ctypes.get_last_error())

    def pids(self):
        value = ProcessList()
        if not self.kernel.QueryInformationJobObject(
            self.handle, 3, ctypes.byref(value), ctypes.sizeof(value), None
        ):
            raise ctypes.WinError(ctypes.get_last_error())
        if value.count > MAX_OWNED or value.assigned > MAX_OWNED:
            raise ValueError("Owned Windows processes exceed the bounded capacity")
        return list(value.pids[: value.count])

    def terminate(self):
        if self.handle and not self.kernel.TerminateJobObject(self.handle, 1):
            raise ctypes.WinError(ctypes.get_last_error())

    def close(self):
        if self.handle:
            handle, self.handle = self.handle, None
            if not self.kernel.CloseHandle(handle):
                raise ctypes.WinError(ctypes.get_last_error())


class WindowsProcess:
    """Popen facade with pipe cancellation and kernel-owned forced termination."""

    def __init__(self, process, job, *, launch_record=None):
        self.process, self.job = process, job
        self.cancelled = False
        self.launch_record = launch_record

    @property
    def pid(self):
        return self.process.pid

    @property
    def returncode(self):
        return self.process.returncode

    def poll(self):
        return self.process.poll()

    def wait(self, timeout=None):
        return self.process.wait(timeout=timeout)

    def send_signal(self, signum):
        if signum == FORCE_SIGNAL:
            self.kill()
        elif signum in (signal.SIGINT, signal.SIGTERM):
            if not self.cancelled and self.poll() is None:
                self.cancelled = True
                try:
                    self.process.stdin.write(CANCEL)
                    self.process.stdin.flush()
                except (BrokenPipeError, OSError):
                    # A finished child may have closed the private control pipe.
                    if self.poll() is None:
                        raise
        else:
            raise ValueError("Unsupported Windows operation signal")

    def terminate(self):
        self.send_signal(signal.SIGTERM)

    def kill(self):
        self.job.terminate()


class WindowsOwnership:
    def __init__(self, process):
        self.process = process
        self.observed = {}
        self.closed = False

    def observe(self):
        # IDs are receipts only. Every signal/cleanup acts on the live Job handle.
        if self.closed:
            return {}
        live = {
            pid: {"pid": pid, "owner_pid": self.process.pid, "authority": "live-windows-job"}
            for pid in self.process.job.pids()
        }
        self.observed.update(live)
        return live

    def signal(self, signum):
        if not self.closed:
            self.process.send_signal(signum)

    def receipt(self):
        return [self.observed[pid] for pid in sorted(self.observed)]

    def close(self):
        """Also safe on inventory/metadata failures before cleanup was entered."""
        if self.closed:
            return
        self.closed = True
        try:
            self.process.process.stdin.close()
        finally:
            self.process.job.close()

    def cleanup(self, grace):
        try:
            remaining = self.observe()
            if remaining:
                self.process.terminate()
            deadline = time.monotonic() + max(0, grace)
            while remaining and time.monotonic() < deadline:
                time.sleep(0.025)
                remaining = self.observe()
            forced = bool(remaining)
            if forced:
                self.process.kill()
            deadline = time.monotonic() + 2
            while remaining and time.monotonic() < deadline:
                time.sleep(0.025)
                remaining = self.observe()
            if self.process.poll() is not None:
                self.process.wait()
            return forced, list(remaining.values())
        finally:
            self.close()


def _stdlib_argv(argv, index):
    """Avoid the current venv's redirector only for explicit no-site starts.

    CPython uses _base_executable itself when constructing a venv. This is not
    discovery of another interpreter: a foreign or site-enabled request retains
    its exact executable, packages and launch contract.
    """
    if "-S" not in argv[1:index] or not os.path.isabs(argv[0]):
        return argv, "requested"
    # Hardlinked launcher bytes can belong to different venvs. Preserve the
    # requested path context instead of treating file identity as runtime identity.
    if os.path.normcase(os.path.abspath(argv[0])) != os.path.normcase(
        os.path.abspath(sys.executable)
    ):
        return argv, "requested"
    try:
        current = os.path.samefile(argv[0], sys.executable)
    except OSError:
        current = False
    if not current:
        return argv, "requested"
    if sys.implementation.name != "cpython" or sys.version_info[:2] != (3, 12):
        raise ValueError("Current no-site Windows workers require CPython 3.12")
    base = getattr(sys, "_base_executable", None)
    if not isinstance(base, str) or not os.path.isabs(base):
        raise ValueError("Current CPython base executable is unavailable")
    base = os.path.realpath(base, strict=True)
    if not stat.S_ISREG(os.stat(base).st_mode):
        raise ValueError("Current CPython base executable is not a regular file")
    if os.path.samefile(base, sys.executable):
        return argv, "current-cpython-direct"
    prefix = os.path.realpath(sys.base_prefix, strict=True)
    if os.path.normcase(os.path.commonpath((base, prefix))) != os.path.normcase(prefix):
        raise ValueError("Current CPython base executable lies outside its base prefix")
    directory = os.path.dirname(base)
    folders = {directory, os.path.dirname(os.path.realpath(sys.executable))}
    if any(
        os.path.lexists(os.path.join(folder, "pyvenv.cfg"))
        for folder in {directory, os.path.dirname(directory)}
    ) or any(
        name.casefold().endswith("._pth") for folder in folders for name in os.listdir(folder)
    ):
        raise ValueError("Current CPython base has unsupported virtual/path configuration")
    return [base, *argv[1:]], "current-cpython-stdlib-base"


def spawn_owned(args, **kwargs):
    """Assign a gated bootstrap to its Job before allowing the native CLI to run."""
    if os.name != "nt":
        raise ValueError("Windows operation launch requires Windows")
    argv = list(args)
    if "-m" not in argv or argv.index("-m") < 1:
        raise ValueError("Windows operations require a trusted installed Python module")
    index = argv.index("-m")
    if any(flag not in {"-B", "-E", "-s", "-S", "-I"} for flag in argv[1:index]):
        raise ValueError("Unsupported Python operation flags")
    if len(argv) <= index + 1 or not argv[index + 1].startswith("experiments."):
        raise ValueError("Windows operations require an OpenT1D module")
    requested = list(argv)
    argv, selection = _stdlib_argv(argv, index)
    actual = argv[: index + 1] + ["experiments.gui.windows_worker"] + argv[index + 1 :]
    kwargs.pop("start_new_session", None)
    if "stdin" in kwargs or "executable" in kwargs or kwargs.get("shell") or kwargs.get("text"):
        raise ValueError("Windows operation control pipe must remain private and binary")
    kwargs["stdin"] = subprocess.PIPE
    # Pipes and redirected logs need no console. Direct no-site CPython avoids
    # a venv redirector creating a worker before we can assign its parent Job.
    kwargs["creationflags"] = kwargs.get("creationflags", 0) | 0x00000008  # DETACHED_PROCESS
    job, process = Job(), None
    try:
        process = subprocess.Popen(actual, **kwargs)
        job.assign(process)
        owned = WindowsProcess(
            process,
            job,
            launch_record={"requested_argv": requested, "argv": actual, "selection": selection},
        )
        ownership = WindowsOwnership(owned)
        ownership.observe()
        process.stdin.write(START)
        process.stdin.flush()
        return owned, ownership
    except BaseException:
        job.close()
        if process is not None:
            if process.stdin is not None:
                process.stdin.close()
            if process.poll() is None:
                process.kill()
            process.wait(timeout=2)
        raise
