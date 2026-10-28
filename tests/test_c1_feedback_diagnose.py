"""Hand-counted interval and command diagnostics for C1/0.8."""

import unittest

from experiments.c1.feedback_diagnose import action_summary, threshold_flow


class FeedbackDiagnoseTest(unittest.TestCase):
    def test_threshold_flow_keeps_both_sides_and_exact_interval_clock(self):
        base = [
            {"start_min": 0, "end_min": 3, "glucose_mg_dl": 65},
            {"start_min": 3, "end_min": 6, "glucose_mg_dl": 190},
            {"start_min": 6, "end_min": 9, "glucose_mg_dl": 100},
            {"start_min": 9, "end_min": 12, "glucose_mg_dl": 100},
        ]
        other = [
            {"start_min": 0, "end_min": 3, "glucose_mg_dl": 75},
            {"start_min": 3, "end_min": 6, "glucose_mg_dl": 175},
            {"start_min": 6, "end_min": 9, "glucose_mg_dl": 65},
            {"start_min": 9, "end_min": 12, "glucose_mg_dl": 181},
        ]
        result = threshold_flow(base, other)
        self.assertEqual(result["gained_in_from_below_70"], 1)
        self.assertEqual(result["gained_in_from_above_180"], 1)
        self.assertEqual(result["lost_in_to_below_70"], 1)
        self.assertEqual(result["lost_in_to_above_180"], 1)
        self.assertEqual(result["net_in_intervals"], 0)
        self.assertEqual((result["first_gain_start_min"], result["first_loss_start_min"]), (0, 6))
        with self.assertRaises(ValueError):
            threshold_flow(base, [dict(other[0], end_min=4), *other[1:]])

    def test_action_totals_use_three_minute_rates(self):
        commands = [
            {
                "time_min": 1440,
                "correction_u_h": -2,
                "rise_mg_dl_min": 0,
                "reason": "fresh_feedback",
                "total_clamped": False,
                "slew_limited": False,
                "integral_frozen": False,
                "final_basal_u_h": 1,
            },
            {
                "time_min": 1443,
                "correction_u_h": 1,
                "rise_mg_dl_min": 2,
                "reason": "fresh_feedback",
                "total_clamped": True,
                "slew_limited": False,
                "integral_frozen": True,
                "final_basal_u_h": 2,
            },
        ]
        result = action_summary(commands)
        self.assertEqual(result["net_commanded_correction_u"], -0.05)
        self.assertEqual(result["first_positive_correction_min"], 1443)
        self.assertEqual(result["rise_active_intervals"], 1)
        self.assertEqual(result["total_clamped_intervals"], 1)
        self.assertEqual(result["integral_frozen_intervals"], 1)
        with self.assertRaises(ValueError):
            action_summary([dict(commands[0], time_min=1441)])


if __name__ == "__main__":
    unittest.main()
