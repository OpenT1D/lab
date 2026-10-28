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
            "GetProcessTimes",
            (wintypes.HANDLE,) + (ctypes.c_void_p,) * 4,
            wintypes.BOOL,
        ),
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


def inspect_job_processes(process, pids, *, image_cache=None):
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
            creation, exited, system, user = (wintypes.FILETIME() for _ in range(4))
            if api.GetProcessTimes(
                handle,
                ctypes.byref(creation),
                ctypes.byref(exited),
                ctypes.byref(system),
                ctypes.byref(user),
            ):
                item["creation_time"] = creation.dwLowDateTime | creation.dwHighDateTime << 32
            else:
                item["creation_error"] = ctypes.get_last_error()
            image = ctypes.create_unicode_buffer(32768)
            size = wintypes.DWORD(len(image))
            if api.QueryFullProcessImageNameW(handle, 0, image, ctypes.byref(size)):
                item["image_basename"] = PureWindowsPath(image.value).name
            else:
                item["image_error"] = ctypes.get_last_error()
            if image_cache is not None and member.value and "creation_time" in item:
                previous = image_cache.get(pid)
                if previous is not None and previous[0] == item["creation_time"]:
                    item["earlier_running_image_basename"] = previous[1]
                if (
                    row["leader_returncode"] is None
                    and item["wait_result"] == 258
                    and "image_basename" in item
                    and (pid in image_cache or len(image_cache) < 512)
                ):
                    # Values only: never retain a query handle or a process object.
                    image_cache[pid] = (item["creation_time"], item["image_basename"])
        finally:
            if not api.CloseHandle(handle):
                raise ctypes.WinError(ctypes.get_last_error())
    return row
