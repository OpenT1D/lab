"""Actual owned Python fixture stops; no candidate runtime or native model."""

import json
import os
import sys
import tempfile
import threading
import unittest
from pathlib import Path

from experiments.lt1_diagnostic import frozen_setup as stage
from experiments.shared_services.execution import supervise

ROOT = Path(__file__).resolve().parents[1]


@unittest.skipUnless(os.name == "posix", "POSIX setup fixture required")
class LT1SetupProcessTests(unittest.TestCase):
    def stop_case(self, behavior, cancellation):
        with tempfile.TemporaryDirectory() as temp:
            parent = Path(temp).resolve()
            parent.chmod(0o700)
            cancel, done = threading.Event(), threading.Event()

            def watcher():
                while not done.wait(0.01):
                    if (parent / "ready").is_file():
                        cancel.set()
                        return

            thread = threading.Thread(target=watcher, daemon=True) if cancellation else None
            if thread:
                thread.start()
            try:
                receipt = supervise(
                    [
                        sys.executable,
                        str(ROOT / "tests/lt1_setup_fixture.py"),
                        str(parent),
                        behavior,
                    ],
                    parent / "process.log",
                    timeout=1.5 if not cancellation else 5,
                    grace=0.1,
                    cancel=cancel,
                )
            finally:
                done.set()
                if thread:
                    thread.join(timeout=1)
            self.assertEqual(receipt["status"], "interrupted" if cancellation else "failed")
            self.assertEqual(receipt["remaining_owned_processes"], [])
            self.assertTrue((parent / "ready").is_file())
            self.assertEqual((parent / "attempt/payload/a.txt").read_bytes(), b"invented-first")
            self.assertFalse((parent / "attempt/materialized.json").exists())
            self.assertEqual(
                (parent / "attempt/.inventory.pending").exists(), behavior == "pending"
            )
            with self.assertRaisesRegex(ValueError, "incomplete"):
                stage.inspect_materialized(parent / "attempt", "0" * 64, "0" * 64)
            # Retainable receipt serialization must not turn interruption into
            # successful native setup; actual setup authority is never changed.
            self.assertEqual(json.loads(json.dumps(receipt))["status"], receipt["status"])

    def test_deadline_retains_validated_prefix_without_completion(self):
        self.stop_case("prefix", False)

    def test_cancel_during_inventory_publish_retains_only_pending_marker(self):
        self.stop_case("pending", True)
