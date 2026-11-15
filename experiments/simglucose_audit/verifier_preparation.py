"""One-shot future source discovery; ordinary entry closed, invented tests only now.

Observed hashes identify captured bytes, not authentic tag/tree/verifier/trust.
Exactly three fixed text candidates, one readback per completed file; no code
or verifier activation. Rejected prefixes get metadata-only recovery.
"""

import base64
import codecs
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
from datetime import timedelta
from pathlib import Path
from urllib.parse import urlsplit

from experiments import platform_process

from . import fixture_time
from . import intake_collector as core
from .contract import AUTHORITY, SOURCE_FILES, decode, digest, encode, fields, require

ROOT = Path(__file__).resolve().parents[2]
SCHEMA = "opent1d.verifier-source-discovery/1"
DEADLINE = "2026-11-28T18:32:01Z"
HOST = "raw.githubusercontent.com"
NAMES = ("go.mod", "go.sum", "LICENSE")
CAPS = (65536, 524288, 65536)
URLS = tuple("https://" + HOST + "/cli/cli/v2.92.0/" + name for name in NAMES)
CHUNK_BYTES = 65536
FRAME_LIMIT = 512
LIMITS = {
    "requests": 3,
    "redirects": 0,
    "network_body_bytes": 655363,
    "stored_body_bytes": 655360,
    "local_readback_bytes": 655363,
    "combined_body_bytes": 1310726,
    "header_bytes": 8192,
    "header_count": 64,
    "status_line_bytes": 256,
    "request_seconds": 30,
    "whole_seconds": 120,
    "start_headroom_seconds": 140,
    "receipt_bytes": 65536,
    "review_bytes": 65536,
    "root_files": 5,
    "root_bytes": 786432,
    "consumption_marker_bytes": 128,
    "stored_text_readback_passes_per_completed_file": 1,
}
RETENTION = dict(core.RETENTION, known_earlier_utc=DEADLINE)
COVERAGE = (
    "source-location-proposal",
    "collector-source",
    "limited-source-review-basis",
    "proof-allocation",
)
CASES = (
    "ok",
    "extra",
    "empty",
    "utf8",
    "nul",
    "stall-connect",
    "stall-header",
    "stall-body",
    "stall-storage",
    "stall-fsync",
    "stall-readback",
    "stall-finalize",
    "late-source",
)
FIXTURES = (
    b"module invented.example/cli\ngo 1.99\n",
    b"invented.example/dep v0.0.0 h1:INVENTED_ONLY\n" * 4,
    "INVENTED source notice only; caf\u00e9\n".encode(),
)
FIXTURE_CAPS = tuple(len(raw) + 5 for raw in FIXTURES)
INERT_GH_PROBES = {
    "selected_tool_SHA256": None,
    "qualification_SHA256": None,
    "network_isolation_receipt_SHA256": None,
    "execution_authorized": False,
    "argv_templates": [
        ["<held-qualified-gh>", "--version"],
        ["<held-qualified-gh>", "attestation", "verify", "--help"],
    ],
}


def run_preparation(*_args, **_kwargs):
    raise PermissionError("source discovery closed without exact external approval")


def _targets(fixture=False):
    return [
        {
            "name": name,
            "url": url,
            "cap": (FIXTURE_CAPS[i] if fixture else CAPS[i]),
            "expected_sha256": None,
            "existence_content_verified": False,
            "raw_member_authenticated_by_source_archive_SHA": False,
        }
        for i, (name, url) in enumerate(zip(NAMES, URLS, strict=True))
    ]


def _source_hash(path, expiry=None):
    if expiry is not None:
        require(core._now() < expiry, "source-read-before-expiry")
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    try:
        before = os.fstat(fd)
        require(
            stat.S_ISREG(before.st_mode) and before.st_size <= 1048576, "bounded-regular-source"
        )
        raw = bytearray()
        while len(raw) <= before.st_size:
            if expiry is not None:
                require(core._now() < expiry, "source-chunk-before-expiry")
            part = os.read(fd, min(65536, before.st_size + 1 - len(raw)))
            if not part:
                break
            raw += part
        require(
            len(raw) == before.st_size
            and core._fingerprint(before) == core._fingerprint(os.fstat(fd)),
            "stable-source-snapshot",
        )
        return digest(bytes(raw))
    finally:
        os.close(fd)


def _identity(expiry=None):
    parent = sys.modules["experiments"]
    initializer = ROOT / "experiments/__init__.py"
    require(
        not initializer.exists()
        and not initializer.is_symlink()
        and parent.__file__ is None
        and set(parent.__path__) == {str(ROOT / "experiments")},
        "fixed-source-namespace",
    )
    directory = Path(__file__).parent
    return {name: _source_hash(directory / name, expiry) for name in SOURCE_FILES} | {
        "experiments/__init__.py": "namespace-initializer-absent",
        "verifier_preparation.py": _source_hash(Path(__file__), expiry),
    }


def _owner(expiry=None):
    return {name: _source_hash(ROOT / name, expiry) for name in platform_process.SOURCE_FILES}


def _parent_identity(fd):
    info = os.fstat(fd)
    return {
        "dev": info.st_dev,
        "ino": info.st_ino,
        "uid": info.st_uid,
        "mode": stat.S_IMODE(info.st_mode),
    }


def _live(expiry, deadline):
    require(core._now() < expiry and time.monotonic() < deadline, "current-deadline")


def _headers(raw):
    require(
        type(raw) is bytes and len(raw) <= 8192 and raw.endswith(b"\r\n\r\n"), "header-boundary"
    )
    lines = raw[:-4].split(b"\r\n")
    require(
        len(lines[0]) <= 256
        and re.fullmatch(rb"HTTP/1\.[01] [0-9]{3}(?: [\x20-\x7e]*)?", lines[0])
        and len(lines) - 1 <= 64,
        "status-header-count",
    )
    result = {}
    for line in lines[1:]:
        require(b":" in line, "header-colon")
        name, value = line.split(b":", 1)
        require(
            core.TOKEN.fullmatch(name) and all(32 <= c < 127 or c == 9 for c in value),
            "header-grammar",
        )
        name = name.lower().decode("ascii")
        require(name not in result, "duplicate-header")
        result[name] = value.strip().decode("ascii")
    require(
        "transfer-encoding" not in result
        and "content-range" not in result
        and result.get("content-encoding", "identity") == "identity",
        "opaque-identity-framing",
    )
    return int(lines[0].split(b" ")[1]), result


