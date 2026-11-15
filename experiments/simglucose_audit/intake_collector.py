"""Closed public intake and source-bound, one-shot passive collector preparation.

Only caller-held private plan/approval/origin pins authorize collect_approved.
No approval registry, CLI activation, asset parsing or native use exists here.
Owned supervisors bound ordinary blocked transport/storage; they do not prove
preemption of uninterruptible kernel work or authenticated operating-system history.
"""

import base64
import hashlib
import os
import queue
import re
import socket
import ssl
import stat
import subprocess
import sys
import threading
import time
from datetime import UTC, datetime, timedelta
from pathlib import Path

from experiments import platform_process

from . import fixture_time
from .contract import AUTHORITY, decode, digest, encode, fields, require, source_identity

SCHEMA = "opent1d.simglucose-three-csv-intake/1"
REVISION = "a6f6777586c860457a2a1e6cce6d0bd3fd33d1cc"
HOST = "raw.githubusercontent.com"
ROOT = Path(__file__).resolve().parents[2]
SIZES = (17782, 224, 155)
NAMES = ("vpatient_params.csv", "sensor_params.csv", "pump_params.csv")
BLOBS = (
    "bdbabcb7f1b5b88ed9e3c1f1b65e41f1c5722319",
    "0c8ad25125e38b4b734d3c014138ec9c294c581e",
    "e4bae042a867fa295a8ce84eead0a7594c675472",
)
NOTICE_SHA = "ddfd0daee4b3569977580f2d4fc52ffc953c88db7b97f81abecfe2c003e10c75"
NOTICE = (b"INVENTED NOTICE FOR COLLECTOR FIXTURES ONLY\n" + b"x" * 1052)[:1052]
BODIES = tuple(bytes([65 + i]) * size for i, size in enumerate(SIZES))
LIMITS = {
    "whole_seconds": 90,
    "request_seconds": 30,
    "body_bytes": 18164,
    "receipt_bytes": 65536,
    "root_bytes": 84752,
    "header_bytes": 4096,
    "header_count": 32,
    "status_line_bytes": 256,
}
RETENTION = {
    "max_days": 30,
    "not_after_utc": "2026-12-06T00:00:00Z",
    "earlier_limits_win": True,
    "old_origins_reset": False,
    "unknown_origins_timely": False,
    "automatic_cleanup": False,
    "automatic_extension": False,
}
COVERAGE = ("intake-inputs", "collector-source", "notice-copy", "proof-allocation")
CASES = (
    "ok",
    "no-content-length",
    "extra-first",
    "short-first",
    "blob-first",
    "status-first",
    "redirect-first",
    "duplicate-cl",
    "duplicate-ce",
    "bad-cl",
    "transfer-encoding",
    "encoding",
    "bad-header",
    "header-overflow",
    "slow-headers",
    "slow-body",
    "stall-connect",
    "stall-storage",
    "outer-deadline",
)
TOKEN = re.compile(rb"[!#$%&'*+.^_`|~0-9A-Za-z-]+")
HEX = re.compile(r"[0-9a-f]{64}")


def run_intake(*_args, **_kwargs):
    raise PermissionError("intake is closed: no current exact private approval is installed")


def _identity():
    return source_identity() | {"intake_collector.py": digest(Path(__file__).read_bytes())}


def _owner():
    return {name: digest((ROOT / name).read_bytes()) for name in platform_process.SOURCE_FILES}


def _blob(raw):
    return hashlib.sha1(b"blob " + str(len(raw)).encode("ascii") + b"\0" + raw).hexdigest()


def _targets(fixture):
    return [
        {
            "name": name,
            "url": f"https://{HOST}/jxx123/simglucose/{REVISION}/simglucose/params/{name}",
            "revision": REVISION,
            "bytes": size,
            "sentinel_cap": size + 1,
            "git_blob_sha1": _blob(BODIES[i]) if fixture else BLOBS[i],
        }
        for i, (name, size) in enumerate(zip(NAMES, SIZES, strict=True))
    ]


def _utc(value):
    require(
        type(value) is str and re.fullmatch(r"\d{4}-\d\d-\d\dT\d\d:\d\d:\d\dZ", value),
        "canonical-UTC",
    )
    parsed = datetime.strptime(value, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=UTC)
    require(parsed.strftime("%Y-%m-%dT%H:%M:%SZ") == value, "canonical-UTC")
    return parsed


def _stamp(value):
    return value.astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def _now():
    return fixture_time.now()


