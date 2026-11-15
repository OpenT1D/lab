"""Source-bound host control proposal and invented-only cold reconstruction.

No selected runtime, sandbox, socket, child process or native module is executed.
The explicit argv describes a proposed entrypoint that does not yet exist. A
fixture completion never supplies host acceptance or operational permission.
"""

import math
from pathlib import Path, PurePosixPath

from .contract import AUTHORITY, decode, digest, encode, fields, require, source_identity
from .worker_fixture import _owner_identity

PROFILE_SCHEMA = "opent1d.simglucose-host-profile-proposal/1"
REQUEST_SCHEMA = "opent1d.simglucose-host-qualification-request/1"
FRAME_SCHEMA = "opent1d.simglucose-host-invented-frames/1"
MAX_STREAM = 256 * 1024
DEADLINE = "2026-11-28T18:32:01Z"
FIXTURE_INPUT = b"invented matched-control canary version 1; no native or asset bytes\n"
CASES = (
    "complete",
    "cancel-before-start",
    "cancel-after-two",
    "deadline-after-two",
    "error-after-two",
    "error-and-cleanup",
    "cleanup-error",
    "denial-mismatch",
    "crash-after-two",
)
RETENTION = {
    "not_after_utc": DEADLINE,
    "max_days_new_facts": 30,
    "earlier_limits_win": True,
    "old_origins_reset": False,
    "unknown_old_origins_timely": False,
    "automatic_cleanup_or_extension": False,
}
PRECONDITIONS = (
    "exact_runtime_security_update_assessment_sha256",
    "applicable_rights_and_input_access_sha256",
    "selected_executable_sha256",
    "stdlib_native_OS_ABI_filemap_sha256",
    "independent_setup_receipt_sha256",
    "probe_source_sha256",
    "OS_profile_backend_sha256",
    "current_owner_boot_physical_roots_sha256",
    "explicit_scoped_postponement_lift_sha256",
    "exact_bounded_qualification_grant_sha256",
)
EFFECTS = (
    ("file", "read-canary", "outside-allowed-file-canary"),
    ("network", "connect-owned-loopback", "owned-loopback-listener"),
    ("IPC", "connect-owned-IPC", "outside-allowed-IPC-canary"),
    ("process", "spawn-fixed-owned-leaf", "fixed-source-leaf"),
    ("loader", "import-fixed-source-canary", "outside-allowed-module-canary"),
    ("addon", "load-fixed-native-canary", "unadmitted-native-canary"),
)
OUTPUTS = (
    "request.json",
    "input-map.json",
    "parent-events.ndjson",
    "worker-events.ndjson",
    "ownership.json",
    "matched-controls.json",
    "cleanup.json",
    "host-result.json",
)


def run_host_qualification(*_args, **_kwargs):
    """Closed before input/source/path use; no operational launcher is shipped."""
    raise PermissionError("selected-runtime HOST qualification deferred; exact gates remain closed")


def _identity():
    return source_identity() | {
        "host_qualification_fixture.py": digest(Path(__file__).read_bytes())
    }


def invented_candidate():
    return {
        "schema": "opent1d.invented-host-candidate/1",
        "kind": "invented",
        "actual_executable_sha256": None,
        "native_execution_deferred": True,
        "new_authority_granted": False,
    }


def _decode(raw):
    try:
        value = decode(raw)
    except RecursionError as error:
        raise ValueError("bounded-JSON-depth") from error
    todo, visited = [(value, 0)], 0
    while todo:
        item, depth = todo.pop()
        visited += 1
        require(depth <= 64 and visited <= 32768, "bounded-JSON-structure")
        if type(item) is float:
            require(math.isfinite(item), "finite-JSON-number")
        elif type(item) is dict:
            todo.extend((child, depth + 1) for child in item.values())
        elif type(item) is list:
            todo.extend((child, depth + 1) for child in item)
    return value


def _pin(raw, expected, label):
    require(digest(raw) == expected, label)
    return _decode(raw)


def _root(value):
    require(type(value) is str and 0 < len(value.encode("utf-8")) <= 4096, "trusted-proposed-root")
    require(
        all(ord(char) >= 32 and ord(char) != 127 for char in value) and not value.startswith("//"),
        "root-without-control-or-double-slash",
    )
    path = PurePosixPath(value)
    require(
        path.is_absolute() and ".." not in path.parts and len(path.parts) > 1,
        "absolute-proposed-root-without-parent",
    )
    require(str(path) == value and not value.endswith("/"), "canonical-proposed-root")
    return value


