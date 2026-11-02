"""Reviewed data-only materialization. Empty request authority refuses all setup."""

import json
import os
import platform
import re
import socket
import stat
import sys
from pathlib import Path

from experiments.lt1_diagnostic.archive_preflight import digest, unique_object

HERE = Path(__file__).resolve().parent
REQUEST_LIMIT = 4 * 1024 * 1024
FILE_LIMIT = 128 * 1024 * 1024
TOTAL_LIMIT = 512 * 1024 * 1024
MAX_FILES = 4096
MAX_DIRECTORIES = 128
MAX_DEPTH = 16
MAX_PATH = 512


def need(ok, reason):
    if not ok:
        raise ValueError("LT1 setup refused: " + reason)


def fields(value, names):
    need(isinstance(value, dict) and set(value) == set(names.split()), "fields")


def file_identity(value):
    fields(value, "bytes sha256")
    need(type(value["bytes"]) is int and 0 <= value["bytes"] <= FILE_LIMIT, "file bound")
    need(
        isinstance(value["sha256"], str) and re.fullmatch("[a-f0-9]{64}", value["sha256"]),
        "file hash",
    )


def source_identity():
    paths = [
        HERE / name
        for name in (
            "frozen_setup.py",
            "setup_payload.py",
            "archive_preflight.py",
            "payload_selection.py",
        )
    ]
    root = HERE.parents[1]
    paths += [
        folder / "__init__.py"
        for folder in (root / "experiments", HERE)
        if (folder / "__init__.py").is_file()
    ]
    return {
        "python": platform.python_version(),
        "executable_sha256": digest(Path(sys.executable).resolve().read_bytes()),
        "implementation": {p.relative_to(root).as_posix(): digest(p.read_bytes()) for p in paths},
    }


def _read_at(folder, name, limit):
    fd = os.open(name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK | os.O_CLOEXEC, dir_fd=folder)
    try:
        before = os.fstat(fd)
        need(
            stat.S_ISREG(before.st_mode) and before.st_nlink == 1 and before.st_size <= limit,
            "regular bounded input",
        )
        result = bytearray()
        while True:
            part = os.read(fd, min(1024 * 1024, limit + 1 - len(result)))
            if not part:
                break
            result.extend(part)
            need(len(result) <= limit, "input bound")
        after = os.fstat(fd)
        current = os.stat(name, dir_fd=folder, follow_symlinks=False)

        def signature(s):
            return s.st_dev, s.st_ino, s.st_size, s.st_mtime_ns, s.st_ctime_ns

        need(signature(before) == signature(after) == signature(current), "changed input")
        return bytes(result)
    finally:
        os.close(fd)


def _private_directory(path):
    need(os.name == "posix", "POSIX required")
    path = Path(path)
    need(path.is_absolute() and path.resolve() == path, "canonical directory")
    fd = os.open(path, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC)
    try:
        s, live = os.fstat(fd), path.lstat()
        need(
            stat.S_ISDIR(s.st_mode)
            and s.st_uid == os.getuid()
            and s.st_mode & 0o077 == 0
            and (s.st_dev, s.st_ino) == (live.st_dev, live.st_ino),
            "private owned directory",
        )
        return fd
    except BaseException:
        os.close(fd)
        raise


def _write_at(folder, name, raw, mode):
    fd = os.open(
        name,
        os.O_RDWR | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW | os.O_CLOEXEC,
        0o600,
        dir_fd=folder,
    )
    try:
        offset = 0
        while offset < len(raw):
            written = os.write(fd, raw[offset:])
            need(written > 0, "short write")
            offset += written
        os.fsync(fd)
        os.lseek(fd, 0, os.SEEK_SET)
        import hashlib

        checksum = hashlib.sha256()
        while part := os.read(fd, 1024 * 1024):
            checksum.update(part)
        s = os.fstat(fd)
        live = os.stat(name, dir_fd=folder, follow_symlinks=False)
        need(
            s.st_nlink == 1
            and s.st_size == len(raw)
            and (s.st_dev, s.st_ino) == (live.st_dev, live.st_ino)
            and checksum.hexdigest() == digest(raw),
            "written file changed",
        )
        os.fchmod(fd, mode)
        os.fsync(fd)
    finally:
        os.close(fd)
    os.fsync(folder)


