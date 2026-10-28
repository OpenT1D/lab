"""Controlled selection races for the archive frontend, when Node is available."""

import json
import shutil
import subprocess
import unittest
from html.parser import HTMLParser
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class ArchiveControls(HTMLParser):
    def __init__(self):
        super().__init__()
        self.identities = {}
        self.duplicates = []

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        identity = attrs.get("id")
        if identity:
            if identity in self.identities:
                self.duplicates.append(identity)
            self.identities[identity] = (tag, attrs)


class ArchiveFrontendTests(unittest.TestCase):
    @unittest.skipUnless(shutil.which("node"), "Node is required for controlled frontend checks")
    def test_shipped_archive_view_rejects_stale_report_figure_and_error_responses(self):
        result = subprocess.run(
            [shutil.which("node"), "tests/gui_archive_frontend.mjs"],
            cwd=ROOT,
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        receipt = json.loads(result.stdout)
        self.assertTrue(receipt["passed"])
        self.assertEqual(receipt["checks"], 108)

    def test_archive_controls_and_native_sections_have_accessible_semantics(self):
        parser = ArchiveControls()
        parser.feed((ROOT / "experiments/gui/static/index.html").read_text())
        self.assertEqual(parser.duplicates, [])
        nodes = parser.identities
        self.assertEqual(nodes["archive-library"][1]["aria-labelledby"], "library-title")
        self.assertEqual(nodes["library-title"][1]["tabindex"], "-1")
        self.assertNotIn("aria-live", nodes["library-results"][1])
        self.assertEqual(nodes["library-notice"][1]["role"], "alert")
        for identity in (
            "library-digest-status",
            "library-freshness",
            "library-recorded-status",
            "library-verification-status",
            "library-completeness",
            "library-m3-denominators",
            "library-m3-people",
            "library-m3-candidate-results",
            "library-m3-errors",
            "library-m3-contrasts",
            "library-m3-json",
            "library-m5-results",
            "library-m5-denominators",
            "library-m5-analysis-scope",
            "library-m5-people",
            "library-m5-attempts",
            "library-m5-errors",
            "library-m5-declaration",
            "library-m5-json",
            "library-source-results",
            "library-figure",
        ):
            self.assertIn(identity, nodes)
        for identity in (
            "archive-verify",
            "library-download-json",
            "library-download-markdown",
            "library-download-svg",
        ):
            self.assertEqual(nodes[identity][0], "button")
            self.assertEqual(nodes[identity][1]["type"], "button")
        self.assertEqual(nodes["archive-dialog"][1]["aria-labelledby"], "archive-dialog-title")
        self.assertTrue(nodes["archive-close-dialog"][1]["aria-label"])
        self.assertEqual(nodes["library-m3-json"][0], "pre")
        self.assertEqual(nodes["library-m5-json"][0], "pre")


if __name__ == "__main__":
    unittest.main()