def _controls():
    return [
        {
            "id": family + ":" + context,
            "family": family,
            "operation": operation,
            "target_role": target,
            "context": context,
            "expected": expected,
            "control_source_sha256": None,
            "independent_witness_sha256": None,
            "actual_control_qualified": False,
        }
        for family, operation, target in EFFECTS
        for context, expected in (("reference-positive", "allowed"), ("profile-negative", "denied"))
    ]


def propose_profile(candidate_raw, held_candidate_sha256, staged_root, evidence_root):
    """Pure renderer. Roots are trusted API inputs, never selected by JSON."""
    candidate = _pin(candidate_raw, held_candidate_sha256, "held-candidate-pin")
    require(
        type(candidate) is dict and type(candidate.get("schema")) is str,
        "metadata-candidate-object",
    )
    stage, evidence = _root(staged_root), _root(evidence_root)
    require(
        stage != evidence
        and not stage.startswith(evidence + "/")
        and not evidence.startswith(stage + "/"),
        "disjoint-proposed-roots",
    )
    return {
        "schema": PROFILE_SCHEMA,
        "kind": "proposed-not-operational",
        "engine_scope": "simglucose-audit1-host-controls-only",
        "proposed_platform": "Darwin-arm64-not-host-qualified",
        "candidate_sha256": held_candidate_sha256,
        "candidate_admission": "none; opaque metadata identity binding only",
        "staged_root": stage,
        "evidence_root": evidence,
        "argv_status": "proposed-role-paths-entrypoint-not-implemented-or-launched",
        "argv": [
            stage + "/bin/python3",
            "-I",
            "-S",
            "-B",
            stage + "/opent1d/host_qualification_probe.py",
            "--request",
            evidence + "/request.json",
            "--events",
            evidence + "/worker-events.ndjson",
        ],
        "env": {
            "LANG": "C",
            "LC_ALL": "C",
            "PATH": "/usr/bin:/bin",
            "HOME": evidence + "/home",
            "TMPDIR": evidence + "/tmp",
            "MPLCONFIGDIR": evidence + "/mpl",
            "MPLBACKEND": "Agg",
            "PYTHONDONTWRITEBYTECODE": "1",
        },
        "environment_policy": "exact-replacement-no-ambient-proxy-auth-cache-or-SSL-overrides",
        "actual_executable_sha256": None,
        "actual_probe_source_sha256": None,
        "actual_verified_argv_sha256": None,
        "actual_OS_policy_sha256": None,
        "profile_language": "logical-control-proposal-not-an-installed-OS-policy",
        "rules": {
            "default": "deny",
            "read_exact_staged_filemap_sha256": None,
            "write_only_private_evidence_root": evidence,
            "necessary_inherited_parent_channels_only": True,
            "network_including_loopback": "deny",
            "new_subprocesses": "deny",
            "system_fonts_and_user_configuration": "deny",
            "modules_and_addons_outside_exact_staged_filemap": "deny",
            "MPLCONFIGDIR_or_Agg_is_confinement": False,
            "resource_access_is_granted_by_this_profile": False,
        },
        "controls": _controls(),
        "output_file_map": {name: evidence + "/" + name for name in OUTPUTS},
        "bounds": {
            "whole_attempt_ms": 30000,
            "per_control_ms": 1000,
            "cleanup_ms": 1000,
            "frame_bytes": 16384,
            "frames": 64,
            "stream_bytes": MAX_STREAM,
        },
        "missing_actual_prerequisites": dict.fromkeys(PRECONDITIONS),
        "execution_order": [
            "exact-current-runtime-security-update-and-applicable-rights",
            "explicit-scoped-postponement-lift",
            "exact-bounded-qualification-grant",
            "selected-runtime-HOST-controls",
            "separate-EXECUTION-grant-for-model-slots",
        ],
        "LT1_transfer": (
            "none; any LT1/Node probe requires its own current Node assessment and exact scope"
        ),
        "qualification_ready": False,
        "host_qualified": False,
        "authority": dict(AUTHORITY),
        "retention": dict(RETENTION),
    }


