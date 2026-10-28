"""Numerical and scientific-convention checks for the bounded LIT-001 model."""

import json
import unittest
from pathlib import Path

import numpy as np
from model import Parameters, analytic, numerical
from scipy.linalg import expm


class ReferenceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        record = json.loads((Path(__file__).resolve().parents[1] / "parameters.json").read_text())
        cls.p = Parameters.from_record(record)

    def test_closed_form_against_independent_matrix_exponential(self):
        p = self.p
        matrix = np.array([[-(p.ka1 + p.kd), 0, 0], [p.kd, -p.ka2, 0], [p.ka1, p.ka2, -p.ke]])
        times = np.array([0, p.tau - 1e-6, p.tau, p.tau + 1, 30, 60, 100, 600])
        actual = analytic(times, 200, p)
        for i, t in enumerate(times):
            expected = expm(matrix * (t - p.tau)) @ [200, 0, 0] if t >= p.tau else [0, 0, 0]
            np.testing.assert_allclose(actual[i, :3], expected, atol=1e-11, rtol=1e-11)

    def test_delayed_event_and_complete_mass_accounting(self):
        p = self.p
        times = np.array([0, p.tau - 1e-8, p.tau, p.tau + 1e-8, 600])
        result = numerical(times, 200, p, method="DOP853", rtol=1e-10, atol=1e-12)
        np.testing.assert_array_equal(result[:2], 0)
        np.testing.assert_array_equal(result[2], [200, 0, 0, 0])
        pending = np.where(times < p.tau, 200, 0)
        np.testing.assert_allclose(result.sum(axis=1) + pending, 200, atol=1e-8)
        self.assertGreater(result[-1, 3], 199)

    def test_zero_input_and_linear_scaling_only_for_fixed_parameters(self):
        times = np.linspace(0, 600, 500)
        kwargs = {"method": "DOP853", "rtol": 1e-10, "atol": 1e-12}
        np.testing.assert_array_equal(numerical(times, 0, self.p, **kwargs), 0)
        first = numerical(times, 100, self.p, **kwargs)
        second = numerical(times, 200, self.p, **kwargs)
        np.testing.assert_allclose(2 * first, second, rtol=1e-8, atol=1e-8)

    def test_tight_solver_and_state_positivity(self):
        times = np.linspace(0, 600, 1201)
        expected = analytic(times, 200, self.p)
        for method in ("RK45", "DOP853"):
            actual = numerical(times, 200, self.p, method=method, rtol=1e-9, atol=1e-12)
            self.assertLess(np.max(np.abs(actual[:, 2] - expected[:, 2])) / self.p.volume, 1e-5)
            self.assertGreaterEqual(actual.min(), -1e-9)

    def test_invalid_inputs_do_not_produce_a_plausible_curve(self):
        for dose in (True, -1, float("nan"), float("inf")):
            with self.assertRaises(ValueError):
                analytic(np.array([0, 1]), dose, self.p)
        for times in (np.array([]), np.array([1, 0]), np.array([0, 0]), np.array([0, np.nan])):
            with self.assertRaises(ValueError):
                analytic(times, 200, self.p)
        with self.assertRaises(ValueError):
            Parameters(5, 0, 0.01, 0.01, 0.02, 0.1)


if __name__ == "__main__":
    unittest.main()
