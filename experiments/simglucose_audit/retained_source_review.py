"""Qualified structure for two retained-source/report-review substeps.

Ordinary entry is closed. Actual private paths, hashes, sizes, tokens and grant
origins are externally held PRIVATE plan data, never hardcoded here. No Go,
verifier, network or native activation. A returns metadata only; B is explicitly
notice-bearing material access, not cold metadata.
"""

import base64
import codecs
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
from .contract import AUTHORITY, SOURCE_FILES, decode, digest, encode, fields, require

ROOT = Path(__file__).resolve().parents[2]
SCHEMA = "opent1d.retained-source-review/1"
ROLES = ("go.mod", "LICENSE")
ROLE_CAPS = (16384, 4096)
FRAME_LIMIT = 8
_FIXTURE_PROVENANCE = set()
REPORT_CAP = 131072
RECEIPT_CAP = 65536
B_RECEIPT_CAP = 16384
ENVELOPE_CAP = 196608
BASE_LIMITS = {
    "source_whole_seconds": 60,
    "report_review_whole_seconds": 10,
    "source_start_headroom_seconds": 80,
    "review_start_headroom_seconds": 20,
    "report_bytes": REPORT_CAP,
    "receipt_bytes": RECEIPT_CAP,
    "report_review_read_bytes": REPORT_CAP + 1,
    "B_review_receipt_bytes": B_RECEIPT_CAP,
    "B_material_envelope_bytes": ENVELOPE_CAP,
    "source_passes_each": 1,
    "report_review_passes": 1,
    "root_files": 2,
    "root_bytes": 196608,
    "parent_markers_each_bytes": 128,
    "parent_outer_observations_each_bytes": 16384,
    "combined_action_output_bytes": 229632,
}
COVERAGE = (
    "retained-input-identities",
    "reader-source",
    "new-source-read-and-report-copy-basis",
    "proof-allocation",
)
CASES = (
    "ok",
    "source-stall",
    "read-stall",
    "write-stall",
    "fsync-stall",
    "finalize-stall",
    "B-read-stall",
    "B-emit-stall",
)
FIXTURE_NOTICE = 'INVENTED notice only. "Quoted" café\r\nNo real rights or material.\n'


def run_review(*_args, **_kwargs):
    raise PermissionError("retained source/report access closed without exact new approval")


def _retention(value):
    fields(
        value,
        (
            "max_days_new_facts not_after_UTC earlier_limits_win old_orig"
            "ins_reset unknown_older_origins_timely_claimed automatic_cle"
            "anup_or_extension"
        ),
        "retention-fields",
    )
    require(
        type(value["max_days_new_facts"]) is int
        and 0 < value["max_days_new_facts"] <= 30
        and value["earlier_limits_win"] is True
        and value["old_origins_reset"] is False
        and value["unknown_older_origins_timely_claimed"] is False
        and value["automatic_cleanup_or_extension"] is False,
        "retention-policy",
    )
    return core._utc(value["not_after_UTC"])


def _path(value):
    require(
        type(value) is str
        and len(value) <= 4096
        and Path(value).is_absolute()
        and str(Path(value)) == value
        and ".." not in Path(value).parts,
        "canonical-private-path",
    )
    return Path(value)


def _token(info):
    return [
        info.st_dev,
        info.st_ino,
        info.st_uid,
        stat.S_IMODE(info.st_mode),
        info.st_nlink,
        info.st_size,
        info.st_mtime_ns,
        info.st_ctime_ns,
        getattr(info, "st_flags", 0),
    ]


def _limits(targets):
    return BASE_LIMITS | {
        "source_application_read_bytes": sum(t["expected_bytes"] + 1 for t in targets),
        "combined_application_read_bytes": sum(t["expected_bytes"] + 1 for t in targets)
        + REPORT_CAP
        + 1,
    }