def _path_inventory(files):
    need(isinstance(files, dict) and 0 < len(files) <= MAX_FILES, "file count")
    aliases, parents = {}, set()
    for name in files:
        need(
            isinstance(name, str)
            and len(name) <= MAX_PATH
            and re.fullmatch(r"[A-Za-z0-9_@+.,/-]+", name),
            "payload path",
        )
        parts = name.split("/")
        need(len(parts) <= MAX_DEPTH, "payload depth")
        need(
            all(
                p and p not in {".", ".."} and not p.endswith(".") and len(p) <= 128 for p in parts
            ),
            "payload components",
        )
        for i in range(1, len(parts) + 1):
            path = "/".join(parts[:i])
            key = path.casefold()
            need(key not in aliases or aliases[key] == path, "case alias")
            aliases[key] = path
        parents.update("/".join(parts[:i]) for i in range(1, len(parts)))
    need(not parents.intersection(files), "file parent collision")
    need(len(parents) + 1 <= MAX_DIRECTORIES, "directory count")


def _validate(raw, registry):
    fields(registry, "schema requests")
    need(
        registry["schema"] == "opent1d.lt1-setup-request-admissions/1"
        and isinstance(registry["requests"], list),
        "request authority",
    )
    # Unknown bytes refuse before parsing, input access or filesystem mutation.
    need(
        isinstance(raw, bytes)
        and len(raw) <= REQUEST_LIMIT
        and digest(raw) in registry["requests"],
        "no reviewed setup request",
    )
    request = json.loads(raw, object_pairs_hook=unique_object)
    fields(
        request,
        "schema kind parent name inputs files review_receipts "
        "stager_identity host platform machine",
    )
    need(
        request["schema"] == "opent1d.lt1-materialization-request/1"
        and request["kind"] in {"invented", "native"},
        "request schema",
    )
    need(request["stager_identity"] == source_identity(), "stager identity")
    need(
        request["host"] == socket.gethostname()
        and request["platform"] == sys.platform
        and request["machine"] == platform.machine(),
        "named host",
    )
    if request["kind"] == "native":
        need(
            sys.platform == "darwin"
            and platform.machine() == "arm64"
            and sys.flags.isolated
            and sys.flags.no_site,
            "native clean startup",
        )
    need(
        isinstance(request["name"], str)
        and re.fullmatch("[a-z0-9][a-z0-9-]{0,63}", request["name"]),
        "attempt name",
    )
    inputs = request["inputs"]
    need(isinstance(inputs, dict) and 0 < len(inputs) <= MAX_FILES, "input count")
    for name, item in inputs.items():
        need(re.fullmatch("[a-z0-9][a-z0-9-]{0,63}", name), "input id")
        file_identity(item)
    need(sum(i["bytes"] for i in inputs.values()) <= TOTAL_LIMIT, "total inputs")
    _path_inventory(request["files"])
    for value in request["files"].values():
        fields(value, "input bytes sha256 mode")
        need(
            value["input"] in inputs
            and {k: value[k] for k in ("bytes", "sha256")} == inputs[value["input"]],
            "payload input",
        )
        need(type(value["mode"]) is int and value["mode"] in {0o400, 0o500}, "payload mode")
    need(sum(v["bytes"] for v in request["files"].values()) <= TOTAL_LIMIT, "total payload")
    fields(request["review_receipts"], "rights security harness")
    need(
        all(value in inputs for value in request["review_receipts"].values()), "review receipt ids"
    )
    need(
        set(inputs)
        == {v["input"] for v in request["files"].values()}
        | set(request["review_receipts"].values()),
        "unused inputs",
    )
    return request


def _check_directory_bindings(root, dirs):
    for path, fd in dirs.items():
        owner, name = (
            (root, "payload")
            if not path
            else (dirs[path.rpartition("/")[0]], path.rpartition("/")[2])
        )
        live, opened = os.stat(name, dir_fd=owner, follow_symlinks=False), os.fstat(fd)
        need(
            stat.S_ISDIR(live.st_mode)
            and (live.st_dev, live.st_ino) == (opened.st_dev, opened.st_ino),
            "payload directory changed",
        )


def _verify_payload(dirs, files, check=lambda: None):
    check()
    children = {path: set() for path in dirs}
    for path in dirs:
        if path:
            parent, _, name = path.rpartition("/")
            children[parent].add(name)
    for path, expected in files.items():
        check()
        parent, _, name = path.rpartition("/")
        children[parent].add(name)
        raw = _read_at(dirs[parent], name, expected["bytes"])
        need(len(raw) == expected["bytes"] and digest(raw) == expected["sha256"], "payload changed")
        live = os.stat(name, dir_fd=dirs[parent], follow_symlinks=False)
        need(stat.S_IMODE(live.st_mode) == expected["mode"], "payload mode changed")
    need(
        all(set(os.listdir(fd)) == children[path] for path, fd in dirs.items()),
        "unexpected payload entry",
    )
    check()


