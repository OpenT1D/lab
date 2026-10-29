"""Portable negative controls for the explicit Mac application QA helper."""

import shutil
import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class MacProbeLifecycleTests(unittest.TestCase):
    @unittest.skipUnless(shutil.which("node"), "Node is required for probe lifecycle checks")
    def test_cleanup_failures_cannot_commit_pass_or_grant_pid_authority(self):
        result = subprocess.run(
            [shutil.which("node"), "--test", "tests/mac_probe_lifecycle.test.mjs"],
            cwd=ROOT,
            capture_output=True,
            text=True,
            timeout=20,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
