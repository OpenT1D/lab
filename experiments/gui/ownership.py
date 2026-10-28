"""Bounded live process ancestry with OS start identities on macOS and Linux."""

import ctypes
import os
import signal
import sys
import time
from pathlib import Path

MAX_PROCESSES = 32768
MAX_OWNED = 512


class BSDInfo(ctypes.Structure):
    # Darwin SDK sys/proc_info.h: proc_bsdinfo, PROC_PIDTBSDINFO=3; MAXCOMLEN=16.
    _fields_ = [
        (name, ctypes.c_uint32)
        for name in (
            "flags",
            "status",
            "xstatus",
            "pid",
            "ppid",
            "uid",
            "gid",
            "ruid",
            "rgid",
            "svuid",
            "svgid",
            "reserved",
        )
    ] + [
        ("comm", ctypes.c_char * 16),
        ("name", ctypes.c_char * 32),
        ("nfiles", ctypes.c_uint32),
        ("pgid", ctypes.c_uint32),
        ("jobc", ctypes.c_uint32),
        ("tdev", ctypes.c_uint32),
        ("tpgid", ctypes.c_uint32),
        ("nice", ctypes.c_int32),
        ("start_sec", ctypes.c_uint64),
        ("start_usec", ctypes.c_uint64),
    ]


class ProcessTable:
    def __init__(self):
        if sys.platform == "darwin":
            self.lib = ctypes.CDLL("/usr/lib/libproc.dylib", use_errno=True)
            self.lib.proc_listallpids.argtypes = (ctypes.c_void_p, ctypes.c_int)
            self.lib.proc_listallpids.restype = ctypes.c_int
            self.lib.proc_pidinfo.argtypes = (
                ctypes.c_int,
                ctypes.c_int,
                ctypes.c_uint64,
                ctypes.c_void_p,
                ctypes.c_int,
            )
            self.lib.proc_pidinfo.restype = ctypes.c_int
        elif not sys.platform.startswith("linux"):
            raise ValueError("Owned local operations require macOS or Linux")

    def one(self, pid):
        if sys.platform == "darwin":
            value = BSDInfo()
            if self.lib.proc_pidinfo(
                pid, 3, 0, ctypes.byref(value), ctypes.sizeof(value)
            ) != ctypes.sizeof(value):
                return None
            if value.uid != os.getuid() or value.pid != pid:
                return None
            return {
                "pid": pid,
                "ppid": value.ppid,
                "pgid": value.pgid,
                "start": f"darwin:{value.start_sec}:{value.start_usec}",
                "alive": value.status != 5,  # Darwin sys/proc.h: SZOMB.
            }
        try:
            path = Path("/proc") / str(pid) / "stat"
            if path.stat().st_uid != os.getuid():
                return None
            with path.open("rb") as stream:
                raw = stream.read(8193)
            if len(raw) > 8192:
                raise ValueError("Process metadata exceeds its byte limit")
            fields = raw[raw.rfind(b")") + 2 :].split()
            return {
                "pid": pid,
                "ppid": int(fields[1]),
                "pgid": int(fields[2]),
                "start": "linux:" + fields[19].decode("ascii"),
                "alive": fields[0] != b"Z",
            }
        except (OSError, IndexError):
            return None

    def snapshot(self):
        if sys.platform == "darwin":
            buffer = (ctypes.c_int * MAX_PROCESSES)()
            count = self.lib.proc_listallpids(buffer, ctypes.sizeof(buffer))
            if count < 0 or count >= MAX_PROCESSES:
                raise ValueError("Process inventory unavailable or exceeds its bounded capacity")
            pids = list(buffer[:count])
        else:
            pids = []
            with os.scandir("/proc") as entries:
                for entry in entries:
                    if entry.name.isdigit():
                        pids.append(int(entry.name))
                        if len(pids) >= MAX_PROCESSES:
                            raise ValueError("Process inventory exceeds its bounded capacity")
        return {pid: value for pid in pids if pid > 0 and (value := self.one(pid)) is not None}


class Ownership:
    """Authority comes from this live Popen, never from a saved job journal."""

    def __init__(self, process, table=None):
        self.process = process
        self.table = table or ProcessTable()
        self.observed = {}
        self.groups = set()
        root = self.table.one(process.pid)
        if root is not None:
            if root["ppid"] != os.getpid() or root["pgid"] != process.pid:
                raise ValueError("Live entry owner does not belong to its new session")
            self.observed[process.pid] = root
            self.groups.add(root["pgid"])
        elif process.poll() is None:
            raise ValueError("Live entry start identity unavailable")

    def observe(self):
        snapshot = self.table.snapshot()
        live = {
            pid: value
            for pid, value in snapshot.items()
            if pid in self.observed and value["start"] == self.observed[pid]["start"]
        }
        while True:
            children = {
                pid: value
                for pid, value in snapshot.items()
                if pid not in self.observed and value["ppid"] in live
            }
            if not children:
                break
            if len(self.observed) + len(children) > MAX_OWNED:
                raise ValueError("Owned descendants exceed the bounded capacity")
            self.observed.update(children)
            live.update(children)
            self.groups.update(
                value["pgid"] for value in children.values() if value["pid"] == value["pgid"]
            )
        self.groups.update(
            value["pgid"] for value in live.values() if value["pid"] == value["pgid"]
        )
        return {pid: value for pid, value in live.items() if value["alive"]}

    def signal(self, signum):
        """Recheck PID/start and group identity immediately before signalling."""
        signalled = set()
        for pid, owned in tuple(self.observed.items()):
            actual = self.table.one(pid)
            if actual is None or not actual["alive"] or actual["start"] != owned["start"]:
                continue
            group = actual["pgid"]
            try:
                if group in self.groups and group not in signalled:
                    os.killpg(group, signum)
                    signalled.add(group)
                elif group not in self.groups:
                    os.kill(pid, signum)
            except ProcessLookupError:
                pass

    def cleanup(self, grace):
        """Retain observed authority after owner exit and bound remaining cleanup."""
        remaining = self.observe()
        if remaining:
            self.signal(signal.SIGTERM)
        deadline = time.monotonic() + max(0, grace)
        while remaining and time.monotonic() < deadline:
            time.sleep(0.025)
            remaining = self.observe()
        forced = bool(remaining)
        if forced:
            self.signal(signal.SIGKILL)
        deadline = time.monotonic() + 2
        while remaining and time.monotonic() < deadline:
            time.sleep(0.025)
            remaining = self.observe()
        if self.process.poll() is not None:
            self.process.wait()
        return forced, list(remaining.values())

    def receipt(self):
        return [self.observed[pid] for pid in sorted(self.observed)]
