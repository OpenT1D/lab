"""Synthetic counterexamples for the separate AZT1D registered-time contract."""

import copy
import unittest
from unittest.mock import patch

from experiments.m3.azt1d.common import MINUTE, SCHEMA
from experiments.m3.azt1d.data import (
    eligibility,
    forecast_rows,
    history,
    origins,
    target,
    timing_summary,
    training_windows,
    validate_observations,
)


def point(time, source, **changes):
    row = {
        "time_us": time,
        "available_us": time,
        "segment": "invented-segment",
        "raw_time": f"invented-{time}",
        "status": "measured",
        "value": 100.0,
        "bound": None,
        "source_rows": [source + 1],
    }
    row.update(changes)
    return row


def document(rows, start=0, end=200 * MINUTE):
    return {
        "schema": SCHEMA,
        "person": "invented",
        "clock": "local_elapsed",
        "unit": "mg/dL",
        "bounds_us": [start, end],
        "rows": rows,
    }


def regular(offset=0):
    rows = [point(offset + time * MINUTE, index) for index, time in enumerate(range(0, 200, 5))]
    return validate_observations(document(rows), "invented", 0, 200 * MINUTE)


class RegisteredTimeContract(unittest.TestCase):
    def test_irregular_origins_and_exact_microseconds_are_preserved(self):
        offset = 17_000_001
        rows = regular(offset)
        extra = offset + 37 * MINUTE
        rows[extra] = point(extra, 1000, status="missing", value=None)
        self.assertIn(extra, origins(rows))
        origin = offset + 60 * MINUTE
        self.assertEqual(history(rows, origin, 0, "development"), ([100.0] * 6, None))
        self.assertEqual(history(rows, origin + 1, 0, "development"), (None, "history_gap"))
        self.assertEqual(target(rows, origin, 200 * MINUTE)["value"], 100.0)
        huge = 2**53 + 1
        raw = document([point(huge, 0)], huge, huge + 1)
        self.assertEqual(list(validate_observations(raw, "invented", huge, huge + 1)), [huge])

    def test_duplicate_time_and_source_rows_rejected(self):
        for rows in (
            [point(0, 0), point(0, 1)],
            [point(5 * MINUTE, 0), point(0, 1)],
            [point(0, 0), point(MINUTE, 0)],
            [point(0, 0, source_rows=[2, 1])],
            [point(0, 0, source_rows=[1, 1])],
            [point(0, 0, source_rows=[True])],
            [point(0, 0, source_rows=[0])],
        ):
            with self.subTest(rows=rows), self.assertRaises(ValueError):
                validate_observations(document(rows), "invented", 0, 200 * MINUTE)
        row = point(0, 0, source_rows=[1, 2, 3])
        normalized = validate_observations(document([row]), "invented", 0, 200 * MINUTE)
        self.assertEqual(normalized[0]["source_rows"], [1, 2, 3])

    def test_numeric_status_clock_and_unknown_fields_are_strict(self):
        changes = (
            {"time_us": True},
            {"time_us": 0.0},
            {"available_us": -1},
            {"available_us": False},
            {"value": True},
            {"value": float("nan")},
            {"value": 0},
            {"value": "100"},
            {"bound": 40},
            {"status": "unknown"},
            {"status": "ambiguous", "value": 100},
            {"status": "censored_low", "value": 40, "bound": 40},
            {"status": "censored_low", "value": None, "bound": 0},
            {"extra": None},
        )
        for replacement in changes:
            with self.subTest(replacement=replacement), self.assertRaises((ValueError, TypeError)):
                validate_observations(
                    document([point(0, 0, **replacement)]), "invented", 0, 200 * MINUTE
                )
        for status in ("missing", "invalid", "ambiguous", "unsupported"):
            rows = [point(0, 0, status=status, value=None)]
            self.assertEqual(
                validate_observations(document(rows), "invented", 0, 200 * MINUTE)[0]["status"],
                status,
            )
        raw = document([point(0, 0)])
        raw["extra"] = None
        with self.assertRaises(ValueError):
            validate_observations(raw, "invented", 0, 200 * MINUTE)
        with self.assertRaises(ValueError):
            validate_observations(document([point(200 * MINUTE, 0)]), "invented", 0, 200 * MINUTE)
        raw = document([point(0, 0, status="censored_low", value=None, bound=40)])
        self.assertEqual(validate_observations(raw, "invented", 0, 200 * MINUTE)[0]["bound"], 40)

    def test_boundaries_availability_and_segment_exclusions(self):
        rows = regular()
        origin = 60 * MINUTE
        self.assertEqual(
            history(rows, origin, 40 * MINUTE, "validation")[1], "history_outside_split"
        )
        self.assertEqual(history(rows, 59 * MINUTE, 0, "evaluation")[1], "evaluation_warmup")
        self.assertIsNone(history(rows, origin, 0, "evaluation")[1])
        self.assertEqual(target(rows, origin, 90 * MINUTE)["status"], "outside_split")
        rows[origin]["available_us"] = origin + 1
        self.assertEqual(history(rows, origin, 0, "development")[1], "history_unavailable")
        rows[origin]["available_us"] = origin
        rows[origin]["segment"] = "other"
        self.assertEqual(history(rows, origin, 0, "development")[1], "clock_discontinuity")
        self.assertEqual(target(rows, origin, 200 * MINUTE)["status"], "clock_discontinuity")

    def test_delayed_training_label_and_future_target_do_not_change_forecast(self):
        rows = regular()
        origin = 60 * MINUTE
        self.assertIn(origin, [window[0] for window in training_windows(rows, 0, 200 * MINUTE)])
        rows[origin + 30 * MINUTE]["available_us"] = 200 * MINUTE
        self.assertNotIn(origin, [window[0] for window in training_windows(rows, 0, 200 * MINUTE)])
        with patch("experiments.m3.estimator.predict", return_value=101):
            before = {
                row["origin_us"]: row
                for row in forecast_rows(rows, "invented", "evaluation", (0, 200 * MINUTE), {})
            }
            poisoned = copy.deepcopy(rows)
            for time, row in poisoned.items():
                if time > origin:
                    row.update(status="ambiguous", value=None)
            after = {
                row["origin_us"]: row
                for row in forecast_rows(poisoned, "invented", "evaluation", (0, 200 * MINUTE), {})
            }
        self.assertEqual(before[origin]["forecasts"], after[origin]["forecasts"])
        self.assertEqual(after[origin]["forecasts"], {"ridge": 101, "persistence": 100})
        self.assertEqual(after[origin]["target"]["status"], "ambiguous")
        del poisoned[origin + 30 * MINUTE]
        self.assertEqual(target(poisoned, origin, 200 * MINUTE)["status"], "missing")
        with patch("experiments.m3.estimator.predict", return_value=101):
            missing_target = {
                row["origin_us"]: row
                for row in forecast_rows(poisoned, "invented", "evaluation", (0, 200 * MINUTE), {})
            }
        self.assertEqual(missing_target[origin]["forecasts"], before[origin]["forecasts"])

    def test_target_is_inspected_after_prediction(self):
        rows = regular()
        calls = []

        def predict_first(model, features):
            calls.append("prediction")
            return 100

        def target_second(observations, origin, end):
            if origin == 60 * MINUTE:
                self.assertEqual(calls[-1], "prediction")
            calls.append("target")
            return target(observations, origin, end)

        with (
            patch("experiments.m3.estimator.predict", side_effect=predict_first),
            patch("experiments.m3.azt1d.data.target", side_effect=target_second),
        ):
            list(forecast_rows(rows, "invented", "evaluation", (0, 200 * MINUTE), {}))

    def test_all_unusable_registered_origins_and_time_density_remain_accounted(self):
        raw = [
            point(time * MINUTE, index, status="unsupported", value=None)
            for index, time in enumerate((0, 1, 2, 100))
        ]
        rows = validate_observations(document(raw), "invented", 0, 200 * MINUTE)
        trace = list(forecast_rows(rows, "invented", "evaluation", (0, 200 * MINUTE), {}))
        self.assertEqual(len(trace), 4)
        self.assertTrue(all(row["forecasts"] is None for row in trace))
        self.assertTrue(all(row["origin_stratum"] == "unknown" for row in trace))
        timing = timing_summary(rows, 0, 200 * MINUTE)
        self.assertEqual(timing["registered_origins"], 4)
        self.assertEqual(timing["elapsed_us"], 200 * MINUTE)
        self.assertEqual(timing["maximum_interval_us"], 98 * MINUTE)
        self.assertEqual(timing["gaps_over_minutes"]["60"], 1)
        self.assertEqual(
            timing["interval_distribution"],
            [{"interval_us": MINUTE, "count": 2}, {"interval_us": 98 * MINUTE, "count": 1}],
        )

    def test_count_does_not_replace_twenty_four_hour_span(self):
        self.assertFalse(eligibility([index * MINUTE for index in range(288)]))
        self.assertFalse(eligibility([]))
        self.assertFalse(eligibility([index * 5 * MINUTE for index in range(288)]))
        self.assertTrue(eligibility([index * 5 * MINUTE for index in range(289)]))
        with self.assertRaises(ValueError):
            eligibility([0, 0])


if __name__ == "__main__":
    unittest.main()
