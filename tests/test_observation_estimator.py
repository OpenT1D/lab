"""Independent balance, integration, dimension and boundary controls for OT-054."""

import decimal
import math
import unittest

from experiments.observation_analysis.estimator import (
    estimate,
    exponential_integrals,
    interval,
)
from experiments.observation_analysis.fixtures import analysis_settings


class ObservationEstimatorTests(unittest.TestCase):
    def test_whole_body_equilibrium_and_nonzero_initial_inventory(self):
        variant = analysis_settings()["variants"][0]
        result = estimate([0, 15, 30, 60, 90, 120], [200] * 6, variant)
        self.assertEqual(result["status"], "completed")
        self.assertAlmostEqual(result["total_pmol"], 5722.08, delta=1e-8)
        self.assertAlmostEqual(result["minimum_rate_pmol_min"], 47.684, delta=1e-11)
        self.assertGreater(result["initial_peripheral_pmol"], 0)
        self.assertAlmostEqual(
            result["initial_peripheral_pmol"], result["final_peripheral_pmol"], delta=1e-10
        )

    def test_separate_rk4_peripheral_and_secretion_integral(self):
        # The oracle integrates ODEs; it does not call the exact interval formulas.
        variant = {**analysis_settings()["variants"][0], "initial_peripheral_factor": 0.75}
        times, cp = [0, 15, 30, 60, 90, 120], [200, 260, 350, 400, 330, 300]
        result = estimate(times, cp, variant)
        a, b, d, v = (
            variant[key] for key in ("k1_per_min", "k2_per_min", "k3_per_min", "volume_l")
        )
        peripheral, total = variant["initial_peripheral_factor"] * a / b * v * cp[0], 0
        for i, (start, end) in enumerate(zip(times, times[1:])):
            slope = (cp[i + 1] - cp[i]) / (end - start)
            count = math.ceil((end - start) / 0.01)
            step = (end - start) / count

            def rhs(t, state):
                c = cp[i] + slope * t
                return a * v * c - b * state, v * slope + (a + d) * v * c - b * state

            for j in range(count):
                t = j * step
                k1, q1 = rhs(t, peripheral)
                k2, q2 = rhs(t + step / 2, peripheral + step * k1 / 2)
                k3, q3 = rhs(t + step / 2, peripheral + step * k2 / 2)
                k4, q4 = rhs(t + step, peripheral + step * k3)
                peripheral += step * (k1 + 2 * k2 + 2 * k3 + k4) / 6
                total += step * (q1 + 2 * q2 + 2 * q3 + q4) / 6
        self.assertAlmostEqual(total, result["total_pmol"], delta=1e-5)
        self.assertAlmostEqual(peripheral, result["final_peripheral_pmol"], delta=1e-5)

    def test_small_interval_series_against_high_precision_decimal(self):
        with decimal.localcontext() as context:
            context.prec = 70
            for width in (1e-9, 1e-6, 0.001, 0.01):
                b, h = decimal.Decimal("0.031"), decimal.Decimal(str(width))
                u = (1 - (-b * h).exp()) / b
                w = (h - u) / b
                actual_u, actual_w = exponential_integrals(float(b), float(h))
                self.assertLess(abs(actual_u / float(u) - 1), 1e-10)
                self.assertLess(abs(actual_w / float(w) - 1), 1e-10)

    def test_concentration_volume_and_time_unit_covariance(self):
        variant = analysis_settings()["variants"][0]
        reference = estimate([0, 30, 120], [200, 300, 250], variant)
        scaled = estimate(
            [0, 30, 120], [2000, 3000, 2500], {**variant, "volume_l": variant["volume_l"] / 10}
        )
        self.assertLess(abs(scaled["total_pmol"] / reference["total_pmol"] - 1), 1e-11)
        p0 = variant["k1_per_min"] / variant["k2_per_min"] * variant["volume_l"] * 200
        minutes = interval(200, 300, 120, p0, variant)
        seconds = interval(
            200,
            300,
            7200,
            p0,
            {
                **variant,
                **{key: variant[key] / 60 for key in ("k1_per_min", "k2_per_min", "k3_per_min")},
            },
        )
        self.assertLess(abs(seconds["secretion_pmol"] / minutes["secretion_pmol"] - 1), 1e-11)
        with self.assertRaisesRegex(ValueError, "120"):
            estimate([0, 7200], [200, 300], variant)  # Public contract never guesses seconds.

    def test_negative_secretion_is_retained_and_continuous_minimum_is_checked(self):
        variant = analysis_settings()["variants"][0]
        result = estimate([0, 1, 120], [200, 0, 0], variant)
        self.assertEqual(result["status"], "boundary_failed")
        self.assertLess(result["intervals"][0]["secretion_pmol"], 0)
        self.assertLess(result["minimum_rate_pmol_min"], 0)
        stress = {**variant, "initial_peripheral_factor": 0.5}
        p0 = 0.5 * variant["k1_per_min"] / variant["k2_per_min"] * variant["volume_l"] * 200
        segment = interval(200, 250, 120, p0, stress)
        self.assertGreater(segment["minimum_time_in_interval_min"], 0)
        self.assertLess(segment["minimum_time_in_interval_min"], 120)
        self.assertLess(segment["minimum_rate_pmol_min"], segment["start_rate_pmol_min"])
        self.assertLess(segment["minimum_rate_pmol_min"], segment["end_rate_pmol_min"])

    def test_invalid_kinetics_and_observations_refused(self):
        variant = analysis_settings()["variants"][0]
        for key, value in (("volume_l", 0), ("k2_per_min", -1), ("k3_per_min", float("nan"))):
            with self.subTest(key=key), self.assertRaises(ValueError):
                estimate([0, 120], [200, 200], {**variant, key: value})
        for times, cp in (
            ([0, 0, 120], [1, 1, 1]),
            ([1, 120], [1, 1]),
            ([0, 120], [True, 1]),
            ([0, 120], [-1, 1]),
        ):
            with self.assertRaises(ValueError):
                estimate(times, cp, variant)


if __name__ == "__main__":
    unittest.main()
