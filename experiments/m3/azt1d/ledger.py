"""Durable local evaluation-access history, containing no glucose observations.

Callers append and await success *before* opening evaluation inputs or executing
an evaluation. Advisory POSIX locks serialize cooperating processes. Receipts
pin a chain prefix; a later append does not invalidate an earlier receipt.

This is an auditable local record, not an external witness: someone able to
replace the file and every pinned receipt can rewrite history. There is no reset
or repair API. Failed writes remain present and fail closed on subsequent reads.
Disclosure references and person aliases must contain no identifying health data.
"""

import copy
import fcntl
import json
import math
import os
import re
import stat
import uuid
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path

from experiments.m1.artifacts import strict_json
from experiments.m3.common import ID, SHA

from .common import digest, outside_repository, require

SCHEMA = "opent1d.m3.azt1d.access-ledger/1"
EVIDENCE_SCHEMA = "opent1d.m3.azt1d.access-evidence/1"
EVENTS = ("before_normalization", "before_execution")
_TIME = re.compile(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{6}\+00:00\Z")
_BASE = {
    "schema",
    "sequence",
    "previous_sha256",
    "event",
    "recorded_at_utc",
    "identity_sha256",
}
_GENESIS = _BASE | {"ledger_id", "ledger_path", "kind", "prior_access"}
_ACCESS = _BASE | {"freeze_sha256", "person", "phase"}


def _canonical(value):
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False
    ).encode("ascii")


def _json_value(value):
    if value is None or type(value) in (str, bool, int):
        return True
    if type(value) is float:
        return math.isfinite(value)
    if type(value) is list:
        return all(_json_value(item) for item in value)
    if type(value) is dict:
        return all(type(key) is str and _json_value(item) for key, item in value.items())
    return False


def _identity_sha(identity):
    try:
        require(type(identity) is dict and identity and _json_value(identity), "Invalid identity")
        return digest(_canonical(identity))
    except (TypeError, ValueError, OverflowError, RecursionError):
        raise ValueError("Invalid evaluation ledger identity") from None


def _prior_access(prior_access, kind):
    require(kind in ("synthetic", "human"), "Invalid evaluation ledger kind")
    require(
        type(prior_access) is dict
        and set(prior_access) == {"reviewed", "status", "reference"}
        and prior_access["reviewed"] is True
        and prior_access["status"] in ("none", "present", "unknown")
        and type(prior_access["reference"]) is str,
        "Invalid evaluation prior-access disclosure",
    )
    require(
        kind == "synthetic" or bool(prior_access["reference"].strip()),
        "Human prior access requires a reviewed disclosure reference",
    )
    return copy.deepcopy(prior_access)


def _path(path):
    try:
        value = Path(path).absolute()
        return value.parent.resolve(strict=True) / value.name
    except (OSError, ValueError, TypeError, RuntimeError):
        raise ValueError("Invalid evaluation ledger path") from None


def _check_file(fd, path):
    opened = os.fstat(fd)
    current = path.lstat()
    require(
        stat.S_ISREG(opened.st_mode)
        and stat.S_ISREG(current.st_mode)
        and opened.st_nlink == 1
        and (opened.st_dev, opened.st_ino) == (current.st_dev, current.st_ino),
        "Evaluation ledger must be an unchanged regular file",
    )


@contextmanager
def _locked(path, *, create=False, write=False):
    fd = None
    try:
        flags = os.O_NOFOLLOW | (os.O_RDWR | os.O_APPEND if write else os.O_RDONLY)
        if create:
            flags |= os.O_CREAT | os.O_EXCL
        fd = os.open(path, flags, 0o600)
        fcntl.flock(fd, fcntl.LOCK_EX if write else fcntl.LOCK_SH)
        _check_file(fd, path)
        yield fd
        _check_file(fd, path)
    except OSError:
        raise ValueError("Evaluation ledger I/O failed; no access authorized") from None
    finally:
        if fd is not None:
            os.close(fd)


def _read_fd(fd):
    os.lseek(fd, 0, os.SEEK_SET)
    chunks = []
    while chunk := os.read(fd, 64 * 1024):
        chunks.append(chunk)
    return b"".join(chunks)


