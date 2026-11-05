"""One admitted original attempt tree, not recovery exclusion or sanitization.

Only fixed role names at depth zero/one are supported. Historical producer
identities are pinned data; this module never imports the native route.
"""

import ctypes
import errno
import hashlib
import json
import os
import stat
import sys
from pathlib import Path, PurePosixPath

from experiments.lt1_diagnostic import removal, retention
from experiments.lt1_diagnostic.control_identity import ROOT, host, identity
from experiments.lt1_diagnostic.frozen_setup import _private_directory, _read_at

HERE = Path(__file__).resolve().parent
NAMESPACE = HERE / "native_attempt_namespace.json"
AUTHORITY_FILES = {
    "experiments/lt1_diagnostic/" + n
    for n in (
        "native-admissions.json",
        "removal-admissions.json",
        "setup-request-admissions.json",
    )
}
SOURCE_FILES = (
    "experiments/lt1_diagnostic/native_tree_removal.py",
    "experiments/lt1_diagnostic/native_tree_removal_exec.py",
    "experiments/lt1_diagnostic/native_tree_removal_worker.py",
    "experiments/lt1_diagnostic/native_tree_reconciliation.py",
    "experiments/lt1_diagnostic/recovery_evidence.py",
    "experiments/lt1_diagnostic/native_attempt_namespace.json",
    "tests/lt1_native_tree_worker.py",
)
LIMIT = 1024 * 1024
JOURNAL_LIMIT = 2 * LIMIT
AUTHORITY = {
    **removal.AUTHORITY,
    "physical_sanitization_verified": False,
    "absence_time_established": False,
    "ordinary_restore_excluded": False,
}
DIR_FIELDS = "device inode uid mode mtime_ns ctime_ns"
STABLE_DIR = ("device", "inode", "uid", "mode")
FILE_FIELDS = "device inode uid bytes mode mtime_ns ctime_ns sha256"


def need(ok, reason):
    if not ok:
        raise ValueError("LT1 native tree removal refused: " + reason)


def encoded(value):
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"), allow_nan=False).encode()


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def decoded(raw, expected=None, limit=LIMIT):
    need(type(raw) is bytes and 0 < len(raw) <= limit, "bounded bytes")
    if expected is not None:
        need(retention.sha(expected) and digest(raw) == expected, "external byte identity")
    value = json.loads(raw, object_pairs_hook=removal.unique_object)
    need(encoded(value) == raw, "canonical control bytes")
    return value


def source_identity():
    value = identity(__file__)
    for name in (*SOURCE_FILES, *sorted(AUTHORITY_FILES)):
        value["implementation"][name] = digest((ROOT / name).read_bytes())
    return value


def code_source(audit):
    _producer(audit)
    need(AUTHORITY_FILES <= audit["implementation"].keys(), "complete current authority audit")
    return {
        **audit,
        "implementation": {
            name: value
            for name, value in audit["implementation"].items()
            if name not in AUTHORITY_FILES
        },
    }


def registry():
    value = json.loads(
        (HERE / "removal-admissions.json").read_bytes(), object_pairs_hook=removal.unique_object
    )
    retention.fields(value, "schema requests")
    need(
        value["schema"] == "opent1d.lt1-removal-admissions/1"
        and type(value["requests"]) is list
        and len(value["requests"]) <= 4096
        and all(retention.sha(v) for v in value["requests"])
        and len(set(value["requests"])) == len(value["requests"]),
        "canonical removal registry",
    )
    return value


def admitted(raw, grants):
    # No caller context, source identity, path or process is touched first.
    retention.fields(grants, "schema requests")
    need(
        grants["schema"] == "opent1d.lt1-removal-admissions/1"
        and type(grants["requests"]) is list
        and type(raw) is bytes
        and 0 < len(raw) <= LIMIT
        and digest(raw) in grants["requests"],
        "no exact reviewed tree-removal request",
    )


def _directory(record, *, path=False, native_packet=False):
    retention.fields(record, DIR_FIELDS + (" path" if path else ""))
    need(
        all(type(record[k]) is int and record[k] >= 0 for k in DIR_FIELDS.split())
        and record["mode"] == (0o500 if native_packet else 0o700)
        and record["uid"] == os.getuid(),
        "private directory identity",
    )
    if path:
        value = record["path"]
        need(
            type(value) is str
            and 0 < len(value) <= 1024
            and PurePosixPath(value).is_absolute()
            and str(PurePosixPath(value)) == value
            and ".." not in PurePosixPath(value).parts
            and "\0" not in value,
            "absolute canonical directory path",
        )


