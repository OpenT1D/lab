"""One reviewed leaf in a mixed parent; never recursive or effective erasure."""

import json
import os
import re
import stat
from pathlib import Path

from experiments.durable_archives.storage import exclusive_rename
from experiments.lt1_diagnostic.archive_preflight import digest, unique_object
from experiments.lt1_diagnostic.control_identity import host, identity
from experiments.lt1_diagnostic.frozen_setup import _private_directory, _read_at
from experiments.lt1_diagnostic.removal import AUTHORITY, _admitted, _binding, _file, signature
from experiments.lt1_diagnostic.retention import fields, sha

HERE = Path(__file__).resolve().parent
LIMIT = 1024 * 1024
JOURNAL_LIMIT = 2 * LIMIT
FILE_LIMIT = 16 * LIMIT
MAX_SIBLINGS = 128
SCHEMA = "opent1d.lt1-historical-leaf-removal-request/1"
STATUS = "target-namespace-absence-observed"
IDENTITY_FIELDS = "device inode uid bytes mode mtime_ns ctime_ns"
DIRECTORY_FIELDS = "path device inode uid mode mtime_ns ctime_ns"


def need(ok, reason):
    if not ok:
        raise ValueError("LT1 historical leaf removal refused: " + reason)


def source_identity():
    return identity(__file__)


def _name(name):
    need(
        isinstance(name, str)
        and re.fullmatch("[a-z0-9][a-z0-9._-]{0,127}", name)
        and not name.endswith("."),
        "bounded immediate name",
    )


def _numbers(record, keys):
    need(all(type(record[k]) is int and record[k] >= 0 for k in keys.split()), "identity types")


def _directory(record):
    fields(record, DIRECTORY_FIELDS)
    _numbers(record, "device inode uid mode mtime_ns ctime_ns")
    need(record["uid"] == os.getuid() and record["mode"] == 0o700, "directory policy")
    path = record["path"]
    need(isinstance(path, str) and len(path) <= 1024 and Path(path).is_absolute(), "directory path")


def _request(raw, context_raw):
    need(isinstance(raw, bytes) and len(raw) <= LIMIT, "request bound")
    request = json.loads(raw, object_pairs_hook=unique_object)
    fields(
        request,
        "schema kind root evidence_parent attempt target siblings "
        "source_identity host context_sha256",
    )
    need(request["schema"] == SCHEMA and request["kind"] in {"invented", "private-data"}, "schema")
    need(
        request["host"] == host() and request["source_identity"] == source_identity(), "host/source"
    )
    need(
        isinstance(context_raw, bytes)
        and len(context_raw) <= LIMIT
        and sha(request["context_sha256"])
        and digest(context_raw) == request["context_sha256"],
        "external review context",
    )
    context = json.loads(context_raw, object_pairs_hook=unique_object)
    fields(
        context,
        "schema acl_scope_reviewed process_quiescent exclusive_ownership_reviewed "
        "recovery_disposition_sha256 outer_argv_sha256",
    )
    need(
        context["schema"] == "opent1d.lt1-historical-leaf-context/1"
        and all(
            context[k] is True
            for k in ("acl_scope_reviewed", "process_quiescent", "exclusive_ownership_reviewed")
        )
        and sha(context["recovery_disposition_sha256"])
        and sha(context["outer_argv_sha256"]),
        "reviewed ACL/process/ownership/recovery disposition required",
    )
    # These are externally reviewed claims, not an ACL collector, process stop,
    # whole-host copy discovery or recovery-coverage approval by this helper.
    for key in ("root", "evidence_parent"):
        _directory(request[key])
    root, evidence = Path(request["root"]["path"]), Path(request["evidence_parent"]["path"])
    need(
        not root.is_relative_to(evidence) and not evidence.is_relative_to(root), "separate evidence"
    )
    need(request["root"]["device"] == request["evidence_parent"]["device"], "same volume")
    _name(request["attempt"])
    target = request["target"]
    fields(target, "name file")
    _name(target["name"])
    expected = target["file"]
    fields(expected, IDENTITY_FIELDS + " sha256")
    _numbers(expected, IDENTITY_FIELDS)
    need(
        expected["uid"] == os.getuid()
        and expected["device"] == request["root"]["device"]
        and expected["bytes"] <= FILE_LIMIT
        and expected["mode"] in {0o400, 0o600}
        and sha(expected["sha256"]),
        "target policy",
    )
    siblings = request["siblings"]
    need(isinstance(siblings, dict) and len(siblings) <= MAX_SIBLINGS, "sibling bound")
    need(target["name"] not in siblings, "target is not sibling authority")
    for name, record in siblings.items():
        _name(name)
        fields(record, "kind " + IDENTITY_FIELDS + " nlink")
        _numbers(record, IDENTITY_FIELDS + " nlink")
        need(
            record["kind"] in {"file", "directory"}
            and record["uid"] == os.getuid()
            and record["device"] == request["root"]["device"]
            and record["mode"] <= 0o777
            and (record["nlink"] == 1 if record["kind"] == "file" else record["nlink"] >= 1),
            "ordinary owned sibling policy",
        )
    return request


