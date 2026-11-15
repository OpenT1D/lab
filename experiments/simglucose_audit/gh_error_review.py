"""One bounded retained-container pass and one escaped private stderr view.

No executable, network, diagnostic instruction or embedded path is invoked.
Actual identities and consent exist only in the externally held private plan.
Ordinary entry is closed; fixture inputs are internally minted and immutable.
"""

import base64
import binascii
import hashlib
import os
import queue
import re
import stat
import subprocess
import sys
import threading
import time
from datetime import timedelta
from pathlib import Path

from experiments import platform_process

from . import fixture_time
from . import intake_collector as core
from . import retained_source_review as previous
from .contract import AUTHORITY, decode, digest, encode, fields, require

ROOT = Path(__file__).resolve().parents[2]
SCHEMA = "opent1d.gh-error-review/1"
PRODUCER_SCHEMA = "opent1d.gh-startup-probe/1"
CONTAINER_CAP = 8192
STDERR_CAP = 2048
ENVELOPE_CAP = 16384
RECEIPT_CAP = 16384
LIMITS = {
    "whole_seconds": 10,
    "stop_reserve_seconds": 2,
    "join_reserve_seconds": 1,
    "initial_headroom_seconds": 30,
    "input_forward_passes": 1,
    "material_view_attempts": 1,
    "envelope_bytes_including_newline": 16384,
    "receipt_bytes": 16384,
    "root_regular_files": 1,
    "root_regular_bytes": 16384,
    "parent_marker_bytes": 128,
    "outer_observation_bytes": 16384,
    "action_output_bytes": 32896,
}
CASES = (
    "ok",
    "read-stall",
    "parse-stall",
    "write-stall",
    "fsync-stall",
    "emit-stall",
    "late-error",
    "nonzero",
    "overflow-frame",
    "drip-frame",
    "descendant",
)
_FIXTURES = set()


def run_review(*_args, **_kwargs):
    raise PermissionError("error material review closed without exact new consent")


def _identity(expiry=None):
    return previous._identity(expiry) | {
        "gh_error_review.py": previous._source_hash(Path(__file__), expiry)
    }


def _owner(expiry=None):
    return previous._owner(expiry)


def _limits(plan):
    return LIMITS | {
        "input_application_bytes": plan["input"]["bytes"] + 1,
        "escaped_ascii_chars": plan["expected_stderr"]["bytes"] * 4,
    }


def _held_documents(plan_raw, approval_raw, origin_raw, held):
    fields(
        held,
        (
            "plan_sha256 approval_sha256 origin_sha256 source_sha256 owne"
            "r_sha256 rights_basis_sha256 producer_receipt_sha256 output_"
            "root"
        ),
        "held-fields",
    )
    for name, raw in (("plan", plan_raw), ("approval", approval_raw), ("origin", origin_raw)):
        require(
            type(raw) is bytes and 0 < len(raw) <= 32768 and digest(raw) == held[name + "_sha256"],
            "externally-held-document",
        )
    return tuple(map(decode, (plan_raw, approval_raw, origin_raw)))


