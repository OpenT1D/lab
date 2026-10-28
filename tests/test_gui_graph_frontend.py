"""Saved graph values retain native scope, units and snapshot authority."""

import json
import shutil
import subprocess
import unittest
from html.parser import HTMLParser
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class SummaryParents(HTMLParser):
    def __init__(self):
        super().__init__()
        self.stack = []
        self.parents = {}

    def handle_starttag(self, tag, attrs):
        attributes = dict(attrs)
        identity = attributes.get("id")
        if identity in {"library-evidence-summary", "m3-evidence-summary"}:
            self.parents[identity] = [item[1] for item in self.stack]
        if tag not in {"input", "img", "meta", "link", "br", "hr"}:
            self.stack.append((tag, identity))

    def handle_endtag(self, tag):
        if self.stack and self.stack[-1][0] == tag:
            self.stack.pop()


class GraphFrontendTests(unittest.TestCase):
    @unittest.skipUnless(shutil.which("node"), "Node is required for controlled frontend checks")
    def test_native_values_units_and_snapshot_guards(self):
        result = subprocess.run(
            [shutil.which("node"), "tests/gui_graph_frontend.mjs"],
            cwd=ROOT,
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        receipt = json.loads(result.stdout)
        self.assertTrue(receipt["passed"])
        self.assertEqual(receipt["checks"], 9)

    def test_report_summaries_withdraw_with_their_current_native_report(self):
        parser = SummaryParents()
        parser.feed((ROOT / "experiments/gui/static/index.html").read_text())
        self.assertIn("library-results", parser.parents["library-evidence-summary"])
        self.assertIn("m3-results", parser.parents["m3-evidence-summary"])


if __name__ == "__main__":
    unittest.main()
