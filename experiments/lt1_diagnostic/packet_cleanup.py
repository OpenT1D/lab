"""Prepare exact retained-packet removal; never remove, replay or admit.

Historical producer identities are externally pinned data, not executable code.
Cleanup preparation does not depend on the original live removal namespace.
Partial/pending/unknown containers require a separate reviewed manual request.
"""

import copy
import os

from experiments.lt1_diagnostic import reconciliation_packet as packet
from experiments.lt1_diagnostic.control_identity import identity

bundle, wire, retention = packet.bundle, packet.wire, packet.retention
removal = bundle.removal
AUTHORITY = dict(packet.AUTHORITY)


def need(ok, reason):
    if not ok:
        raise ValueError("LT1 packet cleanup refused: " + reason)


def source_identity():
    return identity(__file__)


def _producer(value):
    retention.fields(value, "implementation python executable_sha256")
    need(
        isinstance(value["implementation"], dict)
        and 0 < len(value["implementation"]) <= 4096
        and all(
            isinstance(name, str)
            and len(name) <= 512
            and name.startswith("experiments/")
            and not any(part in ("", ".", "..") for part in name.split("/"))
            and "\\" not in name
            and "\0" not in name
            and retention.sha(digest)
            for name, digest in value["implementation"].items()
        )
        and isinstance(value["python"], str)
        and 0 < len(value["python"]) <= 64
        and retention.sha(value["executable_sha256"]),
        "historical producer identity data",
    )


def _container(files, intent, snapshot, path, registration_sha, context_sha, producer):
    retention.fields(
        intent,
        "schema kind output_name source_identity packet_parent packet_root "
        "registration_sha256 context_sha256 copies subjects "
        "new_bundle_copy_registration_required global_copy_coverage_verified",
    )
    removal.safe_name(intent["output_name"])
    need(
        intent["schema"] == "opent1d.lt1-reconciliation-packet-intent/1"
        and intent["kind"] in ("invented", "observed")
        and not intent["output_name"].endswith(".pending")
        and intent["output_name"] == path.name
        and intent["packet_parent"] == str(path.parent)
        and wire.encoded(intent["packet_root"]) == wire.encoded(snapshot[2])
        and intent["registration_sha256"] == registration_sha
        and intent["context_sha256"] == context_sha
        and wire.encoded(intent["source_identity"]) == wire.encoded(producer)
        and intent["new_bundle_copy_registration_required"] is True
        and intent["global_copy_coverage_verified"] is False,
        "published typed packet identities",
    )
    inputs = packet._inputs(files)
    for role in (*packet.ROLES, *(("previous",) if "previous_raw" in inputs else ())):
        raw = inputs[role + "_raw"]
        need(
            wire.digest(raw) == inputs["expected_" + role + "_sha256"],
            "retained input hash",
        )
    for copy_id, raw in inputs["provenance_raw"].items():
        need(
            wire.digest(raw) == inputs["expected_provenance_sha256"][copy_id],
            "retained provenance hash",
        )
    need(
        inputs["expected_registration_sha256"] == registration_sha
        and inputs["expected_context_sha256"] == context_sha,
        "external registration/context pins",
    )
    need(packet.RESULT in files and "result-register.json" in files, "stored result members")
    result = wire.decoded(files[packet.RESULT], wire.digest(files[packet.RESULT]))
    retention.fields(result, "report provenance")
    index = result["provenance"]
    need(isinstance(result["report"], dict) and isinstance(index, dict), "opaque result metadata")
    names = set(packet.ROLES.values()) | {
        packet.INTENT,
        packet.PINS,
        packet.RESULT,
        bundle.MANIFEST,
        "result-register.json",
    }
    if "previous_raw" in inputs:
        names.add("previous.json")
    names.update(f"input-copy-{i:04d}.json" for i in range(len(inputs["provenance_raw"])))
    for i, (copy_id, name) in enumerate(sorted(index.items())):
        retention.identifier(copy_id)
        need(name == f"result-copy-{i:04d}.json", "fixed result provenance members")
        names.add(name)
    need(set(files) == names, "closed published packet roles")
    current = retention.register(inputs["registration_raw"], registration_sha)
    base = retention.register(inputs["base_raw"], inputs["expected_base_sha256"])
    need(
        current["subjects"].keys() == base["subjects"].keys()
        and current["policy_sha256"] == base["policy_sha256"]
        and current["coverage"]["context_sha256"] == base["coverage"]["context_sha256"]
        and current["coverage"]["recoverable_until"] == base["coverage"]["recoverable_until"],
        "original registration lineage metadata",
    )
    for name, old in base["subjects"].items():
        new = current["subjects"][name]
        need(
            wire.encoded({k: new[k] for k in ("retained_since", "origin_evidence_sha256", "hold")})
            == wire.encoded(
                {k: old[k] for k in ("retained_since", "origin_evidence_sha256", "hold")}
            )
            and all(
                key in new["copies"] and wire.encoded(value) == wire.encoded(new["copies"][key])
                for key, value in old["copies"].items()
            ),
            "original copies/clocks/holds unchanged",
        )
    subjects = {
        name: {key: value[key] for key in ("retained_since", "origin_evidence_sha256", "hold")}
        for name, value in current["subjects"].items()
    }
    need(
        wire.encoded(intent["subjects"]) == wire.encoded(subjects),
        "inherited subjects/clocks/holds",
    )
    assigned = intent["copies"]
    need(isinstance(assigned, dict) and assigned.keys() == subjects.keys(), "exact copy subjects")
    for copy_id in assigned.values():
        retention.identifier(copy_id)
    old_ids = {key for subject in current["subjects"].values() for key in subject["copies"]}
    need(
        len(set(assigned.values())) == len(assigned)
        and not set(assigned.values()) & old_ids
        and len(old_ids) + len(assigned) <= retention.MAX_COPIES,
        "distinct unused allocated copies",
    )
    return inputs


