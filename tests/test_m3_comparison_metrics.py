"""Independent synthetic common-support arithmetic and eligibility boundaries."""

import copy
import unittest

from experiments.m3.azt1d.common import MINUTE
from experiments.m3.comparison.analysis import summarize_common


def rows(origins, prediction=102, *, target=100, persistence=100):
    return [
        {
            "origin_us": origin,
            "features": [persistence] * 6,
            "reason": None,
            "candidate": prediction,
            "persistence": persistence,
            "target": {"status": "measured", "value": target, "bound": None},
        }
        for origin in origins
    ]


def example(origins, *, order=("left", "right"), statuses=None, counts=None):
    person = {"id": "person", "origins_us": origins, "bounds_us": [0, origins[-1] + 60 * MINUTE]}
    cases = {
        candidate: {
            "person": {
                "status": "completed" if statuses is None else statuses[candidate],
                "rows": rows(
                    origins if counts is None else origins[: counts[candidate]], 102 + index * 3
                ),
            }
        }
        for index, candidate in enumerate(order)
    }
    return [person], list(order), cases


class ComparisonMetricTests(unittest.TestCase):
    def test_equal_person_weighting_and_direct_sign_use_same_origins(self):
        people, cases = [], {"left": {}, "right": {}}
        for pid, count, lhs, rhs in (("short", 289, 101, 103), ("long", 578, 109, 104)):
            origins = [(60 + index * 5) * MINUTE for index in range(count)]
            people.append(
                {"id": pid, "origins_us": origins, "bounds_us": [0, origins[-1] + 60 * MINUTE]}
            )
            cases["left"][pid] = {"status": "completed", "rows": rows(origins, lhs)}
            cases["right"][pid] = {"status": "completed", "rows": rows(origins, rhs)}
        report = summarize_common(people, ["left", "right"], cases)
        self.assertTrue(report["complete_cohort"])
        self.assertEqual(report["equal_person_metrics"]["left"]["mae"], 5)
        self.assertEqual(report["equal_person_metrics"]["right"]["mae"], 3.5)
        direct = report["contrasts"][-1]
        self.assertEqual(direct["person_differences"], {"long": 5, "short": -2})
        self.assertEqual(direct["mean_person_mae_difference"], 1.5)
        self.assertEqual(direct["participant_bootstrap_95"], [-2, 5])
        self.assertEqual(report["contrasts"][0]["participant_bootstrap_95"], [1, 9])

    def test_independent_count_and_span_boundary_conjunction(self):
        for count, final_minute, eligible in (
            (287, 1500, False),
            (288, 1495, False),
            (288, 1500, True),
            (289, 1500, True),
        ):
            origins = [(60 + index * 5) * MINUTE for index in range(count - 1)]
            origins.append(final_minute * MINUTE)
            with self.subTest(count=count, final_minute=final_minute):
                report = summarize_common(*example(origins))
                case = report["people"]["person"]
                self.assertEqual(case["common_scored"], count)
                self.assertEqual(case["eligible_for_primary"], eligible)
                if eligible:
                    self.assertEqual(report["contributing_people"], 1)
                    self.assertIsNone(report["contrasts"][0]["participant_bootstrap_95"])
                else:
                    self.assertIsNone(report["contrasts"][0]["mean_person_mae_difference"])
                    self.assertIsNotNone(report["null_reason"])

    def test_long_failed_prefix_is_diagnostic_and_never_eligible(self):
        origins = [(60 + index * 5) * MINUTE for index in range(500)]
        people, order, cases = example(
            origins,
            statuses={"left": "completed", "right": "failed"},
            counts={"left": 500, "right": 450},
        )
        report = summarize_common(people, order, cases)
        case = report["people"]["person"]
        self.assertEqual(case["common_scored"], 450)
        self.assertGreater(case["common_span_us"], 1440 * MINUTE)
        self.assertEqual(case["ineligibility_reasons"], ["incomplete_candidate:right"])
        self.assertEqual(case["common_support_losses"], {"left": 50, "right": 0})
        self.assertEqual(report["contributing_people"], 0)
        self.assertFalse(report["complete_cohort"])
        self.assertIsNone(report["equal_person_metrics"]["left"]["mae"])

    def test_partial_cohort_excludes_long_failed_person_from_primary_arithmetic(self):
        people, cases = [], {"left": {}, "right": {}}
        for pid, count, left, right, status in (
            ("eligible", 289, 102, 105, "completed"),
            ("failed", 500, 900, 101, "failed"),
        ):
            origins = [(60 + index * 5) * MINUTE for index in range(count)]
            people.append(
                {"id": pid, "origins_us": origins, "bounds_us": [0, origins[-1] + 60 * MINUTE]}
            )
            cases["left"][pid] = {"status": "completed", "rows": rows(origins, left)}
            cases["right"][pid] = {
                "status": status,
                "rows": rows(origins if status == "completed" else origins[:450], right),
            }
        report = summarize_common(people, ["left", "right"], cases)
        self.assertEqual(report["planned_people"], 2)
        self.assertEqual(report["contributing_people"], 1)
        self.assertFalse(report["complete_cohort"])
        self.assertEqual(report["people"]["failed"]["common_scored"], 450)
        self.assertGreater(report["people"]["failed"]["common_span_us"], 1440 * MINUTE)
        self.assertEqual(report["equal_person_metrics"]["left"]["mae"], 2)
        self.assertEqual(report["equal_person_metrics"]["right"]["mae"], 5)
        self.assertEqual(report["contrasts"][-1]["person_differences"], {"eligible": -3})
        self.assertEqual(report["contrasts"][-1]["mean_person_mae_difference"], -3)
        self.assertIsNone(report["contrasts"][-1]["participant_bootstrap_95"])

    def test_unattempted_frozen_candidate_cannot_be_dropped_to_rescue_score(self):
        origins = [(60 + index * 5) * MINUTE for index in range(289)]
        people, order, cases = example(
            origins,
            statuses={"left": "completed", "right": "not_attempted"},
            counts={"left": 289, "right": 0},
        )
        report = summarize_common(people, order, cases)
        self.assertEqual(report["people"]["person"]["common_scored"], 0)
        self.assertEqual(report["people"]["person"]["planned_origins"], 289)
        self.assertIsNone(report["equal_person_metrics"]["persistence"]["mae"])
        with self.assertRaises(ValueError):
            summarize_common(people, order, {"left": cases["left"]})

    def test_legal_candidate_names_cannot_overwrite_target_or_origin(self):
        origins = [(60 + index * 5) * MINUTE for index in range(289)]
        report = summarize_common(*example(origins, order=("target", "origin")))
        self.assertEqual(report["equal_person_metrics"]["target"]["mae"], 2)
        self.assertEqual(report["equal_person_metrics"]["origin"]["mae"], 5)
        self.assertEqual(report["contrasts"][-1]["mean_person_mae_difference"], -3)

    def test_successful_omission_and_shared_host_mismatch_are_rejected(self):
        origins = [(60 + index * 5) * MINUTE for index in range(289)]
        people, order, cases = example(origins)
        omitted = copy.deepcopy(cases)
        omitted["right"]["person"]["rows"].pop()
        with self.assertRaises(ValueError):
            summarize_common(people, order, omitted)
        for field in ("features", "target"):
            changed = copy.deepcopy(cases)
            if field == "features":
                changed["right"]["person"]["rows"][0]["features"][0] += 1
            else:
                changed["right"]["person"]["rows"][0]["target"]["value"] += 1
            with self.subTest(field=field), self.assertRaises(ValueError):
                summarize_common(people, order, changed)


if __name__ == "__main__":
    unittest.main()