def _profile(profile_raw, held_profile_sha256, candidate_raw, held_candidate_sha256):
    value = _pin(profile_raw, held_profile_sha256, "held-profile-pin")
    require(type(value) is dict, "profile-object")
    expected = propose_profile(
        candidate_raw, held_candidate_sha256, value.get("staged_root"), value.get("evidence_root")
    )
    require(encode(value) == encode(expected), "fixed-profile-reconstruction")
    return value


def propose_request(profile_raw, held_profile_sha256, candidate_raw, held_candidate_sha256):
    """Bounded request schema only: actual ownership and all execution gates unresolved."""
    profile = _profile(profile_raw, held_profile_sha256, candidate_raw, held_candidate_sha256)
    return {
        "schema": REQUEST_SCHEMA,
        "kind": "qualification-request-proposal",
        "case": None,
        "candidate_sha256": held_candidate_sha256,
        "profile_sha256": held_profile_sha256,
        "source_identity": _identity(),
        "process_owner_source_identity": _owner_identity(),
        "input_sha256": digest(FIXTURE_INPUT),
        "control_ids": [row["id"] for row in profile["controls"]],
        "ownership": None,
        "actual_prerequisites": dict.fromkeys(PRECONDITIONS),
        "actual_qualification_requested": False,
        "model_execution_requested": False,
        "authority": dict(AUTHORITY),
        "retention": dict(RETENTION),
    }


def fixture_request(
    profile_raw, held_profile_sha256, candidate_raw, held_candidate_sha256, case="complete"
):
    require(type(case) is str and case in CASES, "fixed-fixture-case")
    value = propose_request(profile_raw, held_profile_sha256, candidate_raw, held_candidate_sha256)
    value.update(
        kind="invented",
        case=case,
        ownership={
            "kind": "invented-live-owner-token",
            "parent": "invented-parent",
            "worker": "invented-worker",
            "tree": "invented-owned-tree",
            "token": "invented-one-attempt-token",
        },
    )
    return value


def validate_request(
    request_raw,
    held_request_sha256,
    profile_raw,
    held_profile_sha256,
    candidate_raw,
    held_candidate_sha256,
    input_raw=FIXTURE_INPUT,
):
    """Validate data; this never authorizes qualification or opens a path."""
    require(type(input_raw) is bytes and input_raw == FIXTURE_INPUT, "fixed-invented-input-only")
    request = _pin(request_raw, held_request_sha256, "held-request-pin")
    profile = _profile(profile_raw, held_profile_sha256, candidate_raw, held_candidate_sha256)
    require(type(request) is dict, "request-object")
    expected = propose_request(
        profile_raw, held_profile_sha256, candidate_raw, held_candidate_sha256
    )
    if request.get("kind") == "invented":
        expected = fixture_request(
            profile_raw,
            held_profile_sha256,
            candidate_raw,
            held_candidate_sha256,
            request.get("case"),
        )
    require(encode(request) == encode(expected), "fixed-request-reconstruction")
    return request, profile