@fixture_time.selected(4)
def _gate(
    plan_raw,
    approval_raw,
    origin_raw,
    held,
    fixture=False,
    headroom=False,
    substep="A",
    historical_at=None,
):
    require(type(fixture) is bool and substep in ("A", "B"), "fixed-substep")
    fields(
        held,
        (
            "plan_sha256 approval_sha256 origin_sha256 source_sha256 owne"
            "r_sha256 rights_basis_sha256 output_root"
        ),
        "external-held-fields",
    )
    for name, raw in (("plan", plan_raw), ("approval", approval_raw), ("origin", origin_raw)):
        require(
            type(raw) is bytes and 0 < len(raw) <= 32768 and digest(raw) == held[name + "_sha256"],
            "held-document",
        )
    plan, approval, origin = map(decode, (plan_raw, approval_raw, origin_raw))
    fields(
        plan,
        (
            "schema kind targets input_context limits retention source ow"
            "ner rights_basis_sha256 qualification_sha256 output_root par"
            "ent_identity origin_sha256"
        ),
        "plan-fields",
    )
    require(
        plan["schema"] == SCHEMA
        and plan["kind"] == ("invented" if fixture else "private-retained-review-plan"),
        "plan-kind",
    )
    fields(
        plan["input_context"], "root_path root_token objects_path objects_token", "input-context"
    )
    context = plan["input_context"]
    root = _path(context["root_path"])
    objects = _path(context["objects_path"])
    require(objects.parent == root and objects.name == "objects", "fixed-objects-context")
    for key in ("root_token", "objects_token"):
        require(
            type(context[key]) is list
            and len(context[key]) == 9
            and all(type(x) is int for x in context[key]),
            "directory-context-token",
        )
        require(
            context[key][2] == os.getuid() and context[key][3] == 0o700, "private-input-directory"
        )
    require(type(plan["targets"]) is list and len(plan["targets"]) == 2, "two-targets")
    for target, role, cap in zip(plan["targets"], ROLES, ROLE_CAPS, strict=True):
        fields(target, "role path expected_bytes expected_sha256 token", "target-fields")
        require(
            target["role"] == role
            and _path(target["path"]) == objects / role
            and type(target["expected_bytes"]) is int
            and 0 < target["expected_bytes"] <= cap
            and type(target["expected_sha256"]) is str
            and core.HEX.fullmatch(target["expected_sha256"]),
            "fixed-typed-target",
        )
        t = target["token"]
        require(
            type(t) is list
            and len(t) == 9
            and all(type(x) is int for x in t)
            and t[2] == os.getuid()
            and t[3] == 0o600
            and t[4] == 1
            and t[5] == target["expected_bytes"],
            "target-private-token",
        )
    require(
        encode(plan["limits"]) == encode(_limits(plan["targets"]))
        and plan["origin_sha256"] == held["origin_sha256"],
        "exact-limits-origin",
    )
    output = _path(plan["output_root"])
    require(
        str(output) == held["output_root"]
        and output.name
        == ("invented-retained-review" if fixture else "proposed-retained-source-review"),
        "held-output-root",
    )
    require(
        output != root and root not in output.parents and output not in root.parents,
        "separate-input-output",
    )
    if fixture:
        require(
            root.name == "invented-input" and root.parent == output.parent,
            "owned-invented-fixture-layout",
        )
    fields(plan["parent_identity"], "dev ino uid mode", "parent-identity")
    require(
        all(type(v) is int for v in plan["parent_identity"].values())
        and plan["parent_identity"]["uid"] == os.getuid()
        and plan["parent_identity"]["mode"] == 0o700,
        "private-output-parent",
    )
    for key in ("rights_basis_sha256", "qualification_sha256"):
        require(type(plan[key]) is str and core.HEX.fullmatch(plan[key]), "required-policy-pin")
    require(plan["rights_basis_sha256"] == held["rights_basis_sha256"], "held-rights")
    now = core._now() if historical_at is None else historical_at
    private_end = _retention(plan["retention"])
    fields(
        origin,
        (
            "schema kind records retention origin_scope origins_verified "
            "unknown_required_origins does_not_reset_referenced_material_"
            "origins unknown_referenced_origins_timely_claimed"
        ),
        "origin-fields",
    )
    require(
        origin["schema"] == SCHEMA
        and origin["kind"] == ("invented" if fixture else "private-origin-context")
        and encode(origin["retention"]) == encode(plan["retention"])
        and origin["origin_scope"] == "new-observation-or-proposal-fact"
        and origin["origins_verified"] is True
        and origin["unknown_required_origins"] == []
        and origin["does_not_reset_referenced_material_origins"] is True
        and origin["unknown_referenced_origins_timely_claimed"] is False
        and type(origin["records"]) is list
        and len(origin["records"]) == 4,
        "origin-scope",
    )
    deadlines = [private_end]
    for row, subject in zip(origin["records"], COVERAGE, strict=True):
        fields(row, "subject origin_utc deadline_utc evidence_sha256 basis", "origin-row")
        start, end = core._utc(row["origin_utc"]), core._utc(row["deadline_utc"])
        require(
            row["subject"] == subject
            and row["basis"] == "new-technical-fact-evidence"
            and type(row["evidence_sha256"]) is str
            and core.HEX.fullmatch(row["evidence_sha256"])
            and start
            <= now
            < end
            <= start + timedelta(days=plan["retention"]["max_days_new_facts"]),
            "origin-window",
        )
        deadlines.append(end)
    fields(
        approval,
        (
            "schema kind plan_sha256 origin_sha256 rights_basis_sha256 so"
            "urce_sha256 owner_sha256 nonce issued_utc expires_utc scope "
            "authority"
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
                "rights_basis_sha256",
                "source_sha256",
                "owner_sha256",
            )
        )
        and type(approval["nonce"]) is str
        and re.fullmatch(r"[0-9a-f]{32}", approval["nonce"])
        and approval["scope"] == "one-retained-two-source-pass-and-one-notice-report-review"
        and encode(approval["authority"]) == encode(AUTHORITY),
        "same-exact-two-substep-approval",
    )
    issued, expires = core._utc(approval["issued_utc"]), core._utc(approval["expires_utc"])
    expiry = min(expires, *deadlines)
    require(
        issued <= now < expires <= issued + timedelta(hours=1)
        and now < expiry
        and (not headroom or (expiry - now).total_seconds() >= (80 if substep == "A" else 20)),
        "current-earliest-headroom",
    )
    read_expiry = expiry if historical_at is None else min(deadlines)
    require(core._now() < read_expiry, "current-private-retention")
    require(
        plan["source"] == _identity(read_expiry)
        and plan["owner"] == _owner(read_expiry)
        and digest(encode(plan["source"])) == held["source_sha256"]
        and digest(encode(plan["owner"])) == held["owner_sha256"],
        "current-source-owner",
    )
    require(core._now() < read_expiry, "source-finish-window")
    return plan, expiry


def _source_hash(path, expiry=None):
    if expiry is not None:
        require(core._now() < expiry, "source-read-before-expiry")
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    try:
        before = os.fstat(fd)
        named_before = Path(path).lstat()
        require(core._fingerprint(before) == core._fingerprint(named_before), "source-before-name")
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
            and core._fingerprint(before)
            == core._fingerprint(os.fstat(fd))
            == core._fingerprint(Path(path).lstat())
            and (expiry is None or core._now() < expiry),
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
        "retained_source_review.py": _source_hash(Path(__file__), expiry),
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


def _frames(stream, events, maximum=196608):
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
        except (OSError, RuntimeError, ValueError, subprocess.TimeoutExpired):
            errors.append("owned-tree-stop-error")
        try:
            require(not platform_process.tree_exists(process), "owned-tree-stop")
        except (OSError, RuntimeError, ValueError):
            errors.append("owned-tree-unconfirmed")
        try:
            platform_process.close_tree(process)
        except (OSError, RuntimeError, ValueError):
            errors.append("owned-close-error")
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
        require(
            set(os.listdir(directory)) <= {"report.private.json", "receipt.private.json"},
            "fixed-output-membership",
        )
    finally:
        os.close(parent)


def _supervise(wire, deadline):
    environment = core._environment()
    if wire["fixture"] and "OT062_FIXTURE_FORBIDDEN_PATHS" in os.environ:
        environment["OT062_FIXTURE_FORBIDDEN_PATHS"] = os.environ["OT062_FIXTURE_FORBIDDEN_PATHS"]
    process = platform_process.spawn(
        [sys.executable, "-I", "-S", "-B", "-c", _script("_entry;_entry()")],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        cwd=ROOT,
        env=environment,
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
        + ");from experiments.simglucose_audit.retained_source_review import "
        + call
    )


