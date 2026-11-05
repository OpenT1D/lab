"""Fresh invented mixed-parent leaves only; all production admissions stay closed."""

import json
import os
import tempfile
import threading
import unittest
from pathlib import Path
from unittest.mock import patch

from experiments.lt1_diagnostic import historical_leaf_removal as leaf
from experiments.lt1_diagnostic import removal
from tests.lt1_historical_leaf_fixture import directory, outer, prepare


class HistoricalLeafAdmissionTests(unittest.TestCase):
    def test_production_membership_precedes_input_source_and_path_intake(self):
        with patch.object(leaf, "_request", side_effect=AssertionError("input intake")):
            with self.assertRaisesRegex(ValueError, "no reviewed removal request"):
                leaf.remove(b"not json", object())

    def test_unknown_request_does_not_intake_cancel_object(self):
        class Cancel:
            @property
            def is_set(self):
                raise AssertionError("cancel intake before admission")

        with self.assertRaisesRegex(ValueError, "no reviewed removal request"):
            leaf.remove(b"not json", object(), cancel=Cancel())

    def test_unknown_fixture_request_does_not_call_provider_or_stop(self):
        def forbidden():
            raise AssertionError("callback intake before admission")

        registry = {"schema": "opent1d.lt1-removal-admissions/1", "requests": []}
        with self.assertRaisesRegex(ValueError, "no reviewed removal request"):
            leaf._remove_reviewed(
                b"not json", registry, object(), stop=forbidden, _registry_provider=forbidden
            )


