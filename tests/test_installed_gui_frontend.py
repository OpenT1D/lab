"""Regressions for independently reproduced installed GUI identity mistakes."""

import json
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class InstalledGUIFrontendTests(unittest.TestCase):
    @unittest.skipUnless(shutil.which("node"), "Node is required for controlled frontend checks")
    def test_parent_readiness_and_atomic_report_identity(self):
        with tempfile.TemporaryDirectory(prefix="installed-gui-dom-") as temporary:
            receipt = Path(temporary) / "receipt.json"
            result = subprocess.run(
                [
                    shutil.which("node"),
                    str(ROOT / "tests/installed_gui_frontend.mjs"),
                    str(ROOT / "packaging/sdk/opent1d_lab/_gui_assets/app.js"),
                    str(receipt),
                    str(ROOT / "packaging/sdk/opent1d_lab/_gui_assets/drafts.js"),
                    str(ROOT / "packaging/sdk/opent1d_lab/_gui_assets/comparisons.js"),
                    str(ROOT / "packaging/sdk/opent1d_lab/_gui_assets/connected.js"),
                ],
                cwd=ROOT,
                capture_output=True,
                text=True,
                timeout=30,
            )
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            evidence = json.loads(receipt.read_bytes())
            self.assertTrue(evidence["passed"], evidence)
            self.assertEqual(len(evidence["tests"]), 44)