def _producer(value):
    retention.fields(value, "implementation python executable_sha256")
    need(
        type(value["implementation"]) is dict
        and 0 < len(value["implementation"]) <= 4096
        and all(
            type(name) is str
            and 0 < len(name) <= 512
            and not name.startswith("/")
            and not any(part in ("", ".", "..") for part in name.split("/"))
            and "\\" not in name
            and "\0" not in name
            and retention.sha(sha)
            for name, sha in value["implementation"].items()
        )
        and type(value["python"]) is str
        and 0 < len(value["python"]) <= 64
        and retention.sha(value["executable_sha256"]),
        "historical producer data, not current-code authority",
    )


def request(raw, context_raw, audit, *, invented=False):
    value = decoded(raw)
    retention.fields(
        value,
        "schema kind role subject copy allocation_sha256 root parent cleanup_parent "
        "attempt inventory code_source host context_sha256 producer",
    )
    need(
        value["schema"] == "opent1d.lt1-native-tree-removal-request/1"
        and value["kind"] == ("invented" if invented else "private-data")
        and type(value["role"]) is str,
        "request schema/origin/role",
    )
    namespace = json.loads(NAMESPACE.read_bytes(), object_pairs_hook=removal.unique_object)
    retention.fields(namespace, "schema roles")
    need(namespace["schema"] == "opent1d.lt1-attempt-namespace/1", "fixed namespace version")
    need(value["role"] in namespace["roles"], "fixed role")
    role = namespace["roles"][value["role"]]
    for key in ("subject", "copy", "attempt"):
        retention.identifier(value[key])
    need(retention.sha(value["allocation_sha256"]), "allocated copy identity")
    need(
        type(context_raw) is bytes
        and len(context_raw) <= LIMIT
        and digest(context_raw) == value["context_sha256"]
        and value["host"] == host()
        and value["code_source"] == code_source(audit)
        and audit == source_identity(),
        "context/current code/host identity",
    )
    _producer(value["producer"])
    for key in ("root", "parent", "cleanup_parent"):
        _directory(
            value[key], path=True, native_packet=key == "root" and value["role"] == "native-packet"
        )
    root, parent, cleanup = (Path(value[k]["path"]) for k in ("root", "parent", "cleanup_parent"))
    need(
        root.parent == parent
        and root != parent
        and not root.is_relative_to(cleanup)
        and not cleanup.is_relative_to(root),
        "separate cleanup parent and exact original parent",
    )
    removal.safe_name(root.name)
    inventory = value["inventory"]
    retention.fields(inventory, "files directories")
    files, directories = inventory["files"], inventory["directories"]
    need(type(files) is dict and type(directories) is dict, "closed inventory maps")
    if value["role"] == "native-packet":
        need(set(files) == set(role["files"]) and not directories, "exact native packet members")
    need(len(files) + len(directories) <= 128, "inventory count")
    need(set(directories) <= set(role["directories"]), "known depth-one directories")
    for name, record in directories.items():
        _directory(record)
    for name, record in files.items():
        need(type(name) is str, "leaf name type")
        parts = name.split("/")
        need(
            (len(parts) == 1 and name in role["files"])
            or (
                len(parts) == 2
                and parts[0] in directories
                and parts[1] in role["directories"][parts[0]]
            ),
            "known fixed-depth leaf",
        )
        retention.fields(record, FILE_FIELDS)
        need(
            all(type(record[k]) is int and record[k] >= 0 for k in FILE_FIELDS.split()[:-1])
            and record["uid"] == os.getuid()
            and record["mode"] in ((0o400,) if value["role"] == "native-packet" else (0o400, 0o600))
            and record["bytes"] <= removal.FILE_LIMIT
            and retention.sha(record["sha256"]),
            "private bounded file identity",
        )
    need(sum(v["bytes"] for v in files.values()) <= removal.TOTAL_LIMIT, "aggregate bytes")
    return value


def directory_signature(info):
    return {k: v for k, v in removal.signature(info).items() if k != "bytes"}