@unittest.skipUnless(os.name == "posix", "POSIX invented namespace required")
class HistoricalLeafTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.parent = Path(self.temp.name).resolve()
        self.raw, self.registry, self.context, self.target, self.attempt = prepare(self.parent)

    def run_removal(self, **kwargs):
        return leaf._remove_reviewed(self.raw, self.registry, self.context, **kwargs)

    def read(self, outer_raw=None):
        journal = (self.attempt / "events.jsonl").read_bytes()
        raw_outer = outer(self.raw) if outer_raw is None else outer_raw
        return leaf.inspect(
            self.raw,
            leaf.digest(self.raw),
            self.context,
            leaf.digest(journal),
            raw_outer,
            leaf.digest(raw_outer),
        )

    def revise(self, change):
        request = json.loads(self.raw)
        change(request)
        self.raw = (json.dumps(request, sort_keys=True) + "\n").encode()
        self.registry["requests"] = [leaf.digest(self.raw)]

    def refresh_root(self):
        self.revise(lambda r: r.update(root=directory(self.target.parent)))

    def assert_sentinels(self):
        self.assertEqual(
            (self.target.parent / "preserved.txt").read_bytes(), b"invented unrelated sibling\n"
        )
        self.assertEqual(
            (self.target.parent / "preserved-folder/untouched.txt").read_bytes(),
            b"invented nested sentinel\n",
        )

    def test_complete_removes_only_target_and_preserves_immediate_sibling_metadata(self):
        expected = json.loads(self.raw)["siblings"]
        result = self.run_removal()
        self.assertEqual(result["status"], leaf.STATUS)
        self.assertFalse(self.target.exists())
        self.assert_sentinels()
        for name, record in expected.items():
            self.assertEqual(leaf.sibling_signature((self.target.parent / name).lstat()), record)
        report = self.read()
        self.assertEqual(report["status"], "completed")
        self.assertEqual(report["recorded_removed"], [self.target.name])
        self.assertEqual(report["reviewed_immediate_sibling_count"], 2)
        for key in leaf.AUTHORITY:
            self.assertIs(result[key], False)
            self.assertIs(report[key], False)

    def test_historical_flat_helper_still_refuses_the_mixed_namespace(self):
        request = json.loads(self.raw)
        old = {
            "schema": "opent1d.lt1-removal-request/1",
            "kind": "invented",
            "root": {k: request["root"][k] for k in ("path", "device", "inode", "uid")},
            "evidence_parent": request["evidence_parent"]["path"],
            "attempt": "old-attempt",
            "files": {self.target.name: request["target"]["file"]},
            "source_identity": removal.source_identity(),
            "host": removal.host(),
            "context_sha256": removal.digest(self.context),
        }
        raw = json.dumps(old, sort_keys=True).encode()
        registry = {"schema": "opent1d.lt1-removal-admissions/1", "requests": [removal.digest(raw)]}
        with self.assertRaisesRegex(ValueError, "closed initial inventory"):
            removal._remove_reviewed(raw, registry, self.context)
        self.assertTrue(self.target.exists())
        self.assert_sentinels()

    def test_initial_cancel_creates_nothing(self):
        result = self.run_removal(stop=lambda: True)
        self.assertEqual(result["status"], "interrupted")
        self.assertFalse(result["attempt_created"])
        self.assertFalse(self.attempt.exists())
        self.assertTrue(self.target.exists())

    def test_explicit_acl_and_process_context_cannot_be_unknown_or_false(self):
        context = json.loads(self.context)
        context["acl_scope_reviewed"] = False
        self.context = json.dumps(context, sort_keys=True).encode()
        self.revise(lambda r: r.update(context_sha256=leaf.digest(self.context)))
        with self.assertRaisesRegex(ValueError, "reviewed ACL/process"):
            self.run_removal()
        self.assertFalse(self.attempt.exists())

    def test_changed_bytes_are_refused_before_evidence_creation(self):
        self.target.write_bytes(b"invented changed bytes")
        with self.assertRaisesRegex(ValueError, "file identity changed"):
            self.run_removal()
        self.assertFalse(self.attempt.exists())
        self.assert_sentinels()

    def test_target_symlink_and_hardlink_refuse_without_touching_replacements(self):
        original = self.target.read_bytes()
        self.target.unlink()
        self.target.symlink_to(self.target.parent / "preserved.txt")
        self.refresh_root()
        with self.assertRaises(OSError):
            self.run_removal()
        self.target.unlink()
        self.target.write_bytes(original)
        self.target.chmod(0o600)
        os.link(self.target, self.parent / "alias")
        self.refresh_root()
        with self.assertRaisesRegex(ValueError, "single-link"):
            self.run_removal()
        self.assertEqual((self.parent / "alias").read_bytes(), original)
        self.assertFalse(self.attempt.exists())

    def test_replaced_sibling_or_new_immediate_name_refuses(self):
        sibling = self.target.parent / "preserved.txt"
        sibling.rename(self.parent / "old-sibling")
        sibling.write_bytes(b"invented replacement sibling")
        self.refresh_root()
        with self.assertRaisesRegex(ValueError, "sibling identity changed"):
            self.run_removal()
        (self.target.parent / "unlisted").mkdir()
        self.refresh_root()
        with self.assertRaisesRegex(ValueError, "immediate namespace changed"):
            self.run_removal()
        self.assertTrue(self.target.exists())

    def test_sibling_directory_is_not_recursively_claimed_immutable(self):
        nested = self.target.parent / "preserved-folder/untouched.txt"
        nested.write_bytes(b"independently changed nested fixture bytes")
        self.assertEqual(self.run_removal()["status"], leaf.STATUS)
        self.assertEqual(self.read()["status"], "completed")
        self.assertEqual(nested.read_bytes(), b"independently changed nested fixture bytes")

    def test_renamed_parent_is_not_adopted(self):
        retained = self.parent / "retained-parent"

        def replace(event, _name):
            if event == "prepared":
                self.target.parent.rename(retained)
                self.target.parent.mkdir(mode=0o700)
                self.target.write_bytes(b"invented unrelated replacement")

        result = self.run_removal(checkpoint=replace)
        self.assertEqual(result["status"], "failed")
        self.assertTrue((retained / self.target.name).is_file())
        self.assertEqual(self.target.read_bytes(), b"invented unrelated replacement")

    def test_exclusive_attempt_collision_is_not_overwritten(self):
        self.attempt.mkdir(mode=0o700)
        (self.attempt / "sentinel").write_bytes(b"invented collision")
        self.revise(lambda r: r.update(evidence_parent=directory(self.attempt.parent)))
        with self.assertRaises(FileExistsError):
            self.run_removal()
        self.assertTrue(self.target.is_file())
        self.assertEqual((self.attempt / "sentinel").read_bytes(), b"invented collision")

    def test_quarantined_cancel_retains_target_and_never_resumes(self):
        stop = threading.Event()
        result = self.run_removal(
            stop=stop.is_set, checkpoint=lambda e, _n: stop.set() if e == "quarantined" else None
        )
        self.assertEqual(result["status"], "interrupted")
        self.assertEqual(result["removed"], [])
        self.assertTrue((self.attempt / "quarantine" / self.target.name).is_file())
        self.assertEqual(self.read()["status"], "incomplete")
        with self.assertRaises(ValueError):
            self.run_removal()
        self.assert_sentinels()

    def test_membership_withdrawn_before_move_keeps_original_and_incomplete_prefix(self):
        def withdraw(event, _name):
            if event == "prepared":
                self.registry["requests"].clear()

        result = self.run_removal(checkpoint=withdraw)
        self.assertEqual(result["status"], "failed")
        self.assertEqual(result["removed"], [])
        self.assertTrue(self.target.is_file())
        self.assertFalse(list((self.attempt / "quarantine").iterdir()))
        self.assertEqual(self.read()["status"], "incomplete")
        self.assert_sentinels()

    def test_membership_withdrawn_in_quarantine_never_unlinks(self):
        def withdraw(event, _name):
            if event == "quarantined":
                self.registry["requests"].clear()

        result = self.run_removal(checkpoint=withdraw)
        self.assertEqual(result["status"], "failed")
        self.assertEqual(result["removed"], [])
        retained = self.attempt / "quarantine" / self.target.name
        self.assertEqual(retained.read_bytes(), b'{"invented": true}\n')
        self.assertEqual(self.read()["status"], "incomplete")
        self.assert_sentinels()

    def test_withdrawal_during_final_source_check_before_move_is_observed(self):
        actual = leaf.source_identity()
        active, calls = False, 0

        def source():
            nonlocal calls
            if active:
                calls += 1
                if calls == 2:
                    self.registry["requests"].clear()
            return actual

        def checkpoint(event, _name):
            nonlocal active
            if event == "prepared":
                active = True

        with patch.object(leaf, "source_identity", side_effect=source):
            result = self.run_removal(checkpoint=checkpoint)
        self.assertEqual(result["status"], "failed")
        self.assertTrue(self.target.is_file())
        self.assertFalse(list((self.attempt / "quarantine").iterdir()))

    def test_withdrawal_during_final_source_check_before_unlink_is_observed(self):
        actual = leaf.source_identity()
        active, calls = False, 0

        def source():
            nonlocal calls
            if active:
                calls += 1
                if calls == 2:
                    self.registry["requests"].clear()
            return actual

        def checkpoint(event, _name):
            nonlocal active
            if event == "quarantined":
                active = True

        with patch.object(leaf, "source_identity", side_effect=source):
            result = self.run_removal(checkpoint=checkpoint)
        self.assertEqual(result["status"], "failed")
        self.assertEqual(result["removed"], [])
        self.assertTrue((self.attempt / "quarantine" / self.target.name).is_file())

    def test_withdrawal_after_unlink_cannot_report_completed_operation(self):
        def withdraw(event, _name):
            if event == "before-complete":
                self.registry["requests"].clear()

        result = self.run_removal(checkpoint=withdraw)
        self.assertEqual(result["status"], "failed")
        self.assertEqual(result["removed"], [self.target.name])
        self.assertFalse(self.target.exists())
        self.assertEqual(self.read()["status"], "incomplete")

    def test_public_remove_rereads_canonical_provider_after_prepared_event(self):
        actual = leaf.source_identity()

        def provider():
            return json.loads(json.dumps(self.registry))

        def source():
            journal = self.attempt / "events.jsonl"
            if journal.exists() and journal.stat().st_size:
                self.registry["requests"].clear()
            return actual

        with patch.object(leaf, "_canonical_registry", side_effect=provider) as read_registry:
            with patch.object(leaf, "source_identity", side_effect=source):
                result = leaf.remove(self.raw, self.context)
        self.assertGreater(read_registry.call_count, 2)
        self.assertEqual(result["status"], "failed")
        self.assertEqual(result["removed"], [])
        self.assertTrue(self.target.is_file())
        self.assertEqual(self.read()["status"], "incomplete")

    def test_readback_after_historical_completion_needs_no_current_admission(self):
        self.assertEqual(self.run_removal()["status"], leaf.STATUS)
        self.registry["requests"].clear()
        report = self.read()
        self.assertEqual(report["status"], "completed")
        self.assertTrue(all(report[key] is False for key in leaf.AUTHORITY))

    def test_unrecorded_move_and_unlink_gaps_never_complete(self):
        def fail(event, _name):
            if event == "moved-unrecorded":
                raise RuntimeError("invented interruption before move event")

        result = self.run_removal(checkpoint=fail)
        self.assertEqual(result["status"], "failed")
        report = self.read()
        self.assertEqual(report["status"], "incomplete")
        self.assertTrue(report["unrecorded_move_observed"])
        self.assertEqual(report["recorded_removed"], [])

    def test_unrecorded_unlink_is_absence_without_recorded_removal(self):
        def fail(event, _name):
            if event == "unlinked-unrecorded":
                raise RuntimeError("invented interruption before remove event")

        result = self.run_removal(checkpoint=fail)
        self.assertEqual(result["status"], "failed")
        report = self.read()
        self.assertEqual(report["status"], "incomplete")
        self.assertTrue(report["absence_without_recorded_removal"])

    def test_quarantine_replacement_is_never_unlinked(self):
        path = self.attempt / "quarantine" / self.target.name

        def replace(event, _name):
            if event == "quarantined":
                path.rename(self.parent / "retained-target")
                path.write_bytes(b"invented quarantine replacement")
                path.chmod(0o600)

        result = self.run_removal(checkpoint=replace)
        self.assertEqual(result["status"], "failed")
        self.assertEqual(result["removed"], [])
        self.assertEqual(path.read_bytes(), b"invented quarantine replacement")
        with self.assertRaisesRegex(ValueError, "file identity changed"):
            self.read()

    def test_journal_replacement_or_inplace_change_withdraws_before_move(self):
        def replace(event, _name):
            if event == "prepared":
                path = self.attempt / "events.jsonl"
                path.write_bytes(path.read_bytes() + b"{}\n")

        result = self.run_removal(checkpoint=replace)
        self.assertEqual(result["status"], "failed")
        self.assertEqual(result["removed"], [])
        self.assertTrue(self.target.is_file())

    def test_late_target_write_during_final_source_check_is_not_unlinked(self):
        actual = leaf.source_identity()
        active, calls = False, 0
        path = self.attempt / "quarantine" / self.target.name

        def source():
            nonlocal calls
            if active:
                calls += 1
                if calls == 2:
                    path.write_bytes(b"invented late changed bytes")
            return actual

        def checkpoint(event, _name):
            nonlocal active
            if event == "quarantined":
                active = True

        with patch.object(leaf, "source_identity", side_effect=source):
            result = self.run_removal(checkpoint=checkpoint)
        self.assertEqual(result["status"], "failed")
        self.assertEqual(result["removed"], [])
        self.assertEqual(path.read_bytes(), b"invented late changed bytes")

    def test_late_reader_source_hook_cannot_mutate_journal_into_completion(self):
        self.run_removal()
        actual, count = leaf.source_identity(), 0

        def source():
            nonlocal count
            count += 1
            if count == 3:
                path = self.attempt / "events.jsonl"
                path.write_bytes(path.read_bytes() + b"{}\n")
            return actual

        with patch.object(leaf, "source_identity", side_effect=source):
            with self.assertRaisesRegex(ValueError, "reader journal changed"):
                self.read()

    def test_late_reader_source_hook_rechecks_retained_target_bytes(self):
        stop = threading.Event()
        self.run_removal(
            stop=stop.is_set, checkpoint=lambda e, _n: stop.set() if e == "quarantined" else None
        )
        actual, count = leaf.source_identity(), 0

        def source():
            nonlocal count
            count += 1
            if count == 3:
                (self.attempt / "quarantine" / self.target.name).write_bytes(
                    b"invented late replacement bytes"
                )
            return actual

        with patch.object(leaf, "source_identity", side_effect=source):
            with self.assertRaisesRegex(ValueError, "file identity changed"):
                self.read()

    def test_source_withdrawal_before_move_keeps_original_and_prefix(self):
        def withdraw(event, _name):
            if event == "prepared":
                mock = patch.object(leaf, "source_identity", return_value={"changed": True})
                mock.start()
                self.addCleanup(mock.stop)

        result = self.run_removal(checkpoint=withdraw)
        self.assertEqual(result["status"], "failed")
        self.assertTrue(self.target.is_file())
        self.assertEqual(result["removed"], [])

    def test_namespace_change_after_unlink_is_failure_with_original_prefix(self):
        def change(event, _name):
            if event == "removed":
                (self.target.parent / "unexpected.txt").write_bytes(b"invented concurrent writer")

        result = self.run_removal(checkpoint=change)
        self.assertEqual(result["status"], "failed")
        self.assertFalse(self.target.exists())
        self.assertEqual(result["removed"], [self.target.name])
        with self.assertRaisesRegex(ValueError, "namespace changed"):
            self.read()

    def test_external_request_outer_and_journal_pins_refuse_changes(self):
        self.run_removal()
        journal = (self.attempt / "events.jsonl").read_bytes()
        raw_outer = outer(self.raw)
        arguments = [
            self.raw,
            leaf.digest(self.raw),
            self.context,
            leaf.digest(journal),
            raw_outer,
            leaf.digest(raw_outer),
        ]
        for index in (1, 3, 5):
            changed = arguments.copy()
            changed[index] = "0" * 64
            with self.subTest(index=index), self.assertRaisesRegex(ValueError, "external"):
                leaf.inspect(*changed)

    def test_failed_or_superficial_outer_receipts_cannot_complete(self):
        self.run_removal()
        pristine = json.loads(outer(self.raw))
        mutations = [
            lambda r: r.update(status="failed"),
            lambda r: r.update(exit_code=True),
            lambda r: r.update(error="invented failure"),
            lambda r: r.update(cleanup_forced=True),
            lambda r: r.update(remaining_owned_processes=None),
            lambda r: r.update(owned_processes=[]),
            lambda r: r["owned_processes"][0].update(pid=True),
            lambda r: r.pop("cleanup_forced"),
        ]
        for change in mutations:
            with self.subTest(change=change):
                record = json.loads(json.dumps(pristine))
                change(record["supervision"])
                self.assertEqual(self.read(json.dumps(record).encode())["status"], "incomplete")

    def test_genuine_shape_unrelated_command_cannot_be_rewrapped_as_own_completion(self):
        self.run_removal()
        record = json.loads(outer(self.raw))
        record["supervision"]["argv"] = ["unrelated-command"]
        with self.assertRaisesRegex(ValueError, "outer command correspondence"):
            self.read(json.dumps(record).encode())

    def test_truncated_final_event_is_incomplete(self):
        self.run_removal()
        path = self.attempt / "events.jsonl"
        path.write_bytes(path.read_bytes()[:-1])
        self.assertEqual(self.read()["status"], "incomplete")


if __name__ == "__main__":
    unittest.main()
