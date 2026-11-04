"""Immutable private reconciliation evidence; no active register or admission.

The shared flat manifest is a storage container. A distinct packet intent and
closed role map prevent interpreting this evidence as an older review bundle.
Quiet exclusive ownership is required; multi-directory snapshots are not atomic.
"""

import copy
import os
from pathlib import Path

from experiments.lt1_diagnostic import bundle_reconciliation as reconciliation
from experiments.lt1_diagnostic.control_identity import identity

bundle, wire, retention = reconciliation.bundle, reconciliation.wire, reconciliation.retention
AUTHORITY = dict(reconciliation.AUTHORITY)
INTENT = "packet-intent.json"
PINS = "input-pins.json"
RESULT = "result.json"
ROLES = {
    "base": "base.json",
    "registration": "registration.json",
    "policy": "policy.json",
    "allocation": "allocation.json",
    "manifest": "bundle-manifest.json",
    "intent": "bundle-intent.json",
    "request": "request.json",
    "context": "context.bin",
    "journal": "removal-journal.jsonl",
    "outer": "outer.json",
}


def need(ok, reason):
    if not ok:
        raise ValueError("LT1 reconciliation packet refused: " + reason)


def source_identity():
    return identity(__file__)


def _allocation(inputs, copy_ids):
    current = retention.register(inputs["registration_raw"], inputs["expected_registration_sha256"])
    need(
        isinstance(copy_ids, dict) and copy_ids.keys() == current["subjects"].keys(),
        "one allocated packet copy per original subject",
    )
    for value in copy_ids.values():
        retention.identifier(value)
    assigned = copy.deepcopy(copy_ids)
    old_ids = {key for subject in current["subjects"].values() for key in subject["copies"]}
    need(
        len(set(assigned.values())) == len(assigned)
        and not set(assigned.values()) & old_ids
        and len(old_ids) + len(assigned) <= retention.MAX_COPIES,
        "globally unused bounded packet-copy IDs",
    )
    return current, assigned


def _material(inputs, copy_ids, output_name, source, parent, root=None):
    bundle.removal.safe_name(output_name)
    need(not output_name.endswith(".pending"), "reserved pending leaf")
    required = {
        *(role + "_raw" for role in ROLES),
        *("expected_" + role + "_sha256" for role in ROLES),
        "provenance_raw",
        "expected_provenance_sha256",
        "as_of",
        "expected_reader_identity",
    }
    need(
        set(inputs) in (required, required | {"previous_raw", "expected_previous_sha256"}),
        "closed reconciliation inputs",
    )
    current, assigned = _allocation(inputs, copy_ids)
    result = reconciliation.propose_reconciliation(**inputs)
    roles = dict(ROLES)
    if inputs.get("previous_raw") is not None:
        roles["previous"] = "previous.json"
    files = {name: inputs[role + "_raw"] for role, name in roles.items()}
    provenance = {}
    for index, (copy_id, raw) in enumerate(sorted(inputs["provenance_raw"].items())):
        name = f"input-copy-{index:04d}.json"
        files[name] = raw
        provenance[copy_id] = {
            "file": name,
            "sha256": inputs["expected_provenance_sha256"][copy_id],
        }
    pins = {
        "schema": "opent1d.lt1-reconciliation-packet-inputs/1",
        "as_of": inputs["as_of"],
        "reader_identity": inputs["expected_reader_identity"],
        "roles": {
            role: {"file": name, "sha256": inputs["expected_" + role + "_sha256"]}
            for role, name in roles.items()
        },
        "provenance": provenance,
    }
    files[PINS] = wire.encoded(pins)
    files["result-register.json"] = result["register_raw"]
    result_index = {}
    for index, (copy_id, raw) in enumerate(sorted(result["provenance_raw"].items())):
        name = f"result-copy-{index:04d}.json"
        files[name] = raw
        result_index[copy_id] = name
    files[RESULT] = wire.encoded(
        {
            "report": {
                key: value
                for key, value in result.items()
                if key not in {"register_raw", "provenance_raw"}
            },
            "provenance": result_index,
        }
    )
    intent = {
        "schema": "opent1d.lt1-reconciliation-packet-intent/1",
        "kind": result["kind"],
        "output_name": output_name,
        "source_identity": source,
        "packet_parent": str(parent),
        "packet_root": root,
        "registration_sha256": inputs["expected_registration_sha256"],
        "context_sha256": inputs["expected_context_sha256"],
        "copies": assigned,
        "subjects": {
            name: {
                key: subject[key] for key in ("retained_since", "origin_evidence_sha256", "hold")
            }
            for name, subject in current["subjects"].items()
        },
        **bundle.COPY_SCOPE,
    }
    files[INTENT] = wire.encoded(intent)
    files[bundle.MANIFEST] = bundle._manifest(files)
    bundle._bounds(files)
    return files, result, intent


