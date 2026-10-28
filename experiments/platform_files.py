"""Regular-file descriptors with a no-reparse boundary on Windows and POSIX."""

import ctypes
import errno
import ntpath
import os
import stat
from contextlib import contextmanager
from functools import lru_cache
from pathlib import Path, PurePosixPath, PureWindowsPath


def extended_windows_path(value):
    """Normalize an absolute DOS/UNC path before selecting the extended namespace.

    The prefix bypasses MAX_PATH without changing machine policy. It also disables
    Win32's normalization, so remove any existing prefix before collapsing dots.
    Device namespaces are deliberately unsupported for workspace files.
    """
    value = os.fsdecode(os.fspath(value)).replace("/", "\\")
    if value[:8].upper() == "\\\\?\\UNC\\":
        value = "\\\\" + value[8:]
    elif value.startswith("\\\\?\\"):
        value = value[4:]
    if value.startswith(("\\\\.\\", "\\??\\")) or "\0" in value:
        raise ValueError("Expected an absolute Windows filesystem path")
    value = ntpath.normpath(value)
    parsed = PureWindowsPath(value)
    drive = parsed.drive
    if not parsed.is_absolute():
        raise ValueError("Expected an absolute Windows filesystem path")
    if drive.startswith("\\\\"):
        return "\\\\?\\UNC\\" + value[2:]
    if len(drive) != 2 or drive[1] != ":" or not drive[0].isascii() or not drive[0].isalpha():
        raise ValueError("Expected an absolute Windows filesystem path")
    return "\\\\?\\" + value


def native_absolute(path):
    """Return a normalized live path; Windows data paths work beyond MAX_PATH."""
    absolute = os.path.abspath(path)
    return Path(extended_windows_path(absolute) if os.name == "nt" else absolute)


def recorded_path(value):
    """Parse absolute provenance without interpreting it as a path on this host."""
    if not isinstance(value, str) or not value or "\0" in value:
        raise ValueError("Invalid recorded path")
    path = PureWindowsPath(value) if PureWindowsPath(value).drive else PurePosixPath(value)
    if not path.is_absolute():
        raise ValueError("Recorded path must be absolute")
    return path


def is_link(path):
    """Include Windows junctions and other reparse points, not just symlinks."""
    try:
        value = Path(path).lstat()
    except FileNotFoundError:
        return False
    return stat.S_ISLNK(value.st_mode) or bool(getattr(value, "st_file_attributes", 0) & 0x400)


@lru_cache(maxsize=1)
def _windows_file_api():
    """Cache only immutable API bindings/types, never file state or open handles."""
    from ctypes import wintypes

    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    create = kernel.CreateFileW
    create.argtypes = (
        wintypes.LPCWSTR,
        wintypes.DWORD,
        wintypes.DWORD,
        ctypes.c_void_p,
        wintypes.DWORD,
        wintypes.DWORD,
        wintypes.HANDLE,
    )
    create.restype = wintypes.HANDLE
    close = kernel.CloseHandle
    close.argtypes = (wintypes.HANDLE,)
    close.restype = wintypes.BOOL
    query = kernel.GetFileInformationByHandleEx
    query.argtypes = (wintypes.HANDLE, ctypes.c_int, ctypes.c_void_p, wintypes.DWORD)
    query.restype = wintypes.BOOL

    class AttributeTag(ctypes.Structure):
        _fields_ = [("attributes", wintypes.DWORD), ("tag", wintypes.DWORD)]

    # Retain the library and typed functions for this process. Instances queried
    # from handles are always allocated by the caller, never retained here.
    return kernel, create, close, query, AttributeTag


