"""Bounded local GUI convenience files; project authority stays in the SDK."""

import hashlib
import json
import math
import os
import stat
import uuid
from pathlib import Path


def require(condition, message):
    if not condition:
        raise ValueError(message)


def path(value, *, directory=False, fresh=False):
    result = Path(value)
    require(result.is_absolute(), "Choose an absolute location")
    result = result.absolute()
    require(".." not in result.parts, "Choose a canonical absolute location")
    require(not any(p.is_symlink() for p in (result, *result.parents)), "Linked paths refused")
    if directory:
        require(result.is_dir(), "Choose an existing directory")
    if fresh:
        require(not result.exists(), "Choose a new destination")
    return result


def outside_projects(value):
    result = path(value)
    for parent in (result, *result.parents):
        require(
            not all(
                (parent / name).exists()
                for name in ("HEAD.json", "events", "work", "pending", ".lock")
            ),
            "Keep GUI files and new outputs outside existing project stores",
        )
    # The verified shell launcher uses bin/../lib; canonicalise only this
    # trusted installation location, never caller-selected project paths.
    package = Path(__file__).resolve().parent
    require(
        not result.is_relative_to(package.parents[3]), "Keep GUI files outside the SDK environment"
    )
    return result


def read(value, maximum=8 * 1024 * 1024):
    filename = path(value)
    descriptor = os.open(filename, os.O_RDONLY | os.O_NONBLOCK | getattr(os, "O_NOFOLLOW", 0))
    try:
        before = os.fstat(descriptor)
        require(
            stat.S_ISREG(before.st_mode) and before.st_nlink == 1 and before.st_size <= maximum,
            "A bounded regular file is required",
        )
        with os.fdopen(descriptor, "rb", closefd=False) as stream:
            raw = stream.read(maximum + 1)
        after, current = os.fstat(descriptor), filename.stat(follow_symlinks=False)

        def signature(info):
            return info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns, info.st_ctime_ns

        require(
            len(raw) <= maximum and signature(before) == signature(after) == signature(current),
            "File changed during read",
        )
        return raw
    finally:
        os.close(descriptor)


def decode(raw):
    def pairs(items):
        result = {}
        for key, value in items:
            require(key not in result, "Duplicate JSON key")
            result[key] = value
        return result

    def constant(_value):
        raise ValueError("Nonfinite JSON value")

    value = json.loads(raw, object_pairs_hook=pairs, parse_constant=constant)

    def bounded(item, depth=0):
        require(depth <= 30, "JSON nesting is too deep")
        if isinstance(item, float):
            require(math.isfinite(item), "Nonfinite JSON value")
        if isinstance(item, dict):
            require(len(item) <= 10000, "JSON object is too large")
            for child in item.values():
                bounded(child, depth + 1)
        elif isinstance(item, list):
            require(len(item) <= 10000, "JSON array is too large")
            for child in item:
                bounded(child, depth + 1)

    bounded(value)
    return value


def encoded(value):
    return json.dumps(value, indent=2, sort_keys=True, allow_nan=False).encode() + b"\n"


def write(value, data):
    filename = outside_projects(value)
    if filename.exists():
        read(filename)
    temporary = filename.with_name(filename.name + "." + uuid.uuid4().hex)
    try:
        with temporary.open("xb") as stream:
            stream.write(encoded(data))
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, filename)
    finally:
        temporary.unlink(missing_ok=True)


def sha256(raw):
    return hashlib.sha256(raw).hexdigest()


class Lease:
    def __init__(self, filename):
        import fcntl

        filename = path(filename)
        self.fd = os.open(
            filename, os.O_RDWR | os.O_CREAT | os.O_NONBLOCK | getattr(os, "O_NOFOLLOW", 0), 0o600
        )
        try:
            require(
                stat.S_ISREG(os.fstat(self.fd).st_mode) and os.fstat(self.fd).st_nlink == 1,
                "Workspace lock must be a regular file",
            )
            os.set_inheritable(self.fd, False)
            fcntl.flock(self.fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BaseException:
            os.close(self.fd)
            self.fd = None
            raise ValueError("Another GUI may already manage this workspace") from None

    def close(self):
        if self.fd is not None:
            os.close(self.fd)
            self.fd = None
