"""Controlled admission/worker tests; never install or execute native LT1."""

import shutil
import subprocess
import unittest
from pathlib import Path


@unittest.skipUnless(shutil.which("node"), "Node required for invented loader controls")
class LT1NativeLoaderTests(unittest.TestCase):
    def test_invented_loader_controls(self):
        result = subprocess.run(
            [shutil.which("node"), "--test", "tests/lt1_native_loader.test.mjs"],
            cwd=Path(__file__).resolve().parents[1],
            capture_output=True,
            text=True,
            timeout=30,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
