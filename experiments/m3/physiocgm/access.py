"""Durable conversion-only read receipts; not a model-evaluation ledger."""

import fcntl
import json
import os
import stat
from datetime import UTC, datetime

from experiments.m1.artifacts import strict_json
from experiments.m3.common import ID, SHA, digest, require

SCHEMA = "opent1d.physiocgm.conversion-access/1"


def _encoded(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()


def verify_log(raw, plan_sha):
    require(type(raw) is bytes and raw and raw.endswith(b"\n"), "Incomplete read history")
    entries = []
    for line in raw.splitlines():
        entry = strict_json(line)
        require(type(entry) is dict and set(entry) == {"payload", "sha256"}, "Invalid receipt")
        payload = entry["payload"]
        require(
            type(payload) is dict
            and set(payload)
            == {
                "schema",
                "plan_sha256",
                "sequence",
                "previous",
                "action",
                "subject",
                "source_sha256",
                "at_utc",
            }
            and payload["schema"] == SCHEMA
            and payload["plan_sha256"] == plan_sha
            and type(payload["sequence"]) is int
            and payload["sequence"] == len(entries)
            and payload["previous"] == (entries[-1]["sha256"] if entries else None)
            and payload["action"] in ("before_native_read", "before_bundle_read")
            and isinstance(payload["subject"], str)
            and ID.fullmatch(payload["subject"])
            and isinstance(payload["source_sha256"], str)
            and SHA.fullmatch(payload["source_sha256"])
            and entry["sha256"] == digest(_encoded(payload))
            and line == _encoded(entry),
            "Invalid read history",
        )
        timestamp = datetime.fromisoformat(payload["at_utc"])
        require(
            timestamp.utcoffset() is not None and timestamp.utcoffset().total_seconds() == 0,
            "Invalid receipt time",
        )
        entries.append(entry)
    return entries


def record_access(path, plan_sha, action, subject, source_sha):
    """Append and fsync before returning a receipt authorizing the named read."""
    fd = os.open(path, os.O_RDWR | os.O_APPEND | os.O_CREAT | os.O_NOFOLLOW, 0o600)
    try:
        fcntl.flock(fd, fcntl.LOCK_EX)
        info = os.fstat(fd)
        current = path.lstat()
        require(
            stat.S_ISREG(info.st_mode)
            and info.st_nlink == 1
            and not info.st_mode & 0o077
            and (info.st_dev, info.st_ino) == (current.st_dev, current.st_ino),
            "Read history must be a private regular file",
        )
        chunks = []
        while chunk := os.read(fd, 65536):
            chunks.append(chunk)
        raw = b"".join(chunks)
        entries = verify_log(raw, plan_sha) if raw else []
        payload = {
            "schema": SCHEMA,
            "plan_sha256": plan_sha,
            "sequence": len(entries),
            "previous": entries[-1]["sha256"] if entries else None,
            "action": action,
            "subject": subject,
            "source_sha256": source_sha,
            "at_utc": datetime.now(UTC).isoformat(timespec="microseconds"),
        }
        entry = {"payload": payload, "sha256": digest(_encoded(payload))}
        data = _encoded(entry) + b"\n"
        verify_log(raw + data, plan_sha)
        offset = 0
        while offset < len(data):
            count = os.write(fd, data[offset:])
            require(count > 0, "Failed to write read receipt")
            offset += count
        os.fsync(fd)
        directory = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY)
        try:
            os.fsync(directory)
        finally:
            os.close(directory)
        return entry
    finally:
        os.close(fd)
