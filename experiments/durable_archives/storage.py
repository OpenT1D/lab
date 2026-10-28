"""Streamed byte inventories, safe directory traversal and exclusive publication."""

import ctypes
import errno
import hashlib
import json
import os
import re
import shutil
import signal
import stat
import sys
import tempfile
import threading
import time
import unicodedata
from contextlib import contextmanager
from functools import wraps
from pathlib import Path, PureWindowsPath

from experiments.platform_files import (
    _open_regular,
    _windows_file_api,
    native_absolute,
    open_regular,
    recorded_path,
    regular_info,
)

MANIFEST_LIMIT = 8 * 1024 * 1024
FILE_LIMIT = 256 * 1024 * 1024
TOTAL_LIMIT = 2 * 1024 * 1024 * 1024
FILES_LIMIT = 50_000
ENTRIES_LIMIT = 100_000
OPERATION_SECONDS = 900
CHUNK = 1024 * 1024
SHA = re.compile(r"[0-9a-f]{64}\Z")
REVISION = re.compile(r"[0-9a-f]{40}\Z")


def require(condition, message):
    if not condition:
        raise ValueError(message)


def encoded(value):
    return json.dumps(value, sort_keys=True, indent=2, allow_nan=False).encode() + b"\n"


def strict_json(raw):
    def pairs(items):
        result = {}
        for key, value in items:
            require(key not in result, "Duplicate JSON key")
            result[key] = value
        return result

    def constant(_value):
        raise ValueError("Nonfinite JSON value")

    return json.loads(raw, object_pairs_hook=pairs, parse_constant=constant)


class Budget:
    def __init__(self):
        require(
            sys.platform in {"darwin", "win32"} or sys.platform.startswith("linux"),
            "Durable archive filesystem operations require a supported host",
        )
        self.deadline = time.monotonic() + OPERATION_SECONDS

    def check(self):
        require(time.monotonic() < self.deadline, "Archive operation deadline exceeded")


def cancellable(function):
    """Unwind owned staging on TERM/HUP and normal Python INT, including copying."""

    @wraps(function)
    def call(*args, **kwargs):
        main = threading.current_thread() is threading.main_thread()
        previous = {}

        def interrupted(_number, _frame):
            raise KeyboardInterrupt("Durable archive operation cancelled")

        try:
            if main:
                numbers = (signal.SIGTERM,)
                if hasattr(signal, "SIGHUP"):
                    numbers += (signal.SIGHUP,)
                for number in numbers:
                    previous[number] = signal.signal(number, interrupted)
            return function(*args, **kwargs)
        finally:
            if main:
                for number, handler in previous.items():
                    signal.signal(number, handler)

    return call


def relative_name(name):
    require(
        isinstance(name, str)
        and name
        and len(name.encode("utf-8")) <= 4096
        and len(name.split("/")) <= 128
        and not name.startswith("/")
        and "\\" not in name
        and ":" not in name
        and unicodedata.normalize("NFC", name) == name
        and all(ord(char) >= 32 and ord(char) != 127 for char in name)
        and all(part not in {"", ".", ".."} for part in name.split("/")),
        "Unsafe or noncanonical archive path",
    )
    return name


def safe_path(path, *, directory=True, fresh=False):
    """Inspect every caller-supplied ancestor without resolving away a link."""
    require(".." not in Path(path).parts, "Unsafe root path")
    path = native_absolute(path)
    require(str(path) != path.anchor, "Unsafe root path")
    current = Path(path.anchor)
    for index, component in enumerate(path.parts[1:], 1):
        require(
            component not in {"", ".", ".."}
            and unicodedata.normalize("NFC", component) == component,
            "Unsafe ancestor path",
        )
        current /= component
        last = index == len(path.parts) - 1
        if fresh and last:
            require(not os.path.lexists(current), "Output must be a fresh directory")
            # Refuse portable case aliases even on a case-sensitive host.
            with os.scandir(current.parent) as entries:
                for index, entry in enumerate(entries):
                    require(index < ENTRIES_LIMIT, "Output parent entry limit exceeded")
                    require(
                        unicodedata.normalize("NFC", entry.name).casefold() != component.casefold(),
                        "Output has a case/normalization alias",
                    )
            break
        info = current.lstat()
        require(not linked(info), "Linked/reparse-point ancestor refused")
        require(
            stat.S_ISDIR(info.st_mode) if not last or directory else stat.S_ISREG(info.st_mode),
            "Input must have regular directory ancestors",
        )
    return path


