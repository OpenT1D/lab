"""Strict regular-file access and immutable output boundaries for local tools."""

import hashlib
import json
import re
import signal
import stat
import time
from pathlib import Path

from experiments.platform_files import is_link
from experiments.platform_process import (
    close_tree,
    force_tree,
    handled_signals,
    signal_tree,
    spawn,
    tree_exists,
)

ROOT = Path(__file__).resolve().parents[2]
ID = re.compile(r"[a-z][a-z0-9_-]{0,63}\Z")
SHA = re.compile(r"[0-9a-f]{64}\Z")
CLEANUP_GRACE_SECONDS = 10
GROUP_RECHECK_SECONDS = 1


def require(condition, message):
    if not condition:
        raise ValueError(message)


def encoded(value):
    return (json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n").encode()


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def _pairs(pairs):
    result = {}
    for key, value in pairs:
        require(key not in result, "Duplicate JSON key")
        result[key] = value
    return result


def decode(raw):
    def nonfinite(_value):
        raise ValueError("Nonfinite JSON value")

    return json.loads(raw, object_pairs_hook=_pairs, parse_constant=nonfinite)


def regular(path):
    path = Path(path)
    require(not is_link(path), "Symlink or reparse-point input is unsupported")
    require(stat.S_ISREG(path.stat().st_mode), "Input must be a regular file")
    return path


def read(path, limit=32 * 1024 * 1024):
    path = regular(path)
    require(path.stat().st_size <= limit, "JSON input exceeds the bounded reader size")
    return decode(path.read_bytes())


def inventory(directory):
    directory = Path(directory)
    require(not is_link(directory) and directory.is_dir(), "Archive must be a directory")
    result = {}
    for path in sorted(directory.rglob("*")):
        require(not is_link(path), "Archive contains a symlink or reparse point")
        if path.is_dir():
            continue
        regular(path)
        before = path.stat()
        hasher = hashlib.sha256()
        with path.open("rb") as stream:
            while chunk := stream.read(1024 * 1024):
                hasher.update(chunk)
        after = path.stat()
        require(
            (before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns)
            == (after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns),
            "Archive changed while its inventory was read",
        )
        result[path.relative_to(directory).as_posix()] = {
            "sha256": hasher.hexdigest(),
            "size": after.st_size,
        }
    return result


def source_hashes(names):
    return {name: digest(regular(ROOT / name).read_bytes()) for name in names}


def fresh(path, inputs=()):
    path = Path(path).absolute()
    require(not is_link(path) and not path.exists(), "Choose a fresh output directory")
    resolved = path.resolve()
    for source in inputs:
        source = Path(source).resolve()
        require(
            resolved != source
            and resolved not in source.parents
            and source not in resolved.parents,
            "Output overlaps an input archive",
        )
    resolved.mkdir(parents=True, exist_ok=False)
    return resolved


def dump(path, value):
    Path(path).write_bytes(encoded(value))


def seal(directory):
    files = inventory(directory)
    require("manifest.json" not in files, "Output was already sealed")
    dump(directory / "manifest.json", {"schema": "opent1d.local-tool-archive/1", "files": files})


def load_sealed(directory):
    directory = Path(directory).absolute()
    manifest = read(directory / "manifest.json")
    require(
        isinstance(manifest, dict)
        and set(manifest) == {"schema", "files"}
        and manifest["schema"] == "opent1d.local-tool-archive/1",
        "Unsupported local-tool manifest",
    )
    files = inventory(directory)
    files.pop("manifest.json", None)
    require(files == manifest["files"], "Local-tool archive bytes changed")
    return directory


def text(value):
    return str(value).replace("\n", " ").replace("\r", " ").replace("|", "\\|").replace("`", "'")


def _owned_tree_call(process, operation):
    """Clear an access denial only after reaping and observing group disappearance."""
    try:
        return operation(process)
    except PermissionError as error:
        # Darwin killpg excludes zombies and can report EPERM between a leader's
        # exit and our reap. A denied probe alone never establishes an empty group.
        deadline = time.monotonic() + GROUP_RECHECK_SECONDS
        while True:
            process.poll()
            try:
                remaining = tree_exists(process)
            except PermissionError:
                remaining = None
            if remaining is False:
                return False
            if remaining is True or time.monotonic() >= deadline:
                raise error
            time.sleep(0.02)


def cleanup(process):
    """Retain tree ownership after leader exit, allowing bounded graceful cleanup."""
    try:
        _owned_tree_call(process, lambda owned: signal_tree(owned, signal.SIGTERM))
        deadline = time.monotonic() + CLEANUP_GRACE_SECONDS
        while True:
            process.poll()
            if not _owned_tree_call(process, tree_exists) or time.monotonic() >= deadline:
                break
            time.sleep(0.02)
    finally:
        # Also force the tree if cancellation arrives during graceful cleanup.
        try:
            process.poll()
            if _owned_tree_call(process, tree_exists):
                _owned_tree_call(process, force_tree)
            process.wait()
        finally:
            close_tree(process)


def supervise(args, logfile, cwd, env, timeout):
    """Scoped signal handling for explicit trusted tools, never archived scripts."""
    process, received, previous = None, None, {}
    cleaning = False

    def stop(signum, _frame):
        nonlocal received
        if received is None:
            received = signum
            # Launch and final cleanup must finish establishing/releasing their
            # ownership. Their latched signal is checked before returning.
            if process is not None and not cleaning:
                raise KeyboardInterrupt("Local tool operation interrupted")

    try:
        for signum in handled_signals():
            previous[signum] = signal.signal(signum, stop)
        with Path(logfile).open("wb") as log:
            try:
                if received is not None:
                    raise KeyboardInterrupt("Local tool operation interrupted")
                process = spawn(
                    args, cwd=cwd, env=env, stdout=log, stderr=log, start_new_session=True
                )
                if received is not None:
                    raise KeyboardInterrupt("Local tool operation interrupted")
                code = process.wait(timeout=timeout)
            finally:
                cleaning = True
                if process is not None:
                    cleanup(process)
        if received is not None:
            raise KeyboardInterrupt("Local tool operation interrupted")
        return {"status": "completed" if code == 0 else "failed", "exit_code": code}
    except KeyboardInterrupt:
        return {
            "status": "interrupted",
            "exit_code": None if process is None else process.returncode,
            "signal": received or signal.SIGINT,
        }
    finally:
        for signum, handler in previous.items():
            signal.signal(signum, handler)
