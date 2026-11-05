"""Read-only private retention planning; never deletes or grants admission."""

import hashlib
import json
import re
from datetime import UTC, datetime, timedelta

from experiments.lt1_diagnostic.archive_preflight import unique_object

LIMIT = 1024 * 1024
MAX_SUBJECTS = 4096
MAX_COPIES = 8192


def require(ok, reason):
    if not ok:
        raise ValueError("LT1 retention refused: " + reason)


def fields(value, names):
    require(isinstance(value, dict) and set(value) == set(names.split()), "fields")


def sha(value):
    return isinstance(value, str) and re.fullmatch("[a-f0-9]{64}", value) is not None


def stamp(value):
    require(
        isinstance(value, str) and re.fullmatch(r"\d{4}-\d\d-\d\dT\d\d:\d\d:\d\dZ", value),
        "UTC timestamp",
    )
    return datetime.strptime(value, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=UTC)


def identifier(value):
    require(
        isinstance(value, str) and re.fullmatch("[a-z0-9][a-z0-9-]{0,63}", value),
        "opaque identifier",
    )


def decoded(raw, expected):
    require(
        isinstance(raw, bytes)
        and len(raw) <= LIMIT
        and sha(expected)
        and hashlib.sha256(raw).hexdigest() == expected,
        "external byte identity",
    )
    return json.loads(raw, object_pairs_hook=unique_object)


def register(raw, expected):
    value = decoded(raw, expected)
    fields(value, "schema policy_sha256 previous_sha256 subjects coverage")
    require(value["schema"] == "opent1d.lt1-retention-register/1", "register schema")
    require(sha(value["policy_sha256"]), "registered policy identity")
    require(value["previous_sha256"] is None or sha(value["previous_sha256"]), "predecessor")
    subjects = value["subjects"]
    require(isinstance(subjects, dict) and 0 < len(subjects) <= MAX_SUBJECTS, "subject count")
    copy_ids = set()
    for subject_id, subject in subjects.items():
        identifier(subject_id)
        fields(subject, "retained_since origin_evidence_sha256 hold copies")
        require(type(subject["hold"]) is bool, "hold")
        if subject["retained_since"] is None:
            require(subject["origin_evidence_sha256"] is None, "unknown origin")
        else:
            stamp(subject["retained_since"])
            require(sha(subject["origin_evidence_sha256"]), "origin evidence")
        copies = subject["copies"]
        require(isinstance(copies, dict) and 0 < len(copies) <= MAX_COPIES, "copy count")
        for copy_id, copy in copies.items():
            identifier(copy_id)
            require(copy_id not in copy_ids, "duplicate copy identity")
            copy_ids.add(copy_id)
            require(len(copy_ids) <= MAX_COPIES, "aggregate copy count")
            fields(copy, "state evidence_sha256")
            require(copy["state"] in {"present", "absence-observed"}, "copy state")
            require(sha(copy["evidence_sha256"]), "copy evidence")
    coverage = value["coverage"]
    fields(
        coverage,
        "all_copies_registered recovery_scope_reviewed recoverable_until "
        "processes_stopped context_sha256",
    )
    require(
        all(
            type(coverage[key]) is bool
            for key in ("all_copies_registered", "recovery_scope_reviewed", "processes_stopped")
        )
        and sha(coverage["context_sha256"]),
        "coverage evidence",
    )
    if coverage["recoverable_until"] is not None:
        stamp(coverage["recoverable_until"])
    return value


def plan(
    raw,
    expected_sha256,
    policy_raw,
    expected_policy_sha256,
    as_of,
    expected_context_sha256,
    *,
    previous_raw=None,
    expected_previous_sha256=None,
):
    """Assess externally reviewed records, not their truth or deletion permission.

    Stable subjects represent one private object across copies and revisions.
    Independently created outputs are separate subjects. No filesystem timestamp
    supplies an origin automatically, and no personal record is read here.
    """
    policy = decoded(policy_raw, expected_policy_sha256)
    fields(policy, "schema maximum_age_seconds extensions_allowed exports_allowed")
    require(
        policy["schema"] == "opent1d.lt1-retention-policy/1"
        and type(policy["maximum_age_seconds"]) is int
        and 0 < policy["maximum_age_seconds"] <= 366 * 24 * 3600
        and policy["extensions_allowed"] is False
        and policy["exports_allowed"] is False,
        "private policy",
    )
    current = register(raw, expected_sha256)
    require(current["policy_sha256"] == expected_policy_sha256, "policy identity")
    require(
        sha(expected_context_sha256)
        and current["coverage"]["context_sha256"] == expected_context_sha256,
        "stale host/storage/source context",
    )
    subjects = current["subjects"]
    if current["previous_sha256"] is None:
        require(previous_raw is None and expected_previous_sha256 is None, "unexpected predecessor")
    else:
        require(current["previous_sha256"] == expected_previous_sha256, "predecessor identity")
        previous = register(previous_raw, expected_previous_sha256)
        require(previous["policy_sha256"] == current["policy_sha256"], "policy lineage")
        require(previous["subjects"].keys() <= subjects.keys(), "dropped retention subject")
        for subject_id, old in previous["subjects"].items():
            new = subjects[subject_id]
            require(old["copies"].keys() <= new["copies"].keys(), "dropped retained copy")
            if old["retained_since"] is not None:
                require(
                    new["retained_since"] is not None
                    and stamp(new["retained_since"]) <= stamp(old["retained_since"]),
                    "origin extension",
                )
    now = stamp(as_of)
    coverage = current["coverage"]
    blockers, actions, deadlines, expired = [], [], {}, []
    for key in ("all_copies_registered", "recovery_scope_reviewed", "processes_stopped"):
        if coverage[key] is not True:
            blockers.append(key)
    for subject_id, subject in subjects.items():
        if subject["hold"]:
            blockers.append(subject_id + ":hold-does-not-extend-retention")
        origin = subject["retained_since"]
        if origin is None:
            blockers.append(subject_id + ":origin-unestablished")
            deadlines[subject_id] = None
            continue
        require(stamp(origin) <= now, "future origin")
        deadline = stamp(origin) + timedelta(seconds=policy["maximum_age_seconds"])
        deadlines[subject_id] = deadline.strftime("%Y-%m-%dT%H:%M:%SZ")
        if (
            coverage["recoverable_until"] is not None
            and stamp(coverage["recoverable_until"]) > deadline
        ):
            blockers.append(subject_id + ":recovery-outlives-deadline")
        if now >= deadline:
            expired.append(subject_id)
            actions.extend(
                {"subject": subject_id, "copy": copy_id, "action": "remove-and-verify"}
                for copy_id, copy in subject["copies"].items()
                if copy["state"] == "present"
            )
    return {
        "schema": "opent1d.lt1-retention-plan/1",
        "as_of": as_of,
        "register_sha256": expected_sha256,
        "policy_sha256": expected_policy_sha256,
        "context_sha256": expected_context_sha256,
        "status": "blocked"
        if blockers
        else "removal-review-needed"
        if actions
        else "expired-absence-review-needed"
        if expired
        else "within-recorded-window",
        "blockers": blockers,
        "deadlines": deadlines,
        "expired_subjects": expired,
        "actions": actions,
        "effective_erasure_verified": False,
        "deletion_authorized": False,
        "setup_admitted": False,
        "native_execution_authorized": False,
    }