def _connect(url):
    parsed = urlsplit(url)
    context = ssl.create_default_context()
    context.keylog_filename = None
    require(context.check_hostname and context.verify_mode == ssl.CERT_REQUIRED, "tls-defaults")
    sock = socket.create_connection((parsed.hostname, 443), timeout=30)
    try:
        return context.wrap_socket(sock, server_hostname=parsed.hostname)
    except BaseException:
        sock.close()
        raise


def _emit(value):
    sys.stdout.buffer.write(encode(value) + b"\n")
    sys.stdout.buffer.flush()


def _frames(stream, events, maximum=90000):
    try:
        for _ in range(FRAME_LIMIT):
            raw = stream.readline(maximum + 1)
            require(len(raw) <= maximum, "ipc-frame-cap")
            if not raw:
                events.put(("eof", None), timeout=0.1)
                return
            require(raw.endswith(b"\n"), "ipc-line")
            events.put(("frame", decode(raw)), timeout=0.1)
        events.put(("error", None), timeout=0.1)
    except (OSError, ValueError, queue.Full):
        try:
            events.put_nowait(("error", None))
        except queue.Full:
            pass


def _send(stream, raw, result):
    try:
        stream.write(raw)
        stream.close()
        result.append(True)
    except OSError:
        result.append(False)


def _stop(process, reader, writer, owned, deadline):
    errors = []
    forced = process.poll() is None
    try:
        if forced:
            if owned:
                platform_process.force_tree(process)
            else:
                process.kill()
        process.wait(timeout=max(0.001, min(0.5, deadline - time.monotonic())))
    except (OSError, subprocess.TimeoutExpired):
        errors.append("owned-stop")
    for worker in (reader, writer):
        if worker is not None and worker.ident is not None:
            try:
                worker.join(timeout=max(0, min(0.5, deadline - time.monotonic())))
                if worker.is_alive():
                    errors.append("io-not-joined")
            except RuntimeError:
                errors.append("io-join-failed")
    if reader is None or not reader.is_alive():
        try:
            process.stdout.close()
        except OSError:
            errors.append("pipe-close")
    if owned:
        try:
            if platform_process.tree_exists(process):
                forced = True
                platform_process.force_tree(process)
                process.wait(timeout=max(0.001, min(0.5, deadline - time.monotonic())))
            require(not platform_process.tree_exists(process), "owned-tree-stop")
            platform_process.close_tree(process)
        except (OSError, RuntimeError, ValueError, subprocess.TimeoutExpired):
            errors.append("owned-tree-unconfirmed")
    if writer is None or not writer.is_alive():
        try:
            if getattr(process, "stdin", None) is not None:
                process.stdin.close()
        except OSError:
            errors.append("input-pipe-close")
    require(not errors, "owned-cleanup-failed")
    return forced


def _io_threads(process, raw, events, writers):
    return (
        threading.Thread(target=_frames, args=(process.stdout, events), daemon=True),
        threading.Thread(target=_send, args=(process.stdin, raw, writers), daemon=True),
    )


def _namespace(directory, plan):
    parent = core._directory(str(Path(plan["output_root"]).parent))
    try:
        require(_parent_identity(parent) == plan["parent_identity"], "late-parent-binding")
        named = os.stat(Path(plan["output_root"]).name, dir_fd=parent, follow_symlinks=False)
        opened = os.fstat(directory)
        require(
            stat.S_ISDIR(named.st_mode)
            and named.st_dev == opened.st_dev
            and named.st_ino == opened.st_ino,
            "late-root-binding",
        )
        core._private_directory(directory)
    finally:
        os.close(parent)


def _supervise(wire, deadline):
    process = platform_process.spawn(
        [sys.executable, "-I", "-S", "-B", "-c", _script("_entry;_entry()")],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        cwd=ROOT,
        env=core._environment(),
    )
    events, writers = queue.Queue(maxsize=8), []
    reader = writer = None
    receipt, clean = None, False
    try:
        reader, writer = _io_threads(process, encode(wire), events, writers)
        reader.start()
        writer.start()
        while time.monotonic() < wire["deadline"]:
            try:
                kind, frame = events.get(timeout=max(0.001, wire["deadline"] - time.monotonic()))
            except queue.Empty:
                break
            if kind == "eof":
                process.wait(timeout=max(0.001, wire["deadline"] - time.monotonic()))
                clean = process.returncode == 0 and writers == [True]
                break
            if kind == "frame" and type(frame) is dict and set(frame) == {"receipt"}:
                require(receipt is None, "single-receipt")
                receipt = frame["receipt"]
            else:
                receipt = None
                break
    finally:
        forced = _stop(process, reader, writer, True, deadline)
    return None if forced or not clean else receipt


def _script(call):
    return (
        "import sys;sys.path.insert(0,"
        + repr(str(ROOT))
        + ");from experiments.simglucose_audit.verifier_preparation import "
        + call
    )


