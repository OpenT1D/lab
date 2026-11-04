"""Private packet cleanup preparation and fresh owned removals; no admission."""

import copy
import json
import os
import subprocess
import sys
import tempfile
import threading
import unittest
from pathlib import Path
from unittest.mock import patch

import lt1_packet_cleanup_fixture as fixture

from experiments.lt1_diagnostic import packet_cleanup as cleanup
from experiments.shared_services.execution import supervise

packet, bundle, wire = cleanup.packet, cleanup.bundle, cleanup.wire
ROOT = Path(__file__).resolve().parents[1]


@unittest.skipUnless(os.name == "posix", "POSIX private packet cleanup fixture required")
class PacketCleanupTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.storage = tempfile.TemporaryDirectory()
        cls.addClassCleanup(cls.storage.cleanup)
        parent = Path(cls.storage.name).resolve()
        parent.chmod(0o700)
        cls.state = fixture.build(parent)

    def args(self, supplied=True):
        return copy.deepcopy(fixture.args(self.state, supplied=supplied))

    def assert_closed(self, result):
        self.assertEqual(result["status"], "prepared-unadmitted")
        self.assertTrue(all(result[k] is False for k in cleanup.AUTHORITY))
        for key in (
            "original_reconciliation_reassessed",
            "evidence_validity_established",
            "active_register_changed",
            "saved_or_approved",
            "global_copy_coverage_verified",
        ):
            self.assertIs(result[key], False)

    def test_missing_original_namespace_still_prepares_exact_readonly_request(self):
        self.assertFalse((self.state["original"] / "bundle").exists())
        self.assertFalse(
            (self.state["original"] / "reports/remove-derived-bundle/events.jsonl").exists()
        )
        with (
            patch.object(
                packet, "inspect_packet", side_effect=AssertionError("original live replay")
            ),
            patch.object(packet, "_material", side_effect=AssertionError("material replay")),
            patch.object(
                packet.reconciliation,
                "propose_reconciliation",
                side_effect=AssertionError("reconciliation"),
            ),
            patch.object(
                cleanup.removal, "inspect", side_effect=AssertionError("old live namespace")
            ),
        ):
            result = cleanup.prepare_packet_cleanup(**self.args())
        self.assert_closed(result)
        request = json.loads(result["request_raw"])
        self.assertEqual(set(request["files"]), {p.name for p in self.state["target"].iterdir()})
        self.assertEqual(request["root"]["path"], str(self.state["target"]))
        self.assertEqual(request["context_sha256"], self.args()["expected_removal_context_sha256"])
        self.assertTrue(result["packet_copy_accounting_supplied"])
        self.assertTrue(result["stale_packet_context"])
        self.assertIn("stale-packet-context", result["assessment"]["blockers"])
        self.assertNotIn("packet-copies-unregistered", result["assessment"]["blockers"])
        self.assertEqual(
            result["assessment"]["deadlines"],
            {"object-one": "2026-11-08T00:00:00Z", "unknown-object": None},
        )
        self.assertEqual(list(self.state["evidence"].iterdir()), [])
        with patch.object(cleanup.removal, "_request", side_effect=AssertionError("path intake")):
            with self.assertRaisesRegex(ValueError, "no reviewed removal request"):
                cleanup.removal.remove(result["request_raw"], self.args()["removal_context_raw"])

    def test_missing_accounting_does_not_invoke_oversize_or_replay_preflight(self):
        with (
            patch.object(
                packet, "_allocation", side_effect=AssertionError("new-copy size preflight")
            ),
            patch.object(packet, "_accounting", side_effect=AssertionError("new-copy accounting")),
            patch.object(packet, "_material", side_effect=AssertionError("old replay")),
            patch.object(cleanup.removal, "inspect", side_effect=AssertionError("old namespace")),
        ):
            result = cleanup.prepare_packet_cleanup(**self.args(False))
        self.assert_closed(result)
        self.assertFalse(result["packet_copy_accounting_supplied"])
        self.assertIn("packet-copies-unregistered", result["assessment"]["blockers"])
        self.assertEqual(
            result["assessed_register_sha256"], self.state["inputs"]["expected_registration_sha256"]
        )
        self.assertEqual(result["packet_copy_ids"], self.state["copies"])

    def test_historical_producer_pin_is_data_not_current_producer_execution(self):
        target = self.state["target"]
        original_intent = (target / packet.INTENT).read_bytes()
        original_manifest = (target / bundle.MANIFEST).read_bytes()
        try:
            intent = json.loads(original_intent)
            historical = copy.deepcopy(intent["source_identity"])
            historical["python"] = "historical-invented-python"
            historical["implementation"]["experiments/lt1_diagnostic/reconciliation_packet.py"] = (
                "a" * 64
            )
            intent["source_identity"] = historical
            (target / packet.INTENT).write_bytes(wire.encoded(intent))
            manifest = bundle._manifest(
                {p.name: p.read_bytes() for p in target.iterdir() if p.name != bundle.MANIFEST}
            )
            (target / bundle.MANIFEST).write_bytes(manifest)
            args = self.args(False)
            args.update(
                expected_manifest_sha256=wire.digest(manifest),
                expected_historical_producer_identity=historical,
            )
            with patch.object(
                packet,
                "source_identity",
                side_effect=AssertionError("historical producer execution"),
            ):
                result = cleanup.prepare_packet_cleanup(**args)
            self.assert_closed(result)
            self.assertEqual(
                result["historical_producer_identity_sha256"], wire.digest(wire.encoded(historical))
            )
        finally:
            (target / packet.INTENT).write_bytes(original_intent)
            (target / bundle.MANIFEST).write_bytes(original_manifest)

    def test_bad_source_context_accounting_type_or_incomplete_pins_precedes_paths(self):
        args = self.args()

        class BadBytes:
            def __bytes__(self):
                raise AssertionError("caller conversion executed")

        historical = copy.deepcopy(args["expected_historical_producer_identity"])
        historical["implementation"]["experiments/" + "x" * 513] = "a" * 64
        for changes in (
            {"expected_helper_identity": {}},
            {"removal_context_raw": b"foreign current context"},
            {"expected_historical_producer_identity": historical},
            {"accounting_raw": 10**9},
            {"accounting_raw": BadBytes()},
            {"accounting_raw": b"x" * (cleanup.retention.LIMIT + 1)},
            {"provenance_raw": None},
            {"expected_accounting_sha256": "a" * 64},
        ):
            with (
                self.subTest(changes=sorted(changes)),
                patch.object(bundle, "_opened", side_effect=AssertionError("private path")),
            ):
                with self.assertRaises(ValueError):
                    cleanup.prepare_packet_cleanup(**{**args, **changes})

    def test_forged_accounting_cannot_adopt_unapproved_absence_or_replace_provenance(self):
        args = self.args()
        value = json.loads(args["accounting_raw"])
        value["subjects"]["object-one"]["copies"]["copy-live"]["state"] = "absence-observed"
        raw = wire.encoded(value)
        with self.assertRaisesRegex(ValueError, "exact separate packet-accounting branch"):
            cleanup.prepare_packet_cleanup(
                **{**args, "accounting_raw": raw, "expected_accounting_sha256": wire.digest(raw)}
            )
        key = next(iter(args["provenance_raw"]))
        wrong = wire.encoded({"schema": "invented foreign provenance"})
        with self.assertRaisesRegex(ValueError, "exact separate packet-accounting branch"):
            cleanup.prepare_packet_cleanup(
                **{
                    **args,
                    "provenance_raw": {**args["provenance_raw"], key: wrong},
                    "expected_provenance_sha256": {
                        **args["expected_provenance_sha256"],
                        key: wire.digest(wrong),
                    },
                }
            )
        self.assertEqual(list(self.state["evidence"].iterdir()), [])

    def test_rehashed_intent_cannot_reset_original_clock_or_hold_type(self):
        target = self.state["target"]
        originals = {
            name: (target / name).read_bytes() for name in (packet.INTENT, bundle.MANIFEST)
        }
        try:
            for subject, key, value in (
                ("unknown-object", "hold", 1),
                ("object-one", "retained_since", "2026-11-05T00:00:00Z"),
            ):
                intent = json.loads(originals[packet.INTENT])
                intent["subjects"][subject][key] = value
                (target / packet.INTENT).write_bytes(wire.encoded(intent))
                manifest = bundle._manifest(
                    {p.name: p.read_bytes() for p in target.iterdir() if p.name != bundle.MANIFEST}
                )
                (target / bundle.MANIFEST).write_bytes(manifest)
                args = self.args(False)
                args["expected_manifest_sha256"] = wire.digest(manifest)
                with (
                    self.subTest(key=key),
                    self.assertRaisesRegex(ValueError, "inherited subjects/clocks/holds"),
                ):
                    cleanup.prepare_packet_cleanup(**args)
        finally:
            for name, raw in originals.items():
                (target / name).write_bytes(raw)

    def test_late_same_byte_inode_or_helper_source_change_refuses(self):
        args = self.args()
        actual, calls = cleanup.source_identity, 0
        path = self.state["target"] / "registration.json"
        retained = self.state["parent"] / "retained-packet-member"

        def change():
            nonlocal calls
            value = actual()
            calls += 1
            if calls == 2:
                raw = path.read_bytes()
                path.rename(retained)
                path.write_bytes(raw)
                path.chmod(0o600)
            return value

        try:
            with patch.object(cleanup, "source_identity", side_effect=change):
                with self.assertRaisesRegex(ValueError, "packet changed during cleanup"):
                    cleanup.prepare_packet_cleanup(**args)
        finally:
            if retained.exists():
                path.unlink()
                retained.rename(path)
        changed = {**args["expected_helper_identity"], "python": "changed"}
        with patch.object(
            cleanup, "source_identity", side_effect=[args["expected_helper_identity"], changed]
        ):
            with self.assertRaisesRegex(ValueError, "helper source changed"):
                cleanup.prepare_packet_cleanup(**args)

    def test_pending_extra_collision_and_existing_fixture_directory_are_outside_scope(self):
        args = self.args()
        original = self.state["target"]
        pending = original.with_name(original.name + ".pending")
        original.rename(pending)
        try:
            with self.assertRaisesRegex(ValueError, "published typed packet identities"):
                cleanup.prepare_packet_cleanup(**{**args, "path": pending})
        finally:
            pending.rename(original)
        attempt = self.state["evidence"] / args["attempt"]
        attempt.mkdir(mode=0o700)
        try:
            with self.assertRaisesRegex(ValueError, "fresh cleanup attempt"):
                cleanup.prepare_packet_cleanup(**args)
        finally:
            attempt.rmdir()
        extra = original / "extra.json"
        extra.write_bytes(b"invented unclassified metadata")
        extra.chmod(0o600)
        try:
            with self.assertRaisesRegex(ValueError, "closed bundle namespace"):
                cleanup.prepare_packet_cleanup(**args)
        finally:
            extra.unlink()
        with self.assertRaisesRegex(ValueError, "Fresh empty"):
            fixture.build(self.state["parent"])

    def test_actual_owned_wholepacket_complete_and_cancel_keep_old_objects_and_states(self):
        unrelated = subprocess.Popen(
            [sys.executable, "-I", "-S", "-B", "-c", "import time;time.sleep(300)"],
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        try:
            for phase in ("complete", "quarantined"):
                with self.subTest(phase=phase), tempfile.TemporaryDirectory() as folder:
                    parent = Path(folder).resolve()
                    parent.chmod(0o700)
                    pins = fixture.prepare_case(parent)
                    if phase == "complete":
                        for field in ("request_sha256", "context_sha256", "source_sha256"):
                            bad = copy.deepcopy(pins)
                            bad[field] = "a" * 64
                            with self.subTest(pin=field), self.assertRaises(ValueError):
                                fixture.load_prepared(parent, bad)
                        for field in ("parent", "root", "evidence"):
                            bad = copy.deepcopy(pins)
                            bad[field]["inode"] += 1
                            with self.subTest(pin=field), self.assertRaises(ValueError):
                                fixture.load_prepared(parent, bad)
                        request_path = parent / "request.json"
                        original = request_path.read_bytes()
                        for field, value in (
                            ("kind", "private-data"),
                            ("attempt", "other-attempt"),
                            ("evidence_parent", str(parent / "other-evidence")),
                            ("root", {**pins["root"], "path": str(parent / "other-target")}),
                        ):
                            changed = json.loads(original)
                            changed[field] = value
                            raw = wire.encoded(changed)
                            request_path.write_bytes(raw)
                            bad = copy.deepcopy(pins)
                            bad["request_sha256"] = wire.digest(raw)
                            if field == "root":
                                bad["root"] = value
                            try:
                                with self.subTest(boundary=field), self.assertRaises(ValueError):
                                    fixture.load_prepared(parent, bad)
                            finally:
                                request_path.write_bytes(original)
                        self.assertEqual(fixture.load_prepared(parent, pins)[0], original)
                    stopped, done = threading.Event(), threading.Event()

                    def watch():
                        while not done.wait(0.01):
                            if (parent / "ready").exists():
                                stopped.set()
                                return

                    watcher = threading.Thread(target=watch) if phase == "quarantined" else None
                    if watcher:
                        watcher.start()
                    try:
                        with tempfile.TemporaryDirectory() as logs:
                            outer = supervise(
                                [
                                    sys.executable,
                                    "-I",
                                    "-S",
                                    "-B",
                                    str(ROOT / "tests/lt1_packet_cleanup_fixture.py"),
                                    str(parent),
                                    phase,
                                    wire.encoded(pins).decode("utf-8"),
                                ],
                                Path(logs) / "process.log",
                                timeout=60,
                                grace=0.2,
                                cancel=stopped,
                                environment={"LANG": "C", "LC_ALL": "C", "PATH": "/usr/bin:/bin"},
                            )
                            log = (Path(logs) / "process.log").read_bytes()
                    finally:
                        done.set()
                        if watcher:
                            watcher.join(timeout=1)
                    self.assertEqual(
                        outer["status"], "completed" if phase == "complete" else "interrupted", log
                    )
                    self.assertEqual(outer["remaining_owned_processes"], [])
                    self.assertEqual(len(outer["owned_processes"]), 1)
                    self.assertEqual(outer["received_signals"], [])
                    self.assertIsNone(unrelated.poll())
                    raw, context = (
                        (parent / "request.json").read_bytes(),
                        (parent / "context.bin").read_bytes(),
                    )
                    journal = (parent / "cleanup-evidence/remove-packet/events.jsonl").read_bytes()
                    read = cleanup.removal.inspect(
                        raw, wire.digest(raw), context, wire.digest(journal), outer
                    )
                    self.assertEqual(
                        read["status"], "completed" if phase == "complete" else "incomplete"
                    )
                    self.assertTrue(all(read[k] is False for k in cleanup.removal.AUTHORITY))
                    before = json.loads((parent / "before.json").read_bytes())
                    self.assertTrue(before["production_gate_refused"])
                    self.assertEqual(
                        wire.digest(wire.encoded(before["producer_receipt"])),
                        before["producer_receipt_sha256"],
                    )
                    self.assertEqual(before["producer_receipt"]["status"], "completed")
                    self.assertEqual(before["producer_receipt"]["remaining_owned_processes"], [])
                    self.assertIs(
                        before["retained_fixture_metadata_copy_accounted_or_approved"], False
                    )
                    self.assertEqual(
                        wire.digest((parent / "producer/proposed-register.json").read_bytes()),
                        before["old_registration_sha256"],
                    )
                    self.assertEqual(
                        wire.digest((parent / "producer/original-object.txt").read_bytes()),
                        before["old_original_sha256"],
                    )
                    self.assertEqual(
                        before["deadlines"],
                        {"object-one": "2026-11-08T00:00:00Z", "unknown-object": None},
                    )
                    accounting_raw = (parent / "accounting.json").read_bytes()
                    self.assertEqual(wire.digest(accounting_raw), before["accounting_sha256"])
                    accounting = json.loads(accounting_raw)
                    for subject, copy_id in before["packet_copy_ids"].items():
                        self.assertEqual(
                            accounting["subjects"][subject]["copies"][copy_id]["state"], "present"
                        )
                    names = sorted(before["packet_files"])
                    self.assertEqual(read["recorded_removed"], names if phase == "complete" else [])
                    self.assertEqual(
                        read["target_present"], [] if phase == "complete" else names[1:]
                    )
                    self.assertEqual(read["quarantined"], [] if phase == "complete" else names[:1])
                    for name in read["target_present"]:
                        self.assertEqual(
                            wire.digest((parent / "store/packet" / name).read_bytes()),
                            before["packet_files"][name]["sha256"],
                        )
        finally:
            unrelated.terminate()
            unrelated.wait(timeout=3)
