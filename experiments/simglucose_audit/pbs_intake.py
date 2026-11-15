"""Closed PBS entry and explicitly approved future opaque-copy executor.

No gzip, tar, member, signature or executable inspection exists here. Tests use
invented bytes only. Streaming SHA records bytes written, not a cold readback.
Owned watchdogs bound ordinary blocking work, not uninterruptible kernel work.
The caller holding approval pins is the trust boundary; JSON cannot mint trust.
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
from datetime import timedelta
from pathlib import Path
from urllib.parse import urlsplit

from experiments import platform_process

from . import intake_collector as core
from .contract import AUTHORITY, SOURCE_FILES, decode, digest, encode, fields, require

ROOT = Path(__file__).resolve().parents[2]
SCHEMA = "opent1d.pbs-opaque-intake/1"
URL = "https://github.com/astral-sh/python-build-standalone/releases/download/20261026/cpython-3.12.16%2B20261026-aarch64-apple-darwin-install_only.tar.gz"
SIZE = 25172086
SHA = "fbf4afef53c2a6b72bb741bc06d5671a9dfaf87bd84e5aa73ac9b3d0d589f14e"
DEADLINE = "2026-11-28T18:32:01Z"
CDN = "release-assets.githubusercontent.com"
PREFIX = "/github-production-release-asset/162334160/"
LIMITS = {
    "requests": 2,
    "redirects": 1,
    "body_bytes": SIZE + 1,
    "header_bytes": 8192,
    "header_count": 64,
    "status_line_bytes": 256,
    "request_seconds": 60,
    "whole_seconds": 300,
    "start_headroom_seconds": 310,
    "receipt_bytes": 65536,
    "body_readback_passes": 0,
    "root_files": 2,
    "root_bytes": SIZE + 1 + 65536,
    "consumption_marker_bytes": 128,
}
RETENTION = dict(core.RETENTION, known_earlier_utc=DEADLINE)
CHUNK_BYTES = 65536
FRAME_LIMIT = 512
CASES = (
    "ok",
    "extra",
    "short",
    "wrong",
    "redirect",
    "stall-connect",
    "stall-header",
    "stall-body",
    "stall-storage",
    "stall-fsync",
    "stall-finalize",
    "late-source",
)
FIXTURE = b"INVENTED OPAQUE PBS FIXTURE\n" * 41
COVERAGE = ("target-metadata", "collector-source", "rights-basis", "proof-allocation")


def run_intake(*_args, **_kwargs):
    raise PermissionError("PBS intake remains closed without exact external approval")


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
        "pbs_intake.py": _source_hash(Path(__file__), expiry),
    }


def _owner(expiry=None):
    return {name: _source_hash(ROOT / name, expiry) for name in platform_process.SOURCE_FILES}


def _target(fixture=False):
    return {
        "url": URL,
        "published_bytes": len(FIXTURE) if fixture else SIZE,
        "published_sha256": digest(FIXTURE) if fixture else SHA,
        "asset_id": 678574498,
        "release": "20261026",
        "python": "3.12.16",
        "source_commit": "fa506e0858ac9f2cc5b289c137b888a2aa24d1ee",
    }


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
        "schema kind target limits retention source owner rights_basis_sha256 "
        "qualification_sha256 output_root parent_identity origin_sha256",
        "plan-fields",
    )
    require(
        plan["schema"] == SCHEMA and plan["kind"] == ("invented" if fixture else "opaque-pbs-plan"),
        "plan-kind",
    )
    require(
        encode(plan["target"]) == encode(_target(fixture))
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
        and Path(output).name == ("invented-intake" if fixture else "proposed-opaque-pbs-intake"),
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
        and approval["scope"] == "one-opaque-pbs-copy-no-readback"
        and encode(approval["authority"]) == encode(AUTHORITY),
        "exact-private-approval",
    )
    issued, expires = core._utc(approval["issued_utc"]), core._utc(approval["expires_utc"])
    require(issued <= now < expires <= issued + timedelta(days=30), "approval-window")
    expiry = min(expires, *deadlines)
    require(
        (expiry - now).total_seconds() >= (310 if headroom else 0) and now < expiry,
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


def _redirect(value):
    require(
        type(value) is str
        and len(value) <= 4096
        and value.isascii()
        and all(32 < ord(c) < 127 for c in value),
        "redirect-ascii-bounds",
    )
    parsed = urlsplit(value)
    require(
        parsed.scheme == "https"
        and parsed.netloc == CDN
        and not parsed.fragment
        and parsed.path.startswith(PREFIX)
        and len(parsed.path) > len(PREFIX)
        and "%" not in parsed.path
        and "\\" not in parsed.path
        and "//" not in parsed.path
        and all(part not in (".", "..") for part in parsed.path.split("/")),
        "fixed-cdn-redirect",
    )
    return value  # Ephemeral query stays in transport memory only.


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
    sock = socket.create_connection((parsed.hostname, 443), timeout=60)
    try:
        return context.wrap_socket(sock, server_hostname=parsed.hostname)
    except BaseException:
        sock.close()
        raise


def _emit(value):
    sys.stdout.buffer.write(encode(value) + b"\n")
    sys.stdout.buffer.flush()


def _response(connection, url, expected, redirected):
    parsed = urlsplit(url)
    path = parsed.path + ("?" + parsed.query if parsed.query else "")
    connection.sendall(
        (
            f"GET {path} HTTP/1.1\r\nHost: {parsed.hostname}\r\n"
            "Accept-Encoding: identity\r\nConnection: close\r\n\r\n"
        ).encode("ascii")
    )
    raw = bytearray()
    while not raw.endswith(b"\r\n\r\n"):
        require(len(raw) < 8192, "header-cap")
        part = connection.recv(1)
        require(part, "header-eof")
        raw += part
    status, headers = _headers(bytes(raw))
    if status in (301, 302, 303, 307, 308):
        require(not redirected and "location" in headers, "one-redirect-only")
        return _redirect(headers["location"])
    require(status == 200 and "location" not in headers, "final-status")
    if "content-length" in headers:
        require(headers["content-length"] == str(expected), "exact-content-length")
    _emit({"phase": "headers", "redirected": redirected})
    consumed, pending = 0, bytearray()
    while consumed < expected + 1:
        maximum = min(CHUNK_BYTES - len(pending), expected + 1 - consumed)
        raw = connection.recv(maximum)
        if not raw:
            break
        require(len(raw) <= maximum, "opaque-body-cap")
        consumed += len(raw)
        pending += raw
        if len(pending) == CHUNK_BYTES:
            _emit({"phase": "body", "data": base64.b64encode(pending).decode("ascii")})
            pending.clear()
    if pending:
        _emit({"phase": "body", "data": base64.b64encode(pending).decode("ascii")})
    _emit({"phase": "done", "bytes": consumed})
    return None


def _fetch_entry(fixture, case, redirected=False):
    try:
        if fixture:
            require(case in CASES, "invented-case")

            def deny(event, _args):
                if event in ("socket.connect", "socket.getaddrinfo"):
                    raise PermissionError("fixture-network-denied")

            sys.addaudithook(deny)
            if case in ("stall-connect", "stall-header"):
                time.sleep(30)
            _emit({"phase": "headers", "redirected": case == "redirect"})
            body = FIXTURE + (b"!" if case == "extra" else b"")
            if case == "short":
                body = body[:-1]
            if case == "wrong":
                body = b"?" + body[1:]
            _emit({"phase": "body", "data": base64.b64encode(body).decode("ascii")})
            if case == "stall-body":
                time.sleep(30)
            _emit({"phase": "done", "bytes": len(body)})
            return
        require(case is None and type(redirected) is bool, "actual-no-fixture-selector")
        # One leaf performs one request; a redirect is returned privately to controller.
        url = URL if not redirected else sys.stdin.buffer.read(4097).decode("ascii")
        require(not redirected or _redirect(url) == url, "redirect-revalidation")
        connection = _connect(url)
        try:
            location = _response(connection, url, SIZE, redirected)
            if location is not None:
                _emit({"phase": "redirect", "url": location})
        finally:
            connection.close()
    except (OSError, ValueError, TimeoutError):
        _emit({"phase": "error"})  # Never interpolate transport exceptions/URLs.


def _script(call):
    return (
        "import sys;sys.path.insert(0,"
        + repr(str(ROOT))
        + ");from experiments.simglucose_audit.pbs_intake import "
        + call
    )


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


def _request(wire, fd, hasher, count, deadline, expiry, redirect=None):
    fixture, case = wire["fixture"], wire["case"]
    seconds = wire["request_seconds"]
    stop = min(deadline, time.monotonic() + seconds)
    read_until = stop - min(1, seconds / 3)
    process = subprocess.Popen(
        [
            sys.executable,
            "-I",
            "-S",
            "-B",
            "-c",
            _script(f"_fetch_entry;_fetch_entry({fixture!r},{case!r},{redirect is not None!r})"),
        ],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        cwd=ROOT,
        env=core._environment(),
    )  # Inherits owned controller session.
    events, writers = queue.Queue(maxsize=8), []
    reader = writer = None
    headers, done, location = False, False, None
    try:
        reader, writer = _io_threads(process, (redirect or "").encode("ascii"), events, writers)
        reader.start()
        writer.start()
        while True:
            _live(expiry, read_until)
            try:
                kind, frame = events.get(timeout=max(0.001, read_until - time.monotonic()))
            except queue.Empty:
                raise TimeoutError("request-watchdog") from None
            if kind == "eof":
                require(done or location is not None, "complete-response")
                process.wait(timeout=max(0.001, read_until - time.monotonic()))
                require(process.returncode == 0 and writers == [True], "fetch-exit")
                return count, location
            require(kind == "frame" and type(frame) is dict, "fetch-protocol")
            phase = frame.get("phase")
            if phase == "headers":
                fields(frame, "phase redirected", "header-frame")
                require(
                    not headers
                    and not done
                    and frame["redirected"]
                    is (redirect is not None or fixture and case == "redirect"),
                    "header-order",
                )
                headers = True
            elif phase == "body":
                fields(frame, "phase data", "body-frame")
                require(headers and not done and type(frame["data"]) is str, "body-order")
                raw = base64.b64decode(frame["data"], validate=True)
                expected = _target(fixture)["published_bytes"]
                require(
                    0 < len(raw) <= CHUNK_BYTES and count + len(raw) <= expected + 1, "sentinel-cap"
                )
                if fixture and case == "stall-storage":
                    time.sleep(30)
                offset = 0
                while offset < len(raw):
                    _live(expiry, deadline)
                    written = os.write(fd, raw[offset:])
                    require(written > 0, "body-write-progress")
                    hasher.update(raw[offset : offset + written])
                    count += written
                    offset += written
            elif phase == "done":
                fields(frame, "phase bytes", "done-frame")
                require(
                    headers
                    and not done
                    and type(frame["bytes"]) is int
                    and frame["bytes"] == count,
                    "body-count",
                )
                done = True
            elif phase == "redirect":
                fields(frame, "phase url", "redirect-frame")
                require(
                    not headers and not done and count == 0 and redirect is None, "redirect-order"
                )
                location = _redirect(frame["url"])
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


def _receipt(wire, status, count, sha, error):
    return {
        "schema": SCHEMA,
        "kind": "invented" if wire["fixture"] else "opaque-pbs-receipt",
        "status": status,
        "bytes": count,
        "stored_sha256": sha,
        "hash_basis": "producer-stream-write-observation-not-cold-verified",
        "accepted_sha256": sha if status == "completed" else None,
        "body_path": "archive.opaque",
        "body_readback_passes": 0,
        "pins": wire["held"],
        "authority": dict(AUTHORITY),
        "authentication_verified": False,
        "members_inspected": False,
        "runtime_use_authorized": False,
        "actual_tls_observed": False,
        "retention": RETENTION,
        "approval_consumed": True,
        "ended_utc": core._stamp(core._now()),
        "error": error,
    }


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


def _controller(wire):
    plan, expiry = _inputs(wire, True)
    deadline = min(wire["deadline"], time.monotonic() + (expiry - core._now()).total_seconds())
    parent = core._directory(str(Path(plan["output_root"]).parent))
    try:
        require(_parent_identity(parent) == plan["parent_identity"], "physical-parent-current")
        _live(expiry, deadline)
        marker = ".pbs-consumed-" + wire["held"]["approval_sha256"]
        core._write_file(
            parent, marker, encode({"approval_sha256": wire["held"]["approval_sha256"]})
        )
        _live(expiry, deadline)
        name = Path(plan["output_root"]).name
        os.mkdir(name, 0o700, dir_fd=parent)
        os.fsync(parent)
        directory = os.open(name, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=parent)
        core._private_directory(directory)
        _namespace(directory, plan)
    finally:
        os.close(parent)
    fd, count, hasher, error = None, 0, hashlib.sha256(), None
    try:
        _live(expiry, deadline)
        fd = os.open(
            "archive.opaque",
            os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
            0o600,
            dir_fd=directory,
        )
        core._regular(fd)
        try:
            count, redirect = _request(wire, fd, hasher, count, deadline, expiry)
            if redirect is not None:
                count, second = _request(wire, fd, hasher, count, deadline, expiry, redirect)
                require(second is None, "one-redirect")
        except (OSError, ValueError, RuntimeError, TimeoutError, subprocess.TimeoutExpired):
            error = "transport-or-storage-rejected"
        count = os.fstat(fd).st_size
        require(count <= plan["target"]["published_bytes"] + 1, "stored-body-cap")
        _live(expiry, deadline)
        _namespace(directory, plan)
        if wire["fixture"] and wire["case"] == "stall-fsync":
            time.sleep(30)
        os.fsync(fd)
        opened = os.fstat(fd)
        named = os.stat("archive.opaque", dir_fd=directory, follow_symlinks=False)
        core._regular(fd)
        require(core._fingerprint(opened) == core._fingerprint(named), "body-physical-binding")
        plan_after, _ = _inputs(wire)
        require(plan_after == plan, "late-plan-binding")
        if wire["fixture"] and wire["case"] == "late-source":
            raise ValueError("invented-late-source-change")
        target = plan["target"]
        accepted = (
            error is None
            and count == target["published_bytes"]
            and hasher.hexdigest() == target["published_sha256"]
        )
        receipt = _receipt(
            wire, "completed" if accepted else "rejected", count, hasher.hexdigest(), error
        )
        if wire["fixture"] and wire["case"] == "stall-finalize":
            time.sleep(30)
        _live(expiry, deadline)
        _namespace(directory, plan)
        raw = encode(receipt)
        require(len(raw) <= 65536, "receipt-cap")
        core._write_file(directory, "intake-receipt.private.json", raw)
        _live(expiry, deadline)
        _inputs(wire)
        _emit({"receipt": receipt})
    finally:
        if fd is not None:
            os.close(fd)
        os.close(directory)


def _recover(wire):
    plan, expiry = _inputs(wire)
    _live(expiry, wire["deadline"])
    directory = core._directory(plan["output_root"])
    try:
        _namespace(directory, plan)
        # Exactly the same exclusive receipt pathname, never a second partial record.
        try:
            os.stat("intake-receipt.private.json", dir_fd=directory, follow_symlinks=False)
        except FileNotFoundError:
            pass
        else:
            raise ValueError("receipt-path-already-consumed")
        _live(expiry, wire["deadline"])
        fd = os.open(
            "archive.opaque", os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=directory
        )
        try:
            core._regular(fd)
            opened = os.fstat(fd)
            named = os.stat("archive.opaque", dir_fd=directory, follow_symlinks=False)
            require(core._fingerprint(opened) == core._fingerprint(named), "recovery-body-binding")
            count = opened.st_size  # Metadata only: NO opaque-body read.
        finally:
            os.close(fd)
        require(count <= plan["target"]["published_bytes"] + 1, "recovery-prefix-cap")
        receipt = _receipt(wire, "incomplete", count, None, "owned-controller-failure")
        _live(expiry, wire["deadline"])
        _namespace(directory, plan)
        raw = encode(receipt)
        require(len(raw) <= 65536, "recovery-receipt-cap")
        core._write_file(directory, "intake-receipt.private.json", raw)
        _live(expiry, wire["deadline"])
        _inputs(wire)
        _emit({"receipt": receipt})
    finally:
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
            and 0 < wire["request_seconds"] <= 60,
            "fixed-wire-mode",
        )
        if wire["recovery"]:
            _recover(wire)
        else:
            _controller(wire)
    except (OSError, ValueError, RuntimeError, TimeoutError):
        _emit({"error": "controller-rejected"})


def _execute(
    plan_raw,
    approval_raw,
    origin_raw,
    held,
    fixture=False,
    case=None,
    whole_seconds=300,
    request_seconds=60,
):
    start = time.monotonic()
    deadline = start + whole_seconds
    _gate(plan_raw, approval_raw, origin_raw, held, fixture, True)
    require(time.monotonic() < deadline, "preflight-whole-watchdog")
    require(not Path(held["output_root"]).exists(), "one-attempt-no-resume")
    # Four seconds inside the whole window reserve stop + metadata-only recovery.
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
    require(time.monotonic() < deadline, "whole-watchdog")
    if receipt is None and deadline - time.monotonic() > 0.3:
        wire["recovery"] = True
        wire["deadline"] = min(time.monotonic() + 1, deadline - 0.2)
        receipt = _supervise(wire, deadline)
    require(time.monotonic() < deadline, "whole-finalization-watchdog")
    _gate(plan_raw, approval_raw, origin_raw, held, fixture)
    if receipt is None:
        # Existing prefix/partial receipt are retained; no body read or retry.
        return {
            "schema": SCHEMA,
            "kind": "invented" if fixture else "opaque-pbs-failure",
            "status": "incomplete",
            "error": "owned-controller-failure",
            "output_root": held["output_root"],
            "body_readback_passes": 0,
            "accepted_sha256": None,
            "durability_claimed": False,
            "authority": dict(AUTHORITY),
        }
    _, expiry = _gate(plan_raw, approval_raw, origin_raw, held, fixture)
    _validate_receipt(receipt, held, fixture, core._utc(decode(approval_raw)["issued_utc"]), expiry)
    return receipt


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


def _validate_receipt(receipt, held, fixture, issued=None, expiry=None):
    fields(
        receipt,
        "schema kind status bytes stored_sha256 hash_basis accepted_sha256 body_path "
        "body_readback_passes pins authority authentication_verified members_inspected "
        "runtime_use_authorized actual_tls_observed retention approval_consumed ended_utc error",
        "receipt-fields",
    )
    require(
        receipt["hash_basis"] == "producer-stream-write-observation-not-cold-verified"
        and receipt["schema"] == SCHEMA
        and receipt["kind"] == ("invented" if fixture else "opaque-pbs-receipt")
        and receipt["pins"] == held
        and encode(receipt["authority"]) == encode(AUTHORITY)
        and receipt["retention"] == RETENTION
        and receipt["body_path"] == "archive.opaque"
        and type(receipt["body_readback_passes"]) is int
        and receipt["body_readback_passes"] == 0
        and receipt["approval_consumed"] is True
        and all(
            receipt[key] is False
            for key in (
                "authentication_verified",
                "members_inspected",
                "runtime_use_authorized",
                "actual_tls_observed",
            )
        ),
        "receipt-scope",
    )
    target = _target(fixture)
    require(
        type(receipt["bytes"]) is int
        and 0 <= receipt["bytes"] <= target["published_bytes"] + 1
        and (
            receipt["stored_sha256"] is None
            if receipt["status"] == "incomplete"
            else type(receipt["stored_sha256"]) is str
            and core.HEX.fullmatch(receipt["stored_sha256"])
        ),
        "receipt-integrity-fields",
    )
    ended = core._utc(receipt["ended_utc"])
    require(
        ended <= core._now()
        and ended < core._utc(DEADLINE)
        and (issued is None or issued <= ended)
        and (expiry is None or ended < expiry)
        and receipt["error"] in (None, "transport-or-storage-rejected", "owned-controller-failure"),
        "receipt-execution-window",
    )
    if receipt["status"] == "completed":
        require(
            receipt["bytes"] == target["published_bytes"]
            and receipt["stored_sha256"] == receipt["accepted_sha256"] == target["published_sha256"]
            and receipt["error"] is None,
            "exact-completed-identity",
        )
    else:
        require(
            receipt["status"] in ("rejected", "incomplete") and receipt["accepted_sha256"] is None,
            "rejected-no-identity-promotion",
        )


def collect_approved(plan_raw, approval_raw, origin_raw, held):
    """Trusted caller must independently hold exact approval and policy pins.

    This function is not called by CLI or fixtures. No plan self-hash grants
    permission. Calling it consumes the attempt once the fresh root is created.
    Existing/partial roots always refuse. There is no retry or cleanup facility.
    """
    return _execute(plan_raw, approval_raw, origin_raw, held)


def fixture_inputs(output):
    """Invented metadata, incapable of admission through collect_approved."""
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
        "target": _target(True),
        "limits": LIMITS,
        "retention": RETENTION,
        "source": _identity(),
        "owner": _owner(),
        "rights_basis_sha256": digest(b"INVENTED RIGHTS ONLY"),
        "qualification_sha256": digest(b"INVENTED QUALIFICATION ONLY"),
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
        "scope": "one-opaque-pbs-copy-no-readback",
        "authority": dict(AUTHORITY),
    }
    approval_raw = encode(approval)
    held["approval_sha256"] = digest(approval_raw)
    return plan_raw, approval_raw, origin_raw, held


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
