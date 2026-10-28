"""Exercise study supervision with real child exits, without running physiology."""

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from experiments.m2.study import cases, run

WORKER = """
import json, os, signal, sys
from pathlib import Path
output = Path(sys.argv[1])
output.mkdir()
(output / 'manifest.json').write_text(json.dumps({'status': sys.argv[2]}))
print('synthetic worker diagnostic', flush=True)
code = int(sys.argv[3])
if code < 0:
    os.kill(os.getpid(), -code)
sys.exit(code)
"""


class M2SchedulerTests(unittest.TestCase):
    def exercise(self, root, status, code):
        schedule = cases("development")[:2]
        spawn = subprocess.Popen

        def child(command, **kwargs):
            output = command[command.index("--output") + 1]
            return spawn([sys.executable, "-c", WORKER, output, status, str(code)], **kwargs)

        with (
            patch("experiments.m2.study.cases", return_value=schedule),
            patch("experiments.m2.study.subprocess.Popen", side_effect=child),
            patch("experiments.m2.report.write_report") as report,
        ):
            if (status, code) in (("completed", 0), ("terminated", 1)):
                run(root, workers=1)
                report.assert_called_once_with(root, root / "report")
            else:
                with self.assertRaisesRegex(RuntimeError, "exit.*status"):
                    run(root, workers=1)
                report.assert_not_called()
        return schedule, json.loads((root / "study.json").read_text())

    def test_success_and_native_termination_have_distinct_expected_exits(self):
        for status, code, expected in (
            ("completed", 0, "completed"),
            ("terminated", 1, "finished_with_failures"),
        ):
            with self.subTest(status=status), tempfile.TemporaryDirectory() as directory:
                _, saved = self.exercise(Path(directory) / "study", status, code)
                self.assertEqual(saved["status"], expected)

    def test_conflicting_exit_preserves_evidence_and_unattempted_schedule(self):
        for status, code in (
            ("completed", 7),
            ("completed", -9),
            ("terminated", 0),
            ("terminated", 7),
            ("failed", 0),
        ):
            with self.subTest(status=status, code=code), tempfile.TemporaryDirectory() as directory:
                root = Path(directory) / "study"
                schedule, saved = self.exercise(root, status, code)
                self.assertEqual(saved["status"], "started")
                self.assertEqual(saved["cases"], schedule)
                self.assertIn(str(code), saved["error"])
                self.assertIn(status, saved["error"])
                self.assertFalse((root / schedule[1]["id"]).exists())
                manifest = root / schedule[0]["id"] / "manifest.json"
                self.assertEqual(json.loads(manifest.read_text()), {"status": status})
                log = root / "logs" / (schedule[0]["id"] + ".log")
                self.assertIn("synthetic worker diagnostic", log.read_text())

    def test_spawn_failure_closes_log_and_preserves_original_error(self):
        opened = []

        def fail(_command, **kwargs):
            opened.append(kwargs["stdout"])
            raise OSError("synthetic spawn failure")

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "study"
            with patch("experiments.m2.study.subprocess.Popen", side_effect=fail):
                with self.assertRaisesRegex(OSError, "synthetic spawn failure"):
                    run(root, workers=1)
            self.assertTrue(opened[0].closed)
            saved = json.loads((root / "study.json").read_text())
            self.assertEqual(saved["status"], "started")
            self.assertEqual(len(saved["cases"]), 40)
            self.assertEqual(saved["error"], "OSError: synthetic spawn failure")