@fixture_time.selected(7)
def _gate(
    plan_raw,
    plan_pin,
    approval_raw,
    approval_pin,
    notice_raw,
    origin_raw,
    origin_pin,
    fixture=False,
    _at=None,
):
    require(
        type(plan_raw) is bytes
        and len(plan_raw) <= 32768
        and type(approval_raw) is bytes
        and len(approval_raw) <= 32768
        and type(origin_raw) is bytes
        and len(origin_raw) <= 16384,
        "bounded-intake-contract-bytes",
    )
    require(
        digest(plan_raw) == plan_pin
        and digest(approval_raw) == approval_pin
        and digest(origin_raw) == origin_pin,
        "externally-held-input-pins",
    )
    plan, approval, origin = map(decode, (plan_raw, approval_raw, origin_raw))
    fields(
        plan,
        "schema kind source_identity process_owner_source_identity "
        "qualification_sha256 output_root targets notice limits retention "
        "origin_context_sha256",
        "intake-plan-fields",
    )
    require(
        plan["schema"] == SCHEMA
        and plan["kind"] == ("invented" if fixture else "passive-intake-plan"),
        "exact-intake-plan-kind",
    )
    require(
        plan["source_identity"] == _identity()
        and plan["process_owner_source_identity"] == _owner(),
        "current-collector-source",
    )
    require(
        type(plan["qualification_sha256"]) is str and HEX.fullmatch(plan["qualification_sha256"]),
        "held-qualification-identity",
    )
    require(
        encode(plan["targets"]) == encode(_targets(fixture))
        and encode(plan["limits"]) == encode(LIMITS)
        and encode(plan["retention"]) == encode(RETENTION),
        "fixed-three-target-scope",
    )
    expected_notice = {"bytes": 1052, "sha256": digest(NOTICE) if fixture else NOTICE_SHA}
    require(
        encode(plan["notice"]) == encode(expected_notice)
        and type(notice_raw) is bytes
        and len(notice_raw) == 1052
        and digest(notice_raw) == expected_notice["sha256"],
        "notice-byte-pin",
    )
    require(
        type(plan["output_root"]) is str
        and Path(plan["output_root"]).is_absolute()
        and ".." not in Path(plan["output_root"]).parts,
        "exact-trusted-output-root",
    )
    fields(
        origin,
        "schema kind coverage origins_verified unknown_required_origins records retention",
        "origin-context-fields",
    )
    require(
        origin["schema"] == SCHEMA
        and origin["kind"] == ("invented" if fixture else "private-intake-origin-context")
        and origin["coverage"] == list(COVERAGE)
        and origin["origins_verified"] is True
        and origin["unknown_required_origins"] == []
        and encode(origin["retention"]) == encode(RETENTION)
        and plan["origin_context_sha256"] == origin_pin,
        "pinned-required-origins",
    )
    require(
        type(origin["records"]) is list and len(origin["records"]) == 4, "origin-evidence-roster"
    )
    now, deadlines = _now() if _at is None else _at, [_utc(RETENTION["not_after_utc"])]
    for subject, row in zip(COVERAGE, origin["records"], strict=True):
        fields(
            row, "subject origin_utc deadline_utc evidence_sha256 basis", "origin-evidence-fields"
        )
        require(
            row["subject"] == subject
            and row["basis"] == "private-copy-or-acquisition-evidence"
            and type(row["evidence_sha256"]) is str
            and HEX.fullmatch(row["evidence_sha256"]),
            "origin-evidence-binding",
        )
        start, end = _utc(row["origin_utc"]), _utc(row["deadline_utc"])
        require(start <= now < end <= start + timedelta(days=30), "origin-timing")
        deadlines.append(end)
    fields(
        approval,
        "schema kind plan_sha256 source_identity process_owner_source_identity "
        "nonce issued_utc expires_utc origin_context_sha256 scope authority",
        "approval-fields",
    )
    require(
        approval["schema"] == SCHEMA
        and approval["kind"] == ("invented" if fixture else "explicit-user-approval")
        and approval["plan_sha256"] == plan_pin
        and approval["source_identity"] == plan["source_identity"]
        and approval["process_owner_source_identity"] == plan["process_owner_source_identity"]
        and approval["origin_context_sha256"] == origin_pin,
        "approval-source-plan-binding",
    )
    require(
        type(approval["nonce"]) is str and re.fullmatch(r"[0-9a-f]{32}", approval["nonce"]),
        "one-shot-nonce",
    )
    issued, expires = _utc(approval["issued_utc"]), _utc(approval["expires_utc"])
    require(
        issued <= now < expires <= issued + timedelta(days=30) and expires <= min(deadlines),
        "approval-expiry",
    )
    if _at is None:
        require(
            (min(expires, *deadlines) - now).total_seconds() >= 100, "retention-closure-headroom"
        )
    require(
        approval["scope"] == "passive-three-csv-intake-once"
        and encode(approval["authority"]) == encode(dict(AUTHORITY) | {"passive_intake": True}),
        "passive-only-approval",
    )
    return plan, min(expires, *deadlines)


def _directory(path, fresh=False):
    path = Path(path)
    require(
        path.is_absolute() and ".." not in path.parts and len(path.parts) > 1,
        "private-absolute-root",
    )
    flags = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW
    fd = os.open(path.anchor, flags)
    try:
        for i, part in enumerate(path.parts[1:]):
            if fresh and i == len(path.parts) - 2:
                os.mkdir(part, 0o700, dir_fd=fd)
                os.fsync(fd)
            nxt = os.open(part, flags, dir_fd=fd)
            os.close(fd)
            fd = nxt
        _private_directory(fd)
        return fd
    except BaseException:
        os.close(fd)
        raise


def _private_directory(fd):
    info = os.fstat(fd)
    require(
        stat.S_ISDIR(info.st_mode)
        and stat.S_IMODE(info.st_mode) == 0o700
        and (not hasattr(os, "getuid") or info.st_uid == os.getuid()),
        "private-directory-mode-owner",
    )


def _regular(fd):
    info = os.fstat(fd)
    require(
        stat.S_ISREG(info.st_mode)
        and stat.S_IMODE(info.st_mode) == 0o600
        and info.st_nlink == 1
        and (not hasattr(os, "getuid") or info.st_uid == os.getuid()),
        "private-regular-file-mode-owner-links",
    )
    return info


def _fingerprint(info):
    return (
        info.st_dev,
        info.st_ino,
        info.st_size,
        info.st_mtime_ns,
        info.st_ctime_ns,
        info.st_mode,
        info.st_uid,
        info.st_nlink,
    )


def _write_file(directory, name, raw):
    fd = os.open(
        name, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600, dir_fd=directory
    )
    try:
        before = _regular(fd)
        view = memoryview(raw)
        while view:
            written = os.write(fd, view)
            require(written > 0, "short-file-write")
            view = view[written:]
        os.fsync(fd)
        after = _regular(fd)
        named = os.stat(name, dir_fd=directory, follow_symlinks=False)
        require(
            (before.st_dev, before.st_ino)
            == (after.st_dev, after.st_ino)
            == (named.st_dev, named.st_ino)
            and _fingerprint(after) == _fingerprint(named),
            "exclusive-write-binding",
        )
    finally:
        os.close(fd)
    os.fsync(directory)


def _headers(raw, expected):
    require(len(raw) <= 4096 and raw.endswith(b"\r\n\r\n"), "bounded-response-headers")
    lines = raw[:-4].split(b"\r\n")
    require(
        len(lines[0]) <= 256 and re.fullmatch(rb"HTTP/1\.[01] [0-9]{3}(?: [ -~]*)?", lines[0]),
        "HTTP-status-syntax",
    )
    status = int(lines[0][9:12])
    require(status == 200, "HTTP-status-not-200")
    require(len(lines) - 1 <= 32, "header-count")
    values = {}
    for line in lines[1:]:
        name, colon, value = line.partition(b":")
        require(
            colon and TOKEN.fullmatch(name) and all(32 <= c <= 126 for c in value), "header-syntax"
        )
        values.setdefault(name.lower(), []).append(value.strip(b" "))
    require(
        b"transfer-encoding" not in values and b"content-range" not in values, "unsupported-framing"
    )
    length = values.get(b"content-length", [])
    require(len(length) <= 1, "ambiguous-content-length")
    if length:
        require(
            re.fullmatch(rb"[0-9]{1,6}", length[0]) and int(length[0]) == expected,
            "content-length-mismatch",
        )
    coding = values.get(b"content-encoding", [])
    require(
        len(coding) <= 1 and (not coding or coding[0].lower() == b"identity"), "content-encoding"
    )
    return {
        "status": status,
        "content_length": expected if length else None,
        "content_encoding": "identity" if coding else "absent",
        "header_bytes": len(raw),
        "header_count": len(lines) - 1,
    }


def _open_https():
    context = ssl.create_default_context()
    context.minimum_version = ssl.TLSVersion.TLSv1_2
    require(
        context.verify_mode == ssl.CERT_REQUIRED and context.check_hostname is True,
        "verified-TLS-required",
    )
    context.keylog_filename = None
    sock = socket.create_connection((HOST, 443), timeout=30)
    try:
        return context.wrap_socket(sock, server_hostname=HOST)
    except BaseException:
        sock.close()
        raise