def _materialize_reviewed(raw, registry, read_input):
    """Trusted internal authority injection is for invented fixture qualification."""
    request = _validate(raw, registry)
    blobs = {}
    for name, expected in request["inputs"].items():
        value = read_input(name, expected["bytes"])
        need(
            isinstance(value, bytes)
            and len(value) == expected["bytes"]
            and digest(value) == expected["sha256"],
            "input bytes",
        )
        blobs[name] = value
    parent = _private_directory(request["parent"])
    root, dirs = None, {}
    try:
        os.mkdir(request["name"], 0o700, dir_fd=parent)
        os.fsync(parent)
        root = os.open(
            request["name"],
            os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC,
            dir_fd=parent,
        )
        root_id, parent_id = os.fstat(root), os.fstat(parent)
        need(root_id.st_uid == os.getuid(), "output owner")
        os.fchmod(root, 0o700)

        def checked():
            path = Path(request["parent"])
            live_parent = path.lstat()
            actual = os.stat(request["name"], dir_fd=parent, follow_symlinks=False)
            need(
                path.resolve() == path
                and (live_parent.st_dev, live_parent.st_ino) == (parent_id.st_dev, parent_id.st_ino)
                and (actual.st_dev, actual.st_ino) == (root_id.st_dev, root_id.st_ino),
                "output namespace changed",
            )
            for path, fd in dirs.items():
                owner, name = (
                    (root, "payload")
                    if not path
                    else (dirs[path.rpartition("/")[0]], path.rpartition("/")[2])
                )
                live, opened = os.stat(name, dir_fd=owner, follow_symlinks=False), os.fstat(fd)
                need(
                    stat.S_ISDIR(live.st_mode)
                    and (live.st_dev, live.st_ino) == (opened.st_dev, opened.st_ino),
                    "payload directory changed",
                )

        try:
            checked()
            os.mkdir("payload", 0o700, dir_fd=root)
            dirs[""] = os.open(
                "payload", os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC, dir_fd=root
            )
            os.fchmod(dirs[""], 0o700)
            for name, value in sorted(request["files"].items()):
                checked()
                pieces = name.split("/")
                for i in range(1, len(pieces)):
                    relative = "/".join(pieces[:i])
                    if relative not in dirs:
                        owner = dirs["/".join(pieces[: i - 1])]
                        os.mkdir(pieces[i - 1], 0o700, dir_fd=owner)
                        dirs[relative] = os.open(
                            pieces[i - 1],
                            os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC,
                            dir_fd=owner,
                        )
                        os.fchmod(dirs[relative], 0o700)
                checked()
                _write_at(
                    dirs["/".join(pieces[:-1])], pieces[-1], blobs[value["input"]], value["mode"]
                )
            checked()
            _verify_payload(dirs, request["files"])
            need(set(os.listdir(root)) == {"payload"}, "unexpected output entry")
            for fd in reversed(list(dirs.values())):
                os.fchmod(fd, 0o500)
                os.fsync(fd)
            manifest = {
                "schema": "opent1d.lt1-materialized-inventory/1",
                "status": "materialized",
                "kind": request["kind"],
                "request_sha256": digest(raw),
                "files": request["files"],
                "review_receipt_sha256": {
                    k: request["inputs"][v]["sha256"] for k, v in request["review_receipts"].items()
                },
                "stager_identity": request["stager_identity"],
                "setup_admitted": False,
                "native_execution_authorized": False,
            }
            content = (json.dumps(manifest, sort_keys=True) + "\n").encode()
            _write_at(root, ".inventory.pending", content, 0o400)
            checked()
            need(
                set(os.listdir(root)) == {"payload", ".inventory.pending"},
                "unexpected pending entry",
            )
            need(
                _read_at(root, ".inventory.pending", REQUEST_LIMIT) == content,
                "pending inventory changed",
            )
            need(
                stat.S_IMODE(
                    os.stat(".inventory.pending", dir_fd=root, follow_symlinks=False).st_mode
                )
                == 0o400,
                "pending inventory mode",
            )
            os.link(
                ".inventory.pending",
                "materialized.json",
                src_dir_fd=root,
                dst_dir_fd=root,
                follow_symlinks=False,
            )
            os.unlink(".inventory.pending", dir_fd=root)
            os.fsync(root)
            checked()
            need(
                _read_at(root, "materialized.json", REQUEST_LIMIT) == content,
                "published inventory changed",
            )
            need(
                stat.S_IMODE(
                    os.stat("materialized.json", dir_fd=root, follow_symlinks=False).st_mode
                )
                == 0o400,
                "published inventory mode",
            )
            need(
                set(os.listdir(root)) == {"payload", "materialized.json"}, "unexpected final entry"
            )
            return manifest
        except BaseException as error:
            try:
                _write_at(
                    root,
                    "failure.json",
                    (
                        json.dumps(
                            {
                                "status": "failed",
                                "error": str(error)[:4096],
                                "setup_admitted": False,
                            }
                        )
                        + "\n"
                    ).encode(),
                    0o400,
                )
            except BaseException:
                pass
            raise
    finally:
        for fd in dirs.values():
            os.close(fd)
        if root is not None:
            os.close(root)
        os.close(parent)