def _input_directories(plan, expiry, deadline):
    _live(expiry, deadline)
    context = plan["input_context"]
    root = core._directory(context["root_path"])
    objects = None
    try:
        require(_token(os.fstat(root)) == context["root_token"], "input-root-token")
        _live(expiry, deadline)
        objects = os.open("objects", os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=root)
        core._private_directory(objects)
        require(
            _token(os.fstat(objects)) == context["objects_token"]
            and _token(os.stat("objects", dir_fd=root, follow_symlinks=False))
            == context["objects_token"],
            "objects-token",
        )
        require(
            _token(Path(context["root_path"]).lstat()) == context["root_token"], "named-input-root"
        )
        return root, objects
    except BaseException:
        if objects is not None:
            os.close(objects)
        os.close(root)
        raise


def _check_inputs(plan, expiry, deadline):
    root, objects = _input_directories(plan, expiry, deadline)
    try:
        for target in plan["targets"]:
            _live(expiry, deadline)
            named = os.stat(target["role"], dir_fd=objects, follow_symlinks=False)
            require(
                stat.S_ISREG(named.st_mode) and _token(named) == target["token"],
                "named-source-token",
            )
    finally:
        os.close(objects)
        os.close(root)


def _read_source(plan, target, expiry, deadline, case=None):
    root, objects = _input_directories(plan, expiry, deadline)
    fd = None
    try:
        _live(expiry, deadline)
        fd = os.open(target["role"], os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=objects)
        before = os.fstat(fd)
        core._regular(fd)
        require(
            _token(before) == target["token"]
            and _token(os.stat(target["role"], dir_fd=objects, follow_symlinks=False))
            == target["token"],
            "source-before-token",
        )
        if case == "source-stall":
            time.sleep(30)
        count = 0
        hasher = hashlib.sha256()
        chunks = []
        decoder = codecs.getincrementaldecoder("utf-8")("strict")
        while count < target["expected_bytes"] + 1:
            _live(expiry, deadline)
            if case == "read-stall":
                time.sleep(30)
            raw = os.read(fd, min(4096, target["expected_bytes"] + 1 - count))
            if not raw:
                break
            count += len(raw)
            require(
                count <= target["expected_bytes"] and b"\0" not in raw, "source-byte-cap-or-NUL"
            )
            hasher.update(raw)
            chunks.append(decoder.decode(raw, final=False))
        chunks.append(decoder.decode(b"", final=True))
        _live(expiry, deadline)
        require(
            count == target["expected_bytes"] and hasher.hexdigest() == target["expected_sha256"],
            "source-size-hash",
        )
        require(
            _token(os.fstat(fd)) == target["token"]
            and _token(os.stat(target["role"], dir_fd=objects, follow_symlinks=False))
            == target["token"],
            "source-after-token",
        )
        text = "".join(chunks)
        return text, {
            "role": target["role"],
            "bytes": count,
            "sha256": hasher.hexdigest(),
            "source_passes": 1,
            "UTF8_nonNUL": True,
            "LF_count": text.count("\n"),
        }
    finally:
        if fd is not None:
            os.close(fd)
        os.close(objects)
        os.close(root)


def _parse_mod(text):
    result = {
        "module": None,
        "go": None,
        "toolchain": None,
        "require_labels": [],
        "unknown_directives": [],
        "problems": [],
        "line_count": 0,
        "blank_or_comment_lines": 0,
        "require_blocks": 0,
        "labels_truncated": False,
        "complete_supported_lexical_context": False,
        "Go_semantics_dependency_build_API_closure_verified": False,
        "raw_go_mod_or_unparsed_line_text_returned": False,
    }
    headers = set()
    block = None
    block_line = None
    for number, raw in enumerate(text.splitlines(), 1):
        result["line_count"] = number
        if len(raw.encode()) > 4096:
            result["problems"].append({"line": number, "kind": "oversized-line"})
            continue
        line = raw.split("//", 1)[0].strip()
        if not line:
            result["blank_or_comment_lines"] += 1
            continue
        words = line.split()
        first = words[0]
        if line == ")":
            if block is None:
                result["problems"].append({"line": number, "kind": "unmatched-block-close"})
            block = None
            block_line = None
            continue
        if block == "unsupported":
            result["problems"].append({"line": number, "kind": "unsupported-block-content"})
            continue
        if first in ("module", "go", "toolchain") and block is None:
            if first in headers:
                result[first] = None
                result["problems"].append({"line": number, "kind": "duplicate-header"})
            elif len(words) == 2 and re.fullmatch(r"[A-Za-z0-9._~+/-]{1,256}", words[1]):
                result[first] = words[1]
            else:
                result["problems"].append({"line": number, "kind": "unsupported-header-syntax"})
            headers.add(first)
            continue
        if line == "require (" and block is None:
            block = "require"
            block_line = number
            result["require_blocks"] += 1
            continue
        candidate = words if block == "require" else words[1:] if first == "require" else None
        if candidate is not None:
            if (
                len(candidate) == 2
                and re.fullmatch(r"[A-Za-z0-9._~+/-]{1,256}", candidate[0])
                and re.fullmatch(r"[A-Za-z0-9.+_-]{1,128}", candidate[1])
            ):
                result["require_labels"].append(
                    {"line": number, "module": candidate[0], "version": candidate[1]}
                )
            else:
                result["problems"].append({"line": number, "kind": "unsupported-require-syntax"})
            continue
        label = first if re.fullmatch(r"[A-Za-z][A-Za-z0-9_-]{0,31}", first) else None
        result["unknown_directives"].append({"line": number, "directive": label})
        if line.endswith("("):
            block = "unsupported"
            block_line = number
    if block is not None:
        result["problems"].append({"line": block_line, "kind": "unclosed-block"})
    if "module" not in headers:
        result["problems"].append({"line": 0, "kind": "missing-module-header"})
    if any(char in text for char in ("\v", "\f", "\x85", "\u2028", "\u2029")):
        result["problems"].append({"line": 0, "kind": "unsupported-newline-form"})
    result["require_candidate_count"] = len(result["require_labels"])
    result["complete_supported_lexical_context"] = not (
        result["problems"] or result["unknown_directives"]
    )
    return result