class _FixtureSocket:
    def __init__(self, index, case):
        body = BODIES[index]
        status, headers = b"200 OK", [b"Content-Length: " + str(len(body)).encode()]
        if index == 0:
            if case == "extra-first":
                body += b"!"
            if case == "short-first":
                body = body[:-1]
            if case == "blob-first":
                body = b"Z" + body[1:]
            if case == "status-first":
                status = b"500 Failed"
            if case == "redirect-first":
                status = b"302 Found"
            if case == "no-content-length":
                headers = []
            if case == "duplicate-cl":
                headers *= 2
            if case == "duplicate-ce":
                headers += [b"Content-Encoding: identity"] * 2
            if case == "bad-cl":
                headers = [b"Content-Length: 1, 17782"]
            if case == "transfer-encoding":
                headers += [b"Transfer-Encoding: chunked"]
            if case == "encoding":
                headers += [b"Content-Encoding: gzip"]
            if case == "bad-header":
                headers += [b"Content-Length : 17782"]
            if case == "header-overflow":
                headers += [b"X-Pad: " + b"x" * 4096]
            if case in ("stall-connect", "outer-deadline"):
                time.sleep(5)
        header = (
            b"HTTP/1.1 "
            + status
            + b"\r\n"
            + b"\r\n".join(headers)
            + (b"\r\n" if headers else b"")
            + b"\r\n"
        )
        self.raw, self.cursor, self.header_length, self.case = header + body, 0, len(header), case

    def sendall(self, raw):
        require(
            raw.startswith(b"GET /jxx123/simglucose/")
            and b"Accept-Encoding: identity\r\nConnection: close\r\n" in raw,
            "fixed-GET-request",
        )

    def recv(self, maximum):
        if self.case == "slow-headers" and self.cursor < self.header_length:
            time.sleep(0.05)
        if self.case == "slow-body" and self.cursor >= self.header_length:
            time.sleep(0.05)
            maximum = min(maximum, 1)
        value = self.raw[self.cursor : self.cursor + maximum]
        self.cursor += len(value)
        return value

    def close(self):
        pass


def _emit(event):
    raw = encode(event)
    require(len(raw) <= 65536, "bounded-child-frame")
    sys.stdout.buffer.write(raw + b"\n")
    sys.stdout.buffer.flush()


def _fetch(index, case):
    """Shared strict raw HTTP path; Content-Length never masks a sentinel."""
    require(
        type(index) is int and 0 <= index < 3 and (case is None or case in CASES),
        "fixed-fetch-target",
    )
    connection = _open_https() if case is None else _FixtureSocket(index, case)
    try:
        path = f"/jxx123/simglucose/{REVISION}/simglucose/params/{NAMES[index]}".encode()
        connection.sendall(
            b"GET "
            + path
            + b" HTTP/1.1\r\nHost: "
            + HOST.encode()
            + b"\r\nAccept-Encoding: identity\r\nConnection: close\r\n\r\n"
        )
        header = bytearray()
        while not header.endswith(b"\r\n\r\n"):
            require(len(header) < 4096, "bounded-response-headers")
            part = connection.recv(1)
            require(part, "truncated-response-headers")
            header += part
        _emit({"phase": "headers", "observation": _headers(bytes(header), SIZES[index])})
        consumed = 0
        while consumed < SIZES[index] + 1:
            raw = connection.recv(min(4096, SIZES[index] + 1 - consumed))
            if not raw:
                break
            require(len(raw) <= SIZES[index] + 1 - consumed, "raw-read-cap")
            consumed += len(raw)
            _emit({"phase": "body", "bytes_b64": base64.b64encode(raw).decode("ascii")})
        _emit({"phase": "done", "bytes": consumed})
    finally:
        connection.close()


def _fixture_fetch(index, case):
    require(type(case) is str and case in CASES, "fixed-fixture-case")

    def deny(event, _args):
        if event in ("socket.connect", "socket.getaddrinfo"):
            raise PermissionError("fixture-network-denied")

    sys.addaudithook(deny)
    _fetch_entry(index, case)


def _fetch_entry(index, case=None):
    try:
        _fetch(index, case)
    except (OSError, ValueError, TimeoutError):
        _emit({"phase": "error", "reason": "transport-or-header-rejection"})


def _script(call):
    return (
        "import sys; sys.path.insert(0, "
        + repr(str(ROOT))
        + "); from experiments.simglucose_audit.intake_collector import "
        + call
    )


def _environment():
    return {"PATH": os.defpath, "LANG": "C", "LC_ALL": "C"}


def _reader(stream, events, maximum=65536):
    try:
        for _ in range(32):
            raw = stream.readline(maximum + 1)
            if not raw:
                events.put_nowait(("eof", None))
                return
            require(len(raw) <= maximum and raw.endswith(b"\n"), "bounded-process-frame")
            events.put_nowait(("frame", decode(raw)))
        events.put_nowait(("error", "too-many-process-frames"))
    except (OSError, ValueError):
        events.put_nowait(("error", "invalid-process-frame"))


def _finish_process(process, reader, owned):
    error = None
    try:
        if process.poll() is None:
            if owned:
                platform_process.force_tree(process)
            else:
                process.kill()  # Fixed leaf, inherits the outer owned session/Job.
            process.wait(timeout=1)
        if owned:
            if platform_process.tree_exists(process):
                error = "owned-tree-remains"
            else:
                platform_process.close_tree(process)
    except (OSError, RuntimeError, subprocess.TimeoutExpired):
        error = "owned-stop-failed"
    reader.join(timeout=1)
    if reader.is_alive():
        error = error or "reader-not-joined"
    else:
        try:
            process.stdout.close()
        except OSError:
            error = error or "pipe-close-failed"
    return error


