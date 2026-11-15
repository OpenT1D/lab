"""Owned fresh invented leaf-removal workers; unrelated process/data preserved."""

import os
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from pathlib import Path

from experiments.lt1_diagnostic import historical_leaf_removal as leaf
from experiments.shared_services.execution import supervise
from tests.lt1_historical_leaf_fixture import command, outer


@unittest.skipUnless(os.name == "posix", "POSIX owned fixture required")
class HistoricalLeafProcessTests(unittest.TestCase):
    def case(self, phase, *, cancel=False, delayed_start=False, timeout=10):
        with tempfile.TemporaryDirectory() as directory:
            parent = Path(directory).resolve()
            parent.chmod(0o700)
            cancellation, done = threading.Event(), threading.Event()
            ready_seen = []
            sentinel = subprocess.Popen(
                [sys.executable, "-I", "-S", "-B", "-c", "import time; time.sleep(60)"]
            )

            def watcher():
                while not done.wait(0.01):
                    try:
                        ready = (parent / "ready").read_bytes()
                    except FileNotFoundError:
                        continue
                    if ready == phase.encode():
                        ready_seen.append(time.monotonic())
                        if cancel:
                            cancellation.set()
                        return

            complete = phase == "complete"
            thread = threading.Thread(target=watcher, daemon=True) if not complete else None
            if thread:
                thread.start()
            try:
                started = time.monotonic()
                receipt = supervise(
                    command(parent, phase, delayed_start=delayed_start),
                    parent / "worker.log",
                    timeout=timeout,
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
            self.assertEqual(receipt["remaining_owned_processes"], [])
            self.assertEqual(receipt["received_signals"], [])
            self.assertEqual(
                receipt["status"],
                "completed" if complete else "interrupted" if cancel else "failed",
            )
            if not complete:
                self.assertEqual(receipt["error"], "Cancelled" if cancel else "WorkerDeadline")
                diagnostic = {name: receipt.get(name) for name in ("status", "error", "exit_code")}
                self.assertTrue(
                    ready_seen,
                    f"intended phase must actually be reached: {diagnostic}",
                )
                self.assertEqual((parent / "ready").read_bytes(), phase.encode())
                if not cancel:
                    # The supervisor starts its clock after spawn. Observing the
                    # exact phase before this earlier bound proves a real window
                    # remains for the selected, indefinitely paused checkpoint.
                    self.assertLessEqual(
                        ready_seen[0],
                        started + timeout - 0.1,
                        f"intended phase must actually be reached before deadline: {diagnostic}",
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

    def test_delayed_start_needs_phase_budget_before_testing_postphase_deadline(self):
        # These are two fresh invented attempts, not a retry/resume of evidence.
        with self.assertRaisesRegex(AssertionError, "intended phase must actually be reached"):
            self.case("unlinked-unrecorded", delayed_start=True, timeout=3)
        report = self.case("unlinked-unrecorded", delayed_start=True)
        self.assertTrue(report["absence_without_recorded_removal"])


if __name__ == "__main__":
    unittest.main()
