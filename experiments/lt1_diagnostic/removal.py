"""Closed-inventory quarantine/removal; not backup or physical erasure proof."""

import hashlib
import json
import os
import re
import stat
from pathlib import Path

from experiments.durable_archives.storage import exclusive_rename
from experiments.lt1_diagnostic.archive_preflight import digest, unique_object
from experiments.lt1_diagnostic.control_identity import host, identity
from experiments.lt1_diagnostic.frozen_setup import _private_directory, _read_at
from experiments.lt1_diagnostic.retention import fields, sha

HERE = Path(__file__).resolve().parent
REQUEST_LIMIT = 1024 * 1024
JOURNAL_LIMIT = 2 * 1024 * 1024
MAX_FILES = 128
FILE_LIMIT = 16 * 1024 * 1024
TOTAL_LIMIT = 32 * 1024 * 1024
AUTHORITY = {
    "effective_erasure_verified": False,
    "setup_admitted": False,
    "native_execution_authorized": False,
    "new_authority_granted": False,
}


def need(ok, reason):
    if not ok:
        raise ValueError("LT1 removal refused: " + reason)


def source_identity():
    return identity(__file__)


def safe_name(name):
    need(
        isinstance(name, str)
        and re.fullmatch("[a-z0-9][a-z0-9.-]{0,63}", name)
        and not name.endswith("."),
        "flat name",
    )


def names(fd, limit=MAX_FILES):
    result = set()
    with os.scandir(fd) as entries:
        for item in entries:
            result.add(item.name)
            need(len(result) <= limit, "namespace bound")
    return result


def signature(info):
    return {
        "device": info.st_dev,
        "inode": info.st_ino,
        "uid": info.st_uid,
        "bytes": info.st_size,
        "mode": stat.S_IMODE(info.st_mode),
        "mtime_ns": info.st_mtime_ns,
        "ctime_ns": info.st_ctime_ns,
    }


def _request(raw, context_raw):
    need(isinstance(raw, bytes) and len(raw) <= REQUEST_LIMIT, "request bound")
    request = json.loads(raw, object_pairs_hook=unique_object)
    fields(
        request,
        "schema kind root evidence_parent attempt files source_identity host context_sha256",
    )
    need(
        request["schema"] == "opent1d.lt1-removal-request/1"
        and request["kind"] in {"invented", "private-data"},
        "request schema",
    )
    need(
        request["host"] == host() and request["source_identity"] == source_identity(),
        "host or source",
    )
    need(
        isinstance(context_raw, bytes)
        and len(context_raw) <= REQUEST_LIMIT
        and sha(request["context_sha256"])
        and digest(context_raw) == request["context_sha256"],
        "review context",
    )
    fields(request["root"], "path device inode uid")
    for key in ("device", "inode", "uid"):
        need(type(request["root"][key]) is int and request["root"][key] >= 0, "root identity")
    for path in (request["root"]["path"], request["evidence_parent"]):
        need(
            isinstance(path, str) and len(path) <= 1024 and Path(path).is_absolute(),
            "absolute path",
        )
    safe_name(request["attempt"])
    files = request["files"]
    need(isinstance(files, dict) and 0 < len(files) <= MAX_FILES, "file count")
    for name, record in files.items():
        safe_name(name)
        fields(record, "device inode uid bytes mode mtime_ns ctime_ns sha256")
        need(
            all(
                type(record[key]) is int and record[key] >= 0
                for key in ("device", "inode", "uid", "bytes", "mode", "mtime_ns", "ctime_ns")
            ),
            "file identity",
        )
        need(
            record["bytes"] <= FILE_LIMIT
            and record["mode"] in {0o400, 0o600}
            and record["uid"] == os.getuid()
            and sha(record["sha256"]),
            "file policy",
        )
    need(sum(r["bytes"] for r in files.values()) <= TOTAL_LIMIT, "aggregate bytes")
    return request


def _admitted(raw, registry):
    fields(registry, "schema requests")
    need(
        registry["schema"] == "opent1d.lt1-removal-admissions/1"
        and isinstance(registry["requests"], list),
        "fixed removal authority",
    )
    need(
        isinstance(raw, bytes)
        and len(raw) <= REQUEST_LIMIT
        and digest(raw) in registry["requests"],
        "no reviewed removal request",
    )