def present(folder, name):
    try:
        os.stat(name, dir_fd=folder, follow_symlinks=False)
        return True
    except FileNotFoundError:
        return False


def _quarantine_path(request, raw):
    if request["role"] == "native-packet":
        # A read-only directory cannot change parent on supported hosts. The
        # canonical request bytes select one fixed, exclusive sibling name.
        return Path(request["parent"]["path"]) / ("lt1-packet-" + digest(raw))
    return Path(request["cleanup_parent"]["path"]) / request["attempt"] / "target"


def _rename(source_parent, source, target_parent, target):
    """The platform no-replace primitive, relative to held parent descriptors."""
    library = ctypes.CDLL(None, use_errno=True)
    if sys.platform == "darwin":
        function, flag = library.renameatx_np, 4
    elif sys.platform.startswith("linux"):
        function, flag = library.renameat2, 1
    else:
        raise ValueError("Atomic descriptor-relative exclusive rename unavailable")
    function.argtypes = [
        ctypes.c_int,
        ctypes.c_char_p,
        ctypes.c_int,
        ctypes.c_char_p,
        ctypes.c_uint,
    ]
    function.restype = ctypes.c_int
    result = function(source_parent, os.fsencode(source), target_parent, os.fsencode(target), flag)
    if result:
        number = ctypes.get_errno()
        need(number not in (errno.EEXIST, errno.ENOTEMPTY), "quarantine appeared")
        raise OSError(number, os.strerror(number))


def bind(path, fd, expected, *, initial=False):
    # The historical flat helper only accepts 0700. This binding additionally
    # supports the source-fixed immutable packet root before its transition.
    path = Path(path)
    live, opened = path.lstat(), os.fstat(fd)
    need(
        path.resolve() == path
        and stat.S_ISDIR(live.st_mode)
        and (live.st_dev, live.st_ino) == (opened.st_dev, opened.st_ino)
        and opened.st_uid == os.getuid()
        and expected["mode"] in (0o500, 0o700)
        and stat.S_IMODE(opened.st_mode) == expected["mode"],
        "directory binding or fixed mode",
    )
    actual = directory_signature(os.fstat(fd))
    keys = DIR_FIELDS.split() if initial else STABLE_DIR
    need(all(actual[k] == expected[k] for k in keys), "directory changed")


def _open_directory(parent, name, expected, *, initial=False):
    fd = os.open(name, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC, dir_fd=parent)
    try:
        opened = os.fstat(fd)
        named = os.stat(name, dir_fd=parent, follow_symlinks=False)
        keys = DIR_FIELDS.split() if initial else STABLE_DIR
        need(
            stat.S_ISDIR(named.st_mode)
            and directory_signature(opened) == directory_signature(named)
            and all(directory_signature(opened)[k] == expected[k] for k in keys),
            "directory name/open binding",
        )
        return fd
    except BaseException:
        os.close(fd)
        raise


def _tree(root, inventory, *, removed=(), removed_dirs=(), initial=False):
    """Validate exact remaining tree and close every temporary content descriptor."""
    files = {k: v for k, v in inventory["files"].items() if k not in removed}
    directories = {k: v for k, v in inventory["directories"].items() if k not in removed_dirs}
    need(
        removal.names(root) == {n for n in files if "/" not in n} | set(directories),
        "exact root namespace",
    )
    for name, expected in files.items():
        if "/" not in name:
            os.close(removal._file(root, name, expected))
    for name, expected in directories.items():
        fd = _open_directory(root, name, expected, initial=initial)
        try:
            leaves = {n.split("/")[1]: v for n, v in files.items() if n.startswith(name + "/")}
            need(removal.names(fd) == set(leaves), "exact session namespace")
            for leaf, record in leaves.items():
                os.close(removal._file(fd, leaf, record))
        finally:
            os.close(fd)


class Interrupted(Exception):
    pass


