"""Independent arithmetic and missing/failure-denominator checks for Task 2."""

import math
import unittest

from experiments.mmtt_sampling.comparison import direction_comparison, endpoint_comparison


class SamplingComparisonTests(unittest.TestCase):
    def test_signed_absolute_bias_precision_and_all_planned_pairs(self):
        result = endpoint_comparison(
            [(10, 12), (20, 18), (30, None), (None, 40), (50, None), (None, None)]
        )
        self.assertEqual(result["planned_count"], 6)
        self.assertEqual(result["compared_count"], 2)
        self.assertEqual(result["reference_unavailable_count"], 2)
        self.assertEqual(result["reduced_unavailable_count"], 3)
        self.assertEqual(result["both_unavailable_count"], 1)
        self.assertEqual(result["bias_pmol"], 0)
        self.assertEqual(result["mean_absolute_difference_pmol"], 2)
        self.assertEqual(result["median_absolute_difference_pmol"], 2)
        self.assertEqual(result["maximum_absolute_difference_pmol"], 2)
        self.assertAlmostEqual(result["root_mean_square_difference_pmol"], 2, places=12)
        self.assertAlmostEqual(result["precision_sample_sd_pmol"], math.sqrt(8))
        self.assertEqual(
            [r["difference_pmol"] for r in result["rows"]], [2, -2, None, None, None, None]
        )

    def test_one_pair_has_no_precision_estimate_and_no_pairs_is_not_zero_error(self):
        result = endpoint_comparison([(0, 3)])
        self.assertEqual(result["bias_pmol"], 3)
        self.assertIsNone(result["precision_sample_sd_pmol"])
        result = endpoint_comparison([(None, None), (10, None)])
        self.assertEqual(result["planned_count"], 2)
        self.assertEqual(result["compared_count"], 0)
        for field in (
            "bias_pmol",
            "mean_absolute_difference_pmol",
            "precision_sample_sd_pmol",
            "root_mean_square_difference_pmol",
        ):
            self.assertIsNone(result[field])

    def test_zero_reference_and_negative_paired_change_use_absolute_units(self):
        result = endpoint_comparison([(0, 5), (-10, -7), (3, 1)])
        self.assertEqual([r["difference_pmol"] for r in result["rows"]], [5, 3, -2])
        self.assertEqual(result["bias_pmol"], 2)
        self.assertEqual(result["mean_absolute_difference_pmol"], 10 / 3)
        self.assertAlmostEqual(result["root_mean_square_difference_pmol"], math.sqrt(38 / 3))

    def test_large_finite_differences_do_not_overflow_rms_or_median(self):
        result = endpoint_comparison([(0, 1e308)] * 4)
        self.assertEqual(result["root_mean_square_difference_pmol"], 1e308)
        self.assertEqual(result["median_absolute_difference_pmol"], 1e308)
        self.assertEqual(result["precision_sample_sd_pmol"], 0)

    def test_rejects_nonfinite_boolean_and_incomplete_pair_without_silent_exclusion(self):
        for pair in (
            (1, float("nan")),
            (True, 1),
            (1, float("inf")),
            (1, 10**400),
            (1,),
            (-1e308, 1e308),
        ):
            with self.subTest(pair=pair), self.assertRaises(ValueError):
                endpoint_comparison([(1, 2), pair])

        with self.assertRaises(ValueError):
            endpoint_comparison([(0, -1.7e308), (0, 1.7e308)])

    def test_resolved_directions_reversals_and_indeterminate_agreement(self):
        result = direction_comparison(
            [
                ("increase", "increase"),
                ("decrease", "decrease"),
                ("increase", "decrease"),
                ("decrease", "increase"),
                ("unresolved", "unresolved"),
                ("increase", "unresolved"),
                (None, "increase"),
                (None, None),
            ]
        )
        self.assertEqual(result["planned_count"], 8)
        self.assertEqual(result["same_resolved_direction"], 2)
        self.assertEqual(result["direction_reversal"], 2)
        self.assertEqual(result["indeterminate"], 2)
        self.assertEqual(result["unavailable"], 2)
        self.assertEqual(len(result["rows"]), 8)
        with self.assertRaises(ValueError):
            direction_comparison([("no-change", "increase")])


if __name__ == "__main__":
    unittest.main()