@fixture_time.selected(4)
def _gate(plan_raw, approval_raw, origin_raw, held, fixture=False, headroom=False):
    fields(
        held,
        "plan_sha256 approval_sha256 origin_sha256 source_sha256 owner_sha256 "
        "rights_basis_sha256 output_root",
        "external-held-pins",
    )
    for name in ("plan", "approval", "origin"):
        raw = {"plan": plan_raw, "approval": approval_raw, "origin": origin_raw}[name]
        require(
            type(raw) is bytes and len(raw) <= 32768 and digest(raw) == held[name + "_sha256"],
            "external-document-pin",
        )
    for name in ("source_sha256", "owner_sha256", "rights_basis_sha256"):
        require(type(held[name]) is str and core.HEX.fullmatch(held[name]), "external-pin")
    plan, approval, origin = map(decode, (plan_raw, approval_raw, origin_raw))
    fields(
        plan,
        "schema kind targets limits retention source owner rights_basis_sha256 "
        "qualification_sha256 output_root parent_identity origin_sha256",
        "plan-fields",
    )
    require(
        plan["schema"] == SCHEMA
        and plan["kind"] == ("invented" if fixture else "source-discovery-plan"),
        "plan-kind",
    )
    require(
        encode(plan["targets"]) == encode(_targets(fixture))
        and encode(plan["limits"]) == encode(LIMITS)
        and encode(plan["retention"]) == encode(RETENTION),
        "fixed-opaque-scope",
    )
    require(
        plan["rights_basis_sha256"] == held["rights_basis_sha256"]
        and type(plan["qualification_sha256"]) is str
        and core.HEX.fullmatch(plan["qualification_sha256"]),
        "held-rights-qualification",
    )
    output = plan["output_root"]
    require(
        type(output) is str
        and output == held["output_root"]
        and Path(output).is_absolute()
        and str(Path(output)) == output
        and ".." not in Path(output).parts
        and Path(output).name == ("invented-intake" if fixture else "proposed-source-discovery"),
        "physical-output-scope",
    )
    fields(plan["parent_identity"], "dev ino uid mode", "parent-identity-fields")
    require(
        all(type(value) is int for value in plan["parent_identity"].values()),
        "physical-parent-identity",
    )
    fields(
        origin,
        "schema kind records retention origins_verified unknown_required_origins "
        "origin_scope does_not_reset_referenced_material_origins "
        "unknown_referenced_origins_timely_claimed",
        "origin-fields",
    )
    require(
        origin["schema"] == SCHEMA
        and origin["kind"] == ("invented" if fixture else "private-origin-context")
        and origin["retention"] == RETENTION
        and origin["origins_verified"] is True
        and origin["origin_scope"] == "new-observation-or-proposal-fact"
        and origin["does_not_reset_referenced_material_origins"] is True
        and origin["unknown_referenced_origins_timely_claimed"] is False
        and origin["unknown_required_origins"] == []
        and plan["origin_sha256"] == held["origin_sha256"]
        and type(origin["records"]) is list
        and len(origin["records"]) == 4,
        "verified-required-origins",
    )
    now = core._now()
    deadlines = [core._utc(DEADLINE), core._utc(RETENTION["not_after_utc"])]
    for subject, row in zip(COVERAGE, origin["records"], strict=True):
        fields(row, "subject origin_utc deadline_utc evidence_sha256 basis", "origin-row")
        start, end = core._utc(row["origin_utc"]), core._utc(row["deadline_utc"])
        require(
            row["subject"] == subject
            and row["basis"] == "new-technical-fact-evidence"
            and type(row["evidence_sha256"]) is str
            and core.HEX.fullmatch(row["evidence_sha256"])
            and start <= now < end <= start + timedelta(days=30),
            "origin-timing-basis",
        )
        deadlines.append(end)
    fields(
        approval,
        "schema kind plan_sha256 origin_sha256 rights_basis_sha256 source_sha256 "
        "owner_sha256 nonce issued_utc expires_utc scope authority",
        "approval-fields",
    )
    require(
        approval["schema"] == SCHEMA
        and approval["kind"] == ("invented" if fixture else "private-one-shot-approval")
        and all(
            approval[name] == held[name]
            for name in (
                "plan_sha256",
                "origin_sha256",
                "rights_basis_sha256",
                "source_sha256",
                "owner_sha256",
            )
        )
        and type(approval["nonce"]) is str
        and re.fullmatch(r"[0-9a-f]{32}", approval["nonce"])
        and approval["scope"] == "one-three-text-discovery-plus-single-readback"
        and encode(approval["authority"]) == encode(AUTHORITY),
        "exact-private-approval",
    )
    issued, expires = core._utc(approval["issued_utc"]), core._utc(approval["expires_utc"])
    require(issued <= now < expires <= issued + timedelta(days=30), "approval-window")
    expiry = min(expires, *deadlines)
    require(
        (expiry - now).total_seconds() >= (140 if headroom else 0) and now < expiry,
        "earliest-expiry-headroom",
    )
    require(
        plan["source"] == _identity(expiry)
        and plan["owner"] == _owner(expiry)
        and digest(encode(plan["source"])) == held["source_sha256"]
        and digest(encode(plan["owner"])) == held["owner_sha256"],
        "current-source-owner",
    )
    require(core._now() < expiry, "source-finish-before-expiry")
    return plan, expiry


def _response(connection, index, cap):
    parsed = urlsplit(URLS[index])
    connection.sendall(
        (
            f"GET {parsed.path} HTTP/1.1\r\nHost: {HOST}\r\n"
            "Accept-Encoding: identity\r\nConnection: close\r\n\r\n"
        ).encode("ascii")
    )
    header = bytearray()
    while not header.endswith(b"\r\n\r\n"):
        require(len(header) < 8192, "header-cap")
        chunk = connection.recv(1)
        require(chunk, "header-eof")
        header += chunk
    status, headers = _headers(bytes(header))
    require(status == 200 and "location" not in headers, "no-redirect-final200")
    declared = None
    if "content-length" in headers:
        value = headers["content-length"]
        require(
            re.fullmatch(r"[0-9]{1,9}", value) and 0 < int(value) <= cap, "bounded-content-length"
        )
        declared = int(value)
    _emit({"phase": "headers", "declared": declared})
    consumed, pending = 0, bytearray()
    while consumed < cap + 1:
        maximum = min(CHUNK_BYTES - len(pending), cap + 1 - consumed)
        chunk = connection.recv(maximum)
        if not chunk:
            break
        require(len(chunk) <= maximum, "network-body-cap")
        consumed += len(chunk)
        pending += chunk
        if len(pending) == CHUNK_BYTES:
            _emit({"phase": "body", "data": base64.b64encode(pending).decode("ascii")})
            pending.clear()
    if pending:
        _emit({"phase": "body", "data": base64.b64encode(pending).decode("ascii")})
    _emit({"phase": "done", "bytes": consumed})


def _fetch_entry(fixture, case, index):
    try:
        require(type(index) is int and 0 <= index < 3, "fixed-target-index")
        if fixture:
            require(case in CASES, "invented-case")

            def deny(event, _args):
                if event in ("socket.connect", "socket.getaddrinfo"):
                    raise PermissionError("fixture-network-denied")

            sys.addaudithook(deny)
            if index == 0 and case in ("stall-connect", "stall-header"):
                time.sleep(30)
            body = FIXTURES[index]
            if index == 0:
                if case == "extra":
                    body = b"A" * (FIXTURE_CAPS[0] + 1)
                elif case == "empty":
                    body = b""
                elif case == "utf8":
                    body = b"\xff" + body
                elif case == "nul":
                    body = b"\0" + body
            _emit({"phase": "headers", "declared": None})
            if body:
                _emit({"phase": "body", "data": base64.b64encode(body).decode("ascii")})
            if index == 0 and case == "stall-body":
                time.sleep(30)
            _emit({"phase": "done", "bytes": len(body)})
            return
        require(case is None, "actual-no-fixture-selector")
        connection = _connect(URLS[index])
        try:
            _response(connection, index, CAPS[index])
        finally:
            connection.close()
    except (OSError, ValueError, TimeoutError):
        _emit({"phase": "error"})


