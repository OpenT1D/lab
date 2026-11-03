"""Fresh invented metadata bundles only; no live pilot, runtime or removal."""

import copy
import json
import os
import stat
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import test_lt1_recovery_readback as fixtures

from experiments.lt1_diagnostic import review_bundle as bundle


@unittest.skipUnless(os.name == "posix", "POSIX private bundle storage required")
class ReviewBundleTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.parent = Path(temp.name).resolve()
        self.parent.chmod(0o700)
        self.output = self.parent / "review"
        self.fixture = fixtures.RecoveryReadbackTests()
        self.fixture.setUp()
        self.context = b"invented independently reviewed storage context\n"
        context_sha = bundle.bridge.digest(self.context)
        self.fixture.fixture.context = context_sha
        self.fixture.current["coverage"]["context_sha256"] = context_sha
        self.fixture.fixture.scope["context_sha256"] = context_sha
        self.fixture.mapping["context_sha256"] = context_sha
        self.inputs = self.fixture.args()
        self.active = self.parent / "active.json"
        self.active.write_bytes(self.inputs["register_raw"])
        self.active.chmod(0o600)

    def save(self, **options):
        return bundle.save_review_bundle(self.output, **self.inputs, **options)

    def inspect(self, saved, **options):
        values = {
            "expected_manifest_sha256": saved["manifest_sha256"],
            "expected_current_register_sha256": self.inputs["expected_register_sha256"],
            "expected_context_sha256": self.inputs["expected_context_sha256"],
            "as_of": self.inputs["as_of"],
        }
        values.update(options)
        return bundle.inspect_bundle(self.output, **values)

    def assert_false_gates(self, result):
        self.assertTrue(all(result[key] is False for key in bundle.AUTHORITY))

    def test_roundtrip_exact_bytes_and_active_register_untouched(self):
        original = copy.deepcopy(self.inputs)
        result = self.save()
        self.assertEqual(result["status"], "published")
        self.assertTrue(result["durability_confirmed"])
        read = self.inspect(result)
        self.assertEqual(read["status"], "verified-proposal")
        self.assertEqual(read["stored_assessment"]["as_of"], self.inputs["as_of"])
        self.assertEqual(self.active.read_bytes(), self.inputs["register_raw"])
        self.assertEqual(self.inputs, original)
        self.assertEqual((self.output / "register.json").read_bytes(), self.inputs["register_raw"])
        self.assertEqual(stat.S_IMODE(self.output.stat().st_mode), 0o700)
        for path in self.output.iterdir():
            self.assertEqual(stat.S_IMODE(path.stat().st_mode), 0o600)
            self.assertEqual(path.stat().st_nlink, 1)
            bundle.removal.safe_name(path.name)
        self.assert_false_gates(result)
        self.assert_false_gates(read)

    def test_intent_is_durable_before_copies_and_keeps_unknown_origins_holds(self):
        subject = self.fixture.current["subjects"]["object-one"]
        subject.update(retained_since=None, origin_evidence_sha256=None, hold=True)
        self.inputs = self.fixture.args()
        stopped = False

        def stop_after_intent(event, _name):
            nonlocal stopped
            if event == "intent":
                stopped = True

        result = self.save(stop=lambda: stopped, checkpoint=stop_after_intent)
        self.assertEqual(result["status"], "interrupted")
        pending = Path(result["pending"])
        self.assertEqual({p.name for p in pending.iterdir()}, {bundle.INTENT})
        intent = json.loads((pending / bundle.INTENT).read_bytes())
        inherited = intent["subjects"]["object-one"]
        self.assertIsNone(inherited["retained_since"])
        self.assertIsNone(inherited["origin_evidence_sha256"])
        self.assertTrue(inherited["hold"])
        self.assertEqual(intent["context_sha256"], self.inputs["expected_context_sha256"])
        self.assertFalse(self.output.exists())
        self.assert_false_gates(result)

    def test_known_origin_and_existing_predecessor_are_retained(self):
        prior = self.inputs["register_raw"]
        self.fixture.current["previous_sha256"] = bundle.bridge.digest(prior)
        self.inputs = self.fixture.args()
        self.inputs.update(previous_raw=prior, expected_previous_sha256=bundle.bridge.digest(prior))
        result = self.save()
        self.inspect(result)
        self.assertEqual((self.output / "previous.json").read_bytes(), prior)
        intent = json.loads((self.output / bundle.INTENT).read_bytes())
        self.assertEqual(
            intent["subjects"]["object-one"]["retained_since"],
            self.fixture.current["subjects"]["object-one"]["retained_since"],
        )
        self.assertNotIn("created_at", intent)

    def test_initial_cancel_creates_no_prefix(self):
        result = self.save(stop=lambda: True)
        self.assertEqual(result["status"], "interrupted")
        self.assertIsNone(result["pending"])
        self.assertEqual({p.name for p in self.parent.iterdir()}, {"active.json"})

    def test_write_failure_keeps_intent_and_owned_prefix(self):
        def fault(event, name):
            if event == "member" and name == "register.json":
                raise OSError("invented fault")

        result = self.save(checkpoint=fault)
        self.assertEqual(result["status"], "failed")
        pending = Path(result["pending"])
        self.assertTrue((pending / bundle.INTENT).is_file())
        self.assertEqual((pending / "register.json").read_bytes(), self.inputs["register_raw"])
        self.assertFalse(self.output.exists())
        self.assertEqual(self.active.read_bytes(), self.inputs["register_raw"])

    def test_target_and_pending_collisions_never_overwrite(self):
        self.output.mkdir(mode=0o700)
        sentinel = self.output / "sentinel"
        sentinel.write_bytes(b"invented collision")
        with self.assertRaisesRegex(ValueError, "fresh"):
            self.save()
        self.assertEqual(sentinel.read_bytes(), b"invented collision")

    def test_collision_at_publication_keeps_foreign_target_and_pending(self):
        def collide(event, _name):
            if event == "prepared":
                self.output.mkdir(mode=0o700)
                (self.output / "sentinel").write_bytes(b"invented collision")

        result = self.save(checkpoint=collide)
        self.assertFalse(result["published"])
        self.assertEqual(result["status"], "failed")
        self.assertTrue(Path(result["pending"]).is_dir())
        self.assertEqual((self.output / "sentinel").read_bytes(), b"invented collision")

    def test_committed_rename_followed_by_error_is_uncertain_and_retained(self):
        original = bundle.exclusive_rename

        def fail_after_rename(source, target):
            original(source, target)
            raise OSError("invented post-rename fault")

        with patch.object(bundle, "exclusive_rename", side_effect=fail_after_rename):
            result = self.save()
        self.assertEqual(result["status"], "publication-uncertain")
        self.assertTrue(result["published"])
        self.assertFalse(result["durability_confirmed"])
        self.assertIsNone(result["pending"])
        self.inspect(result)

    def test_failed_parent_fsync_after_publish_never_deletes_target(self):
        original = bundle.os.fsync

        def fail_parent(fd):
            if self.output.exists() and os.fstat(fd).st_ino == self.parent.stat().st_ino:
                raise OSError("invented parent fsync fault")
            return original(fd)

        with patch.object(bundle.os, "fsync", side_effect=fail_parent):
            result = self.save()
        self.assertEqual(result["status"], "publication-uncertain")
        self.assertTrue(self.output.is_dir())
        self.assertFalse(result["durability_confirmed"])
        self.inspect(result)

    def test_stored_assessment_is_not_refreshed_or_overwritten(self):
        result = self.save()
        stored = (self.output / "assessment.json").read_bytes()
        read = self.inspect(result, as_of="2026-11-05T12:10:00Z")
        self.assertEqual(read["stored_assessment"]["as_of"], self.inputs["as_of"])
        self.assertEqual(read["current_assessment"]["as_of"], "2026-11-05T12:10:00Z")
        self.assertTrue(any("stale" in reason for reason in read["current_assessment"]["blockers"]))
        self.assertEqual((self.output / "assessment.json").read_bytes(), stored)
        with self.assertRaisesRegex(ValueError, "clock reversed"):
            self.inspect(result, as_of="2026-11-05T11:59:59Z")

    def test_external_manifest_current_register_and_context_are_required(self):
        result = self.save()
        for key in (
            "expected_manifest_sha256",
            "expected_current_register_sha256",
            "expected_context_sha256",
        ):
            with self.subTest(key=key), self.assertRaises(ValueError):
                self.inspect(result, **{key: "f" * 64})

    def test_rehashed_forged_assessment_cannot_pass_replay(self):
        result = self.save()
        changed = self.output / "assessment.json"
        value = json.loads(changed.read_bytes())
        value["scoped_removal_evidence_complete"] = True
        changed.write_bytes(bundle.bridge.encoded(value))
        files = {p.name: p.read_bytes() for p in self.output.iterdir() if p.name != bundle.MANIFEST}
        raw = bundle._manifest(files)
        (self.output / bundle.MANIFEST).write_bytes(raw)
        with self.assertRaisesRegex(ValueError, "exact stored proposal replay"):
            self.inspect(result, expected_manifest_sha256=bundle.bridge.digest(raw))

    def test_extra_symlink_hardlink_or_wrong_mode_cannot_be_adopted(self):
        result = self.save()
        extra = self.output / "extra.json"
        extra.write_bytes(b"invented")
        extra.chmod(0o600)
        with self.assertRaisesRegex(ValueError, "closed bundle"):
            self.inspect(result)
        extra.unlink()
        member = self.output / "assessment.json"
        original = member.read_bytes()
        member.unlink()
        member.symlink_to(self.active)
        with self.assertRaisesRegex(ValueError, "single-link member"):
            self.inspect(result)
        member.unlink()
        member.write_bytes(original)
        member.chmod(0o600)
        member.chmod(0o644)
        with self.assertRaisesRegex(ValueError, "single-link member"):
            self.inspect(result)
        member.chmod(0o600)
        os.link(member, self.parent / "invented-hardlink")
        with self.assertRaisesRegex(ValueError, "single-link member"):
            self.inspect(result)

    def test_changed_member_after_last_source_consumption_refuses(self):
        result = self.save()
        original = bundle.source_identity
        calls = 0

        def alter():
            nonlocal calls
            value = original()
            calls += 1
            if calls == 2:
                (self.output / "assessment.json").write_bytes(b"invented changed")
            return value

        with patch.object(bundle, "source_identity", side_effect=alter):
            with self.assertRaises(ValueError):
                self.inspect(result)

    def test_bounds_and_invalid_lineage_refuse_before_staging(self):
        with patch.object(bundle.removal, "TOTAL_LIMIT", 1):
            with self.assertRaisesRegex(ValueError, "aggregate byte"):
                self.save()
        self.assertFalse(self.output.exists())
        self.assertFalse((self.parent / "review.pending").exists())
        self.inputs["expected_register_sha256"] = "f" * 64
        with self.assertRaises(ValueError):
            self.save()
        self.assertFalse((self.parent / "review.pending").exists())

    def test_entire_bundle_request_is_unadmitted_and_nothing_is_saved(self):
        result = self.save()
        evidence = self.parent / "removal-evidence"
        evidence.mkdir(mode=0o700)
        host = {
            "platform": "darwin",
            "machine": "arm64",
            "name": "invented-host",
            "uid": os.getuid(),
        }
        registry = bundle.removal.HERE / "removal-admissions.json"
        registry_before = registry.read_bytes()
        with (
            patch.object(bundle.removal, "host", return_value=host),
            patch.object(bundle.removal, "remove", side_effect=AssertionError("removal")),
            patch("subprocess.run", side_effect=AssertionError("process")),
        ):
            prepared = bundle.prepare_removal_request(
                self.output,
                result["manifest_sha256"],
                self.inputs["expected_register_sha256"],
                self.inputs["expected_context_sha256"],
                as_of=self.inputs["as_of"],
                context_raw=self.context,
                evidence_parent=evidence,
                attempt="invented-removal",
            )
            request = bundle.removal._request(prepared["request_raw"], self.context)
        self.assertEqual(set(request["files"]), {p.name for p in self.output.iterdir()})
        self.assertEqual(request["root"]["path"], str(self.output))
        for name, signature in request["files"].items():
            self.assertEqual(signature["inode"], (self.output / name).stat().st_ino)
            self.assertEqual(signature["ctime_ns"], (self.output / name).stat().st_ctime_ns)
        self.assertEqual(list(evidence.iterdir()), [])
        self.assertEqual(registry.read_bytes(), registry_before)
        self.assert_false_gates(prepared)

    def test_removal_context_and_nested_evidence_refuse(self):
        result = self.save()
        args = (
            self.output,
            result["manifest_sha256"],
            self.inputs["expected_register_sha256"],
            self.inputs["expected_context_sha256"],
        )
        with self.assertRaisesRegex(ValueError, "context bytes"):
            bundle.prepare_removal_request(
                *args,
                as_of=self.inputs["as_of"],
                context_raw=b"changed",
                evidence_parent=self.parent,
                attempt="invented",
            )
        with self.assertRaisesRegex(ValueError, "separate removal"):
            bundle.prepare_removal_request(
                *args,
                as_of=self.inputs["as_of"],
                context_raw=self.context,
                evidence_parent=self.parent,
                attempt="invented",
            )

    def test_preexisting_pending_prefix_is_never_reused(self):
        pending = self.parent / "review.pending"
        pending.mkdir(mode=0o700)
        sentinel = pending / "intent.json"
        sentinel.write_bytes(b"invented interrupted predecessor")
        with self.assertRaisesRegex(ValueError, "fresh"):
            self.save()
        self.assertEqual(sentinel.read_bytes(), b"invented interrupted predecessor")
        self.assertFalse(self.output.exists())

    def test_keyboard_interrupt_keeps_only_durable_intent(self):
        def interrupt(event, _name):
            if event == "intent":
                raise KeyboardInterrupt()

        result = self.save(checkpoint=interrupt)
        self.assertEqual(result["status"], "interrupted")
        self.assertEqual({p.name for p in Path(result["pending"]).iterdir()}, {bundle.INTENT})
        self.assertFalse(self.output.exists())

    def test_changed_parent_mode_refuses_publication_without_cleanup(self):
        def change(event, _name):
            if event == "prepared":
                self.parent.chmod(0o755)

        try:
            result = self.save(checkpoint=change)
        finally:
            self.parent.chmod(0o700)
        self.assertEqual(result["status"], "failed")
        self.assertTrue(Path(result["pending"]).is_dir())
        self.assertFalse(self.output.exists())

    def test_rehashed_intent_cannot_reset_unknown_origin_or_remove_hold(self):
        self.fixture.current["subjects"]["object-one"].update(
            retained_since=None, origin_evidence_sha256=None, hold=True
        )
        self.inputs = self.fixture.args()
        result = self.save()
        path = self.output / bundle.INTENT
        intent = json.loads(path.read_bytes())
        intent["subjects"]["object-one"].update(
            retained_since=self.inputs["as_of"], origin_evidence_sha256="f" * 64, hold=False
        )
        path.write_bytes(bundle.bridge.encoded(intent))
        files = {p.name: p.read_bytes() for p in self.output.iterdir() if p.name != bundle.MANIFEST}
        raw = bundle._manifest(files)
        (self.output / bundle.MANIFEST).write_bytes(raw)
        with self.assertRaisesRegex(ValueError, "exact stored proposal replay"):
            self.inspect(result, expected_manifest_sha256=bundle.bridge.digest(raw))
