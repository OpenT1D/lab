"""OT-055 method-independent preparation and observation leakage controls."""

import json
import unittest
from copy import deepcopy
from pathlib import Path

from experiments.mmtt_sampling.design import project_samples, retained_indices, validate_design

FIXTURE = Path(__file__).resolve().parents[1] / "experiments/mmtt_sampling/fixtures/design.json"


class SamplingDesignTests(unittest.TestCase):
    def setUp(self):
        self.design = json.loads(FIXTURE.read_text())

    def test_frozen_synthetic_design(self):
        self.assertEqual(validate_design(self.design), self.design)
        for subset in self.design["subsets"].values():
            self.assertEqual(retained_indices(self.design["full_times_minutes"], subset)[-1], 5)

    def test_rejects_evaluation_selection_and_unallocated_person(self):
        for person in ("invented-evaluation-01", "unallocated"):
            with self.subTest(person=person):
                self.design["selection_participants"] = [person]
                with self.assertRaisesRegex(ValueError, "development participants only"):
                    validate_design(self.design)

    def test_rejects_non_observed_times_changed_window_and_duplicate_design(self):
        for value in ([0, 20, 120], [0, 60, 90], [0, 60, 60, 120], [0, True, 120]):
            with self.subTest(value=value), self.assertRaises(ValueError):
                retained_indices([0, 30, 60, 90, 120], value)
        self.design["subsets"]["four-times"] = self.design["subsets"]["three-times"]
        with self.assertRaisesRegex(ValueError, "distinct"):
            validate_design(self.design)

    def test_rejects_boolean_window_and_unbounded_times_without_numeric_overflow(self):
        for window in ([False, 120], [0, True], [0, 60, 120], [0, 10**400, 120]):
            with self.subTest(window=window), self.assertRaises(ValueError):
                self.design["window_minutes"] = window
                validate_design(self.design)
        for actual in ([0, 10**400, 120], [0, float("inf"), 120], [0, -1, 120]):
            with self.subTest(actual=actual), self.assertRaises(ValueError):
                retained_indices(actual, [0, 120])

    def test_removed_rows_cannot_affect_projected_input(self):
        samples = [
            {"time_minutes": t, "c_peptide": [10, 20], "glucose": 5 + t / 20}
            for t in self.design["full_times_minutes"]
        ]
        schedule = self.design["subsets"]["three-times"]
        expected = project_samples(samples, schedule)
        poisoned = deepcopy(samples)
        for row in poisoned:
            if row["time_minutes"] not in schedule:
                row["c_peptide"] = "invalid-removed-value"
                row["glucose"] = float("nan")
        self.assertEqual(project_samples(poisoned, schedule), expected)
        expected[0]["c_peptide"].append(999)
        self.assertEqual(samples[0]["c_peptide"], [10, 20])

    def test_missing_time_fails_instead_of_inventing_measurement(self):
        with self.assertRaisesRegex(ValueError, "not actually observed"):
            project_samples([{"time_minutes": 0}, {"time_minutes": 120}], [0, 60, 120])

    def test_rejects_unknown_fields_and_non_synthetic_execution(self):
        self.design["scope"] = "human-evaluation"
        with self.assertRaisesRegex(ValueError, "synthetic"):
            validate_design(self.design)
        self.design["scope"] = "synthetic-preparation"
        self.design["full_fit_initial_values"] = [1, 2]
        with self.assertRaisesRegex(ValueError, "Unexpected"):
            validate_design(self.design)


class SelectionFreezeTests(unittest.TestCase):
    def test_development_inventory_keeps_visits_together(self):
        from experiments.mmtt_sampling.design import validate_development_times

        design = json.loads(FIXTURE.read_text())
        inventory = json.loads(FIXTURE.with_name("development-times.json").read_text())
        self.assertEqual(validate_development_times(design, inventory), inventory)
        mutations = [
            inventory[:-1],
            inventory + [inventory[0]],
            [dict(inventory[0], participant_id="invented-evaluation-01")],
            [dict(row, times_minutes=[0, 60, 120]) for row in inventory],
        ]
        for mutation in mutations:
            with self.subTest(mutation=mutation), self.assertRaises(ValueError):
                validate_development_times(design, mutation)

    def test_duplicate_json_allocation_is_rejected(self):
        from experiments.mmtt_sampling.__main__ import unique_fields

        with self.assertRaisesRegex(ValueError, "Duplicate JSON"):
            json.loads(
                '{"person": "development", "person": "evaluation"}', object_pairs_hook=unique_fields
            )

    def test_freeze_cli_saves_source_hashes_and_refuses_overwrite(self):
        import hashlib
        import subprocess
        import sys
        import tempfile

        with tempfile.TemporaryDirectory() as temporary:
            target = Path(temporary) / "selection.json"
            command = [
                sys.executable,
                "-m",
                "experiments.mmtt_sampling",
                "freeze",
                "--design",
                str(FIXTURE),
                "--development-times",
                str(FIXTURE.with_name("development-times.json")),
                "--output",
                str(target),
            ]
            result = subprocess.run(command, capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            saved = target.read_bytes()
            receipt = json.loads(saved)
            self.assertEqual(
                receipt["design_sha256"], hashlib.sha256(FIXTURE.read_bytes()).hexdigest()
            )
            repeated = subprocess.run(command, capture_output=True, text=True)
            self.assertEqual(repeated.returncode, 2)
            self.assertEqual(target.read_bytes(), saved)


if __name__ == "__main__":
    unittest.main()