def _request(wire, index, fd, hasher, deadline, expiry, observed=None):
    if observed is None:
        observed = {}
    observed["received"] = 0
    fixture, case = wire["fixture"], wire["case"]
    cap = _targets(fixture)[index]["cap"]
    stop = min(deadline, time.monotonic() + wire["request_seconds"])
    read_until = stop - min(1, wire["request_seconds"] / 3)
    process = subprocess.Popen(
        [
            sys.executable,
            "-I",
            "-S",
            "-B",
            "-c",
            _script(f"_fetch_entry;_fetch_entry({fixture!r},{case!r},{index!r})"),
        ],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        cwd=ROOT,
        env=core._environment(),
    )
    events, writers = queue.Queue(maxsize=8), []
    reader = writer = None
    headers, done, declared = False, False, None
    received, count = 0, 0
    decoder = codecs.getincrementaldecoder("utf-8")("strict")
    try:
        reader, writer = _io_threads(process, b"", events, writers)
        reader.start()
        writer.start()
        while True:
            _live(expiry, read_until)
            try:
                kind, frame = events.get(timeout=max(0.001, read_until - time.monotonic()))
            except queue.Empty:
                raise TimeoutError("request-watchdog") from None
            if kind == "eof":
                require(done, "complete-response")
                process.wait(timeout=max(0.001, read_until - time.monotonic()))
                require(process.returncode == 0 and writers == [True], "fetch-exit")
                return count, received
            require(kind == "frame" and type(frame) is dict, "fetch-protocol")
            phase = frame.get("phase")
            if phase == "headers":
                fields(frame, "phase declared", "header-frame")
                require(
                    not headers
                    and not done
                    and (
                        frame["declared"] is None
                        or type(frame["declared"]) is int
                        and 0 < frame["declared"] <= cap
                    ),
                    "header-order",
                )
                headers, declared = True, frame["declared"]
            elif phase == "body":
                fields(frame, "phase data", "body-frame")
                require(headers and not done and type(frame["data"]) is str, "body-order")
                raw = base64.b64decode(frame["data"], validate=True)
                require(
                    0 < len(raw) <= CHUNK_BYTES and received + len(raw) <= cap + 1,
                    "sentinel-network-cap",
                )
                received += len(raw)
                observed["received"] = received
                writable = raw[: max(0, cap - count)]
                require(b"\0" not in writable, "NUL-text-refused")
                decoder.decode(writable, final=False)
                if fixture and case == "stall-storage":
                    time.sleep(30)
                offset = 0
                while offset < len(writable):
                    _live(expiry, deadline)
                    written = os.write(fd, writable[offset:])
                    require(0 < written <= len(writable) - offset, "body-write-progress")
                    hasher.update(writable[offset : offset + written])
                    count += written
                    offset += written
                require(len(writable) == len(raw), "overflow-sentinel-not-stored")
            elif phase == "done":
                fields(frame, "phase bytes", "done-frame")
                require(
                    headers
                    and not done
                    and type(frame["bytes"]) is int
                    and frame["bytes"] == received == count
                    and 0 < count <= cap
                    and (declared is None or declared == count),
                    "body-count-framing",
                )
                decoder.decode(b"", final=True)
                done = True
            else:
                raise ValueError("transport-rejected")
    finally:
        _stop(process, reader, writer, False, stop)


def _inputs(wire, headroom=False):
    return _gate(
        *(base64.b64decode(wire[name], validate=True) for name in ("plan", "approval", "origin")),
        wire["held"],
        wire["fixture"],
        headroom,
    )


def _readback(
    fd, directory, name, cap, expected_bytes, expected_sha, expiry, deadline, observed=None
):
    if observed is None:
        observed = {}
    observed["bytes"] = 0
    _live(expiry, deadline)
    before = os.fstat(fd)
    core._regular(fd)
    require(
        core._fingerprint(before)
        == core._fingerprint(os.stat(name, dir_fd=directory, follow_symlinks=False)),
        "readback-name-binding",
    )
    require(os.lseek(fd, 0, os.SEEK_SET) == 0, "readback-same-descriptor")
    count, lines = 0, 0
    mod_chunks = []
    hasher = hashlib.sha256()
    decoder = codecs.getincrementaldecoder("utf-8")("strict")
    while count < cap + 1:
        _live(expiry, deadline)
        raw = os.read(fd, min(CHUNK_BYTES, cap + 1 - count))
        if not raw:
            break
        count += len(raw)
        observed["bytes"] = count
        require(count <= cap and b"\0" not in raw, "readback-cap-or-NUL")
        hasher.update(raw)
        text = decoder.decode(raw, final=False)
        lines += text.count("\n")
        if name == "go.mod":
            mod_chunks.append(text)
    decoder.decode(b"", final=True)
    _live(expiry, deadline)
    after = os.fstat(fd)
    named = os.stat(name, dir_fd=directory, follow_symlinks=False)
    require(
        core._fingerprint(before) == core._fingerprint(after) == core._fingerprint(named)
        and count == expected_bytes
        and hasher.hexdigest() == expected_sha,
        "single-readback-integrity",
    )
    return {
        "readback_passes": 1,
        "readback_bytes": count,
        "readback_sha256": hasher.hexdigest(),
        "UTF8_nonNUL": True,
        "LF_count": lines,
        "semantic_or_license_authentication": False,
        "static_summary": _summarize_mod("".join(mod_chunks))
        if name == "go.mod"
        else {"kind": "size-hash-UTF8-linecount-only", "semantic_evaluation": False},
    }


def _row(
    name, status, count, sha, received=None, readback=None, attempts=None, readback_bytes=None
):
    return {
        "name": name,
        "path": "objects/" + name,
        "status": status,
        "stored_bytes": count,
        "stream_write_sha256": sha,
        "controller_received_bytes": received,
        "readback": readback,
        "readback_attempts": attempts,
        "readback_observed_bytes": readback_bytes,
        "accepted_observed_sha256": sha if status == "observed" else None,
        "source_authenticated": False,
        "tag_tree_correspondence_authenticated": False,
    }


def _receipt(wire, status, rows, error, review_sha=None):
    return {
        "schema": SCHEMA,
        "kind": "invented" if wire["fixture"] else "source-discovery-receipt",
        "status": status,
        "rows": rows,
        "pins": wire["held"],
        "limits": dict(LIMITS),
        "retention": dict(RETENTION),
        "metadata_review_sha256": review_sha,
        "discovery_only": True,
        "source_authenticated": False,
        "installed_binary_verified": False,
        "trust_roots_admitted": False,
        "GH_execution_authorized": False,
        "approval_consumed": True,
        "ended_utc": core._stamp(core._now()),
        "authority": dict(AUTHORITY),
        "error": error,
    }


