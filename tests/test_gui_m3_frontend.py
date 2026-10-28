"""Exercise shipped M3 asynchronous UI behavior and accessible static controls."""

import json
import shutil
import subprocess
import unittest
from html.parser import HTMLParser
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class Controls(HTMLParser):
    def __init__(self):
        super().__init__()
        self.stack = []
        self.nodes = {}
        self.duplicates = []

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        identity = attrs.get("id")
        if identity:
            if identity in self.nodes:
                self.duplicates.append(identity)
            self.nodes[identity] = {"tag": tag, "attrs": attrs, "parents": list(self.stack)}
        if tag not in {"input", "meta", "link", "img", "br", "hr"}:
            self.stack.append(tag)

    def handle_endtag(self, tag):
        if tag in self.stack:
            index = len(self.stack) - 1 - self.stack[::-1].index(tag)
            self.stack = self.stack[:index]


class M3FrontendTests(unittest.TestCase):
    @unittest.skipUnless(shutil.which("node"), "Node is required for controlled frontend checks")
    def test_m3_intake_readiness_roster_retention_and_deferred_responses(self):
        result = subprocess.run(
            [shutil.which("node"), "tests/gui_m3_frontend.mjs"],
            cwd=ROOT,
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        receipt = json.loads(result.stdout)
        self.assertTrue(receipt["passed"])
        self.assertEqual(receipt["checks"], 34)

    def test_m3_controls_have_labels_and_status_while_existing_workflows_remain(self):
        controls = Controls()
        controls.feed((ROOT / "experiments/gui/static/index.html").read_text())
        self.assertEqual(controls.duplicates, [])
        for identity in ("m3-root", "m3-path", "m3-task", "m3-timeout"):
            self.assertIn("label", controls.nodes[identity]["parents"], identity)
        self.assertEqual(controls.nodes["m3-panel"]["attrs"]["aria-labelledby"], "m3-title")
        self.assertEqual(controls.nodes["m3-title"]["attrs"]["tabindex"], "-1")
        self.assertNotIn("aria-live", controls.nodes["m3-activity-detail"]["attrs"])
        self.assertIn(
            'role="status" aria-live="polite"',
            (ROOT / "experiments/gui/static/index.html").read_text(),
        )
        self.assertEqual(controls.nodes["m3-notice"]["attrs"]["role"], "alert")
        self.assertEqual(controls.nodes["m3-dialog"]["attrs"]["aria-labelledby"], "m3-dialog-title")
        self.assertTrue(controls.nodes["m3-close-dialog"]["attrs"]["aria-label"])
        for identity in (
            "open-m3",
            "m3-fixture",
            "m3-browse",
            "m3-cancel",
            "m3-reconstruct",
            "m3-export",
            "m3-retain",
            "m3-download-json",
            "m3-download-markdown",
        ):
            self.assertEqual(controls.nodes[identity]["tag"], "button", identity)
            self.assertEqual(controls.nodes[identity]["attrs"].get("type", "button"), "button")
        for identity in (
            "study-form",
            "run-study",
            "campaign-form",
            "campaign-run",
            "archive-form",
            "archive-verify",
            "durable-export-form",
            "durable-register-form",
        ):
            self.assertIn(identity, controls.nodes)


if __name__ == "__main__":
    unittest.main()