@fixture_time.selected(4)
def _gate(
    plan_raw, approval_raw, origin_raw, held, fixture=False, headroom=False, historical_at=None
):
    require(type(fixture) is bool, "typed-fixed-mode")
    plan, approval, origin = _held_documents(plan_raw, approval_raw, origin_raw, held)
    fields(
        plan,
        (
            "schema kind input producer_receipt expected_stderr reader_so"
            "urce owner rights_basis_sha256 qualification_sha256 origin_s"
            "ha256 output_root parent_identity limits retention"
        ),
        "plan-fields",
    )
    require(
        plan["schema"] == SCHEMA
        and plan["kind"] == ("invented" if fixture else "private-error-review-plan"),
        "plan-kind",
    )
    source = plan["input"]
    fields(source, "path bytes sha256 token parent_identity", "input-fields")
    path = previous._path(source["path"])
    output = previous._path(plan["output_root"])
    require(
        type(source["bytes"]) is int
        and 0 < source["bytes"] <= CONTAINER_CAP
        and type(source["sha256"]) is str
        and core.HEX.fullmatch(source["sha256"]),
        "typed-container-identity",
    )
    token = source["token"]
    require(
        type(token) is list
        and len(token) == 9
        and all(type(v) is int for v in token)
        and token[2] == os.getuid()
        and token[3] == 0o600
        and token[4] == 1
        and token[5] == source["bytes"],
        "private-container-token",
    )
    for identity in (source["parent_identity"], plan["parent_identity"]):
        fields(identity, "dev ino uid mode", "parent-fields")
        require(
            all(type(v) is int for v in identity.values())
            and identity["uid"] == os.getuid()
            and identity["mode"] == 0o700,
            "private-parent",
        )
    require(
        str(output) == held["output_root"]
        and output.name == ("invented-error-review" if fixture else "proposed-gh-error-review")
        and path.parent != output
        and output not in path.parents,
        "fixed-output",
    )
    if fixture:
        require(path == output.parent / "invented-container.json", "fixed-fixture-path")
    fields(plan["expected_stderr"], "bytes sha256", "stderr-identity-fields")
    expected = plan["expected_stderr"]
    require(
        type(expected["bytes"]) is int
        and 0 < expected["bytes"] <= STDERR_CAP
        and expected["bytes"] <= source["bytes"]
        and type(expected["sha256"]) is str
        and core.HEX.fullmatch(expected["sha256"]),
        "typed-stderr-identity",
    )
    require(
        encode(plan["limits"]) == encode(_limits(plan))
        and plan["origin_sha256"] == held["origin_sha256"]
        and plan["rights_basis_sha256"] == held["rights_basis_sha256"],
        "fixed-budget-pins",
    )
    for name in ("rights_basis_sha256", "qualification_sha256"):
        require(type(plan[name]) is str and core.HEX.fullmatch(plan[name]), "required-policy-pin")
    producer = plan["producer_receipt"]
    require(
        type(producer) is dict
        and digest(encode(producer)) == held["producer_receipt_sha256"]
        and producer.get("report_sha256") == source["sha256"]
        and type(producer.get("report_bytes")) is int
        and producer["report_bytes"] == source["bytes"],
        "held-producer-report-lineage",
    )
    _producer_metadata(producer, expected)
    now = core._now() if historical_at is None else historical_at
    retention_end = previous._retention(plan["retention"])
    fields(
        origin,
        (
            "schema kind recorded_new_fact_utc not_after_UTC retention ol"
            "d_origins_reset unknown_older_origins_timely_claimed evidenc"
            "e_sha256"
        ),
        "origin-fields",
    )
    require(
        origin["schema"] == SCHEMA
        and origin["kind"] == ("invented" if fixture else "private-new-review-context")
        and encode(origin["retention"]) == encode(plan["retention"])
        and origin["old_origins_reset"] is False
        and origin["unknown_older_origins_timely_claimed"] is False
        and type(origin["evidence_sha256"]) is str
        and core.HEX.fullmatch(origin["evidence_sha256"]),
        "new-fact-only-origin",
    )
    first, end = core._utc(origin["recorded_new_fact_utc"]), core._utc(origin["not_after_UTC"])
    require(first <= now < end <= first + timedelta(days=30), "origin-window")
    fields(
        approval,
        (
            "schema kind plan_sha256 origin_sha256 source_sha256 owner_sh"
            "a256 rights_basis_sha256 producer_receipt_sha256 nonce issue"
            "d_utc expires_utc scope authority"
        ),
        "approval-fields",
    )
    require(
        approval["schema"] == SCHEMA
        and approval["kind"] == ("invented" if fixture else "private-one-shot-approval")
        and all(
            approval[k] == held[k]
            for k in (
                "plan_sha256",
                "origin_sha256",
                "source_sha256",
                "owner_sha256",
                "rights_basis_sha256",
                "producer_receipt_sha256",
            )
        )
        and type(approval["nonce"]) is str
        and re.fullmatch(r"[0-9a-f]{32}", approval["nonce"])
        and approval["scope"] == "one-retained-startup-report-read-and-one-escaped-stderr-view"
        and encode(approval["authority"]) == encode(AUTHORITY),
        "fresh-limited-approval",
    )
    issued, expires = core._utc(approval["issued_utc"]), core._utc(approval["expires_utc"])
    expiry = min(expires, end, retention_end)
    current_end = expiry if historical_at is None else min(end, retention_end)
    require(
        issued <= now < expires <= issued + timedelta(hours=1)
        and core._now() < current_end
        and (not headroom or (expiry - now).total_seconds() >= 30),
        "current-window-headroom",
    )
    require(
        plan["reader_source"] == _identity(current_end)
        and plan["owner"] == _owner(current_end)
        and digest(encode(plan["reader_source"])) == held["source_sha256"]
        and digest(encode(plan["owner"])) == held["owner_sha256"],
        "current-source-owner",
    )
    require(core._now() < current_end, "late-source-window")
    return plan, expiry


