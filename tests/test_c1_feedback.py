"""Hand-computed arithmetic checks for the unconfigured C1/0.6 kernel."""

import unittest
from dataclasses import replace

from experiments.c1.feedback import FeedbackController, FeedbackSettings, without_rise


def settings(**changes):
    # Invented engineering fixtures, never a selected or patient-specific setting.
    return replace(FeedbackSettings(100, 80, 0.02, 0.001, 0.1, 5, 10, 100, 0.5, 2), **changes)


def step(policy, time, glucose, *, base=1, source=None, available=True):
    return policy.command(
        time_min=time,
        glucose_mg_dl=glucose,
        source_time_min=time if source is None else source,
        available=available,
        base_u_h=base,
    )


class FeedbackKernelTest(unittest.TestCase):
    def test_matched_comparator_differs_only_on_fresh_rise(self):
        candidate = FeedbackController(settings())
        comparator = FeedbackController(without_rise(settings()))
        self.assertEqual(
            candidate.settings, replace(comparator.settings, rise_gain_u_h_per_mg_dl_min=0.1)
        )
        self.assertEqual(step(candidate, 0, 100), step(comparator, 0, 100))
        up = step(candidate, 5, 110)
        no_rise = step(comparator, 5, 110)
        self.assertAlmostEqual(up.rise_mg_dl_min, 2)
        self.assertAlmostEqual(up.final_u_h, 1.45)
        self.assertAlmostEqual(no_rise.final_u_h, 1.25)
        self.assertEqual(up.integral_mg_dl_min, no_rise.integral_mg_dl_min)
        self.assertEqual(step(candidate, 10, 110).final_u_h, step(comparator, 10, 110).final_u_h)

    def test_two_sided_rate_and_native_base_with_zero_gains(self):
        policy = FeedbackController(settings(ki_u_h_per_mg_dl_min=0, rise_gain_u_h_per_mg_dl_min=0))
        self.assertAlmostEqual(step(policy, 0, 90).final_u_h, 0.8)
        self.assertAlmostEqual(step(policy, 5, 110).final_u_h, 1.2)
        zero = FeedbackController(
            settings(
                kp_u_h_per_mg_dl=0,
                ki_u_h_per_mg_dl_min=0,
                rise_gain_u_h_per_mg_dl_min=0,
            )
        )
        self.assertEqual(step(zero, 0, 100, base=1).final_u_h, 1)
        self.assertEqual(step(zero, 5, 150, base=1.8).final_u_h, 1.8)
        self.assertEqual(step(zero, 10, 50, base=0.2).final_u_h, 0.2)

    def test_low_gate_clears_positive_integral_and_allows_downward_action(self):
        policy = FeedbackController(settings(rise_gain_u_h_per_mg_dl_min=0))
        step(policy, 0, 100)
        high = step(policy, 5, 101)
        self.assertEqual(high.integral_mg_dl_min, 5)
        low = step(policy, 10, 75)
        self.assertEqual(low.reason, "fresh_low_gate")
        self.assertLess(low.final_u_h, low.base_u_h)
        self.assertLessEqual(low.correction_u_h, 0)
        self.assertLess(low.integral_mg_dl_min, 0)

        rising_low = FeedbackController(
            settings(
                kp_u_h_per_mg_dl=0,
                ki_u_h_per_mg_dl_min=0,
                rise_gain_u_h_per_mg_dl_min=1,
            )
        )
        step(rising_low, 0, 60)
        gated = step(rising_low, 5, 80)
        self.assertEqual(gated.rise_mg_dl_min, 4)
        self.assertEqual(gated.final_u_h, gated.base_u_h)

    def test_upper_lower_and_upward_slew_freeze_integral(self):
        upper = FeedbackController(
            settings(
                kp_u_h_per_mg_dl=0.06,
                ki_u_h_per_mg_dl_min=0.01,
                rise_gain_u_h_per_mg_dl_min=0,
                max_up_correction_step_u_h=2,
            )
        )
        step(upper, 0, 100)
        high = step(upper, 1, 120)
        self.assertEqual((high.integral_mg_dl_min, high.final_u_h), (0, 2))
        self.assertTrue(high.integral_frozen)
        self.assertTrue(high.total_clamped)
        self.assertGreater(high.raw_total_u_h, 2)

        lower = FeedbackController(
            settings(
                kp_u_h_per_mg_dl=0.06,
                ki_u_h_per_mg_dl_min=0.01,
                rise_gain_u_h_per_mg_dl_min=0,
                max_up_correction_step_u_h=2,
            )
        )
        step(lower, 0, 100)
        low = step(lower, 1, 70)
        self.assertEqual((low.integral_mg_dl_min, low.final_u_h), (0, 0))
        self.assertTrue(low.integral_frozen)
        self.assertTrue(low.total_clamped)
        self.assertLess(low.raw_total_u_h, 0)

        slew = FeedbackController(
            settings(
                kp_u_h_per_mg_dl=0.04,
                ki_u_h_per_mg_dl_min=0.01,
                rise_gain_u_h_per_mg_dl_min=0,
                max_up_correction_step_u_h=0.2,
            )
        )
        step(slew, 0, 100)
        limited = step(slew, 1, 110)
        self.assertAlmostEqual(limited.final_u_h, 1.2)
        self.assertEqual(limited.integral_mg_dl_min, 0)
        self.assertTrue(limited.integral_frozen)
        self.assertTrue(limited.slew_limited)

    def test_opposing_error_unwinds_integral(self):
        policy = FeedbackController(
            settings(
                kp_u_h_per_mg_dl=0,
                ki_u_h_per_mg_dl_min=0.01,
                rise_gain_u_h_per_mg_dl_min=0,
                max_up_correction_step_u_h=2,
            )
        )
        step(policy, 0, 100)
        self.assertEqual(step(policy, 1, 110).integral_mg_dl_min, 10)
        unwound = step(policy, 2, 95)
        self.assertEqual(unwound.integral_mg_dl_min, 5)
        self.assertFalse(unwound.integral_frozen)
        self.assertAlmostEqual(unwound.final_u_h, 1.05)

    def test_held_fallback_then_fresh_uses_only_current_interval(self):
        policy = FeedbackController(settings(rise_gain_u_h_per_mg_dl_min=0))
        step(policy, 0, 100)
        prior = step(policy, 5, 110)
        held = step(policy, 10, 110, base=1.5, source=5, available=False)
        self.assertEqual((held.final_u_h, held.correction_u_h), (1.5, 0))
        self.assertFalse(held.total_clamped or held.slew_limited)
        self.assertEqual(held.integral_mg_dl_min, prior.integral_mg_dl_min)
        fresh = step(policy, 15, 110)
        self.assertEqual(fresh.integral_mg_dl_min, 100)
        self.assertEqual(fresh.rise_mg_dl_min, 0)

    def test_long_gap_skips_integration_and_trend(self):
        policy = FeedbackController(settings())
        step(policy, 0, 100)
        late = step(policy, 20, 110)
        self.assertEqual((late.integral_mg_dl_min, late.rise_mg_dl_min), (0, 0))

    def test_reset_repeats_and_invalid_inputs_do_not_advance_state(self):
        policy = FeedbackController(settings())
        first = step(policy, 0, 100)
        with self.assertRaises(ValueError):
            step(policy, 5, 110, source=4, available=True)
        with self.assertRaises(ValueError):
            step(policy, 5, 110, source=0, available=False)
        with self.assertRaises(ValueError):
            step(policy, 5, float("nan"))
        with self.assertRaises(ValueError):
            step(policy, 5, 110, base=3)
        with self.assertRaises(ValueError):
            step(policy, 5, 110, source=6)
        good = step(policy, 5, 110)
        self.assertAlmostEqual(good.final_u_h, 1.45)
        with self.assertRaises(ValueError):
            step(policy, 5, 110)
        policy.reset()
        self.assertEqual(step(policy, 0, 100), first)
        self.assertEqual(step(policy, 5, 110), good)

    def test_invalid_settings_and_overflow_leave_state_unchanged(self):
        with self.assertRaises(TypeError):
            FeedbackController(None)
        with self.assertRaises(ValueError):
            settings(target_mg_dl=80)
        with self.assertRaises(ValueError):
            settings(ki_u_h_per_mg_dl_min=float("inf"))
        policy = FeedbackController(settings(kp_u_h_per_mg_dl=1e308))
        step(policy, 0, 100)
        with self.assertRaises(ValueError):
            step(policy, 1, 200)
        self.assertEqual(step(policy, 2, 100).integral_mg_dl_min, 0)


if __name__ == "__main__":
    unittest.main()
