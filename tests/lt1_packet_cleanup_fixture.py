"""Construct every packet before fixture-only removal; never consume an audit."""

import json
import os
import stat
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / "tests")]
import lt1_reconciliation_packet_fixture as producer  # noqa: E402
from test_lt1_reconciliation_packet import owned_case  # noqa: E402

from experiments.lt1_diagnostic import packet_cleanup as cleanup  # noqa: E402

packet, wire, removal = cleanup.packet, cleanup.wire, cleanup.removal


def build(parent):
    parent = Path(parent)
    if parent.resolve() != parent or any(parent.iterdir()):
        raise ValueError("Fresh empty canonical cleanup fixture directory required")
    info = parent.stat()
    if info.st_uid != os.getuid() or stat.S_IMODE(info.st_mode) != 0o700:
        raise ValueError("Owned private cleanup fixture directory required")
    original, store, evidence = [
        parent / name for name in ("producer", "store", "cleanup-evidence")
    ]
    for directory in (original, store, evidence):
        directory.mkdir(mode=0o700)
    outer = owned_case(original, "complete")
    inputs = producer.inputs(original, wire.encoded(outer), packet.reconciliation)
    current = json.loads(inputs["registration_raw"])
    copies = {name: f"cleanup-packet-{i}" for i, name in enumerate(sorted(current["subjects"]))}
    target = store / "packet"
    saved = packet.save_packet(
        target, copy_ids=copies, expected_identity=packet.source_identity(), **inputs
    )
    if saved["status"] != "published":
        raise AssertionError("Fresh cleanup fixture packet did not publish")
    # Metadata cleanup must not require the old live namespace or journal.
    (original / "bundle").rmdir()
    (original / "reports/remove-derived-bundle/events.jsonl").rename(
        original / "retained-old-journal.jsonl"
    )
    return {
        "parent": parent,
        "original": original,
        "target": target,
        "evidence": evidence,
        "saved": saved,
        "inputs": inputs,
        "copies": copies,
    }


def args(state, *, supplied=True):
    context = b"invented separate current packet-cleanup review\n"
    result = {
        "path": state["target"],
        "expected_manifest_sha256": state["saved"]["manifest_sha256"],
        "expected_registration_sha256": state["inputs"]["expected_registration_sha256"],
        "expected_packet_context_sha256": state["inputs"]["expected_context_sha256"],
        "expected_historical_producer_identity": state["saved"]["source_identity"],
        "removal_context_raw": context,
        "expected_removal_context_sha256": wire.digest(context),
        "evidence_parent": state["evidence"],
        "attempt": "remove-packet",
        "as_of": "2026-11-06T12:00:00Z",
        "expected_helper_identity": cleanup.source_identity(),
    }
    if supplied:
        accounting = state["saved"]["packet_copy_accounting"]
        result.update(
            accounting_raw=accounting["register_raw"],
            expected_accounting_sha256=accounting["register_sha256"],
            provenance_raw=accounting["provenance_raw"],
            expected_provenance_sha256={
                key: wire.digest(raw) for key, raw in accounting["provenance_raw"].items()
            },
        )
    return result


def main():
    parent, phase = Path(sys.argv[1]), sys.argv[2]
    if phase not in {"complete", "quarantined"}:
        raise ValueError("Fixed invented cleanup phase required")
    state = build(parent)
    inputs = args(state)
    prepared = cleanup.prepare_packet_cleanup(**inputs)
    raw, context = prepared["request_raw"], inputs["removal_context_raw"]
    try:
        removal.remove(raw, context)
    except ValueError as error:
        if "no reviewed removal request" not in str(error):
            raise
    else:
        raise AssertionError("Production cleanup gate unexpectedly admitted fixture")
    before = {
        "packet_files": json.loads(raw)["files"],
        "packet_copy_ids": prepared["packet_copy_ids"],
        "production_gate_refused": True,
        "old_registration_sha256": wire.digest(
            (state["original"] / "proposed-register.json").read_bytes()
        ),
        "old_original_sha256": wire.digest(
            (state["original"] / "original-object.txt").read_bytes()
        ),
        "accounting_sha256": state["saved"]["packet_copy_accounting"]["register_sha256"],
        "deadlines": prepared["assessment"]["deadlines"],
    }
    for name, value in {
        "request.json": raw,
        "context.bin": context,
        "accounting.json": inputs["accounting_raw"],
        "before.json": wire.encoded(before),
    }.items():
        producer.cycle.write_private(parent / name, value)

    def checkpoint(event, name):
        if event == phase:
            producer.cycle.write_private(
                parent / "ready.pending", wire.encoded({"event": event, "name": name})
            )
            (parent / "ready.pending").rename(parent / "ready")
            while True:
                time.sleep(0.02)

    registry = {"schema": "opent1d.lt1-removal-admissions/1", "requests": [wire.digest(raw)]}
    outcome = removal._remove_reviewed(raw, registry, context, checkpoint=checkpoint)
    producer.cycle.write_private(parent / "outcome.json", wire.encoded(outcome))
    return 0 if outcome["status"] == "namespace-absence-observed" else 23


if __name__ == "__main__":
    raise SystemExit(main())
