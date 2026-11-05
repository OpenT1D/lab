"""Exact packet-copy proposals using real invented cleanup ownership only."""

import copy
import json
import os
import subprocess
import sys
import tempfile
import unittest
from contextlib import contextmanager
from pathlib import Path
from unittest.mock import patch

import lt1_packet_reconciliation_fixture as fixture

from experiments.lt1_diagnostic import packet_reconciliation as reader

packet, cleanup, bundle, wire, removal = (
    reader.packet,
    reader.cleanup,
    reader.bundle,
    reader.wire,
    reader.removal,
)


def rebound(args, files):
    """Fully rehash invented retained metadata, without invoking old live replay."""
    args, files = copy.deepcopy(args), dict(files)
    pins = json.loads(files[packet.PINS])
    for record in (*pins["roles"].values(), *pins["provenance"].values()):
        record["sha256"] = wire.digest(files[record["file"]])
    files[packet.PINS] = wire.encoded(pins)
    intent = json.loads(files[packet.INTENT])
    intent["registration_sha256"] = wire.digest(files[packet.ROLES["registration"]])
    files[packet.INTENT] = wire.encoded(intent)
    files[bundle.MANIFEST] = bundle._manifest(
        {k: v for k, v in files.items() if k != bundle.MANIFEST}
    )
    manifest_sha = wire.digest(files[bundle.MANIFEST])
    request = json.loads(args["request_raw"])
    for name, raw in files.items():
        request["files"][name].update(bytes=len(raw), sha256=wire.digest(raw))
    request_raw = wire.encoded(request)
    inputs = packet._inputs(files)
    snapshot = (
        files,
        request["files"],
        {k: request["root"][k] for k in ("device", "inode", "uid")},
    )
    accounting = packet._accounting(
        Path(request["root"]["path"]), manifest_sha, inputs, intent, snapshot
    )
    report = json.loads(args["cleanup_raw"])
    report.update(
        packet_manifest_sha256=manifest_sha,
        request_sha256=wire.digest(request_raw),
        assessed_register_sha256=accounting["register_sha256"],
        historical_producer_identity_sha256=wire.digest(wire.encoded(intent["source_identity"])),
    )
    args.update(
        retained_files=files,
        expected_manifest_sha256=manifest_sha,
        expected_registration_sha256=inputs["expected_registration_sha256"],
        request_raw=request_raw,
        expected_request_sha256=wire.digest(request_raw),
        cleanup_raw=wire.encoded(report),
        expected_cleanup_sha256=wire.digest(wire.encoded(report)),
        accounting_raw=accounting["register_raw"],
        expected_accounting_sha256=accounting["register_sha256"],
        provenance_raw=accounting["provenance_raw"],
        expected_provenance_sha256={
            k: wire.digest(v) for k, v in accounting["provenance_raw"].items()
        },
    )
    return args


