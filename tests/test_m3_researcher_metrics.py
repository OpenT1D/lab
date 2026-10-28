"""Hand-calculated synthetic researcher forecast arithmetic and failure accounting."""

import copy
import json
import math
import random
import subprocess
import sys
import unittest

from experiments.m3.azt1d.common import MINUTE
from experiments.m3.researcher.metrics import METRIC, summarize_case, summarize_study


def trace(
    origin,
    *,
    candidate=102,
    persistence=100,
    target=100,
    status="measured",
    bound=None,
    reason=None,
):
    return {
        "origin_us": origin,
        "features": [persistence] * 6 if reason is None else None,
        "reason": reason,
        "candidate": candidate if reason is None else None,
        "persistence": persistence if reason is None else None,
        "target": {
            "status": status,
            "value": target if status == "measured" else None,
            "bound": bound,
        },
    }


def summary(rows, *, planned=None, status="completed", bounds=None):
    if planned is None:
        planned = [row["origin_us"] for row in rows]
    if bounds is None:
        bounds = (0, max(planned) + 60 * MINUTE if planned else 100 * MINUTE)
    return summarize_case(planned, rows, execution_status=status, bounds_us=bounds)


def qualified(candidate_error=2, *, persistence_error=0, count=289, step=5, **kwargs):
    return summary(
        [
            trace(
                (60 + index * step) * MINUTE,
                candidate=100 + candidate_error,
                persistence=100 + persistence_error,
            )
            for index in range(count)
        ],
        **kwargs,
    )