def _windows_open(path, flags, *, delete_access=False):
    import msvcrt

    _kernel, create, close, query, AttributeTag = _windows_file_api()
    # Do not truncate before the handle and pathname identity are checked.
    access = 0x80000000 | (0x10000 if delete_access else 0)
    if flags & (os.O_WRONLY | os.O_RDWR):
        access |= 0x40000000
    disposition = 3  # OPEN_EXISTING
    if flags & os.O_CREAT:
        disposition = 1 if flags & os.O_EXCL else 4  # CREATE_NEW / OPEN_ALWAYS
    handle = create(str(Path(path).absolute()), access, 0x7, None, disposition, 0x00200000, None)
    if handle == ctypes.c_void_p(-1).value:
        raise ctypes.WinError(ctypes.get_last_error())
    try:
        info = AttributeTag()
        if not query(handle, 9, ctypes.byref(info), ctypes.sizeof(info)):
            raise ctypes.WinError(ctypes.get_last_error())
        if info.attributes & 0x400:
            raise ValueError("Reparse-point files are unsupported")
        descriptor = msvcrt.open_osfhandle(
            int(handle), (flags & (os.O_RDONLY | os.O_WRONLY | os.O_RDWR)) | os.O_BINARY
        )
    except BaseException:
        close(handle)
        raise
    return descriptor


def _open_regular(path, flags, mode):
    """Return the owned descriptor and its checked, pre-truncation snapshot.

    Snapshot consumers use O_RDONLY. The public opener retains its flags/API.
    """
    path = Path(path)
    if is_link(path):
        raise OSError(errno.ELOOP, "Linked files are unsupported", str(path))
    if os.name == "nt":
        descriptor = _windows_open(path, flags)
    else:
        descriptor = os.open(
            path,
            (flags & ~os.O_TRUNC) | os.O_NOFOLLOW | os.O_NONBLOCK | os.O_CLOEXEC,
            mode,
        )
    try:
        os.set_inheritable(descriptor, False)
        current = path.lstat()
        # Take the handle snapshot last so same-open metadata consumers observe
        # mutations during pathname validation, without a duplicate fstat.
        opened = os.fstat(descriptor)
        # Type/reparse policy and identity must use the same fresh pathname
        # snapshot; callers still verify the descriptor after their bounded read.
        if (
            not stat.S_ISREG(opened.st_mode)
            or stat.S_ISLNK(current.st_mode)
            or bool(getattr(current, "st_file_attributes", 0) & 0x400)
            or (opened.st_dev, opened.st_ino) != (current.st_dev, current.st_ino)
        ):
            raise ValueError("Expected a stable regular file; nonregular or changed file refused")
        if flags & os.O_TRUNC:
            os.ftruncate(descriptor, 0)
        return descriptor, opened
    except BaseException:
        os.close(descriptor)
        raise


def open_regular(path, flags=os.O_RDONLY, mode=0o600):
    """Open a stable regular file without following its final link/reparse point.

    Callers still own bounded reads and their application's ancestor policy.
    Truncation happens only after validation, including for a freshly created file.
    """
    return _open_regular(path, flags, mode)[0]


def regular_info(path):
    """Snapshot a fresh no-link descriptor, comparable to another descriptor.

    CPython 3.12 Windows path stat reports creation time as st_ctime, whereas
    fstat reports ChangeTime. Reopening retains the latter mutation check without
    comparing those different clocks or following a replaced link.
    """
    descriptor, snapshot = _open_regular(path, os.O_RDONLY, 0o600)
    try:
        return snapshot
    finally:
        os.close(descriptor)


@lru_cache(maxsize=1)
def _windows_rename_api():
    """Retain immutable native bindings, never a file handle or filesystem result."""
    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    rename = kernel.SetFileInformationByHandle
    rename.argtypes = (ctypes.c_void_p, ctypes.c_int, ctypes.c_void_p, ctypes.c_uint32)
    rename.restype = ctypes.c_int

    class RenameInfo(ctypes.Structure):
        _fields_ = [
            ("Flags", ctypes.c_uint32),
            ("RootDirectory", ctypes.c_void_p),
            ("FileNameLength", ctypes.c_uint32),
            ("FileName", ctypes.c_uint16 * 1),
        ]

    return kernel, rename, RenameInfo