def _inputs(files):
    need(PINS in files and INTENT in files, "typed packet metadata required")
    pins = wire.decoded(files[PINS], wire.digest(files[PINS]))
    retention.fields(pins, "schema as_of reader_identity roles provenance")
    need(pins["schema"] == "opent1d.lt1-reconciliation-packet-inputs/1", "input schema")
    roles = pins["roles"]
    need(
        isinstance(roles, dict) and set(roles) in (set(ROLES), set(ROLES) | {"previous"}),
        "fixed input roles",
    )
    inputs = {"as_of": pins["as_of"], "expected_reader_identity": pins["reader_identity"]}
    for role, record in roles.items():
        retention.fields(record, "file sha256")
        name = ROLES.get(role, "previous.json")
        need(record["file"] == name and name in files, "fixed role member")
        inputs[role + "_raw"] = files[name]
        inputs["expected_" + role + "_sha256"] = record["sha256"]
    indexed = pins["provenance"]
    need(isinstance(indexed, dict), "input provenance map")
    inputs.update(provenance_raw={}, expected_provenance_sha256={})
    for index, (copy_id, record) in enumerate(sorted(indexed.items())):
        retention.fields(record, "file sha256")
        name = f"input-copy-{index:04d}.json"
        need(record["file"] == name and name in files, "fixed provenance member")
        inputs["provenance_raw"][copy_id] = files[name]
        inputs["expected_provenance_sha256"][copy_id] = record["sha256"]
    return inputs


def _verify(path, fd, manifest_sha, registration_sha, context_sha, source, *, pending=False):
    snapshot = bundle._snapshot(path, fd, manifest_sha)
    files = snapshot[0]
    need(INTENT in files, "distinct reconciliation intent required")
    intent = wire.decoded(files[INTENT], wire.digest(files[INTENT]))
    retention.fields(
        intent,
        "schema kind output_name source_identity registration_sha256 context_sha256 "
        "copies subjects packet_parent packet_root "
        "new_bundle_copy_registration_required global_copy_coverage_verified",
    )
    need(
        intent["schema"] == "opent1d.lt1-reconciliation-packet-intent/1"
        and intent["source_identity"] == source
        and intent["registration_sha256"] == registration_sha
        and intent["context_sha256"] == context_sha,
        "external packet source/registration/context",
    )
    need(
        path.name == intent["output_name"] + (".pending" if pending else "")
        and intent["packet_parent"] == str(path.parent)
        and wire.encoded(intent["packet_root"]) == wire.encoded(snapshot[2]),
        "intended published packet root/leaf",
    )
    inputs = _inputs(files)
    need(
        inputs["expected_registration_sha256"] == registration_sha
        and inputs["expected_context_sha256"] == context_sha,
        "external input identities",
    )
    expected, result, _ = _material(
        inputs, intent["copies"], intent["output_name"], source, path.parent, snapshot[2]
    )
    need(expected == files, "exact packet result replay")
    _final(path, fd, manifest_sha, inputs, result, source, snapshot)
    return inputs, result, intent, snapshot