def _one_request(index, case, deadline, seconds):
    start = time.monotonic()
    started_utc, before = _stamp(_now()), _identity()
    deadline = min(deadline, start + seconds - min(2, seconds / 2))
    call = (
        f"_fixture_fetch; _fixture_fetch({index}, {case!r})"
        if case is not None
        else f"_fetch_entry; _fetch_entry({index})"
    )
    process = subprocess.Popen(
        [sys.executable, "-I", "-S", "-B", "-c", _script(call)],
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        cwd=ROOT,
        env=_environment(),
    )
    reader, started = None, False
    body, headers, done, error = bytearray(), None, False, None
    try:
        _emit(
            {
                "phase": "request-launched",
                "index": index,
                "pid": process.pid,
                "owner_group": os.getpgrp() if os.name != "nt" else None,
                "leaf_group": os.getpgid(process.pid) if os.name != "nt" else None,
            }
        )
        events = queue.Queue(maxsize=40)
        reader = threading.Thread(target=_reader, args=(process.stdout, events), daemon=True)
        reader.start()
        started = True
        while True:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                error = "request-deadline"
                break
            try:
                kind, value = events.get(timeout=remaining)
            except queue.Empty:
                error = "request-deadline"
                break
            if kind == "error":
                error = value
                break
            if kind == "eof":
                process.wait(timeout=max(0.001, deadline - time.monotonic()))
                if not done or process.returncode != 0:
                    error = "incomplete-response"
                break
            phase = value.get("phase") if type(value) is dict else None
            if phase == "headers":
                fields(value, "phase observation", "headers-frame")
                require(headers is None and not body and not done, "headers-sequence")
                headers = value["observation"]
            elif phase == "body":
                fields(value, "phase bytes_b64", "body-frame")
                require(
                    headers is not None and not done and type(value["bytes_b64"]) is str,
                    "body-sequence",
                )
                raw = base64.b64decode(value["bytes_b64"], validate=True)
                require(
                    0 < len(raw) <= 4096 and len(body) + len(raw) <= SIZES[index] + 1,
                    "body-sentinel-cap",
                )
                body += raw
                _emit({"phase": "acquired-chunk", "index": index, "bytes_b64": value["bytes_b64"]})
            elif phase == "done":
                fields(value, "phase bytes", "done-frame")
                require(
                    headers is not None
                    and not done
                    and type(value["bytes"]) is int
                    and value["bytes"] == len(body),
                    "done-sequence",
                )
                done = True
            elif phase == "error":
                fields(value, "phase reason", "error-frame")
                error = "transport-or-header-rejection"
                break
            else:
                raise ValueError("fixed-response-phase")
    except (OSError, ValueError, RuntimeError, subprocess.TimeoutExpired):
        error = "invalid-response-protocol"
    finally:
        if started:
            cleanup = _finish_process(process, reader, False)
        else:
            cleanup = None
            try:
                if process.poll() is None:
                    process.kill()
                    process.wait(timeout=1)
                process.stdout.close()
            except (OSError, subprocess.TimeoutExpired):
                cleanup = "request-cleanup-failed"
    return (
        bytes(body),
        headers,
        error or cleanup,
        {
            "pid": process.pid,
            "returncode": process.returncode,
            "cleanup_error": cleanup,
            "elapsed_ns": max(0, int((time.monotonic() - start) * 1e9)),
            "started_utc": started_utc,
            "ended_utc": _stamp(_now()),
            "source_before": before,
            "source_after": _identity(),
        },
    )


def _receipt_base(wire):
    plan = decode(base64.b64decode(wire["plan"]))
    return {
        "schema": SCHEMA,
        "kind": "invented" if wire["case"] is not None else "passive-intake",
        "source_identity": _identity(),
        "process_owner_source_identity": _owner(),
        "plan_sha256": wire["plan_pin"],
        "approval_sha256": wire["approval_pin"],
        "origin_context_sha256": wire["origin_pin"],
        "notice": plan["notice"],
        "retention": RETENTION,
        "targets": [
            dict(
                row,
                status="not-run",
                actual_bytes=0,
                body_path=None,
                accepted_sha256=None,
                computed_git_blob_sha1=None,
                headers=None,
                process=None,
                error=None,
            )
            for row in plan["targets"]
        ],
        "inventory": {},
        "status": "incomplete",
        "error": None,
        "approval_consumed": True,
        "authority": dict(AUTHORITY),
        "actual_HTTPS_qualified": False,
        "controller_pid": os.getpid(),
        "controller_started_utc": _stamp(_now()),
        "controller_ended_utc": None,
        "source_identity_after": None,
        "nonce_sha256": digest(decode(base64.b64decode(wire["approval"]))["nonce"].encode("ascii")),
        "controller_elapsed_ns": None,
    }


def _store_receipt(directory, receipt):
    raw = encode(receipt)
    require(len(raw) <= 65536, "bounded-receipt")
    name = (
        "intake-receipt.private.json"
        if receipt["status"] == "completed"
        else "intake-failure.private.json"
    )
    _write_file(directory, name, raw)
    return raw


def _controller(wire):
    with fixture_time.use(wire["case"] is not None):
        plan_raw, approval_raw, origin_raw, notice_raw = (
            base64.b64decode(wire[name], validate=True)
            for name in ("plan", "approval", "origin", "notice")
        )
        plan, expiry = _gate(
            plan_raw,
            wire["plan_pin"],
            approval_raw,
            wire["approval_pin"],
            notice_raw,
            origin_raw,
            wire["origin_pin"],
            wire["case"] is not None,
        )
        deadline = min(
            time.monotonic() + wire["whole_seconds"],
            time.monotonic() + max(0, (expiry - _now()).total_seconds()),
        )
        directory = _directory(plan["output_root"], fresh=True)
        receipt = _receipt_base(wire)
        try:
            os.mkdir("objects", 0o700, dir_fd=directory)
            os.mkdir("notices", 0o700, dir_fd=directory)
            os.fsync(directory)
            notices = os.open(
                "notices", os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=directory
            )
            try:
                _write_file(notices, "simglucose-LICENSE.txt", notice_raw)
            finally:
                os.close(notices)
            receipt["inventory"]["notices/simglucose-LICENSE.txt"] = {
                "bytes": len(notice_raw),
                "sha256": digest(notice_raw),
            }
            _emit({"phase": "notice-preserved"})
            objects = os.open(
                "objects", os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=directory
            )
            try:
                for index, row in enumerate(receipt["targets"]):
                    if time.monotonic() >= deadline:
                        row.update(status="incomplete", error="whole-deadline")
                        break
                    _emit({"phase": "target-start", "index": index})
                    body, headers, error, observed = _one_request(
                        index, wire["case"], deadline, wire["request_seconds"]
                    )
                    row.update(actual_bytes=len(body), headers=headers, process=observed)
                    if body:
                        if wire["case"] == "stall-storage" and index == 0:
                            time.sleep(5)
                        _write_file(objects, row["name"], body)
                        row["body_path"] = "objects/" + row["name"]
                        receipt["inventory"][row["body_path"]] = {
                            "bytes": len(body),
                            "sha256": digest(body),
                        }
                    if error:
                        row.update(
                            status="incomplete" if "deadline" in error else "rejected", error=error
                        )
                    elif len(body) != row["bytes"]:
                        row.update(status="rejected", error="body-size")
                    else:
                        row["computed_git_blob_sha1"] = _blob(body)
                        if row["computed_git_blob_sha1"] != row["git_blob_sha1"]:
                            row.update(status="rejected", error="git-blob-mismatch")
                        else:
                            row.update(status="accepted", accepted_sha256=digest(body))
                    if time.monotonic() >= deadline:
                        row.update(status="incomplete", error="whole-deadline")
                    _emit({"phase": "target-finish", "index": index, "row": row})
                    if row["status"] != "accepted":
                        break
            finally:
                os.close(objects)
            receipt["status"] = (
                "completed"
                if all(row["status"] == "accepted" for row in receipt["targets"])
                else "incomplete"
            )
            if time.monotonic() >= deadline:
                receipt.update(status="incomplete", error="whole-deadline")
            require(_identity() == plan["source_identity"], "source-changed-during-intake")
            receipt.update(
                controller_ended_utc=_stamp(_now()),
                source_identity_after=_identity(),
                controller_elapsed_ns=max(0, time.monotonic_ns() - wire["started_monotonic_ns"]),
            )
            raw = _store_receipt(directory, receipt)
            require(time.monotonic() < deadline, "finalization-deadline")
            _emit({"phase": "receipt", "receipt_b64": base64.b64encode(raw).decode("ascii")})
        finally:
            os.close(directory)


