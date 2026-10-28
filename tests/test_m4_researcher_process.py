"""Real worker cleanup on deadlines and interruption; no numerical simulators."""

import os
import signal
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from experiments.m4.causal_secretion import run as causal_run
from experiments.m4.researcher_workflow import process


class ProcessTests(unittest.TestCase):
    def child_factory(self, children):
        original = subprocess.Popen

        def create(*args, **kwargs):
            child = original(*args, **kwargs)
            children.append(child)
            return child

        return create

    def assert_reaped(self, child):
        self.assertEqual(child.returncode, -signal.SIGKILL)
        with self.assertRaises(ProcessLookupError):
            os.kill(child.pid, 0)

    def test_deadline_kills_and_reaps_real_worker(self):
        children = []
        with (
            tempfile.TemporaryDirectory() as tmp,
            patch.object(process.subprocess, "Popen", side_effect=self.child_factory(children)),
        ):
            output = Path(tmp)
            with self.assertRaisesRegex(TimeoutError, "exceeded 0.05 seconds"):
                process.command(
                    [sys.executable, "-c", "import time; time.sleep(30)"],
                    output,
                    "deadline.log",
                    0.05,
                )
            self.assertEqual(len(children), 1)
            self.assert_reaped(children[0])
            self.assertTrue((output / "deadline.log").is_file())

    def test_keyboard_interrupt_kills_before_failure_sealing(self):
        children = []
        original_wait = subprocess.Popen.wait
        interrupted = False

        def wait(child, *args, **kwargs):
            nonlocal interrupted
            if not interrupted:
                interrupted = True
                raise KeyboardInterrupt("controlled interruption")
            return original_wait(child, *args, **kwargs)

        with (
            tempfile.TemporaryDirectory() as tmp,
            patch.object(process.subprocess.Popen, "wait", wait),
            patch.object(process.subprocess, "Popen", side_effect=self.child_factory(children)),
        ):
            output = Path(tmp)
            with self.assertRaisesRegex(KeyboardInterrupt, "controlled interruption"):
                process.command(
                    [sys.executable, "-c", "import time; time.sleep(30)"],
                    output,
                    "interrupted.log",
                    30,
                )
            self.assertTrue(interrupted)
            self.assertEqual(len(children), 1)
            self.assert_reaped(children[0])
            self.assertTrue((output / "interrupted.log").is_file())

    def test_causal_supervisor_binding_restores_after_nested_failure(self):
        original = causal_run.command
        with self.assertRaisesRegex(RuntimeError, "controlled failure"):
            with process.causal_commands():
                self.assertIs(causal_run.command, process.command)
                with process.causal_commands():
                    self.assertIs(causal_run.command, process.command)
                self.assertIs(causal_run.command, process.command)
                raise RuntimeError("controlled failure")
        self.assertIs(causal_run.command, original)

    def test_nonzero_exit_retains_log_and_original_error_contract(self):
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp)
            with self.assertRaisesRegex(RuntimeError, "exited 7; inspect failed.log"):
                process.command(
                    [
                        sys.executable,
                        "-c",
                        "print('controlled exit', flush=True); raise SystemExit(7)",
                    ],
                    output,
                    "failed.log",
                    30,
                )
            self.assertIn("controlled exit", (output / "failed.log").read_text())


if __name__ == "__main__":
    unittest.main()