def materialize(raw, packet):
    """Production authority is fixed in trusted source, never caller-supplied."""
    registry = json.loads(
        (HERE / "setup-request-admissions.json").read_bytes(), object_pairs_hook=unique_object
    )
    _validate(raw, registry)
    packet_fd = _private_directory(packet)
    try:
        return _materialize_reviewed(
            raw, registry, lambda name, limit: _read_at(packet_fd, name, limit)
        )
    finally:
        os.close(packet_fd)


def inspect_materialized(path, request_sha256, manifest_sha256):
    """Structural same-source verification using externally retained identities.

    This never registers a native setup receipt. A completed owned process and
    reviewed actual setup evidence are still required by the separate authority.
    """
    output_path = Path(path)
    root = _private_directory(path)
    dirs = {}
    try:
        need(
            set(os.listdir(root)) == {"payload", "materialized.json"}, "incomplete materialization"
        )
        raw = _read_at(root, "materialized.json", REQUEST_LIMIT)
        need(
            stat.S_IMODE(os.stat("materialized.json", dir_fd=root, follow_symlinks=False).st_mode)
            == 0o400,
            "manifest file mode",
        )
        need(digest(raw) == manifest_sha256, "manifest identity")
        need(
            all(
                isinstance(v, str) and re.fullmatch("[a-f0-9]{64}", v)
                for v in (request_sha256, manifest_sha256)
            ),
            "expected identity format",
        )
        record = json.loads(raw, object_pairs_hook=unique_object)
        fields(
            record,
            "schema status kind request_sha256 files review_receipt_sha256 "
            "stager_identity setup_admitted native_execution_authorized",
        )
        need(
            record["schema"] == "opent1d.lt1-materialized-inventory/1"
            and record["status"] == "materialized"
            and record["kind"] in {"invented", "native"},
            "manifest schema",
        )
        need(
            record["request_sha256"] == request_sha256
            and record["stager_identity"] == source_identity(),
            "manifest source or request",
        )
        need(
            record["setup_admitted"] is False and record["native_execution_authorized"] is False,
            "manifest authority",
        )
        _path_inventory(record["files"])
        fields(record["review_receipt_sha256"], "rights security harness")
        need(
            all(
                isinstance(v, str) and re.fullmatch("[a-f0-9]{64}", v)
                for v in record["review_receipt_sha256"].values()
            ),
            "review receipt hash",
        )
        directories = {""} | {path.rpartition("/")[0] for path in record["files"] if "/" in path}
        directories |= {
            "/".join(path.split("/")[:i])
            for path in directories
            for i in range(1, len(path.split("/")))
        }
        dirs[""] = os.open(
            "payload", os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC, dir_fd=root
        )
        for path in sorted(directories - {""}, key=lambda p: (p.count("/"), p)):
            parent, _, name = path.rpartition("/")
            dirs[path] = os.open(
                name,
                os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC,
                dir_fd=dirs[parent],
            )
        need(
            all(
                os.fstat(fd).st_uid == os.getuid() and stat.S_IMODE(os.fstat(fd).st_mode) == 0o500
                for fd in dirs.values()
            ),
            "materialized directory mode",
        )
        for value in record["files"].values():
            fields(value, "input bytes sha256 mode")
            file_identity({k: value[k] for k in ("bytes", "sha256")})
            need(
                type(value["mode"]) is int and value["mode"] in {0o400, 0o500},
                "materialized file mode",
            )
        original = os.fstat(root)

        def check_namespace():
            live = output_path.lstat()
            need(
                output_path.resolve() == output_path
                and (live.st_dev, live.st_ino) == (original.st_dev, original.st_ino),
                "reader root changed",
            )
            _check_directory_bindings(root, dirs)
            need(
                all(
                    os.fstat(fd).st_uid == os.getuid()
                    and stat.S_IMODE(os.fstat(fd).st_mode) == 0o500
                    for fd in dirs.values()
                ),
                "materialized directory mode changed",
            )
            need(
                stat.S_IMODE(
                    os.stat("materialized.json", dir_fd=root, follow_symlinks=False).st_mode
                )
                == 0o400,
                "published inventory mode",
            )
            need(
                set(os.listdir(root)) == {"payload", "materialized.json"},
                "incomplete materialization",
            )

        need(
            sum(v["bytes"] for v in record["files"].values()) <= TOTAL_LIMIT,
            "materialized total bound",
        )
        _verify_payload(dirs, record["files"], check_namespace)
        need(
            _read_at(root, "materialized.json", REQUEST_LIMIT) == raw,
            "manifest changed during read",
        )
        check_namespace()
        return record
    finally:
        for fd in dirs.values():
            os.close(fd)
        os.close(root)