def separate(first, second):
    require(
        first != second and first not in second.parents and second not in first.parents,
        "Source, checkout and output paths must not overlap",
    )


def separate_recorded(first, second):
    """Compare inert provenance in its recorded flavor; never open foreign paths."""

    def canonical(value):
        path = recorded_path(value)
        if isinstance(path, PureWindowsPath):
            value = str(path)
            if value.lower().startswith("\\\\?\\unc\\"):
                value = "\\\\" + value[8:]
            elif value.startswith("\\\\?\\"):
                value = value[4:]
            path = PureWindowsPath(value)
        return path

    separate(canonical(first), canonical(second))


def signature(info):
    return info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns, info.st_ctime_ns


def directory_signature(info, descriptor):
    """Keep directory identity/timestamps without Windows' unstable size field.

    Windows path queries can report a nonzero directory size before its handle
    is opened, then zero while pinned. File sizes remain part of signature().
    """
    value = signature(info)
    return value[:2] + value[3:] if isinstance(descriptor, WindowsDirectory) else value


def linked(info):
    return stat.S_ISLNK(info.st_mode) or bool(getattr(info, "st_file_attributes", 0) & 0x400)


class WindowsDirectory:
    """Pin an ordinary directory against deletion/rename for the traversal lifetime."""

    def __init__(self, path):
        self.path = Path(path)
        _kernel, create, self.close_handle, query, Attributes = _windows_file_api()
        # FILE_LIST_DIRECTORY | FILE_READ_ATTRIBUTES for the attribute query;
        # share reads/writes, never delete. Open the reparse point itself so a
        # junction cannot silently redirect traversal.
        handle = create(str(self.path), 0x81, 3, None, 3, 0x02200000, None)
        if handle == ctypes.c_void_p(-1).value:
            raise ctypes.WinError(ctypes.get_last_error())
        self.handle = handle
        try:
            attributes = Attributes()
            if not query(handle, 9, ctypes.byref(attributes), ctypes.sizeof(attributes)):
                raise ctypes.WinError(ctypes.get_last_error())
            require(
                attributes.attributes & 0x10 and not attributes.attributes & 0x400,
                "Directory handle is linked or nonregular",
            )
            self.initial = self.path.stat(follow_symlinks=False)
            require(not linked(self.initial), "Reparse-point directory refused")
        except BaseException:
            self.close()
            raise

    def close(self):
        if self.handle is not None:
            handle, self.handle = self.handle, None
            self.close_handle(handle)


def directory_info(descriptor):
    if isinstance(descriptor, WindowsDirectory):
        info = descriptor.path.stat(follow_symlinks=False)
        require(
            not linked(info) and signature(info)[:2] == signature(descriptor.initial)[:2],
            "Pinned directory identity changed",
        )
        return info
    return os.fstat(descriptor)


def close_directory(descriptor):
    if isinstance(descriptor, WindowsDirectory):
        descriptor.close()
    else:
        os.close(descriptor)


def entry_info(descriptor, name):
    if isinstance(descriptor, WindowsDirectory):
        return (descriptor.path / name).stat(follow_symlinks=False)
    return os.stat(name, dir_fd=descriptor, follow_symlinks=False)


def open_file(descriptor, name):
    if isinstance(descriptor, WindowsDirectory):
        return open_regular(descriptor.path / name)
    return os.open(name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=descriptor)


def regular_entry_info(descriptor, name):
    """Keep Windows ChangeTime comparisons entirely on no-link file handles."""
    if isinstance(descriptor, WindowsDirectory):
        return regular_info(descriptor.path / name)
    return entry_info(descriptor, name)


