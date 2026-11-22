"""Inventory exact tracked Git source bytes for internal builds."""

import hashlib
import re
import stat
import subprocess
from pathlib import PurePosixPath

MAX_SOURCE_BYTES = 512 * 1024 * 1024
EXCLUDED = {".git", ".venv", "__pycache__", "node_modules", "results", "private", "raw"}


def git(root, *args):
    return subprocess.check_output(["git", *args], cwd=root, timeout=60)


def source_inventory(root, *, allow_dirty=False):
    """Only tracked, regular files; never sweep a working directory into a release."""
    revision = git(root, "rev-parse", "HEAD").decode().strip()
    dirty = bool(git(root, "status", "--porcelain", "--untracked-files=all"))
    if not re.fullmatch(r"[0-9a-f]{40}", revision):
        raise ValueError("Invalid source revision")
    committed = {}
    for entry in git(root, "ls-tree", "-r", "-z", revision).split(b"\0"):
        if not entry:
            continue
        metadata, name = entry.split(b"\t", 1)
        mode, kind, object_id = metadata.split()
        if kind != b"blob" or mode not in {b"100644", b"100755"}:
            raise ValueError("Only regular committed source files may be packaged")
        committed[name.decode("utf-8")] = object_id.decode("ascii")
    names = sorted(
        name.decode("utf-8") for name in git(root, "ls-files", "-z").split(b"\0") if name
    )
    # Index flags and clean filters can make `git status` hide byte differences.
    # A clean package must bind the actual delivered bytes to this exact commit.
    dirty |= set(names) != set(committed)
    total, files = 0, {}
    for name in names:
        parts = PurePosixPath(name).parts
        if any(part in EXCLUDED or part == ".env" or part.startswith(".env.") for part in parts):
            raise ValueError("Tracked private/generated material is not permitted in an installer")
        path = root / name
        if any(parent.is_symlink() for parent in (path, *path.parents)):
            raise ValueError("Linked source paths are not permitted in an installer")
        try:
            info = path.lstat()
        except FileNotFoundError as exc:
            raise ValueError("A tracked source file is missing") from exc
        if not stat.S_ISREG(info.st_mode):
            raise ValueError("Only regular tracked source files may be packaged")
        total += info.st_size
        if total > MAX_SOURCE_BYTES or len(files) >= 20000:
            raise ValueError("Source payload exceeds its size/count limit")
        contents = path.read_bytes()
        if len(contents) != info.st_size:
            raise ValueError("Source changed during inventory")
        object_id = hashlib.sha1(b"blob " + str(len(contents)).encode() + b"\0" + contents)
        dirty |= object_id.hexdigest() != committed.get(name)
        files[name] = {"sha256": hashlib.sha256(contents).hexdigest(), "bytes": len(contents)}
    if dirty and not allow_dirty:
        raise ValueError(
            "Commit the complete source before building; --allow-dirty is for local tests"
        )
    return {"revision": revision, "dirty": dirty, "files": files}