def _remove_reviewed(
    raw,
    grants,
    context_raw,
    audit,
    *,
    invented=False,
    stop=lambda: False,
    checkpoint=lambda *_: None,
):
    """Trusted fixture boundary; production exposes no registry/checkpoint selector."""
    admitted(raw, grants)
    r = request(raw, context_raw, audit, invented=invented)
    if stop():
        return {"status": "interrupted", "attempt_created": False, **AUTHORITY}
    root_path, parent_path, cleanup_path = (
        Path(r[k]["path"]) for k in ("root", "parent", "cleanup_parent")
    )
    quarantine_path = _quarantine_path(r, raw)
    parent = cleanup = attempt = root = journal = None
    removed, removed_dirs, recorded_removed, recorded_dirs = [], [], [], []
    moved = root_removed = packet_writable = False
    try:
        parent, cleanup = _private_directory(parent_path), _private_directory(cleanup_path)
        bind(parent_path, parent, r["parent"])
        bind(cleanup_path, cleanup, r["cleanup_parent"])
        need(os.fstat(parent).st_dev == os.fstat(cleanup).st_dev, "same filesystem")
        if r["role"] == "native-packet":
            need(not present(parent, quarantine_path.name), "packet quarantine appeared")
        root = _open_directory(parent, root_path.name, r["root"], initial=True)
        _tree(root, r["inventory"], initial=True)
        need(source_identity() == audit, "source before evidence creation")
        os.mkdir(r["attempt"], 0o700, dir_fd=cleanup)
        os.fsync(cleanup)
        attempt_path = cleanup_path / r["attempt"]
        attempt = _private_directory(attempt_path)
        quarantine_parent = parent if r["role"] == "native-packet" else attempt
        attempt_identity = directory_signature(os.fstat(attempt))
        journal = os.open(
            "events.jsonl",
            os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW | os.O_CLOEXEC,
            0o600,
            dir_fd=attempt,
        )
        os.fsync(attempt)
        journal_identity = os.fstat(journal)

        def append(value):
            line = encoded(value) + b"\n"
            need(os.fstat(journal).st_size + len(line) <= JOURNAL_LIMIT, "journal bound")
            view = memoryview(line)
            while view:
                count = os.write(journal, view)
                need(count > 0, "journal write")
                view = view[count:]
            os.fsync(journal)

        def guard(phase):
            checkpoint(phase)
            if stop():
                raise Interrupted("actual worker cancellation")
            need(source_identity() == audit, "current source changed")
            if not invented:
                admitted(raw, registry())
            bind(parent_path, parent, r["parent"])
            bind(cleanup_path, cleanup, r["cleanup_parent"])
            bind(attempt_path, attempt, attempt_identity)
            named = os.stat("events.jsonl", dir_fd=attempt, follow_symlinks=False)
            opened = os.fstat(journal)
            need(
                stat.S_ISREG(named.st_mode)
                and named.st_nlink == opened.st_nlink == 1
                and named.st_uid == opened.st_uid == os.getuid()
                and stat.S_IMODE(named.st_mode) == stat.S_IMODE(opened.st_mode) == 0o600
                and (named.st_dev, named.st_ino)
                == (journal_identity.st_dev, journal_identity.st_ino)
                == (opened.st_dev, opened.st_ino),
                "journal descriptor/name binding",
            )
            need(
                removal.names(attempt, 2)
                == {"events.jsonl"}
                | (
                    {"target"}
                    if r["role"] != "native-packet" and moved and not root_removed
                    else set()
                ),
                "attempt namespace",
            )
            if not root_removed:
                target = quarantine_path if moved else root_path
                expected_root = {**r["root"], "mode": 0o700} if packet_writable else r["root"]
                bind(target, root, expected_root, initial=not moved)
                _tree(root, r["inventory"], removed=removed, removed_dirs=removed_dirs)
            need(present(parent, root_path.name) is (not moved), "original namespace phase")
            need(
                present(quarantine_parent, quarantine_path.name) is (moved and not root_removed),
                "quarantine namespace phase",
            )

        append(
            {
                "event": "prepared",
                "request_sha256": digest(raw),
                "audit_sha256": digest(encoded(audit)),
                **AUTHORITY,
            }
        )
        status, error = "namespace-absence-observed", None
        try:
            guard("prepared")
            # Both named parents and original tree were bound immediately above.
            _rename(parent, root_path.name, quarantine_parent, quarantine_path.name)
            moved = True
            os.fsync(parent)
            if quarantine_parent != parent:
                os.fsync(quarantine_parent)
            checkpoint("after-rename-before-journal")
            append({"event": "quarantined"})
            guard("quarantined")
            if r["role"] == "native-packet":
                # No path chmod or caller mode: the exclusively quarantined FD
                # has just been bound in its original fixed 0500 mode.
                os.fchmod(root, 0o700)
                packet_writable = True
                os.fsync(root)
                checkpoint("after-packet-chmod-before-journal")
                append({"event": "packet-writable"})
                guard("packet-writable")
            for name, expected in sorted(r["inventory"]["files"].items()):
                guard("before-unlink:" + name)
                parts = name.split("/")
                folder = root
                opened = None
                try:
                    if len(parts) == 2:
                        opened = _open_directory(
                            root, parts[0], r["inventory"]["directories"][parts[0]]
                        )
                        folder = opened
                    content = removal._file(folder, parts[-1], expected)
                    try:
                        # Last name/open proof is inside _file; no callback before unlink.
                        os.unlink(parts[-1], dir_fd=folder)
                        removed.append(name)
                        os.fsync(folder)
                    finally:
                        os.close(content)
                finally:
                    if opened is not None:
                        os.close(opened)
                checkpoint("after-unlink-before-journal:" + name)
                append({"event": "removed", "name": name})
                recorded_removed.append(name)
                guard("removed:" + name)
            for name, expected in sorted(r["inventory"]["directories"].items()):
                guard("before-rmdir:" + name)
                fd = _open_directory(root, name, expected)
                try:
                    need(not removal.names(fd), "session still empty")
                    os.rmdir(name, dir_fd=root)
                    removed_dirs.append(name)
                    os.fsync(root)
                finally:
                    os.close(fd)
                checkpoint("after-rmdir-before-journal:" + name)
                append({"event": "directory-removed", "name": name})
                recorded_dirs.append(name)
            guard("before-root-rmdir")
            need(not removal.names(root), "quarantined root empty")
            os.rmdir(quarantine_path.name, dir_fd=quarantine_parent)
            root_removed = True
            os.fsync(quarantine_parent)
            os.close(root)
            root = None
            checkpoint("after-root-rmdir-before-journal")
            append({"event": "root-removed"})
            guard("before-finish")
        except (OSError, ValueError, Interrupted) as exc:
            status = "interrupted" if isinstance(exc, Interrupted) else "failed"
            error = type(exc).__name__ + ": " + str(exc)[:500]
        # Content and removed-root FDs are closed before any completion claim.
        if root is not None:
            os.close(root)
            root = None
        append(
            {
                "event": "finished",
                "status": status,
                "error": error,
                "removed": recorded_removed,
                "directories_removed": recorded_dirs,
                "original_present": present(parent, root_path.name),
                "quarantine_present": present(quarantine_parent, quarantine_path.name),
                **AUTHORITY,
            }
        )
        return {
            "status": status,
            "attempt_created": True,
            "removed": removed,
            "directories_removed": removed_dirs,
            **AUTHORITY,
        }
    finally:
        for fd in (journal, root, attempt, cleanup, parent):
            if fd is not None:
                os.close(fd)


