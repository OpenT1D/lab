"""Actual owned Python stops against fresh invented removal namespaces only."""

import os
import sys
import tempfile
import threading
import unittest
from pathlib import Path

from experiments.lt1_diagnostic import removal
from experiments.shared_services.execution import supervise

ROOT = Path(__file__).resolve().parents[1]


@unittest.skipUnless(os.name == "posix", "POSIX removal fixture required")
class RemovalProcessTests(unittest.TestCase):
    def case(self, phase, *, cancel=False):
        with tempfile.TemporaryDirectory() as folder:
            parent = Path(folder).resolve()
            parent.chmod(0o700)
            cancellation, done = threading.Event(), threading.Event()

            def watcher():
                while not done.wait(0.01):
                    if (parent / "ready").is_file():
                        cancellation.set()
                        return

            thread = threading.Thread(target=watcher, daemon=True) if cancel else None
            if thread:
                thread.start()
            try:
                outer = supervise(
                    [
                        sys.executable,
                        "-I",
                        "-S",
                        "-B",
                        str(ROOT / "tests/lt1_removal_fixture.py"),
                        str(parent),
                        phase,
                    ],
                    parent / "process.log",
                    timeout=10 if cancel or phase == "complete" else 3,
                    grace=0.2,
                    cancel=cancellation,
                    environment={"LANG": "C", "LC_ALL": "C", "PATH": "/usr/bin:/bin"},
                )
            finally:
                done.set()
                if thread:
                    thread.join(timeout=1)
            self.assertEqual(outer["remaining_owned_processes"], [])
            self.assertEqual(outer["received_signals"], [])
            complete = phase == "complete"
            self.assertEqual(
                outer["status"], "completed" if complete else "interrupted" if cancel else "failed"
            )
            self.assertEqual(
                outer["error"], None if complete else "Cancelled" if cancel else "WorkerDeadline"
            )
            if not complete:
                self.assertTrue(
                    (parent / "ready").is_file(), "Stop must follow the intended checkpoint"
                )
                self.assertFalse((parent / "outcome.json").exists())
            raw, context = (
                (parent / "request.json").read_bytes(),
                (parent / "context.txt").read_bytes(),
            )
            attempt = parent / "reports/attempt-one"
            journal = (attempt / "events.jsonl").read_bytes()
            report = removal.inspect(
                raw, removal.digest(raw), context, removal.digest(journal), outer
            )
            self.assertEqual(report["status"], "completed" if complete else "incomplete")
            self.assertFalse(report["effective_erasure_verified"])
            self.assertFalse(report["new_authority_granted"])
            expected_target = (
                []
                if complete
                else ["b.txt"]
                if phase in {"quarantined", "removed"}
                else ["a.txt", "b.txt"]
            )
            self.assertEqual(report["target_present"], expected_target)
            for name in expected_target:
                self.assertEqual(
                    (parent / "target" / name).read_bytes(),
                    {"a.txt": b"invented-first", "b.txt": b"invented-second"}[name],
                )
            self.assertEqual(report["quarantined"], ["a.txt"] if phase == "quarantined" else [])
            self.assertEqual(
                report["recorded_removed"],
                ["a.txt", "b.txt"] if complete else ["a.txt"] if phase == "removed" else [],
            )
            if phase == "quarantined":
                self.assertEqual((attempt / "quarantine/a.txt").read_bytes(), b"invented-first")

    def test_complete_owned_process_has_current_empty_namespaces(self):
        self.case("complete")

    def test_deadline_before_move_preserves_all_files(self):
        self.case("prepared")

    def test_deadline_after_first_removal_retains_exact_prefix(self):
        self.case("removed")

    def test_cancel_after_quarantine_retains_unremoved_copy(self):
        self.case("quarantined", cancel=True)