def _inputs(wire, substep=None, headroom=False):
    return _gate(
        *(base64.b64decode(wire[k], validate=True) for k in ("plan", "approval", "origin")),
        wire["held"],
        wire["fixture"],
        headroom,
        substep or wire["substep"],
    )


def _consume(plan, wire, expiry, deadline, substep):
    parent = core._directory(str(Path(plan["output_root"]).parent))
    try:
        require(_parent_identity(parent) == plan["parent_identity"], "current-output-parent")
        _live(expiry, deadline)
        raw = encode({"approval_sha256": wire["held"]["approval_sha256"], "substep": substep})
        require(len(raw) <= 128, "marker-cap")
        _write_checked(
            parent,
            ".retained-review-" + substep + "-" + wire["held"]["approval_sha256"],
            raw,
            expiry,
            deadline,
        )
    finally:
        os.close(parent)


def _write_report(directory, raw, expiry, deadline, case):
    require(len(raw) <= REPORT_CAP, "report-output-cap")
    _live(expiry, deadline)
    fd = os.open(
        "report.private.json",
        os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
        0o600,
        dir_fd=directory,
    )
    try:
        core._regular(fd)
        count = 0
        hasher = hashlib.sha256()
        while count < len(raw):
            _live(expiry, deadline)
            if case == "write-stall":
                time.sleep(30)
            part = raw[count : count + 65536]
            n = os.write(fd, part)
            require(0 < n <= len(part), "report-write-progress")
            hasher.update(part[:n])
            count += n
        if case == "fsync-stall":
            time.sleep(30)
        _live(expiry, deadline)
        os.fsync(fd)
        _live(expiry, deadline)
        core._regular(fd)
        require(
            core._fingerprint(os.fstat(fd))
            == core._fingerprint(
                os.stat("report.private.json", dir_fd=directory, follow_symlinks=False)
            ),
            "report-write-name-binding",
        )
        return count, hasher.hexdigest(), _token(os.fstat(fd))
    finally:
        os.close(fd)


def _report(plan, wire, rows, go, notice):
    return {
        "schema": SCHEMA,
        "kind": "notice-bearing-static-review-report",
        "bindings": {
            k: wire["held"][k]
            for k in (
                "plan_sha256",
                "approval_sha256",
                "origin_sha256",
                "source_sha256",
                "owner_sha256",
                "rights_basis_sha256",
            )
        },
        "source_observations": rows,
        "go_mod_context": _parse_mod(go),
        "notice": {
            "role": "LICENSE",
            "bytes": len(notice.encode()),
            "sha256": digest(notice.encode()),
            "full_literal_text": notice,
        },
        "claims": {
            "notice_bearing_material_copy": True,
            "Go_evaluated_or_resolved": False,
            "full_license_title_or_runtime_rights_cleared": False,
            "publisher_or_tag_tree_authenticated": False,
            "actual_crypto_or_native_admission": False,
        },
        "retention": plan["retention"],
    }


def _produce_A(wire):
    plan, expiry = _inputs(wire, headroom=True)
    deadline = wire["deadline"]
    _consume(plan, wire, expiry, deadline, "A")
    _check_inputs(plan, expiry, deadline)
    texts = []
    rows = []
    for target in plan["targets"]:
        text, row = _read_source(
            plan, target, expiry, deadline, wire["case"] if wire["fixture"] else None
        )
        texts.append(text)
        rows.append(row)
    _check_inputs(plan, expiry, deadline)
    _inputs(wire)
    report = _report(plan, wire, rows, *texts)
    raw = encode(report)
    require(len(raw) <= REPORT_CAP, "report-output-cap")
    # Only verified exact source text may enter a notice-bearing output.
    _live(expiry, deadline)
    parent = core._directory(str(Path(plan["output_root"]).parent))
    try:
        require(_parent_identity(parent) == plan["parent_identity"], "output-parent-before-create")
        os.mkdir(Path(plan["output_root"]).name, 0o700, dir_fd=parent)
        _live(expiry, deadline)
        os.fsync(parent)
        _live(expiry, deadline)
        directory = os.open(
            Path(plan["output_root"]).name,
            os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW,
            dir_fd=parent,
        )
        core._private_directory(directory)
    finally:
        os.close(parent)
    try:
        _namespace(directory, plan)
        count, sha, report_token = _write_report(directory, raw, expiry, deadline, wire["case"])
        _check_inputs(plan, expiry, deadline)
        _namespace(directory, plan)
        _inputs(wire)
        receipt = {
            "schema": SCHEMA,
            "kind": "invented" if wire["fixture"] else "retained-source-receipt",
            "substep": "A",
            "status": "completed",
            "pins": wire["held"],
            "source_rows": rows,
            "report_sha256": sha,
            "report_bytes": count,
            "report_token": report_token,
            "report_notice_bearing": True,
            "notice_body_in_receipt": False,
            "source_body_passes_each": 1,
            "report_readback_passes": 0,
            "output_identity": _parent_identity(directory),
            "ended_utc": core._stamp(core._now()),
            "authority": dict(AUTHORITY),
            "retention": plan["retention"],
        }
        if wire["fixture"] and wire["case"] == "finalize-stall":
            time.sleep(30)
        _live(expiry, deadline)
        encoded = encode(receipt)
        require(len(encoded) <= RECEIPT_CAP, "A-receipt-cap")
        _write_checked(directory, "receipt.private.json", encoded, expiry, deadline)
        _check_inputs(plan, expiry, deadline)
        _namespace(directory, plan)
        _inputs(wire)
        _live(expiry, deadline)
        _emit({"receipt": receipt})  # METADATA ONLY, never report/notice.
    finally:
        os.close(directory)


def _load_file(directory, name, cap, expiry, deadline, expected_token=None, case=None):
    _live(expiry, deadline)
    fd = os.open(name, os.O_RDONLY | os.O_NONBLOCK | os.O_NOFOLLOW, dir_fd=directory)
    try:
        before = os.fstat(fd)
        core._regular(fd)
        require(
            before.st_size <= cap and (expected_token is None or _token(before) == expected_token),
            "bounded-private-file",
        )
        require(
            core._fingerprint(before)
            == core._fingerprint(os.stat(name, dir_fd=directory, follow_symlinks=False)),
            "private-file-before-binding",
        )
        raw = bytearray()
        while len(raw) < cap + 1:
            _live(expiry, deadline)
            if case == "B-read-stall":
                time.sleep(30)
            chunk = os.read(fd, min(65536, cap + 1 - len(raw)))
            if not chunk:
                break
            raw += chunk
            require(len(raw) <= cap, "file-overflow-sentinel")
        _live(expiry, deadline)
        require(
            len(raw) == before.st_size
            and core._fingerprint(before)
            == core._fingerprint(os.fstat(fd))
            == core._fingerprint(os.stat(name, dir_fd=directory, follow_symlinks=False)),
            "private-file-after-binding",
        )
        return bytes(raw)
    finally:
        os.close(fd)