def _append(fd, entry):
    data = _canonical(entry) + b"\n"
    offset = 0
    while offset < len(data):
        written = os.write(fd, data[offset:])
        if written <= 0:
            raise OSError("Ledger write failed")
        offset += written
    os.fsync(fd)


def _time():
    return datetime.now(UTC).isoformat(timespec="microseconds")


def _entry(payload):
    return {"payload": payload, "sha256": digest(_canonical(payload))}


def _parse(raw, identity_sha):
    try:
        require(type(raw) is bytes and raw and raw.endswith(b"\n"), "Invalid ledger bytes")
        entries = []
        for sequence, line in enumerate(raw.splitlines()):
            entry = strict_json(line)
            require(
                type(entry) is dict and set(entry) == {"payload", "sha256"},
                "Invalid ledger entry",
            )
            payload = entry["payload"]
            require(
                type(payload) is dict
                and set(payload) == (_GENESIS if sequence == 0 else _ACCESS)
                and payload["schema"] == SCHEMA
                and type(payload["sequence"]) is int
                and payload["sequence"] == sequence
                and payload["previous_sha256"] == (entries[-1]["sha256"] if entries else None)
                and payload["identity_sha256"] == identity_sha
                and entry["sha256"] == digest(_canonical(payload))
                and line == _canonical(entry),
                "Invalid ledger chain",
            )
            timestamp = payload["recorded_at_utc"]
            require(type(timestamp) is str and _TIME.fullmatch(timestamp), "Invalid ledger time")
            datetime.fromisoformat(timestamp)
            if sequence == 0:
                require(
                    payload["event"] == "created"
                    and type(payload["ledger_id"]) is str
                    and re.fullmatch(r"[0-9a-f]{32}", payload["ledger_id"])
                    and type(payload["ledger_path"]) is str
                    and Path(payload["ledger_path"]).is_absolute(),
                    "Invalid ledger genesis",
                )
                _prior_access(payload["prior_access"], payload["kind"])
            else:
                _access_fields(
                    payload["freeze_sha256"], payload["event"], payload["person"], payload["phase"]
                )
            entries.append(entry)
        return entries
    except (ValueError, TypeError, OverflowError, RecursionError, KeyError):
        raise ValueError("Invalid evaluation ledger history") from None


def _access_fields(freeze_sha, event, person, phase):
    require(type(freeze_sha) is str and SHA.fullmatch(freeze_sha), "Invalid learned freeze hash")
    require(event in EVENTS and phase == "evaluation", "Invalid evaluation access event")
    require(type(person) is str and ID.fullmatch(person), "Invalid evaluation person alias")


def _physical(entries, path):
    genesis = entries[0]["payload"]
    require(genesis["ledger_path"] == str(path), "Evaluation ledger path changed")
    if genesis["kind"] == "human":
        outside_repository(path)


def _evidence(entries, sequence):
    genesis = entries[0]["payload"]
    entry = entries[sequence]
    payload = entry["payload"]
    previous = [item["payload"] for item in entries[1:sequence]]
    prior_person = [item for item in previous if item["person"] == payload.get("person")]
    prior_same = [item for item in prior_person if item["event"] == payload["event"]]
    return {
        "schema": EVIDENCE_SCHEMA,
        "ledger_id": genesis["ledger_id"],
        "ledger_path": genesis["ledger_path"],
        "identity_sha256": genesis["identity_sha256"],
        "genesis_sha256": entries[0]["sha256"],
        "sequence": sequence,
        "event_sha256": entry["sha256"],
        "event": payload["event"],
        "freeze_sha256": payload.get("freeze_sha256"),
        "person": payload.get("person"),
        "phase": payload.get("phase"),
        "kind": genesis["kind"],
        "prior_access": copy.deepcopy(genesis["prior_access"]),
        "prior_event_count": max(0, sequence - 1),
        "prior_person_event_count": len(prior_person),
        "prior_same_event_count": len(prior_same),
        "repeated_event": bool(prior_same),
    }