def _open_directory(path, *, dir_fd=None):
    if os.name == "nt":
        return WindowsDirectory(Path(path) if dir_fd is None else dir_fd.path / path)
    return os.open(path, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=dir_fd)


@contextmanager
def root_fd(root):
    """Open each absolute ancestor relative to its already checked parent."""
    root = safe_path(root)
    descriptor = _open_directory(root.anchor)
    parents = []
    try:
        for component in root.parts[1:]:
            next_descriptor = _open_directory(component, dir_fd=descriptor)
            # Windows path-based access retains all ancestor handles, whose
            # no-delete sharing prevents an ancestor replacement during reads.
            if os.name == "nt":
                parents.append(descriptor)
            else:
                close_directory(descriptor)
            descriptor = next_descriptor
        yield descriptor
    finally:
        close_directory(descriptor)
        for parent in reversed(parents):
            close_directory(parent)


def stream_file(parent_fd, name, *, destination=None, limit=FILE_LIMIT, budget):
    if isinstance(parent_fd, WindowsDirectory):
        descriptor, before = _open_regular(parent_fd.path / name, os.O_RDONLY, 0o600)
    else:
        descriptor, before = open_file(parent_fd, name), None
    with os.fdopen(descriptor, "rb") as source:
        if before is None:
            before = os.fstat(source.fileno())
        require(stat.S_ISREG(before.st_mode), "Special archive file refused")
        require(before.st_nlink == 1, "Hardlinked archive file refused")
        require(before.st_size <= limit, "File exceeds byte limit")
        digest, total = hashlib.sha256(), 0
        output = None if destination is None else open(destination, "xb")
        try:
            while True:
                budget.check()
                raw = source.read(CHUNK)
                if not raw:
                    break
                total += len(raw)
                require(total <= limit, "File exceeds byte limit")
                digest.update(raw)
                if output is not None:
                    output.write(raw)
            require(
                signature(before) == signature(os.fstat(source.fileno()))
                and total == before.st_size,
                "File changed while reading",
            )
        finally:
            if output is not None:
                output.close()
    after = regular_entry_info(parent_fd, name)
    require(signature(before) == signature(after), "File replaced while reading")
    return {"sha256": digest.hexdigest(), "size": total}, signature(before)


def inventory(root, budget, *, destination=None, exclude_manifest=False):
    """Inspect the exact tree, optionally copying streams into owned staging."""
    root = safe_path(root)
    files, directories, signatures = {}, [], {}
    aliases, totals = set(), {"files": 0, "entries": 0, "bytes": 0}

    def walk(descriptor, prefix=""):
        before = directory_info(descriptor)
        signatures[prefix] = directory_signature(before, descriptor)
        with os.scandir(
            descriptor.path if isinstance(descriptor, WindowsDirectory) else descriptor
        ) as entries:
            names = []
            for entry in entries:
                budget.check()
                totals["entries"] += 1
                require(totals["entries"] <= ENTRIES_LIMIT, "Inspected entry limit exceeded")
                name = relative_name(prefix + entry.name)
                alias = name.casefold()
                require(alias not in aliases, "Case/normalization alias in archive")
                aliases.add(alias)
                names.append((entry.name, name))
            for basename, name in sorted(names):
                budget.check()
                info = entry_info(descriptor, basename)
                require(not linked(info), "Linked/reparse-point archive entry refused")
                if stat.S_ISDIR(info.st_mode):
                    directories.append(name)
                    if destination is not None:
                        (destination / name).mkdir()
                    child = _open_directory(basename, dir_fd=descriptor)
                    try:
                        require(
                            directory_signature(directory_info(child), child)
                            == directory_signature(info, child),
                            "Directory replaced",
                        )
                        walk(child, name + "/")
                    finally:
                        close_directory(child)
                    require(
                        directory_signature(info, descriptor)
                        == directory_signature(entry_info(descriptor, basename), descriptor),
                        "Directory changed while reading",
                    )
                else:
                    require(stat.S_ISREG(info.st_mode), "Special archive entry refused")
                    require(info.st_nlink == 1, "Hardlinked archive file refused")
                    if exclude_manifest and name == "manifest.json":
                        require(info.st_size <= MANIFEST_LIMIT, "Manifest exceeds byte limit")
                        continue
                    totals["files"] += 1
                    require(totals["files"] <= FILES_LIMIT, "File count limit exceeded")
                    require(
                        totals["bytes"] + info.st_size <= TOTAL_LIMIT, "Total byte limit exceeded"
                    )
                    target = None if destination is None else destination / name
                    record, observed = stream_file(
                        descriptor, basename, destination=target, limit=FILE_LIMIT, budget=budget
                    )
                    files[name] = record
                    signatures[name] = observed
                    totals["bytes"] += record["size"]
                    require(totals["bytes"] <= TOTAL_LIMIT, "Total byte limit exceeded")
        require(
            directory_signature(before, descriptor)
            == directory_signature(directory_info(descriptor), descriptor),
            "Directory changed while reading",
        )

    with root_fd(root) as descriptor:
        walk(descriptor)
    totals["entries"] = len(files) + len(directories)
    return {"files": files, "directories": sorted(directories), "totals": totals}, signatures


