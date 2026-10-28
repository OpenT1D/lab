"""Second internal UI/UX regressions; no scientific validity claim."""

import json
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

from experiments.gui.service import Service, digest

ROOT = Path(__file__).resolve().parents[1]


class Round2Tests(unittest.TestCase):
    @unittest.skipUnless(shutil.which("node"), "Node is required for frontend checks")
    def test_tab_draft_recovery_does_not_restore_authority(self):
        result = subprocess.run(
            [shutil.which("node"), "tests/gui_draft_frontend.mjs"],
            cwd=ROOT,
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue(json.loads(result.stdout)["passed"])

    def test_draft_scope_is_stable_and_specific_to_workspace(self):
        with tempfile.TemporaryDirectory() as temporary:
            roots = [Path(temporary) / name for name in ("first", "second")]
            scopes = []
            for root in roots:
                root.mkdir()
                service = Service(root)
                try:
                    scope = service.bootstrap()["draft_scope"]
                    self.assertEqual(scope, digest(str(root.resolve()).encode()))
                    self.assertEqual(service.bootstrap()["draft_scope"], scope)
                    scopes.append(scope)
                finally:
                    service.close()
            self.assertNotEqual(*scopes)