def _wire(value, recovery=False):
    names = (
        "plan approval origin notice plan_pin approval_pin origin_pin case "
        "whole_seconds request_seconds started_utc started_monotonic_ns"
    )
    if recovery:
        names += " acquisition_error progress acquired"
    fields(value, names, "fixed-private-wire-fields")
    require(
        value["case"] is None or type(value["case"]) is str and value["case"] in CASES,
        "fixed-private-transport-kind",
    )
    require(
        type(value["whole_seconds"]) in (int, float)
        and 0 < value["whole_seconds"] <= (2 if recovery else 90)
        and type(value["request_seconds"]) in (int, float)
        and 0 < value["request_seconds"] <= 30,
        "private-wire-budget-caps",
    )
    require(
        type(value["started_monotonic_ns"]) is int and value["started_monotonic_ns"] > 0,
        "private-wire-clock",
    )
    _utc(value["started_utc"])
    return value


def _controller_entry():
    try:
        raw = sys.stdin.buffer.read(262145)
        require(len(raw) <= 262144, "bounded-private-wire")
        wire = _wire(decode(raw))
        _controller(wire)
    except (OSError, ValueError, TimeoutError):
        _emit({"phase": "controller-error", "reason": "controller-or-storage-failure"})


def _recovery_entry():
    try:
        raw = sys.stdin.buffer.read(262145)
        require(len(raw) <= 262144, "bounded-private-wire")
        wire = _wire(decode(raw), recovery=True)
        with fixture_time.use(wire["case"] is not None):
            plan_raw, approval_raw, origin_raw, notice = (
                base64.b64decode(wire[name], validate=True)
                for name in ("plan", "approval", "origin", "notice")
            )
            plan, _expiry = _gate(
                plan_raw,
                wire["plan_pin"],
                approval_raw,
                wire["approval_pin"],
                notice,
                origin_raw,
                wire["origin_pin"],
                wire["case"] is not None,
                _at=_utc(wire["started_utc"]),
            )
            origin = decode(origin_raw)
            retention_deadline = min(
                _expiry,
                _utc(RETENTION["not_after_utc"]),
                *(_utc(row["deadline_utc"]) for row in origin["records"]),
            )
            require(
                _now() + timedelta(seconds=5) < retention_deadline,
                "current-retention-before-recovery",
            )
            directory = _directory(plan["output_root"])
            try:
                names = set(os.listdir(directory))
                require(
                    not names & {"intake-receipt.private.json", "intake-failure.private.json"},
                    "unissued-existing-receipt-preserved",
                )
                receipt = _receipt_base(wire)
                receipt.update(
                    error=wire["acquisition_error"], controller_started_utc=wire["started_utc"]
                )
                notices = os.open(
                    "notices", os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=directory
                )
                try:
                    copied_notice = _read_file(notices, "simglucose-LICENSE.txt", 1052)
                    require(copied_notice == notice, "notice-before-recovery")
                finally:
                    os.close(notices)
                receipt["inventory"]["notices/simglucose-LICENSE.txt"] = {
                    "bytes": len(notice),
                    "sha256": digest(notice),
                }
                objects = os.open(
                    "objects", os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=directory
                )
                try:
                    existing = set(os.listdir(objects))
                    require(existing <= set(NAMES), "fixed-recovery-objects")
                    finished = {
                        item["index"]: item["row"]
                        for item in wire["progress"]
                        if item["phase"] == "target-finish"
                    }
                    started = {
                        item["index"]
                        for item in wire["progress"]
                        if item["phase"] == "target-start"
                    }
                    stopped = False
                    for index, row in enumerate(receipt["targets"]):
                        published = base64.b64decode(
                            wire["acquired"].get(str(index), ""), validate=True
                        )
                        require(len(published) <= SIZES[index] + 1, "bounded-recovery-prefix")
                        if row["name"] not in existing and published:
                            require(
                                _now() < retention_deadline,
                                "current-retention-before-preservation-write",
                            )
                            _write_file(objects, row["name"], published)
                        body = (
                            _read_file(objects, row["name"], SIZES[index] + 1)
                            if row["name"] in existing or published
                            else b""
                        )
                        require(not body or published.startswith(body), "published-prefix-binding")
                        if index in finished and not stopped:
                            row.update(finished[index])
                        elif index in started or body:
                            row.update(status="incomplete", error=wire["acquisition_error"])
                            stopped = True
                        retained = row["name"] in existing or bool(published)
                        row.update(
                            actual_bytes=len(body),
                            body_path="objects/" + row["name"] if retained else None,
                        )
                        if row["status"] != "accepted":
                            row["accepted_sha256"] = None
                        if retained:
                            receipt["inventory"][row["body_path"]] = {
                                "bytes": len(body),
                                "sha256": digest(body),
                            }
                    receipt.update(
                        status="incomplete",
                        controller_ended_utc=_stamp(_now()),
                        source_identity_after=_identity(),
                        controller_elapsed_ns=max(
                            0, time.monotonic_ns() - wire["started_monotonic_ns"]
                        ),
                    )
                    require(_now() < retention_deadline, "current-retention-before-failure-receipt")
                    receipt_raw = _store_receipt(directory, receipt)
                    _emit(
                        {
                            "phase": "receipt",
                            "receipt_b64": base64.b64encode(receipt_raw).decode("ascii"),
                        }
                    )
                finally:
                    os.close(objects)
            finally:
                os.close(directory)
    except (OSError, ValueError, TimeoutError):
        _emit({"phase": "controller-error", "reason": "bounded-failure-preservation-incomplete"})


def _writer(stream, raw):
    try:
        stream.write(raw)
        stream.close()
    except (OSError, ValueError):
        try:
            stream.close()
        except (OSError, ValueError):
            pass


