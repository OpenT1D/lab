"""Strict saved-data comparison for Windows installer acceptance.

Restart expectations are computed from original bytes before maintenance and
must be bound with that snapshot. They are evidence, never live verification
authority. All unlisted changes, including report/data changes, remain failures.
"""

import hashlib
import json
import re
from pathlib import PurePosixPath

SCHEMA = "opent1d.windows-preservation/1"
TRANSITION = "native_reader_verified-to-recorded_verification"
_ID = r"[0-9a-f]{32}"
_RECORDS = (
    (rf"workspace/results/gui/(job-{_ID})/job.json", "opent1d.gui-job/1"),
    (
        rf"workspace/results/gui/observations/archives/(obs-study-{_ID})/record.json",
        "opent1d.gui-observation-entry/1",
    ),
    (
        rf"workspace/results/gui/sampling/archives/(sam-study-{_ID})/record.json",
        "opent1d.gui-sampling-entry/1",
    ),
)


def identity(raw):
    return {"bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest()}


def _name(value):
    if not isinstance(value, str) or "\\" in value or ":" in value or "\0" in value:
        raise ValueError("Invalid snapshot path")
    path = PurePosixPath(value)
    if (
        path.is_absolute()
        or len(path.parts) < 2
        or path.parts[0] not in {"workspace", "durable"}
        or any(part in {".", ".."} for part in path.parts)
        or path.as_posix() != value
    ):
        raise ValueError("Invalid snapshot path")
    return value


def _record_kind(relative):
    for pattern, schema in _RECORDS:
        match = re.fullmatch(pattern, relative)
        if match:
            return schema, match[1]
    return None


def _unique(pairs):
    value = {}
    for key, item in pairs:
        if key in value:
            raise ValueError("Duplicate bookkeeping field")
        value[key] = item
    return value


def _encode(value):
    # This is the persisted GUI journal/observation encoding, not a semantic
    # comparison: even another harmless formatting change must fail the check.
    return json.dumps(value, sort_keys=True, indent=2, allow_nan=False).encode() + b"\n"


def restart_expectation(relative, raw):
    """Return one exact permitted after-identity, or None for strict bytes only.

    Only canonical, completed observation/sampling records and closed GUI jobs
    can acquire this expectation. A nested value with the same spelling, other
    verification transitions, and every other field remain byte-bound.
    """
    kind = _record_kind(_name(relative))
    if kind is None or len(raw) > 8 * 1024 * 1024:
        return None
    try:
        value = json.loads(raw, object_pairs_hook=_unique)
        if not isinstance(value, dict) or raw != _encode(value):
            return None
        schema, record_id = kind
        if (
            value.get("schema") != schema
            or value.get("id") != record_id
            or value.get("verification") != "native_reader_verified"
        ):
            return None
        if schema == "opent1d.gui-job/1":
            if (
                value.get("state") not in {"completed", "failed", "cancelled"}
                or type(value.get("exit_code")) is not int
                or value.get("pid", "missing") is not None
                or value.get("cleanup_forced") is not False
                or value.get("remaining_owned_processes") != []
            ):
                return None
        elif value.get("state") != "completed":
            return None
        value["verification"] = "recorded_verification"
        return {
            "transition": TRANSITION,
            "schema": schema,
            "record_id": record_id,
            "before": identity(raw),
            "after": identity(_encode(value)),
        }
    except (ValueError, TypeError, UnicodeError, RecursionError):
        return None


def _inventory(value):
    if not isinstance(value, dict) or not value:
        raise ValueError("A nonempty saved-data inventory is required")
    for name, record in value.items():
        _name(name)
        if (
            not isinstance(record, dict)
            or set(record) != {"bytes", "sha256"}
            or type(record["bytes"]) is not int
            or record["bytes"] < 0
            or not isinstance(record["sha256"], str)
            or not re.fullmatch(r"[0-9a-f]{64}", record["sha256"])
        ):
            raise ValueError("Invalid saved-data byte identity")


def compare_preservation(before, after, *, expected_bookkeeping=None):
    """Compare measured inventories against a separately hash-bound snapshot.

    New files are counted separately, as in the original acceptance protocol.
    The caller must validate filesystem paths/reads and bind the complete before
    snapshot, including expectations, before any installer or desktop restart.
    """
    _inventory(before)
    _inventory(after)
    expected = {} if expected_bookkeeping is None else expected_bookkeeping
    if not isinstance(expected, dict) or not set(expected) <= set(before):
        raise ValueError("Bookkeeping expectation is not in the original inventory")
    for name, item in expected.items():
        if (
            not isinstance(item, dict)
            or set(item) != {"transition", "schema", "record_id", "before", "after"}
            or item["transition"] != TRANSITION
            or _record_kind(name) != (item["schema"], item["record_id"])
            or item["before"] != before[name]
            or item["after"] == item["before"]
        ):
            raise ValueError("Bookkeeping expectation differs from its bound original")
        _inventory({name: item["after"]})
    changed, missing, allowed = [], [], []
    unchanged = 0
    for name, record in before.items():
        if name not in after:
            missing.append(name)
        elif after[name] == record:
            unchanged += 1
        elif name in expected and after[name] == expected[name]["after"]:
            allowed.append({"path": name, **expected[name]})
        else:
            changed.append(name)
    if changed or missing:
        raise ValueError(
            "Saved data changed or disappeared: "
            + json.dumps({"changed": sorted(changed), "missing": sorted(missing)}, sort_keys=True)
        )
    return {
        "schema": SCHEMA,
        "original_files": len(before),
        "original_files_unchanged": unchanged,
        "expected_bookkeeping_changes": sorted(allowed, key=lambda item: item["path"]),
        "additional_files": len(set(after) - set(before)),
        "all_original_bytes_identical": not allowed,
        "preservation_passed": True,
        "fresh_verification_claim": False,
    }
