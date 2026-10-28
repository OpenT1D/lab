"""Causal external prediction checks on self-authored normalized observations."""

import copy
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from experiments.m3.azt1d.common import MINUTE
from experiments.m3.azt1d.data import forecast_rows, validate_observations
from experiments.m3.common import read
from experiments.m3.external.fixtures import generate
from experiments.m3.external.metrics import summarize_case


class ExternalCausalDataTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.registry = generate(self.root / "input", people=1)
        self.person = self.registry["people"][0]
        self.document = read(self.person["input"]["file"])[0]
        self.rows = validate_observations(
            self.document, self.person["id"], *self.person["bounds_us"]
        )
        # Declared arithmetic coefficients, not a claimed fitted/verified model.
        # Unequal weights make feature order and use of all six values observable.
        self.model = {
            "intercept": 7.0,
            "coef": [1, 2, 3, 4, 5, 6],
            "mean": [10, 20, 30, 40, 50, 60],
            "scale": [1, 2, 3, 4, 5, 6],
        }

    def forecast(self, rows, origin=60 * MINUTE):
        with patch("experiments.m3.estimator.fit", side_effect=AssertionError("No external fit")):
            return next(
                row
                for row in forecast_rows(
                    rows, self.person["id"], "evaluation", self.person["bounds_us"], self.model
                )
                if row["origin_us"] == origin
            )

    def test_exact_six_previous_measurements_drive_prediction_in_declared_order(self):
        origin = 60 * MINUTE
        row = self.forecast(self.rows)
        expected_times = [minute * MINUTE for minute in (35, 40, 45, 50, 55, 60)]
        expected_values = [self.rows[time]["value"] for time in expected_times]
        self.assertEqual([point["time_us"] for point in row["history_rows"]], expected_times)
        self.assertEqual(row["features"], expected_values)
        expected = 7 + sum(
            value - center for value, center in zip(expected_values, self.model["mean"])
        )
        self.assertAlmostEqual(row["forecasts"]["ridge"], expected)
        self.assertEqual(row["forecasts"]["persistence"], self.rows[origin]["value"])
        changed = copy.deepcopy(self.rows)
        for time, point in changed.items():
            if time not in expected_times:
                point["value"] = 999
        self.assertEqual(self.forecast(changed)["forecasts"], row["forecasts"])

    def test_future_target_values_missingness_and_availability_cannot_change_prediction(self):
        original = self.forecast(self.rows)
        target_time = 90 * MINUTE
        for changes in (
            {"value": 50},
            {"value": 350},
            {"status": "ambiguous", "value": None},
            {"available_us": self.person["bounds_us"][1] + MINUTE},
        ):
            with self.subTest(changes=changes):
                changed = copy.deepcopy(self.rows)
                changed[target_time].update(changes)
                after = self.forecast(changed)
                self.assertEqual(after["features"], original["features"])
                self.assertEqual(after["forecasts"], original["forecasts"])
        changed = copy.deepcopy(self.rows)
        del changed[target_time]
        after = self.forecast(changed)
        self.assertEqual(after["forecasts"], original["forecasts"])
        self.assertEqual(after["target"]["status"], "missing")

    def test_late_history_is_unavailable_until_it_has_arrived(self):
        changed = copy.deepcopy(self.rows)
        changed[45 * MINUTE]["available_us"] = 60 * MINUTE + 1
        row = self.forecast(changed)
        self.assertIsNone(row["forecasts"])
        self.assertEqual(row["reason"], "history_unavailable")
        self.assertIsNotNone(self.forecast(changed, origin=65 * MINUTE)["forecasts"])
        changed[45 * MINUTE]["available_us"] = 60 * MINUTE
        self.assertEqual(self.forecast(changed)["forecasts"], self.forecast(self.rows)["forecasts"])

    def test_a_clock_break_excludes_only_histories_spanning_that_break(self):
        changed = copy.deepcopy(self.rows)
        for time, point in changed.items():
            if time >= 50 * MINUTE:
                point["segment"] = "second-invented-segment"
        row = self.forecast(changed)
        self.assertIsNone(row["forecasts"])
        self.assertEqual(row["reason"], "clock_discontinuity")
        self.assertIsNotNone(self.forecast(changed, origin=75 * MINUTE)["forecasts"])

    def test_microsecond_jitter_is_never_rounded_into_history_or_target(self):
        for minute, expected_reason, target_status in (
            (45, "history_gap", "measured"),
            (90, None, "missing"),
        ):
            with self.subTest(minute=minute):
                changed = copy.deepcopy(self.document)
                point = next(p for p in changed["rows"] if p["time_us"] == minute * MINUTE)
                point["time_us"] += 1
                point["available_us"] += 1
                point["raw_time"] += ".000001"
                rows = validate_observations(changed, self.person["id"], *self.person["bounds_us"])
                row = self.forecast(rows)
                self.assertEqual(row["reason"], expected_reason)
                self.assertEqual(row["target"]["status"], target_status)
                if expected_reason is None:
                    self.assertEqual(row["forecasts"], self.forecast(self.rows)["forecasts"])
                else:
                    self.assertIsNone(row["forecasts"])

    def test_external_warmup_and_end_targets_keep_the_registered_denominator(self):
        unchanged_model = copy.deepcopy(self.model)
        with patch("experiments.m3.estimator.fit", side_effect=AssertionError("No external fit")):
            traces = list(
                forecast_rows(
                    self.rows, self.person["id"], "evaluation", self.person["bounds_us"], self.model
                )
            )
        result = summarize_case(
            self.person["origins_us"],
            traces,
            execution_status="completed",
            bounds_us=self.person["bounds_us"],
        )
        self.assertEqual(len(traces), len(self.person["origins_us"]))
        self.assertTrue(all(row["reason"] == "evaluation_warmup" for row in traces[:12]))
        self.assertIsNotNone(traces[12]["forecasts"])
        self.assertTrue(all(row["target"]["status"] == "outside_split" for row in traces[-6:]))
        self.assertTrue(all(row["forecasts"] is not None for row in traces[-6:]))
        self.assertEqual(
            (result["planned"], result["predicted"], result["scored"]), (864, 852, 846)
        )
        self.assertTrue(result["eligible_for_primary"])
        self.assertNotIn("development_eligible", result)
        self.assertEqual(self.model, unchanged_model)

    def test_optional_fixture_defects_preserve_missingness_and_disclose_prior_conversion(self):
        registry = generate(self.root / "with-gaps", people=1, gaps=True)
        self.assertEqual(registry["prior_access"]["status"], "present")
        self.assertEqual(registry["source"]["format"], "normalized-cgm/1")
        person = registry["people"][0]
        self.assertNotEqual(person["id"], "invented-1")
        self.assertEqual(set(person), {"id", "input", "bounds_us", "origins_us"})
        document = read(person["input"]["file"])[0]
        rows = validate_observations(document, person["id"], *person["bounds_us"])
        self.assertEqual(rows[23 * 5 * MINUTE]["status"], "missing")
        self.assertIsNone(rows[23 * 5 * MINUTE]["value"])
        self.assertNotIn(59 * 5 * MINUTE, rows)
        self.assertNotIn(59 * 5 * MINUTE, person["origins_us"])
        self.assertEqual(rows[67 * 5 * MINUTE]["available_us"], (67 * 5 + 1) * MINUTE)
        self.assertEqual(person["origins_us"], sorted(rows))


if __name__ == "__main__":
    unittest.main()