def _final(path, fd, manifest_sha, inputs, result, source, snapshot):
    """Recheck after every derivation, including returned copy accounting."""
    need(source_identity() == source, "packet reader source changed")
    outer = wire.decoded(inputs["outer_raw"], inputs["expected_outer_sha256"])
    need(
        bundle.removal.inspect(
            inputs["request_raw"],
            inputs["expected_request_sha256"],
            inputs["context_raw"],
            inputs["expected_journal_sha256"],
            outer,
        )
        == result["removal_readback"],
        "live removal evidence changed",
    )
    need(bundle._snapshot(path, fd, manifest_sha) == snapshot, "packet changed during replay")


def _accounting(path, manifest_sha, inputs, intent, snapshot):
    """Separate proposal from supplied registration, never adopt reconciliation."""
    current, assigned = _allocation(inputs, intent["copies"])
    proposed = copy.deepcopy(current)
    proposed["previous_sha256"] = inputs["expected_registration_sha256"]
    for key in ("all_copies_registered", "recovery_scope_reviewed", "processes_stopped"):
        proposed["coverage"][key] = False
    provenance = {}
    for subject, copy_id in sorted(assigned.items()):
        raw = wire.encoded(
            {
                "schema": "opent1d.lt1-reconciliation-packet-copy/1",
                "kind": intent["kind"],
                "subject": subject,
                "copy": copy_id,
                "packet_manifest_sha256": manifest_sha,
                "packet_path": str(path),
                "packet_root": snapshot[2],
                "registration_sha256": inputs["expected_registration_sha256"],
                "context_sha256": inputs["expected_context_sha256"],
                "source_identity_sha256": wire.digest(wire.encoded(intent["source_identity"])),
                "inherited": intent["subjects"][subject],
            }
        )
        provenance[copy_id] = raw
        proposed["subjects"][subject]["copies"][copy_id] = {
            "state": "present",
            "evidence_sha256": wire.digest(raw),
        }
    need(
        sum(map(len, provenance.values())) <= reconciliation.PROVENANCE_LIMIT,
        "copy provenance bound",
    )
    raw = wire.encoded(proposed)
    need(len(raw) <= retention.LIMIT, "accounting register bound")
    assessment = retention.plan(
        raw,
        wire.digest(raw),
        inputs["policy_raw"],
        inputs["expected_policy_sha256"],
        inputs["as_of"],
        inputs["expected_context_sha256"],
        previous_raw=inputs["registration_raw"],
        expected_previous_sha256=inputs["expected_registration_sha256"],
    )
    return {
        "register_raw": raw,
        "register_sha256": wire.digest(raw),
        "provenance_raw": provenance,
        "assessment": assessment,
        "saved_or_approved": False,
        "reconciliation_proposal_adopted": False,
    }


def inspect_packet(
    path,
    expected_manifest_sha256,
    expected_registration_sha256,
    expected_context_sha256,
    *,
    expected_identity,
):
    """Replay supplied evidence and current namespaces; not a historical-only read."""
    source = source_identity()
    need(source == expected_identity, "expected packet reader source")
    need(
        all(
            retention.sha(v)
            for v in (
                expected_manifest_sha256,
                expected_registration_sha256,
                expected_context_sha256,
            )
        ),
        "external identity pins",
    )
    with bundle._opened(path) as (path, fd):
        inputs, result, intent, snapshot = _verify(
            path,
            fd,
            expected_manifest_sha256,
            expected_registration_sha256,
            expected_context_sha256,
            source,
        )
        need(path.name == intent["output_name"], "intended published packet leaf")
        accounting = _accounting(path, expected_manifest_sha256, inputs, intent, snapshot)
        _final(path, fd, expected_manifest_sha256, inputs, result, source, snapshot)
    return {
        "schema": "opent1d.lt1-reconciliation-packet-readback/1",
        "status": "verified-evidence",
        "manifest_sha256": expected_manifest_sha256,
        "source_identity": source,
        "reconciliation": result,
        "packet_copy_accounting": accounting,
        "packet_saved": True,
        "active_register_changed": False,
        "additional_saved_outputs_require_accounting": True,
        "assessment_as_of": inputs["as_of"],
        "assessment_refreshed": False,
        **AUTHORITY,
        **bundle.COPY_SCOPE,
    }


