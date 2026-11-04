"""Unsaved allocated packet-copy absence proposals; no admission or activation.

Retained packet bytes establish a bounded inventory/accounting relationship, not
the truth of opaque old evidence. Only the unchanged live removal reader decides
complete versus incomplete. Quiet exclusive ownership remains necessary.
"""

import copy
from pathlib import Path, PurePosixPath

from experiments.lt1_diagnostic import packet_cleanup as cleanup
from experiments.lt1_diagnostic.control_identity import identity

packet, bundle, wire, retention, removal = (
    cleanup.packet,
    cleanup.bundle,
    cleanup.wire,
    cleanup.retention,
    cleanup.removal,
)
AUTHORITY = {
    **cleanup.AUTHORITY,
    "original_reconciliation_reassessed": False,
    "evidence_validity_established": False,
    "active_register_changed": False,
}
PROVENANCE_LIMIT = packet.reconciliation.PROVENANCE_LIMIT


def need(ok, reason):
    if not ok:
        raise ValueError("LT1 packet reconciliation refused: " + reason)


def source_identity():
    return identity(__file__)


def bounded(raw, expected, limit):
    need(isinstance(raw, bytes) and 0 < len(raw) <= limit, "bounded input bytes")
    return wire.decoded(raw, expected)


def _retained(files, expected_manifest):
    need(isinstance(files, dict), "retained packet map")
    files = dict(files)
    bundle._bounds(files)
    need(bundle.MANIFEST in files, "retained manifest required")
    manifest = bounded(files[bundle.MANIFEST], expected_manifest, removal.REQUEST_LIMIT)
    retention.fields(manifest, "schema files")
    need(manifest["schema"] == "opent1d.lt1-review-bundle/1", "manifest container schema")
    members = manifest["files"]
    need(
        isinstance(members, dict)
        and bundle.MANIFEST not in members
        and set(files) == set(members) | {bundle.MANIFEST},
        "closed retained namespace",
    )
    for name, record in members.items():
        retention.fields(record, "bytes sha256")
        need(
            type(record["bytes"]) is int
            and record["bytes"] == len(files[name])
            and record["sha256"] == wire.digest(files[name]),
            "retained member identity",
        )
    return files, members