def _validate_A(receipt, plan, held, fixture, issued, expiry):
    fields(
        receipt,
        (
            "schema kind substep status pins source_rows report_sha256 re"
            "port_bytes report_token report_notice_bearing notice_body_in"
            "_receipt source_body_passes_each report_readback_passes outp"
            "ut_identity ended_utc authority retention"
        ),
        "A-receipt-fields",
    )
    require(
        receipt["schema"] == SCHEMA
        and receipt["kind"] == ("invented" if fixture else "retained-source-receipt")
        and receipt["substep"] == "A"
        and receipt["status"] == "completed"
        and receipt["pins"] == held
        and encode(receipt["authority"]) == encode(AUTHORITY)
        and encode(receipt["retention"]) == encode(plan["retention"])
        and receipt["report_notice_bearing"] is True
        and receipt["notice_body_in_receipt"] is False
        and type(receipt["source_body_passes_each"]) is int
        and receipt["source_body_passes_each"] == 1
        and type(receipt["report_readback_passes"]) is int
        and receipt["report_readback_passes"] == 0,
        "A-metadata-scope",
    )
    require(
        type(receipt["report_sha256"]) is str
        and core.HEX.fullmatch(receipt["report_sha256"])
        and type(receipt["report_bytes"]) is int
        and 0 < receipt["report_bytes"] <= REPORT_CAP,
        "report-identity-fields",
    )
    t = receipt["report_token"]
    require(
        type(t) is list
        and len(t) == 9
        and all(type(x) is int for x in t)
        and t[2] == os.getuid()
        and t[3] == 0o600
        and t[4] == 1
        and t[5] == receipt["report_bytes"],
        "A-report-token",
    )
    fields(receipt["output_identity"], "dev ino uid mode", "A-output-identity")
    require(
        all(type(x) is int for x in receipt["output_identity"].values())
        and receipt["output_identity"]["uid"] == os.getuid()
        and receipt["output_identity"]["mode"] == 0o700,
        "A-output-private",
    )
    require(
        type(receipt["source_rows"]) is list and len(receipt["source_rows"]) == 2,
        "two-source-observations",
    )
    for row, target in zip(receipt["source_rows"], plan["targets"], strict=True):
        fields(
            row, "role bytes sha256 source_passes UTF8_nonNUL LF_count", "source-observation-fields"
        )
        require(
            row["role"] == target["role"]
            and type(row["bytes"]) is int
            and row["bytes"] == target["expected_bytes"]
            and row["sha256"] == target["expected_sha256"]
            and type(row["source_passes"]) is int
            and row["source_passes"] == 1
            and row["UTF8_nonNUL"] is True
            and type(row["LF_count"]) is int
            and 0 <= row["LF_count"] <= row["bytes"],
            "exact-source-observation",
        )
    ended = core._utc(receipt["ended_utc"])
    require(issued <= ended < expiry and ended <= core._now(), "A-execution-window")


def _validate_report(report, raw, receipt, plan, held):
    fields(
        report,
        "schema kind bindings source_observations go_mod_context notice claims retention",
        "report-fields",
    )
    require(
        report["schema"] == SCHEMA
        and report["kind"] == "notice-bearing-static-review-report"
        and report["bindings"]
        == {
            k: held[k]
            for k in (
                "plan_sha256",
                "approval_sha256",
                "origin_sha256",
                "source_sha256",
                "owner_sha256",
                "rights_basis_sha256",
            )
        }
        and encode(report["source_observations"]) == encode(receipt["source_rows"])
        and encode(report["retention"]) == encode(plan["retention"])
        and encode(report) == raw,
        "report-bindings-canonical",
    )
    fields(report["notice"], "role bytes sha256 full_literal_text", "notice-fields")
    notice = report["notice"]
    target = plan["targets"][1]
    require(
        notice["role"] == "LICENSE"
        and type(notice["full_literal_text"]) is str
        and len(notice["full_literal_text"].encode()) == notice["bytes"] == target["expected_bytes"]
        and digest(notice["full_literal_text"].encode())
        == notice["sha256"]
        == target["expected_sha256"]
        and "\0" not in notice["full_literal_text"],
        "literal-notice-integrity",
    )
    require(
        encode(report["claims"])
        == encode(
            {
                "notice_bearing_material_copy": True,
                "Go_evaluated_or_resolved": False,
                "full_license_title_or_runtime_rights_cleared": False,
                "publisher_or_tag_tree_authenticated": False,
                "actual_crypto_or_native_admission": False,
            }
        ),
        "no-report-authority",
    )
    _validate_context(report["go_mod_context"], plan["targets"][0]["expected_bytes"])


