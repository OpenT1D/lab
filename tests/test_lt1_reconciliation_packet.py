"""Actual owned metadata producer to immutable private packet; all gates closed."""

import copy
import json
import os
import shutil
import sys
import tempfile
import threading
import unittest
from pathlib import Path
from unittest.mock import patch

import lt1_reconciliation_packet_fixture as fixture

from experiments.lt1_diagnostic import reconciliation_packet as packet
from experiments.shared_services.execution import supervise

ROOT = Path(__file__).resolve().parents[1]
wire, bundle = packet.wire, packet.bundle


def owned_case(parent, phase):
    stopped, done = threading.Event(), threading.Event()

    def watch():
        while not done.wait(0.01):
            if (parent / "ready").exists():
                stopped.set()
                return

    thread = threading.Thread(target=watch) if phase == "quarantined" else None
    if thread:
        thread.start()
    try:
        with tempfile.TemporaryDirectory() as logs:
            outer = supervise(
                [
                    sys.executable,
                    "-I",
                    "-S",
                    "-B",
                    str(ROOT / "tests/lt1_reconciliation_packet_fixture.py"),
                    str(parent),
                    phase,
                ],
                Path(logs) / "process.log",
                timeout=30,
                grace=0.2,
                cancel=stopped,
                environment={"LANG": "C", "LC_ALL": "C", "PATH": "/usr/bin:/bin"},
            )
            log = (Path(logs) / "process.log").read_bytes()
    finally:
        done.set()
        if thread:
            thread.join(timeout=1)
    if outer["remaining_owned_processes"] != [] or outer["status"] != (
        "completed" if phase == "complete" else "interrupted"
    ):
        raise AssertionError((outer, log))
    return outer


