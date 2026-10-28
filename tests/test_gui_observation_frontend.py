"""Controlled display and async checks against actual native synthetic reports."""

import json
import shutil
import subprocess
import unittest

from experiments.observation_analysis.analysis import evaluate, report_from_attempts
from experiments.observation_analysis.fixtures import CASES, analysis_settings, case_csv, package
from tests.test_gui_m3_frontend import ROOT, Controls


class ObservationFrontendTests(unittest.TestCase):
    @unittest.skipUnless(shutil.which("node"), "Node is required for controlled frontend checks")
    def test_native_display_failures_readiness_and_deferred_replies(self):
        settings = analysis_settings()
        reports = {
            case: report_from_attempts(
                {
                    "schema": "opent1d.observation-analysis-plan/1",
                    "human_execution_authorized": False,
                    "settings": settings,
                },
                evaluate(settings, package(), case_csv(case)),
            )
            for case in CASES
        }
        for report in reports.values():
            report["execution_status"] = "completed"
        result = subprocess.run(
            [shutil.which("node"), "tests/gui_observation_frontend.mjs"],
            cwd=ROOT,
            input=json.dumps(reports),
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue(json.loads(result.stdout)["passed"])

    def test_named_regions_labels_and_dialog(self):
        controls = Controls()
        controls.feed((ROOT / "experiments/gui/static/index.html").read_text())
        self.assertFalse(controls.duplicates)
        self.assertIn(
            'value="mmtt-sensitivity">Paired meal-test sensitivity',
            (ROOT / "experiments/gui/static/index.html").read_text(),
        )
        self.assertEqual(
            controls.nodes["observations-panel"]["attrs"]["aria-labelledby"], "observations-title"
        )
        self.assertEqual(controls.nodes["observations-title"]["attrs"]["tabindex"], "-1")
        for identity in (
            "obs-package",
            "obs-csv",
            "obs-settings-path",
            "obs-case",
            "obs-draws",
            "obs-seed",
            "obs-independent-sd",
            "obs-shared-sd",
        ):
            self.assertIn("label", controls.nodes[identity]["parents"])
        self.assertNotIn("form", controls.nodes["obs-cancel"]["parents"])
        self.assertEqual(controls.nodes["obs-notice"]["attrs"]["role"], "alert")
        self.assertEqual(
            controls.nodes["obs-file-dialog"]["attrs"]["aria-labelledby"], "obs-file-dialog-title"
        )
