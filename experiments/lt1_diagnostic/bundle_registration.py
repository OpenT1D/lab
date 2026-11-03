"""Unsaved aggregate bundle-copy accounting against an exact existing register.

A verified bundle contains private metadata about every old subject. One explicit
new copy ID per subject conservatively accounts for that whole derived bundle;
this is neither a new origin nor proof that all copies have been registered.
"""

import copy
from pathlib import Path

from experiments.lt1_diagnostic import recovery_readback as wire
from experiments.lt1_diagnostic import retention, review_bundle
from experiments.lt1_diagnostic.control_identity import identity

AUTHORITY = dict(review_bundle.AUTHORITY)
PROVENANCE_LIMIT = 4 * 1024 * 1024


def need(ok, reason):
    if not ok:
        raise ValueError("LT1 bundle registration refused: " + reason)


def source_identity():
    return identity(__file__)


def propose_registration(
    bundle_path,
    expected_manifest_sha256,
    register_raw,
    expected_register_sha256,
    policy_raw,
    expected_policy_sha256,
    allocation_raw,
    expected_allocation_sha256,
    *,
    as_of,
    expected_context_sha256,
    previous_raw=None,
    expected_previous_sha256=None,
):
    """Return private proposal/provenance bytes; never save, activate or admit.

    Validate supplied register/policy/history and allocation before private path
    intake. The stored BASE register must match; its unapproved recovery proposal
    supplies no old copy states. External identity pins do not prove observation
    truth, complete restore coverage, physical erasure or a live host boundary.
    """
    old_plan = retention.plan(
        register_raw,
        expected_register_sha256,
        policy_raw,
        expected_policy_sha256,
        as_of,
        expected_context_sha256,
        previous_raw=previous_raw,
        expected_previous_sha256=expected_previous_sha256,
    )
    base = retention.register(register_raw, expected_register_sha256)
    allocation = wire.decoded(allocation_raw, expected_allocation_sha256)
    retention.fields(
        allocation,
        "schema kind manifest_sha256 register_sha256 policy_sha256 context_sha256 "
        "source_identity copies",
    )
    need(
        allocation["schema"] == "opent1d.lt1-bundle-copy-allocation/1"
        and allocation["kind"] in ("invented", "observed")
        and retention.sha(expected_manifest_sha256)
        and allocation["manifest_sha256"] == expected_manifest_sha256
        and allocation["register_sha256"] == expected_register_sha256
        and allocation["policy_sha256"] == expected_policy_sha256
        and allocation["context_sha256"] == expected_context_sha256,
        "allocation input identities",
    )
    assigned = allocation["copies"]
    need(
        isinstance(assigned, dict) and assigned.keys() == base["subjects"].keys(),
        "exactly one allocation per existing subject",
    )
    for copy_id in assigned.values():
        retention.identifier(copy_id)
    old_ids = {copy_id for subject in base["subjects"].values() for copy_id in subject["copies"]}
    need(
        len(set(assigned.values())) == len(assigned) and not (set(assigned.values()) & old_ids),
        "new globally unused copy IDs",
    )
    need(len(old_ids) + len(assigned) <= retention.MAX_COPIES, "aggregate copy bound")
    proposed = copy.deepcopy(base)
    proposed["previous_sha256"] = expected_register_sha256
    for name, copy_id in assigned.items():
        proposed["subjects"][name]["copies"][copy_id] = {
            "state": "present",
            "evidence_sha256": "0" * 64,
        }
    for key in ("all_copies_registered", "recovery_scope_reviewed", "processes_stopped"):
        proposed["coverage"][key] = False
    # Evidence hashes have fixed length, so this exact size bound precedes reads.
    need(len(wire.encoded(proposed)) <= retention.LIMIT, "successor register byte bound")
    source = source_identity()
    need(allocation["source_identity"] == source, "reviewed registration source identity")

    bundle_path = Path(bundle_path)
    report, snapshot = review_bundle._inspect(
        bundle_path,
        expected_manifest_sha256,
        expected_register_sha256,
        expected_context_sha256,
        as_of,
    )
    need(
        snapshot[0]["register.json"] == register_raw
        and snapshot[0]["policy.json"] == policy_raw
        and report["intent"]["kind"] == allocation["kind"],
        "exact stored base, policy and evidence kind",
    )
    registration_source_sha = wire.digest(wire.encoded(source))
    bundle_source_sha = wire.digest(wire.encoded(report["intent"]["source_identity"]))
    provenance, provenance_bytes = {}, 0
    for name, copy_id in sorted(assigned.items()):
        subject = base["subjects"][name]
        raw = wire.encoded(
            {
                "schema": "opent1d.lt1-aggregate-bundle-copy/1",
                "kind": allocation["kind"],
                "accounting": "conservative-whole-derived-bundle-per-existing-subject",
                "subject": name,
                "copy": copy_id,
                "manifest_sha256": expected_manifest_sha256,
                "base_register_sha256": expected_register_sha256,
                "policy_sha256": expected_policy_sha256,
                "context_sha256": expected_context_sha256,
                "allocation_sha256": expected_allocation_sha256,
                "registration_source_identity_sha256": registration_source_sha,
                "bundle_source_identity_sha256": bundle_source_sha,
                "bundle_path": str(bundle_path),
                "bundle_root": snapshot[2],
                "bundle_leaf": report["intent"]["output_name"],
                "as_of": as_of,
                "inherited": {
                    key: subject[key]
                    for key in ("retained_since", "origin_evidence_sha256", "hold")
                },
            }
        )
        provenance_bytes += len(raw)
        need(provenance_bytes <= PROVENANCE_LIMIT, "aggregate provenance byte bound")
        provenance[copy_id] = raw
        proposed["subjects"][name]["copies"][copy_id]["evidence_sha256"] = wire.digest(raw)
    next_raw = wire.encoded(proposed)
    next_sha = wire.digest(next_raw)
    assessment = retention.plan(
        next_raw,
        next_sha,
        policy_raw,
        expected_policy_sha256,
        as_of,
        expected_context_sha256,
        previous_raw=register_raw,
        expected_previous_sha256=expected_register_sha256,
    )
    need(assessment["deadlines"] == old_plan["deadlines"], "inherited deadlines changed")
    need(source_identity() == source, "registration source changed")
    with review_bundle._opened(bundle_path) as (path, fd):
        need(
            review_bundle._snapshot(path, fd, expected_manifest_sha256) == snapshot,
            "bundle changed during registration",
        )
    return {
        "schema": "opent1d.lt1-bundle-registration-proposal/1",
        "kind": allocation["kind"],
        "manifest_sha256": expected_manifest_sha256,
        "base_register_sha256": expected_register_sha256,
        "allocation_sha256": expected_allocation_sha256,
        "source_identity": source,
        "register_raw": next_raw,
        "register_sha256": next_sha,
        "provenance_raw": provenance,
        "assessment": assessment,
        "saved_or_approved": False,
        "provenance_retention_required": True,
        "external_observations_independently_proved": False,
        **AUTHORITY,
        **review_bundle.COPY_SCOPE,
    }
