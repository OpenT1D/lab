"""Unified results preserve workflow ownership and browser reading position."""

import json
import shutil
import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class UXFrontendTests(unittest.TestCase):
    @unittest.skipUnless(shutil.which("node"), "Node is required for controlled frontend checks")
    def test_owned_results_and_digest_polling_retain_identity_and_focus(self):
        result = subprocess.run(
            [shutil.which("node"), "tests/gui_ux_frontend.mjs"],
            cwd=ROOT,
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        receipt = json.loads(result.stdout)
        self.assertTrue(receipt["passed"])
        self.assertEqual(receipt["checks"], 20)


if __name__ == "__main__":
    unittest.main()