def _supervise(wire, recovery=False):
    start = time.monotonic()
    deadline = start + wire["whole_seconds"]
    process = platform_process.spawn(
        [
            sys.executable,
            "-I",
            "-S",
            "-B",
            "-c",
            _script(
                "_recovery_entry; _recovery_entry()"
                if recovery
                else "_controller_entry; _controller_entry()"
            ),
        ],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        cwd=ROOT,
        env=_environment(),
    )
    reader, writer, started = None, None, []
    receipt_raw, error, progress, acquired = None, None, [], {}
    try:
        events = queue.Queue(maxsize=40)
        reader = threading.Thread(target=_reader, args=(process.stdout, events, 90000), daemon=True)
        writer = threading.Thread(target=_writer, args=(process.stdin, encode(wire)), daemon=True)
        for thread in (reader, writer):
            thread.start()
            started.append(thread)
        while True:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                error = "whole-deadline"
                break
            try:
                kind, value = events.get(timeout=remaining)
            except queue.Empty:
                error = "whole-deadline"
                break
            if kind == "error":
                error = value
                break
            if kind == "eof":
                process.wait(timeout=max(0.001, deadline - time.monotonic()))
                if process.returncode != 0 or receipt_raw is None:
                    error = "controller-incomplete"
                break
            require(
                type(value) is dict
                and value.get("phase")
                in (
                    "notice-preserved",
                    "target-start",
                    "request-launched",
                    "target-finish",
                    "acquired-chunk",
                    "receipt",
                    "controller-error",
                ),
                "fixed-controller-phase",
            )
            if value["phase"] == "acquired-chunk":
                fields(value, "phase index bytes_b64", "acquired-chunk-fields")
                index = value["index"]
                require(type(index) is int and 0 <= index < 3, "fixed-acquired-target")
                raw = base64.b64decode(value["bytes_b64"], validate=True)
                require(0 < len(raw) <= 4096, "bounded-acquired-chunk")
                acquired[index] = acquired.get(index, b"") + raw
                require(
                    len(acquired[index]) <= SIZES[index] + 1
                    and sum(map(len, acquired.values())) <= 18164,
                    "published-body-cap",
                )
            elif value["phase"] == "receipt":
                require(receipt_raw is None, "one-receipt-frame")
                receipt_raw = base64.b64decode(value["receipt_b64"], validate=True)
                require(len(receipt_raw) <= 65536, "bounded-receipt")
            elif value["phase"] == "controller-error":
                error = "controller-or-storage-failure"
                break
            else:
                progress.append(value)
    except (OSError, ValueError, RuntimeError, subprocess.TimeoutExpired):
        error = "controller-protocol-failure"
    finally:
        cleanup = None
        if reader in started:
            cleanup = _finish_process(process, reader, True)
        else:
            try:
                if process.poll() is None:
                    platform_process.force_tree(process)
                    process.wait(timeout=1)
                if platform_process.tree_exists(process):
                    cleanup = "owned-tree-remains"
                else:
                    platform_process.close_tree(process)
            except (OSError, RuntimeError, subprocess.TimeoutExpired):
                cleanup = "owned-stop-failed"
            try:
                process.stdout.close()
            except OSError:
                cleanup = cleanup or "pipe-close-failed"
        if writer in started:
            writer.join(timeout=1)
            if writer.is_alive():
                cleanup = cleanup or "writer-not-joined"
        elif not process.stdin.closed:
            try:
                process.stdin.close()
            except OSError:
                cleanup = cleanup or "pipe-close-failed"
    if error or cleanup:
        return {
            "kind": "invented" if wire["case"] is not None else "passive-intake",
            "status": "incomplete",
            "error": error or cleanup,
            "receipt_sha256": None,
            "progress": progress,
            "owned_cleanup_error": cleanup,
            "parent_pid": os.getpid(),
            "controller_pid": process.pid,
            "returncode": process.returncode,
            "actual_HTTPS_qualified": False,
            "_acquired": acquired,
        }
    receipt = decode(receipt_raw)
    return {
        "kind": receipt["kind"],
        "status": receipt["status"],
        "receipt_sha256": digest(receipt_raw),
        "receipt": receipt,
        "owned_cleanup_error": None,
        "parent_pid": os.getpid(),
        "controller_pid": process.pid,
        "returncode": process.returncode,
        "actual_HTTPS_qualified": False,
    }


def _collect(
    plan_raw, plan_pin, approval_raw, approval_pin, notice_raw, origin_raw, origin_pin, case=None
):
    with fixture_time.use(case is not None):
        _plan, expiry = _gate(
            plan_raw,
            plan_pin,
            approval_raw,
            approval_pin,
            notice_raw,
            origin_raw,
            origin_pin,
            case is not None,
        )
        whole = min(90, max(0, (expiry - _now()).total_seconds()))
        request = 30
        if case in ("slow-headers", "slow-body", "stall-connect"):
            request = 0.2
        if case in ("stall-storage", "outer-deadline"):
            whole = min(whole, 0.3)
        wire = {
            name: base64.b64encode(raw).decode("ascii")
            for name, raw in (
                ("plan", plan_raw),
                ("approval", approval_raw),
                ("notice", notice_raw),
                ("origin", origin_raw),
            )
        }
        wire.update(
            plan_pin=plan_pin,
            approval_pin=approval_pin,
            origin_pin=origin_pin,
            case=case,
            whole_seconds=whole,
            request_seconds=request,
            started_utc=_stamp(_now()),
            started_monotonic_ns=time.monotonic_ns(),
        )
        result = _supervise(wire)
        acquired = result.pop("_acquired", {})
        if result["receipt_sha256"] is None and result["owned_cleanup_error"] is None:
            failure = dict(
                wire,
                whole_seconds=2,
                acquisition_error=result["error"],
                progress=result.get("progress", []),
                acquired={
                    str(index): base64.b64encode(body).decode("ascii")
                    for index, body in acquired.items()
                },
            )
            recovered = _supervise(failure, recovery=True)
            recovered.pop("_acquired", None)
            if recovered["receipt_sha256"] is not None:
                recovered["acquisition_error"] = result["error"]
                recovered["acquisition_process"] = {
                    key: result[key]
                    for key in ("controller_pid", "returncode", "owned_cleanup_error")
                }
                recovered["acquisition_progress"] = result.get("progress", [])
                result = recovered
            else:
                result["failure_preservation_error"] = recovered.get(
                    "error", "failure-preservation-incomplete"
                )
        if (
            _identity() != _plan["source_identity"]
            or _owner() != _plan["process_owner_source_identity"]
        ):
            result.update(status="incomplete", error="source-changed", receipt_sha256=None)
        return result


@fixture_time.actual
def collect_approved(
    plan_raw,
    expected_plan_sha256,
    approval_raw,
    expected_approval_sha256,
    notice_raw,
    origin_raw,
    expected_origin_sha256,
):
    """Trusted-controller API; no real approval is shipped or registered."""
    return _collect(
        plan_raw,
        expected_plan_sha256,
        approval_raw,
        expected_approval_sha256,
        notice_raw,
        origin_raw,
        expected_origin_sha256,
    )


