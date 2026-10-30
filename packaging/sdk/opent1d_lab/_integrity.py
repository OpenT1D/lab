"""Bounded checks of the installed source artifact, before payload imports."""

import hashlib
import json
import os
import stat
from pathlib import Path, PurePosixPath

SCHEMA = "opent1d.installed-sdk/3"
TASKS = ["mmtt-sensitivity", "m4-study-secure", "m4-study-installed", "mmtt-sampling"]


def regular_bytes(path, limit=16 * 1024 * 1024):
    path = Path(path)
    if any(p.is_symlink() for p in (path, *path.parents)):
        raise ValueError("Linked installed source is unsupported")
    initial = path.stat(follow_symlinks=False)
    if not stat.S_ISREG(initial.st_mode):
        raise ValueError("Installed source must be a regular file")
    descriptor = os.open(path, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0) | os.O_NONBLOCK)
    try:
        before = os.fstat(descriptor)
        if not stat.S_ISREG(before.st_mode) or before.st_nlink != 1 or before.st_size > limit:
            raise ValueError("Installed source must be a bounded regular copy")
        with os.fdopen(descriptor, "rb", closefd=False) as stream:
            raw = stream.read(limit + 1)
        after, current = os.fstat(descriptor), path.stat(follow_symlinks=False)

        def signature(info):
            return (info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns, info.st_ctime_ns)

        if (
            len(raw) > limit
            or signature(before) != signature(after)
            or signature(after) != signature(current)
        ):
            raise ValueError("Installed source changed while reading")
        return raw
    finally:
        os.close(descriptor)


def verify(package):
    package = Path(package)
    metadata = json.loads(regular_bytes(package / "_manifest.json", 4 * 1024 * 1024))
    if (
        not isinstance(metadata, dict)
        or set(metadata)
        != {"schema", "source", "build_label", "files", "tasks", "native_execution"}
        or not (
            (
                metadata["schema"] == SCHEMA
                and metadata["tasks"] == TASKS
                and metadata["native_execution"] == "explicit-reviewed-attachment/1"
            )
            or (
                metadata["schema"] == "opent1d.installed-sdk/2"
                and metadata["tasks"] == TASKS[:3]
                and metadata["native_execution"] == "explicit-reviewed-attachment/1"
            )
            or (
                metadata["schema"] == "opent1d.installed-sdk/1"
                and metadata["tasks"] == ["mmtt-sensitivity", "m4-study-secure"]
                and metadata["native_execution"] == "unavailable-public-policy"
            )
        )
        or not isinstance(metadata["files"], dict)
        or not 1 <= len(metadata["files"]) <= 2000
    ):
        raise ValueError("Unsupported installed artifact descriptor")
    for name, expected in metadata["files"].items():
        relative = PurePosixPath(name)
        if (
            not name
            or relative.is_absolute()
            or relative.as_posix() != name
            or any(part in {".", ".."} for part in relative.parts)
            or ":" in name
            or "\\" in name
            or "\0" in name
        ):
            raise ValueError("Unsafe installed source name")
        raw = regular_bytes(package.joinpath(*relative.parts))
        if expected != {"sha256": hashlib.sha256(raw).hexdigest(), "bytes": len(raw)}:
            raise ValueError("Installed source identity changed: " + name)
    observed, directories = set(), set()
    for path in package.rglob("*"):
        relative = path.relative_to(package)
        if path.is_symlink():
            raise ValueError("Linked installed entry is unsupported")
        # Normal Python API imports may cache the facade; payload workers use
        # -B and their entire executable source/data tree stays exact.
        if "__pycache__" in relative.parts and "_payload" not in relative.parts:
            continue
        if path.is_file() and relative.as_posix() != "_manifest.json":
            observed.add(relative.as_posix())
        elif path.is_dir():
            directories.add(relative.as_posix())
        elif not path.is_file():
            raise ValueError("Special installed entry refused")
    expected_directories = {
        parent.as_posix()
        for name in metadata["files"]
        for parent in PurePosixPath(name).parents
        if parent.parts
    }
    if observed != set(metadata["files"]) or directories != expected_directories:
        raise ValueError("Installed source roster differs")
    return metadata
