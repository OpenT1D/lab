"""Causal and bound checks for the unconfigured C1 overlay."""

import unittest

from experiments.c1.core import Settings, TrendOverlay


def settings():
    # Invented arithmetic fixture, not selected gains or a patient profile.
    return Settings(140, 90, 1, 10, 10, 60, 1, 3, 0.5, 4)


class TrendOverlayTest(unittest.TestCase):
    def test_fresh_rise_is_bounded_and_missing_sensor_removes_extra(self):
        policy = TrendOverlay(settings())
        first = policy.command(
            time_min=0, glucose_mg_dl=140, source_time_min=0, available=True, base_u_h=1
        )
        rise = policy.command(
            time_min=5, glucose_mg_dl=180, source_time_min=5, available=True, base_u_h=1
        )
        held = policy.command(
            time_min=10, glucose_mg_dl=180, source_time_min=5, available=False, base_u_h=1
        )
        after_gap = policy.command(
            time_min=40, glucose_mg_dl=190, source_time_min=40, available=True, base_u_h=1
        )
        self.assertEqual(
            (first.extra_u_h, rise.extra_u_h, held.extra_u_h, after_gap.extra_u_h), (0, 0.5, 0, 0)
        )
        self.assertEqual(held.reason, "held_observation")
        self.assertGreater(after_gap.inventory_u, 0)

    def test_low_gate_and_reset(self):
        policy = TrendOverlay(settings())
        policy.command(time_min=0, glucose_mg_dl=130, source_time_min=0, available=True, base_u_h=1)
        low = policy.command(
            time_min=5, glucose_mg_dl=85, source_time_min=5, available=True, base_u_h=1
        )
        self.assertEqual((low.final_u_h, low.reason), (1, "low_glucose_gate"))
        policy.reset()
        first = policy.command(
            time_min=0, glucose_mg_dl=130, source_time_min=0, available=True, base_u_h=1
        )
        self.assertEqual((first.inventory_u, first.extra_u_h), (0, 0))

    def test_rejects_leakage_and_invalid_actions_without_advancing_clock(self):
        policy = TrendOverlay(settings())
        with self.assertRaises(ValueError):
            policy.command(
                time_min=0, glucose_mg_dl=140, source_time_min=1, available=True, base_u_h=1
            )
        with self.assertRaises(ValueError):
            policy.command(
                time_min=0, glucose_mg_dl=140, source_time_min=0, available=True, base_u_h=5
            )
        policy.command(time_min=0, glucose_mg_dl=140, source_time_min=0, available=True, base_u_h=1)
        with self.assertRaises(ValueError):
            policy.command(
                time_min=5, glucose_mg_dl=150, source_time_min=0, available=False, base_u_h=1
            )
        self.assertEqual(
            policy.command(
                time_min=5, glucose_mg_dl=150, source_time_min=5, available=True, base_u_h=1
            ).reason,
            "bounded_rise",
        )
        with self.assertRaises(ValueError):
            policy.command(
                time_min=5, glucose_mg_dl=160, source_time_min=5, available=True, base_u_h=1
            )

    def test_unconfigured_or_invalid_parameters_rejected(self):
        with self.assertRaises(TypeError):
            TrendOverlay(None)
        with self.assertRaises(ValueError):
            Settings(90, 90, 1, 10, 10, 60, 1, 3, 0.5, 4)
        with self.assertRaises(ValueError):
            Settings(140, 90, float("nan"), 10, 10, 60, 1, 3, 0.5, 4)


if __name__ == "__main__":
    unittest.main()
