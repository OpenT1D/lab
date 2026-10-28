"""Workspace navigation preserves native workflow state and active-operation access."""

import json
import shutil
import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class WorkspaceFrontendTests(unittest.TestCase):
    @unittest.skipUnless(shutil.which("node"), "Node is required for controlled frontend checks")
    def test_navigation_retains_state_focus_history_and_operation_access(self):
        result = subprocess.run(
            [shutil.which("node"), "tests/gui_workspace_frontend.mjs"],
            cwd=ROOT,
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        receipt = json.loads(result.stdout)
        self.assertTrue(receipt["passed"])
        self.assertEqual(receipt["checks"], 14)


if __name__ == "__main__":
    unittest.main()
