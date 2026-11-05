"""Unsaved one-copy proposal, preserving origin clocks and recovery blockers."""

import copy

from experiments.lt1_diagnostic import native_tree_removal as tree
from experiments.lt1_diagnostic import recovery_evidence, retention
from experiments.lt1_diagnostic.control_identity import identity

RECORD_ROLES = ("request", "control", "journal", "launch-log", "outer", "readback")


def source_identity():
    return identity(__file__)


def propose(
    *,
    register_raw,
    expected_register_sha256,
    policy_raw,
    expected_policy_sha256,
    provenance_raw,
    expected_provenance_sha256,
    request_raw,
    expected_request_sha256,
    context_raw,
    journal_raw,
    expected_journal_sha256,
    outer_receipt,
    expected_outer_sha256,
    audit,
    expected_audit_sha256,
    reader_audit,
    allocation_raw,
    expected_allocation_sha256,
    record_copy_ids,
    as_of,
    previous_raw=None,
    expected_previous_sha256=None,
    recovery_inputs=None,
    invented=False,
):
    """Only complete strict readback can change the allocated original copy.

    New record allocations are returned separately and remain unregistered.
    Therefore coverage is conservatively false in a proposed successor; no
    retention, timing, restore or physical-erasure conclusion follows.
    """
    source = source_identity()
    r = tree.request(request_raw, context_raw, reader_audit, invented=invented)
    tree.decoded(request_raw, expected_request_sha256)
    tree.need(
        tree.digest(journal_raw) == expected_journal_sha256
        and len(journal_raw) <= tree.JOURNAL_LIMIT,
        "retained journal bytes",
    )
    current = retention.register(register_raw, expected_register_sha256)
    current_plan = retention.plan(
        register_raw,
        expected_register_sha256,
        policy_raw,
        expected_policy_sha256,
        as_of,
        tree.digest(context_raw),
        previous_raw=previous_raw,
        expected_previous_sha256=expected_previous_sha256,
    )
    allocation = tree.decoded(allocation_raw, expected_allocation_sha256)
    retention.fields(
        allocation, "schema kind role subject copy root producer context_sha256 inherited"
    )
    tree.need(
        allocation["schema"] == "opent1d.lt1-native-tree-copy-allocation/1"
        and allocation["kind"] == r["kind"]
        and allocation["role"] == r["role"]
        and allocation["subject"] == r["subject"]
        and allocation["copy"] == r["copy"]
        and allocation["root"] == r["root"]
        and allocation["producer"] == r["producer"]
        and allocation["context_sha256"] == r["context_sha256"]
        and r["allocation_sha256"] == expected_allocation_sha256,
        "exact externally allocated physical root/copy",
    )
    subject = current["subjects"].get(r["subject"])
    tree.need(subject is not None and r["copy"] in subject["copies"], "registered allocated copy")
    inherited = {k: subject[k] for k in ("retained_since", "origin_evidence_sha256", "hold")}
    tree.need(allocation["inherited"] == inherited, "unchanged inherited origin/hold")
    tree.need(
        type(provenance_raw) is dict
        and type(expected_provenance_sha256) is dict
        and provenance_raw.keys() == expected_provenance_sha256.keys(),
        "retained provenance map",
    )
    all_ids = {copy_id for s in current["subjects"].values() for copy_id in s["copies"]}
    tree.need(
        set(provenance_raw) <= all_ids
        and r["copy"] in provenance_raw
        and all(type(v) is bytes for v in provenance_raw.values())
        and sum(len(v) for v in provenance_raw.values()) <= tree.LIMIT,
        "bounded copy provenance",
    )
    for copy_id, raw in provenance_raw.items():
        tree.need(
            type(raw) is bytes and tree.digest(raw) == expected_provenance_sha256[copy_id],
            "external provenance identity",
        )
    target_provenance = tree.decoded(
        provenance_raw[r["copy"]], expected_provenance_sha256[r["copy"]]
    )
    tree.need(
        target_provenance == allocation
        and subject["copies"][r["copy"]]
        == {"state": "present", "evidence_sha256": expected_provenance_sha256[r["copy"]]},
        "registered root provenance",
    )
    tree.need(
        type(record_copy_ids) is dict and set(record_copy_ids) == set(RECORD_ROLES),
        "explicit new record-copy allocations",
    )
    for copy_id in record_copy_ids.values():
        retention.identifier(copy_id)
    tree.need(
        len(set(record_copy_ids.values())) == len(RECORD_ROLES)
        and not set(record_copy_ids.values()) & all_ids
        and len(all_ids) + len(RECORD_ROLES) <= retention.MAX_COPIES,
        "unused distinct record copy IDs",
    )
    read_args = (
        request_raw,
        expected_request_sha256,
        context_raw,
        expected_journal_sha256,
        outer_receipt,
    )
    read_kw = dict(
        expected_outer_sha256=expected_outer_sha256,
        audit=audit,
        expected_audit_sha256=expected_audit_sha256,
        reader_audit=reader_audit,
        invented=invented,
    )
    readback = tree.inspect(*read_args, **read_kw)
    # The caller supplies the retained bytes; the reader checks the live bound
    # journal too. A forged retained copy cannot silently stand in for it.
    tree.need(
        readback["journal_sha256"] == tree.digest(journal_raw), "retained/live journal binding"
    )
    complete = readback["status"] == "completed"
    successor, next_provenance = copy.deepcopy(current), dict(provenance_raw)
    bindings = {
        "register": expected_register_sha256,
        "policy": expected_policy_sha256,
        "allocation": expected_allocation_sha256,
        "request": expected_request_sha256,
        "context": tree.digest(context_raw),
        "journal": expected_journal_sha256,
        "producer_audit": expected_audit_sha256,
        "reader_audit": tree.digest(tree.encoded(reader_audit)),
        "outer": tree.digest(tree.encoded(outer_receipt)) if outer_receipt is not None else None,
    }
    if complete:
        successor["previous_sha256"] = expected_register_sha256
        for key in ("all_copies_registered", "recovery_scope_reviewed", "processes_stopped"):
            successor["coverage"][key] = False
        raw = tree.encoded(
            {
                "schema": "opent1d.lt1-native-tree-copy-absence/1",
                "kind": r["kind"],
                "subject": r["subject"],
                "copy": r["copy"],
                "role": r["role"],
                "assessment_at": as_of,
                "bindings": bindings,
                "inherited": inherited,
                "registration_provenance_sha256": expected_provenance_sha256[r["copy"]],
                **tree.AUTHORITY,
            }
        )
        next_provenance[r["copy"]] = raw
        successor["subjects"][r["subject"]]["copies"][r["copy"]] = {
            "state": "absence-observed",
            "evidence_sha256": tree.digest(raw),
        }
    next_raw = tree.encoded(successor) if complete else register_raw
    tree.need(len(next_raw) <= retention.LIMIT, "successor bound")
    assessment = retention.plan(
        next_raw,
        tree.digest(next_raw),
        policy_raw,
        expected_policy_sha256,
        as_of,
        tree.digest(context_raw),
        previous_raw=register_raw if complete else previous_raw,
        expected_previous_sha256=expected_register_sha256 if complete else expected_previous_sha256,
    )
    tree.need(assessment["deadlines"] == current_plan["deadlines"], "origin deadline changed")
    recovery = None
    if recovery_inputs is not None:
        tree.need(
            type(recovery_inputs) is dict
            and set(recovery_inputs)
            == {
                "scope_raw",
                "expected_scope_sha256",
                "observations_raw",
                "expected_observations_sha256",
            },
            "fixed recovery assessor inputs",
        )
        recovery = recovery_evidence.assess(
            next_raw,
            tree.digest(next_raw),
            policy_raw,
            expected_policy_sha256,
            **recovery_inputs,
            as_of=as_of,
            expected_context_sha256=tree.digest(context_raw),
            previous_raw=register_raw if complete else previous_raw,
            expected_previous_sha256=expected_register_sha256
            if complete
            else expected_previous_sha256,
        )
    record_proposals = {
        name: {
            "subject": r["subject"],
            "copy": record_copy_ids[name],
            "state": "proposed-present-if-retained",
            "kind": r["kind"],
            "inherited": inherited,
            "evidence_sha256": bindings.get(name),
            "registered": False,
            "origin_time_newly_established": False,
            "saved_or_approved": False,
            "external_truth_proved": False,
        }
        for name in RECORD_ROLES
    }
    record_proposals["readback"]["evidence_sha256"] = tree.digest(tree.encoded(readback))
    if type(outer_receipt) is dict:
        record_proposals["control"]["evidence_sha256"] = outer_receipt.get("control_sha256")
        record_proposals["launch-log"]["evidence_sha256"] = outer_receipt.get("log_sha256")
    for record in record_proposals.values():
        if record["evidence_sha256"] is None:
            record["state"] = "not-observed"
    tree.need(
        tree.inspect(*read_args, **read_kw) == readback and source_identity() == source,
        "source/evidence changed during proposal",
    )
    return {
        "schema": "opent1d.lt1-native-tree-reconciliation-proposal/1",
        "status": "proposed" if complete else "incomplete",
        "kind": r["kind"],
        "register_raw": next_raw,
        "register_sha256": tree.digest(next_raw),
        "provenance_raw": next_provenance,
        "readback": readback,
        "bindings": bindings,
        "assessment": assessment,
        "recovery_assessment": recovery,
        "new_record_copy_proposals": record_proposals,
        "new_records_registered": False,
        "all_copy_coverage_verified": False,
        "saved_or_approved": False,
        "register_activated": False,
        "unregistered_records_block_effective_erasure": True,
        "native_stage_packet_snapshot_backup_coverage": False,
        **tree.AUTHORITY,
    }
