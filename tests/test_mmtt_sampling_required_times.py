"""Shared-clock admission precedes initialization, draws and estimation."""

import csv
import io
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from experiments.catalogue.storage import dump
from experiments.mmtt_sampling.design import validate_design
from experiments.mmtt_sampling.fixtures import DESIGN
from experiments.observation_analysis.analysis import evaluate
from experiments.observation_analysis.estimator import estimate
from experiments.observation_analysis.fixtures import analysis_settings, csv_bytes, package
from experiments.observation_analysis.plan import freeze, validate_settings
from experiments.observation_analysis.run import reconstruct, run


class RequiredSamplingTimesTests(unittest.TestCase):
    def settings(self):
        settings = analysis_settings()
        settings["uncertainty"]["draws"] = 32
        settings["required_times_min"] = [0, 30, 60, 90, 120]
        return settings

    def missing_raw(self):
        rows = list(csv.reader(io.StringIO(csv_bytes().decode())))[1:]
        return csv_bytes([row for row in rows if not (row[1] == "before" and row[3] == "60")])

    def test_missing_required_time_never_reaches_estimator(self):
        settings = self.settings()
        with patch("experiments.observation_analysis.analysis.estimate", wraps=estimate) as call:
            result = evaluate(settings, package(), self.missing_raw())
        self.assertFalse(result["import_valid"])
        person = result["people"]["invented-01"]
        self.assertEqual(len(person["perturbations"]), 0)
        self.assertEqual(call.call_count, len(settings["variants"]))
        errors = person["references"]["before"]["import_errors"]
        self.assertTrue(any(error.get("times_min") == [60] for error in errors))
        for variant in person["variants"].values():
            self.assertEqual(variant["point"]["visits"]["before"]["status"], "failed")
            self.assertEqual(variant["point"]["visits"]["after"]["status"], "completed")
            self.assertEqual(variant["draws"], [])

    def test_required_times_are_frozen_and_failure_reconstructs_natively(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            dump(root / "package.json", package())
            dump(root / "settings.json", self.settings())
            (root / "data.csv").write_bytes(self.missing_raw())
            freeze(root / "package.json", root / "data.csv", root / "settings.json", root / "plan")
            result = run(root / "plan", root / "result")
            self.assertFalse(result["coverage"]["complete_cohort"])
            self.assertEqual(result["coverage"]["planned_variant_pairs"], 3)
            self.assertEqual(
                reconstruct(root / "result", root / "reader", allow_failed=True), result
            )
            self.assertEqual(
                (root / "reader/report.md").read_bytes(), (root / "result/report.md").read_bytes()
            )

    def test_bad_clocks_and_unsafe_schedule_names_refused(self):
        import json

        for times in ([False, 120], [0, 60, 60, 120], [0, 121, 120], [0, 90], [0, "60", 120]):
            settings = self.settings()
            settings["required_times_min"] = times
            with self.subTest(times=times), self.assertRaises(ValueError):
                validate_settings(settings, package())
        for name in ("../outside", "x/y", "x\\y", ".."):
            design = json.loads(DESIGN.read_text())
            design["subsets"][name] = design["subsets"].pop("three-times")
            with self.subTest(name=name), self.assertRaises(ValueError):
                validate_design(design)


if __name__ == "__main__":
    unittest.main()
