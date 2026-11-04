"""Fresh retained packet bytes and actual shared-owner cleanup; no real audit."""

import json
import sys
import tempfile
import threading
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / "tests")]
import lt1_packet_cleanup_fixture as previous  # noqa: E402

from experiments.lt1_diagnostic import packet_reconciliation as reader  # noqa: E402
from experiments.shared_services.execution import supervise  # noqa: E402

packet, cleanup, wire, removal = reader.packet, reader.cleanup, reader.wire, reader.removal


def prepare(parent):
    """Original real producer and packet preparation precede cleanup ownership."""
    pins = previous.prepare_case(parent)
    request_raw, context = (
        (parent / "request.json").read_bytes(),
        (parent / "context.bin").read_bytes(),
    )
    request = json.loads(request_raw)
    target = parent / "store/packet"
    retained = {p.name: p.read_bytes() for p in target.iterdir()}
    intent = json.loads(retained[packet.INTENT])
    inputs = packet._inputs(retained)
    snapshot = (
        retained,
        request["files"],
        {k: request["root"][k] for k in ("device", "inode", "uid")},
    )
    accounting = packet._accounting(
        target, wire.digest(retained[reader.bundle.MANIFEST]), inputs, intent, snapshot
    )
    prepared = cleanup.prepare_packet_cleanup(
        target,
        wire.digest(retained[reader.bundle.MANIFEST]),
        inputs["expected_registration_sha256"],
        inputs["expected_context_sha256"],
        expected_historical_producer_identity=intent["source_identity"],
        removal_context_raw=context,
        expected_removal_context_sha256=wire.digest(context),
        evidence_parent=parent / "cleanup-evidence",
        attempt="remove-packet",
        as_of="2026-11-06T12:00:00Z",
        expected_helper_identity=cleanup.source_identity(),
        accounting_raw=accounting["register_raw"],
        expected_accounting_sha256=accounting["register_sha256"],
        provenance_raw=accounting["provenance_raw"],
        expected_provenance_sha256={
            k: wire.digest(v) for k, v in accounting["provenance_raw"].items()
        },
    )
    if prepared["request_raw"] != request_raw:
        raise AssertionError("Fresh externally pinned request changed")
    report = {k: v for k, v in prepared.items() if k != "request_raw"}
    args = {
        "retained_files": retained,
        "expected_manifest_sha256": wire.digest(retained[reader.bundle.MANIFEST]),
        "expected_registration_sha256": inputs["expected_registration_sha256"],
        "expected_packet_context_sha256": inputs["expected_context_sha256"],
        "expected_historical_producer_identity": intent["source_identity"],
        "cleanup_raw": wire.encoded(report),
        "expected_cleanup_sha256": wire.digest(wire.encoded(report)),
        "expected_cleanup_identity": report["source_identity"],
        "accounting_raw": accounting["register_raw"],
        "expected_accounting_sha256": accounting["register_sha256"],
        "provenance_raw": accounting["provenance_raw"],
        "expected_provenance_sha256": {
            k: wire.digest(v) for k, v in accounting["provenance_raw"].items()
        },
        "request_raw": request_raw,
        "expected_request_sha256": wire.digest(request_raw),
        "context_raw": context,
        "expected_context_sha256": wire.digest(context),
        "as_of": "2026-11-06T12:00:00Z",
    }
    return {"parent": parent, "pins": pins, "args": args}


def owned(state, phase):
    stopped, done = threading.Event(), threading.Event()

    def watch():
        while not done.wait(0.01):
            if (state["parent"] / "ready").exists():
                stopped.set()
                return

    watcher = threading.Thread(target=watch) if phase == "quarantined" else None
    if watcher:
        watcher.start()
    try:
        with tempfile.TemporaryDirectory() as logs:
            log = Path(logs) / "worker.log"
            outer = supervise(
                [
                    sys.executable,
                    "-I",
                    "-S",
                    "-B",
                    str(Path(__file__)),
                    str(state["parent"]),
                    phase,
                    wire.encoded(state["pins"]).decode("utf-8"),
                ],
                log,
                timeout=60,
                grace=0.2,
                cancel=stopped,
                environment={"LANG": "C", "LC_ALL": "C", "PATH": "/usr/bin:/bin"},
            )
            expected = {"complete": "completed", "quarantined": "interrupted", "removed": "failed"}[
                phase
            ]
            if outer["status"] != expected or outer["remaining_owned_processes"] != []:
                raise AssertionError((outer, log.read_bytes()))
    finally:
        done.set()
        if watcher:
            watcher.join(timeout=1)
    state["outer"] = outer
    return outer


def arguments(state):
    result = dict(state["args"])
    journal = (state["parent"] / "cleanup-evidence/remove-packet/events.jsonl").read_bytes()
    outer = wire.encoded(state["outer"])
    result.update(
        journal_raw=journal,
        expected_journal_sha256=wire.digest(journal),
        outer_raw=outer,
        expected_outer_sha256=wire.digest(outer),
        expected_reader_identity=reader.source_identity(),
    )
    return result


def main():
    previous.need(len(sys.argv) == 4 and len(sys.argv[3]) <= 16384, "bounded external pins")
    parent, phase = Path(sys.argv[1]), sys.argv[2]
    previous.need(
        phase in {"complete", "quarantined", "removed"}, "fixed reconciliation fixture phase"
    )
    raw, context = previous.load_prepared(
        parent, json.loads(sys.argv[3], object_pairs_hook=removal.unique_object)
    )
    try:
        removal.remove(raw, context)
    except ValueError as error:
        previous.need("no reviewed removal request" in str(error), "production gate refusal")
    else:
        raise AssertionError("Production gate admitted invented packet removal")

    def checkpoint(event, name):
        if event == phase:
            previous.producer.cycle.write_private(
                parent / "ready.pending", wire.encoded({"event": event, "name": name})
            )
            (parent / "ready.pending").rename(parent / "ready")
            while True:
                time.sleep(0.02)

    registry = {"schema": "opent1d.lt1-removal-admissions/1", "requests": [wire.digest(raw)]}
    outcome = removal._remove_reviewed(raw, registry, context, checkpoint=checkpoint)
    previous.producer.cycle.write_private(parent / "outcome.json", wire.encoded(outcome))
    return 0 if outcome["status"] == "namespace-absence-observed" else 23


if __name__ == "__main__":
    raise SystemExit(main())
