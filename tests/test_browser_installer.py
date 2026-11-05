"""Exercise browser install supervision without installing browsers or packages."""

import os
import shutil
import subprocess
import unittest
from pathlib import Path


class BrowserInstallerTests(unittest.TestCase):
    @unittest.skipUnless(shutil.which("node"), "Node application grouping control")
    def test_complete_application_file_groups_and_refusals(self):
        root = Path(__file__).resolve().parents[1]
        result = subprocess.run(
            ["node", "--test", "tests/browser/application-shards.test.mjs"],
            cwd=root,
            capture_output=True,
            text=True,
            timeout=15,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    @unittest.skipUnless(
        shutil.which("node") and os.name == "posix", "Node and POSIX install supervision"
    )
    def test_failure_deadline_descendant_cleanup_and_unrelated_process_control(self):
        root = Path(__file__).resolve().parents[1]
        result = subprocess.run(
            ["node", "--test", "tests/browser/installer-process.test.mjs"],
            cwd=root,
            capture_output=True,
            text=True,
            timeout=15,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
