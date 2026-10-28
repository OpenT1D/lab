"""Paired interpretation, shared uncertainty and complete observation failures."""

import copy
import json
import math
import statistics
import tempfile
import unittest
from pathlib import Path

from experiments.catalogue.storage import dump
from experiments.observation_analysis.analysis import classify, evaluate, report_from_attempts
from experiments.observation_analysis.fixtures import (
    analysis_settings,
    case_csv,
    csv_bytes,
    package,
)
from experiments.observation_analysis.plan import freeze, load_plan


class ObservationAnalysisTests(unittest.TestCase):
    def test_uncertainty_matches_independent_linear_gaussian_one_compartment_reference(self):
        # k1=0 independently reduces the endpoint to V*(Cend-C0)+k3*V*AUC.
        # Its trapezoid weights give analytic variances and paired covariance;
        # no estimator derivative or simulated fit is used to derive them.
        settings = analysis_settings()
        settings["variants"] = [
            {**variant, "k1_per_min": 0} for variant in settings["variants"][:2]
        ]
        settings["uncertainty"]["draws"] = 1024
        person = evaluate(settings, package(), csv_bytes())["people"]["invented-01"]
        variant = settings["variants"][0]
        v, d = variant["volume_l"], variant["k3_per_min"]
        weights = [v * (-1 + d * 15), *[v * d * 30] * 3, v * (1 + d * 15)]
        independent = settings["uncertainty"]["independent_sd_pmol_l"] ** 2 * sum(
            w * w for w in weights
        )
        covariance = settings["uncertainty"]["paired_offset_sd_pmol_l"] ** 2 * sum(weights) ** 2
        draws = person["variants"]["nominal"]["draws"]
        self.assertTrue(all(draw["status"] == "completed" for draw in draws))
        before = [draw["visits"]["before"]["estimate"]["total_pmol"] for draw in draws]
        after = [draw["visits"]["after"]["estimate"]["total_pmol"] for draw in draws]
        differences = [b - a for a, b in zip(before, after, strict=True)]
        self.assertLess(abs(statistics.variance(before) / (independent + covariance) - 1), 0.15)
        self.assertLess(abs(statistics.variance(differences) / (2 * independent) - 1), 0.15)
        self.assertLess(abs(statistics.covariance(before, after) / covariance - 1), 0.25)
        from experiments.observation_analysis.analysis import summarize_variant

        interval = summarize_variant(person["variants"]["nominal"], 1024)[
            "conditional_interval_pmol"
        ]
        expected = statistics.NormalDist().inv_cdf(0.975) * math.sqrt(2 * independent)
        self.assertLess(abs((interval[1] - interval[0]) / 2 / expected - 1), 0.15)

    def test_engineered_observation_case_exposes_real_assumption_dependence(self):
        settings = analysis_settings()
        report = report_from_attempts(
            {"settings": settings}, evaluate(settings, package(), case_csv("assumption-dependent"))
        )
        person = report["people"]["invented-01"]
        self.assertEqual(person["classification"], "assumption-dependent")
        self.assertTrue(report["coverage"]["complete_cohort"])
        self.assertEqual(person["variants"]["nominal"]["direction"], "unresolved")
        self.assertEqual(person["variants"]["peripheral-075"]["direction"], "increase")
        self.assertAlmostEqual(person["variants"]["nominal"]["paired_change_pmol"], -10, delta=1e-8)
        self.assertGreater(
            person["references"]["after"]["cpeptide_auc_pmol_min_l"],
            person["references"]["before"]["cpeptide_auc_pmol_min_l"],
        )

    def test_complete_paired_engineering_case_keeps_endpoint_reference_and_all_draws(self):
        settings = analysis_settings()
        attempts = evaluate(settings, package(), csv_bytes())
        report = report_from_attempts({"settings": settings}, attempts)
        person = report["people"]["invented-01"]
        self.assertEqual(person["classification"], "consistent within investigated assumptions")
        self.assertTrue(report["coverage"]["complete_cohort"])
        self.assertEqual(report["coverage"]["planned_variant_pairs"], 3)
        nominal = person["variants"]["nominal"]
        self.assertAlmostEqual(
            nominal["point"]["visits"]["before"]["estimate"]["total_pmol"], 5722.08, delta=1e-8
        )
        self.assertAlmostEqual(nominal["paired_change_pmol"], 2861.04, delta=1e-8)
        self.assertEqual(person["references"]["before"]["cpeptide_auc_pmol_min_l"], 24000)
        self.assertEqual(person["references"]["before"]["glucose_auc_mmol_min_l"], 660)
        for record in person["variants"].values():
            self.assertEqual(record["attempted_draws"], 128)
            self.assertEqual(len(record["draws"]), 128)
            self.assertEqual(record["failed_draws"], 0)
            self.assertGreater(record["conditional_interval_pmol"][0], 0)
            for visit in ("before", "after"):
                interval = record["visit_intervals_pmol"][visit]
                total = record["point"]["visits"][visit]["estimate"]["total_pmol"]
                self.assertLess(interval[0], total)
                self.assertGreater(interval[1], total)
        self.assertEqual(attempts, evaluate(settings, package(), csv_bytes()))

    def test_zero_crossing_intervals_are_unresolved_never_evidence_of_no_change(self):
        rows = [
            ["invented-01", visit, "meal-01", time, 5.5, "observed", 0.2, "observed"]
            for visit in ("before", "after")
            for time in (0, 30, 60, 90, 120)
        ]
        settings = analysis_settings()
        result = report_from_attempts(
            {"settings": settings}, evaluate(settings, package(), csv_bytes(rows))
        )
        person = result["people"]["invented-01"]
        self.assertEqual(person["classification"], "insufficiently determined")
        self.assertEqual(person["status"], "complete")  # Computation is separate from resolution.
        self.assertTrue(all(v["direction"] == "unresolved" for v in person["variants"].values()))
        self.assertNotIn("no change", json.dumps(result))
        self.assertEqual(
            classify(
                [
                    {"status": "complete", "direction": "increase"},
                    {"status": "complete", "direction": "unresolved"},
                ]
            ),
            "assumption-dependent",
        )
        self.assertEqual(
            classify(
                [
                    {"status": "complete", "direction": "increase"},
                    {"status": "incomplete", "direction": "increase"},
                ]
            ),
            "insufficiently determined",
        )

    def test_censored_visit_and_missing_glucose_keep_all_variants_and_denominators(self):
        settings = analysis_settings()
        for missing in ("cpeptide", "glucose"):
            rows = [
                ["invented-01", visit, "meal-01", time, 5.5, "observed", 0.2, "observed"]
                for visit in ("before", "after")
                for time in (0, 30, 60, 90, 120)
            ]
            if missing == "cpeptide":
                rows[2][-2:] = ["", "below_loq"]
            else:
                rows[2][4:6] = ["", "missing"]
            report = report_from_attempts(
                {"settings": settings}, evaluate(settings, package(), csv_bytes(rows))
            )
            self.assertFalse(report["coverage"]["complete_cohort"])
            person = report["people"]["invented-01"]
            self.assertEqual(person["classification"], "insufficiently determined")
            self.assertEqual(len(person["variants"]), 3)
            self.assertTrue(
                all(value["status"] == "incomplete" for value in person["variants"].values())
            )
            for variant in person["variants"].values():
                self.assertEqual(variant["planned_draws"], 128)
                self.assertIsNone(variant["conditional_interval_pmol"])
                self.assertTrue(
                    all(value is None for value in variant["visit_intervals_pmol"].values())
                )

    def test_failed_draws_are_retained_without_success_only_interval(self):
        settings = analysis_settings()
        settings["uncertainty"].update(independent_sd_pmol_l=1000, draws=32)
        report = report_from_attempts(
            {"settings": settings}, evaluate(settings, package(), csv_bytes())
        )
        for variant in report["people"]["invented-01"]["variants"].values():
            self.assertEqual(variant["attempted_draws"], 32)
            self.assertGreater(variant["failed_draws"], 0)
            self.assertEqual(variant["completed_draws"] + variant["failed_draws"], 32)
            self.assertIsNone(variant["conditional_interval_pmol"])

    def test_fixed_plan_binds_original_bytes_settings_protocol_and_trusted_sources(self):
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            dump(directory / "package.json", package())
            dump(directory / "settings.json", analysis_settings())
            (directory / "observations.csv").write_bytes(csv_bytes())
            saved = freeze(
                directory / "package.json",
                directory / "observations.csv",
                directory / "settings.json",
                directory / "frozen",
            )
            plan, people, raw = load_plan(directory / "frozen", check_runtime=True)
            self.assertEqual(plan, saved)
            self.assertEqual(people, package())
            self.assertEqual(raw["observations.csv"], csv_bytes())
            with self.assertRaisesRegex(ValueError, "fresh"):
                freeze(
                    directory / "package.json",
                    directory / "observations.csv",
                    directory / "settings.json",
                    directory / "frozen",
                )
            (directory / "frozen/observations.csv").write_bytes(csv_bytes() + b"\n")
            with self.assertRaisesRegex(ValueError, "bytes changed"):
                load_plan(directory / "frozen")
            settings = copy.deepcopy(analysis_settings())
            settings["visit_order"] = ["before", "typo"]
            dump(directory / "settings.json", settings)
            with self.assertRaisesRegex(ValueError, "visit order"):
                freeze(
                    directory / "package.json",
                    directory / "observations.csv",
                    directory / "settings.json",
                    directory / "bad-plan",
                )
            self.assertFalse((directory / "bad-plan").exists())


if __name__ == "__main__":
    unittest.main()