def sized(args, target):
    original = json.loads(args["retained_files"][packet.ROLES["registration"]])
    assigned = json.loads(args["retained_files"][packet.INTENT])["copies"]

    def registration(count):
        result = copy.deepcopy(original)
        result["subjects"]["object-one"]["copies"].update(
            {
                f"pad{i:05d}" + "x" * 20: {"state": "present", "evidence_sha256": "e" * 64}
                for i in range(count)
            }
        )
        return result

    def size(current):
        value = copy.deepcopy(current)
        value["previous_sha256"] = "0" * 64
        for subject, copy_id in assigned.items():
            value["subjects"][subject]["copies"][copy_id] = {
                "state": "present",
                "evidence_sha256": "0" * 64,
            }
        return len(wire.encoded(value))

    low, high = 0, reader.retention.MAX_COPIES - 10
    while low < high:
        mid = (low + high + 1) // 2
        if size(registration(mid)) <= target:
            low = mid
        else:
            high = mid - 1
    current = registration(low)
    gap = target - size(current)
    copies = current["subjects"]["object-one"]["copies"]
    for i in range(gap // 9):
        copies[f"pad{i:05d}" + "x" * 20]["state"] = "absence-observed"
    old = f"pad{low - 1:05d}" + "x" * 20
    copies[old + "x" * (gap % 9)] = copies.pop(old)
    base = json.loads(args["retained_files"][packet.ROLES["base"]])
    base["subjects"]["object-one"]["copies"].update(
        {k: v for k, v in copies.items() if k.startswith("pad")}
    )
    files = dict(args["retained_files"])
    files[packet.ROLES["base"]] = wire.encoded(base)
    current["previous_sha256"] = wire.digest(files[packet.ROLES["base"]])
    files[packet.ROLES["registration"]] = wire.encoded(current)
    result = rebound(args, files)
    if len(result["accounting_raw"]) != target:
        raise AssertionError((len(result["accounting_raw"]), target))
    return result


@unittest.skipUnless(os.name == "posix", "POSIX owned packet fixture required")
class PacketReconciliationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.storage = tempfile.TemporaryDirectory()
        cls.addClassCleanup(cls.storage.cleanup)
        cls.parent = Path(cls.storage.name).resolve()
        cls.parent.chmod(0o700)
        cls.state = fixture.prepare(cls.parent)
        fixture.owned(cls.state, "complete")
        cls.initial = fixture.arguments(cls.state)

    def args(self):
        result = copy.deepcopy(self.initial)
        result["expected_reader_identity"] = reader.source_identity()
        return result

    @contextmanager
    def journal_for(self, args):
        path = self.parent / "cleanup-evidence/remove-packet/events.jsonl"
        saved = path.read_bytes()
        lines = [json.loads(line) for line in saved.splitlines()]
        lines[0]["request_sha256"] = args["expected_request_sha256"]
        raw = b"".join(wire.encoded(line) + b"\n" for line in lines)
        args.update(journal_raw=raw, expected_journal_sha256=wire.digest(raw))
        path.write_bytes(raw)
        try:
            yield
        finally:
            path.write_bytes(saved)

    def assert_closed(self, result):
        self.assertTrue(all(result[k] is False for k in reader.AUTHORITY))
        self.assertIs(result["saved_or_approved"], False)
        self.assertIs(result["global_copy_coverage_verified"], False)
        self.assertIs(result["output_copy_accounting_required"], True)

    def test_complete_changes_only_allocated_copies_without_old_replay(self):
        args = self.args()
        with (
            patch.object(packet, "inspect_packet", side_effect=AssertionError("deleted packet")),
            patch.object(packet, "_material", side_effect=AssertionError("old replay")),
            patch.object(
                packet.reconciliation,
                "propose_reconciliation",
                side_effect=AssertionError("old live evidence"),
            ),
            patch.object(
                cleanup, "prepare_packet_cleanup", side_effect=AssertionError("old namespace")
            ),
        ):
            result = reader.propose_packet_reconciliation(**args)
        self.assert_closed(result)
        self.assertEqual(result["status"], "proposed")
        current, proposed = json.loads(args["accounting_raw"]), json.loads(result["register_raw"])
        assigned = json.loads(args["retained_files"][packet.INTENT])["copies"]
        self.assertEqual(proposed["previous_sha256"], args["expected_accounting_sha256"])
        self.assertEqual(current["coverage"], proposed["coverage"])
        self.assertNotEqual(args["expected_context_sha256"], args["expected_packet_context_sha256"])
        for subject, before in current["subjects"].items():
            after = proposed["subjects"][subject]
            for key in ("retained_since", "origin_evidence_sha256", "hold"):
                self.assertEqual(before[key], after[key])
            for copy_id, value in before["copies"].items():
                if copy_id == assigned[subject]:
                    self.assertEqual(after["copies"][copy_id]["state"], "absence-observed")
                else:
                    self.assertEqual(value, after["copies"][copy_id])
        self.assertIn("stale-packet-context", result["assessment"]["blockers"])
        self.assertEqual(
            result["assessment"]["deadlines"],
            {"object-one": "2026-11-08T00:00:00Z", "unknown-object": None},
        )

    def test_actual_cancel_and_deadline_preserve_raw_accounting_and_real_receipts(self):
        unrelated = subprocess.Popen(
            [sys.executable, "-I", "-S", "-B", "-c", "import time;time.sleep(300)"],
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        try:
            for phase in ("quarantined", "removed"):
                with self.subTest(phase=phase), tempfile.TemporaryDirectory() as folder:
                    parent = Path(folder).resolve()
                    parent.chmod(0o700)
                    state = fixture.prepare(parent)
                    outer = fixture.owned(state, phase)
                    args = fixture.arguments(state)
                    result = reader.propose_packet_reconciliation(**args)
                    self.assert_closed(result)
                    self.assertEqual(result["status"], "incomplete")
                    self.assertEqual(result["register_raw"], args["accounting_raw"])
                    self.assertEqual(result["provenance_raw"], {})
                    self.assertEqual(len(outer["owned_processes"]), 1)
                    self.assertEqual(outer["received_signals"], [])
                    if phase == "removed":
                        self.assertEqual(outer["error"], "WorkerDeadline")
                        self.assertEqual(len(result["removal_readback"]["recorded_removed"]), 1)
                    else:
                        self.assertEqual(len(result["removal_readback"]["quarantined"]), 1)
                    before = json.loads((parent / "before.json").read_bytes())
                    self.assertEqual(before["producer_receipt"]["status"], "completed")
                    self.assertEqual(
                        wire.digest(wire.encoded(before["producer_receipt"])),
                        before["producer_receipt_sha256"],
                    )
                    self.assertIsNone(unrelated.poll())
        finally:
            unrelated.terminate()
            unrelated.wait(timeout=3)

    def test_input_pins_types_and_rehashed_lineage_fail_before_live_intake(self):
        initial = self.args()
        changes = [
            {"expected_accounting_sha256": "a" * 64},
            {"expected_context_sha256": "b" * 64},
            {"expected_cleanup_sha256": "c" * 64},
            {"accounting_raw": 100},
            {"journal_raw": b""},
            {"expected_reader_identity": {}},
            {"as_of": "2026-11-04T12:00:00Z"},
        ]
        for change in changes:
            with (
                self.subTest(change=list(change)),
                patch.object(removal, "inspect", side_effect=AssertionError("live intake")),
            ):
                with self.assertRaises(ValueError):
                    reader.propose_packet_reconciliation(**{**initial, **change})
        files = dict(initial["retained_files"])
        intent = json.loads(files[packet.INTENT])
        intent["subjects"]["unknown-object"]["hold"] = 1
        files[packet.INTENT] = wire.encoded(intent)
        changed = rebound(initial, files)
        with patch.object(removal, "inspect", side_effect=AssertionError("live intake")):
            with self.assertRaisesRegex(ValueError, "inherited subjects"):
                reader.propose_packet_reconciliation(**changed)

    def test_opaque_report_does_not_override_incomplete_outer_or_whole_inventory(self):
        args = self.args()
        report = json.loads(args["cleanup_raw"])
        report["assessment"] = {"status": "approved", "all_evidence_valid": True}
        args.update(
            cleanup_raw=wire.encoded(report),
            expected_cleanup_sha256=wire.digest(wire.encoded(report)),
        )
        outer = json.loads(args["outer_raw"])
        outer.update(status="failed", error="WorkerDeadline", exit_code=-15)
        args.update(
            outer_raw=wire.encoded(outer), expected_outer_sha256=wire.digest(wire.encoded(outer))
        )
        result = reader.propose_packet_reconciliation(**args)
        self.assertEqual(result["status"], "incomplete")
        self.assertEqual(result["register_raw"], args["accounting_raw"])
        request = json.loads(args["request_raw"])
        request["files"].pop(next(iter(request["files"])))
        args.update(
            request_raw=wire.encoded(request),
            expected_request_sha256=wire.digest(wire.encoded(request)),
        )
        with patch.object(removal, "inspect", side_effect=AssertionError("live intake")):
            with self.assertRaisesRegex(ValueError, "whole packet"):
                reader.propose_packet_reconciliation(**args)

    def test_final_source_namespace_and_journal_rechecks_refuse_late_changes(self):
        args = self.args()
        source = args["expected_reader_identity"]
        target = Path(json.loads(args["request_raw"])["root"]["path"])
        name = next(iter(json.loads(args["request_raw"])["files"]))
        journal = self.parent / "cleanup-evidence/remove-packet/events.jsonl"
        original = journal.read_bytes()
        for mode in ("source", "namespace", "journal"):
            calls = 0

            def observe():
                nonlocal calls
                calls += 1
                if calls == 3:
                    if mode == "source":
                        return {**source, "python": "changed"}
                    if mode == "namespace":
                        (target / name).write_bytes(b"invented recreated metadata")
                        (target / name).chmod(0o600)
                    else:
                        journal.write_bytes(original + b"\n")
                return source

            try:
                with (
                    self.subTest(mode=mode),
                    patch.object(reader, "source_identity", side_effect=observe),
                ):
                    with self.assertRaises(ValueError):
                        reader.propose_packet_reconciliation(**args)
            finally:
                (target / name).unlink(missing_ok=True)
                journal.write_bytes(original)

    def test_rebound_empty_target_refuses_instead_of_historical_completion(self):
        args = self.args()
        target = Path(json.loads(args["request_raw"])["root"]["path"])
        retained = target.with_name("retained-root")
        target.rename(retained)
        target.mkdir(mode=0o700)
        try:
            with self.assertRaisesRegex(ValueError, "reader root identity"):
                reader.propose_packet_reconciliation(**args)
        finally:
            target.rmdir()
            retained.rename(target)

    def test_exact_successor_limit_and_incomplete_overflow_preservation(self):
        initial = self.args()
        assigned = json.loads(initial["retained_files"][packet.INTENT])["copies"]
        growth = 9 * len(assigned)  # Both predecessor hashes already have fixed64 width.
        for extra in (0, 1):
            args = sized(initial, reader.retention.LIMIT - growth + extra)
            with self.subTest(overflow=bool(extra)), self.journal_for(args):
                if extra:
                    with self.assertRaisesRegex(ValueError, "complete successor byte bound"):
                        reader.propose_packet_reconciliation(**args)
                    outer = json.loads(args["outer_raw"])
                    outer.update(status="failed", error="WorkerDeadline", exit_code=-15)
                    args.update(
                        outer_raw=wire.encoded(outer),
                        expected_outer_sha256=wire.digest(wire.encoded(outer)),
                    )
                    result = reader.propose_packet_reconciliation(**args)
                    self.assertEqual(result["register_raw"], args["accounting_raw"])
                    self.assertIs(result["hypothetical_complete_successor_overflow"], True)
                    self.assertEqual(result["provenance_raw"], {})
                else:
                    result = reader.propose_packet_reconciliation(**args)
                    self.assertEqual(len(result["register_raw"]), reader.retention.LIMIT)
                    self.assertIs(result["hypothetical_complete_successor_overflow"], False)

    def test_historical_producer_and_cleanup_identities_remain_pinned_data(self):
        args = self.args()
        files = dict(args["retained_files"])
        intent = json.loads(files[packet.INTENT])
        intent["source_identity"]["python"] = "historical-producer"
        files[packet.INTENT] = wire.encoded(intent)
        args = rebound(args, files)
        args["expected_historical_producer_identity"] = intent["source_identity"]
        report = json.loads(args["cleanup_raw"])
        report["source_identity"]["python"] = "historical-cleanup-helper"
        args.update(
            expected_cleanup_identity=report["source_identity"],
            cleanup_raw=wire.encoded(report),
            expected_cleanup_sha256=wire.digest(wire.encoded(report)),
        )
        with (
            self.journal_for(args),
            patch.object(
                packet, "source_identity", side_effect=AssertionError("historical execution")
            ),
            patch.object(
                cleanup, "source_identity", side_effect=AssertionError("historical execution")
            ),
        ):
            result = reader.propose_packet_reconciliation(**args)
        self.assertEqual(result["status"], "proposed")
        self.assert_closed(result)