def _observed_tree(root, inventory, recorded_removed, recorded_dirs, *, initial=False):
    """Missing unrecorded objects are crash gaps, never fabricated journal events."""
    dirs, files = inventory["directories"], inventory["files"]
    observed_files, observed_dirs = [], []
    names = removal.names(root)
    need(names <= {n for n in files if "/" not in n} | set(dirs), "unknown root entry")
    need(not set(recorded_dirs) & names, "recorded removed directory reappeared")
    for name in sorted(names):
        if name in dirs:
            fd = _open_directory(root, name, dirs[name], initial=initial)
            try:
                leaves = removal.names(fd)
                allowed = {n.split("/")[1] for n in files if n.startswith(name + "/")}
                need(leaves <= allowed, "unknown session entry")
                observed_dirs.append(name)
                for leaf in sorted(leaves):
                    key = name + "/" + leaf
                    need(key not in recorded_removed, "recorded removed file reappeared")
                    os.close(removal._file(fd, leaf, files[key]))
                    observed_files.append(key)
            finally:
                os.close(fd)
        else:
            need(name not in recorded_removed, "recorded removed file reappeared")
            os.close(removal._file(root, name, files[name]))
            observed_files.append(name)
    return observed_files, observed_dirs


def inspect(
    raw,
    expected_request_sha256,
    context_raw,
    expected_journal_sha256,
    outer_receipt,
    *,
    expected_outer_sha256,
    audit,
    expected_audit_sha256,
    reader_audit,
    invented=False,
):
    """Strict retained prefix and both parent namespaces; never resume or admit."""
    decoded(raw, expected_request_sha256)
    need(
        type(outer_receipt) in (dict, type(None))
        and len(encoded(outer_receipt)) <= LIMIT
        and retention.sha(expected_outer_sha256)
        and digest(encoded(outer_receipt)) == expected_outer_sha256,
        "external actual outer identity",
    )
    # The full production audit in the journal is historical, externally pinned
    # data. Withdrawal of authority never requires reinstating it for readback.
    _producer(audit)
    need(
        digest(encoded(audit)) == expected_audit_sha256 and retention.sha(expected_audit_sha256),
        "external producer audit",
    )
    need(code_source(audit) == code_source(reader_audit), "producer/current reader code projection")
    r = request(raw, context_raw, reader_audit, invented=invented)
    root_path, parent_path, cleanup_path = (
        Path(r[k]["path"]) for k in ("root", "parent", "cleanup_parent")
    )
    quarantine_path = _quarantine_path(r, raw)
    parent = cleanup = attempt = root = None
    try:
        parent, cleanup = _private_directory(parent_path), _private_directory(cleanup_path)
        bind(parent_path, parent, r["parent"])
        bind(cleanup_path, cleanup, r["cleanup_parent"])
        attempt_path = cleanup_path / r["attempt"]
        if not present(cleanup, r["attempt"]):
            if r["role"] == "native-packet":
                need(
                    not present(parent, quarantine_path.name),
                    "unstarted packet quarantine appeared",
                )
            need(expected_journal_sha256 == digest(b""), "missing attempt has no journal")
            root = _open_directory(parent, root_path.name, r["root"], initial=True)
            _tree(root, r["inventory"], initial=True)
            if r["role"] != "native-packet":
                os.close(root)
                root = None
            bind(parent_path, parent, r["parent"])
            bind(cleanup_path, cleanup, r["cleanup_parent"])
            need(
                not present(cleanup, r["attempt"]) and source_identity() == reader_audit,
                "unstarted evidence changed",
            )
            if r["role"] == "native-packet":
                bind(parent_path, parent, r["parent"])
                bind(cleanup_path, cleanup, r["cleanup_parent"])
                bind(root_path, root, r["root"], initial=True)
                need(
                    not present(parent, quarantine_path.name)
                    and not present(cleanup, r["attempt"]),
                    "late unstarted packet namespace changed",
                )
                os.close(root)
                root = None
            return {
                "schema": "opent1d.lt1-native-tree-removal-readback/1",
                "status": "incomplete",
                "role": r["role"],
                "subject": r["subject"],
                "copy": r["copy"],
                "request_sha256": digest(raw),
                "journal_sha256": digest(b""),
                "producer_audit_sha256": expected_audit_sha256,
                "reader_audit_sha256": digest(encoded(reader_audit)),
                "removed": [],
                "directories_removed": [],
                "original_present": True,
                "quarantine_present": False,
                "unrecorded_mutations": [],
                "truncated": False,
                "outer_complete": False,
                "prepared": False,
                **(
                    {"packet_mode": {"writable_recorded": False, "observed": 0o500}}
                    if r["role"] == "native-packet"
                    else {}
                ),
                **AUTHORITY,
            }
        attempt = _private_directory(attempt_path)
        quarantine_parent = parent if r["role"] == "native-packet" else attempt
        attempt_identity = directory_signature(os.fstat(attempt))
        allowed_attempt = {"events.jsonl"} | ({"target"} if r["role"] != "native-packet" else set())
        need(removal.names(attempt, 2) <= allowed_attempt, "reader attempt namespace")
        journal = (
            _read_at(attempt, "events.jsonl", JOURNAL_LIMIT)
            if present(attempt, "events.jsonl")
            else b""
        )
        need(
            retention.sha(expected_journal_sha256) and digest(journal) == expected_journal_sha256,
            "external journal identity",
        )
        journal_stat = (
            os.stat("events.jsonl", dir_fd=attempt, follow_symlinks=False)
            if present(attempt, "events.jsonl")
            else None
        )
        if journal_stat is not None:
            need(
                stat.S_IMODE(journal_stat.st_mode) == 0o600
                and journal_stat.st_uid == os.getuid()
                and journal_stat.st_nlink == 1,
                "private journal",
            )
        lines = journal.splitlines(keepends=True)
        truncated = bool(lines and not lines[-1].endswith(b"\n"))
        if truncated:
            lines.pop()
        events = [decoded(line[:-1]) for line in lines]
        if events:
            need(
                events[0]
                == {
                    "event": "prepared",
                    "request_sha256": digest(raw),
                    "audit_sha256": digest(encoded(audit)),
                    **AUTHORITY,
                },
                "prepared journal identity",
            )
        else:
            need(
                not present(quarantine_parent, quarantine_path.name)
                and present(parent, root_path.name),
                "unprepared original tree",
            )
        moved = root_removed = packet_writable = False
        removed, directories, terminal = [], [], None
        for e in events[1:]:
            need(terminal is None and type(e) is dict, "event after terminal")
            event = e.get("event")
            if event == "quarantined":
                retention.fields(e, "event")
                need(not moved, "duplicate quarantine")
                moved = True
            elif event == "packet-writable":
                retention.fields(e, "event")
                need(
                    r["role"] == "native-packet"
                    and moved
                    and not packet_writable
                    and not root_removed
                    and not removed
                    and not directories,
                    "packet mode event order",
                )
                packet_writable = True
            elif event == "removed":
                retention.fields(e, "event name")
                name = e["name"]
                need(
                    moved
                    and (r["role"] != "native-packet" or packet_writable)
                    and not root_removed
                    and type(name) is str
                    and name in r["inventory"]["files"]
                    and name not in removed
                    and not directories
                    and name == sorted(r["inventory"]["files"])[len(removed)],
                    "file event order",
                )
                removed.append(name)
            elif event == "directory-removed":
                retention.fields(e, "event name")
                name = e["name"]
                need(
                    moved
                    and not root_removed
                    and set(removed) == set(r["inventory"]["files"])
                    and type(name) is str
                    and name in r["inventory"]["directories"]
                    and name not in directories
                    and name == sorted(r["inventory"]["directories"])[len(directories)],
                    "directory event order",
                )
                directories.append(name)
            elif event == "root-removed":
                retention.fields(e, "event")
                need(
                    moved
                    and (r["role"] != "native-packet" or packet_writable)
                    and not root_removed
                    and set(removed) == set(r["inventory"]["files"])
                    and set(directories) == set(r["inventory"]["directories"]),
                    "root event order",
                )
                root_removed = True
            else:
                retention.fields(
                    e,
                    "event status error removed directories_removed "
                    "original_present quarantine_present " + " ".join(AUTHORITY),
                )
                need(
                    event == "finished"
                    and e["status"] in ("namespace-absence-observed", "failed", "interrupted")
                    and (
                        e["error"] is None
                        or (type(e["error"]) is str and 0 < len(e["error"]) <= 1024)
                    )
                    and e["removed"] == removed
                    and e["directories_removed"] == directories
                    and type(e["original_present"]) is bool
                    and type(e["quarantine_present"]) is bool
                    and all(e[k] is v for k, v in AUTHORITY.items()),
                    "terminal schema/replay",
                )
                if e["status"] == "namespace-absence-observed":
                    need(
                        root_removed
                        and e["error"] is None
                        and not e["original_present"]
                        and not e["quarantine_present"],
                        "completed terminal contradiction",
                    )
                terminal = e
        original_present = present(parent, root_path.name)
        quarantine_present = present(quarantine_parent, quarantine_path.name)
        need(not (original_present and quarantine_present), "two target namespaces")
        need(
            not (moved and original_present) and not (root_removed and quarantine_present),
            "recorded namespace contradiction",
        )
        observed_files, observed_dirs = [], []
        observed_mode = None
        mode_gap = False
        if original_present or quarantine_present:
            folder, name = (
                (parent, root_path.name)
                if original_present
                else (quarantine_parent, quarantine_path.name)
            )
            expected_root = r["root"]
            if r["role"] == "native-packet":
                observed_mode = stat.S_IMODE(
                    os.stat(name, dir_fd=folder, follow_symlinks=False).st_mode
                )
                if quarantine_present:
                    need(observed_mode in (0o500, 0o700), "fixed quarantined packet mode")
                    need(
                        not packet_writable or observed_mode == 0o700,
                        "recorded packet mode contradiction",
                    )
                    mode_gap = observed_mode == 0o700 and not packet_writable
                    expected_root = {**r["root"], "mode": observed_mode}
            root = _open_directory(folder, name, expected_root, initial=original_present)
            observed_files, observed_dirs = _observed_tree(
                root, r["inventory"], removed, directories, initial=original_present
            )
            if r["role"] != "native-packet":
                os.close(root)
                root = None
        if terminal is not None:
            need(
                terminal["original_present"] == original_present
                and terminal["quarantine_present"] == quarantine_present,
                "terminal namespace changed",
            )
        expected_files = set(r["inventory"]["files"]) - set(removed)
        expected_dirs = set(r["inventory"]["directories"]) - set(directories)
        gaps = sorted(expected_files - set(observed_files)) + sorted(
            expected_dirs - set(observed_dirs)
        )
        if not moved and quarantine_present:
            gaps.append("root-rename")
        if moved and not root_removed and not quarantine_present:
            gaps.append("root-rmdir")
        if not moved and not original_present and not quarantine_present:
            gaps.append("unobserved-root-absence")
        if mode_gap:
            gaps.append("packet-mode")
        from experiments.lt1_diagnostic import native_tree_removal_exec as runner

        outer_ok = runner.complete_outer(outer_receipt, raw, r, context_raw, audit)
        if outer_ok:
            outer_ok = bool(
                journal_stat is not None
                and outer_receipt["journal"]
                == {
                    "sha256": digest(journal),
                    "identity": removal.signature(journal_stat),
                }
            )
        complete = bool(
            terminal
            and terminal["status"] == "namespace-absence-observed"
            and root_removed
            and not original_present
            and not quarantine_present
            and not truncated
            and not gaps
            and outer_ok
        )
        if r["role"] == "native-packet":
            need(source_identity() == reader_audit, "reader current source changed")
        for path, fd, expected in (
            (parent_path, parent, r["parent"]),
            (cleanup_path, cleanup, r["cleanup_parent"]),
            (attempt_path, attempt, attempt_identity),
        ):
            bind(path, fd, expected)
        if journal_stat is not None:
            need(
                _read_at(attempt, "events.jsonl", JOURNAL_LIMIT) == journal,
                "journal changed during readback",
            )
            need(
                removal.signature(os.stat("events.jsonl", dir_fd=attempt, follow_symlinks=False))
                == removal.signature(journal_stat),
                "journal replaced during readback",
            )
        else:
            need(not present(attempt, "events.jsonl"), "missing journal appeared")
        if r["role"] != "native-packet":
            need(source_identity() == reader_audit, "reader current source changed")
        if root is not None:
            bind(
                root_path if original_present else quarantine_path,
                root,
                expected_root,
                initial=original_present,
            )
            need(
                _observed_tree(root, r["inventory"], removed, directories, initial=original_present)
                == (observed_files, observed_dirs),
                "late packet tree changed",
            )
        need(
            present(parent, root_path.name) == original_present
            and present(quarantine_parent, quarantine_path.name) == quarantine_present,
            "late target namespace changed",
        )
        if root is not None:
            os.close(root)
            root = None
        return {
            "schema": "opent1d.lt1-native-tree-removal-readback/1",
            "status": "completed" if complete else "incomplete",
            "role": r["role"],
            "subject": r["subject"],
            "copy": r["copy"],
            "request_sha256": digest(raw),
            "producer_audit_sha256": expected_audit_sha256,
            "reader_audit_sha256": digest(encoded(reader_audit)),
            "journal_sha256": digest(journal),
            "removed": removed,
            "directories_removed": directories,
            "original_present": original_present,
            "quarantine_present": quarantine_present,
            "unrecorded_mutations": gaps,
            "truncated": truncated,
            "outer_complete": outer_ok,
            "prepared": bool(events),
            **(
                {"packet_mode": {"writable_recorded": packet_writable, "observed": observed_mode}}
                if r["role"] == "native-packet"
                else {}
            ),
            **AUTHORITY,
        }
    finally:
        for fd in (root, attempt, cleanup, parent):
            if fd is not None:
                os.close(fd)
