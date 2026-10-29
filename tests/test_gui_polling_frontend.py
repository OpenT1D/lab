"""Polling keeps reading state while current snapshot failures still withdraw it."""

import json
import shutil
import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class PollingFrontendTests(unittest.TestCase):
    @unittest.skipUnless(shutil.which("node"), "Node is required for controlled frontend checks")
    def test_polling_retains_focus_disclosures_and_current_snapshot_guards(self):
        result = subprocess.run(
            [shutil.which("node"), "tests/gui_polling_frontend.mjs"],
            cwd=ROOT,
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        receipt = json.loads(result.stdout)
        self.assertTrue(receipt["passed"])
        self.assertEqual(receipt["checks"], 25)


if __name__ == "__main__":
    unittest.main()
