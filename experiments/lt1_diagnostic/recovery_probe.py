"""Fixed private read-only observations; successful queries are not coverage.

No CLI, caller-selected command, mount, backup alteration or cleanup operation.
Return raw responses/paths/digests only to private owner-only evidence storage.
"""

import base64
import hashlib
import os
import platform
import plistlib
import stat
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path
from xml.parsers.expat import ExpatError

from experiments.lt1_diagnostic.control_identity import ROOT, identity
from experiments.lt1_diagnostic.frozen_setup import _private_directory

DATA = Path("/System/Volumes/Data")
TOOLS = {"diskutil": Path("/usr/sbin/diskutil"), "tmutil": Path("/usr/bin/tmutil")}
COMMANDS = {
    "apfs_snapshots": ("diskutil", "apfs", "listSnapshots", "-plist", str(DATA)),
    "time_machine_snapshots": ("tmutil", "listlocalsnapshots", str(DATA)),
    "configured_destinations": ("tmutil", "destinationinfo", "-X"),
}
ENVIRONMENT = {"LANG": "C", "LC_ALL": "C", "PATH": "/usr/bin:/bin"}
QUERY_LIMIT = 256 * 1024
MAX_TARGETS = 16
FILE_LIMIT = 16 * 1024 * 1024
TOTAL_LIMIT = 64 * 1024 * 1024
COVERAGE = {
    "all_copies_registered": False,
    "recovery_scope_reviewed": False,
    "snapshot_coverage_complete": False,
    "backup_coverage_complete": False,
}
AUTHORITY = {
    "effective_erasure_verified": False,
    "physical_sanitization_verified": False,
    "deletion_authorized": False,
    "setup_admitted": False,
    "native_execution_authorized": False,
}


def need(ok, reason):
    if not ok:
        raise ValueError("LT1 recovery probe refused: " + reason)


def _source_identity():
    return identity(__file__)


def _tool_identity():
    result = {}
    for name, path in TOOLS.items():
        try:
            result[name] = hashlib.sha256(path.read_bytes()).hexdigest()
        except OSError:
            result[name] = None
    return result


def _data_device():
    try:
        info = DATA.stat()
        return info.st_dev if stat.S_ISDIR(info.st_mode) else None
    except OSError:
        return None


def _inside_checkout(path):
    """Resolve filesystem identity, including a differently cased checkout."""
    try:

        def token(point):
            info = point.stat()
            return info.st_dev, info.st_ino

        root_token = token(ROOT)
        root_ancestors = {token(parent) for parent in (ROOT, *ROOT.parents)}
        parents = {token(parent) for parent in path.parents}
        try:
            leaf = token(path)
        except FileNotFoundError:
            leaf = None
        return root_token in parents or leaf in root_ancestors
    except OSError as error:
        raise ValueError("LT1 recovery probe refused: checkout ancestry unavailable") from error


def _query(name):
    need(name in COMMANDS, "fixed query")
    tool, *args = COMMANDS[name]
    try:
        result = subprocess.run(
            [str(TOOLS[tool]), *args],
            env=ENVIRONMENT,
            stdin=subprocess.DEVNULL,
            capture_output=True,
            check=False,
            timeout=5,
        )
        out, error = result.stdout[:QUERY_LIMIT], result.stderr[:QUERY_LIMIT]
        truncated = len(result.stdout) > QUERY_LIMIT or len(result.stderr) > QUERY_LIMIT
        plist_valid = None
        if name != "time_machine_snapshots":
            try:
                plist_valid = isinstance(plistlib.loads(out), (dict, list))
            except (ValueError, plistlib.InvalidFileException, OverflowError, ExpatError):
                plist_valid = False
        observed = (
            type(result.returncode) is int
            and result.returncode == 0
            and not truncated
            and bool(out)
            and plist_valid is not False
        )
        return {
            "status": "response-observed" if observed else "unavailable",
            "returncode": result.returncode,
            "truncated": truncated,
            "plist_valid": plist_valid,
            "stdout_base64": base64.b64encode(out).decode("ascii"),
            "stderr_base64": base64.b64encode(error).decode("ascii"),
            "stdout_sha256": hashlib.sha256(out).hexdigest(),
            "stderr_sha256": hashlib.sha256(error).hexdigest(),
        }
    except (OSError, subprocess.SubprocessError) as error:
        return {"status": "unavailable", "returncode": None, "error": type(error).__name__}


def _signature(info):
    return (
        info.st_dev,
        info.st_ino,
        info.st_uid,
        info.st_mode,
        info.st_size,
        info.st_mtime_ns,
        info.st_ctime_ns,
        info.st_nlink,
    )