def _controller(wire):
    with fixture_time.use(wire["fixture"]):
        plan, expiry = _inputs(wire, True)
        deadline = wire["deadline"]
        parent = core._directory(str(Path(plan["output_root"]).parent))
        try:
            require(_parent_identity(parent) == plan["parent_identity"], "physical-parent-current")
            _live(expiry, deadline)
            core._write_file(
                parent,
                ".discovery-consumed-" + wire["held"]["approval_sha256"],
                encode({"approval_sha256": wire["held"]["approval_sha256"]}),
            )
            name = Path(plan["output_root"]).name
            _live(expiry, deadline)
            os.mkdir(name, 0o700, dir_fd=parent)
            os.fsync(parent)
            directory = os.open(name, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=parent)
            core._private_directory(directory)
            _namespace(directory, plan)
        finally:
            os.close(parent)
        rows = []
        error = None
        objects = None
        try:
            _live(expiry, deadline)
            os.mkdir("objects", 0o700, dir_fd=directory)
            os.fsync(directory)
            objects = os.open(
                "objects", os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=directory
            )
            core._private_directory(objects)
            _objects_binding(directory, objects)
            for index, target in enumerate(plan["targets"]):
                _live(expiry, deadline)
                _namespace(directory, plan)
                _inputs(wire)
                fd = os.open(
                    target["name"],
                    os.O_RDWR | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
                    0o600,
                    dir_fd=objects,
                )
                hasher = hashlib.sha256()
                received = None
                accepted = False
                readback = None
                observed = {}
                attempts = 0
                read_observed = {}
                try:
                    core._regular(fd)
                    try:
                        count, received = _request(
                            wire, index, fd, hasher, deadline, expiry, observed
                        )
                        _live(expiry, deadline)
                        if wire["fixture"] and wire["case"] == "stall-fsync":
                            time.sleep(30)
                        os.fsync(fd)
                        if wire["fixture"] and wire["case"] == "stall-readback":
                            time.sleep(30)
                        _namespace(directory, plan)
                        _objects_binding(directory, objects)
                        attempts = 1
                        readback = _readback(
                            fd,
                            objects,
                            target["name"],
                            target["cap"],
                            count,
                            hasher.hexdigest(),
                            expiry,
                            deadline,
                            read_observed,
                        )
                        _namespace(directory, plan)
                        _objects_binding(directory, objects)
                        accepted = True
                    except (
                        OSError,
                        ValueError,
                        RuntimeError,
                        TimeoutError,
                        subprocess.TimeoutExpired,
                    ):
                        error = "capture-or-readback-rejected"
                        readback = None
                    received = observed.get("received")
                    count = os.fstat(fd).st_size
                    require(count <= target["cap"], "stored-prefix-cap")
                    rows.append(
                        _row(
                            target["name"],
                            "observed" if accepted else "rejected",
                            count,
                            hasher.hexdigest(),
                            received,
                            readback,
                            attempts,
                            read_observed.get("bytes", 0),
                        )
                    )
                finally:
                    os.close(fd)
                _objects_binding(directory, objects)
                if not accepted:
                    break
            _live(expiry, deadline)
            _namespace(directory, plan)
            _inputs(wire)
            if wire["fixture"] and wire["case"] == "late-source":
                raise ValueError("invented-source-drift")
            review = {
                "schema": SCHEMA,
                "kind": "static-text-quality-metadata-only",
                "rows": rows,
                "raw_source_text_returned": False,
                "evaluated_or_resolved": False,
                "full_license_or_tag_tree_authenticated": False,
            }
            review_raw = encode(review)
            require(len(review_raw) <= 65536, "review-cap")
            core._write_file(directory, "metadata-review.private.json", review_raw)
            receipt = _receipt(
                wire,
                "completed" if len(rows) == 3 and error is None else "rejected",
                rows,
                error,
                digest(review_raw),
            )
            if wire["fixture"] and wire["case"] == "stall-finalize":
                time.sleep(30)
            _live(expiry, deadline)
            _namespace(directory, plan)
            _inputs(wire)
            raw = encode(receipt)
            require(len(raw) <= 65536, "receipt-cap")
            core._write_file(directory, "intake-receipt.private.json", raw)
            _live(expiry, deadline)
            _inputs(wire)
            _emit({"receipt": receipt})
        finally:
            if objects is not None:
                os.close(objects)
            os.close(directory)


def _recover(wire):
    with fixture_time.use(wire["fixture"]):
        plan, expiry = _inputs(wire)
        deadline = wire["deadline"]
        _live(expiry, deadline)
        directory = core._directory(plan["output_root"])
        objects = None
        rows = []
        try:
            _namespace(directory, plan)
            try:
                os.stat("intake-receipt.private.json", dir_fd=directory, follow_symlinks=False)
            except FileNotFoundError:
                pass
            else:
                raise ValueError("receipt-already-consumed")
            try:
                objects = os.open(
                    "objects", os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=directory
                )
            except FileNotFoundError:
                pass
            if objects is not None:
                core._private_directory(objects)
                _objects_binding(directory, objects)
                for target in plan["targets"]:
                    _live(expiry, deadline)
                    try:
                        s = os.stat(target["name"], dir_fd=objects, follow_symlinks=False)
                    except FileNotFoundError:
                        continue
                    require(
                        stat.S_ISREG(s.st_mode)
                        and s.st_uid == os.getuid()
                        and stat.S_IMODE(s.st_mode) == 0o600
                        and s.st_nlink == 1
                        and s.st_size <= target["cap"],
                        "recovery-prefix-metadata",
                    )
                    rows.append(
                        _row(target["name"], "incomplete", s.st_size, None)
                    )  # STAT ONLY, never body.
            if objects is not None:
                _objects_binding(directory, objects)
            receipt = _receipt(wire, "incomplete", rows, "owned-controller-failure")
            _live(expiry, deadline)
            _namespace(directory, plan)
            core._write_file(directory, "intake-receipt.private.json", encode(receipt))
            _live(expiry, deadline)
            _inputs(wire)
            _emit({"receipt": receipt})
        finally:
            if objects is not None:
                os.close(objects)
            os.close(directory)