def propose_packet_reconciliation(
    *,
    retained_files,
    expected_manifest_sha256,
    expected_registration_sha256,
    expected_packet_context_sha256,
    expected_historical_producer_identity,
    cleanup_raw,
    expected_cleanup_sha256,
    expected_cleanup_identity,
    accounting_raw,
    expected_accounting_sha256,
    provenance_raw,
    expected_provenance_sha256,
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
):
    """Validate retained bytes before live intake; never reopen the deleted packet.

    A hypothetical complete successor is sized first. Its overflow does not
    prevent an incomplete observation from retaining the supplied register bytes.
    No caller-supplied inspector result or executable historical reader is used.
    """
    source = source_identity()
    need(source == expected_reader_identity, "current reader identity")
    producer, helper = (
        copy.deepcopy(expected_historical_producer_identity),
        copy.deepcopy(expected_cleanup_identity),
    )
    cleanup._producer(producer)
    cleanup._producer(helper)
    files, members = _retained(retained_files, expected_manifest_sha256)
    report = bounded(cleanup_raw, expected_cleanup_sha256, retention.LIMIT)
    outer = bounded(outer_raw, expected_outer_sha256, removal.REQUEST_LIMIT)
    need(isinstance(outer, dict), "outer receipt object")
    need(
        isinstance(context_raw, bytes)
        and len(context_raw) <= removal.REQUEST_LIMIT
        and wire.digest(context_raw) == expected_context_sha256,
        "current removal context pin",
    )
    bounded(request_raw, expected_request_sha256, removal.REQUEST_LIMIT)
    request = removal._request(request_raw, context_raw)  # Pure byte/host/source validation.
    need(
        isinstance(journal_raw, bytes)
        and 0 < len(journal_raw) <= removal.JOURNAL_LIMIT
        and retention.sha(expected_journal_sha256)
        and wire.digest(journal_raw) == expected_journal_sha256,
        "bounded journal pin",
    )
    root = request["root"]
    lexical = PurePosixPath(root["path"])
    need(str(lexical) == root["path"] and ".." not in lexical.parts, "canonical root metadata")
    expected_members = {
        **members,
        bundle.MANIFEST: {"bytes": len(files[bundle.MANIFEST]), "sha256": expected_manifest_sha256},
    }
    need(
        {name: {k: v[k] for k in ("bytes", "sha256")} for name, v in request["files"].items()}
        == expected_members,
        "whole packet/request inventory",
    )
    snapshot = (files, request["files"], {k: root[k] for k in ("device", "inode", "uid")})
    need(packet.INTENT in files, "typed packet intent required")
    intent = bounded(files[packet.INTENT], wire.digest(files[packet.INTENT]), removal.FILE_LIMIT)
    inputs = cleanup._container(
        files,
        intent,
        snapshot,
        Path(root["path"]),
        expected_registration_sha256,
        expected_packet_context_sha256,
        producer,
    )
    need(
        retention.stamp(inputs["as_of"]) <= retention.stamp(as_of),
        "assessment precedes retained packet assessment",
    )
    need(
        request["kind"] == ("invented" if intent["kind"] == "invented" else "private-data"),
        "packet/removal origin",
    )
    current = retention.register(accounting_raw, expected_accounting_sha256)
    assigned = copy.deepcopy(intent["copies"])
    need(
        isinstance(provenance_raw, dict)
        and isinstance(expected_provenance_sha256, dict)
        and provenance_raw.keys() == expected_provenance_sha256.keys() == set(assigned.values())
        and all(isinstance(raw, bytes) for raw in provenance_raw.values())
        and sum(map(len, provenance_raw.values())) <= PROVENANCE_LIMIT,
        "bounded exact accounting provenance",
    )
    provenance_raw, provenance_pins = dict(provenance_raw), dict(expected_provenance_sha256)
    derived = packet._accounting(
        Path(root["path"]), expected_manifest_sha256, inputs, intent, snapshot
    )
    need(
        accounting_raw == derived["register_raw"]
        and provenance_raw == derived["provenance_raw"]
        and all(wire.digest(raw) == provenance_pins[key] for key, raw in provenance_raw.items()),
        "exact separate accounting branch",
    )
    retention.fields(
        report,
        "schema status request_sha256 source_identity historical_producer_identity_sha256 "
        "packet_manifest_sha256 packet_context_sha256 removal_context_sha256 packet_copy_ids "
        "packet_copy_accounting_supplied assessed_register_sha256 assessment "
        "original_reconciliation_reassessed evidence_validity_established active_register_changed "
        "saved_or_approved stale_packet_context "
        + " ".join(cleanup.AUTHORITY)
        + " "
        + " ".join(bundle.COPY_SCOPE),
    )
    stale = expected_packet_context_sha256 != expected_context_sha256
    need(
        report["schema"] == "opent1d.lt1-packet-cleanup-preparation/1"
        and report["status"] == "prepared-unadmitted"
        and report["request_sha256"] == expected_request_sha256
        and wire.encoded(report["source_identity"]) == wire.encoded(helper)
        and report["historical_producer_identity_sha256"] == wire.digest(wire.encoded(producer))
        and report["packet_manifest_sha256"] == expected_manifest_sha256
        and report["packet_context_sha256"] == expected_packet_context_sha256
        and report["removal_context_sha256"] == expected_context_sha256
        and wire.encoded(report["packet_copy_ids"]) == wire.encoded(assigned)
        and report["packet_copy_accounting_supplied"] is True
        and report["assessed_register_sha256"] == expected_accounting_sha256
        and isinstance(report["assessment"], dict)
        and report["stale_packet_context"] is stale
        and all(
            report[k] is False
            for k in (
                *cleanup.AUTHORITY,
                "original_reconciliation_reassessed",
                "evidence_validity_established",
                "active_register_changed",
                "saved_or_approved",
                "global_copy_coverage_verified",
            )
        )
        and report["new_bundle_copy_registration_required"] is True,
        "externally pinned cleanup preparation metadata",
    )
    current_plan = cleanup._assessment(
        inputs,
        accounting_raw,
        expected_accounting_sha256,
        inputs["registration_raw"],
        expected_registration_sha256,
        as_of,
    )
    bindings = {
        "packet_manifest": expected_manifest_sha256,
        "packet_intent": wire.digest(files[packet.INTENT]),
        "registration": expected_registration_sha256,
        "packet_context": expected_packet_context_sha256,
        "cleanup": expected_cleanup_sha256,
        "accounting": expected_accounting_sha256,
        "request": expected_request_sha256,
        "context": expected_context_sha256,
        "journal": expected_journal_sha256,
        "outer": expected_outer_sha256,
        "reader_identity": wire.digest(wire.encoded(source)),
    }
    successor, candidate_provenance = copy.deepcopy(current), {}
    successor["previous_sha256"] = expected_accounting_sha256
    for subject, copy_id in sorted(assigned.items()):
        raw = wire.encoded(
            {
                "schema": "opent1d.lt1-packet-copy-reconciliation/1",
                "kind": intent["kind"],
                "subject": subject,
                "copy": copy_id,
                "state": "absence-observed",
                "assessment_at": as_of,
                "bindings": bindings,
                "accounting_provenance_sha256": provenance_pins[copy_id],
                "absence_time_established": False,
                "retention_deadline_compliance_verified": False,
            }
        )
        candidate_provenance[copy_id] = raw
        successor["subjects"][subject]["copies"][copy_id] = {
            "state": "absence-observed",
            "evidence_sha256": wire.digest(raw),
        }
    candidate_raw = wire.encoded(successor)
    overflow = (
        len(candidate_raw) > retention.LIMIT
        or sum(map(len, candidate_provenance.values())) > PROVENANCE_LIMIT
    )
    need(source_identity() == source, "reader source changed before live intake")
    args = (request_raw, expected_request_sha256, context_raw, expected_journal_sha256, outer)
    readback = removal.inspect(*args)
    completed = readback["status"] == "completed"
    need(not completed or not overflow, "complete successor byte bound")
    next_raw = candidate_raw if completed else accounting_raw
    assessment = retention.plan(
        next_raw,
        wire.digest(next_raw),
        inputs["policy_raw"],
        inputs["expected_policy_sha256"],
        as_of,
        expected_packet_context_sha256,
        previous_raw=accounting_raw if completed else inputs["registration_raw"],
        expected_previous_sha256=expected_accounting_sha256
        if completed
        else expected_registration_sha256,
    )
    need(assessment["deadlines"] == current_plan["deadlines"], "original deadlines changed")
    if stale:
        assessment["blockers"].append("stale-packet-context")
        assessment["status"] = "blocked"
    need(source_identity() == source, "reader source changed")
    need(removal.inspect(*args) == readback, "live removal evidence changed")
    return {
        "schema": "opent1d.lt1-packet-reconciliation-proposal/1",
        "kind": intent["kind"],
        "status": "proposed" if completed else "incomplete",
        "reader_identity": source,
        "bindings": bindings,
        "removal_readback": readback,
        "register_raw": next_raw,
        "register_sha256": wire.digest(next_raw),
        "provenance_raw": candidate_provenance if completed else {},
        "assessment": assessment,
        "hypothetical_complete_successor_overflow": overflow,
        "new_revision_proposed": completed,
        "saved_or_approved": False,
        "output_copy_accounting_required": True,
        "provenance_retention_required": True,
        **AUTHORITY,
        **bundle.COPY_SCOPE,
    }
