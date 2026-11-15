"""Owned invented two-pass descriptor fixtures; actual PBS inspection is closed.

No fixture assertion authenticates material or admits real archive reads. The
second pass opaquely drains decompressed member bytes; it is not zero-body I/O.
The unchanged marker-strict fixture parser supplies only its smaller grammar.
"""

import hashlib
import os
import stat
import time
from datetime import UTC, datetime, timedelta
from pathlib import Path

from . import fixture_time, pbs_archive
from .contract import AUTHORITY, decode, digest, encode, require, source_identity

SCHEMA = "opent1d.pbs-two-pass-inspection-fixture/1"
CONTEXT_SCHEMA = "opent1d.pbs-two-pass-context-fixture/1"
CAP_UTC = "2026-11-28T18:32:01Z"
FIXTURE_SECONDS = 5
FUTURE_UNQUALIFIED = {
    "compressed_bytes_per_pass": 25172086,
    "compressed_passes": 2,
    "compressed_bytes_total": 50344172,
    "EOF_probe_bytes_max_total": 2,
    "decompressed_bytes": 512 * 1024 * 1024,
    "members": 20000,
    "member_bytes": 256 * 1024 * 1024,
    "path_utf8_bytes": 4096,
    "path_depth": 32,
    "inventory_bytes": 8 * 1024 * 1024,
    "notice_selection": None,
    "member_body_selection": None,
}
STAGES = ("created", "pass1", "fixture-auth", "rewind", "pass2", "inventory")


def inspect_archive(*_args, **_kwargs):
    """No actual body/path/source access while actual authentication is absent."""
    raise PermissionError(
        "actual PBS phaseB inspection closed: authentication/executor not qualified"
    )


def _identity():
    return source_identity() | {
        "pbs_archive.py": digest(Path(pbs_archive.__file__).read_bytes()),
        "pbs_inspection.py": digest(Path(__file__).read_bytes()),
    }


def _now():
    return fixture_time.now()


def _instant(text):
    require(type(text) is str and text.endswith("Z"), "UTC-instant")
    try:
        value = datetime.fromisoformat(text[:-1] + "+00:00")
    except ValueError as error:
        raise ValueError("UTC-instant") from error
    require(
        value.tzinfo == UTC and value.isoformat().replace("+00:00", "Z") == text,
        "canonical-UTC-instant",
    )
    return value


@fixture_time.invented
def make_invented_context(raw):
    """Fixed invented-only test context. This creates no actual admission."""
    require(
        type(raw) is bytes and 18 <= len(raw) <= pbs_archive.LIMITS["compressed_bytes"],
        "bounded-owned-invented-buffer",
    )
    issued = _now().replace(microsecond=0)
    expiry = min(issued + timedelta(hours=1), _instant(CAP_UTC))
    return encode(
        {
            "schema": CONTEXT_SCHEMA,
            "kind": "invented",
            "artifact_sha256": digest(raw),
            "artifact_bytes": len(raw),
            "source_identity": _identity(),
            "issued_utc": issued.isoformat().replace("+00:00", "Z"),
            "expires_utc": expiry.isoformat().replace("+00:00", "Z"),
            "retention_not_after_utc": CAP_UTC,
            "fixture_auth_status": "fixture-controls-passed",
            "actual_crypto_verified": False,
            "actual_authentication_admitted": False,
        }
    )