def _event_sequence(request, profile):
    """Producer only. Reader checks protocol state independently below."""
    case = request["case"]
    yield {
        "event": "header",
        "data": {
            "schema": FRAME_SCHEMA,
            "kind": "invented",
            "candidate_sha256": request["candidate_sha256"],
            "profile_sha256": request["profile_sha256"],
            "request_sha256": request["_raw_sha256"],
            "input_sha256": request["input_sha256"],
            "source_identity": request["source_identity"],
            "process_owner_source_identity": request["process_owner_source_identity"],
            "ownership": request["ownership"],
            "actual_OS_observation": False,
            "clock_kind": "invented-monotonic-ms",
        },
    }
    if case == "cancel-before-start":
        yield {
            "event": "cancel",
            "data": {
                "at_ms": 0,
                "source": "invented-parent",
                "owner_token": request["ownership"]["token"],
            },
        }
        yield {
            "event": "terminal",
            "data": _terminal("interrupted", "invented-cancel-before-start", None, 0, None),
        }
        return
    yield {
        "event": "constructed",
        "data": {"at_ms": 0, "owner_token": request["ownership"]["token"]},
    }
    observed, pending, primary, status = 0, None, None, "completed"
    for index, control in enumerate(profile["controls"]):
        pending = control["id"]
        yield {
            "event": "control-start",
            "data": {
                "id": pending,
                "at_ms": (index + 1) * 100,
                "input_sha256": request["input_sha256"],
            },
        }
        if index == 2 and case in (
            "cancel-after-two",
            "deadline-after-two",
            "error-after-two",
            "error-and-cleanup",
            "crash-after-two",
        ):
            if case == "crash-after-two":
                return
            if case == "cancel-after-two":
                yield {
                    "event": "cancel",
                    "data": {
                        "at_ms": 300,
                        "source": "invented-parent",
                        "owner_token": request["ownership"]["token"],
                    },
                }
            elif case == "deadline-after-two":
                deadline = 300 + profile["bounds"]["per_control_ms"]
                yield {
                    "event": "deadline",
                    "data": {
                        "id": pending,
                        "at_ms": deadline,
                        "deadline_ms": deadline,
                        "scope": "control",
                        "clock_kind": "invented-monotonic-ms",
                    },
                }
            else:
                yield {
                    "event": "control-error",
                    "data": {"id": pending, "at_ms": 300, "error": "invented-control-error"},
                }
            status = (
                "interrupted"
                if case == "cancel-after-two"
                else "incomplete"
                if case == "deadline-after-two"
                else "failed"
            )
            primary = {
                "cancel-after-two": "invented-cancel",
                "deadline-after-two": "invented-deadline",
                "error-after-two": "invented-control-error",
                "error-and-cleanup": "invented-control-error",
            }[case]
            break
        result = "allowed" if index == 1 and case == "denial-mismatch" else control["expected"]
        yield {
            "event": "control-result",
            "data": {
                "id": pending,
                "at_ms": (index + 1) * 100 + 10,
                "result": result,
                "actual_OS_observation": False,
            },
        }
        observed += 1
        pending = None
        if index == 1 and case == "denial-mismatch":
            status, primary = "failed", "invented-unexpected-denial-result"
            break
    cleanup_error = (
        "invented-cleanup-error" if case in ("cleanup-error", "error-and-cleanup") else None
    )
    if cleanup_error:
        status = "failed"
    yield {
        "event": "cleanup",
        "data": {
            "owner_token": request["ownership"]["token"],
            "worker_exited": True,
            "owned_tree_absent": cleanup_error is None,
            "reader_joined": True,
            "writer_joined": True,
            "error": cleanup_error,
            "actual_OS_observation": False,
        },
    }
    yield {
        "event": "terminal",
        "data": _terminal(status, primary, cleanup_error, observed, pending),
    }


def _terminal(status, primary, cleanup, observed, pending):
    return {
        "status": status,
        "primary_error": primary,
        "cleanup_error": cleanup,
        "observed_controls": observed,
        "planned_controls": 12,
        "pending_control": pending,
        "host_result": {
            "profile_applied_on_actual_host": False,
            "host_qualified": False,
            "native_acceptance": False,
            "model_slots_admitted": False,
        },
        "authority": dict(AUTHORITY),
        "retention": dict(RETENTION),
    }


def run_fixture(
    request_raw,
    profile_raw,
    held_profile_sha256,
    candidate_raw,
    held_candidate_sha256,
    input_raw=FIXTURE_INPUT,
):
    request, profile = validate_request(
        request_raw,
        digest(request_raw),
        profile_raw,
        held_profile_sha256,
        candidate_raw,
        held_candidate_sha256,
        input_raw,
    )
    require(request["kind"] == "invented", "invented-fixture-only")
    request = request | {"_raw_sha256": digest(request_raw)}
    previous, lines = None, []
    for sequence, event in enumerate(_event_sequence(request, profile)):
        raw = encode({"sequence": sequence, "previous_sha256": previous, **event}) + b"\n"
        require(len(raw) <= 16384, "bounded-fixture-frame")
        lines.append(raw)
        previous = digest(raw)
    require(_identity() == request["source_identity"], "source-changed-during-fixture")
    return b"".join(lines)


