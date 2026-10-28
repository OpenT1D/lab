"""Synthetic study lifecycle checks in the locked M3 estimator environment."""

import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from experiments.m3.azt1d.common import read, save
from experiments.m3.azt1d.fixtures import generate_study
from experiments.m3.azt1d.study import fit_plan, freeze, init_ledger, run_study


class NativeAZT1DStudy(unittest.TestCase):
    def setup_study(self, root, **options):
        generate_study(root / "input", **options)
        freeze(root / "input/registry.json", root / "plan")
        init_ledger(root / "plan/plan.json")
        return root / "plan/plan.json"

    def test_full_study_reconstructs_without_original_inputs_or_estimator(self):
        from experiments.m3.azt1d.analysis import reconstruct

        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            plan = self.setup_study(root)
            fit_plan(plan, root / "fit")
            report = run_study(plan, root / "fit", root / "study")
            self.assertTrue(report["evaluation"]["complete_cohort"])
            self.assertEqual(report, reconstruct(root / "study"))
            shutil.rmtree(root / "input")
            shutil.rmtree(root / "fit")
            shutil.rmtree(root / "plan")
            result = subprocess.run(
                [
                    sys.executable,
                    "-S",
                    "-m",
                    "experiments.m3.azt1d",
                    "report",
                    "--study",
                    str(root / "study"),
                    "--output",
                    str(root / "reconstructed.json"),
                ],
                capture_output=True,
                text=True,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(report, json.loads((root / "reconstructed.json").read_text()))

    def test_unsupported_person_remains_in_cohort_and_reuse_is_recorded(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            plan = self.setup_study(root, unsupported_last=True)
            fit_plan(plan, root / "fit")
            first = run_study(plan, root / "fit", root / "study-one")
            self.assertFalse(first["evaluation"]["complete_cohort"])
            self.assertEqual(first["evaluation"]["planned_people"], 2)
            self.assertEqual(first["evaluation"]["contributing_people"], 1)
            run_study(plan, root / "fit", root / "study-two")
            evidence, _ = read(root / "study-two/invented-1/normalization-access.json")
            self.assertTrue(evidence["repeated_event"])
            with self.assertRaisesRegex(ValueError, "do not refit"):
                fit_plan(plan, root / "forbidden-refit")
            self.assertFalse((root / "forbidden-refit").exists())
            with patch(
                "experiments.m3.azt1d.analysis.reconstruct",
                side_effect=ValueError("report failure"),
            ):
                with self.assertRaisesRegex(ValueError, "report failure"):
                    run_study(plan, root / "fit", root / "failed-report")
            state, _ = read(root / "failed-report/study.json")
            self.assertEqual(state["status"], "failed")
            self.assertEqual(state["error"]["type"], "ValueError")

    def test_heldout_native_failure_does_not_prevent_fitting_or_disappear(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            plan = self.setup_study(root)
            # Descriptors and converted development/validation remain intact.
            # A fit must not touch either native source, including its future records.
            for native in (root / "input").glob("*/source.csv"):
                native.write_bytes(b"poisoned unseen source")
            fit_plan(plan, root / "fit")
            report = run_study(plan, root / "fit", root / "failed-study")
            self.assertFalse(report["evaluation"]["complete_cohort"])
            self.assertEqual(report["evaluation"]["contributing_people"], 0)
            for case in report["evaluation"]["people"].values():
                self.assertEqual(case["execution_status"], "failed")
                self.assertGreater(case["planned"], 0)
                self.assertEqual(case["attempted"], 0)

    def test_no_qualified_development_preserves_failed_fit(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            plan = self.setup_study(root, people=1, days=1)
            with self.assertRaises(ValueError):
                fit_plan(plan, root / "failed-fit")
            state, _ = read(root / "failed-fit/state.json")
            self.assertEqual(state["status"], "failed")
            self.assertIn("development.json", state["files"])
            self.assertFalse((root / "failed-fit/freeze.json").exists())

    def test_invalid_model_cannot_be_used_after_inventory_tampering(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            plan = self.setup_study(root, people=1)
            fit_plan(plan, root / "fit")
            model, _ = read(root / "fit/model.json")
            model["coef"][0] += 1
            save(root / "fit/model.json", model)
            with self.assertRaises(ValueError):
                run_study(plan, root / "fit", root / "forbidden-study")
            self.assertFalse((root / "forbidden-study").exists())


if __name__ == "__main__":
    unittest.main()
