"""Unsaved explicit bundle-copy reconciliation; no removal or admission.

Retained registration bytes bind the deleted bundle; it is never reopened for
registration replay. Namespace absence is separate from timing, recovery scope
and effective erasure. All supplied paths remain private caller metadata.
"""

import copy
from pathlib import PurePosixPath

from experiments.lt1_diagnostic import bundle_registration as registration
from experiments.lt1_diagnostic.control_identity import identity

retention, bundle, wire = registration.retention, registration.review_bundle, registration.wire
removal = bundle.removal
AUTHORITY = {
    **bundle.AUTHORITY,
    "register_activated": False,
    "absence_time_established": False,
    "retention_deadline_compliance_verified": False,
    "external_observations_independently_proved": False,
}
PROVENANCE_LIMIT = registration.PROVENANCE_LIMIT


def need(ok, reason):
    if not ok:
        raise ValueError("LT1 bundle reconciliation refused: " + reason)


def source_identity():
    return identity(__file__)


def bounded(raw, expected, limit):
    need(isinstance(raw, bytes) and 0 < len(raw) <= limit, "input byte bound")
    return wire.decoded(raw, expected)


def propose_reconciliation(
    *,
    base_raw,
    expected_base_sha256,
    registration_raw,
    expected_registration_sha256,
    policy_raw,
    expected_policy_sha256,
    allocation_raw,
    expected_allocation_sha256,
    provenance_raw,
    expected_provenance_sha256,
    manifest_raw,
    expected_manifest_sha256,
    intent_raw,
    expected_intent_sha256,
    request_raw,
    expected_request_sha256,
    context_raw,
    expected_context_sha256,
    journal_raw,
    expected_journal_sha256,
    outer_raw,
    expected_outer_sha256,
    as_of,
    expected_reader_identity,
    previous_raw=None,
    expected_previous_sha256=None,
):
    """Validate retained bytes before namespace intake and return an unsaved proposal.

    Only allocated aggregate-copy IDs can change, and only for complete strict
    removal readback. Incomplete evidence returns the original registration bytes.
    The caller pins observations; a matching hash does not prove their truth.
    """
    source = source_identity()
    need(source == expected_reader_identity, "current reconciliation reader identity")
    base_plan = retention.plan(
        base_raw,
        expected_base_sha256,
        policy_raw,
        expected_policy_sha256,
        as_of,
        expected_context_sha256,
        previous_raw=previous_raw,
        expected_previous_sha256=expected_previous_sha256,
    )
    base = retention.register(base_raw, expected_base_sha256)
    current = retention.register(registration_raw, expected_registration_sha256)
    current_plan = retention.plan(
        registration_raw,
        expected_registration_sha256,
        policy_raw,
        expected_policy_sha256,
        as_of,
        expected_context_sha256,
        previous_raw=base_raw,
        expected_previous_sha256=expected_base_sha256,
    )
    allocation = bounded(allocation_raw, expected_allocation_sha256, retention.LIMIT)
    retention.fields(
        allocation,
        "schema kind manifest_sha256 register_sha256 policy_sha256 "
        "context_sha256 source_identity copies",
    )
    registration_source = registration.source_identity()
    need(
        allocation["schema"] == "opent1d.lt1-bundle-copy-allocation/1"
        and allocation["kind"] in ("invented", "observed")
        and allocation["manifest_sha256"] == expected_manifest_sha256
        and allocation["register_sha256"] == expected_base_sha256
        and allocation["policy_sha256"] == expected_policy_sha256
        and allocation["context_sha256"] == expected_context_sha256
        and allocation["source_identity"] == registration_source,
        "registration allocation binding",
    )
    assigned = allocation["copies"]
    need(
        isinstance(assigned, dict) and assigned.keys() == base["subjects"].keys(),
        "exact subject allocation",
    )
    for copy_id in assigned.values():
        retention.identifier(copy_id)
    ids = set(assigned.values())
    old_ids = {key for subject in base["subjects"].values() for key in subject["copies"]}
    need(len(ids) == len(assigned) and not ids & old_ids, "unused distinct allocated copies")
    need(
        isinstance(provenance_raw, dict)
        and isinstance(expected_provenance_sha256, dict)
        and provenance_raw.keys() == expected_provenance_sha256.keys() == ids
        and all(isinstance(value, bytes) for value in provenance_raw.values())
        and sum(map(len, provenance_raw.values())) <= PROVENANCE_LIMIT,
        "complete bounded provenance map",
    )
    manifest = bounded(manifest_raw, expected_manifest_sha256, removal.REQUEST_LIMIT)
    retention.fields(manifest, "schema files")
    members = manifest["files"]
    need(
        manifest["schema"] == "opent1d.lt1-review-bundle/1"
        and isinstance(members, dict)
        and 0 < len(members) < removal.MAX_FILES
        and bundle.MANIFEST not in members,
        "retained closed manifest",
    )
    for name, record in members.items():
        removal.safe_name(name)
        retention.fields(record, "bytes sha256")
        need(
            type(record["bytes"]) is int
            and 0 <= record["bytes"] <= removal.FILE_LIMIT
            and retention.sha(record["sha256"]),
            "manifest member identity",
        )
    need(
        len(manifest_raw) + sum(v["bytes"] for v in members.values()) <= removal.TOTAL_LIMIT,
        "manifest aggregate bound",
    )
    intent = bounded(intent_raw, expected_intent_sha256, removal.FILE_LIMIT)
    retention.fields(
        intent,
        "schema kind output_name source_identity as_of context_sha256 inputs subjects "
        "new_bundle_copy_registration_required global_copy_coverage_verified",
    )
    bundle_source = bundle.source_identity()
    need(
        intent["schema"] == "opent1d.lt1-review-bundle-intent/1"
        and intent["kind"] == allocation["kind"]
        and intent["source_identity"] == bundle_source
        and intent["context_sha256"] == expected_context_sha256
        and intent["new_bundle_copy_registration_required"] is True
        and intent["global_copy_coverage_verified"] is False
        and retention.stamp(intent["as_of"]) <= retention.stamp(as_of),
        "retained bundle intent",
    )
    removal.safe_name(intent["output_name"])
    need(not intent["output_name"].endswith(".pending"), "published bundle leaf")
    inputs = intent["inputs"]
    expected_inputs = {name + ".json" for name in bundle.INPUTS}
    if previous_raw is not None:
        expected_inputs.add("previous.json")
    need(isinstance(inputs, dict) and set(inputs) == expected_inputs, "fixed stored inputs")
    need(
        all(members.get(name) == record for name, record in inputs.items()),
        "intent/manifest input map",
    )
    fixed_members = expected_inputs | {
        bundle.INTENT,
        "proposed-register.json",
        "observations.json",
        "assessment.json",
        "provenance-index.json",
    }
    copied = set(members) - fixed_members
    need(
        set(members) == fixed_members | copied
        and fixed_members <= members.keys()
        and len(copied) <= len(old_ids)
        and copied == {f"copy-{index:04d}.json" for index in range(len(copied))},
        "fixed bundle member roles",
    )
    retained = {"register.json": base_raw, "policy.json": policy_raw, bundle.INTENT: intent_raw}
    if previous_raw is not None:
        retained["previous.json"] = previous_raw
    for name, raw in retained.items():
        need(
            members.get(name) == {"bytes": len(raw), "sha256": wire.digest(raw)},
            "retained base/policy/history/intent identity",
        )
    subjects = {
        name: {
            **{key: subject[key] for key in ("retained_since", "origin_evidence_sha256", "hold")},
            "copies": sorted(subject["copies"]),
        }
        for name, subject in base["subjects"].items()
    }
    need(
        wire.encoded(intent["subjects"]) == wire.encoded(subjects),
        "intent preserves original subjects",
    )
    request = bounded(request_raw, expected_request_sha256, removal.REQUEST_LIMIT)
    need(
        isinstance(context_raw, bytes)
        and len(context_raw) <= removal.REQUEST_LIMIT
        and wire.digest(context_raw) == expected_context_sha256,
        "context identity",
    )
    # This existing validator checks bytes/host/source/types only, without opening paths.
    request = removal._request(request_raw, context_raw)
    request_members = {
        name: {"bytes": value["bytes"], "sha256": value["sha256"]}
        for name, value in request["files"].items()
    }
    need(
        request_members
        == {
            **members,
            bundle.MANIFEST: {"bytes": len(manifest_raw), "sha256": expected_manifest_sha256},
        },
        "complete removal/manifest inventory",
    )
    need(
        request["kind"] == ("invented" if allocation["kind"] == "invented" else "private-data")
        and request["context_sha256"] == expected_context_sha256,
        "removal origin/context",
    )
    root = request["root"]
    path = PurePosixPath(root["path"])
    need(
        str(path) == root["path"] and ".." not in path.parts and path.name == intent["output_name"],
        "exact published root/leaf",
    )
    prototype = copy.deepcopy(base)
    prototype["previous_sha256"] = expected_base_sha256
    for key in ("all_copies_registered", "recovery_scope_reviewed", "processes_stopped"):
        prototype["coverage"][key] = False
    registration_at = None
    for name, copy_id in sorted(assigned.items()):
        raw = provenance_raw[copy_id]
        provenance = bounded(raw, expected_provenance_sha256[copy_id], PROVENANCE_LIMIT)
        need(isinstance(provenance, dict), "aggregate-copy provenance object")
        if registration_at is None:
            registration_at = provenance.get("as_of")
        expected = {
            "schema": "opent1d.lt1-aggregate-bundle-copy/1",
            "kind": allocation["kind"],
            "accounting": "conservative-whole-derived-bundle-per-existing-subject",
            "subject": name,
            "copy": copy_id,
            "manifest_sha256": expected_manifest_sha256,
            "base_register_sha256": expected_base_sha256,
            "policy_sha256": expected_policy_sha256,
            "context_sha256": expected_context_sha256,
            "allocation_sha256": expected_allocation_sha256,
            "registration_source_identity_sha256": wire.digest(wire.encoded(registration_source)),
            "bundle_source_identity_sha256": wire.digest(wire.encoded(bundle_source)),
            "bundle_path": root["path"],
            "bundle_root": {key: root[key] for key in ("device", "inode", "uid")},
            "bundle_leaf": intent["output_name"],
            "as_of": provenance.get("as_of"),
            "inherited": {
                key: base["subjects"][name][key]
                for key in ("retained_since", "origin_evidence_sha256", "hold")
            },
        }
        need(
            wire.encoded(provenance) == wire.encoded(expected)
            and provenance["as_of"] == registration_at
            and retention.stamp(intent["as_of"])
            <= retention.stamp(provenance["as_of"])
            <= retention.stamp(as_of),
            "exact aggregate-copy provenance",
        )
        prototype["subjects"][name]["copies"][copy_id] = {
            "state": "present",
            "evidence_sha256": expected_provenance_sha256[copy_id],
        }
    need(
        current == prototype and current_plan["deadlines"] == base_plan["deadlines"],
        "exact retained registration delta",
    )
    outer = bounded(outer_raw, expected_outer_sha256, removal.REQUEST_LIMIT)
    need(isinstance(outer, dict), "outer receipt object")
    need(
        isinstance(journal_raw, bytes)
        and 0 < len(journal_raw) <= removal.JOURNAL_LIMIT
        and wire.digest(journal_raw) == expected_journal_sha256,
        "bounded journal identity",
    )
    need(source_identity() == source, "reconciliation source changed")
    args = (request_raw, expected_request_sha256, context_raw, expected_journal_sha256, outer)
    readback = removal.inspect(*args)
    completed = readback["status"] == "completed"
    successor = copy.deepcopy(current)
    next_provenance = {}
    bindings = {
        "base": expected_base_sha256,
        "registration": expected_registration_sha256,
        "policy": expected_policy_sha256,
        "allocation": expected_allocation_sha256,
        "manifest": expected_manifest_sha256,
        "intent": expected_intent_sha256,
        "request": expected_request_sha256,
        "context": expected_context_sha256,
        "journal": expected_journal_sha256,
        "outer": expected_outer_sha256,
        "reader_identity": wire.digest(wire.encoded(source)),
    }
    if completed:
        successor["previous_sha256"] = expected_registration_sha256
        for name, copy_id in sorted(assigned.items()):
            raw = wire.encoded(
                {
                    "schema": "opent1d.lt1-bundle-copy-reconciliation/1",
                    "kind": allocation["kind"],
                    "subject": name,
                    "copy": copy_id,
                    "state": "absence-observed",
                    "assessment_at": as_of,
                    "bindings": bindings,
                    "registration_provenance_sha256": expected_provenance_sha256[copy_id],
                    "absence_time_established": False,
                    "retention_deadline_compliance_verified": False,
                }
            )
            next_provenance[copy_id] = raw
            successor["subjects"][name]["copies"][copy_id] = {
                "state": "absence-observed",
                "evidence_sha256": wire.digest(raw),
            }
    need(
        sum(map(len, next_provenance.values())) <= PROVENANCE_LIMIT,
        "successor provenance byte bound",
    )
    next_raw = wire.encoded(successor) if completed else registration_raw
    need(len(next_raw) <= retention.LIMIT, "successor register byte bound")
    assessment = retention.plan(
        next_raw,
        wire.digest(next_raw),
        policy_raw,
        expected_policy_sha256,
        as_of,
        expected_context_sha256,
        previous_raw=registration_raw if completed else base_raw,
        expected_previous_sha256=expected_registration_sha256
        if completed
        else expected_base_sha256,
    )
    need(assessment["deadlines"] == current_plan["deadlines"], "inherited deadlines changed")
    need(source_identity() == source, "reconciliation source changed")
    need(removal.inspect(*args) == readback, "removal evidence changed during reconciliation")
    return {
        "schema": "opent1d.lt1-bundle-reconciliation-proposal/1",
        "kind": allocation["kind"],
        "status": "proposed" if completed else "incomplete",
        "reader_identity": source,
        "bindings": bindings,
        "removal_readback": readback,
        "register_raw": next_raw,
        "register_sha256": wire.digest(next_raw),
        "provenance_raw": next_provenance,
        "assessment": assessment,
        "saved_or_approved": False,
        "new_revision_proposed": completed,
        "provenance_retention_required": True,
        **AUTHORITY,
        **bundle.COPY_SCOPE,
    }
