"""Private data-only recovery proposals; no I/O, deletion or approval."""

import base64
import binascii
import copy
import hashlib
import json
import plistlib
from datetime import UTC, datetime
from pathlib import PurePosixPath
from xml.parsers.expat import ExpatError

from experiments.lt1_diagnostic import recovery_evidence as evidence
from experiments.lt1_diagnostic import recovery_probe as probe
from experiments.lt1_diagnostic import retention
from experiments.lt1_diagnostic.archive_preflight import unique_object

LIMIT = 4 * 1024 * 1024
AUTHORITY = dict(evidence.AUTHORITY)


def need(ok, reason):
    if not ok:
        raise ValueError("LT1 recovery readback refused: " + reason)


def encoded(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def decoded(raw, expected):
    need(
        isinstance(raw, bytes)
        and 0 < len(raw) <= LIMIT
        and retention.sha(expected)
        and digest(raw) == expected,
        "expected bounded bytes",
    )
    return json.loads(raw, object_pairs_hook=unique_object)


def interval(start, end, now):
    def stamp(value):
        need(isinstance(value, str) and len(value) <= 64, "interval timestamp")
        try:
            at = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError as error:
            raise ValueError("LT1 recovery readback refused: interval timestamp") from error
        need(at.tzinfo is not None and at.utcoffset().total_seconds() == 0, "UTC interval")
        return at.astimezone(UTC)

    lower, upper = stamp(start), stamp(end)
    need(lower <= upper <= now, "reversed or future interval")
    return lower, upper


def _query(name, value, tools):
    need(isinstance(value, dict), "query object")
    if set(value) == {"status", "returncode", "error"}:
        need(
            value["status"] == "unavailable"
            and value["returncode"] is None
            and isinstance(value["error"], str)
            and 0 < len(value["error"]) <= 256,
            "unavailable query",
        )
        if tools[probe.COMMANDS[name][0]] is None:
            need(value["error"] == "tool-unavailable", "missing tool result")
        return
    retention.fields(
        value,
        "status returncode truncated plist_valid stdout_base64 stderr_base64 "
        "stdout_sha256 stderr_sha256",
    )
    need(
        type(value["returncode"]) is int
        and type(value["truncated"]) is bool
        and tools[probe.COMMANDS[name][0]] is not None,
        "query result fields",
    )
    parts = {}
    for field in ("stdout", "stderr"):
        raw = value[field + "_base64"]
        need(
            isinstance(raw, str) and len(raw) <= 4 * ((probe.QUERY_LIMIT + 2) // 3),
            "query output bound",
        )
        try:
            decoded = base64.b64decode(raw, validate=True)
        except (ValueError, binascii.Error) as error:
            raise ValueError("LT1 recovery readback refused: query base64") from error
        need(
            len(decoded) <= probe.QUERY_LIMIT
            and base64.b64encode(decoded).decode("ascii") == raw
            and digest(decoded) == value[field + "_sha256"],
            "query output identity",
        )
        parts[field] = decoded
    valid = None
    if name != "time_machine_snapshots":
        try:
            valid = isinstance(plistlib.loads(parts["stdout"]), (dict, list))
        except (ValueError, plistlib.InvalidFileException, OverflowError, ExpatError):
            valid = False
    need(value["plist_valid"] is valid, "query plist result")
    observed = (
        value["returncode"] == 0
        and not value["truncated"]
        and bool(parts["stdout"])
        and valid is not False
    )
    need(
        value["status"] == ("response-observed" if observed else "unavailable"),
        "inconsistent query status",
    )


def propose(
    register_raw,
    expected_register_sha256,
    policy_raw,
    expected_policy_sha256,
    scope_raw,
    expected_scope_sha256,
    mapping_raw,
    expected_mapping_sha256,
    probe_raw,
    expected_probe_sha256,
    *,
    as_of,
    expected_context_sha256,
    previous_raw=None,
    expected_previous_sha256=None,
):
    """Return unsaved successor bytes and provenance, never an admitted action.

    Expected identities/mapping are supplied by external review. Their truth is
    not proved here. Whole-second v1 observed_at is only a conservative floor of
    the interval start; raw bounds are retained and absent_since stays null.
    """
    retention.plan(
        register_raw,
        expected_register_sha256,
        policy_raw,
        expected_policy_sha256,
        as_of,
        expected_context_sha256,
        previous_raw=previous_raw,
        expected_previous_sha256=expected_previous_sha256,
    )
    current = retention.register(register_raw, expected_register_sha256)
    scope = retention.decoded(scope_raw, expected_scope_sha256)
    mapping = decoded(mapping_raw, expected_mapping_sha256)
    observed = decoded(probe_raw, expected_probe_sha256)
    retention.fields(
        mapping,
        "schema kind context_sha256 probe_sha256 collector_identity tool_sha256 "
        "data_device owner_uid copies",
    )
    need(
        mapping["schema"] == "opent1d.lt1-recovery-readback-map/1"
        and mapping["kind"] in ("invented", "observed")
        and mapping["context_sha256"] == expected_context_sha256
        and mapping["probe_sha256"] == expected_probe_sha256
        and type(mapping["data_device"]) is int
        and mapping["data_device"] >= 0
        and type(mapping["owner_uid"]) is int
        and mapping["owner_uid"] >= 0,
        "mapping identity",
    )
    retention.fields(
        observed,
        "schema kind observed_from observed_to status collector_identity tool_sha256 "
        "data_device queries local_readbacks coverage authorizations",
    )
    need(
        observed["schema"] == "opent1d.lt1-readonly-recovery-probe/1"
        and observed["kind"] == "point-observation"
        and observed["collector_identity"] == mapping["collector_identity"]
        and observed["tool_sha256"] == mapping["tool_sha256"]
        and type(observed["data_device"]) is int
        and observed["data_device"] == mapping["data_device"]
        and observed["coverage"] == probe.COVERAGE
        and all(v is False for v in observed["coverage"].values())
        and observed["authorizations"] == probe.AUTHORITY
        and all(v is False for v in observed["authorizations"].values()),
        "probe identity, Data device or authority",
    )
    source = observed["collector_identity"]
    retention.fields(source, "implementation python executable_sha256")
    need(
        isinstance(source["implementation"], dict)
        and source["implementation"]
        and all(
            isinstance(k, str)
            and k.startswith("experiments/")
            and not any(p in ("", ".", "..") for p in k.split("/"))
            and "\\" not in k
            and retention.sha(v)
            for k, v in source["implementation"].items()
        )
        and retention.sha(source["executable_sha256"])
        and isinstance(source["python"], str)
        and "experiments/lt1_diagnostic/recovery_probe.py" in source["implementation"],
        "collector source identity",
    )
    need(
        isinstance(observed["tool_sha256"], dict)
        and observed["tool_sha256"].keys() == probe.TOOLS.keys()
        and all(v is None or retention.sha(v) for v in observed["tool_sha256"].values()),
        "fixed tool identity",
    )
    now = retention.stamp(as_of)
    start, end = interval(observed["observed_from"], observed["observed_to"], now)
    rows = observed["local_readbacks"]
    need(isinstance(rows, list) and len(rows) <= probe.MAX_TARGETS, "target count")
    by_path, anchors, charged = {}, {}, 0
    for row in rows:
        need(isinstance(row, dict), "readback row")
        required = {"path", "observed_from", "observed_to", "state", "data_device_matches"}
        allowed = required | {
            "bytes",
            "sha256",
            "device",
            "inode",
            "uid",
            "mode",
            "mtime_ns",
            "ctime_ns",
            "error",
            "inspected_bytes",
        }
        need(required <= row.keys() <= allowed, "readback fields")
        path = row["path"]
        need(
            isinstance(path, str)
            and path.startswith("/")
            and len(path) <= 1024
            and "\0" not in path
            and path not in by_path,
            "unique exact path",
        )
        lower, upper = interval(row["observed_from"], row["observed_to"], now)
        need(start <= lower <= upper <= end, "readback outside acquisition interval")
        need(row["state"] in ("present", "absence-observed", "unknown"), "readback state")
        if row["state"] != "unknown":
            need(
                "error" not in row and "inspected_bytes" not in row,
                "known readback contains failure or partial-read metadata",
            )
            need(
                not path.startswith("//")
                and PurePosixPath(path).as_posix() == path
                and all(part not in ("", ".", "..") for part in path.split("/")[1:]),
                "known readback needs canonical lexical path",
            )
            need(
                row["data_device_matches"] is True
                and type(row.get("device")) is int
                and row["device"] == observed["data_device"],
                "readback Data device",
            )
        if row["state"] == "present":
            need(
                type(row.get("bytes")) is int
                and 0 <= row["bytes"] <= probe.FILE_LIMIT
                and retention.sha(row.get("sha256"))
                and type(row.get("uid")) is int
                and row["uid"] == mapping["owner_uid"]
                and type(row.get("inode")) is int
                and row["inode"] > 0
                and type(row.get("mode")) is int
                and row["mode"] in (0o400, 0o600),
                "present file evidence",
            )
            charged += row["bytes"]
        else:
            need(
                not ({"bytes", "sha256", "inode", "uid", "mode"} & row.keys()),
                "nonpresent row claims file bytes",
            )
            count = row.get("inspected_bytes", 0)
            need(type(count) is int and 0 <= count <= probe.FILE_LIMIT + 1, "read budget")
            charged += count
        by_path[path] = row
        anchors[path] = lower.replace(microsecond=0).strftime("%Y-%m-%dT%H:%M:%SZ")
    need(charged <= probe.TOTAL_LIMIT + probe.MAX_TARGETS, "aggregate read budget")
    queries = observed["queries"]
    need(isinstance(queries, dict) and queries.keys() == probe.COMMANDS.keys(), "fixed queries")
    need(
        all(
            isinstance(q, dict) and q.get("status") in ("response-observed", "unavailable")
            for q in queries.values()
        ),
        "query status",
    )
    for name, value in queries.items():
        _query(name, value, observed["tool_sha256"])
    complete = all(q["status"] == "response-observed" for q in queries.values()) and all(
        r["state"] != "unknown" for r in rows
    )
    need(observed["status"] == ("observed" if complete else "partial"), "probe status")
    copies = {
        c: (s, item)
        for s, subject in current["subjects"].items()
        for c, item in subject["copies"].items()
    }
    selected = mapping["copies"]
    need(
        isinstance(selected, dict)
        and len(selected) <= probe.MAX_TARGETS
        and selected.keys() <= copies.keys(),
        "registered mapping",
    )
    need(isinstance(scope, dict) and scope.get("kind") == mapping["kind"], "evidence kind")
    channels = scope.get("copy_channels")
    need(isinstance(channels, dict) and channels.keys() == copies.keys(), "complete copy scope")
    successor = copy.deepcopy(current)
    successor["previous_sha256"] = expected_register_sha256
    provenance, observations, used = {}, {}, set()
    for copy_id, selection in selected.items():
        retention.fields(selection, "subject channel path")
        subject, _ = copies[copy_id]
        path = selection["path"]
        need(
            selection["subject"] == subject
            and selection["channel"] == channels[copy_id]
            and selection["channel"] in ("live", "quarantine")
            and isinstance(path, str)
            and path in by_path
            and path not in used,
            "exact subject/channel/path mapping",
        )
        used.add(path)
        row = by_path[path]
        raw = encoded(
            {
                "schema": "opent1d.lt1-copy-readback-provenance/1",
                "kind": mapping["kind"],
                "context_sha256": expected_context_sha256,
                "probe_sha256": expected_probe_sha256,
                "mapping_sha256": expected_mapping_sha256,
                "copy": copy_id,
                "subject": subject,
                "channel": selection["channel"],
                "freshness_anchor_kind": "floor-interval-start-not-exact-instant",
                "readback": row,
            }
        )
        provenance[copy_id] = raw
        state = {"present": "present", "absence-observed": "absent", "unknown": "unknown"}[
            row["state"]
        ]
        if state != "unknown":
            successor["subjects"][subject]["copies"][copy_id] = {
                "state": row["state"],
                "evidence_sha256": digest(raw),
            }
        observations[copy_id] = {
            "subject": subject,
            "channel": selection["channel"],
            "state": state,
            "method": "namespace-readback",
            "observed_at": anchors[path],
            "absent_since": None,
            "evidence_sha256": digest(raw),
        }
    need(used == by_path.keys(), "unmapped acquired target")
    next_raw = encoded(successor)
    obs = {
        "schema": "opent1d.lt1-recovery-observations/1",
        "kind": mapping["kind"],
        "register_sha256": digest(next_raw),
        "scope_sha256": expected_scope_sha256,
        "context_sha256": expected_context_sha256,
        "copies": observations,
        "coverage": {
            c: {"complete": False, "observed_at": None, "evidence_sha256": None}
            for c in evidence.CHANNELS
        },
    }
    obs_raw = encoded(obs)
    assessment = evidence.assess(
        next_raw,
        digest(next_raw),
        policy_raw,
        expected_policy_sha256,
        scope_raw,
        expected_scope_sha256,
        obs_raw,
        digest(obs_raw),
        as_of,
        expected_context_sha256,
        previous_raw=register_raw,
        expected_previous_sha256=expected_register_sha256,
    )
    return {
        "schema": "opent1d.lt1-recovery-readback-proposal/1",
        "kind": mapping["kind"],
        "saved_or_approved": False,
        "register_raw": next_raw,
        "observations_raw": obs_raw,
        "provenance_raw": provenance,
        "assessment": assessment,
        "external_observations_independently_proved": False,
        **AUTHORITY,
    }
