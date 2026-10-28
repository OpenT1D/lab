"""IV-001 one-factor intent, masking and honest paired-comparison checks."""

import copy
import unittest

from experiments.verification.analysis import validate_trace
from experiments.verification.common import configurations, meals, validate
from experiments.verification.conditions import announcements, available
from experiments.verification.robustness import comparisons, schedule


def cfg(variant):
    return configurations()[0] | dict(schema="iv001.robust-case/1", variant=variant)


class RobustnessTests(unittest.TestCase):
    def test_frozen_one_factor_count_and_rejections(self):
        cases = schedule()
        self.assertEqual(len(cases), 170)
        self.assertEqual(len({c["id"] for c in cases}), 170)
        self.assertEqual(
            {c["config"]["profile"] for c in cases}, {"adult#001", "adult#002", "reference"}
        )
        for change in (
            {"variant": "unknown"},
            {"factor": 10},
            {"factor": True},
            {"mode": "replay"},
            {"warmup": 0},
            {"variant": None},
            {"profile": "adult#003"},
        ):
            with self.assertRaises(ValueError):
                validate(cfg("baseline") | change)

    def test_truthful_amount_timing_and_delayed_information(self):
        self.assertEqual(dict(meals(cfg("meal-half")))[1860], 22.5)
        self.assertEqual(dict(meals(cfg("meal-half")))[420], 45)
        self.assertEqual(dict(meals(cfg("meal-one-half")))[1860], 67.5)
        self.assertIn((1830, 45), meals(cfg("meal-early")))
        self.assertNotIn((1860, 45), meals(cfg("meal-early")))
        late = cfg("announcement-late")
        self.assertIn((1875, 1860, 45), announcements(late, meals(late)))
        self.assertNotIn((1860, 1860, 45), announcements(late, meals(late)))
        self.assertIn((420, 420, 45), announcements(late, meals(late)))
        none = cfg("announcement-none")
        self.assertEqual(len(announcements(none, meals(none))), 5)
        self.assertEqual(meals(none), meals(cfg("baseline")))

    def test_gap_endpoints_and_hold_while_raw_values_continue(self):
        case = cfg("gap-15")
        self.assertTrue(available(case, 2157))
        self.assertFalse(available(case, 2160))
        self.assertFalse(available(case, 2172))
        self.assertTrue(available(case, 2175))
        rows = []
        held = (0, 100)
        for t in range(0, 2178, 3):
            end = t + 3
            visible = not 2160 <= end < 2175
            rows.append(
                dict(
                    start_min=t,
                    end_min=end,
                    glucose_mg_dl=100,
                    raw_cgm_mg_dl=100 + end,
                    sensor_available=visible,
                    controller_cgm_mg_dl=held[1],
                    controller_source_min=held[0],
                    announced_g=dict(meals(case)).get(t, 0),
                    true_meal_g=dict(meals(case)).get(t, 0),
                    basal_u_min=0,
                    bolus_u_min=0,
                    delivered_u_min=0,
                    terminal=False,
                )
            )
            if visible:
                held = (end, 100 + end)
        validate_trace(rows, case, {"cgm_mg_dl": 100})
        altered = copy.deepcopy(rows)
        altered[720]["controller_source_min"] = 2160
        altered[720]["controller_cgm_mg_dl"] = 2260
        with self.assertRaisesRegex(ValueError, "observation"):
            validate_trace(altered, case, {"cgm_mg_dl": 100})
        altered = copy.deepcopy(rows)
        altered[720]["raw_cgm_mg_dl"] = None
        with self.assertRaises(ValueError):
            validate_trace(altered, case, {"cgm_mg_dl": 100})

    def test_reversals_missing_pairs_ties_and_ranges(self):
        cases = []
        for c in schedule():
            index = int(c["id"][:2])
            variant = c["config"]["variant"]
            value = 100 + (10 if index % 2 else 0)
            if variant == "meal-half" and index % 2:
                value = 95
            cases.append(
                c
                | dict(
                    status="completed",
                    metrics=dict(
                        observed_minutes=1440, glucose={"mean_mg_dl": value}, delivered_insulin_u=1
                    ),
                )
            )
        result = comparisons(cases)
        pair = next(p for p in result["controller_pairs"] if p["first"] == "00-meal-half")
        self.assertEqual(pair["delta_second_minus_first"]["mean_mg_dl"], -5)
        self.assertEqual(pair["versus_baseline"]["mean_mg_dl"], "reversal")
        self.assertEqual(pair["versus_baseline"]["delivered_insulin_u"], "tie")
        cases[17]["status"] = "terminated"  # missing baseline for the first PID
        result = comparisons(cases)
        baseline = next(p for p in result["controller_pairs"] if p["first"] == "00-baseline")
        self.assertIsNone(baseline["delta_second_minus_first"])
        changed = next(p for p in result["controller_pairs"] if p["first"] == "00-meal-half")
        self.assertIsNone(changed["versus_baseline"])
        summary = next(
            p
            for p in result["development_ranges"]
            if p["engine"] == "simglucose" and p["variant"] == "baseline"
        )
        self.assertEqual(summary["planned_pairs"], 4)
        self.assertEqual(summary["complete_pairs"], 3)
