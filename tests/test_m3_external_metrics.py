"""Synthetic external-cohort arithmetic, qualification and failure accounting."""

import copy
import inspect
import json
import math
import subprocess
import sys
import unittest

from experiments.m3.azt1d.common import MINUTE
from experiments.m3.external.metrics import METRIC, summarize_case, summarize_study


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
    return {
        "person": "invented_external",
        "phase": phase,
        "origin_us": origin,
        "history_rows": [
            {
                "time_us": origin - offset * MINUTE,
                "available_us": origin - offset * MINUTE,
                "status": "measured",
                "value": persistence,
            }
            for offset in (25, 20, 15, 10, 5, 0)
        ],
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


def summary(rows, *, planned=None, status="completed"):
    if planned is None:
        planned = [row["origin_us"] for row in rows]
    end = max(planned) + 60 * MINUTE if planned else 100 * MINUTE
    return summarize_case(planned, rows, execution_status=status, bounds_us=(0, end))


def qualified(ridge_error=2, *, persistence_error=0, count=289, step=5, **kwargs):
    rows = [
        trace(
            (60 + index * step) * MINUTE,
            ridge=100 + ridge_error,
            persistence=100 + persistence_error,
        )
        for index in range(count)
    ]
    return summary(rows, **kwargs)


class ExternalMetricsTests(unittest.TestCase):
    def test_hand_calculated_signed_bias_and_paired_windows(self):
        rows = [
            trace(60 * MINUTE, ridge=110, persistence=100, target=120),
            trace(65 * MINUTE, ridge=130, persistence=100, target=120),
            trace(70 * MINUTE, ridge=55, persistence=60, target=50),
            trace(75 * MINUTE, target=None, status="missing"),
            trace(80 * MINUTE, reason="history_gap"),
        ]
        result = summary(rows)
        self.assertEqual(result["ridge"]["mae"], 25 / 3)
        self.assertAlmostEqual(result["ridge"]["rmse"], math.sqrt(75))
        self.assertEqual(result["ridge"]["bias"], 5 / 3)
        self.assertEqual(result["persistence"]["mae"], 50 / 3)
        self.assertEqual(result["persistence"]["bias"], -10)
        self.assertEqual(result["paired"]["mae_difference"], -25 / 3)
        self.assertEqual(result["ridge"]["scored"], result["persistence"]["scored"])
        self.assertEqual((result["planned"], result["predicted"], result["scored"]), (5, 4, 3))
        self.assertEqual(result["score_coverage"], 3 / 5)
        self.assertEqual(result["origin_strata"]["low"]["scored"], 1)
        self.assertEqual(result["origin_strata"]["in_range"]["scored"], 2)
        json.dumps(result, allow_nan=False)

    def test_people_not_observation_counts_receive_equal_weight(self):
        first = qualified(2, persistence_error=10)
        second = qualified(10, count=2890)
        result = summarize_study({"more_rows": second, "fewer_rows": first})
        # Per-person differences -8 and +10 give +1, not the pooled +8.36.
        self.assertEqual(result["primary"]["mean_person_mae_difference"], 1)
        self.assertEqual(result["equal_person_metrics"]["ridge"]["mae"], 6)
        self.assertEqual(result["equal_person_metrics"]["persistence"]["mae"], 5)
        self.assertEqual(result["primary"]["participant_bootstrap_95"], [-8, 10])
        self.assertTrue(result["complete_cohort"])
        self.assertEqual(result["contributing_people"], 2)
        self.assertEqual(result, summarize_study({"fewer_rows": first, "more_rows": second}))
        repeated = summarize_study(
            {"fewer_rows": qualified(2, persistence_error=10, count=578), "more_rows": second}
        )
        self.assertEqual(result["primary"], repeated["primary"])

    def test_qualification_needs_count_span_and_completed_evaluation(self):
        self.assertTrue(qualified()["eligible_for_primary"])
        count_limited = qualified(count=287, step=10)
        self.assertEqual(
            count_limited["ineligibility_reasons"], ["insufficient_evaluation_windows"]
        )
        span_limited = qualified(count=288)
        self.assertEqual(span_limited["ineligibility_reasons"], ["insufficient_evaluation_span"])
        self.assertFalse(qualified(count=600, step=1)["eligible_for_primary"])
        self.assertFalse(qualified(status="interrupted")["eligible_for_primary"])
        rows = [trace((60 + i * 5) * MINUTE, phase="validation") for i in range(289)]
        self.assertEqual(summary(rows)["ineligibility_reasons"], ["not_evaluation"])

    def test_external_metric_does_not_invent_a_training_qualification(self):
        self.assertNotIn("development_eligible", inspect.signature(summarize_case).parameters)
        result = summarize_study({"invented_external": qualified()})
        self.assertEqual(result["metric"], "external-cgm-forecast/1")
        self.assertEqual(result["people"]["invented_external"]["metric"], METRIC)
        self.assertNotIn("development_eligible", json.dumps(result))
        self.assertIn("without refitting", result["interpretation"])
        false = dict(qualified(), development_eligible=True)
        with self.assertRaisesRegex(ValueError, "External case summary"):
            summarize_study({"invented_external": false})

    def test_failed_prefix_and_unattempted_cases_preserve_frozen_denominators(self):
        planned = [time * MINUTE for time in (60, 65, 70, 75, 80)]
        rows = [
            trace(planned[0]),
            trace(planned[1], status="missing"),
            trace(planned[2], reason="history_gap"),
        ]
        failed = summary(rows, planned=planned, status="failed")
        missing = summary([], planned=planned, status="not_attempted")
        self.assertEqual(
            (failed["planned"], failed["attempted"], failed["not_attempted"]), (5, 3, 2)
        )
        self.assertEqual((failed["prediction_coverage"], failed["score_coverage"]), (2 / 5, 1 / 5))
        self.assertEqual(failed["scoring_exclusions"], {"history_gap": 1, "target_missing": 1})
        self.assertEqual(failed["origin_strata"]["unknown"]["not_attempted"], 2)
        self.assertEqual(sum(s["planned"] for s in failed["origin_strata"].values()), 5)
        study = summarize_study({"available": qualified(), "failed": failed, "missing": missing})
        self.assertEqual((study["planned_people"], study["contributing_people"]), (3, 1))
        self.assertFalse(study["complete_cohort"])
        self.assertEqual(study["primary"]["excluded_people"], ["failed", "missing"])
        self.assertIsNone(study["primary"]["participant_bootstrap_95"])
        self.assertEqual(
            study["execution_status_counts"], {"completed": 1, "failed": 1, "not_attempted": 1}
        )
        empty = summarize_study({"missing": missing})
        self.assertIsNone(empty["primary"]["mean_person_mae_difference"])
        self.assertIsNone(empty["equal_person_metrics"]["ridge"]["mae"])
        with self.assertRaisesRegex(ValueError, "False case completion"):
            summary(rows, planned=planned)
        with self.assertRaisesRegex(ValueError, "Unattempted case"):
            summary(rows, planned=planned, status="not_attempted")

    def test_censoring_does_not_become_a_point_target(self):
        result = summary(
            [
                trace(60 * MINUTE, ridge=50, persistence=35, status="censored_low", bound=40),
                trace(65 * MINUTE, ridge=350, persistence=410, status="censored_high", bound=400),
            ]
        )
        self.assertEqual((result["predicted"], result["scored"]), (2, 0))
        self.assertIsNone(result["ridge"]["mae"])
        self.assertEqual(result["ridge"]["censored_count"], 2)
        self.assertEqual(result["ridge"]["mean_censored_absolute_error_lower_bound"], 30)

    def test_false_completion_forecast_pairing_and_identity_are_rejected(self):
        for replacement in (
            {"origin_us": 65 * MINUTE},
            {"forecasts": {"ridge": 102}},
            {"forecasts": {"ridge": float("nan"), "persistence": 100}},
            {"forecasts": {"ridge": 102, "persistence": 99}},
            {"origin_stratum": "low"},
        ):
            with self.subTest(replacement=replacement), self.assertRaises(ValueError):
                summary([dict(trace(60 * MINUTE), **replacement)], planned=[60 * MINUTE])
        case = copy.deepcopy(qualified())
        case["execution_status"] = "failed"
        with self.assertRaisesRegex(ValueError, "False primary eligibility"):
            summarize_study({"invented_external": case})
        case = dict(qualified(), metric="azt1d-cgm-forecast/1")
        with self.assertRaisesRegex(ValueError, "External case summary"):
            summarize_study({"invented_external": case})

    def test_metrics_import_requires_no_estimator_or_site_packages(self):
        command = (
            "import sys; import experiments.m3.external.metrics; "
            "assert 'experiments.m3.estimator' not in sys.modules; "
            "assert 'sklearn' not in sys.modules; assert 'numpy' not in sys.modules"
        )
        subprocess.run([sys.executable, "-S", "-c", command], check=True)


if __name__ == "__main__":
    unittest.main()