def read_file(root, name, budget, *, limit=MANIFEST_LIMIT):
    relative_name(name)
    with root_fd(root) as root:
        parents, descriptor = [], root
        try:
            for component in name.split("/")[:-1]:
                descriptor = _open_directory(component, dir_fd=descriptor)
                parents.append(descriptor)
            basename = name.split("/")[-1]
            fd = open_file(descriptor, basename)
            try:
                before = os.fstat(fd)
                require(
                    stat.S_ISREG(before.st_mode)
                    and before.st_nlink == 1
                    and before.st_size <= limit,
                    "Metadata must be a bounded regular file",
                )
                with os.fdopen(fd, "rb", closefd=False) as handle:
                    raw = handle.read(limit + 1)
                budget.check()
                require(
                    len(raw) <= limit
                    and signature(before) == signature(os.fstat(fd))
                    and signature(before) == signature(regular_entry_info(descriptor, basename)),
                    "Metadata changed or exceeds byte limit",
                )
                return raw
            finally:
                os.close(fd)
        finally:
            for parent in reversed(parents):
                close_directory(parent)


def exclusive_rename(source, target):
    """Publish a directory with the host's atomic no-replace primitive."""
    source, target = os.fsencode(source), os.fsencode(target)
    if sys.platform == "win32":
        os.rename(source, target)
        return
    library = ctypes.CDLL(None, use_errno=True)
    if sys.platform == "darwin":
        function = library.renamex_np
        function.argtypes = [ctypes.c_char_p, ctypes.c_char_p, ctypes.c_uint]
        function.restype = ctypes.c_int
        code = function(source, target, 4)  # RENAME_EXCL
    elif sys.platform.startswith("linux"):
        function = library.renameat2
        function.argtypes = [
            ctypes.c_int,
            ctypes.c_char_p,
            ctypes.c_int,
            ctypes.c_char_p,
            ctypes.c_uint,
        ]
        function.restype = ctypes.c_int
        code = function(-100, source, -100, target, 1)  # AT_FDCWD, RENAME_NOREPLACE
    else:
        raise ValueError("Atomic exclusive directory publication unavailable on this host")
    if code:
        number = ctypes.get_errno()
        if number in {errno.EEXIST, errno.ENOTEMPTY}:
            raise ValueError("Output appeared during publication; refusing replacement")
        raise OSError(number, os.strerror(number))


@contextmanager
def staging(output, inputs):
    output = safe_path(output, fresh=True)
    for source in inputs:
        separate(output, safe_path(source))
    parent_info = signature(output.parent.stat())[:2]
    stage = Path(tempfile.mkdtemp(prefix=".opent1d-durable-", dir=output.parent))
    try:
        yield stage
        safe_path(output, fresh=True)
        require(signature(output.parent.stat())[:2] == parent_info, "Output parent replaced")
        exclusive_rename(stage, output)
    finally:
        if stage.exists():
            shutil.rmtree(stage)
