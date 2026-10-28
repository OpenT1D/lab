"""Independent units, shape, causality and basal normalization checks."""

import math
import unittest

from experiments.m4.causal_secretion.example_model import evaluate as delayed_source
from experiments.m4.ultradian_secretion.model import evaluate, response
from experiments.m4.ultradian_secretion.verify import published_rate, verify


class UltradianEquationTests(unittest.TestCase):
    def setUp(self):
        self.params = {"a1": 6.6, "C1_mg_l": 300.0}

    def rate(self, glucose, slope=0, state=0.8, time=0, basal=0.8):
        return evaluate(time, glucose, slope, state, basal, 138.56, self.params)

    def test_published_amount_equation_and_mg_dl_conversion(self):
        # At 198 mg/dL, Gamount/(Vg*C1)=6.6 and published f1=Rm/2.
        self.assertEqual(published_rate(198), 104.5)
        self.assertEqual(response(198, 6.6, 300), 0.5)
        check = verify()
        self.assertTrue(check["passed"])
        self.assertLess(check["max_rate_error_pmol_kg_min"], 1e-12)

    def test_exact_basal_zero_capacity_and_unused_state(self):
        for time in (240, 4, 0, 120, 4):
            self.assertEqual(self.rate(138.56, time=time), [0, 0.8])
        for glucose in (0, 50, 198, 600):
            self.assertEqual(self.rate(glucose, basal=0), [0, 0])
            self.assertEqual(self.rate(glucose, state=100), self.rate(glucose, state=0))

    def test_memoryless_response_is_distinct_from_delayed_positive_slope_law(self):
        for slope in (-5, 0, 5):
            self.assertEqual(self.rate(180, slope), self.rate(180))
        original_params = {
            "alpha_per_min": 0.05,
            "beta_pmol_kg_min_per_mg_dl": 0.11,
            "K_pmol_kg_per_mg_dl": 2.3,
        }
        self.assertNotEqual(
            delayed_source(0, 138.56, 1, 0.8, 0.8, 138.56, original_params),
            self.rate(138.56, 1),
        )

    def test_inflection_slope_saturation_and_low_branch_are_not_clamped(self):
        epsilon = 1e-3
        slope = (response(198 + epsilon, 6.6, 300) - response(198 - epsilon, 6.6, 300)) / (
            2 * epsilon
        )
        self.assertAlmostEqual(slope, 1 / 120, places=11)
        values = [response(g, 6.6, 300) for g in (0, 30, 100, 198, 300, 600, 100000)]
        self.assertEqual(values, sorted(values))
        self.assertGreater(values[0], 0)
        self.assertEqual(values[-1], 1)
        self.assertLess(self.rate(30)[1], 0.8)

    def test_nonfinite_negative_and_invalid_units_domain_rejected(self):
        for glucose in (-1, math.inf, math.nan, True):
            with self.subTest(glucose=glucose), self.assertRaises(ValueError):
                self.rate(glucose)
        for a1, c1 in ((math.nan, 300), (6.6, 0), (6.6, -300), (51, 300), (True, 300)):
            with self.subTest(a1=a1, c1=c1), self.assertRaises(ValueError):
                response(100, a1, c1)
        for basal, threshold in ((-1, 100), (0.8, 0), (math.nan, 100), (True, 100)):
            with self.subTest(basal=basal, threshold=threshold), self.assertRaises(ValueError):
                evaluate(0, 100, 0, 0.8, basal, threshold, self.params)


if __name__ == "__main__":
    unittest.main()