def _readback(path, data_device, budget):
    """One exact reviewed local file, never a root walk or payload copy."""
    result = {
        "path": str(path),
        "observed_from": datetime.now(UTC).isoformat(),
        "state": "unknown",
        "data_device_matches": None,
    }
    parent = file = None
    count = 0
    try:
        need(data_device is not None, "Data mapping unavailable")
        parent = _private_directory(path.parent)
        parent_id = os.fstat(parent)
        result["data_device_matches"] = parent_id.st_dev == data_device
        need(result["data_device_matches"], "outside Data device")

        def bound():
            live, opened = path.parent.lstat(), os.fstat(parent)
            need(
                path.parent.resolve() == path.parent
                and (live.st_dev, live.st_ino)
                == (opened.st_dev, opened.st_ino)
                == (parent_id.st_dev, parent_id.st_ino)
                and opened.st_uid == os.getuid()
                and stat.S_IMODE(opened.st_mode) == 0o700,
                "parent binding changed",
            )

        try:
            file = os.open(
                path.name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK | os.O_CLOEXEC, dir_fd=parent
            )
        except FileNotFoundError:
            bound()
            try:
                os.stat(path.name, dir_fd=parent, follow_symlinks=False)
            except FileNotFoundError:
                bound()
                result.update(state="absence-observed", device=parent_id.st_dev)
                return result, 0
            raise ValueError("LT1 recovery probe refused: absent path reappeared")
        before = os.fstat(file)
        result["data_device_matches"] = before.st_dev == data_device
        need(result["data_device_matches"], "file outside Data device")
        need(
            stat.S_ISREG(before.st_mode)
            and before.st_nlink == 1
            and before.st_uid == os.getuid()
            and stat.S_IMODE(before.st_mode) in (0o400, 0o600),
            "ordinary private single-link file",
        )
        need(before.st_size <= min(FILE_LIMIT, budget), "copy byte bound")
        checksum, count = hashlib.sha256(), 0
        while chunk := os.read(file, min(1024 * 1024, before.st_size + 1 - count)):
            count += len(chunk)
            need(count <= before.st_size, "copy grew")
            checksum.update(chunk)
        live = os.stat(path.name, dir_fd=parent, follow_symlinks=False)
        need(
            _signature(before) == _signature(os.fstat(file)) == _signature(live)
            and count == before.st_size,
            "copy bytes or binding changed",
        )
        bound()
        result.update(
            state="present",
            bytes=count,
            sha256=checksum.hexdigest(),
            device=before.st_dev,
            inode=before.st_ino,
            uid=before.st_uid,
            mode=stat.S_IMODE(before.st_mode),
            mtime_ns=before.st_mtime_ns,
            ctime_ns=before.st_ctime_ns,
        )
        return result, count
    except (OSError, ValueError) as error:
        result.update(state="unknown", error=str(error), inspected_bytes=count)
        return result, count
    finally:
        for fd in (file, parent):
            if fd is not None:
                os.close(fd)
        result["observed_to"] = datetime.now(UTC).isoformat()


def capture(*, targets=()):
    """Explicit fixed collector; never grants scope approval or restoration proof."""
    need(
        Path(__file__).resolve() == ROOT / "experiments/lt1_diagnostic/recovery_probe.py",
        "canonical collector required",
    )
    need(sys.platform == "darwin" and platform.machine() == "arm64", "Darwin arm64 required")
    need(
        isinstance(targets, (list, tuple)) and len(targets) <= MAX_TARGETS, "reviewed target count"
    )
    paths = []
    for value in targets:
        need(isinstance(value, (str, Path)), "reviewed target path")
        path = Path(value)
        need(
            path.is_absolute()
            and len(str(path)) <= 1024
            and "\0" not in str(path)
            and not path.is_relative_to(ROOT)
            and not ROOT.is_relative_to(path),
            "absolute reviewed path outside checkout",
        )
        need(not _inside_checkout(path), "reviewed path outside checkout required")
        need(path not in paths, "duplicate target")
        paths.append(path)
    started = datetime.now(UTC).isoformat()
    source, tools, device = _source_identity(), _tool_identity(), _data_device()
    readbacks, remaining = [], TOTAL_LIMIT
    for path in paths:
        observation, count = _readback(path, device, remaining)
        readbacks.append(observation)
        remaining = max(0, remaining - count)
    queries = {
        name: _query(name)
        if tools[command[0]] is not None
        else {"status": "unavailable", "returncode": None, "error": "tool-unavailable"}
        for name, command in COMMANDS.items()
    }
    need(
        source == _source_identity() and tools == _tool_identity() and device == _data_device(),
        "source/tool/Data mapping changed",
    )
    observed = (
        device is not None
        and all(q["status"] == "response-observed" for q in queries.values())
        and all(r["state"] != "unknown" for r in readbacks)
    )
    return {
        "schema": "opent1d.lt1-readonly-recovery-probe/1",
        "kind": "point-observation",
        "observed_from": started,
        "observed_to": datetime.now(UTC).isoformat(),
        "status": "observed" if observed else "partial",
        "collector_identity": source,
        "tool_sha256": tools,
        "data_device": device,
        "queries": queries,
        "local_readbacks": readbacks,
        "coverage": dict(COVERAGE),
        "authorizations": dict(AUTHORITY),
    }