def inspect_fixture(
    frames_raw,
    held_frames_sha256,
    request_raw,
    held_request_sha256,
    profile_raw,
    held_profile_sha256,
    candidate_raw,
    held_candidate_sha256,
    input_raw=FIXTURE_INPUT,
):
    """Cold finite-fixture state validation; no producer, runner or engine calls."""
    require(
        type(frames_raw) is bytes and 0 < len(frames_raw) <= MAX_STREAM, "bounded-fixture-stream"
    )
    require(digest(frames_raw) == held_frames_sha256, "held-frame-stream-pin")
    request, profile = validate_request(
        request_raw,
        held_request_sha256,
        profile_raw,
        held_profile_sha256,
        candidate_raw,
        held_candidate_sha256,
        input_raw,
    )
    require(request["kind"] == "invented", "invented-fixture-only")
    lines = frames_raw.splitlines(keepends=True)
    require(len(lines) <= 64, "bounded-fixture-frame-count")
    torn = not lines[-1].endswith(b"\n")
    if torn:
        lines.pop()
    previous, phase, observed, pending, terminal = None, "header", 0, None, None
    case, cleanup_error = request["case"], None
    cancel_seen, deadline_seen, error_seen = False, False, False
    for sequence, raw in enumerate(lines):
        require(len(raw) <= 16384 and raw.endswith(b"\n"), "bounded-fixture-frame")
        row = _decode(raw[:-1])
        fields(row, "sequence previous_sha256 event data", "frame-fields")
        require(
            type(row["sequence"]) is int
            and row["sequence"] == sequence
            and row["previous_sha256"] == previous,
            "frame-sequence-chain",
        )
        event, data = row["event"], row["data"]
        require(type(data) is dict and terminal is None, "frame-data-before-terminal")
        if phase == "header":
            expected = {
                "schema": FRAME_SCHEMA,
                "kind": "invented",
                "candidate_sha256": held_candidate_sha256,
                "profile_sha256": held_profile_sha256,
                "request_sha256": held_request_sha256,
                "input_sha256": digest(input_raw),
                "source_identity": request["source_identity"],
                "process_owner_source_identity": request["process_owner_source_identity"],
                "ownership": request["ownership"],
                "actual_OS_observation": False,
                "clock_kind": "invented-monotonic-ms",
            }
            require(
                event == "header" and encode(data) == encode(expected), "source-input-owner-header"
            )
            phase = "pre-start" if case == "cancel-before-start" else "construction"
        elif phase == "construction":
            require(
                event == "constructed"
                and encode(data)
                == encode({"at_ms": 0, "owner_token": request["ownership"]["token"]}),
                "fresh-invented-owner-construction",
            )
            phase = "control-start"
        elif event == "cancel":
            require(
                not cancel_seen and case in ("cancel-before-start", "cancel-after-two"),
                "single-invented-cancel",
            )
            before = case == "cancel-before-start"
            require(
                (before and phase == "pre-start" and observed == 0)
                or (not before and phase == "control-result" and observed == 2),
                "cancel-prefix-state",
            )
            expected = {
                "at_ms": 0 if before else 300,
                "source": "invented-parent",
                "owner_token": request["ownership"]["token"],
            }
            require(encode(data) == encode(expected), "cancel-owner-binding")
            cancel_seen = True
        elif event == "deadline":
            require(
                not deadline_seen
                and case == "deadline-after-two"
                and phase == "control-result"
                and observed == 2,
                "single-invented-deadline",
            )
            deadline = 300 + profile["bounds"]["per_control_ms"]
            expected = {
                "id": pending,
                "at_ms": deadline,
                "deadline_ms": deadline,
                "scope": "control",
                "clock_kind": "invented-monotonic-ms",
            }
            require(
                encode(data) == encode(expected)
                and deadline <= profile["bounds"]["whole_attempt_ms"],
                "deadline-clock-binding",
            )
            deadline_seen = True
        elif event == "control-error":
            require(
                not error_seen
                and case in ("error-after-two", "error-and-cleanup")
                and phase == "control-result"
                and observed == 2,
                "single-invented-control-error",
            )
            require(
                encode(data)
                == encode({"id": pending, "at_ms": 300, "error": "invented-control-error"}),
                "pending-error-binding",
            )
            error_seen = True
        elif event == "control-start":
            require(phase == "control-start" and observed < 12, "control-start-state")
            require(not (case == "denial-mismatch" and observed >= 2), "stop-after-denial-mismatch")
            expected = {
                "id": profile["controls"][observed]["id"],
                "at_ms": (observed + 1) * 100,
                "input_sha256": digest(input_raw),
            }
            require(encode(data) == encode(expected), "fixed-control-start")
            pending, phase = data["id"], "control-result"
        elif event == "control-result":
            require(phase == "control-result" and pending is not None, "control-result-state")
            require(
                not (
                    observed == 2
                    and case
                    in (
                        "cancel-after-two",
                        "deadline-after-two",
                        "error-after-two",
                        "error-and-cleanup",
                        "crash-after-two",
                    )
                ),
                "preserved-pending-prefix",
            )
            result = (
                "allowed"
                if case == "denial-mismatch" and observed == 1
                else profile["controls"][observed]["expected"]
            )
            expected = {
                "id": pending,
                "at_ms": (observed + 1) * 100 + 10,
                "result": result,
                "actual_OS_observation": False,
            }
            require(encode(data) == encode(expected), "fixed-matched-control-result")
            observed, pending, phase = observed + 1, None, "control-start"
        elif event == "cleanup":
            require(
                case not in ("cancel-before-start", "crash-after-two"),
                "no-cleanup-for-unstarted-or-crashed",
            )
            expected_count = (
                2
                if case
                in (
                    "cancel-after-two",
                    "deadline-after-two",
                    "error-after-two",
                    "error-and-cleanup",
                    "denial-mismatch",
                )
                else 12
            )
            expected_pending = (
                profile["controls"][2]["id"]
                if case
                in (
                    "cancel-after-two",
                    "deadline-after-two",
                    "error-after-two",
                    "error-and-cleanup",
                )
                else None
            )
            require(
                (case != "cancel-after-two" or cancel_seen)
                and (case != "deadline-after-two" or deadline_seen)
                and (case not in ("error-after-two", "error-and-cleanup") or error_seen),
                "required-primary-observation",
            )
            require(
                observed == expected_count
                and pending == expected_pending
                and phase in ("control-start", "control-result"),
                "cleanup-prefix-accounting",
            )
            cleanup_error = (
                "invented-cleanup-error" if case in ("cleanup-error", "error-and-cleanup") else None
            )
            expected = {
                "owner_token": request["ownership"]["token"],
                "worker_exited": True,
                "owned_tree_absent": cleanup_error is None,
                "reader_joined": True,
                "writer_joined": True,
                "error": cleanup_error,
                "actual_OS_observation": False,
            }
            require(encode(data) == encode(expected), "owned-stop-join-cleanup-data")
            phase = "terminal"
        elif event == "terminal":
            require(
                phase in ("terminal", "pre-start")
                and (case != "cancel-before-start" or cancel_seen),
                "terminal-after-required-cleanup",
            )
            statuses = {
                "complete": ("completed", None),
                "cleanup-error": ("failed", None),
                "denial-mismatch": ("failed", "invented-unexpected-denial-result"),
                "cancel-after-two": ("interrupted", "invented-cancel"),
                "deadline-after-two": ("incomplete", "invented-deadline"),
                "error-after-two": ("failed", "invented-control-error"),
                "error-and-cleanup": ("failed", "invented-control-error"),
                "cancel-before-start": ("interrupted", "invented-cancel-before-start"),
            }
            require(case in statuses, "no-terminal-for-crash")
            status, primary = statuses[case]
            require(
                encode(data)
                == encode(_terminal(status, primary, cleanup_error, observed, pending)),
                "terminal-host-status-authority-binding",
            )
            terminal = data
        else:
            raise ValueError("fixed-frame-state")
        previous = digest(raw)
    require(lines and phase != "header", "fixture-header-required")
    require(not (torn and terminal is not None), "trailing-bytes-after-terminal")
    require(_identity() == request["source_identity"], "source-changed-during-cold-read")
    return {
        "kind": "invented",
        "status": terminal["status"] if terminal else "incomplete",
        "observed_controls": observed,
        "planned_controls": 12,
        "pending_control": pending,
        "torn_tail": torn,
        "host_qualified": False,
        "actual_OS_observation": False,
        "native_acceptance": False,
        "authority": dict(AUTHORITY),
        "retention": dict(RETENTION),
    }
