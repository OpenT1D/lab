"""Private pipe gate and cooperative interrupt for a trusted installed CLI module."""

import _thread
import os
import runpy
import signal
import sys
import threading
import time

START = b"OPENT1D_START\n"
CANCEL = b"OPENT1D_CANCEL\n"


def _windows_pipe_available(descriptor):
    import ctypes
    import msvcrt
    from ctypes import wintypes

    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    peek = kernel.PeekNamedPipe
    peek.argtypes = (
        wintypes.HANDLE,
        ctypes.c_void_p,
        wintypes.DWORD,
        ctypes.c_void_p,
        ctypes.POINTER(wintypes.DWORD),
        ctypes.c_void_p,
    )
    peek.restype = wintypes.BOOL
    handle = msvcrt.get_osfhandle(descriptor)

    def available():
        count = wintypes.DWORD()
        if not peek(handle, None, 0, None, ctypes.byref(count), None):
            error = ctypes.get_last_error()
            if error == 109:  # Writer closed: the existing EOF cancellation rule.
                return None
            raise ctypes.WinError(error)
        return count.value

    return available


def read_command(descriptor, available=None):
    # Raw descriptor reads avoid a daemon holding sys.stdin's buffered-I/O lock
    # while Python finalizes after a normally completed command.
    data = bytearray()
    while len(data) < 64:
        if available is not None:
            count = available()
            if count is None:
                return bytes(data)
            if count == 0:
                time.sleep(0.02)
                continue
        part = os.read(descriptor, 1)
        if not part:
            return bytes(data)
        data.extend(part)
        if part == b"\n":
            return bytes(data)
    return bytes(data)


def main():
    if len(sys.argv) < 2 or not sys.argv[1].startswith("experiments."):
        raise ValueError("A trusted OpenT1D module is required")
    control = sys.stdin.fileno()
    # A pending synchronous stdin read can block CRT fstat during NumPy's
    # DLL initialization (numpy/numpy#24290). There is only one pipe consumer:
    # the gate finishes before its watcher starts. Bind the API before watching,
    # and read only available bytes; PeekNamedPipe itself is not universally
    # nonblocking when another thread has outstanding synchronous pipe I/O.
    available = _windows_pipe_available(control) if os.name == "nt" else None
    # The parent assigns this process to its kill-on-close Job before this gate.
    # EOF before admission cannot start scientific work.
    if read_command(control, available) != START:
        return 2

    def watch():
        # EOF means the manager disappeared; its Job handle also closes on exit.
        try:
            command = read_command(control, available)
        except Exception:
            # A broken control channel cannot silently leave work uncancellable.
            _thread.interrupt_main(signal.SIGINT)
            raise
        if command in (CANCEL, b""):
            _thread.interrupt_main(signal.SIGINT)

    threading.Thread(target=watch, daemon=True, name="opent1d-control").start()
    module = sys.argv[1]
    sys.argv = sys.argv[1:]
    runpy.run_module(module, run_name="__main__", alter_sys=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