@fixture_time.invented
def _context(raw, pin):
    require(
        type(raw) is bytes and 0 < len(raw) <= 65536 and digest(raw) == pin, "held-bounded-context"
    )
    value = decode(raw)
    require(
        type(value) is dict
        and set(value)
        == {
            "schema",
            "kind",
            "artifact_sha256",
            "artifact_bytes",
            "source_identity",
            "issued_utc",
            "expires_utc",
            "retention_not_after_utc",
            "fixture_auth_status",
            "actual_crypto_verified",
            "actual_authentication_admitted",
        },
        "exact-fixture-context",
    )
    require(
        value["schema"] == CONTEXT_SCHEMA and value["kind"] == "invented", "invented-context-only"
    )
    require(
        type(value["artifact_sha256"]) is str
        and len(value["artifact_sha256"]) == 64
        and all(c in "0123456789abcdef" for c in value["artifact_sha256"])
        and type(value["artifact_bytes"]) is int
        and 18 <= value["artifact_bytes"] <= pbs_archive.LIMITS["compressed_bytes"],
        "bounded-artifact-context",
    )
    require(value["source_identity"] == _identity(), "context-source-binding")
    require(
        value["fixture_auth_status"] in ("fixture-controls-passed", "denied", "pending")
        and value["actual_crypto_verified"] is False
        and value["actual_authentication_admitted"] is False,
        "no-actual-auth-from-fixtures",
    )
    issued, expiry = _instant(value["issued_utc"]), _instant(value["expires_utc"])
    cap = _instant(value["retention_not_after_utc"])
    require(
        issued < expiry <= min(issued + timedelta(days=30), cap, _instant(CAP_UTC)),
        "retention-no-reset-or-extension",
    )
    require(issued <= _now() < expiry, "current-fixture-window")
    return value


def _checkpoint(context_raw, context_pin, identity, deadline):
    require(time.monotonic() < deadline, "fixture-logical-deadline")
    require(_identity() == identity, "source-changed")
    _context(context_raw, context_pin)


def _token(value):
    return {
        "dev": value.st_dev,
        "ino": value.st_ino,
        "size": value.st_size,
        "mode": stat.S_IMODE(value.st_mode),
        "uid": value.st_uid,
        "nlink": value.st_nlink,
        "mtime_ns": value.st_mtime_ns,
        "ctime_ns": value.st_ctime_ns,
    }


def _observe(fd, directory_fd, parent_fd, directory_name):
    directory = os.fstat(directory_fd)
    named_directory = os.stat(directory_name, dir_fd=parent_fd, follow_symlinks=False)
    require(
        stat.S_ISDIR(named_directory.st_mode)
        and stat.S_IMODE(directory.st_mode) == 0o700
        and directory.st_uid == os.getuid()
        and _token(directory) == _token(named_directory),
        "same-private-directory-name-binding",
    )
    observed = os.fstat(fd)
    named = os.stat("input.fixture", dir_fd=directory_fd, follow_symlinks=False)
    require(
        stat.S_ISREG(observed.st_mode)
        and stat.S_ISREG(named.st_mode)
        and observed.st_uid == os.getuid()
        and observed.st_nlink == 1
        and stat.S_IMODE(observed.st_mode) == 0o600,
        "private-owned-regular-fixture",
    )
    require(_token(observed) == _token(named), "same-fd-name-binding")
    return _token(observed)


def _read_pass(fd, limit, checkpoint, observation):
    # checkpoint is an internal fixed closure; never JSON or a public callback.
    size, hasher, chunks = 0, hashlib.sha256(), []
    while size < limit:
        checkpoint()
        chunk = os.read(fd, min(4096, limit - size))
        require(chunk, "truncated-compressed-pass")
        chunks.append(chunk)
        hasher.update(chunk)
        size += len(chunk)
        observation.update(bytes=size, sha256=hasher.hexdigest())
    checkpoint()
    observation["EOF_probes"] += 1
    require(os.read(fd, 1) == b"", "compressed-EOF-sentinel")
    return b"".join(chunks), hasher.hexdigest(), size


def _headers(raw, pin):
    # Do not bypass the old parser's marker or claim its bounds cover real PBS.
    parsed = pbs_archive.inspect_invented_archive(raw, pin)
    return {
        "rows": [
            {key: row[key] for key in ("path", "kind", "bytes", "mode", "link_target")}
            for row in parsed["members"]
        ],
        "decompressed_bytes_drained": parsed["expanded_bytes"],
        "decompressed_member_bytes_drained": sum(row["bytes"] for row in parsed["members"]),
        "inventory_bytes": parsed["inventory_bytes"],
    }