def _produce_B(wire):
    plan, expiry = _inputs(wire, headroom=True)
    deadline = wire["deadline"]
    for key in ("held_producer_receipt_sha256", "held_report_sha256"):
        require(type(wire[key]) is str and core.HEX.fullmatch(wire[key]), "B-held-producer-pins")
    _consume(plan, wire, expiry, deadline, "B")
    _check_inputs(plan, expiry, deadline)  # metadata only, no original source reopen.
    directory = core._directory(plan["output_root"])
    try:
        _namespace(directory, plan)
        require(
            set(os.listdir(directory)) == {"report.private.json", "receipt.private.json"},
            "B-exact-output-membership",
        )
        receipt_raw = _load_file(directory, "receipt.private.json", RECEIPT_CAP, expiry, deadline)
        require(digest(receipt_raw) == wire["held_producer_receipt_sha256"], "B-held-A-receipt")
        receipt = decode(receipt_raw)
        approval = decode(base64.b64decode(wire["approval"], validate=True))
        _validate_A(
            receipt, plan, wire["held"], wire["fixture"], core._utc(approval["issued_utc"]), expiry
        )
        require(
            receipt["report_sha256"] == wire["held_report_sha256"]
            and _parent_identity(directory) == receipt["output_identity"],
            "B-exact-report-and-output",
        )
        _namespace(directory, plan)
        _check_inputs(plan, expiry, deadline)
        _inputs(wire)
        raw = _load_file(
            directory,
            "report.private.json",
            REPORT_CAP,
            expiry,
            deadline,
            receipt["report_token"],
            wire["case"] if wire["fixture"] else None,
        )
        require(
            len(raw) == receipt["report_bytes"] and digest(raw) == wire["held_report_sha256"],
            "B-material-report-identity",
        )
        review = decode(raw)
        _validate_report(review, raw, receipt, plan, wire["held"])
        _namespace(directory, plan)
        _check_inputs(plan, expiry, deadline)
        _inputs(wire)
        metadata = {
            "schema": SCHEMA,
            "substep": "B",
            "status": "completed",
            "pins": wire["held"],
            "producer_receipt_sha256": wire["held_producer_receipt_sha256"],
            "report_sha256": wire["held_report_sha256"],
            "report_bytes_read": len(raw),
            "report_material_passes": 1,
            "original_sources_reopened": False,
            "notice_bearing_private_view": True,
            "authority": dict(AUTHORITY),
            "ended_utc": core._stamp(core._now()),
        }
        require(len(encode(metadata)) <= B_RECEIPT_CAP, "B-metadata-cap")
        result = {"review": review, "review_receipt": metadata}
        require(len(encode(result)) <= ENVELOPE_CAP, "B-material-envelope-cap")
        if wire["fixture"] and wire["case"] == "B-emit-stall":
            time.sleep(30)
        _live(expiry, deadline)
        _namespace(directory, plan)
        _inputs(wire)
        _emit({"receipt": result})  # B only: exactly one approved material view via private pipe.
    finally:
        os.close(directory)


def _entry():
    try:
        raw = sys.stdin.buffer.read(131073)
        require(len(raw) <= 131072, "worker-wire-cap")
        wire = decode(raw)
        fields(
            wire,
            (
                "plan approval origin held fixture case substep deadline held"
                "_producer_receipt_sha256 held_report_sha256"
            ),
            "wire-fields",
        )
        require(
            type(wire["fixture"]) is bool
            and wire["substep"] in ("A", "B")
            and (wire["case"] in CASES if wire["fixture"] else wire["case"] is None),
            "fixed-worker-mode",
        )
        if wire["fixture"]:
            forbidden = decode(os.environ.get("OT062_FIXTURE_FORBIDDEN_PATHS", "[]").encode())
            require(
                type(forbidden) is list and all(type(p) is str for p in forbidden),
                "fixture-denial-list",
            )

            def deny(event, args):
                if event in ("socket.connect", "socket.getaddrinfo"):
                    raise PermissionError("fixture-network-denied")
                if (
                    event == "open"
                    and args
                    and isinstance(args[0], (str, bytes))
                    and os.fsdecode(args[0]) in forbidden
                ):
                    raise PermissionError("fixture-material-denied")

            sys.addaudithook(deny)
        with fixture_time.use(wire["fixture"]):
            (_produce_A if wire["substep"] == "A" else _produce_B)(wire)
    except (OSError, ValueError, RuntimeError, TimeoutError):
        _emit({"error": "retained-review-worker-rejected"})


@fixture_time.selected(5)
def _execute(
    plan_raw,
    approval_raw,
    origin_raw,
    held,
    substep,
    fixture=False,
    case=None,
    whole_seconds=None,
    held_producer_receipt_sha256=None,
    held_report_sha256=None,
):
    seconds = (60 if substep == "A" else 10) if whole_seconds is None else whole_seconds
    start = time.monotonic()
    deadline = start + seconds
    plan, expiry = _gate(plan_raw, approval_raw, origin_raw, held, fixture, True, substep)
    _live(expiry, deadline)
    if substep == "A":
        require(not Path(plan["output_root"]).exists(), "fresh-one-shot-output")
    wire = {
        k: base64.b64encode(v).decode()
        for k, v in (("plan", plan_raw), ("approval", approval_raw), ("origin", origin_raw))
    }
    wire.update(
        held=held,
        fixture=fixture,
        case=case,
        substep=substep,
        deadline=deadline - min(3, seconds / 3),
        held_producer_receipt_sha256=held_producer_receipt_sha256,
        held_report_sha256=held_report_sha256,
    )
    result = _supervise(wire, deadline)
    _live(expiry, deadline)
    _gate(plan_raw, approval_raw, origin_raw, held, fixture, False, substep)
    if result is None:
        return {
            "schema": SCHEMA,
            "substep": substep,
            "status": "incomplete",
            "error": "owned-worker-failure",
            "authority": dict(AUTHORITY),
        }
    issued = core._utc(decode(approval_raw)["issued_utc"])
    if substep == "A":
        require(len(encode(result)) <= RECEIPT_CAP, "A-return-cap")
        _validate_A(result, plan, held, fixture, issued, expiry)
    else:
        _validate_B(
            result, plan, held, held_producer_receipt_sha256, held_report_sha256, issued, expiry
        )
    _live(expiry, deadline)
    return result


@fixture_time.actual
def read_approved(plan_raw, approval_raw, origin_raw, held):
    """Privileged source pass; trusted caller must independently hold actual consent."""
    return _execute(plan_raw, approval_raw, origin_raw, held, "A")


@fixture_time.actual
def review_report_approved(
    plan_raw, approval_raw, origin_raw, held, *, held_producer_receipt_sha256, held_report_sha256
):
    """Privileged ONCE material view; this is not cold metadata or general read use."""
    return _execute(
        plan_raw,
        approval_raw,
        origin_raw,
        held,
        "B",
        held_producer_receipt_sha256=held_producer_receipt_sha256,
        held_report_sha256=held_report_sha256,
    )


def _emit(value):
    raw = encode(value)
    require(len(raw) <= ENVELOPE_CAP, "private-frame-cap")
    sys.stdout.buffer.write(raw + b"\n")
    sys.stdout.buffer.flush()