def replace_windows_handle(handle, target):
    """Publish a caller-owned DELETE handle; existing readers retain old bytes.

    The caller owns ancestor, ordinary-file and identity checks, and closing the
    handle. This primitive never retries or falls back to non-atomic copying.
    """
    _library, rename, RenameInfo = _windows_rename_api()
    encoded = str(native_absolute(target)).encode("utf-16-le")
    # FileNameLength excludes the terminator, which must remain in the buffer.
    size = max(ctypes.sizeof(RenameInfo), RenameInfo.FileName.offset + len(encoded) + 2)
    buffer = ctypes.create_string_buffer(size)
    info = RenameInfo.from_buffer(buffer)
    # FileRenameInfoEx: REPLACE_IF_EXISTS | POSIX_SEMANTICS. NULL RootDirectory
    # selects the absolute extended path. Existing read handles remain valid.
    info.Flags, info.RootDirectory, info.FileNameLength = 0x3, None, len(encoded)
    ctypes.memmove(ctypes.addressof(buffer) + RenameInfo.FileName.offset, encoded, len(encoded))
    if not rename(handle, 22, buffer, size):
        raise ctypes.WinError(ctypes.get_last_error())


@contextmanager
def _windows_publication_parent(path):
    """Pin every ordinary ancestor without permitting a concurrent rename."""
    _kernel, create, close, query, Attributes = _windows_file_api()
    handles = []
    try:
        for parent in reversed(path.parents):
            handle = create(str(parent), 0x81, 3, None, 3, 0x02200000, None)
            if handle == ctypes.c_void_p(-1).value:
                raise ctypes.WinError(ctypes.get_last_error())
            handles.append(handle)
            attributes = Attributes()
            if not query(handle, 9, ctypes.byref(attributes), ctypes.sizeof(attributes)):
                raise ctypes.WinError(ctypes.get_last_error())
            if not attributes.attributes & 0x10 or attributes.attributes & 0x400:
                raise ValueError("Publication requires ordinary directory ancestors")
        yield
    finally:
        for handle in reversed(handles):
            close(handle)


def _publication_signature(info):
    if (
        not stat.S_ISREG(info.st_mode)
        or getattr(info, "st_file_attributes", 0) & 0x400
        or info.st_nlink != 1
    ):
        raise ValueError("Publication requires ordinary single-link files")
    return info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns, info.st_ctime_ns


def _publication_target(path):
    try:
        return _publication_signature(regular_info(path))[:2]
    except FileNotFoundError:
        return None