@unittest.skipUnless(os.name == "posix", "POSIX private packet fixture required")
class ReconciliationPacketTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.producer_storage = tempfile.TemporaryDirectory()
        cls.addClassCleanup(cls.producer_storage.cleanup)
        cls.producer = Path(cls.producer_storage.name).resolve()
        cls.producer.chmod(0o700)
        cls.outer = owned_case(cls.producer, "complete")
        cls.original_inputs = fixture.inputs(
            cls.producer, wire.encoded(cls.outer), packet.reconciliation
        )

    def setUp(self):
        storage = tempfile.TemporaryDirectory()
        self.addCleanup(storage.cleanup)
        self.parent = Path(storage.name).resolve()
        self.parent.chmod(0o700)
        self.output = self.parent / "evidence"
        self.inputs = copy.deepcopy(self.original_inputs)
        current = json.loads(self.inputs["registration_raw"])
        stem = self._testMethodName[5:30].replace("_", "-")
        self.copy_ids = {
            name: f"packet-{stem}-{i}" for i, name in enumerate(sorted(current["subjects"]))
        }

    def save(self, **options):
        return packet.save_packet(
            self.output,
            copy_ids=self.copy_ids,
            expected_identity=packet.source_identity(),
            **self.inputs,
            **options,
        )

    def inspect(self, saved, **options):
        return packet.inspect_packet(
            self.output,
            saved["manifest_sha256"],
            self.inputs["expected_registration_sha256"],
            self.inputs["expected_context_sha256"],
            expected_identity=packet.source_identity(),
            **options,
        )

    def assert_closed(self, result):
        self.assertTrue(all(result[key] is False for key in packet.AUTHORITY))
        self.assertTrue(result["new_bundle_copy_registration_required"])
        self.assertFalse(result["global_copy_coverage_verified"])

    def test_owned_complete_packet_replays_exact_bytes_and_keeps_proposals_separate(self):
        before = copy.deepcopy(self.inputs)
        saved = self.save()
        self.assertEqual(saved["status"], "published")
        self.assertEqual(saved["reconciliation"]["status"], "proposed")
        read = self.inspect(saved)
        self.assertEqual(read["reconciliation"], saved["reconciliation"])
        self.assertEqual(read["packet_copy_accounting"], saved["packet_copy_accounting"])
        self.assertEqual((self.output / "outer.json").read_bytes(), wire.encoded(self.outer))
        self.assertEqual(
            wire.digest((self.output / "outer.json").read_bytes()),
            self.inputs["expected_outer_sha256"],
        )
        self.assertTrue(self.outer["owned_processes"])
        base = json.loads(self.inputs["registration_raw"])
        proposed = json.loads(read["packet_copy_accounting"]["register_raw"])
        for name, old in base["subjects"].items():
            for key in ("retained_since", "origin_evidence_sha256", "hold"):
                self.assertEqual(proposed["subjects"][name][key], old[key])
            for copy_id, record in old["copies"].items():
                self.assertEqual(proposed["subjects"][name]["copies"][copy_id], record)
            new_id = self.copy_ids[name]
            self.assertEqual(proposed["subjects"][name]["copies"][new_id]["state"], "present")
            self.assertEqual(
                proposed["previous_sha256"], self.inputs["expected_registration_sha256"]
            )
        self.assertFalse(read["packet_copy_accounting"]["reconciliation_proposal_adopted"])
        self.assertEqual(
            read["packet_copy_accounting"]["assessment"]["deadlines"],
            {"object-one": "2026-11-08T00:00:00Z", "unknown-object": None},
        )
        self.assertEqual(self.inputs, before)
        self.assertFalse(read["active_register_changed"])
        self.assert_closed(read)
        with self.assertRaisesRegex(ValueError, "intent required"):
            bundle.inspect_bundle(
                self.output,
                saved["manifest_sha256"],
                self.inputs["expected_registration_sha256"],
                self.inputs["expected_context_sha256"],
                as_of=self.inputs["as_of"],
            )

    def test_owned_cancel_prefix_is_saved_without_absence_or_register_activation(self):
        with tempfile.TemporaryDirectory() as folder:
            parent = Path(folder).resolve()
            parent.chmod(0o700)
            outer = owned_case(parent, "quarantined")
            self.assertEqual(outer["error"], "Cancelled")
            self.inputs = fixture.inputs(parent, wire.encoded(outer), packet.reconciliation)
            saved = self.save()
            read = self.inspect(saved)
            self.assertEqual(read["reconciliation"]["status"], "incomplete")
            self.assertEqual(
                read["reconciliation"]["register_raw"], self.inputs["registration_raw"]
            )
            self.assertTrue(list((parent / "reports/remove-derived-bundle/quarantine").iterdir()))
            self.assert_closed(read)

    def test_intent_is_first_durable_copy_and_allocation_is_detached(self):
        stopped = False
        original = copy.deepcopy(self.copy_ids)

        def checkpoint(event, _name):
            nonlocal stopped
            if event == "intent":
                self.copy_ids.clear()
                stopped = True

        result = self.save(stop=lambda: stopped, checkpoint=checkpoint)
        pending = Path(result["pending"])
        self.assertEqual({p.name for p in pending.iterdir()}, {packet.INTENT})
        intent = json.loads((pending / packet.INTENT).read_bytes())
        self.assertEqual(intent["copies"], original)
        self.assertIsNone(intent["subjects"]["unknown-object"]["retained_since"])
        self.assertTrue(intent["subjects"]["unknown-object"]["hold"])
        self.assertFalse(self.output.exists())
        self.assert_closed(result)

    def test_complete_pending_packet_is_not_published_and_is_retained(self):
        stopped = False

        def checkpoint(event, _name):
            nonlocal stopped
            if event == "prepared":
                stopped = True

        saved = self.save(stop=lambda: stopped, checkpoint=checkpoint)
        pending = Path(saved["pending"])
        manifest_sha = wire.digest((pending / bundle.MANIFEST).read_bytes())
        with self.assertRaisesRegex(ValueError, "published packet root/leaf"):
            packet.inspect_packet(
                pending,
                manifest_sha,
                self.inputs["expected_registration_sha256"],
                self.inputs["expected_context_sha256"],
                expected_identity=packet.source_identity(),
            )
        self.assertTrue(pending.exists())
        self.assertFalse(self.output.exists())

    def test_publication_collision_keeps_foreign_directory_and_complete_pending(self):
        def collide(event, _name):
            if event == "prepared":
                self.output.mkdir(mode=0o700)
                (self.output / "sentinel").write_bytes(b"invented foreign object")

        result = self.save(checkpoint=collide)
        self.assertEqual(result["status"], "failed")
        self.assertEqual((self.output / "sentinel").read_bytes(), b"invented foreign object")
        self.assertTrue((Path(result["pending"]) / bundle.MANIFEST).is_file())

    def test_bad_source_or_copy_allocation_refuses_before_packet_intake(self):
        with patch.object(bundle, "_opened", side_effect=AssertionError("private path")):
            with self.assertRaisesRegex(ValueError, "expected packet writer source"):
                packet.save_packet(
                    self.output, copy_ids=self.copy_ids, expected_identity={}, **self.inputs
                )
            for value in ({}, {name: "copy-live" for name in self.copy_ids}):
                with (
                    self.subTest(value=value),
                    patch.object(
                        packet.reconciliation,
                        "propose_reconciliation",
                        side_effect=AssertionError("replay"),
                    ),
                ):
                    with self.assertRaises(ValueError):
                        packet.save_packet(
                            self.output,
                            copy_ids=value,
                            expected_identity=packet.source_identity(),
                            **self.inputs,
                        )
        self.assertFalse(self.output.exists())

    def test_rehashed_packet_context_cannot_rebind_external_input_identity(self):
        self.save()
        (self.output / "context.bin").write_bytes(b"forged invented context")
        files = {p.name: p.read_bytes() for p in self.output.iterdir() if p.name != bundle.MANIFEST}
        manifest = bundle._manifest(files)
        (self.output / bundle.MANIFEST).write_bytes(manifest)
        with patch.object(
            bundle.removal, "inspect", side_effect=AssertionError("original namespace")
        ):
            with self.assertRaises(ValueError):
                packet.inspect_packet(
                    self.output,
                    wire.digest(manifest),
                    self.inputs["expected_registration_sha256"],
                    self.inputs["expected_context_sha256"],
                    expected_identity=packet.source_identity(),
                )
        self.assertTrue((self.output / "context.bin").exists())

    def test_final_same_byte_member_inode_replacement_is_refused(self):
        saved = self.save()
        actual, calls = packet.source_identity, 0

        def replace():
            nonlocal calls
            value = actual()
            calls += 1
            if calls == 3:
                path = self.output / "registration.json"
                raw = path.read_bytes()
                path.rename(self.parent / "retained-original-registration")
                path.write_bytes(raw)
                path.chmod(0o600)
            return value

        with patch.object(packet, "source_identity", side_effect=replace):
            with self.assertRaisesRegex(ValueError, "packet changed during replay"):
                self.inspect(saved)

    def test_recreated_original_namespace_refuses_current_packet_replay(self):
        saved = self.save()
        path = self.producer / "bundle/recreated"
        path.write_bytes(b"invented recreated original namespace")
        self.addCleanup(path.unlink)
        with self.assertRaisesRegex(ValueError, "unexpected retained"):
            self.inspect(saved)
        self.assertTrue(self.output.is_dir())

    def test_physical_packet_duplicate_cannot_reuse_allocated_copy_ids(self):
        saved = self.save()
        duplicate_parent = self.parent / "duplicate-parent"
        duplicate_parent.mkdir(mode=0o700)
        duplicate = duplicate_parent / self.output.name
        shutil.copytree(self.output, duplicate)
        with self.assertRaisesRegex(ValueError, "published packet root/leaf"):
            packet.inspect_packet(
                duplicate,
                saved["manifest_sha256"],
                self.inputs["expected_registration_sha256"],
                self.inputs["expected_context_sha256"],
                expected_identity=packet.source_identity(),
            )

    def test_after_accounting_replacement_never_returns_verified_packet(self):
        actual = packet._accounting

        def replace(path, *args):
            result = actual(path, *args)
            retained = path.parent / (path.name + "-retained-original")
            path.rename(retained)
            shutil.copytree(retained, path)
            path.chmod(0o700)
            return result

        with patch.object(packet, "_accounting", side_effect=replace):
            result = self.save()
        self.assertEqual(result["status"], "publication-uncertain")
        self.assertTrue(result["published"])
        self.assertTrue((self.parent / "evidence-retained-original").is_dir())
        self.assertTrue(self.output.is_dir())
        self.output = self.parent / "read-evidence"
        saved = self.save()
        with patch.object(packet, "_accounting", side_effect=replace):
            with self.assertRaisesRegex(ValueError, "directory binding"):
                self.inspect(saved)
        self.assertTrue((self.parent / "read-evidence-retained-original").is_dir())
