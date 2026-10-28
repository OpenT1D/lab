"""Record source revision and actual edits in a checkout or installed source tree."""

import hashlib
import os
import re
import subprocess
from pathlib import Path, PurePosixPath

from experiments.desktop.admission_sources import SOURCE_FILES as ADMISSION_SOURCES
from experiments.desktop.runtime import SOURCE_FILES as RUNTIME_SOURCES
from experiments.desktop.runtime import packaged_manifest
from experiments.platform_files import is_link, open_regular

SOURCE_FILES = (
    "experiments/desktop/__init__.py",
    "experiments/desktop/provenance.py",
    *RUNTIME_SOURCES,
    *ADMISSION_SOURCES,
)


def source_version(root):
    root = Path(root).resolve(strict=True)
    package = packaged_manifest(root)
    if package is None:
        return {
            "revision": subprocess.check_output(
                ["git", "rev-parse", "HEAD"], cwd=root, text=True
            ).strip(),
            "dirty": bool(subprocess.check_output(["git", "status", "--porcelain"], cwd=root)),
        }
    source = package["source"]
    if (
        not isinstance(source, dict)
        or not isinstance(source.get("revision"), str)
        or re.fullmatch(r"[0-9a-f]{40}", source["revision"]) is None
        or type(source.get("dirty")) is not bool
        or not isinstance(source.get("files"), dict)
        or not 1 <= len(source["files"]) <= 20000
    ):
        raise ValueError("Invalid installed source identity")
    dirty = source["dirty"]
    actual = set()
    for path in root.rglob("*"):
        if is_link(path):
            raise ValueError("Installed source cannot contain linked files or directories")
        if path.is_file() and "__pycache__" not in path.parts and path.suffix != ".pyc":
            actual.add(path.relative_to(root).as_posix())
        elif not path.is_dir() and path.suffix != ".pyc":
            raise ValueError("Installed source must contain only regular files and directories")
    dirty |= actual != set(source["files"])
    for name, expected in source["files"].items():
        relative = PurePosixPath(name)
        if (
            not relative.parts
            or relative.is_absolute()
            or relative.as_posix() != name
            or any(part in {".", ".."} or ":" in part for part in relative.parts)
            or "\\" in name
        ):
            raise ValueError("Invalid installed source filename")
        path = root.joinpath(*relative.parts)
        if any(is_link(parent) for parent in (path, *path.parents)):
            raise ValueError("Installed source cannot contain linked files or directories")
        try:
            descriptor = open_regular(path)
            with os.fdopen(descriptor, "rb") as stream:
                opened = os.fstat(stream.fileno())
                dirty |= opened.st_size != expected["bytes"]
                dirty |= hashlib.file_digest(stream, "sha256").hexdigest() != expected["sha256"]
        except FileNotFoundError:
            dirty = True
    return {"revision": source["revision"], "dirty": dirty}