class ResearcherMetricsTests(unittest.TestCase):
    def test_hand_calculated_paired_error_bias_and_coverage(self):
        result = summary(
            [
                trace(60 * MINUTE, candidate=110, persistence=100, target=120),
                trace(65 * MINUTE, candidate=130, persistence=100, target=120),
                trace(70 * MINUTE, candidate=55, persistence=60, target=50),
                trace(75 * MINUTE, status="missing"),
                trace(80 * MINUTE, reason="history_gap"),
            ]
        )
        self.assertEqual(result["candidate"]["mae"], 25 / 3)
        self.assertAlmostEqual(result["candidate"]["rmse"], math.sqrt(75))
        self.assertEqual(result["candidate"]["bias"], 5 / 3)
        self.assertEqual(result["persistence"]["mae"], 50 / 3)
        self.assertEqual(result["persistence"]["bias"], -10)
        self.assertEqual(
            result["paired"],
            {"scored": 3, "origins_span_us": 10 * MINUTE, "mae_difference": -25 / 3},
        )
        self.assertEqual((result["planned"], result["forecastable"], result["scored"]), (5, 4, 3))
        self.assertEqual((result["prediction_coverage"], result["score_coverage"]), (4 / 5, 3 / 5))
        self.assertEqual(result["history_exclusions"], {"history_gap": 1})
        self.assertEqual(result["scoring_exclusions"], {"history_gap": 1, "target_missing": 1})
        self.assertEqual(result["target_status_counts"], {"measured": 4, "missing": 1})
        json.dumps(result, allow_nan=False)

    def test_negative_candidate_is_retained_as_a_valid_finite_forecast(self):
        result = summary([trace(60 * MINUTE, candidate=-5, target=10)])
        self.assertEqual(result["candidate"]["mae"], 15)
        self.assertEqual(result["candidate"]["bias"], -15)
        self.assertEqual(result["paired"]["mae_difference"], -75)

    def test_large_finite_errors_use_scaled_rmse_without_squaring_overflow(self):
        result = summary(
            [
                trace(60 * MINUTE, candidate=1e200),
                trace(65 * MINUTE, candidate=2e200),
            ]
        )
        expected = 2e200 * math.sqrt((0.5**2 + 1) / 2)
        self.assertTrue(math.isclose(result["candidate"]["rmse"], expected, rel_tol=1e-15))
        self.assertTrue(math.isclose(result["candidate"]["mae"], 1.5e200, rel_tol=1e-15))
        self.assertTrue(math.isclose(result["candidate"]["bias"], 1.5e200, rel_tol=1e-15))
        json.dumps(result, allow_nan=False)

    def test_largest_forecasts_support_finite_means_and_participant_bootstrap(self):
        result = summary(
            [
                trace(60 * MINUTE, candidate=1e308),
                trace(65 * MINUTE, candidate=-1e308),
            ]
        )
        self.assertEqual(result["candidate"]["mae"], 1e308)
        self.assertEqual(result["candidate"]["rmse"], 1e308)
        self.assertEqual(result["candidate"]["bias"], 0)
        study = summarize_study(
            {"positive": qualified(1e308), "negative": qualified(0, persistence_error=1e308)}
        )
        self.assertEqual(study["primary"]["mean_person_mae_difference"], 0)
        self.assertEqual(study["primary"]["participant_bootstrap_95"], [-1e308, 1e308])
        self.assertEqual(study["equal_person_metrics"]["candidate"]["mae"], 5e307)
        self.assertEqual(study["equal_person_metrics"]["persistence"]["mae"], 5e307)
        json.dumps(study, allow_nan=False)

    def test_extreme_representable_boundaries_do_not_overflow_or_underflow_means(self):
        minimum = math.ulp(0.0)
        origins = [(60 + index * 5) * MINUTE for index in range(289)]
        for candidate, target, expected in (
            (2 * minimum, minimum, minimum),
            (sys.float_info.max, minimum, sys.float_info.max),
        ):
            case = summary(
                [
                    trace(origin, candidate=candidate, persistence=target, target=target)
                    for origin in origins
                ]
            )
            with self.subTest(candidate=candidate):
                self.assertEqual(case["candidate"]["mae"], expected)
                self.assertEqual(case["candidate"]["rmse"], expected)
                self.assertEqual(case["candidate"]["bias"], expected)
                study = summarize_study({"first": case, "second": case})
                self.assertEqual(study["primary"]["mean_person_mae_difference"], expected)
                self.assertEqual(study["primary"]["participant_bootstrap_95"], [expected, expected])

    def test_unrepresentable_forecast_error_is_rejected_explicitly(self):
        with self.assertRaises(ValueError):
            summary([trace(60 * MINUTE, candidate=-1e308, target=1e308)])

    def test_censoring_and_unavailable_targets_never_become_point_scores(self):
        statuses = (
            "censored_low",
            "censored_high",
            "missing",
            "invalid",
            "ambiguous",
            "unsupported",
            "clock_discontinuity",
        )
        rows = [
            trace(
                (60 + index * 5) * MINUTE,
                status=status,
                bound=40
                if status == "censored_low"
                else 400
                if status == "censored_high"
                else None,
            )
            for index, status in enumerate(statuses)
        ]
        result = summary(rows)
        self.assertEqual((result["forecastable"], result["scored"]), (7, 0))
        self.assertEqual(result["target_status_counts"], dict.fromkeys(sorted(statuses), 1))
        for method in ("candidate", "persistence"):
            self.assertEqual(result[method]["scored"], 0)
            self.assertIsNone(result[method]["mae"])
            self.assertIsNone(result[method]["rmse"])
            self.assertIsNone(result[method]["bias"])
        self.assertIsNone(result["paired"]["origins_span_us"])
        result = summary([trace(60 * MINUTE, status="censored_low", bound=None)])
        self.assertEqual(result["scored"], 0)

    def test_failed_prefix_and_not_attempted_cases_preserve_denominators(self):
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
        self.assertIsNone(empty["equal_person_metrics"]["candidate"]["mae"])
        self.assertEqual(empty["people"]["missing"]["planned"], 5)
        with self.assertRaisesRegex(ValueError, "False case completion"):
            summary(rows, planned=planned)
        with self.assertRaisesRegex(ValueError, "Unattempted case"):
            summary(rows, planned=planned, status="not_attempted")
        with self.assertRaisesRegex(ValueError, "schedule"):
            summary(rows[1:], planned=planned, status="failed")

    def test_primary_floor_needs_both_paired_count_and_span_and_completion(self):
        self.assertTrue(qualified()["eligible_for_primary"])
        self.assertEqual(
            qualified(count=287, step=10)["ineligibility_reasons"],
            ["insufficient_evaluation_windows"],
        )
        self.assertEqual(
            qualified(count=288)["ineligibility_reasons"], ["insufficient_evaluation_span"]
        )
        self.assertFalse(qualified(count=600, step=1)["eligible_for_primary"])
        self.assertEqual(
            qualified(status="interrupted")["ineligibility_reasons"], ["execution_incomplete"]
        )
        # Exactly 288 paired windows and exactly 24 hours meet the declared floor.
        origins = [(60 + index * 5) * MINUTE for index in range(287)] + [1500 * MINUTE]
        self.assertTrue(summary([trace(origin) for origin in origins])["eligible_for_primary"])
        # Unscored long-span traces cannot establish the span of paired windows.
        rows = [trace((60 + index * 5) * MINUTE) for index in range(288)]
        rows.append(trace(1500 * MINUTE, status="missing"))
        self.assertEqual(summary(rows)["ineligibility_reasons"], ["insufficient_evaluation_span"])

    def test_aggregation_weights_people_and_resamples_people_not_windows(self):
        first = qualified(2, persistence_error=10)
        second = qualified(10, count=2890)
        study = summarize_study({"more_rows": second, "fewer_rows": first})
        self.assertEqual(study["primary"]["mean_person_mae_difference"], 1)
        self.assertEqual(study["equal_person_metrics"]["candidate"]["mae"], 6)
        self.assertEqual(study["equal_person_metrics"]["persistence"]["mae"], 5)
        self.assertEqual(study["primary"]["participant_bootstrap_95"], [-8, 10])
        self.assertTrue(study["complete_cohort"])
        repeated = summarize_study(
            {"fewer_rows": qualified(2, persistence_error=10, count=578), "more_rows": second}
        )
        self.assertEqual(study["primary"], repeated["primary"])
        self.assertEqual(study, summarize_study({"fewer_rows": first, "more_rows": second}))
        random.seed(99)
        self.assertEqual(study, summarize_study({"fewer_rows": first, "more_rows": second}))
        self.assertEqual(
            study["primary"]["person_differences"], {"fewer_rows": -8, "more_rows": 10}
        )

    def test_fixed_participant_bootstrap_and_execution_metadata_retention(self):
        cases = {
            name: dict(
                qualified(error, persistence_error=14 if name == "a" else 0),
                execution={"status": "completed", "elapsed_s": 1.5},
            )
            for name, error in (("a", 7), ("b", 2), ("c", 4), ("d", 19))
        }
        # Source-study bootstrap: 2000 draws, seed 301, empirical 50th/1950th
        # order statistics, applied to participant differences -7, 2, 4, 19.
        study = summarize_study(cases)
        self.assertEqual(study["primary"]["participant_bootstrap_95"], [-4.25, 14.75])
        self.assertEqual(study["people"]["a"]["execution"]["elapsed_s"], 1.5)

    def test_empty_schedule_uses_null_coverage_and_cannot_qualify(self):
        result = summary([], planned=[], bounds=(0, 100 * MINUTE))
        self.assertEqual(
            (result["planned"], result["attempted"], result["not_attempted"]), (0, 0, 0)
        )
        self.assertIsNone(result["prediction_coverage"])
        self.assertIsNone(result["score_coverage"])
        self.assertFalse(result["eligible_for_primary"])
        self.assertEqual(result["target_status_counts"], {})

    def test_evaluation_boundaries_and_warmup_are_exact(self):
        origin = 60 * MINUTE
        for malformed in (origin + 1, True, -1, 1.0):
            with self.subTest(time=malformed), self.assertRaises(ValueError):
                summary([dict(trace(origin), origin_us=malformed)], planned=[origin])
        for planned in ([origin, origin], [65 * MINUTE, origin], [True], [-1], [1.0]):
            with self.subTest(planned=planned), self.assertRaises(ValueError):
                summary([], planned=planned, status="not_attempted", bounds=(0, 100 * MINUTE))
        for bounds in ((True, 100 * MINUTE), (0, 0), (-1, 100), (0,), (0, 100, 200)):
            with self.subTest(bounds=bounds), self.assertRaises(ValueError):
                summary([], status="not_attempted", bounds=bounds)
        with self.assertRaisesRegex(ValueError, "warm-up"):
            summary([trace(59 * MINUTE)], bounds=(0, 100 * MINUTE))
        with self.assertRaisesRegex(ValueError, "history crosses"):
            summary([trace(20 * MINUTE)], bounds=(0, 100 * MINUTE))
        self.assertEqual(
            summary([trace(90 * MINUTE)], bounds=(30 * MINUTE, 150 * MINUTE))["scored"], 1
        )
        outside = trace(origin, status="outside_split")
        self.assertEqual(summary([outside], bounds=(0, 90 * MINUTE))["scored"], 0)
        with self.assertRaisesRegex(ValueError, "exclusion differs"):
            summary([trace(origin)], bounds=(0, 90 * MINUTE))
        with self.assertRaisesRegex(ValueError, "exclusion differs"):
            summary([outside], bounds=(0, 90 * MINUTE + 1))

    def test_invalid_forecast_feature_and_reason_combinations_are_rejected(self):
        origin = 60 * MINUTE
        replacements = (
            {"unexpected": 1},
            {"features": []},
            {"features": [100] * 5},
            {"features": [True] + [100] * 5},
            {"features": [0] + [100] * 5},
            {"features": ["100"] + [100] * 5},
            {"features": [float("nan")] + [100] * 5},
            {"candidate": None},
            {"candidate": True},
            {"candidate": float("inf")},
            {"persistence": 99},
            {"reason": "history_gap"},
            {"features": None},
            {"features": None, "reason": "history_gap"},
            {"features": None, "candidate": None, "persistence": None, "reason": " "},
        )
        for replacement in replacements:
            with self.subTest(replacement=replacement), self.assertRaises(ValueError):
                summary([dict(trace(origin), **replacement)])

    def test_target_contract_rejects_point_imputation_and_invalid_bounds(self):
        targets = (
            {"status": "measured", "value": 0, "bound": None},
            {"status": "measured", "value": True, "bound": None},
            {"status": "measured", "value": 100, "bound": 100},
            {"status": "missing", "value": 100, "bound": None},
            {"status": "missing", "value": None, "bound": 100},
            {"status": "censored_low", "value": None, "bound": -1},
            {"status": "censored_low", "value": None, "bound": False},
            {"status": "censored_high", "value": None, "bound": float("nan")},
            {"status": "invented", "value": None, "bound": None},
            {"status": "missing", "value": None},
        )
        for target in targets:
            with self.subTest(target=target), self.assertRaises(ValueError):
                summary([dict(trace(60 * MINUTE), target=target)])

    def test_study_rejects_forged_eligibility_and_count_or_metric_corruption(self):
        replacements = (
            {"execution_status": "failed"},
            {"execution_status": "started"},
            {"eligible_for_primary": 1},
            {"eligible_for_primary": False},
            {"planned": True},
            {"not_attempted": 1},
            {"scored": 288},
            {"metric": "external-cgm-forecast/1"},
        )
        for replacement in replacements:
            with self.subTest(replacement=replacement), self.assertRaises(ValueError):
                summarize_study({"person": dict(qualified(), **replacement)})
        for method in ("candidate", "persistence"):
            for value in (None, True, float("nan"), -1):
                case = copy.deepcopy(qualified())
                case[method]["mae"] = value
                with self.subTest(method=method, value=value), self.assertRaises(ValueError):
                    summarize_study({"person": case})
        for cases in ({}, {" ": qualified()}, {1: qualified()}, {"person": {}}):
            with self.subTest(cases=cases), self.assertRaises(ValueError):
                summarize_study(cases)

    def test_metrics_import_without_site_packages_never_loads_model_runtime(self):
        command = (
            "import sys; import experiments.m3.researcher.metrics; "
            "assert 'experiments.m3.estimator' not in sys.modules; "
            "assert 'sklearn' not in sys.modules; assert 'numpy' not in sys.modules"
        )
        subprocess.run([sys.executable, "-S", "-c", command], check=True)
        self.assertEqual(METRIC, "researcher-cgm-forecast/1")


if __name__ == "__main__":
    unittest.main()