def _producer_metadata(producer, expected):
    # Exact full metadata equality is established against the held receipt digest.
    require(
        producer.get("schema") == PRODUCER_SCHEMA
        and producer.get("status") == "rejected"
        and producer.get("raw_outputs_in_receipt") is False
        and type(producer.get("report_readback_passes")) is int
        and producer["report_readback_passes"] == 0,
        "producer-observation-kind",
    )
    rows = producer.get("probes")
    require(type(rows) is list and len(rows) == 1, "one-producer-row")
    row = rows[0]
    fields(
        row,
        (
            "role status exit_code error consumed_application_bytes store"
            "d_bytes stored_sha256 parsed real_selected_tool_invocation r"
            "eal_crypto_or_artifact_verification"
        ),
        "producer-row-fields",
    )
    require(
        all(
            type(row[k]) is dict
            for k in ("consumed_application_bytes", "stored_bytes", "stored_sha256", "parsed")
        ),
        "producer-row-maps",
    )
    require(
        all(
            type(row[k].get(stream)) is int
            for k in ("consumed_application_bytes", "stored_bytes")
            for stream in ("stdout", "stderr")
        ),
        "producer-count-types",
    )
    require(
        type(row) is dict
        and row.get("role") == "version"
        and row.get("status") == "rejected"
        and type(row.get("exit_code")) is int
        and row["exit_code"] == 2
        and row.get("real_selected_tool_invocation") is True
        and row.get("real_crypto_or_artifact_verification") is False,
        "expected-rejected-version-only",
    )
    require(
        row.get("stored_bytes") == {"stdout": 0, "stderr": expected["bytes"]}
        and row.get("consumed_application_bytes") == {"stdout": 0, "stderr": expected["bytes"]}
        and row.get("stored_sha256") == {"stdout": digest(b""), "stderr": expected["sha256"]},
        "producer-stderr-only-identity",
    )
    require(
        encode(row.get("parsed")) == encode({"version_matches": False, "observed_help_markers": []})
        and row.get("error") is None,
        "no-producer-success-or-error-text",
    )


def escape_ascii(raw):
    require(type(raw) is bytes and len(raw) <= STDERR_CAP, "bounded-byte-view")
    return "".join(
        chr(byte)
        if 32 <= byte <= 126 and byte != 92
        else chr(92) * 2
        if byte == 92
        else "\\x" + format(byte, "02x")
        for byte in raw
    )


def reverse_ascii(text):
    require(type(text) is str and len(text) <= STDERR_CAP * 4, "bounded-ASCII-view")
    result = bytearray()
    index = 0
    while index < len(text):
        char = text[index]
        require(32 <= ord(char) <= 126, "ASCII-view-only")
        if char != "\\":
            result.append(ord(char))
            index += 1
            continue
        require(index + 1 < len(text), "complete-escape")
        if text[index + 1] == "\\":
            result.append(92)
            index += 2
            continue
        require(
            text[index + 1] == "x"
            and index + 3 < len(text)
            and re.fullmatch(r"[0-9a-f]{2}", text[index + 2 : index + 4]),
            "fixed-lowercase-hex-escape",
        )
        byte = int(text[index + 2 : index + 4], 16)
        require(byte < 32 or byte > 126, "canonical-nonprintable-escape")
        result.append(byte)
        index += 4
    require(
        len(result) <= STDERR_CAP and escape_ascii(bytes(result)) == text, "canonical-lossless-view"
    )
    return bytes(result)


def _namespace(directory, plan):
    parent = core._directory(str(Path(plan["output_root"]).parent))
    try:
        require(previous._parent_identity(parent) == plan["parent_identity"], "late-output-parent")
        opened = os.fstat(directory)
        named = os.stat(Path(plan["output_root"]).name, dir_fd=parent, follow_symlinks=False)
        require(
            stat.S_ISDIR(named.st_mode)
            and previous._token(opened)[:4] == previous._token(named)[:4],
            "late-output-root",
        )
        core._private_directory(directory)
        with os.scandir(directory) as entries:
            for i, entry in enumerate(entries):
                require(i < 1 and entry.name == "receipt.private.json", "one-metadata-file")
    finally:
        os.close(parent)


def _input_context(plan, expiry, deadline, fd=None):
    previous._live(expiry, deadline)
    source = plan["input"]
    path = Path(source["path"])
    parent = core._directory(str(path.parent))
    try:
        named_parent = path.parent.lstat()
        require(
            previous._parent_identity(parent) == source["parent_identity"]
            and previous._parent_identity(parent)
            == {
                "dev": named_parent.st_dev,
                "ino": named_parent.st_ino,
                "uid": named_parent.st_uid,
                "mode": stat.S_IMODE(named_parent.st_mode),
            },
            "input-parent-name-binding",
        )
        named = os.stat(path.name, dir_fd=parent, follow_symlinks=False)
        require(
            stat.S_ISREG(named.st_mode) and previous._token(named) == source["token"],
            "input-name-token",
        )
        if fd is not None:
            require(previous._token(os.fstat(fd)) == source["token"], "input-held-FD-token")
    finally:
        os.close(parent)


