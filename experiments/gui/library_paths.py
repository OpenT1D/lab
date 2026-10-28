"""Explicit read-only archive roots, separate from workspace output permissions."""

import hashlib
import os
import stat
from pathlib import Path, PurePosixPath

from experiments.platform_files import is_link, native_absolute


def directory_identity(path):
    value = Path(path).lstat()
    if not stat.S_ISDIR(value.st_mode) or is_link(path):
        raise ValueError("Choose a regular archive directory")
    return {"path": str(path), "device": value.st_dev, "inode": value.st_ino}


def validate_identity(identity):
    if (
        not isinstance(identity, dict)
        or set(identity) != {"path", "device", "inode"}
        or not isinstance(identity["path"], str)
        or not Path(identity["path"]).is_absolute()
        or type(identity["device"]) is not int
        or type(identity["inode"]) is not int
        or directory_identity(identity["path"]) != identity
    ):
        raise ValueError("Registered directory identity changed or is unavailable")
    return Path(identity["path"])


def relative_path(value):
    if not isinstance(value, str) or len(value) > 4096 or "\\" in value:
        raise ValueError("Choose a relative archive directory")
    path = PurePosixPath(value or ".")
    if path.is_absolute() or any(p == ".." or p.startswith(".") for p in path.parts):
        raise ValueError("Hidden, parent and absolute archive paths are unavailable")
    return path.as_posix() if path.parts else ""


def resolve_archive(root_identity, relative, expected=None):
    root = validate_identity(root_identity)
    relative = relative_path(relative)
    current = root
    for part in PurePosixPath(relative).parts:
        current /= part
        directory_identity(current)  # lstat refuses links at every selected component.
    identity = directory_identity(current)
    if expected is not None and identity != expected:
        raise ValueError("Registered archive directory was replaced")
    return current, identity


class ArchiveRoots:
    def __init__(self, workspace, extra=()):
        self.roots = {}
        for value in (workspace, *extra):
            canonical = native_absolute(value).resolve(strict=True)
            identity = directory_identity(canonical)
            raw = str(canonical) + ":" + str(identity["device"]) + ":" + str(identity["inode"])
            key = "root-" + hashlib.sha256(raw.encode()).hexdigest()[:24]
            self.roots[key] = identity

    def listing(self):
        return [
            {"id": key, "name": Path(value["path"]).name, "directory": value["path"]}
            for key, value in self.roots.items()
        ]

    def identity(self, key):
        if key not in self.roots:
            raise ValueError("Archive root is not enabled for this server")
        value = self.roots[key]
        validate_identity(value)
        return dict(value)

    def resolve(self, key, relative, expected=None):
        return resolve_archive(self.identity(key), relative, expected)

    def browse(self, key, relative=""):
        folder, _ = self.resolve(key, relative)
        entries, inspected = [], 0
        with os.scandir(folder) as children:
            for child in children:
                inspected += 1
                if inspected > 2000:
                    raise ValueError("Directory exceeds the bounded archive browser")
                if child.name.startswith(".") or is_link(child.path):
                    continue
                if child.is_dir(follow_symlinks=False):
                    if len(entries) >= 500:
                        raise ValueError("Directory has too many child directories")
                    path = (PurePosixPath(relative_path(relative)) / child.name).as_posix()
                    entries.append({"name": child.name, "path": path, "kind": "directory"})
        relative = relative_path(relative)
        parent = PurePosixPath(relative).parent.as_posix() if relative else None
        return {
            "root_id": key,
            "directory": relative,
            "parent": "" if parent == "." else parent,
            "entries": sorted(entries, key=lambda item: item["name"]),
        }
