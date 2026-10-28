"""Controlled campaign intake and selection races against shipped frontend code."""

import json
import shutil
import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class CampaignFrontendTests(unittest.TestCase):
    @unittest.skipUnless(shutil.which("node"), "Node is required for controlled frontend checks")
    def test_campaign_snapshot_matrix_roster_and_deferred_responses(self):
        result = subprocess.run(
            [shutil.which("node"), "tests/gui_campaign_frontend.mjs"],
            cwd=ROOT,
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        receipt = json.loads(result.stdout)
        self.assertTrue(receipt["passed"])
        self.assertEqual(receipt["checks"], 23)


if __name__ == "__main__":
    unittest.main()