def _base(input_pin, context_pin, context):
    return {
        "schema": SCHEMA,
        "kind": "invented",
        "input_sha256": input_pin,
        "context_sha256": context_pin,
        "source_identity": context["source_identity"],
        "fixture_limits": dict(pbs_archive.LIMITS),
        "future_limits_unqualified": dict(FUTURE_UNQUALIFIED),
        "actual_crypto_verified": False,
        "actual_authentication_admitted": False,
        "actual_execution_ready": False,
        "actual_archive_inspection_authorized": False,
        "authority": dict(AUTHORITY),
        "extraction_performed": False,
        "member_text_returned": False,
        "member_hashes_returned": False,
        "notice_text_returned": False,
        "selected_notices": [],
        "static_payload_selectors": None,
        "physical_history_authenticated": False,
        "deadline_semantics": "logical-checkpoints-not-preemptive-I/O-or-OS-qualification",
        "retention_not_after_utc": context["retention_not_after_utc"],
    }


@fixture_time.invented
def inspect_invented_file(raw, held_input_sha256, context_raw, held_context_sha256, fresh_root):
    """Create a NEW private owned fixture file, then hold its FD for two passes.

    fresh_root is a trusted direct fixture-output API argument, never JSON input.
    Only owned literal invented bytes belong here; a marker is not provenance.
    No actual retained archive path is accepted or opened by this API.
    """
    context = _context(context_raw, held_context_sha256)
    require(
        type(raw) is bytes
        and len(raw) == context["artifact_bytes"]
        and digest(raw) == held_input_sha256 == context["artifact_sha256"],
        "held-invented-input",
    )
    require(
        hasattr(os, "O_NOFOLLOW") and os.open in os.supports_dir_fd,
        "fixture-host-dirfd-support-only",
    )
    identity, deadline = _identity(), time.monotonic() + FIXTURE_SECONDS
    result = _base(held_input_sha256, held_context_sha256, context) | {
        "status": "incomplete",
        "events": [],
        "error": None,
        "cleanup_error": None,
        "pass1": None,
        "pass2": None,
        "tokens": [],
        "inventory": None,
        "owned_descriptor_closed": False,
        "fixture_auth_observation": None,
    }
    parent_fd = directory_fd = fd = None
    primary = None
    try:

        def checkpoint():
            _checkpoint(context_raw, held_context_sha256, identity, deadline)

        checkpoint()
        destination = Path(fresh_root)
        require(
            destination.is_absolute() and destination.name not in ("", ".", ".."),
            "trusted-fresh-fixture-destination",
        )
        parent_fd = os.open(destination.parent, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
        parent = os.fstat(parent_fd)
        require(
            stat.S_IMODE(parent.st_mode) == 0o700 and parent.st_uid == os.getuid(),
            "private-trusted-fixture-parent",
        )
        os.mkdir(destination.name, 0o700, dir_fd=parent_fd)
        directory_fd = os.open(
            destination.name, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=parent_fd
        )
        fd = os.open(
            "input.fixture",
            os.O_RDWR | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
            0o600,
            dir_fd=directory_fd,
        )
        offset = 0
        while offset < len(raw):
            checkpoint()
            count = os.write(fd, raw[offset : offset + 4096])
            require(count > 0, "fixture-write-progress")
            offset += count
        os.fsync(fd)
        initial = _observe(fd, directory_fd, parent_fd, destination.name)
        result["tokens"].append(initial)
        result["events"].append("created")
        checkpoint()
        require(os.lseek(fd, 0, os.SEEK_SET) == 0, "initial-rewind")
        result["pass1"] = {"bytes": 0, "sha256": digest(b""), "EOF_probes": 0}
        opaque, sha, count = _read_pass(fd, len(raw), checkpoint, result["pass1"])
        require(sha == held_input_sha256 and count == len(raw), "pass1-size-digest")
        result["pass1"] = {"bytes": count, "sha256": sha, "EOF_probes": 1}
        result["events"].append("pass1")
        current = _observe(fd, directory_fd, parent_fd, destination.name)
        result["tokens"].append(current)
        require(current == initial, "file-changed-after-pass1")
        checkpoint()
        result["fixture_auth_observation"] = context["fixture_auth_status"]
        require(
            context["fixture_auth_status"] == "fixture-controls-passed", "fixture-auth-not-admitted"
        )
        result["events"].append("fixture-auth")
        require(opaque == raw, "pass1-owned-invented-bytes")
        checkpoint()
        require(os.lseek(fd, 0, os.SEEK_SET) == 0, "same-descriptor-rewind")
        result["events"].append("rewind")
        result["pass2"] = {"bytes": 0, "sha256": digest(b""), "EOF_probes": 0}
        second, sha, count = _read_pass(fd, len(raw), checkpoint, result["pass2"])
        result["pass2"] = {"bytes": count, "sha256": sha, "EOF_probes": 1}
        require(second == raw and sha == held_input_sha256, "pass2-size-digest")
        result["events"].append("pass2")
        current = _observe(fd, directory_fd, parent_fd, destination.name)
        result["tokens"].append(current)
        require(current == initial, "file-changed-after-pass2")
        checkpoint()
        result["inventory"] = _headers(second, held_input_sha256)
        result["events"].append("inventory")
        checkpoint()
        current = _observe(fd, directory_fd, parent_fd, destination.name)
        result["tokens"].append(current)
        require(current == initial, "file-changed-after-inventory")
    except (OSError, ValueError) as error:
        primary = (
            type(error).__name__
            + ":"
            + (str(error) if isinstance(error, ValueError) else str(error.errno))
        )
    finally:
        for owned in (fd, directory_fd, parent_fd):
            if owned is not None:
                try:
                    os.close(owned)
                except OSError as error:
                    result["cleanup_error"] = "close-errno:" + str(error.errno)
        result["owned_descriptor_closed"] = fd is not None and result["cleanup_error"] is None
    if primary is None:
        try:
            _checkpoint(context_raw, held_context_sha256, identity, deadline)
        except ValueError as error:
            primary = "ValueError:" + str(error)
    result["error"] = primary
    if primary is None and result["cleanup_error"] is None and result["events"] == list(STAGES):
        result["status"] = "fixture-two-pass-completed"
    return result


@fixture_time.invented
def inspect_fixture_report(
    report_raw, held_report_sha256, raw, held_input_sha256, context_raw, held_context_sha256
):
    """Cold byte reconstruction only; physical tokens remain fixture observations."""
    context = _context(context_raw, held_context_sha256)
    require(
        type(raw) is bytes
        and digest(raw) == held_input_sha256 == context["artifact_sha256"]
        and len(raw) == context["artifact_bytes"],
        "cold-held-invented-input",
    )
    require(
        type(report_raw) is bytes
        and 0 < len(report_raw) <= 1024 * 1024
        and digest(report_raw) == held_report_sha256,
        "cold-held-report",
    )
    report = decode(report_raw)
    base = _base(held_input_sha256, held_context_sha256, context)
    require(
        type(report) is dict
        and set(report)
        == set(base)
        | {
            "status",
            "events",
            "error",
            "cleanup_error",
            "pass1",
            "pass2",
            "tokens",
            "inventory",
            "owned_descriptor_closed",
            "fixture_auth_observation",
        },
        "exact-cold-report",
    )
    require(encode({key: report[key] for key in base}) == encode(base), "cold-static-bindings")
    events = report["events"]
    require(type(events) is list and events == list(STAGES[: len(events)]), "cold-prefix-order")
    require(type(report["tokens"]) is list and len(report["tokens"]) <= 4, "cold-token-count")
    reachable_token_counts = ((0,), (1,), (1, 2), (2,), (2,), (2, 3), (3, 4))
    require(
        len(report["tokens"]) in reachable_token_counts[len(events)],
        "cold-token-prefix-reachability",
    )
    require(
        type(report["owned_descriptor_closed"]) is bool
        and all(
            value is None or type(value) is str and 0 < len(value) <= 256
            for value in (report["error"], report["cleanup_error"])
        ),
        "cold-cleanup-diagnostic-types",
    )
    for token in report["tokens"]:
        require(
            type(token) is dict
            and set(token) == {"dev", "ino", "size", "mode", "uid", "nlink", "mtime_ns", "ctime_ns"}
            and all(type(value) is int and value >= 0 for value in token.values()),
            "cold-token-shape",
        )
        require(
            token["mode"] == 0o600 and token["nlink"] == 1,
            "cold-private-file-token",
        )
    expected_pass = {"bytes": len(raw), "sha256": held_input_sha256, "EOF_probes": 1}
    for phase, stage in (("pass1", "pass1"), ("pass2", "pass2")):
        if report[phase] is not None:
            require(
                ("created" if phase == "pass1" else "rewind") in events,
                "cold-pass-prefix-reachability",
            )
        if stage in events:
            require(encode(report[phase]) == encode(expected_pass), "cold-pass-binding")
        elif report[phase] is not None:
            observed = report[phase]
            require(
                type(observed) is dict
                and set(observed) == set(expected_pass)
                and type(observed["bytes"]) is int
                and 0 <= observed["bytes"] <= len(raw)
                and observed["sha256"] == digest(raw[: observed["bytes"]])
                and type(observed["EOF_probes"]) is int
                and observed["EOF_probes"] in (0, 1)
                and (observed["EOF_probes"] == 0 or observed["bytes"] == len(raw))
                and report["error"] is not None,
                "cold-unfinished-pass",
            )
    require(
        report["fixture_auth_observation"]
        in (None, "fixture-controls-passed", "denied", "pending"),
        "cold-auth-observation",
    )
    if report["fixture_auth_observation"] is not None:
        require(
            "pass1" in events
            and len(report["tokens"]) >= 2
            and report["fixture_auth_observation"] == context["fixture_auth_status"],
            "cold-auth-prefix-reachability",
        )
        require(
            (report["fixture_auth_observation"] == "fixture-controls-passed")
            == ("fixture-auth" in events),
            "cold-auth-outcome-prefix",
        )
    if "fixture-auth" in events:
        require(
            context["fixture_auth_status"]
            == report["fixture_auth_observation"]
            == "fixture-controls-passed",
            "cold-auth-before-second-pass",
        )
    if "inventory" in events:
        require(
            encode(report["inventory"]) == encode(_headers(raw, held_input_sha256)),
            "cold-inventory",
        )
    else:
        require(report["inventory"] is None, "cold-no-premature-inventory")
    if report["status"] == "fixture-two-pass-completed":
        require(
            events == list(STAGES)
            and report["error"] is None
            and report["cleanup_error"] is None
            and report["owned_descriptor_closed"] is True
            and len(report["tokens"]) == 4
            and report["tokens"][0]["size"] == len(raw)
            and all(token == report["tokens"][0] for token in report["tokens"]),
            "cold-completion-lifecycle",
        )
    else:
        require(
            report["status"] == "incomplete"
            and (type(report["error"]) is str or type(report["cleanup_error"]) is str),
            "cold-incomplete-diagnostic",
        )
    return {
        "kind": "invented",
        "status": "fixture-metadata-consistent",
        "producer_status": report["status"],
        "physical_history_authenticated": False,
        "actual_authentication_admitted": False,
        "actual_execution_ready": False,
        "actual_archive_inspection_authorized": False,
        "authority": dict(AUTHORITY),
    }
