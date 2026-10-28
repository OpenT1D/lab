"""Independent arithmetic, missingness and participant-weighting examples."""

import copy
import json
import math
import subprocess
import sys
import unittest

from experiments.m3.azt1d.common import MINUTE
from experiments.m3.azt1d.metrics import summarize_case, summarize_study


def trace(
    origin,
    *,
    ridge=102,
    persistence=100,
    target=100,
    status="measured",
    bound=None,
    reason=None,
    phase="evaluation",
):
    history = [
        {
            "time_us": origin - offset * MINUTE,
            "available_us": origin - offset * MINUTE,
            "status": "measured",
            "value": persistence,
        }
        for offset in (25, 20, 15, 10, 5, 0)
    ]
    return {
        "person": "invented",
        "phase": phase,
        "origin_us": origin,
        "history_rows": history,
        "features": [persistence] * 6 if reason is None else None,
        "forecasts": {"ridge": ridge, "persistence": persistence} if reason is None else None,
        "target": {
            "status": status,
            "value": target if status == "measured" else None,
            "bound": bound,
        },
        "reason": reason,
        "origin_stratum": "low"
        if persistence < 70
        else "high"
        if persistence > 180
        else "in_range",
    }


def summary(rows, *, planned=None, development=True, status="completed"):
    if planned is None:
        planned = [row["origin_us"] for row in rows]
    end = (max(planned) + 60 * MINUTE) if planned else 100 * MINUTE
    return summarize_case(
        planned, rows, development_eligible=development, execution_status=status, bounds_us=(0, end)
    )


def qualified(difference, *, count=289, step=5, **kwargs):
    # Constant targets and persistent origin readings make exact per-person MAE differences.
    rows = [trace((60 + index * step) * MINUTE, ridge=100 + difference) for index in range(count)]
    return summary(rows, **kwargs)