def _entry():
    try:
        raw = sys.stdin.buffer.read(131073)
        require(len(raw) <= 131072, "controller-input-cap")
        wire = decode(raw)
        fields(
            wire,
            "plan approval origin held fixture case deadline request_seconds recovery",
            "wire-fields",
        )
        require(
            type(wire["fixture"]) is bool
            and type(wire["recovery"]) is bool
            and (wire["case"] in CASES if wire["fixture"] else wire["case"] is None)
            and 0 < wire["request_seconds"] <= 30,
            "fixed-wire-mode",
        )
        (_recover if wire["recovery"] else _controller)(wire)
    except (OSError, ValueError, RuntimeError, TimeoutError):
        _emit({"error": "controller-rejected"})


@fixture_time.selected(4)
def _execute(
    plan_raw,
    approval_raw,
    origin_raw,
    held,
    fixture=False,
    case=None,
    whole_seconds=120,
    request_seconds=30,
):
    start = time.monotonic()
    deadline = start + whole_seconds
    _gate(plan_raw, approval_raw, origin_raw, held, fixture, True)
    require(time.monotonic() < deadline, "preflight-whole-watchdog")
    require(not Path(held["output_root"]).exists(), "one-attempt-no-resume")
    acquisition = deadline - min(4, whole_seconds / 3)
    wire = {
        name: base64.b64encode(raw).decode("ascii")
        for name, raw in (("plan", plan_raw), ("approval", approval_raw), ("origin", origin_raw))
    }
    wire.update(
        held=held,
        fixture=fixture,
        case=case,
        deadline=acquisition,
        request_seconds=request_seconds,
        recovery=False,
    )
    receipt = _supervise(wire, deadline - min(1.5, whole_seconds / 6))
    require(time.monotonic() < deadline, "post-stop-whole-watchdog")
    _gate(plan_raw, approval_raw, origin_raw, held, fixture)
    if receipt is None and deadline - time.monotonic() > 0.3:
        wire["recovery"] = True
        wire["deadline"] = min(time.monotonic() + 1, deadline - 0.2)
        receipt = _supervise(wire, deadline)
    require(time.monotonic() < deadline, "whole-finalization-watchdog")
    _, expiry = _gate(plan_raw, approval_raw, origin_raw, held, fixture)
    if receipt is None:
        return {
            "schema": SCHEMA,
            "kind": "invented" if fixture else "source-discovery-failure",
            "status": "incomplete",
            "error": "owned-controller-failure",
            "accepted_source": False,
            "output_root": held["output_root"],
            "authority": dict(AUTHORITY),
        }
    _validate_receipt(receipt, held, fixture, core._utc(decode(approval_raw)["issued_utc"]), expiry)
    return receipt


@fixture_time.actual
def collect_approved(plan_raw, approval_raw, origin_raw, held):
    """Privileged trusted caller must independently hold exact real approval pins."""
    return _execute(plan_raw, approval_raw, origin_raw, held)


@fixture_time.invented
def fixture_inputs(output):
    parent = core._directory(str(Path(output).parent))
    try:
        identity = _parent_identity(parent)
    finally:
        os.close(parent)
    now = core._now().replace(microsecond=0)
    origin = {
        "schema": SCHEMA,
        "kind": "invented",
        "retention": RETENTION,
        "origins_verified": True,
        "origin_scope": "new-observation-or-proposal-fact",
        "does_not_reset_referenced_material_origins": True,
        "unknown_referenced_origins_timely_claimed": False,
        "unknown_required_origins": [],
        "records": [
            {
                "subject": subject,
                "origin_utc": core._stamp(now),
                "deadline_utc": DEADLINE,
                "evidence_sha256": digest(subject.encode()),
                "basis": "new-technical-fact-evidence",
            }
            for subject in COVERAGE
        ],
    }
    origin_raw = encode(origin)
    plan = {
        "schema": SCHEMA,
        "kind": "invented",
        "targets": _targets(True),
        "limits": LIMITS,
        "retention": RETENTION,
        "source": _identity(),
        "owner": _owner(),
        "rights_basis_sha256": digest(b"INVENTED limited source review"),
        "qualification_sha256": digest(b"INVENTED qualification"),
        "output_root": str(output),
        "parent_identity": identity,
        "origin_sha256": digest(origin_raw),
    }
    plan_raw = encode(plan)
    held = {
        "plan_sha256": digest(plan_raw),
        "origin_sha256": digest(origin_raw),
        "source_sha256": digest(encode(plan["source"])),
        "owner_sha256": digest(encode(plan["owner"])),
        "rights_basis_sha256": plan["rights_basis_sha256"],
        "output_root": str(output),
    }
    approval = {
        "schema": SCHEMA,
        "kind": "invented",
        **{
            key: held[key]
            for key in (
                "plan_sha256",
                "origin_sha256",
                "source_sha256",
                "owner_sha256",
                "rights_basis_sha256",
            )
        },
        "nonce": "01" * 16,
        "issued_utc": core._stamp(now),
        "expires_utc": DEADLINE,
        "scope": "one-three-text-discovery-plus-single-readback",
        "authority": dict(AUTHORITY),
    }
    approval_raw = encode(approval)
    held["approval_sha256"] = digest(approval_raw)
    return plan_raw, approval_raw, origin_raw, held


@fixture_time.invented
def run_fixture(output, case="ok", whole_seconds=3, request_seconds=1):
    require(
        case in CASES and 0.1 < whole_seconds <= 5 and 0.1 < request_seconds <= 2,
        "invented-budgets",
    )
    return _execute(
        *fixture_inputs(output),
        fixture=True,
        case=case,
        whole_seconds=whole_seconds,
        request_seconds=request_seconds,
    )