def _names(fd, limit):
    result = set()
    with os.scandir(fd) as entries:
        for item in entries:
            result.add(item.name)
            need(len(result) <= limit, "namespace bound")
    return result


def _directory_binding(record, fd, *, initial=False):
    _binding(record["path"], fd)
    current = signature(os.fstat(fd))
    keys = "device inode uid mode mtime_ns ctime_ns" if initial else "device inode uid mode"
    need(all(current[k] == record[k] for k in keys.split()), "directory identity changed")


def sibling_signature(info):
    """Immediate metadata only; never reads or inventories directory contents."""
    kind = (
        "file"
        if stat.S_ISREG(info.st_mode)
        else "directory"
        if stat.S_ISDIR(info.st_mode)
        else "special"
    )
    return {"kind": kind, **signature(info), "nlink": info.st_nlink}


def _siblings(root, request, target_present):
    names = set(request["siblings"]) | ({request["target"]["name"]} if target_present else set())
    need(_names(root, MAX_SIBLINGS + 1) == names, "immediate namespace changed")
    for name, expected in request["siblings"].items():
        actual = os.stat(name, dir_fd=root, follow_symlinks=False)
        need(sibling_signature(actual) == expected, "sibling identity changed")


def _remove_reviewed(raw, registry, context_raw, *, stop=lambda: False, checkpoint=lambda *_: None):
    """Fixture registry injection; exclusive quiescent ownership is a prerequisite."""
    _admitted(raw, registry)  # No request/path/source/context intake before membership.
    request = _request(raw, context_raw)
    if stop():
        return {"status": "interrupted", "attempt_created": False, "removed": [], **AUTHORITY}
    root_path = Path(request["root"]["path"])
    evidence_path = Path(request["evidence_parent"]["path"])
    target, expected = request["target"]["name"], request["target"]["file"]
    root = evidence = attempt = quarantine = journal = held = None
    location, moved, removed, journal_healthy = "root", False, False, True
    prefix = b""
    try:
        root = _private_directory(root_path)
        evidence = _private_directory(evidence_path)
        _directory_binding(request["root"], root, initial=True)
        _directory_binding(request["evidence_parent"], evidence, initial=True)
        _siblings(root, request, True)
        held = _file(root, target, expected)
        os.mkdir(request["attempt"], 0o700, dir_fd=evidence)
        os.fsync(evidence)
        attempt_path = evidence_path / request["attempt"]
        attempt = _private_directory(attempt_path)
        os.mkdir("quarantine", 0o700, dir_fd=attempt)
        quarantine_path = attempt_path / "quarantine"
        quarantine = _private_directory(quarantine_path)
        journal = os.open(
            "events.jsonl",
            os.O_RDWR | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW | os.O_CLOEXEC,
            0o600,
            dir_fd=attempt,
        )
        journal_id = os.fstat(journal)
        os.fsync(attempt)

        def check():
            need(request["source_identity"] == source_identity(), "source changed")
            _directory_binding(request["root"], root)
            _directory_binding(request["evidence_parent"], evidence)
            _binding(attempt_path, attempt)
            _binding(quarantine_path, quarantine)
            _siblings(root, request, location == "root")
            need(
                _names(quarantine, 1) == ({target} if location == "quarantine" else set()),
                "quarantine namespace changed",
            )
            need(_names(attempt, 2) == {"quarantine", "events.jsonl"}, "attempt namespace changed")
            current = os.stat("events.jsonl", dir_fd=attempt, follow_symlinks=False)
            opened = os.fstat(journal)
            need(
                stat.S_ISREG(current.st_mode)
                and current.st_nlink == opened.st_nlink == 1
                and current.st_uid == os.getuid()
                and stat.S_IMODE(current.st_mode) == 0o600
                and (current.st_dev, current.st_ino)
                == (opened.st_dev, opened.st_ino)
                == (journal_id.st_dev, journal_id.st_ino)
                and _read_at(attempt, "events.jsonl", JOURNAL_LIMIT) == prefix,
                "journal binding or bytes changed",
            )

        def append(event):
            nonlocal prefix, journal_healthy
            try:
                check()
                content = (json.dumps(event, sort_keys=True) + "\n").encode()
                need(len(prefix) + len(content) <= JOURNAL_LIMIT, "journal bound")
                offset = 0
                while offset < len(content):
                    count = os.write(journal, content[offset:])
                    need(count > 0, "journal short write")
                    offset += count
                os.fsync(journal)
                prefix += content
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
            checkpoint("prepared", target)
            check()
            if stop():
                status = "interrupted"
            else:
                verify = _file(root, target, expected)
                os.close(verify)
                check()
                exclusive_rename(root_path / target, quarantine_path / target)
                location = "quarantine"
                os.fsync(root)
                os.fsync(quarantine)
                checkpoint("moved-unrecorded", target)
                append({"event": "quarantined", "name": target})
                moved = True
                checkpoint("quarantined", target)
                if stop():
                    status = "interrupted"
                else:
                    check()
                    verify = _file(quarantine, target, expected, moved=True)
                    try:
                        verified = signature(os.fstat(verify))
                        need(
                            signature(os.fstat(held)) == verified and os.fstat(held).st_nlink == 1,
                            "held target identity changed",
                        )
                        check()
                        if stop():
                            status = "interrupted"
                        else:
                            late = _file(quarantine, target, expected, moved=True)
                            os.close(late)
                            need(
                                signature(os.fstat(held))
                                == signature(os.fstat(verify))
                                == signature(
                                    os.stat(target, dir_fd=quarantine, follow_symlinks=False)
                                )
                                == verified
                                and os.fstat(held).st_nlink == 1,
                                "target changed immediately before unlink",
                            )
                            # Unlink has no atomic expected-inode argument. This
                            # cannot isolate an adversarial same-UID writer.
                            os.unlink(target, dir_fd=quarantine)
                            location = "absent"
                            os.fsync(quarantine)
                            checkpoint("unlinked-unrecorded", target)
                            append({"event": "removed", "name": target})
                            removed = True
                            checkpoint("removed", target)
                            checkpoint("before-complete", target)
                            check()
                            status = "interrupted" if stop() else STATUS
                    finally:
                        os.close(verify)
        except Exception as exc:
            error = type(exc).__name__ + ": " + str(exc)[:1000]
        result = {
            "event": "finished",
            "status": status,
            "error": error,
            "removed": [target] if removed else [],
            "target_present": [target] if target in _names(root, MAX_SIBLINGS + 1) else [],
            "quarantined": sorted(_names(quarantine, 1)),
            "recorded_move": moved,
            **AUTHORITY,
        }
        if journal_healthy:
            try:
                append(result)
            except Exception as exc:
                result.update(status="failed", journal_error=type(exc).__name__)
        else:
            result.update(status="failed", journal_error="unverified-prefix-retained")
        return result
    finally:
        for fd in (held, journal, quarantine, attempt, evidence, root):
            if fd is not None:
                os.close(fd)