def _binding(path, fd):
    path = Path(path)
    live, opened = path.lstat(), os.fstat(fd)
    need(
        path.resolve() == path
        and stat.S_ISDIR(live.st_mode)
        and (live.st_dev, live.st_ino) == (opened.st_dev, opened.st_ino)
        and opened.st_uid == os.getuid()
        and stat.S_IMODE(opened.st_mode) == 0o700,
        "directory binding or mode",
    )


def _file(folder, name, expected, *, moved=False):
    fd = os.open(name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK | os.O_CLOEXEC, dir_fd=folder)
    try:
        start = os.fstat(fd)
        need(stat.S_ISREG(start.st_mode) and start.st_nlink == 1, "single-link regular file")
        want = {
            k: v for k, v in expected.items() if k != "sha256" and (not moved or k != "ctime_ns")
        }
        need(
            {k: v for k, v in signature(start).items() if k in want} == want,
            "file identity changed",
        )
        checksum, count = hashlib.sha256(), 0
        while part := os.read(fd, min(1024 * 1024, expected["bytes"] + 1 - count)):
            count += len(part)
            need(count <= expected["bytes"], "file grew")
            checksum.update(part)
        live = os.stat(name, dir_fd=folder, follow_symlinks=False)
        need(
            signature(start) == signature(os.fstat(fd)) == signature(live)
            and live.st_nlink == 1
            and count == expected["bytes"]
            and checksum.hexdigest() == expected["sha256"],
            "file bytes or binding changed",
        )
        return fd
    except BaseException:
        os.close(fd)
        raise


