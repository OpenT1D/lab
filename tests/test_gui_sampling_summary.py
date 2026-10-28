"""Exercise the shipped sampling presentation against native synthetic reports."""

import csv
import io
import json
import shutil
import subprocess
import unittest
from copy import deepcopy
from pathlib import Path

from experiments.mmtt_sampling.fixtures import example
from experiments.mmtt_sampling.masking import mask_csv
from experiments.mmtt_sampling.report import build
from experiments.observation_analysis.analysis import evaluate, report_from_attempts
from experiments.observation_analysis.fixtures import analysis_settings, csv_bytes

ROOT = Path(__file__).resolve().parents[1]


def native_report(case):
    package, raw, design = example(case="constant" if case == "unresolved" else case)
    if case == "unresolved":
        rows = list(csv.reader(io.StringIO(raw.decode())))[1:]
        for row in rows:
            row[6] = "0.2"
        raw = csv_bytes(rows)
    settings = analysis_settings()
    settings["uncertainty"]["draws"] = 32
    plan = {
        "schema": "opent1d.mmtt-sampling-plan/1",
        "human_execution_authorized": False,
        "design": design,
        "settings": settings,
    }
    records = {}
    for name, times in {"full": design["full_times_minutes"], **design["subsets"]}.items():
        masked, inventory = mask_csv(raw, package, times)
        child_settings = {**deepcopy(settings), "required_times_min": list(times)}
        child = report_from_attempts(
            {
                "schema": "opent1d.observation-analysis-plan/1",
                "human_execution_authorized": False,
                "settings": child_settings,
            },
            evaluate(child_settings, package, masked),
        )
        child["execution_status"] = "completed"
        records[name] = {
            "status": "completed",
            "times_min": times,
            "inventory": inventory,
            "report": child,
        }
    return build(plan, package, records, "completed")


class SamplingSummaryFrontendTests(unittest.TestCase):
    @unittest.skipUnless(shutil.which("node"), "Node is required for controlled frontend checks")
    def test_native_conclusions_missing_results_and_complete_details(self):
        reports = {
            case: native_report(case)
            for case in ("information-loss", "constant", "incomplete", "unresolved")
        }
        result = subprocess.run(
            [shutil.which("node"), "tests/gui_sampling_summary.mjs"],
            cwd=ROOT,
            input=json.dumps(reports),
            capture_output=True,
            text=True,
            timeout=15,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue(json.loads(result.stdout)["passed"])


if __name__ == "__main__":
    unittest.main()