def _write_checked(directory, name, raw, expiry, deadline):
    _live(expiry, deadline)
    fd = os.open(
        name, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600, dir_fd=directory
    )
    try:
        core._regular(fd)
        count = 0
        while count < len(raw):
            _live(expiry, deadline)
            n = os.write(fd, raw[count:])
            require(0 < n <= len(raw) - count, "metadata-write-progress")
            count += n
        _live(expiry, deadline)
        os.fsync(fd)
        _live(expiry, deadline)
        require(
            core._fingerprint(os.fstat(fd))
            == core._fingerprint(os.stat(name, dir_fd=directory, follow_symlinks=False)),
            "metadata-write-binding",
        )
    finally:
        os.close(fd)


def _validate_context(context, max_bytes):
    fields(
        context,
        (
            "module go toolchain require_labels unknown_directives proble"
            "ms line_count blank_or_comment_lines require_blocks labels_t"
            "runcated complete_supported_lexical_context Go_semantics_dep"
            "endency_build_API_closure_verified raw_go_mod_or_unparsed_li"
            "ne_text_returned require_candidate_count"
        ),
        "context-fields",
    )
    for name in ("module", "go", "toolchain"):
        require(
            context[name] is None
            or (
                type(context[name]) is str
                and re.fullmatch(r"[A-Za-z0-9._~+/-]{1,256}", context[name])
            ),
            "context-header",
        )
    for name in (
        "line_count",
        "blank_or_comment_lines",
        "require_blocks",
        "require_candidate_count",
    ):
        require(type(context[name]) is int and 0 <= context[name] <= max_bytes, "context-count")
    require(
        context["blank_or_comment_lines"] <= context["line_count"]
        and context["require_blocks"] <= context["line_count"],
        "context-line-counts",
    )
    require(
        context["labels_truncated"] is False
        and context["raw_go_mod_or_unparsed_line_text_returned"] is False
        and context["Go_semantics_dependency_build_API_closure_verified"] is False,
        "context-no-promotion",
    )
    for name in ("require_labels", "unknown_directives", "problems"):
        require(
            type(context[name]) is list and len(context[name]) <= max_bytes + 2, "context-list-cap"
        )
    require(
        context["require_candidate_count"] == len(context["require_labels"]), "all-candidate-labels"
    )
    for row in context["require_labels"]:
        fields(row, "line module version", "require-label-fields")
        require(
            type(row["line"]) is int
            and 1 <= row["line"] <= context["line_count"]
            and type(row["module"]) is str
            and re.fullmatch(r"[A-Za-z0-9._~+/-]{1,256}", row["module"])
            and type(row["version"]) is str
            and re.fullmatch(r"[A-Za-z0-9.+_-]{1,128}", row["version"]),
            "bounded-require-label",
        )
    for row in context["unknown_directives"]:
        fields(row, "line directive", "unknown-directive-fields")
        require(
            type(row["line"]) is int
            and 1 <= row["line"] <= context["line_count"]
            and (
                row["directive"] is None
                or (
                    type(row["directive"]) is str
                    and re.fullmatch(r"[A-Za-z][A-Za-z0-9_-]{0,31}", row["directive"])
                )
            ),
            "bounded-unknown-directive",
        )
    for row in context["problems"]:
        fields(row, "line kind", "problem-fields")
        require(
            type(row["line"]) is int
            and 0 <= row["line"] <= context["line_count"]
            and row["kind"]
            in (
                "oversized-line",
                "unmatched-block-close",
                "unsupported-block-content",
                "duplicate-header",
                "unsupported-header-syntax",
                "unsupported-require-syntax",
                "unclosed-block",
                "missing-module-header",
                "unsupported-newline-form",
            ),
            "bounded-problem",
        )
    require(
        type(context["complete_supported_lexical_context"]) is bool
        and context["complete_supported_lexical_context"]
        == (not bool(context["problems"] or context["unknown_directives"])),
        "context-completeness",
    )


def _validate_B(result, plan, held, producer_pin, report_pin, issued, expiry):
    require(len(encode(result)) <= ENVELOPE_CAP, "B-envelope-cap")
    fields(result, "review review_receipt", "B-envelope-fields")
    meta = result["review_receipt"]
    fields(
        meta,
        (
            "schema substep status pins producer_receipt_sha256 report_sh"
            "a256 report_bytes_read report_material_passes original_sourc"
            "es_reopened notice_bearing_private_view authority ended_utc"
        ),
        "B-metadata-fields",
    )
    raw = encode(result["review"])
    require(
        len(encode(meta)) <= B_RECEIPT_CAP
        and 0 < len(raw) <= REPORT_CAP
        and digest(raw) == report_pin,
        "B-held-view-digest",
    )
    require(
        meta["schema"] == SCHEMA
        and meta["substep"] == "B"
        and meta["status"] == "completed"
        and meta["pins"] == held
        and meta["producer_receipt_sha256"] == producer_pin
        and meta["report_sha256"] == report_pin
        and type(meta["report_bytes_read"]) is int
        and meta["report_bytes_read"] == len(raw)
        and type(meta["report_material_passes"]) is int
        and meta["report_material_passes"] == 1
        and meta["original_sources_reopened"] is False
        and meta["notice_bearing_private_view"] is True
        and encode(meta["authority"]) == encode(AUTHORITY),
        "B-complete-scope",
    )
    require(
        issued <= core._utc(meta["ended_utc"]) < expiry
        and core._utc(meta["ended_utc"]) <= core._now(),
        "B-execution-window",
    )
    rows = result["review"].get("source_observations")
    # Validate metadata independently without reopening either original source.
    require(type(rows) is list and len(rows) == 2, "B-source-rows")
    for row, target in zip(rows, plan["targets"], strict=True):
        fields(row, "role bytes sha256 source_passes UTF8_nonNUL LF_count", "B-source-row-fields")
        require(
            row["role"] == target["role"]
            and type(row["bytes"]) is int
            and row["bytes"] == target["expected_bytes"]
            and row["sha256"] == target["expected_sha256"]
            and type(row["source_passes"]) is int
            and row["source_passes"] == 1
            and row["UTF8_nonNUL"] is True
            and type(row["LF_count"]) is int
            and 0 <= row["LF_count"] <= row["bytes"],
            "B-source-row",
        )
    _validate_report(result["review"], raw, {"source_rows": rows}, plan, held)