def save_packet(
    output, *, copy_ids, expected_identity, stop=lambda: False, checkpoint=lambda *_: None, **inputs
):
    """Write a fresh evidence packet. Keep every interrupted or uncertain prefix."""
    source = source_identity()
    need(source == expected_identity, "expected packet writer source")
    inputs = copy.deepcopy(inputs)
    copy_ids = copy.deepcopy(copy_ids)
    output = Path(output)
    need(output.is_absolute(), "absolute output")
    files, _, intent = _material(inputs, copy_ids, output.name, source, output.parent)
    published, created, stage_fd, pending = False, False, None, None
    with bundle._opened(output.parent) as (parent, parent_fd):
        pending = parent / (output.name + ".pending")
        need(
            not os.path.lexists(output) and not os.path.lexists(pending), "fresh packet and pending"
        )
        if stop():
            return {
                "status": "interrupted",
                "published": False,
                "pending": None,
                **AUTHORITY,
                **bundle.COPY_SCOPE,
            }
        try:
            os.mkdir(pending.name, 0o700, dir_fd=parent_fd)
            created = True
            os.fsync(parent_fd)
            _, stage_fd = bundle._directory(pending)
            intent["packet_root"] = bundle._root(stage_fd)
            files[INTENT] = wire.encoded(intent)
            files.pop(bundle.MANIFEST)
            files[bundle.MANIFEST] = bundle._manifest(files)
            bundle._bounds(files)
            manifest_sha = wire.digest(files[bundle.MANIFEST])
            bundle._write_at(stage_fd, INTENT, files[INTENT], 0o600)
            checkpoint("intent", INTENT)
            for name in [*sorted(set(files) - {INTENT, bundle.MANIFEST}), bundle.MANIFEST]:
                if stop():
                    raise InterruptedError("packet cancelled")
                bundle.removal._binding(parent, parent_fd)
                bundle.removal._binding(pending, stage_fd)
                bundle._write_at(stage_fd, name, files[name], 0o600)
                checkpoint("member", name)
            checkpoint("prepared", None)
            if stop():
                raise InterruptedError("packet cancelled")
            _verify(
                pending,
                stage_fd,
                manifest_sha,
                inputs["expected_registration_sha256"],
                inputs["expected_context_sha256"],
                source,
                pending=True,
            )
            bundle.removal._binding(parent, parent_fd)
            bundle.exclusive_rename(pending, output)
            published = True
            checkpoint("published", None)
            verified_inputs, result, verified_intent, snapshot = _verify(
                output,
                stage_fd,
                manifest_sha,
                inputs["expected_registration_sha256"],
                inputs["expected_context_sha256"],
                source,
            )
            need(verified_intent == intent, "published intent changed")
            accounting = _accounting(output, manifest_sha, verified_inputs, intent, snapshot)
            os.fsync(parent_fd)
            _final(output, stage_fd, manifest_sha, verified_inputs, result, source, snapshot)
            return {
                "status": "published",
                "published": True,
                "durability_confirmed": True,
                "pending": None,
                "manifest_sha256": manifest_sha,
                "source_identity": source,
                "reconciliation": result,
                "packet_copy_accounting": accounting,
                "packet_saved": True,
                "active_register_changed": False,
                "additional_saved_outputs_require_accounting": True,
                "assessment_as_of": inputs["as_of"],
                "assessment_refreshed": False,
                **AUTHORITY,
                **bundle.COPY_SCOPE,
            }
        except (Exception, KeyboardInterrupt) as error:
            if created and stage_fd is not None:
                try:
                    named, opened = output.lstat(), os.fstat(stage_fd)
                    published = published or (named.st_dev, named.st_ino) == (
                        opened.st_dev,
                        opened.st_ino,
                    )
                except OSError:
                    pass
            return {
                "status": "publication-uncertain"
                if published
                else "interrupted"
                if isinstance(error, (InterruptedError, KeyboardInterrupt))
                else "failed",
                "published": published,
                "durability_confirmed": False,
                "pending": str(pending) if created and not published else None,
                "error": type(error).__name__,
                "new_packet_copy_accounting_required": created,
                **AUTHORITY,
                **bundle.COPY_SCOPE,
            }
        finally:
            if stage_fd is not None:
                os.close(stage_fd)
