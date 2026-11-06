"""Owned fresh invented leaf-removal workers; unrelated process/data preserved."""

import os
import subprocess
import sys
import tempfile
import threading
import unittest
from pathlib import Path

from experiments.lt1_diagnostic import historical_leaf_removal as leaf
from experiments.shared_services.execution import supervise
from tests.lt1_historical_leaf_fixture import command, outer


@unittest.skipUnless(os.name == "posix", "POSIX owned fixture required")
class HistoricalLeafProcessTests(unittest.TestCase):
    def case(self, phase, *, cancel=False):
        with tempfile.TemporaryDirectory() as directory:
            parent = Path(directory).resolve()
            parent.chmod(0o700)
            cancellation, done = threading.Event(), threading.Event()
            sentinel = subprocess.Popen(
                [sys.executable, "-I", "-S", "-B", "-c", "import time; time.sleep(60)"]
            )

            def watcher():
                while not done.wait(0.01):
                    if (parent / "ready").is_file():
                        cancellation.set()
                        return

            thread = threading.Thread(target=watcher, daemon=True) if cancel else None
            if thread:
                thread.start()
            try:
                receipt = supervise(
                    command(parent, phase),
                    parent / "worker.log",
                    timeout=10 if cancel or phase == "complete" else 3,
                    grace=0.2,
                    cancel=cancellation,
                    environment={"LANG": "C", "LC_ALL": "C", "PATH": "/usr/bin:/bin"},
                )
                self.assertIsNone(sentinel.poll(), "unrelated sentinel must remain alive")
            finally:
                done.set()
                if thread:
                    thread.join(timeout=1)
                sentinel.terminate()
                sentinel.wait(timeout=5)
            complete = phase == "complete"
            self.assertEqual(receipt["remaining_owned_processes"], [])
            self.assertEqual(receipt["received_signals"], [])
            self.assertEqual(
                receipt["status"],
                "completed" if complete else "interrupted" if cancel else "failed",
            )
            if not complete:
                self.assertTrue(
                    (parent / "ready").is_file(), "intended phase must actually be reached"
                )
                self.assertFalse((parent / "outcome.json").exists())
            raw = (parent / "request.json").read_bytes()
            context = (parent / "context.json").read_bytes()
            journal = (parent / "reports/attempt-one/events.jsonl").read_bytes()
            outer_raw = outer(raw, receipt)
            report = leaf.inspect(
                raw,
                leaf.digest(raw),
                context,
                leaf.digest(journal),
                outer_raw,
                leaf.digest(outer_raw),
            )
            self.assertEqual(report["status"], "completed" if complete else "incomplete")
            self.assertEqual(
                (parent / "mixed/preserved.txt").read_bytes(), b"invented unrelated sibling\n"
            )
            self.assertEqual(
                (parent / "mixed/preserved-folder/untouched.txt").read_bytes(),
                b"invented nested sentinel\n",
            )
            for key in leaf.AUTHORITY:
                self.assertIs(report[key], False)
            return report

    def test_owned_success_only_removes_reviewed_leaf(self):
        self.case("complete")

    def test_deadline_before_move_keeps_target_and_siblings(self):
        report = self.case("prepared")
        self.assertEqual(report["target_present"], ["invented-decision.json"])

    def test_cancel_after_quarantine_retains_payload(self):
        report = self.case("quarantined", cancel=True)
        self.assertEqual(report["quarantined"], ["invented-decision.json"])

    def test_deadline_before_move_event_retains_unrecorded_quarantine(self):
        self.assertTrue(self.case("moved-unrecorded")["unrecorded_move_observed"])

    def test_deadline_before_remove_event_does_not_manufacture_removal(self):
        self.assertTrue(self.case("unlinked-unrecorded")["absence_without_recorded_removal"])


if __name__ == "__main__":
    unittest.main()
