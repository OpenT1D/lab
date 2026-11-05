"""Only newly created invented bytes are moved or unlinked by these tests."""

import json
import os
import tempfile
import threading
import unittest
from pathlib import Path
from unittest.mock import patch

from experiments.lt1_diagnostic import removal
from tests.lt1_removal_fixture import prepare

OUTER = {
    "status": "completed",
    "exit_code": 0,
    "remaining_owned_processes": [],
    "received_signals": [],
}


class RemovalAuthorityTests(unittest.TestCase):
    def test_unknown_production_request_refuses_before_parsing_or_path_intake(self):
        with patch.object(removal, "_request", side_effect=AssertionError("path intake")):
            with self.assertRaisesRegex(ValueError, "no reviewed removal request"):
                removal.remove(b"not json", object())


@unittest.skipUnless(os.name == "posix", "POSIX fixture namespace required")
class RemovalTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.parent = Path(self.temp.name).resolve()
        self.raw, self.registry, self.context, self.target, self.attempt = prepare(self.parent)

    def run_removal(self, **kwargs):
        return removal._remove_reviewed(self.raw, self.registry, self.context, **kwargs)

    def inspect(self, outer=None):
        journal = (self.attempt / "events.jsonl").read_bytes()
        return removal.inspect(
            self.raw,
            removal.digest(self.raw),
            self.context,
            removal.digest(journal),
            OUTER if outer is None else outer,
        )

    def reidentify(self, change):
        request = json.loads(self.raw)
        change(request)
        self.raw = json.dumps(request, sort_keys=True).encode()
        self.registry["requests"] = [removal.digest(self.raw)]

    def test_complete_leaves_only_empty_owned_namespaces_and_no_authority(self):
        result = self.run_removal()
        self.assertEqual(result["status"], "namespace-absence-observed")
        self.assertEqual(list(self.target.iterdir()), [])
        self.assertEqual(list((self.attempt / "quarantine").iterdir()), [])
        read = self.inspect()
        self.assertEqual(read["status"], "completed")
        self.assertEqual(read["recorded_removed"], ["a.txt", "b.txt"])
        for key in removal.AUTHORITY:
            self.assertIs(result[key], False)
            self.assertIs(read[key], False)

    def test_initial_cancellation_mutates_nothing(self):
        result = self.run_removal(stop=lambda: True)
        self.assertEqual(result["status"], "interrupted")
        self.assertFalse(result["attempt_created"])
        self.assertEqual({p.name for p in self.target.iterdir()}, {"a.txt", "b.txt"})
        self.assertEqual(list(self.attempt.parent.iterdir()), [])

    def test_all_input_bytes_are_checked_before_creating_evidence_or_removing(self):
        path = self.target / "b.txt"
        path.chmod(0o600)
        path.write_bytes(b"changed invented bytes")
        with self.assertRaisesRegex(ValueError, "file identity changed"):
            self.run_removal()
        self.assertTrue((self.target / "a.txt").is_file())
        self.assertFalse(self.attempt.exists())

    def test_links_fifo_extra_entries_and_wrong_root_are_refused(self):
        path = self.target / "b.txt"
        original = path.read_bytes()
        path.unlink()
        path.symlink_to(self.target / "a.txt")
        with self.assertRaises(OSError):
            self.run_removal()
        path.unlink()
        os.mkfifo(path)
        with self.assertRaisesRegex(ValueError, "regular file"):
            self.run_removal()
        path.unlink()
        os.link(self.target / "a.txt", path)
        with self.assertRaisesRegex(ValueError, "single-link"):
            self.run_removal()
        path.unlink()
        path.write_bytes(original)
        path.chmod(0o400)
        (self.target / "extra.txt").write_bytes(b"invented unlisted")
        with self.assertRaisesRegex(ValueError, "closed initial inventory"):
            self.run_removal()
        self.assertFalse(self.attempt.exists())

    def test_quarantined_cancel_retains_data_and_cannot_resume(self):
        stop = threading.Event()
        result = self.run_removal(
            stop=stop.is_set,
            checkpoint=lambda event, _name: stop.set() if event == "quarantined" else None,
        )
        self.assertEqual(result["status"], "interrupted")
        self.assertEqual(result["removed"], [])
        self.assertEqual((self.attempt / "quarantine/a.txt").read_bytes(), b"invented-first")
        self.assertTrue((self.target / "b.txt").is_file())
        self.assertEqual(self.inspect()["status"], "incomplete")
        with self.assertRaisesRegex(ValueError, "closed initial inventory"):
            self.run_removal()

    def test_primary_failure_retains_exact_removed_prefix_and_remaining_file(self):
        def fail(event, _name):
            if event == "removed":
                raise RuntimeError("invented primary fault")

        result = self.run_removal(checkpoint=fail)
        self.assertEqual(result["status"], "failed")
        self.assertIn("invented primary fault", result["error"])
        self.assertEqual(result["removed"], ["a.txt"])
        self.assertEqual(self.inspect()["target_present"], ["b.txt"])
        self.assertEqual(self.inspect()["status"], "incomplete")

    def test_exclusive_move_never_overwrites_a_quarantine_collision(self):
        original = removal.exclusive_rename

        def collide(source, target):
            target.write_bytes(b"invented collision sentinel")
            original(source, target)

        with patch.object(removal, "exclusive_rename", side_effect=collide):
            result = self.run_removal()
        self.assertEqual(result["status"], "failed")
        self.assertEqual(result["removed"], [])
        self.assertEqual(
            (self.attempt / "quarantine/a.txt").read_bytes(), b"invented collision sentinel"
        )
        self.assertEqual((self.target / "a.txt").read_bytes(), b"invented-first")

    def test_swap_before_move_is_retained_after_post_move_identity_failure(self):
        original = removal.exclusive_rename

        def swap(source, target):
            source.rename(self.parent / "invented-retained-original")
            source.write_bytes(b"invented replacement")
            source.chmod(0o400)
            original(source, target)

        with patch.object(removal, "exclusive_rename", side_effect=swap):
            result = self.run_removal()
        self.assertEqual(result["status"], "failed")
        self.assertEqual(result["removed"], [])
        self.assertEqual((self.attempt / "quarantine/a.txt").read_bytes(), b"invented replacement")
        self.assertEqual(
            (self.parent / "invented-retained-original").read_bytes(), b"invented-first"
        )

    def test_journal_replacement_withdraws_before_any_removal(self):
        def replace(event, _name):
            if event == "prepared":
                journal = self.attempt / "events.jsonl"
                journal.rename(self.parent / "retained-journal")
                journal.write_bytes(b"invented forged journal")
                journal.chmod(0o600)

        result = self.run_removal(checkpoint=replace)
        self.assertEqual(result["status"], "failed")
        self.assertEqual(result["removed"], [])
        self.assertEqual({p.name for p in self.target.iterdir()}, {"a.txt", "b.txt"})

    def test_truncated_journal_keeps_lower_bound_and_never_completion(self):
        original_write = os.write
        calls = 0

        def partial(fd, content):
            nonlocal calls
            calls += 1
            if calls == 1:
                return original_write(fd, content[:3])
            raise OSError("invented journal failure")

        patcher = patch.object(removal.os, "write", side_effect=partial)

        def fail(event, _name):
            if event == "quarantined":
                patcher.start()

        try:
            result = self.run_removal(checkpoint=fail)
        finally:
            patcher.stop()
        self.assertEqual(result["status"], "failed")
        self.assertEqual(result["removed"], ["a.txt"])
        report = self.inspect()
        self.assertEqual(report["status"], "incomplete")
        self.assertTrue(report["truncated_journal"])
        self.assertEqual(report["recorded_removed"], [])
        self.assertEqual(report["target_present"], ["b.txt"])

    def test_marker_alone_wrong_outer_exit_and_rebound_root_never_complete(self):
        self.run_removal()
        for outer in (
            {**OUTER, "exit_code": 23},
            {**OUTER, "exit_code": False},
            {**OUTER, "exit_code": 0.0},
            {**OUTER, "error": "invented primary error"},
            {**OUTER, "cleanup_error": "invented cleanup failure"},
            {**OUTER, "status": "interrupted"},
            {**OUTER, "remaining_owned_processes": None},
            {**OUTER, "received_signals": [15]},
        ):
            self.assertEqual(self.inspect(outer)["status"], "incomplete")
        journal_path = self.attempt / "events.jsonl"
        original = journal_path.read_bytes()
        events = [json.loads(line) for line in original.splitlines()]
        events[-1]["error"] = "invented retained primary error"
        journal_path.write_bytes(b"".join((json.dumps(event) + "\n").encode() for event in events))
        self.assertEqual(self.inspect()["status"], "incomplete")
        journal_path.write_bytes(original)
        journal_path.chmod(0o644)
        with self.assertRaisesRegex(ValueError, "reader journal mode"):
            self.inspect()
        journal_path.chmod(0o600)
        self.target.rename(self.parent / "retained-empty-target")
        self.target.mkdir(mode=0o700)
        with self.assertRaisesRegex(ValueError, "reader root identity"):
            self.inspect()

    def test_reader_reobserves_namespace_and_journal_after_final_source_check(self):
        self.run_removal()
        original = removal.source_identity
        calls = 0

        def change():
            nonlocal calls
            result = original()
            calls += 1
            if calls == 2:
                (self.target / "a.txt").write_bytes(b"invented reappeared")
            return result

        with patch.object(removal, "source_identity", side_effect=change):
            with self.assertRaisesRegex(ValueError, "reader namespace changed"):
                self.inspect()

    def test_context_source_and_resource_bounds_refuse_before_mutation(self):
        self.context = b"invented changed context"
        with self.assertRaisesRegex(ValueError, "review context"):
            self.run_removal()
        self.context = b"invented independently reviewed storage/process context\n"
        with patch.object(removal, "source_identity", return_value={}):
            with self.assertRaisesRegex(ValueError, "host or source"):
                self.run_removal()
        with patch.object(removal, "MAX_FILES", 1):
            with self.assertRaisesRegex(ValueError, "file count"):
                self.run_removal()
        with patch.object(removal, "TOTAL_LIMIT", 1):
            with self.assertRaisesRegex(ValueError, "aggregate bytes"):
                self.run_removal()
        self.assertFalse(self.attempt.exists())