@fixture_time.selected(2)
def _validate_receipt(receipt, held, fixture, issued=None, expiry=None):
    fields(
        receipt,
        "schema kind status rows pins limits retention metadata_review_sha256 discovery_only "
        "source_authenticated installed_binary_verified trust_roots_admitted "
        "GH_execution_authorized "
        "approval_consumed ended_utc authority error",
        "receipt-fields",
    )
    require(
        receipt["schema"] == SCHEMA
        and receipt["kind"] == ("invented" if fixture else "source-discovery-receipt")
        and receipt["pins"] == held
        and encode(receipt["limits"]) == encode(LIMITS)
        and encode(receipt["retention"]) == encode(RETENTION)
        and encode(receipt["authority"]) == encode(AUTHORITY)
        and receipt["discovery_only"] is True
        and receipt["approval_consumed"] is True
        and all(
            receipt[k] is False
            for k in (
                "source_authenticated",
                "installed_binary_verified",
                "trust_roots_admitted",
                "GH_execution_authorized",
            )
        ),
        "receipt-untrusted-scope",
    )
    require(
        receipt["status"] in ("completed", "rejected", "incomplete")
        and type(receipt["rows"]) is list
        and len(receipt["rows"]) <= 3,
        "receipt-status-rows",
    )
    require(all(type(r) is dict for r in receipt["rows"]), "row-object-types")
    require(
        [r.get("name") for r in receipt["rows"]] == list(NAMES[: len(receipt["rows"])]),
        "exact-prefix-order",
    )
    targets = _targets(fixture)
    seen = set()
    for row in receipt["rows"]:
        fields(
            row,
            "name path status stored_bytes stream_write_sha256 controller_received_bytes readback "
            "accepted_observed_sha256 source_authenticated tag_tree_correspondence_authenticated "
            "readback_attempts readback_observed_bytes",
            "row-fields",
        )
        require(row["name"] in NAMES and row["name"] not in seen, "unique-fixed-row")
        seen.add(row["name"])
        target = targets[NAMES.index(row["name"])]
        count = row["stored_bytes"]
        require(
            row["path"] == "objects/" + row["name"]
            and type(count) is int
            and 0 <= count <= target["cap"]
            and row["source_authenticated"] is False
            and row["tag_tree_correspondence_authenticated"] is False,
            "row-fixed-scope",
        )
        require(
            row["controller_received_bytes"] is None
            or type(row["controller_received_bytes"]) is int
            and 0 <= row["controller_received_bytes"] <= target["cap"] + 1,
            "controller-received-bound",
        )
        require(
            row["readback_attempts"] is None
            or type(row["readback_attempts"]) is int
            and row["readback_attempts"] in (0, 1),
            "readback-attempt-bound",
        )
        require(
            row["readback_observed_bytes"] is None
            or type(row["readback_observed_bytes"]) is int
            and 0 <= row["readback_observed_bytes"] <= target["cap"] + 1,
            "readback-byte-bound",
        )
        if row["status"] == "observed":
            require(
                count > 0
                and row["readback_attempts"] == 1
                and row["readback_observed_bytes"] == count
                and type(row["stream_write_sha256"]) is str
                and core.HEX.fullmatch(row["stream_write_sha256"])
                and row["accepted_observed_sha256"] == row["stream_write_sha256"]
                and row["controller_received_bytes"] == count,
                "observed-identity",
            )
            r = row["readback"]
            fields(
                r,
                "readback_passes readback_bytes readback_sha256 UTF8_nonNUL LF_count "
                "semantic_or_license_authentication static_summary",
                "readback-fields",
            )
            require(
                type(r["readback_passes"]) is int
                and r["readback_passes"] == 1
                and type(r["readback_bytes"]) is int
                and r["readback_bytes"] == count
                and r["readback_sha256"] == row["stream_write_sha256"]
                and r["UTF8_nonNUL"] is True
                and type(r["LF_count"]) is int
                and 0 <= r["LF_count"] <= count
                and r["semantic_or_license_authentication"] is False,
                "one-readback-observation",
            )
            _validate_static(r["static_summary"], row["name"])
        else:
            require(
                row["status"] in ("rejected", "incomplete")
                and row["accepted_observed_sha256"] is None
                and row["readback"] is None
                and (
                    row["stream_write_sha256"] is None
                    or type(row["stream_write_sha256"]) is str
                    and core.HEX.fullmatch(row["stream_write_sha256"])
                ),
                "failed-no-source-clearance",
            )
    if receipt["status"] == "rejected":
        require(
            bool(receipt["rows"])
            and receipt["rows"][-1]["status"] == "rejected"
            and all(r["status"] == "observed" for r in receipt["rows"][:-1])
            and receipt["error"] == "capture-or-readback-rejected",
            "stopped-at-first-rejection",
        )
    if receipt["status"] == "incomplete":
        require(
            receipt["error"] == "owned-controller-failure"
            and receipt["metadata_review_sha256"] is None
            and all(
                r["status"] == "incomplete"
                and r["stream_write_sha256"] is None
                and r["controller_received_bytes"] is None
                and r["readback"] is None
                and r["readback_attempts"] is None
                and r["readback_observed_bytes"] is None
                for r in receipt["rows"]
            ),
            "stat-only-incomplete",
        )
    for row in receipt["rows"]:
        if row["status"] == "rejected":
            require(
                type(row["stream_write_sha256"]) is str
                and type(row["readback_attempts"]) is int
                and row["readback_attempts"] in (0, 1)
                and (
                    row["readback_observed_bytes"] == 0
                    if row["readback_attempts"] == 0
                    else row["stored_bytes"] > 0
                    and row["controller_received_bytes"] == row["stored_bytes"]
                ),
                "rejected-capture-or-readback-stage",
            )
    ended = core._utc(receipt["ended_utc"])
    require(
        ended <= core._now()
        and ended < core._utc(DEADLINE)
        and (issued is None or issued <= ended)
        and (expiry is None or ended < expiry)
        and receipt["error"] in (None, "capture-or-readback-rejected", "owned-controller-failure"),
        "receipt-time-error",
    )
    if receipt["status"] == "completed":
        require(
            [r["name"] for r in receipt["rows"]] == list(NAMES)
            and all(r["status"] == "observed" for r in receipt["rows"])
            and receipt["error"] is None,
            "complete-three-discoveries",
        )
    require(
        receipt["metadata_review_sha256"] is None
        or type(receipt["metadata_review_sha256"]) is str
        and core.HEX.fullmatch(receipt["metadata_review_sha256"]),
        "review-pin",
    )
    require(
        receipt["status"] != "completed" or receipt["metadata_review_sha256"] is not None,
        "complete-review-pin",
    )


