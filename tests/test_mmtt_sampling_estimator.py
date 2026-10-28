"""Prepared independent vectors executed on OT-054, without another estimator."""

import csv
import io
import json
import unittest
from pathlib import Path

from experiments.mmtt_sampling.design import retained_indices
from experiments.mmtt_sampling.fixtures import example
from experiments.mmtt_sampling.masking import mask_csv
from experiments.observation_analysis.analysis import evaluate
from experiments.observation_analysis.estimator import estimate, trapezoid
from experiments.observation_analysis.fixtures import analysis_settings, csv_bytes

HERE = Path(__file__).resolve().parents[1] / "experiments/mmtt_sampling/fixtures"


class SharedSamplingEstimatorTests(unittest.TestCase):
    def test_manufactured_totals_auc_pair_changes_and_negative_rate_are_schedule_invariant(self):
        reference = json.loads((HERE / "numerical-reference.json").read_text())
        design = json.loads((HERE / "design.json").read_text())
        variant = {
            key: float(reference["kinetics"][key])
            for key in ("k1_per_min", "k2_per_min", "k3_per_min", "volume_l")
        }
        variant.update(
            id="manufactured",
            rationale="Independent synthetic closed-form control",
            initial_peripheral_factor=1.0,
        )
        tolerance = float(reference["absolute_software_tolerance_pmol"])
        for case in reference["cases"]:
            for name, schedule in {
                "full": design["full_times_minutes"],
                **design["subsets"],
            }.items():
                with self.subTest(case=case["id"], schedule=name):
                    indices = retained_indices(reference["times_minutes"], schedule)
                    cp = [float(case["baseline_cpeptide_pmol_l"][i]) for i in indices]
                    result = estimate(schedule, cp, variant)
                    self.assertAlmostEqual(
                        result["total_pmol"], float(case["expected_total_pmol"]), delta=tolerance
                    )
                    self.assertAlmostEqual(
                        trapezoid(schedule, cp),
                        float(case["expected_cpeptide_auc_pmol_min_l"]),
                        delta=tolerance,
                    )
                    if "expected_terminal_rate_pmol_min" in case:
                        self.assertEqual(result["status"], "boundary_failed")
                        self.assertAlmostEqual(
                            result["minimum_rate_pmol_min"],
                            float(case["expected_terminal_rate_pmol_min"]),
                            delta=tolerance,
                        )
                        self.assertLess(result["intervals"][-1]["end_rate_pmol_min"], 0)
                    else:
                        self.assertEqual(result["status"], "completed")
                    if "followup_cpeptide_pmol_l" in case:
                        follow = estimate(
                            schedule,
                            [float(case["followup_cpeptide_pmol_l"][i]) for i in indices],
                            variant,
                        )
                        self.assertAlmostEqual(
                            follow["total_pmol"] - result["total_pmol"],
                            float(case["expected_paired_change_pmol"]),
                            delta=tolerance,
                        )

    def test_every_retained_uncertainty_draw_reuses_the_same_keyed_measurement_error(self):
        package, raw, _ = example()
        settings = analysis_settings()
        settings["uncertainty"]["draws"] = 32
        full = evaluate(settings, package, raw)
        masked, _ = mask_csv(raw, package, [0, 60, 120])
        reduced = evaluate(settings, package, masked)
        for person, full_record in full["people"].items():
            reduced_record = reduced["people"][person]
            self.assertEqual(
                len(full_record["perturbations"]), len(reduced_record["perturbations"])
            )
            for a, b in zip(
                full_record["perturbations"], reduced_record["perturbations"], strict=True
            ):
                self.assertEqual(a["shared_offset_pmol_l"], b["shared_offset_pmol_l"])
                for visit in settings["visit_order"]:
                    indices = retained_indices(
                        full_record["references"][visit]["times_min"], [0, 60, 120]
                    )
                    self.assertEqual([a["visits"][visit][i] for i in indices], b["visits"][visit])

    def test_full_then_reduced_has_no_state_or_omitted_value_influence(self):
        package, raw, _ = example()
        settings = analysis_settings()
        settings["uncertainty"]["draws"] = 32
        masked, _ = mask_csv(raw, package, [0, 60, 120])
        expected = evaluate(settings, package, masked)
        rows = list(csv.reader(io.StringIO(raw.decode())))[1:]
        for row in rows:
            if float(row[3]) not in (0, 60, 120):
                row[4:] = ["NaN", "invalid status", "invalid removed C-peptide", "bad status"]
        poisoned = csv_bytes(rows)
        invalid_full = evaluate(settings, package, poisoned)
        self.assertFalse(invalid_full["import_valid"])
        retained, _ = mask_csv(poisoned, package, [0, 60, 120])
        self.assertEqual(evaluate(settings, package, retained), expected)


if __name__ == "__main__":
    unittest.main()
