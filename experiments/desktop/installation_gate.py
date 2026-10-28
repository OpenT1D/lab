"""Coordinate Windows launcher admission with installation and uninstallation."""

import ctypes
import os

NAME = "Local\\OpenT1D-Installation"


class InstallationGate:
    """Acquire on construction; release on the creating thread after admission.

    The installer holds the same mutex across maintenance and file replacement.
    Its --stop child must not acquire this gate. POSIX developer launches do not
    use the Windows installer and need no equivalent gate.
    """

    def __init__(self, timeout_ms=10000):
        if type(timeout_ms) is not int or not 0 <= timeout_ms <= 10000:
            raise ValueError("Installation wait must be between 0 and 10000 milliseconds")
        self.handle = None
        self.acquired = False
        if os.name != "nt":
            return
        from ctypes import wintypes

        self.kernel = ctypes.WinDLL("kernel32", use_last_error=True)
        for name, arguments, result in (
            ("CreateMutexW", (ctypes.c_void_p, wintypes.BOOL, wintypes.LPCWSTR), wintypes.HANDLE),
            ("WaitForSingleObject", (wintypes.HANDLE, wintypes.DWORD), wintypes.DWORD),
            ("ReleaseMutex", (wintypes.HANDLE,), wintypes.BOOL),
            ("CloseHandle", (wintypes.HANDLE,), wintypes.BOOL),
        ):
            function = getattr(self.kernel, name)
            function.argtypes, function.restype = arguments, result
        self.handle = self.kernel.CreateMutexW(None, False, NAME)
        if not self.handle:
            raise ctypes.WinError(ctypes.get_last_error())
        try:
            result = self.kernel.WaitForSingleObject(self.handle, timeout_ms)
            if result in (0, 0x80):  # WAIT_OBJECT_0 / WAIT_ABANDONED: caller now owns it.
                self.acquired = True
            elif result == 258:  # WAIT_TIMEOUT
                raise ValueError(
                    "Another OpenT1D installation or launch is in progress; try again shortly"
                )
            elif result == 0xFFFFFFFF:  # WAIT_FAILED
                raise ctypes.WinError(ctypes.get_last_error())
            else:
                raise OSError("Windows returned an unsupported installation-lock state")
        except BaseException:
            self.close()
            raise

    def close(self):
        if self.handle is None:
            return
        handle, self.handle = self.handle, None
        acquired, self.acquired = self.acquired, False
        try:
            if acquired and not self.kernel.ReleaseMutex(handle):
                raise ctypes.WinError(ctypes.get_last_error())
        finally:
            if not self.kernel.CloseHandle(handle):
                raise ctypes.WinError(ctypes.get_last_error())

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        self.close()