@fixture_time.selected(3)
def inspect_receipt_metadata(
    receipt_raw,
    held_producer_sha256,
    held,
    *,
    fixture=False,
    review_raw=None,
    held_review_sha256=None,
):
    """Byte-only metadata reconstruction; NEVER opens or hashes stored source bodies.

    Caller must separately hold the producer receipt pin. This cold record proves
    metadata consistency, not fresh stored-text integrity or publisher authenticity.
    """
    require(
        type(fixture) is bool
        and type(receipt_raw) is bytes
        and 0 < len(receipt_raw) <= 65536
        and type(held_producer_sha256) is str
        and core.HEX.fullmatch(held_producer_sha256)
        and digest(receipt_raw) == held_producer_sha256,
        "held-producer-metadata",
    )
    require(core._now() < core._utc(DEADLINE), "current-retention")
    source_before = _cold_binding(held)
    receipt = decode(receipt_raw)
    _validate_receipt(receipt, held, fixture)
    if receipt["metadata_review_sha256"] is not None:
        require(
            type(review_raw) is bytes
            and 0 < len(review_raw) <= 65536
            and held_review_sha256 == receipt["metadata_review_sha256"] == digest(review_raw),
            "held-review-metadata",
        )
        review = decode(review_raw)
        expected = {
            "schema": SCHEMA,
            "kind": "static-text-quality-metadata-only",
            "rows": receipt["rows"],
            "raw_source_text_returned": False,
            "evaluated_or_resolved": False,
            "full_license_or_tag_tree_authenticated": False,
        }
        require(encode(review) == encode(expected), "cold-static-metadata-reconstruction")
    else:
        require(review_raw is None and held_review_sha256 is None, "no-unissued-review")
    require(_cold_binding(held) == source_before, "cold-current-source-owner-drift")
    return {
        "schema": SCHEMA,
        "status": "producer-metadata-reconstructed",
        "kind": "invented" if fixture else "source-discovery-metadata",
        "producer_status": receipt["status"],
        "source_bodies_reopened_or_hashed": False,
        "current_source_body_integrity_verified": False,
        "publisher_authenticated": False,
        "GH_execution_authorized": False,
        "authority": dict(AUTHORITY),
    }


def _objects_binding(directory, objects):
    core._private_directory(objects)
    opened = os.fstat(objects)
    named = os.stat("objects", dir_fd=directory, follow_symlinks=False)
    require(
        stat.S_ISDIR(named.st_mode)
        and opened.st_dev == named.st_dev
        and opened.st_ino == named.st_ino,
        "objects-physical-binding",
    )


def _summarize_mod(text):
    """Bounded lexical labels, not a Go parser, dependency solver or trust check."""
    result = {
        "kind": "go-mod-lexical-candidates",
        "module": None,
        "go": None,
        "toolchain": None,
        "dependencies": [],
        "dependency_candidate_count": 0,
        "unknown_directives": [],
        "unparsed_lines": 0,
        "oversized_lines": 0,
        "labels_truncated": False,
        "ambiguous_headers": [],
        "semantic_or_dependency_closure_verified": False,
    }
    in_require = False
    headers = set()
    for original in text.splitlines():
        if len(original.encode()) > 4096:
            result["oversized_lines"] += 1
            continue
        line = original.split("//", 1)[0].strip()
        if not line:
            continue
        parts = line.split()
        first = parts[0]
        if line == ")":
            in_require = False
            continue
        if first in ("module", "go", "toolchain"):
            valid = len(parts) == 2 and re.fullmatch(r"[A-Za-z0-9._~+/-]{1,256}", parts[1])
            if first in headers:
                result[first] = None
                if first not in result["ambiguous_headers"]:
                    result["ambiguous_headers"].append(first)
            elif valid:
                result[first] = parts[1]
            else:
                result["unparsed_lines"] += 1
            headers.add(first)
            continue
        if line == "require (":
            in_require = True
            continue
        dep = parts[1:] if first == "require" else parts if in_require else None
        if dep is not None:
            if (
                len(dep) == 2
                and re.fullmatch(r"[A-Za-z0-9._~+/-]{1,256}", dep[0])
                and re.fullmatch(r"[A-Za-z0-9.+_-]{1,128}", dep[1])
            ):
                result["dependency_candidate_count"] += 1
                if len(result["dependencies"]) < 64:
                    result["dependencies"].append({"module": dep[0], "version": dep[1]})
                else:
                    result["labels_truncated"] = True
            else:
                result["unparsed_lines"] += 1
            continue
        if (
            re.fullmatch(r"[A-Za-z][A-Za-z0-9_-]{0,31}", first)
            and first not in result["unknown_directives"]
        ):
            if len(result["unknown_directives"]) < 16:
                result["unknown_directives"].append(first)
            else:
                result["labels_truncated"] = True
        result["unparsed_lines"] += 1
    return result


def _validate_static(value, name):
    if name != "go.mod":
        require(
            encode(value)
            == encode({"kind": "size-hash-UTF8-linecount-only", "semantic_evaluation": False}),
            "static-summary-scope",
        )
        return
    fields(
        value,
        "kind module go toolchain dependencies dependency_candidate_count unknown_directives "
        "unparsed_lines oversized_lines labels_truncated ambiguous_headers "
        "semantic_or_dependency_closure_verified",
        "mod-summary-fields",
    )
    require(
        value["kind"] == "go-mod-lexical-candidates"
        and value["semantic_or_dependency_closure_verified"] is False
        and type(value["labels_truncated"]) is bool,
        "mod-summary-untrusted",
    )
    for key in ("module", "go", "toolchain"):
        require(
            value[key] is None
            or type(value[key]) is str
            and re.fullmatch(r"[A-Za-z0-9._~+/-]{1,256}", value[key]),
            "bounded-mod-header",
        )
    for key in ("dependency_candidate_count", "unparsed_lines", "oversized_lines"):
        require(type(value[key]) is int and 0 <= value[key] <= 65536, "mod-summary-count")
    require(
        type(value["dependencies"]) is list
        and len(value["dependencies"]) <= 64
        and type(value["unknown_directives"]) is list
        and len(value["unknown_directives"]) <= 16
        and type(value["ambiguous_headers"]) is list
        and len(value["ambiguous_headers"]) <= 3,
        "mod-summary-list-cap",
    )
    for dep in value["dependencies"]:
        fields(dep, "module version", "dependency-label-fields")
        require(
            type(dep["module"]) is str
            and re.fullmatch(r"[A-Za-z0-9._~+/-]{1,256}", dep["module"])
            and type(dep["version"]) is str
            and re.fullmatch(r"[A-Za-z0-9.+_-]{1,128}", dep["version"]),
            "dependency-label-bounds",
        )
    require(
        all(
            type(x) is str and re.fullmatch(r"[A-Za-z][A-Za-z0-9_-]{0,31}", x)
            for x in value["unknown_directives"]
        )
        and all(x in ("module", "go", "toolchain") for x in value["ambiguous_headers"]),
        "unknown-directive-labels",
    )


def _cold_binding(held):
    fields(
        held,
        "plan_sha256 approval_sha256 origin_sha256 source_sha256 owner_sha256 "
        "rights_basis_sha256 output_root",
        "cold-held-fields",
    )
    source, owner = _identity(), _owner()
    require(
        digest(encode(source)) == held["source_sha256"]
        and digest(encode(owner)) == held["owner_sha256"],
        "cold-current-source-owner-binding",
    )
    return source, owner