def _assessment(inputs, current_raw, current_sha, previous_raw, previous_sha, as_of):
    # Both history checks are pure. No original request, journal, root or process
    # is consumed as a live observation merely to prepare deletion of metadata.
    retention.plan(
        inputs["base_raw"],
        inputs["expected_base_sha256"],
        inputs["policy_raw"],
        inputs["expected_policy_sha256"],
        as_of,
        inputs["expected_context_sha256"],
        previous_raw=inputs.get("previous_raw"),
        expected_previous_sha256=inputs.get("expected_previous_sha256"),
    )
    retention.plan(
        inputs["registration_raw"],
        inputs["expected_registration_sha256"],
        inputs["policy_raw"],
        inputs["expected_policy_sha256"],
        as_of,
        inputs["expected_context_sha256"],
        previous_raw=inputs["base_raw"],
        expected_previous_sha256=inputs["expected_base_sha256"],
    )
    return retention.plan(
        current_raw,
        current_sha,
        inputs["policy_raw"],
        inputs["expected_policy_sha256"],
        as_of,
        inputs["expected_context_sha256"],
        previous_raw=previous_raw,
        expected_previous_sha256=previous_sha,
    )


def prepare_packet_cleanup(
    path,
    expected_manifest_sha256,
    expected_registration_sha256,
    expected_packet_context_sha256,
    *,
    expected_historical_producer_identity,
    removal_context_raw,
    expected_removal_context_sha256,
    evidence_parent,
    attempt,
    as_of,
    expected_helper_identity,
    accounting_raw=None,
    expected_accounting_sha256=None,
    provenance_raw=None,
    expected_provenance_sha256=None,
):
    """Return an unsaved exact request and blockers, never an admitted operation.

    A complete published snapshot is required; current reconciliation validity is
    deliberately not reassessed. Accounting is either exactly supplied or marked
    unavailable, including pre-fix packets whose copy-register delta cannot fit.
    """
    source = source_identity()
    need(source == expected_helper_identity, "current cleanup helper identity")
    producer = copy.deepcopy(expected_historical_producer_identity)
    _producer(producer)
    need(
        all(
            retention.sha(v)
            for v in (
                expected_manifest_sha256,
                expected_registration_sha256,
                expected_packet_context_sha256,
                expected_removal_context_sha256,
            )
        ),
        "external identity pins",
    )
    need(
        isinstance(removal_context_raw, bytes)
        and len(removal_context_raw) <= removal.REQUEST_LIMIT
        and wire.digest(removal_context_raw) == expected_removal_context_sha256,
        "current removal context pin",
    )
    optional = (
        accounting_raw,
        expected_accounting_sha256,
        provenance_raw,
        expected_provenance_sha256,
    )
    supplied = all(value is not None for value in optional)
    need(
        supplied or all(value is None for value in optional), "complete optional accounting inputs"
    )
    if supplied:
        need(
            isinstance(accounting_raw, bytes) and len(accounting_raw) <= retention.LIMIT,
            "bounded accounting bytes",
        )
        need(
            isinstance(provenance_raw, dict)
            and isinstance(expected_provenance_sha256, dict)
            and 0 < len(provenance_raw) <= retention.MAX_SUBJECTS
            and provenance_raw.keys() == expected_provenance_sha256.keys(),
            "complete accounting provenance map",
        )
        provenance_raw = copy.deepcopy(provenance_raw)
        expected_provenance_sha256 = copy.deepcopy(expected_provenance_sha256)
        retention.register(accounting_raw, expected_accounting_sha256)
        need(
            isinstance(provenance_raw, dict)
            and isinstance(expected_provenance_sha256, dict)
            and all(isinstance(raw, bytes) for raw in provenance_raw.values())
            and sum(map(len, provenance_raw.values())) <= packet.reconciliation.PROVENANCE_LIMIT,
            "bounded supplied accounting provenance",
        )
    removal.safe_name(attempt)
    with bundle._opened(path) as (path, fd):
        snapshot = bundle._snapshot(path, fd, expected_manifest_sha256)
        files = snapshot[0]
        need(packet.INTENT in files, "published reconciliation packet intent required")
        intent = wire.decoded(files[packet.INTENT], wire.digest(files[packet.INTENT]))
        inputs = _container(
            files,
            intent,
            snapshot,
            path,
            expected_registration_sha256,
            expected_packet_context_sha256,
            producer,
        )
        current_raw, current_sha = inputs["registration_raw"], expected_registration_sha256
        previous_raw, previous_sha = inputs["base_raw"], inputs["expected_base_sha256"]
        if supplied:
            derived = packet._accounting(path, expected_manifest_sha256, inputs, intent, snapshot)
            need(
                accounting_raw == derived["register_raw"]
                and provenance_raw == derived["provenance_raw"]
                and provenance_raw.keys() == expected_provenance_sha256.keys()
                and all(
                    wire.digest(raw) == expected_provenance_sha256[key]
                    for key, raw in provenance_raw.items()
                ),
                "exact separate packet-accounting branch",
            )
            current_raw, current_sha = accounting_raw, expected_accounting_sha256
            previous_raw, previous_sha = inputs["registration_raw"], expected_registration_sha256
        assessment = _assessment(
            inputs, current_raw, current_sha, previous_raw, previous_sha, as_of
        )
        if not supplied:
            assessment["blockers"].append("packet-copies-unregistered")
        stale = expected_packet_context_sha256 != expected_removal_context_sha256
        if stale:
            assessment["blockers"].append("stale-packet-context")
        if assessment["blockers"]:
            assessment["status"] = "blocked"
        with bundle._opened(evidence_parent) as (evidence, evidence_fd):
            need(not bundle._overlap(path, evidence), "separate cleanup evidence root")
            need(not os.path.lexists(evidence / attempt), "fresh cleanup attempt")
            request = {
                "schema": "opent1d.lt1-removal-request/1",
                "kind": "invented" if intent["kind"] == "invented" else "private-data",
                "root": {"path": str(path), **snapshot[2]},
                "evidence_parent": str(evidence),
                "attempt": attempt,
                "files": snapshot[1],
                "source_identity": removal.source_identity(),
                "host": removal.host(),
                "context_sha256": expected_removal_context_sha256,
            }
            raw = wire.encoded(request)
            removal._request(raw, removal_context_raw)
            need(source_identity() == source, "cleanup helper source changed")
            bundle.removal._binding(evidence, evidence_fd)
            need(not os.path.lexists(evidence / attempt), "cleanup attempt changed")
            need(
                bundle._snapshot(path, fd, expected_manifest_sha256) == snapshot,
                "packet changed during cleanup preparation",
            )
    return {
        "schema": "opent1d.lt1-packet-cleanup-preparation/1",
        "status": "prepared-unadmitted",
        "request_raw": raw,
        "request_sha256": wire.digest(raw),
        "source_identity": source,
        "historical_producer_identity_sha256": wire.digest(wire.encoded(producer)),
        "packet_manifest_sha256": expected_manifest_sha256,
        "packet_context_sha256": expected_packet_context_sha256,
        "removal_context_sha256": expected_removal_context_sha256,
        "packet_copy_ids": copy.deepcopy(intent["copies"]),
        "packet_copy_accounting_supplied": supplied,
        "assessed_register_sha256": current_sha,
        "assessment": assessment,
        "original_reconciliation_reassessed": False,
        "evidence_validity_established": False,
        "active_register_changed": False,
        "saved_or_approved": False,
        "stale_packet_context": stale,
        **AUTHORITY,
        **bundle.COPY_SCOPE,
    }