@fixture_time.invented
def fixture_inputs(destination):
    """Invented approval/context bytes cannot enter collect_approved."""
    now = _now().replace(microsecond=0) - timedelta(seconds=1)
    end = min(now + timedelta(hours=1), _utc(RETENTION["not_after_utc"]))
    origin = {
        "schema": SCHEMA,
        "kind": "invented",
        "coverage": list(COVERAGE),
        "origins_verified": True,
        "unknown_required_origins": [],
        "retention": RETENTION,
        "records": [
            {
                "subject": subject,
                "origin_utc": _stamp(now),
                "deadline_utc": _stamp(end),
                "evidence_sha256": digest(("invented-origin:" + subject).encode()),
                "basis": "private-copy-or-acquisition-evidence",
            }
            for subject in COVERAGE
        ],
    }
    origin_raw = encode(origin)
    plan = {
        "schema": SCHEMA,
        "kind": "invented",
        "source_identity": _identity(),
        "process_owner_source_identity": _owner(),
        "qualification_sha256": digest(b"invented-qualification-only"),
        "output_root": str(destination),
        "targets": _targets(True),
        "notice": {"bytes": len(NOTICE), "sha256": digest(NOTICE)},
        "limits": LIMITS,
        "retention": RETENTION,
        "origin_context_sha256": digest(origin_raw),
    }
    plan_raw = encode(plan)
    approval = {
        "schema": SCHEMA,
        "kind": "invented",
        "plan_sha256": digest(plan_raw),
        "source_identity": plan["source_identity"],
        "process_owner_source_identity": plan["process_owner_source_identity"],
        "nonce": "1" * 32,
        "issued_utc": _stamp(now),
        "expires_utc": _stamp(end),
        "origin_context_sha256": digest(origin_raw),
        "scope": "passive-three-csv-intake-once",
        "authority": dict(AUTHORITY) | {"passive_intake": True},
    }
    return plan_raw, encode(approval), NOTICE, origin_raw


@fixture_time.invented
def run_fixture_collector(raw, destination):
    value = decode(raw)
    fields(value, "schema kind case", "fixture-intake-fields")
    require(
        value["schema"] == SCHEMA
        and value["kind"] == "invented"
        and type(value["case"]) is str
        and value["case"] in CASES,
        "fixed-invented-intake",
    )
    plan, approval, notice, origin = fixture_inputs(destination)
    return _collect(
        plan,
        digest(plan),
        approval,
        digest(approval),
        notice,
        origin,
        digest(origin),
        value["case"],
    )


def _read_file(directory, name, maximum):
    fd = os.open(name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=directory)
    try:
        before = _regular(fd)
        chunks, total = [], 0
        while total <= maximum:
            raw = os.read(fd, min(4096, maximum + 1 - total))
            if not raw:
                break
            chunks.append(raw)
            total += len(raw)
        require(total <= maximum, "bounded-intake-file")
        after = _regular(fd)
        named = os.stat(name, dir_fd=directory, follow_symlinks=False)
        require(
            _fingerprint(before) == _fingerprint(after) == _fingerprint(named),
            "stable-intake-byte-snapshot",
        )
        return b"".join(chunks)
    finally:
        os.close(fd)


def read_intake_fixture(destination):
    """Bounded byte loader only; successful producer receipt pin is external."""
    directory = _directory(destination)
    result = {}
    try:
        require(
            set(os.listdir(directory))
            <= {"objects", "notices", "intake-receipt.private.json", "intake-failure.private.json"},
            "fixed-intake-roster",
        )
        for folder, allowed in (
            (None, ("intake-receipt.private.json", "intake-failure.private.json")),
            ("objects", NAMES),
            ("notices", ("simglucose-LICENSE.txt",)),
        ):
            child = (
                directory
                if folder is None
                else os.open(folder, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=directory)
            )
            try:
                _private_directory(child)
                names = set(os.listdir(child))
                if folder is not None:
                    require(names <= set(allowed), "fixed-intake-subroster")
                for name in allowed:
                    if name not in names:
                        continue
                    maximum = (
                        65536
                        if folder is None
                        else 1052
                        if folder == "notices"
                        else SIZES[NAMES.index(name)] + 1
                    )
                    result[(folder + "/" if folder else "") + name] = _read_file(
                        child, name, maximum
                    )
            finally:
                if child != directory:
                    os.close(child)
        require(sum(map(len, result.values())) <= 84752, "retained-root-cap")
        return result
    finally:
        os.close(directory)


@fixture_time.invented
def inspect_intake_fixture(
    files,
    expected_receipt_sha256,
    plan_raw,
    expected_plan_sha256,
    approval_raw,
    expected_approval_sha256,
    origin_raw,
    expected_origin_sha256,
):
    return _inspect_intake(
        files,
        expected_receipt_sha256,
        plan_raw,
        expected_plan_sha256,
        approval_raw,
        expected_approval_sha256,
        origin_raw,
        expected_origin_sha256,
        True,
    )


@fixture_time.actual
def inspect_approved_intake(
    files,
    expected_receipt_sha256,
    plan_raw,
    expected_plan_sha256,
    approval_raw,
    expected_approval_sha256,
    origin_raw,
    expected_origin_sha256,
):
    return _inspect_intake(
        files,
        expected_receipt_sha256,
        plan_raw,
        expected_plan_sha256,
        approval_raw,
        expected_approval_sha256,
        origin_raw,
        expected_origin_sha256,
        False,
    )