def _read_container(plan, expiry, deadline, case=None):
    _input_context(plan, expiry, deadline)
    source = plan["input"]
    previous._live(expiry, deadline)
    fd = os.open(source["path"], os.O_RDONLY | os.O_NONBLOCK | os.O_NOFOLLOW)
    try:
        core._regular(fd)
        _input_context(plan, expiry, deadline, fd)
        raw = bytearray()
        hasher = hashlib.sha256()
        while len(raw) < source["bytes"] + 1:
            previous._live(expiry, deadline)
            if case == "read-stall":
                time.sleep(30)
            part = os.read(fd, min(4096, source["bytes"] + 1 - len(raw)))
            if not part:
                break
            raw += part
            require(len(raw) <= source["bytes"], "container-overflow-sentinel")
            hasher.update(part)
        previous._live(expiry, deadline)
        _input_context(plan, expiry, deadline, fd)
        require(
            len(raw) == source["bytes"] and hasher.hexdigest() == source["sha256"],
            "single-pass-container-identity",
        )
        return bytes(raw)
    finally:
        os.close(fd)


def _decode_stderr(raw, plan):
    raw.decode("utf-8", "strict")
    require(not raw.startswith(b"\xef\xbb\xbf"), "strict-UTF8-JSON-without-BOM")
    report = decode(raw)
    fields(
        report,
        (
            "schema kind pins binary_hash_observation probes fixture_only"
            " authentication_or_runtime_admission"
        ),
        "seven-report-fields",
    )
    producer = plan["producer_receipt"]
    require(
        report["schema"] == PRODUCER_SCHEMA
        and report["kind"] == "private-startup-output-report"
        and encode(report["pins"]) == encode(producer["pins"])
        and encode(report["binary_hash_observation"]) == encode(producer["binary_hash_observation"])
        and report["fixture_only"] is False
        and report["authentication_or_runtime_admission"] is False,
        "exact-producer-report-context",
    )
    rows = report["probes"]
    require(type(rows) is list and len(rows) == 1 and type(rows[0]) is dict, "only-one-report-row")
    row = rows[0]
    require(
        set(row) == set(producer["probes"][0]) | {"raw_base64"}
        and encode({k: v for k, v in row.items() if k != "raw_base64"})
        == encode(producer["probes"][0]),
        "whole-probe-row-equality",
    )
    fields(row["raw_base64"], "stdout stderr", "two-encoded-stream-fields")
    require(
        row["raw_base64"]["stdout"] == "" and type(row["raw_base64"]["stderr"]) is str,
        "stderr-only-view",
    )
    encoded = row["raw_base64"]["stderr"]
    require(len(encoded) <= 4 * ((plan["expected_stderr"]["bytes"] + 2) // 3), "encoded-stderr-cap")
    try:
        decoded = base64.b64decode(encoded, validate=True)
    except (ValueError, binascii.Error):
        raise ValueError("canonical-base64-required") from None
    require(
        base64.b64encode(decoded).decode() == encoded
        and len(decoded) == plan["expected_stderr"]["bytes"]
        and digest(decoded) == plan["expected_stderr"]["sha256"],
        "decoded-stderr-identity",
    )
    return decoded


def _consume(plan, held, expiry, deadline):
    parent = core._directory(str(Path(plan["output_root"]).parent))
    try:
        require(previous._parent_identity(parent) == plan["parent_identity"], "marker-parent")
        raw = encode({"approval_sha256": held["approval_sha256"], "kind": "GHerror"})
        require(len(raw) <= 128, "marker-cap")
        previous._write_checked(
            parent, ".gh-error-consumed-" + held["approval_sha256"], raw, expiry, deadline
        )
    finally:
        os.close(parent)


def _write_receipt(directory, raw, expiry, deadline, case=None):
    require(len(raw) <= RECEIPT_CAP, "receipt-cap")
    previous._live(expiry, deadline)
    fd = os.open(
        "receipt.private.json",
        os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
        0o600,
        dir_fd=directory,
    )
    try:
        core._regular(fd)
        done = 0
        while done < len(raw):
            previous._live(expiry, deadline)
            if case == "write-stall":
                time.sleep(30)
            n = os.write(fd, raw[done:])
            require(0 < n <= len(raw) - done, "receipt-write-progress")
            done += n
        previous._live(expiry, deadline)
        if case == "fsync-stall":
            time.sleep(30)
        previous._live(expiry, deadline)
        os.fsync(fd)
        previous._live(expiry, deadline)
        require(
            previous._token(os.fstat(fd))
            == previous._token(
                os.stat("receipt.private.json", dir_fd=directory, follow_symlinks=False)
            ),
            "metadata-FD-name-binding",
        )
    finally:
        os.close(fd)


def _validate_receipt(receipt, plan, held, issued, expiry, fixture=False):
    fields(
        receipt,
        (
            "schema kind status pins input_bytes input_sha256 input_passe"
            "s decoded_bytes decoded_sha256 escape_encoding material_view"
            "_prepared downstream_display_confirmed new_local_material_fi"
            "le_written metadata_receipt_readback_passes ended_utc author"
            "ity retention"
        ),
        "receipt-fields",
    )
    require(
        receipt["schema"] == SCHEMA
        and receipt["kind"] == ("invented" if fixture else "error-review-receipt")
        and receipt["status"] == "prepared"
        and receipt["pins"] == held
        and encode(receipt["authority"]) == encode(AUTHORITY)
        and encode(receipt["retention"]) == encode(plan["retention"]),
        "receipt-exact-bindings",
    )
    require(
        type(receipt["input_bytes"]) is int
        and receipt["input_bytes"] == plan["input"]["bytes"]
        and receipt["input_sha256"] == plan["input"]["sha256"]
        and type(receipt["input_passes"]) is int
        and receipt["input_passes"] == 1
        and type(receipt["decoded_bytes"]) is int
        and receipt["decoded_bytes"] == plan["expected_stderr"]["bytes"]
        and receipt["decoded_sha256"] == plan["expected_stderr"]["sha256"],
        "receipt-byte-identities",
    )
    require(
        receipt["escape_encoding"] == "printable-ASCII-backslash-or-lowercase-hex-v1"
        and receipt["material_view_prepared"] is True
        and receipt["downstream_display_confirmed"] is False
        and receipt["new_local_material_file_written"] is False
        and type(receipt["metadata_receipt_readback_passes"]) is int
        and receipt["metadata_receipt_readback_passes"] == 0,
        "no-extra-material-or-display-claim",
    )
    require(
        issued <= core._utc(receipt["ended_utc"]) < expiry
        and core._utc(receipt["ended_utc"]) <= core._now(),
        "historical-execution-window",
    )


def validate_review_result(result, plan, held, issued, expiry, fixture=False):
    """Pure parent validation; never opens a path or evaluates escaped material."""
    require(len(encode(result)) + 1 <= ENVELOPE_CAP, "bounded-single-view-envelope")
    fields(result, "review review_receipt", "result-fields")
    _validate_receipt(result["review_receipt"], plan, held, issued, expiry, fixture)
    view = result["review"]
    fields(view, "escaped_ascii decoded_bytes decoded_sha256 untrusted_data", "view-fields")
    require(
        view["untrusted_data"] is True
        and type(view["decoded_bytes"]) is int
        and view["decoded_bytes"] == plan["expected_stderr"]["bytes"]
        and view["decoded_sha256"] == plan["expected_stderr"]["sha256"]
        and type(view["escaped_ascii"]) is str
        and len(view["escaped_ascii"]) <= plan["expected_stderr"]["bytes"] * 4,
        "view-exact-scope",
    )
    decoded = reverse_ascii(view["escaped_ascii"])
    require(
        len(decoded) == view["decoded_bytes"] and digest(decoded) == view["decoded_sha256"],
        "parent-independent-view-integrity",
    )
    return result


def _emit(value):
    raw = encode(value) + b"\n"
    require(len(raw) <= ENVELOPE_CAP, "bounded-private-frame")
    sys.stdout.buffer.write(raw)
    sys.stdout.buffer.flush()


def _worker_gate(wire, headroom=False):
    return _gate(
        *(base64.b64decode(wire[n], validate=True) for n in ("plan", "approval", "origin")),
        wire["held"],
        wire["fixture"],
        headroom,
    )


def _produce(wire):
    plan, expiry = _worker_gate(wire, True)
    deadline = wire["deadline"]
    output = Path(plan["output_root"])
    require(not output.exists() and not output.is_symlink(), "fresh-output-before-read")
    _consume(plan, wire["held"], expiry, deadline)
    raw = _read_container(plan, expiry, deadline, wire["case"] if wire["fixture"] else None)
    if wire["fixture"] and wire["case"] == "parse-stall":
        time.sleep(30)
    decoded = _decode_stderr(raw, plan)
    view = {
        "escaped_ascii": escape_ascii(decoded),
        "decoded_bytes": len(decoded),
        "decoded_sha256": digest(decoded),
        "untrusted_data": True,
    }
    _input_context(plan, expiry, deadline)
    _worker_gate(wire)
    previous._live(expiry, deadline)
    parent = core._directory(str(output.parent))
    try:
        require(previous._parent_identity(parent) == plan["parent_identity"], "allocation-parent")
        os.mkdir(output.name, 0o700, dir_fd=parent)
        previous._live(expiry, deadline)
        os.fsync(parent)
        directory = os.open(
            output.name, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=parent
        )
    finally:
        os.close(parent)
    try:
        _namespace(directory, plan)
        receipt = {
            "schema": SCHEMA,
            "kind": "invented" if wire["fixture"] else "error-review-receipt",
            "status": "prepared",
            "pins": wire["held"],
            "input_bytes": len(raw),
            "input_sha256": digest(raw),
            "input_passes": 1,
            "decoded_bytes": len(decoded),
            "decoded_sha256": digest(decoded),
            "escape_encoding": "printable-ASCII-backslash-or-lowercase-hex-v1",
            "material_view_prepared": True,
            "downstream_display_confirmed": False,
            "new_local_material_file_written": False,
            "metadata_receipt_readback_passes": 0,
            "ended_utc": core._stamp(core._now()),
            "authority": dict(AUTHORITY),
            "retention": plan["retention"],
        }
        result = {"review": view, "review_receipt": receipt}
        validate_review_result(
            result,
            plan,
            wire["held"],
            core._utc(decode(base64.b64decode(wire["approval"]))["issued_utc"]),
            expiry,
            wire["fixture"],
        )
        _write_receipt(
            directory, encode(receipt), expiry, deadline, wire["case"] if wire["fixture"] else None
        )
        _input_context(plan, expiry, deadline)
        _namespace(directory, plan)
        _worker_gate(wire)
        if wire["fixture"] and wire["case"] == "emit-stall":
            time.sleep(30)
        previous._live(expiry, deadline)
        _emit(result)
    finally:
        os.close(directory)


def _entry():
    try:
        raw = sys.stdin.buffer.read(131073)
        require(len(raw) <= 131072, "worker-metadata-wire-cap")
        wire = decode(raw)
        fields(wire, "plan approval origin held fixture case deadline", "fixed-worker-fields")
        require(
            type(wire["fixture"]) is bool
            and (wire["case"] in CASES if wire["fixture"] else wire["case"] is None),
            "fixed-worker-mode",
        )
        if wire["fixture"]:
            forbidden = decode(os.environ.get("OT062_FIXTURE_FORBIDDEN_PATHS", "[]").encode())

            def deny(event, args):
                if event in ("socket.connect", "socket.getaddrinfo"):
                    raise PermissionError("fixture-network-denied")
                if (
                    event == "open"
                    and args
                    and isinstance(args[0], (str, bytes))
                    and os.fsdecode(args[0]) in forbidden
                ):
                    raise PermissionError("actual-material-denied")

            sys.addaudithook(deny)
            if wire["case"] == "overflow-frame":
                sys.stdout.buffer.write(b"x" * 20000)
                sys.stdout.buffer.flush()
                return
            if wire["case"] == "drip-frame":
                for _ in range(200):
                    sys.stdout.buffer.write(b"x")
                    sys.stdout.buffer.flush()
                    time.sleep(0.05)
                return
            if wire["case"] == "descendant":
                subprocess.Popen(
                    [sys.executable, "-I", "-S", "-B", "-c", "import time;time.sleep(30)"]
                )
        with fixture_time.use(wire["fixture"]):
            _produce(wire)
        if wire["fixture"] and wire["case"] == "late-error":
            _emit({"error": "invented-late-protocol-error"})
        if wire["fixture"] and wire["case"] == "nonzero":
            raise SystemExit(7)
    except (OSError, ValueError, RuntimeError):
        _emit({"error": "error-review-worker-rejected"})


def _supervise(wire, deadline):
    environment = core._environment()
    if wire["fixture"] and "OT062_FIXTURE_FORBIDDEN_PATHS" in os.environ:
        environment["OT062_FIXTURE_FORBIDDEN_PATHS"] = os.environ["OT062_FIXTURE_FORBIDDEN_PATHS"]
    script = (
        "import sys;sys.path.insert(0,"
        + repr(str(ROOT))
        + ");from experiments.simglucose_audit.gh_error_review import _entry;_entry()"
    )
    events = queue.Queue(maxsize=3)
    writers = []
    reader = writer = None
    result = None
    clean = False
    process = platform_process.spawn(
        [sys.executable, "-I", "-S", "-B", "-c", script],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        cwd=ROOT,
        env=environment,
    )
    try:
        reader = threading.Thread(target=_read_frames, args=(process.stdout, events), daemon=True)
        writer = threading.Thread(
            target=previous._send, args=(process.stdin, encode(wire), writers), daemon=True
        )
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
            if (
                kind == "frame"
                and type(frame) is dict
                and set(frame) == {"review", "review_receipt"}
            ):
                require(result is None, "one-private-result-only")
                result = frame
            else:
                result = None
                break
    finally:
        forced = previous._stop(process, reader, writer, True, deadline)
    return None if forced or not clean else result


@fixture_time.selected(4)
def _execute(plan_raw, approval_raw, origin_raw, held, fixture=False, case=None, whole_seconds=10):
    start = time.monotonic()
    deadline = start + whole_seconds
    plan, expiry = _gate(plan_raw, approval_raw, origin_raw, held, fixture, True)
    output = Path(plan["output_root"])
    require(not output.exists() and not output.is_symlink(), "absent-output-before-worker")
    previous._live(expiry, deadline)
    wire = {
        key: base64.b64encode(raw).decode()
        for key, raw in (("plan", plan_raw), ("approval", approval_raw), ("origin", origin_raw))
    }
    wire.update(
        held=held, fixture=fixture, case=case, deadline=deadline - min(3, whole_seconds / 3)
    )
    result = _supervise(wire, deadline)
    previous._live(expiry, deadline)
    _gate(plan_raw, approval_raw, origin_raw, held, fixture)
    require(result is not None, "owned-worker-incomplete-no-view")
    validate_review_result(
        result, plan, held, core._utc(decode(approval_raw)["issued_utc"]), expiry, fixture
    )
    previous._live(expiry, deadline)
    return result


@fixture_time.actual
def review_approved(plan_raw, approval_raw, origin_raw, held):
    """Trusted fixed caller only; returns one explicitly material private view."""
    return _execute(plan_raw, approval_raw, origin_raw, held)


def _fixture_key(inputs):
    require(
        type(inputs) is tuple
        and len(inputs) == 4
        and all(type(raw) is bytes for raw in inputs[:3])
        and type(inputs[3]) is dict,
        "minted-fixture-tuple",
    )
    return digest(
        b"".join(len(raw).to_bytes(4, "big") + raw for raw in (*inputs[:3], encode(inputs[3])))
    )


@fixture_time.invented
def fixture_inputs(parent, stderr=b"INVENTED diagnostic only.\n", *, mutate_report=None):
    """Mint only new owned synthetic bytes, with no filesystem input selector."""
    require(type(stderr) is bytes and 0 < len(stderr) <= STDERR_CAP, "invented-stderr-cap")
    parent = Path(parent)
    directory = core._directory(str(parent))
    try:
        with os.scandir(directory) as entries:
            require(next(entries, None) is None, "fresh-empty-owned-fixture-parent")
        parent_identity = previous._parent_identity(directory)
        row = {
            "role": "version",
            "status": "rejected",
            "exit_code": 2,
            "error": None,
            "consumed_application_bytes": {"stdout": 0, "stderr": len(stderr)},
            "stored_bytes": {"stdout": 0, "stderr": len(stderr)},
            "stored_sha256": {"stdout": digest(b""), "stderr": digest(stderr)},
            "parsed": {"version_matches": False, "observed_help_markers": []},
            "real_selected_tool_invocation": True,
            "real_crypto_or_artifact_verification": False,
        }
        pins = {"invented_context_sha256": digest(b"INVENTED old observation")}
        observation = {
            "bytes": 31,
            "sha256": digest(b"INVENTED nonexecutable"),
            "body_passes": 1,
            "OS_exec_mapping_library_IO_included": False,
        }
        report = {
            "schema": PRODUCER_SCHEMA,
            "kind": "private-startup-output-report",
            "pins": pins,
            "binary_hash_observation": observation,
            "probes": [
                row | {"raw_base64": {"stdout": "", "stderr": base64.b64encode(stderr).decode()}}
            ],
            "fixture_only": False,
            "authentication_or_runtime_admission": False,
        }
        # Mutation is fixed invented-scenario data, never a callback or code argument.
        require(
            mutate_report
            in (
                None,
                "extra-field",
                "extra-row",
                "stdout",
                "wrong-b64",
                "wrong-kind",
                "duplicate",
                "trailing",
                "wrong-row",
                "fixture-kind",
                "noncanonical-b64",
                "numeric-type",
                "utf16",
            ),
            "fixed-mutation-enum",
        )
        if mutate_report == "extra-field":
            report["extra"] = "INVENTED"
        if mutate_report == "extra-row":
            report["probes"] *= 2
        if mutate_report == "stdout":
            report["probes"][0]["raw_base64"]["stdout"] = "eA=="
        if mutate_report == "wrong-b64":
            report["probes"][0]["raw_base64"]["stderr"] = "!"
        if mutate_report == "noncanonical-b64":
            report["probes"][0]["raw_base64"]["stderr"] += "\n"
        if mutate_report == "wrong-kind":
            report["kind"] = "INVENTED other body"
        if mutate_report == "wrong-row":
            report["probes"][0]["exit_code"] = 1
        if mutate_report == "fixture-kind":
            report["fixture_only"] = True
        if mutate_report == "numeric-type":
            report["binary_hash_observation"] = observation | {"bytes": 31.0}
        raw = encode(report)
        if mutate_report == "utf16":
            raw = raw.decode().encode("utf-16")
        if mutate_report == "duplicate":
            raw = raw[:-1] + b',"schema":"duplicate"}'
        if mutate_report == "trailing":
            raw += b"{}"
        previous._write_checked(
            directory,
            "invented-container.json",
            raw,
            core._now() + timedelta(seconds=20),
            time.monotonic() + 10,
        )
    finally:
        os.close(directory)
    producer = {
        "schema": PRODUCER_SCHEMA,
        "kind": "startup-probe-receipt",
        "status": "rejected",
        "pins": pins,
        "binary_hash_observation": observation,
        "probes": [row],
        "report_sha256": digest(raw),
        "report_bytes": len(raw),
        "report_readback_passes": 0,
        "raw_outputs_in_receipt": False,
    }
    # Preserve the independent old metadata when the invented report row was mutated.
    if mutate_report == "wrong-row":
        producer["probes"][0] = row | {"exit_code": 2}
    source = parent / "invented-container.json"
    now = core._now()
    end = now + timedelta(days=1)
    retention = {
        "max_days_new_facts": 30,
        "not_after_UTC": core._stamp(end),
        "earlier_limits_win": True,
        "old_origins_reset": False,
        "unknown_older_origins_timely_claimed": False,
        "automatic_cleanup_or_extension": False,
    }
    origin = {
        "schema": SCHEMA,
        "kind": "invented",
        "recorded_new_fact_utc": core._stamp(now),
        "not_after_UTC": core._stamp(end),
        "retention": retention,
        "old_origins_reset": False,
        "unknown_older_origins_timely_claimed": False,
        "evidence_sha256": digest(b"INVENTED fresh review proposal"),
    }
    origin_raw = encode(origin)
    reader_source, owner = _identity(), _owner()
    plan = {
        "schema": SCHEMA,
        "kind": "invented",
        "input": {
            "path": str(source),
            "bytes": len(raw),
            "sha256": digest(raw),
            "token": previous._token(source.lstat()),
            "parent_identity": parent_identity,
        },
        "producer_receipt": producer,
        "expected_stderr": {"bytes": len(stderr), "sha256": digest(stderr)},
        "reader_source": reader_source,
        "owner": owner,
        "rights_basis_sha256": digest(b"INVENTED review-only rights"),
        "qualification_sha256": digest(b"INVENTED fixtures only"),
        "origin_sha256": digest(origin_raw),
        "output_root": str(parent / "invented-error-review"),
        "parent_identity": parent_identity,
        "retention": retention,
    }
    plan["limits"] = _limits(plan)
    plan_raw = encode(plan)
    held = {
        "plan_sha256": digest(plan_raw),
        "origin_sha256": digest(origin_raw),
        "source_sha256": digest(encode(reader_source)),
        "owner_sha256": digest(encode(owner)),
        "rights_basis_sha256": plan["rights_basis_sha256"],
        "producer_receipt_sha256": digest(encode(producer)),
        "output_root": plan["output_root"],
    }
    approval = {
        "schema": SCHEMA,
        "kind": "invented",
        **{
            k: held[k]
            for k in (
                "plan_sha256",
                "origin_sha256",
                "source_sha256",
                "owner_sha256",
                "rights_basis_sha256",
                "producer_receipt_sha256",
            )
        },
        "nonce": "3" * 32,
        "issued_utc": core._stamp(now),
        "expires_utc": core._stamp(now + timedelta(minutes=30)),
        "scope": "one-retained-startup-report-read-and-one-escaped-stderr-view",
        "authority": dict(AUTHORITY),
    }
    approval_raw = encode(approval)
    held["approval_sha256"] = digest(approval_raw)
    inputs = (plan_raw, approval_raw, origin_raw, held)
    _FIXTURES.add(_fixture_key(inputs))
    return inputs


@fixture_time.invented
def run_fixture_review(inputs, case="ok", *, whole_seconds=10):
    require(_fixture_key(inputs) in _FIXTURES and case in CASES, "minted-fixed-fixture")
    require(type(whole_seconds) in (int, float) and 0 < whole_seconds <= 10, "bounded-fixture-time")
    return _execute(*inputs, True, case, whole_seconds)


@fixture_time.selected(4)
def inspect_receipt_metadata(
    plan_raw, approval_raw, origin_raw, held, *, held_receipt_sha256, fixture=False
):
    _held_documents(plan_raw, approval_raw, origin_raw, held)
    issued = core._utc(decode(approval_raw)["issued_utc"])
    plan, expiry = _gate(plan_raw, approval_raw, origin_raw, held, fixture, historical_at=issued)
    retained = min(
        previous._retention(plan["retention"]), core._utc(decode(origin_raw)["not_after_UTC"])
    )
    deadline = time.monotonic() + 10
    directory = core._directory(plan["output_root"])
    try:
        _namespace(directory, plan)
        raw = previous._load_file(
            directory, "receipt.private.json", RECEIPT_CAP, retained, deadline
        )
        require(digest(raw) == held_receipt_sha256, "held-metadata-receipt")
        receipt = decode(raw)
        _validate_receipt(receipt, plan, held, issued, expiry, fixture)
        _namespace(directory, plan)
        _gate(plan_raw, approval_raw, origin_raw, held, fixture, historical_at=issued)
        return receipt
    finally:
        os.close(directory)


def _read_frames(stream, events):
    try:
        previous._frames(stream, events, ENVELOPE_CAP)
    finally:
        stream.close()