def _remove_reviewed(raw, registry, context_raw, *, stop=lambda: False, checkpoint=lambda *_: None):
    """Trusted fixture injection, not isolation from a hostile same-user process."""
    _admitted(raw, registry)
    request = _request(raw, context_raw)
    if stop():
        return {"status": "interrupted", "attempt_created": False, "removed": [], **AUTHORITY}
    root_path, evidence_path = Path(request["root"]["path"]), Path(request["evidence_parent"])
    need(
        not root_path.is_relative_to(evidence_path) and not evidence_path.is_relative_to(root_path),
        "separate evidence root",
    )
    root, evidence, attempt, quarantine, journal = (
        _private_directory(root_path),
        None,
        None,
        None,
        None,
    )
    original_fds, removed = {}, []
    try:
        evidence = _private_directory(evidence_path)
        need(os.fstat(root).st_dev == os.fstat(evidence).st_dev, "same filesystem")
        need(
            all(
                signature(os.fstat(root))[key] == request["root"][key]
                for key in ("device", "inode", "uid")
            ),
            "reviewed root identity",
        )
        _binding(root_path, root)
        _binding(evidence_path, evidence)
        need(names(root) == request["files"].keys(), "closed initial inventory")
        for name, expected in request["files"].items():
            original_fds[name] = _file(root, name, expected)
        os.mkdir(request["attempt"], 0o700, dir_fd=evidence)
        os.fsync(evidence)
        attempt_path = evidence_path / request["attempt"]
        attempt = _private_directory(attempt_path)
        os.mkdir("quarantine", 0o700, dir_fd=attempt)
        quarantine_path = attempt_path / "quarantine"
        quarantine = _private_directory(quarantine_path)
        journal = os.open(
            "events.jsonl",
            os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW | os.O_CLOEXEC,
            0o600,
            dir_fd=attempt,
        )
        journal_id = os.fstat(journal)
        os.fsync(attempt)
        journal_healthy = True

        def check():
            need(request["source_identity"] == source_identity(), "source changed")
            for path, fd in (
                (root_path, root),
                (evidence_path, evidence),
                (attempt_path, attempt),
                (quarantine_path, quarantine),
            ):
                _binding(path, fd)
            live, opened = (
                os.stat("events.jsonl", dir_fd=attempt, follow_symlinks=False),
                os.fstat(journal),
            )
            need(
                (live.st_dev, live.st_ino)
                == (opened.st_dev, opened.st_ino)
                == (journal_id.st_dev, journal_id.st_ino)
                and stat.S_ISREG(live.st_mode)
                and live.st_nlink == 1
                and stat.S_IMODE(live.st_mode) == 0o600
                and live.st_uid == os.getuid()
                and names(attempt, 2) == {"quarantine", "events.jsonl"},
                "journal binding",
            )

        def append(value):
            nonlocal journal_healthy
            try:
                check()
                content = (json.dumps(value, sort_keys=True) + "\n").encode()
                offset = 0
                while offset < len(content):
                    written = os.write(journal, content[offset:])
                    need(written > 0, "journal short write")
                    offset += written
                os.fsync(journal)
                need(os.fstat(journal).st_size <= JOURNAL_LIMIT, "journal bound")
                check()
            except BaseException:
                journal_healthy = False
                raise

        append(
            {
                "event": "prepared",
                "request_sha256": digest(raw),
                "kind": request["kind"],
                **AUTHORITY,
            }
        )
        status, error = "failed", None
        try:
            checkpoint("prepared", None)
            for name, expected in sorted(request["files"].items()):
                check()
                if stop():
                    status = "interrupted"
                    break
                need(
                    names(root) == set(request["files"]) - set(removed)
                    and names(quarantine) == set(),
                    "inventory changed before move",
                )
                verify = _file(root, name, expected)
                os.close(verify)
                exclusive_rename(root_path / name, quarantine_path / name)
                os.fsync(root)
                os.fsync(quarantine)
                append({"event": "quarantined", "name": name})
                checkpoint("quarantined", name)
                if stop():
                    status = "interrupted"
                    break
                check()
                verify = _file(quarantine, name, expected, moved=True)
                os.close(verify)
                need(
                    names(root) == set(request["files"]) - set(removed) - {name}
                    and names(quarantine) == {name},
                    "inventory changed in quarantine",
                )
                # Exclusive ownership is required: POSIX unlink does not compare
                # an expected inode atomically. No hostile-owner guarantee.
                os.unlink(name, dir_fd=quarantine)
                os.fsync(quarantine)
                removed.append(name)
                append({"event": "removed", "name": name})
                checkpoint("removed", name)
            else:
                check()
                need(not names(root) and not names(quarantine), "absence observation")
                status = "interrupted" if stop() else "namespace-absence-observed"
        except Exception as exc:
            error = type(exc).__name__ + ": " + str(exc)[:1000]
        result = {
            "event": "finished",
            "status": status,
            "error": error,
            "removed": removed,
            "target_present": sorted(names(root)),
            "quarantined": sorted(names(quarantine)),
            **AUTHORITY,
        }
        if journal_healthy:
            try:
                append(result)
            except Exception as exc:
                result.update(status="failed", journal_error=type(exc).__name__)
        else:
            result.update(status="failed", journal_error="unverified-journal-prefix-retained")
        return result
    finally:
        for fd in [*original_fds.values(), journal, quarantine, attempt, evidence, root]:
            if fd is not None:
                os.close(fd)


def remove(raw, context_raw, *, cancel=None):
    registry = json.loads(
        (HERE / "removal-admissions.json").read_bytes(), object_pairs_hook=unique_object
    )
    return _remove_reviewed(
        raw, registry, context_raw, stop=(cancel.is_set if cancel is not None else lambda: False)
    )