@fixture_time.invented
def fixture_inputs(parent, *, go_text=None, notice_text=FIXTURE_NOTICE):
    """Create only caller-owned invented files; never consult retained materials."""
    parent = Path(parent)
    checked = core._directory(str(parent))
    try:
        core._private_directory(checked)
        with os.scandir(checked) as entries:
            require(next(entries, None) is None, "fresh-empty-owned-fixture-parent")
    finally:
        os.close(checked)
    require(
        parent.is_dir() and stat.S_IMODE(parent.lstat().st_mode) == 0o700, "fixture-private-parent"
    )
    root = parent / "invented-input"
    root.mkdir(mode=0o700)
    objects = root / "objects"
    objects.mkdir(mode=0o700)
    if go_text is None:
        go_text = (
            "module invented.invalid/project\ngo 1.23\nrequire (\n"
            + "".join(f"invented.invalid/dep{i} v1.0.0\n" for i in range(201))
            + ")\n"
        )
    targets = []
    for role, text in zip(ROLES, (go_text, notice_text), strict=True):
        raw = text.encode()
        path = objects / role
        fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        try:
            count = 0
            while count < len(raw):
                count += os.write(fd, raw[count:])
            os.fsync(fd)
        finally:
            os.close(fd)
        targets.append(
            {
                "role": role,
                "path": str(path),
                "expected_bytes": len(raw),
                "expected_sha256": digest(raw),
                "token": _token(path.lstat()),
            }
        )
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
        "records": [
            {
                "subject": subject,
                "origin_utc": core._stamp(now),
                "deadline_utc": core._stamp(end),
                "evidence_sha256": digest(subject.encode()),
                "basis": "new-technical-fact-evidence",
            }
            for subject in COVERAGE
        ],
        "retention": retention,
        "origin_scope": "new-observation-or-proposal-fact",
        "origins_verified": True,
        "unknown_required_origins": [],
        "does_not_reset_referenced_material_origins": True,
        "unknown_referenced_origins_timely_claimed": False,
    }
    origin_raw = encode(origin)
    source = _identity()
    owner = _owner()
    output = parent / "invented-retained-review"
    directory = core._directory(str(parent))
    try:
        parent_identity = _parent_identity(directory)
    finally:
        os.close(directory)
    plan = {
        "schema": SCHEMA,
        "kind": "invented",
        "targets": targets,
        "input_context": {
            "root_path": str(root),
            "root_token": _token(root.lstat()),
            "objects_path": str(objects),
            "objects_token": _token(objects.lstat()),
        },
        "limits": _limits(targets),
        "retention": retention,
        "source": source,
        "owner": owner,
        "rights_basis_sha256": digest(b"INVENTED limited fixture rights"),
        "qualification_sha256": digest(b"INVENTED fixture qualification"),
        "output_root": str(output),
        "parent_identity": parent_identity,
        "origin_sha256": digest(origin_raw),
    }
    plan_raw = encode(plan)
    held = {
        "plan_sha256": digest(plan_raw),
        "origin_sha256": digest(origin_raw),
        "source_sha256": digest(encode(source)),
        "owner_sha256": digest(encode(owner)),
        "rights_basis_sha256": plan["rights_basis_sha256"],
        "output_root": str(output),
    }
    approval = {
        "schema": SCHEMA,
        "kind": "invented",
        "plan_sha256": held["plan_sha256"],
        "origin_sha256": held["origin_sha256"],
        "rights_basis_sha256": held["rights_basis_sha256"],
        "source_sha256": held["source_sha256"],
        "owner_sha256": held["owner_sha256"],
        "nonce": "1" * 32,
        "issued_utc": core._stamp(now),
        "expires_utc": core._stamp(now + timedelta(minutes=30)),
        "scope": "one-retained-two-source-pass-and-one-notice-report-review",
        "authority": dict(AUTHORITY),
    }
    approval_raw = encode(approval)
    held["approval_sha256"] = digest(approval_raw)
    inputs = (plan_raw, approval_raw, origin_raw, held)
    _FIXTURE_PROVENANCE.add(_fixture_key(inputs))
    return inputs


@fixture_time.invented
def run_fixture_review(
    inputs,
    *,
    substep="A",
    case="ok",
    whole_seconds=None,
    held_producer_receipt_sha256=None,
    held_report_sha256=None,
):
    require(_fixture_key(inputs) in _FIXTURE_PROVENANCE, "internally-created-fixture-required")
    require(case in CASES, "fixed-invented-case")
    return _execute(
        *inputs,
        substep,
        True,
        case,
        whole_seconds,
        held_producer_receipt_sha256,
        held_report_sha256,
    )


@fixture_time.selected(4)
def inspect_receipt_metadata(
    plan_raw, approval_raw, origin_raw, held, *, held_receipt_sha256, fixture=False
):
    """Cold metadata only: never opens either source or the notice-bearing report."""
    issued = core._utc(decode(approval_raw)["issued_utc"])
    plan, expiry = _gate(plan_raw, approval_raw, origin_raw, held, fixture, historical_at=issued)
    retained_expiry = min(
        _retention(plan["retention"]),
        *(core._utc(row["deadline_utc"]) for row in decode(origin_raw)["records"]),
    )
    deadline = time.monotonic() + 10
    directory = core._directory(plan["output_root"])
    try:
        _namespace(directory, plan)
        raw = _load_file(directory, "receipt.private.json", RECEIPT_CAP, retained_expiry, deadline)
        require(digest(raw) == held_receipt_sha256, "held-A-metadata-receipt")
        result = decode(raw)
        _validate_A(
            result, plan, held, fixture, core._utc(decode(approval_raw)["issued_utc"]), expiry
        )
        _namespace(directory, plan)
        _gate(plan_raw, approval_raw, origin_raw, held, fixture, historical_at=issued)
        return result
    finally:
        os.close(directory)


def _fixture_key(inputs):
    require(type(inputs) is tuple and len(inputs) == 4, "owned-fixture-tuple")
    require(
        all(type(raw) is bytes for raw in inputs[:3]) and type(inputs[3]) is dict,
        "owned-fixture-types",
    )
    return digest(
        b"".join(len(raw).to_bytes(4, "big") + raw for raw in (*inputs[:3], encode(inputs[3])))
    )