@fixture_time.selected(8)
def _inspect_intake(
    files,
    expected_receipt_sha256,
    plan_raw,
    expected_plan_sha256,
    approval_raw,
    expected_approval_sha256,
    origin_raw,
    expected_origin_sha256,
    fixture,
):
    """Historical execution pins, current retention; no PID/URL/path action."""
    require(
        type(files) is dict and all(type(k) is str and type(v) is bytes for k, v in files.items()),
        "intake-byte-buffers",
    )
    notice = files.get("notices/simglucose-LICENSE.txt", b"")
    receipt_names = set(files) & {"intake-receipt.private.json", "intake-failure.private.json"}
    require(len(receipt_names) == 1, "one-intake-receipt")
    name = next(iter(receipt_names))
    require(
        len(files[name]) <= 65536 and digest(files[name]) == expected_receipt_sha256,
        "external-receipt-pin",
    )
    receipt = decode(files[name])
    require(type(receipt) is dict, "receipt-object")
    started, ended = (
        _utc(receipt.get("controller_started_utc")),
        _utc(receipt.get("controller_ended_utc")),
    )
    plan, expiry = _gate(
        plan_raw,
        expected_plan_sha256,
        approval_raw,
        expected_approval_sha256,
        notice,
        origin_raw,
        expected_origin_sha256,
        fixture,
        _at=started,
    )
    require(started <= ended <= _now(), "receipt-execution-window")
    if receipt.get("status") == "completed":
        require(ended <= expiry, "receipt-execution-expiry")
    origin = decode(origin_raw)
    require(
        _now()
        < min(
            _utc(RETENTION["not_after_utc"]),
            *(_utc(row["deadline_utc"]) for row in origin["records"]),
        ),
        "current-retention-window",
    )
    fields(
        receipt,
        "schema kind source_identity process_owner_source_identity plan_sha256 "
        "approval_sha256 origin_context_sha256 notice retention targets "
        "inventory status error approval_consumed authority "
        "actual_HTTPS_qualified controller_pid controller_started_utc "
        "controller_ended_utc source_identity_after nonce_sha256 "
        "controller_elapsed_ns",
        "receipt-fields",
    )
    require(
        receipt["schema"] == SCHEMA
        and receipt["kind"] == ("invented" if fixture else "passive-intake")
        and receipt["source_identity"] == receipt["source_identity_after"] == _identity()
        and receipt["process_owner_source_identity"] == _owner()
        and receipt["plan_sha256"] == expected_plan_sha256
        and receipt["approval_sha256"] == expected_approval_sha256
        and receipt["origin_context_sha256"] == expected_origin_sha256
        and encode(receipt["notice"]) == encode(plan["notice"])
        and encode(receipt["retention"]) == encode(RETENTION)
        and receipt["approval_consumed"] is True
        and encode(receipt["authority"]) == encode(AUTHORITY)
        and receipt["actual_HTTPS_qualified"] is False
        and type(receipt["controller_pid"]) is int
        and receipt["controller_pid"] > 0
        and receipt["nonce_sha256"] == digest(decode(approval_raw)["nonce"].encode("ascii")),
        "receipt-source-authority-binding",
    )
    require(
        type(receipt["targets"]) is list and len(receipt["targets"]) == 3, "receipt-three-targets"
    )
    require(
        receipt["status"] in ("completed", "incomplete")
        and (receipt["error"] is None or type(receipt["error"]) is str)
        and type(receipt["controller_elapsed_ns"]) is int
        and receipt["controller_elapsed_ns"] >= 0,
        "receipt-status-clock",
    )
    if receipt["status"] == "completed":
        require(
            receipt["error"] is None
            and receipt["controller_elapsed_ns"] <= 90_000_000_000
            and (ended - started).total_seconds() <= 90,
            "completed-deadline-error",
        )
    inventory = {"notices/simglucose-LICENSE.txt": {"bytes": len(notice), "sha256": digest(notice)}}
    stopped = False
    for index, (fixed, row) in enumerate(zip(_targets(fixture), receipt["targets"], strict=True)):
        fields(
            row,
            "name url revision bytes sentinel_cap git_blob_sha1 status actual_bytes"
            " body_path accepted_sha256 computed_git_blob_sha1 headers process "
            "error",
            "target-receipt-fields",
        )
        require(
            all(row[k] == v and type(row[k]) is type(v) for k, v in fixed.items()),
            "fixed-receipt-target",
        )
        require(
            row["status"] in ("not-run", "accepted", "rejected", "incomplete")
            and type(row["actual_bytes"]) is int
            and 0 <= row["actual_bytes"] <= SIZES[index] + 1
            and (not stopped or row["status"] == "not-run"),
            "complete-failure-denominator",
        )
        body = files.get("objects/" + row["name"], b"")
        retained = "objects/" + row["name"] in files
        require(
            len(body) == row["actual_bytes"]
            and row["body_path"] == ("objects/" + row["name"] if retained else None),
            "retained-body-binding",
        )
        if retained:
            inventory[row["body_path"]] = {"bytes": len(body), "sha256": digest(body)}
        if row["status"] == "accepted":
            fields(
                row["headers"],
                "status content_length content_encoding header_bytes header_count",
                "retained-header-observation",
            )
            fields(
                row["process"],
                "pid returncode cleanup_error elapsed_ns started_utc ended_utc "
                "source_before source_after",
                "request-process-observation",
            )
            process, headers = row["process"], row["headers"]
            require(
                headers["status"] == 200
                and type(headers["status"]) is int
                and (
                    headers["content_length"] is None
                    or type(headers["content_length"]) is int
                    and headers["content_length"] == fixed["bytes"]
                )
                and headers["content_encoding"] in ("absent", "identity")
                and type(headers["header_bytes"]) is int
                and 0 < headers["header_bytes"] <= 4096
                and type(headers["header_count"]) is int
                and 0 <= headers["header_count"] <= 32,
                "accepted-HTTP-observation",
            )
            require(
                type(process["pid"]) is int
                and process["pid"] > 0
                and type(process["elapsed_ns"]) is int
                and 0 <= process["elapsed_ns"] <= 30_000_000_000
                and started
                <= _utc(process["started_utc"])
                <= _utc(process["ended_utc"])
                <= min(ended, expiry)
                and process["source_before"] == process["source_after"] == plan["source_identity"]
                and type(process["returncode"]) is int,
                "accepted-request-clock-source",
            )
            require(
                len(body) == fixed["bytes"]
                and _blob(body) == fixed["git_blob_sha1"]
                and (not fixture or body == BODIES[index])
                and row["accepted_sha256"] == digest(body)
                and row["computed_git_blob_sha1"] == _blob(body)
                and row["error"] is None
                and type(row["headers"]) is dict
                and row["headers"].get("status") == 200
                and type(row["process"]) is dict
                and row["process"].get("returncode") == 0
                and row["process"].get("cleanup_error") is None,
                "accepted-opaque-body",
            )
        else:
            stopped = True
            require(row["accepted_sha256"] is None, "no-partial-acceptance")
            if row["status"] == "not-run":
                require(
                    not retained
                    and row["actual_bytes"] == 0
                    and all(
                        row[key] is None
                        for key in ("computed_git_blob_sha1", "headers", "process", "error")
                    ),
                    "not-run-has-no-evidence",
                )
            else:
                require(type(row["error"]) is str and row["error"], "failed-target-reason")
                require(
                    row["computed_git_blob_sha1"] is None
                    or len(body) == fixed["bytes"]
                    and row["computed_git_blob_sha1"] == _blob(body),
                    "failed-blob-observation",
                )
    require(
        encode(receipt["inventory"]) == encode(inventory)
        and set(files) == set(inventory) | {name}
        and sum(map(len, files.values())) <= 84752,
        "receipt-inventory-closure",
    )
    completed = all(row["status"] == "accepted" for row in receipt["targets"])
    require(
        (receipt["status"] == "completed") == completed
        and (name == "intake-receipt.private.json") == completed,
        "no-forged-completion",
    )
    return {
        "kind": receipt["kind"],
        "status": receipt["status"],
        "accepted_targets": sum(row["status"] == "accepted" for row in receipt["targets"]),
        "actual_HTTPS_qualified": False,
        "authority": dict(AUTHORITY),
    }