def remove(raw, context_raw, *, cancel=None):
    registry = json.loads(
        (HERE / "removal-admissions.json").read_bytes(), object_pairs_hook=unique_object
    )
    return _remove_reviewed(
        raw, registry, context_raw, stop=cancel.is_set if cancel is not None else lambda: False
    )


def _outer(raw, expected, request_sha256):
    need(
        isinstance(raw, bytes) and len(raw) <= LIMIT and sha(expected) and digest(raw) == expected,
        "external outer identity",
    )
    outer = json.loads(raw, object_pairs_hook=unique_object)
    fields(outer, "schema request_sha256 supervision")
    need(
        outer["schema"] == "opent1d.lt1-historical-leaf-outer/1"
        and outer["request_sha256"] == request_sha256,
        "outer request binding",
    )
    need(isinstance(outer["supervision"], dict), "outer supervision")
    return outer["supervision"]


def command_digest(argv):
    need(
        isinstance(argv, list)
        and 0 < len(argv) <= 32
        and all(isinstance(v, str) and 0 < len(v) <= 2048 and "\0" not in v for v in argv),
        "bounded reviewed outer command",
    )
    return digest(json.dumps(argv, sort_keys=True).encode())


def _owned(outer):
    required = {
        "argv",
        "status",
        "exit_code",
        "error",
        "cleanup_forced",
        "owned_processes",
        "remaining_owned_processes",
        "received_signals",
    }
    records = outer.get("owned_processes")
    if set(outer) != required or type(records) is not list or not 0 < len(records) <= 128:
        return False
    seen = set()
    for record in records:
        if (
            type(record) is not dict
            or set(record) != {"pid", "ppid", "pgid", "start", "alive"}
            or not all(type(record[k]) is int and record[k] > 0 for k in ("pid", "ppid", "pgid"))
            or record["pid"] == record["ppid"]
            or record["pid"] in seen
            or type(record["start"]) is not str
            or not 0 < len(record["start"]) <= 256
            or type(record["alive"]) is not bool
        ):
            return False
        seen.add(record["pid"])
    return records[0]["pid"] == records[0]["pgid"] and outer["cleanup_forced"] is False


