"""Numerical and source-boundary checks for the invented OT-027 comparison."""

import copy
import json
import math
import tempfile
import unittest
from pathlib import Path

from experiments.m5.synthetic_prognosis.run import (
    assess,
    digest,
    execute,
    features,
    fit,
    fixture,
    predict,
    reconstruct,
    solve,
    write,
)


class M5SyntheticPrognosisTests(unittest.TestCase):
    def test_roster_split_and_paired_metric_are_reconstructible(self):
        report = assess(fixture())
        self.assertEqual(report["roster_count"], 32)
        self.assertEqual(report["development_paired_count"], 20)
        self.assertEqual(report["evaluation_paired_count"], 7)
        people = {person["alias"]: person for person in report["people"]}
        self.assertEqual(people["SYN005"]["issues"][0], "paired_function_values_unavailable")
        self.assertIn("protocol_not_collected_confirmed_graft_failure", people["SYN005"]["issues"])
        self.assertIn("missing_or_ambiguous_first_infusion_y1", people["SYN020"]["issues"])
        self.assertTrue(people["SYN020"]["visit15_present"])
        self.assertFalse(people["SYN020"]["y1_present"])
        self.assertEqual(people["SYN006"]["intervening_infusion_days"], [150])
        self.assertEqual(
            {item["alias"] for item in report["evaluation_predictions"]},
            {
                person["alias"]
                for person in report["people"]
                if person["split"] == "evaluation" and person["paired_comparison_eligible"]
            },
        )
        scored = report["evaluation_predictions"]
        for model in ("baseline", "added"):
            expected = sum(
                abs(
                    item[f"{model}_prediction_u_day"] - item["observed_reported_insulin_mean_u_day"]
                )
                for item in scored
            ) / len(scored)
            self.assertAlmostEqual(report[f"{model}_mae_u_day"], expected, places=12)
        self.assertFalse(report["human_execution_authorized"])
        self.assertFalse(report["treatment_effect_or_cure_estimated"])

    def test_future_baseline_and_visit15_cannot_enter_prediction(self):
        packet = fixture()
        person = copy.deepcopy(packet["people"][19])
        row, issues = features(person)
        self.assertIsNone(row)
        self.assertIn("missing_or_ambiguous_first_infusion_y1", issues)
        person = copy.deepcopy(packet["people"][0])
        person["glycemic_status"]["day"] = 100
        row, issues = features(person)
        self.assertIsNone(row)
        self.assertIn("baseline_after_landmark", issues)
        person = copy.deepcopy(packet["people"][0])
        person["mmtt"]["day"] = 365
        row, issues = features(person)
        self.assertIsNone(row)
        self.assertIn("invalid_day75_landmark", issues)

    def test_fixed_toy_ridge_uses_development_only(self):
        packet = fixture()
        train = [
            features(person)[0]
            for number, person in enumerate(packet["people"], 1)
            if number % 4 and features(person)[0] is not None
        ]
        held_out = features(packet["people"][3])[0]
        model = fit(train, include_function=True)
        original = predict(model, held_out, include_function=True)
        changed = {**held_out, "outcome": held_out["outcome"] + 1000}
        self.assertEqual(original, predict(model, changed, include_function=True))
        self.assertEqual(len(model["coefficients"]), 5)
        self.assertTrue(math.isfinite(original))
        self.assertEqual(solve([[2.0, 0.0], [0.0, 4.0]], [6.0, 8.0]), [3.0, 2.0])

    def test_only_fixed_invented_fixture_and_untampered_archive_are_accepted(self):
        changed = fixture()
        changed["people"][0]["alias"] = "SYN999"
        with self.assertRaisesRegex(ValueError, "fixed invented fixture"):
            assess(changed)
        with tempfile.TemporaryDirectory() as root:
            archive = Path(root) / "archive"
            report = execute(archive)
            self.assertEqual(reconstruct(archive), report)
            altered = json.loads((archive / "report.json").read_text())
            altered["human_execution_authorized"] = True
            write(archive / "report.json", altered)
            manifest = json.loads((archive / "manifest.json").read_text())
            manifest["files"]["report.json"] = digest(archive / "report.json")
            write(archive / "manifest.json", manifest)
            with self.assertRaisesRegex(ValueError, "differs"):
                reconstruct(archive)


if __name__ == "__main__":
    unittest.main()