class AZT1DMetricsTests(unittest.TestCase):
    def test_independent_hand_calculations_and_origin_strata(self):
        rows = [
            trace(60 * MINUTE, ridge=110, persistence=100, target=120),
            trace(65 * MINUTE, ridge=130, persistence=100, target=120),
            trace(70 * MINUTE, ridge=55, persistence=60, target=50),
        ]
        result = summary(rows)
        self.assertEqual(result["planned"], 3)
        self.assertEqual(result["ridge"]["mae"], 25 / 3)
        self.assertAlmostEqual(result["ridge"]["rmse"], math.sqrt(75))
        self.assertEqual(result["ridge"]["bias"], 5 / 3)
        self.assertEqual(result["persistence"]["mae"], 50 / 3)
        self.assertEqual(result["persistence"]["rmse"], math.sqrt(300))
        self.assertEqual(result["persistence"]["bias"], -10)
        self.assertEqual(result["paired"]["mae_difference"], -25 / 3)
        self.assertEqual(result["origin_strata"]["low"]["scored"], 1)
        self.assertEqual(result["origin_strata"]["in_range"]["scored"], 2)
        self.assertFalse(result["eligible_for_primary"])
        json.dumps(result, allow_nan=False)

    def test_censor_bounds_are_not_point_targets(self):
        rows = [
            trace(60 * MINUTE, ridge=50, persistence=35, status="censored_low", bound=40),
            trace(65 * MINUTE, ridge=350, persistence=410, status="censored_high", bound=400),
            trace(70 * MINUTE, ridge=250, status="censored_high", bound=None),
        ]
        result = summary(rows)
        self.assertEqual(result["predicted"], 3)
        self.assertEqual(result["scored"], 0)
        self.assertIsNone(result["ridge"]["mae"])
        self.assertEqual(result["ridge"]["censored_targets"], 3)
        self.assertEqual(result["ridge"]["censored_count"], 2)
        self.assertEqual(result["ridge"]["mean_censored_absolute_error_lower_bound"], 30)
        self.assertEqual(result["persistence"]["mean_censored_absolute_error_lower_bound"], 0)

    def test_partial_failures_keep_full_denominators_and_missing_future_forecasts(self):
        planned = [time * MINUTE for time in (60, 65, 70, 75, 80)]
        rows = [
            trace(planned[0]),
            trace(planned[1], status="missing"),
            trace(planned[2], reason="history_gap"),
        ]
        result = summary(rows, planned=planned, status="failed")
        self.assertEqual(
            (result["planned"], result["attempted"], result["not_attempted"]), (5, 3, 2)
        )
        self.assertEqual((result["predicted"], result["scored"]), (2, 1))
        self.assertEqual(result["prediction_coverage"], 2 / 5)
        self.assertEqual(result["score_coverage"], 1 / 5)
        self.assertEqual(result["scoring_exclusions"], {"history_gap": 1, "target_missing": 1})
        self.assertEqual(result["origin_strata"]["unknown"]["not_attempted"], 2)
        self.assertEqual(sum(s["planned"] for s in result["origin_strata"].values()), 5)
        self.assertFalse(result["eligible_for_primary"])
        with self.assertRaisesRegex(ValueError, "False case completion"):
            summary(rows, planned=planned)
        with self.assertRaisesRegex(ValueError, "Unattempted case"):
            summary(rows, planned=planned, status="not_attempted")

    def test_eligibility_needs_independent_development_span_and_completion(self):
        self.assertTrue(qualified(2)["eligible_for_primary"])
        self.assertFalse(qualified(2, count=288)["eligible_for_primary"])
        self.assertFalse(qualified(2, count=600, step=1)["eligible_for_primary"])
        self.assertFalse(qualified(2, development=False)["eligible_for_primary"])
        self.assertFalse(qualified(2, status="interrupted")["eligible_for_primary"])
        rows = [trace((60 + i * 5) * MINUTE, phase="validation") for i in range(289)]
        self.assertFalse(summary(rows)["eligible_for_primary"])

    def test_study_weights_people_not_correlated_points(self):
        first, second = qualified(2), qualified(10, count=2890)
        result = summarize_study({"b": second, "a": first})
        self.assertEqual(result["primary"]["mean_person_mae_difference"], 6)
        self.assertEqual(result["equal_person_metrics"]["ridge"]["mae"], 6)
        self.assertEqual(result["primary"]["participant_bootstrap_95"], [2, 10])
        self.assertEqual(result["primary"]["paired_people"], 2)
        self.assertTrue(result["complete_cohort"])
        self.assertEqual(result, summarize_study({"a": first, "b": second}))
        doubled = summarize_study({"a": qualified(2, count=578), "b": second})
        self.assertEqual(result["primary"], doubled["primary"])
        json.dumps(result, allow_nan=False)

    def test_incomplete_people_remain_and_single_person_uncertainty_is_undefined(self):
        failed = summary([], planned=[60 * MINUTE], status="not_attempted")
        result = summarize_study({"available": qualified(2), "missing": failed})
        self.assertFalse(result["complete_cohort"])
        self.assertEqual(result["planned_people"], 2)
        self.assertEqual(result["contributing_people"], 1)
        self.assertEqual(result["primary"]["excluded_people"], ["missing"])
        self.assertIsNone(result["primary"]["participant_bootstrap_95"])
        self.assertEqual(set(result["people"]), {"available", "missing"})
        none = summarize_study({"missing": failed})
        self.assertIsNone(none["primary"]["mean_person_mae_difference"])
        self.assertIsNone(none["equal_person_metrics"]["ridge"]["mae"])

    def test_false_schedules_nonfinite_metrics_and_strata_are_rejected(self):
        row = trace(60 * MINUTE)
        for replacement in (
            {"origin_us": 65 * MINUTE},
            {"origin_stratum": "low"},
            {"forecasts": {"ridge": float("nan"), "persistence": 100}},
            {"forecasts": {"ridge": 102, "persistence": 99}},
            {"target": {"status": "measured", "value": 100, "bound": 40}},
        ):
            changed = dict(row, **replacement)
            with self.subTest(replacement=replacement), self.assertRaises(ValueError):
                summary([changed], planned=[60 * MINUTE])
        case = copy.deepcopy(qualified(2))
        case["execution_status"] = "failed"
        with self.assertRaisesRegex(ValueError, "False primary eligibility"):
            summarize_study({"invented": case})

    def test_metrics_import_needs_no_estimator_or_site_packages(self):
        command = (
            "import sys; import experiments.m3.azt1d.metrics; "
            "assert 'experiments.m3.estimator' not in sys.modules; "
            "assert 'sklearn' not in sys.modules; assert 'numpy' not in sys.modules"
        )
        subprocess.run([sys.executable, "-S", "-c", command], check=True)


if __name__ == "__main__":
    unittest.main()
