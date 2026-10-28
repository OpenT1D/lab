"""The simple repetition route retains owned configuration and async boundaries."""

import json
import shutil
import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class RepetitionFrontendTests(unittest.TestCase):
    @unittest.skipUnless(shutil.which("node"), "Node is required for controlled frontend checks")
    def test_saved_study_draft_focus_and_deferred_guards(self):
        result = subprocess.run(
            [shutil.which("node"), "tests/gui_repetition_frontend.mjs"],
            cwd=ROOT,
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        receipt = json.loads(result.stdout)
        self.assertTrue(receipt["passed"])
        self.assertEqual(receipt["checks"], 5)


if __name__ == "__main__":
    unittest.main()