def create_ledger(path, identity, prior_access, kind):
    """Explicitly initialize a new path, fsync it, and return genesis evidence.

    ``identity`` is a nonempty JSON dictionary supplied by the caller binding the
    study, source, allocation and split. Only its canonical SHA256 is recorded.
    ``prior_access`` is exactly ``{reviewed: True, status: none|present|unknown,
    reference: str}``; human histories require a nonempty disclosure reference.
    Existing paths, including empty files from unsuccessful creation, are refused.
    """
    identity_sha = _identity_sha(identity)
    prior_access = _prior_access(prior_access, kind)
    path = _path(path)
    if kind == "human":
        outside_repository(path)
    entry = _entry(
        {
            "schema": SCHEMA,
            "sequence": 0,
            "previous_sha256": None,
            "event": "created",
            "recorded_at_utc": _time(),
            "identity_sha256": identity_sha,
            "ledger_id": uuid.uuid4().hex,
            "ledger_path": str(path),
            "kind": kind,
            "prior_access": prior_access,
        }
    )
    with _locked(path, create=True, write=True) as fd:
        _append(fd, entry)
        directory = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY)
        try:
            os.fsync(directory)
        finally:
            os.close(directory)
    return _evidence([entry], 0)


def record_access(path, identity, freeze_sha, event, person, phase="evaluation"):
    """Durably append an access event before the caller performs that access.

    The returned evidence discloses prior total, per-person and same-event counts.
    A repeated event is counted across learned freezes. No claim of being unseen
    is inferred from either a new file or a particular disclosure status.
    """
    identity_sha = _identity_sha(identity)
    _access_fields(freeze_sha, event, person, phase)
    path = _path(path)
    with _locked(path, write=True) as fd:
        entries = _parse(_read_fd(fd), identity_sha)
        _physical(entries, path)
        entry = _entry(
            {
                "schema": SCHEMA,
                "sequence": len(entries),
                "previous_sha256": entries[-1]["sha256"],
                "event": event,
                "recorded_at_utc": _time(),
                "identity_sha256": identity_sha,
                "freeze_sha256": freeze_sha,
                "person": person,
                "phase": phase,
            }
        )
        _append(fd, entry)
        entries.append(entry)
    return _evidence(entries, len(entries) - 1)


def _verified(entries, evidence):
    require(type(evidence) is dict, "Invalid evaluation access evidence")
    sequence = evidence.get("sequence")
    require(
        type(sequence) is int and 0 <= sequence < len(entries),
        "Evaluation access evidence is absent from ledger",
    )
    expected = _evidence(entries, sequence)
    try:
        unchanged = _json_value(evidence) and _canonical(evidence) == _canonical(expected)
    except (ValueError, TypeError, OverflowError, RecursionError):
        unchanged = False
    require(unchanged, "Evaluation access evidence changed")
    return {
        "event_count": len(entries) - 1,
        "head_sequence": len(entries) - 1,
        "head_sha256": entries[-1]["sha256"],
        "prior_access": copy.deepcopy(entries[0]["payload"]["prior_access"]),
        "kind": entries[0]["payload"]["kind"],
        "evidence": expected,
    }


def verify_snapshot(raw_bytes, identity, evidence):
    """Pure chain/prefix verification, including a copied reconstruction snapshot.

    The entire supplied chain is checked; it may extend the evidence's prefix.
    This checks the original path recorded in evidence without accessing that
    path. It cannot attest that a snapshot contains the live ledger's latest head.
    Returns event_count, head_sequence, head_sha256, prior_access, kind, evidence.
    """
    return _verified(_parse(raw_bytes, _identity_sha(identity)), evidence)


def verify_evidence(path, identity, evidence):
    """Check the live original ledger and a receipt under a shared lock.

    Return keys match ``verify_snapshot``. In particular, callers checking for
    evaluation access before fitting must use current ``event_count``, not the
    earlier receipt's ``prior_event_count``. A later append remains valid history.
    """
    path = _path(path)
    with _locked(path) as fd:
        entries = _parse(_read_fd(fd), _identity_sha(identity))
        _physical(entries, path)
        return _verified(entries, evidence)


def snapshot_ledger(path, identity, evidence):
    """Return a complete, validated byte snapshot under the live shared lock.

    The original physical path, full chain and pinned evidence must agree before
    any bytes are returned. Later appends are allowed after this snapshot; use
    ``verify_snapshot`` to inspect its recorded head without reopening the source.
    """
    path = _path(path)
    with _locked(path) as fd:
        raw = _read_fd(fd)
        entries = _parse(raw, _identity_sha(identity))
        _physical(entries, path)
        _verified(entries, evidence)
        return raw
