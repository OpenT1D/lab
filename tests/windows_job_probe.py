"""Read-only diagnostics for current Job members; never control a process by PID."""

import ctypes
from ctypes import wintypes
from functools import lru_cache
from pathlib import PureWindowsPath


@lru_cache(maxsize=1)
def kernel():
    library = ctypes.WinDLL("kernel32", use_last_error=True)
    for name, arguments, result in (
        ("OpenProcess", (wintypes.DWORD, wintypes.BOOL, wintypes.DWORD), wintypes.HANDLE),
        ("IsProcessInJob", (wintypes.HANDLE, wintypes.HANDLE, ctypes.c_void_p), wintypes.BOOL),
        ("GetExitCodeProcess", (wintypes.HANDLE, ctypes.c_void_p), wintypes.BOOL),
        (
            "QueryFullProcessImageNameW",
            (wintypes.HANDLE, wintypes.DWORD, wintypes.LPWSTR, ctypes.c_void_p),
            wintypes.BOOL,
        ),
        ("WaitForSingleObject", (wintypes.HANDLE, wintypes.DWORD), wintypes.DWORD),
        ("CloseHandle", (wintypes.HANDLE,), wintypes.BOOL),
    ):
        function = getattr(library, name)
        function.argtypes, function.restype = arguments, result
    return library


def inspect_job_processes(process, pids):
    """Call only with IDs just returned by this retained process's live Job."""
    if len(pids) > 512:
        raise ValueError("Windows test probe exceeds current Job capacity")
    api = kernel()
    row = {
        "leader_pid": process.pid,
        "leader_returncode": process.poll(),
        "leader_handle_wait": api.WaitForSingleObject(int(process.process._handle), 0),
        "associated": list(pids),
        "processes": [],
    }
    for pid in pids:
        # SYNCHRONIZE | QUERY_LIMITED_INFORMATION; no process-control access.
        handle = api.OpenProcess(0x00100000 | 0x1000, False, pid)
        item = {"pid": pid, "leader": pid == process.pid}
        row["processes"].append(item)
        if not handle:
            item["open_error"] = ctypes.get_last_error()
            continue
        try:
            member, code = wintypes.BOOL(), wintypes.DWORD()
            if not api.IsProcessInJob(handle, process.job.handle, ctypes.byref(member)):
                raise ctypes.WinError(ctypes.get_last_error())
            if not api.GetExitCodeProcess(handle, ctypes.byref(code)):
                raise ctypes.WinError(ctypes.get_last_error())
            item.update(
                in_job=bool(member.value),
                exit_code=code.value,
                wait_result=api.WaitForSingleObject(handle, 0),
            )
            image = ctypes.create_unicode_buffer(32768)
            size = wintypes.DWORD(len(image))
            if api.QueryFullProcessImageNameW(handle, 0, image, ctypes.byref(size)):
                item["image_basename"] = PureWindowsPath(image.value).name
            else:
                item["image_error"] = ctypes.get_last_error()
        finally:
            if not api.CloseHandle(handle):
                raise ctypes.WinError(ctypes.get_last_error())
    return row
