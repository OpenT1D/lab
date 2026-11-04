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


def prepare_case(parent):
    """Keep real producer construction outside the owned cleanup deadline."""
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
        "producer_receipt": json.loads(state["inputs"]["outer_raw"]),
        "producer_receipt_sha256": wire.digest(state["inputs"]["outer_raw"]),
        "retained_fixture_metadata_copy_accounted_or_approved": False,
    }
    for name, value in {
        "request.json": raw,
        "context.bin": context,
        "accounting.json": inputs["accounting_raw"],
        "before.json": wire.encoded(before),
    }.items():
        producer.cycle.write_private(parent / name, value)
    return {
        "request_sha256": wire.digest(raw),
        "context_sha256": wire.digest(context),
        "source_sha256": wire.digest(wire.encoded(removal.source_identity())),
        "parent": directory_identity(parent),
        "root": json.loads(raw)["root"],
        "evidence": directory_identity(state["evidence"]),
    }


def need(ok, message):
    if not ok:
        raise ValueError("Invented cleanup fixture refused: " + message)


def directory_identity(path):
    info = path.lstat()
    need(
        path.resolve() == path
        and stat.S_ISDIR(info.st_mode)
        and info.st_uid == os.getuid()
        and stat.S_IMODE(info.st_mode) == 0o700,
        "private canonical directory",
    )
    return {"device": info.st_dev, "inode": info.st_ino, "uid": info.st_uid}


def private_input(parent_fd, name):
    fd = os.open(name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK | os.O_CLOEXEC, dir_fd=parent_fd)
    try:
        before = os.fstat(fd)
        need(
            stat.S_ISREG(before.st_mode)
            and before.st_nlink == 1
            and before.st_uid == os.getuid()
            and stat.S_IMODE(before.st_mode) == 0o600
            and before.st_size <= removal.REQUEST_LIMIT,
            "bounded private input",
        )
        raw = b""
        while part := os.read(fd, min(65536, removal.REQUEST_LIMIT + 1 - len(raw))):
            raw += part
            need(len(raw) <= removal.REQUEST_LIMIT, "input grew")
        named = os.stat(name, dir_fd=parent_fd, follow_symlinks=False)
        need(
            removal.signature(before) == removal.signature(os.fstat(fd)) == removal.signature(named)
            and named.st_nlink == 1,
            "input binding changed",
        )
        return raw
    finally:
        os.close(fd)


def load_prepared(parent, pins):
    """Only externally pinned fresh fixture bytes reach the private injection."""
    removal.fields(pins, "request_sha256 context_sha256 source_sha256 parent root evidence")
    for key in ("parent", "evidence"):
        removal.fields(pins[key], "device inode uid")
        need(
            all(type(value) is int and value >= 0 for value in pins[key].values()),
            "typed directory pin",
        )
    removal.fields(pins["root"], "path device inode uid")
    need(
        all(
            type(pins["root"][key]) is int and pins["root"][key] >= 0
            for key in ("device", "inode", "uid")
        ),
        "typed target pin",
    )
    for key in ("request_sha256", "context_sha256", "source_sha256"):
        need(removal.sha(pins[key]), "external hash pin")
    need(directory_identity(parent) == pins["parent"], "parent identity pin")
    need(
        wire.digest(wire.encoded(removal.source_identity())) == pins["source_sha256"],
        "current source pin",
    )
    parent_fd = removal._private_directory(parent)
    try:
        removal._binding(parent, parent_fd)
        need(
            removal.names(parent_fd)
            == {
                "producer",
                "store",
                "cleanup-evidence",
                "request.json",
                "context.bin",
                "accounting.json",
                "before.json",
            },
            "closed prepared prefix",
        )
        raw = private_input(parent_fd, "request.json")
        context = private_input(parent_fd, "context.bin")
        need(wire.digest(raw) == pins["request_sha256"], "request hash pin")
        need(wire.digest(context) == pins["context_sha256"], "context hash pin")
        request = removal._request(raw, context)
        need(
            request["kind"] == "invented"
            and request["root"] == pins["root"]
            and request["root"]["path"] == str(parent / "store/packet")
            and request["evidence_parent"] == str(parent / "cleanup-evidence")
            and request["attempt"] == "remove-packet",
            "fixed invented request boundary",
        )
        need(
            directory_identity(parent / "store/packet")
            == {key: request["root"][key] for key in ("device", "inode", "uid")},
            "target identity pin",
        )
        evidence = parent / "cleanup-evidence"
        need(directory_identity(evidence) == pins["evidence"], "evidence identity pin")
        need(not any(evidence.iterdir()), "fresh evidence prefix")
        need(directory_identity(parent) == pins["parent"], "final parent identity pin")
        removal._binding(parent, parent_fd)
        return raw, context
    finally:
        os.close(parent_fd)


def main():
    need(len(sys.argv) == 4 and len(sys.argv[3]) <= 16384, "bounded external pins")
    parent, phase = Path(sys.argv[1]), sys.argv[2]
    need(phase in {"complete", "quarantined"}, "fixed cleanup phase")
    pins = json.loads(sys.argv[3], object_pairs_hook=removal.unique_object)
    raw, context = load_prepared(parent, pins)
    try:
        removal.remove(raw, context)
    except ValueError as error:
        need("no reviewed removal request" in str(error), "production refusal")
    else:
        raise AssertionError("Production cleanup gate unexpectedly admitted fixture")

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