def inspect(raw, expected_request_sha256, context_raw, expected_journal_sha256, outer_receipt):
    """Inspect a retained prefix without resuming, granting authority or erasing."""
    need(
        digest(raw) == expected_request_sha256 and sha(expected_request_sha256),
        "external request identity",
    )
    request = _request(raw, context_raw)
    attempt_path = Path(request["evidence_parent"]) / request["attempt"]
    root = _private_directory(request["root"]["path"])
    attempt = quarantine = None
    try:
        attempt = _private_directory(attempt_path)
        quarantine = _private_directory(attempt_path / "quarantine")
        need(
            all(
                signature(os.fstat(root))[key] == request["root"][key]
                for key in ("device", "inode", "uid")
            ),
            "reader root identity",
        )
        need(names(attempt, 2) == {"quarantine", "events.jsonl"}, "evidence inventory")
        need(
            stat.S_IMODE(os.stat("events.jsonl", dir_fd=attempt, follow_symlinks=False).st_mode)
            == 0o600,
            "reader journal mode",
        )
        journal = _read_at(attempt, "events.jsonl", JOURNAL_LIMIT)
        need(
            sha(expected_journal_sha256) and digest(journal) == expected_journal_sha256,
            "external journal identity",
        )
        complete_lines = journal.splitlines(keepends=True)
        truncated = bool(complete_lines and not complete_lines[-1].endswith(b"\n"))
        if truncated:
            complete_lines.pop()
        events = [json.loads(line, object_pairs_hook=unique_object) for line in complete_lines]
        need(
            events
            and events[0]
            == {
                "event": "prepared",
                "request_sha256": expected_request_sha256,
                "kind": request["kind"],
                **AUTHORITY,
            },
            "prepared event",
        )
        moved, removed, terminal = set(), set(), None
        for event in events[1:]:
            need(terminal is None, "events after terminal")
            if event.get("event") == "finished":
                fields(
                    event,
                    "event status error removed target_present quarantined " + " ".join(AUTHORITY),
                )
                terminal = event
                need(
                    event["status"] in {"namespace-absence-observed", "failed", "interrupted"}
                    and (event["error"] is None or isinstance(event["error"], str))
                    and all(
                        isinstance(event[key], list)
                        for key in ("removed", "target_present", "quarantined")
                    ),
                    "terminal schema",
                )
                need(all(event.get(k) is v for k, v in AUTHORITY.items()), "terminal authority")
            else:
                fields(event, "event name")
                name = event["name"]
                need(name in request["files"], "unknown event file")
                if event["event"] == "quarantined":
                    need(name not in moved, "duplicate move")
                    moved.add(name)
                else:
                    need(
                        event["event"] == "removed" and name in moved and name not in removed,
                        "removal order",
                    )
                    removed.add(name)
        target_names, quarantine_names = names(root), names(quarantine)
        need(
            target_names | quarantine_names <= request["files"].keys(), "unexpected retained entry"
        )
        for path, fd in (
            (Path(request["root"]["path"]), root),
            (attempt_path, attempt),
            (attempt_path / "quarantine", quarantine),
        ):
            _binding(path, fd)
        need(request["source_identity"] == source_identity(), "reader source changed")
        need(
            _read_at(attempt, "events.jsonl", JOURNAL_LIMIT) == journal,
            "journal changed during read",
        )
        need(
            stat.S_IMODE(os.stat("events.jsonl", dir_fd=attempt, follow_symlinks=False).st_mode)
            == 0o600,
            "reader journal mode changed",
        )
        for path, fd in (
            (Path(request["root"]["path"]), root),
            (attempt_path, attempt),
            (attempt_path / "quarantine", quarantine),
        ):
            _binding(path, fd)
        need(
            names(root) == target_names and names(quarantine) == quarantine_names,
            "reader namespace changed",
        )
        completed = (
            not truncated
            and terminal is not None
            and terminal.get("status") == "namespace-absence-observed"
            and terminal.get("error") is None
            and removed == request["files"].keys()
            and terminal.get("removed") == sorted(removed)
            and not target_names
            and not quarantine_names
            and terminal.get("target_present") == []
            and terminal.get("quarantined") == []
            and outer_receipt.get("status") == "completed"
            and outer_receipt.get("error") is None
            and outer_receipt.get("cleanup_error") is None
            and type(outer_receipt.get("exit_code")) is int
            and outer_receipt.get("exit_code") == 0
            and outer_receipt.get("remaining_owned_processes") == []
            and outer_receipt.get("received_signals") == []
        )
        return {
            "status": "completed" if completed else "incomplete",
            "truncated_journal": truncated,
            "recorded_removed": sorted(removed),
            "target_present": sorted(target_names),
            "quarantined": sorted(quarantine_names),
            **AUTHORITY,
        }
    finally:
        for fd in (quarantine, attempt, root):
            if fd is not None:
                os.close(fd)