def _windows_atomic_write(path, temporary, content, *, text):
    """Write one fresh sibling, then publish its retained, validated handle."""
    import msvcrt
    import uuid

    path, temporary = native_absolute(path), native_absolute(temporary)
    if path == temporary or path.parent != temporary.parent:
        raise ValueError("Publication requires distinct sibling paths")
    if not text:
        # GUI administration must recover without adopting a crash's pending file.
        # Native text archives retain their existing, explicitly allowed .tmp names.
        temporary = temporary.with_name(temporary.name + "." + uuid.uuid4().hex + ".tmp")
    with _windows_publication_parent(path):
        target_identity = _publication_target(path)
        # Never open or truncate an existing pending entry.
        descriptor = _windows_open(
            temporary, os.O_RDWR | os.O_CREAT | os.O_EXCL, delete_access=True
        )
        identity = None
        try:
            os.set_inheritable(descriptor, False)
            identity = _publication_signature(os.fstat(descriptor))[:2]
            if _publication_target(temporary) != identity:
                raise ValueError("Publication pending file was replaced")
            # Default text encoding/newline match Path.write_text; bytes stay exact.
            with os.fdopen(descriptor, "w" if text else "wb", closefd=False) as stream:
                stream.write(content)
                stream.flush()
                raw = content.replace("\n", os.linesep).encode(stream.encoding) if text else content
            before = _publication_signature(os.fstat(descriptor))
            os.lseek(descriptor, 0, os.SEEK_SET)
            with os.fdopen(descriptor, "rb", closefd=False) as stream:
                for offset in range(0, len(raw), 1024 * 1024):
                    if (
                        stream.read(min(1024 * 1024, len(raw) - offset))
                        != raw[offset : offset + 1024 * 1024]
                    ):
                        raise ValueError("Publication pending bytes changed")
                if stream.read(1):
                    raise ValueError("Publication pending bytes changed")
            if (
                _publication_signature(regular_info(temporary)) != before
                or _publication_signature(os.fstat(descriptor)) != before
            ):
                raise ValueError("Publication pending file changed")
            if _publication_target(path) != target_identity:
                raise ValueError("Publication destination was replaced")
            replace_windows_handle(msvcrt.get_osfhandle(descriptor), path)
            if _publication_target(path) != identity:
                raise ValueError("Published file was replaced")
        finally:
            os.close(descriptor)
            # Never remove a substituted pending entry, even after a failed rename.
            try:
                current = _publication_target(temporary)
            except (OSError, ValueError):
                current = None
            if identity is not None and current == identity:
                temporary.unlink()


def _posix_atomic_write(path, temporary, content, *, text):
    """Write a fresh regular sibling; callers own their directory ancestry policy."""
    import uuid

    path, temporary = native_absolute(path), native_absolute(temporary)
    if path == temporary or path.parent != temporary.parent:
        raise ValueError("Publication requires distinct sibling paths")
    if not text:
        # A crash's fixed-name GUI pending entry is evidence, never authority.
        temporary = temporary.with_name(temporary.name + "." + uuid.uuid4().hex + ".tmp")
    descriptor = os.open(
        temporary,
        os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW | os.O_NONBLOCK | os.O_CLOEXEC,
        0o666,
    )
    identity = None
    try:
        identity = _publication_signature(os.fstat(descriptor))[:2]
        if _publication_signature(temporary.lstat())[:2] != identity:
            raise ValueError("Publication pending file was replaced")
        # Match Path.write_text's default encoding/newline and keep bytes exact.
        with os.fdopen(descriptor, "w" if text else "wb", closefd=False) as stream:
            stream.write(content)
            stream.flush()
        before = _publication_signature(os.fstat(descriptor))
        if (
            _publication_signature(temporary.lstat()) != before
            or _publication_signature(os.fstat(descriptor)) != before
        ):
            raise ValueError("Publication pending file changed")
        temporary.replace(path)
    finally:
        os.close(descriptor)
        # A substituted or newly hardlinked pending entry is not ours to remove.
        try:
            current = _publication_signature(temporary.lstat())[:2]
        except (OSError, ValueError):
            current = None
        if identity is not None and current == identity:
            temporary.unlink()


def atomic_write_bytes(path, content, *, temporary=None):
    """Publish complete bytes through a fresh sibling, retaining existing readers.

    ``temporary`` is a sibling naming template on both platforms. Old pending
    entries remain evidence, never authority for a new write.
    """
    path = Path(path)
    temporary = path.with_name(path.name + ".tmp") if temporary is None else Path(temporary)
    if os.name == "nt":
        _windows_atomic_write(path, temporary, content, text=False)
    else:
        _posix_atomic_write(path, temporary, content, text=False)


def atomic_write_text(path, content, *, temporary=None):
    """Keep native text bytes and fixed pending names; refuse existing pending entries."""
    path = Path(path)
    temporary = path.with_name(path.name + ".tmp") if temporary is None else Path(temporary)
    if os.name == "nt":
        _windows_atomic_write(path, temporary, content, text=True)
    else:
        _posix_atomic_write(path, temporary, content, text=True)