def inspect(
    raw,
    expected_request_sha256,
    context_raw,
    expected_journal_sha256,
    outer_raw,
    expected_outer_sha256,
):
    """Read pinned evidence from an externally reviewed trusted outer producer.

    Byte pins/command correspondence do not authenticate that producer's origin.
    This never resumes or grants removal/erasure authority.
    """
    need(
        isinstance(raw, bytes)
        and sha(expected_request_sha256)
        and digest(raw) == expected_request_sha256,
        "external request identity",
    )
    outer = _outer(outer_raw, expected_outer_sha256, expected_request_sha256)
    request = _request(raw, context_raw)
    context = json.loads(context_raw, object_pairs_hook=unique_object)
    need(
        command_digest(outer.get("argv")) == context["outer_argv_sha256"],
        "outer command correspondence",
    )
    root = evidence = attempt = quarantine = None
    target, expected = request["target"]["name"], request["target"]["file"]
    try:
        root = _private_directory(request["root"]["path"])
        evidence = _private_directory(request["evidence_parent"]["path"])
        attempt_path = Path(request["evidence_parent"]["path"]) / request["attempt"]
        attempt = _private_directory(attempt_path)
        quarantine = _private_directory(attempt_path / "quarantine")

        def bindings():
            _directory_binding(request["root"], root)
            _directory_binding(request["evidence_parent"], evidence)
            _binding(attempt_path, attempt)
            _binding(attempt_path / "quarantine", quarantine)
            need(_names(attempt, 2) == {"quarantine", "events.jsonl"}, "reader attempt namespace")
            entry = os.stat("events.jsonl", dir_fd=attempt, follow_symlinks=False)
            need(
                entry.st_uid == os.getuid() and stat.S_IMODE(entry.st_mode) == 0o600,
                "reader journal policy",
            )

        need(request["source_identity"] == source_identity(), "reader source changed")
        bindings()
        journal = _read_at(attempt, "events.jsonl", JOURNAL_LIMIT)
        need(
            sha(expected_journal_sha256) and digest(journal) == expected_journal_sha256,
            "external journal identity",
        )
        lines = journal.splitlines(keepends=True)
        truncated = bool(lines and not lines[-1].endswith(b"\n"))
        if truncated:
            lines.pop()
        events = [json.loads(line, object_pairs_hook=unique_object) for line in lines]
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
        moved, removed, terminal = False, False, None
        for event in events[1:]:
            need(terminal is None, "events after terminal")
            if event.get("event") == "finished":
                fields(
                    event,
                    "event status error removed target_present quarantined recorded_move "
                    + " ".join(AUTHORITY),
                )
                need(
                    event["status"] in {STATUS, "failed", "interrupted"}
                    and (event["error"] is None or isinstance(event["error"], str))
                    and event["removed"] == ([target] if removed else [])
                    and event["recorded_move"] is moved
                    and all(event[k] is False for k in AUTHORITY),
                    "terminal event",
                )
                terminal = event
            else:
                fields(event, "event name")
                need(event["name"] == target, "event target")
                if event["event"] == "quarantined":
                    need(not moved, "duplicate move")
                    moved = True
                else:
                    need(event["event"] == "removed" and moved and not removed, "removal order")
                    removed = True
        root_names, quarantine_names = _names(root, MAX_SIBLINGS + 1), _names(quarantine, 1)
        target_present = target in root_names
        need(
            quarantine_names <= {target} and not (target_present and quarantine_names),
            "target location conflict",
        )
        _siblings(root, request, target_present)
        if target_present:
            need(not moved and not removed, "recorded move contradicts live target")
            fd = _file(root, target, expected)
            os.close(fd)
        if quarantine_names:
            need(not removed, "recorded removal contradicts quarantine")
            fd = _file(quarantine, target, expected, moved=True)
            os.close(fd)
        if terminal is not None:
            need(
                terminal["target_present"] == ([target] if target_present else [])
                and terminal["quarantined"] == sorted(quarantine_names),
                "terminal live locations",
            )
        need(request["source_identity"] == source_identity(), "reader source changed")
        bindings()
        need(_read_at(attempt, "events.jsonl", JOURNAL_LIMIT) == journal, "reader journal changed")
        if target_present or quarantine_names:
            fd = _file(
                root if target_present else quarantine,
                target,
                expected,
                moved=bool(quarantine_names),
            )
            os.close(fd)
        _siblings(root, request, target_present)
        need(_names(quarantine, 1) == quarantine_names, "reader quarantine changed")
        bindings()
        completed = (
            not truncated
            and terminal is not None
            and terminal["status"] == STATUS
            and terminal["error"] is None
            and moved
            and removed
            and not target_present
            and not quarantine_names
            and outer.get("status") == "completed"
            and outer.get("error") is None
            and outer.get("cleanup_error") is None
            and outer.get("signal_error") is None
            and type(outer.get("exit_code")) is int
            and outer["exit_code"] == 0
            and outer.get("remaining_owned_processes") == []
            and outer.get("received_signals") == []
            and _owned(outer)
        )
        return {
            "status": "completed" if completed else "incomplete",
            "truncated_journal": truncated,
            "recorded_removed": [target] if removed else [],
            "target_present": [target] if target_present else [],
            "quarantined": sorted(quarantine_names),
            "reviewed_immediate_sibling_count": len(request["siblings"]),
            "unrecorded_move_observed": bool(quarantine_names) and not moved,
            "absence_without_recorded_removal": not target_present
            and not quarantine_names
            and not removed,
            **AUTHORITY,
        }
    finally:
        for fd in (quarantine, attempt, evidence, root):
            if fd is not None:
                os.close(fd)
