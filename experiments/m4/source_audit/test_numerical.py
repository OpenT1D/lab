"""Independent numerical checks of the limited analytical source audit."""

import copy
import unittest
from types import SimpleNamespace
from unittest.mock import patch

import numpy as np

from experiments.m4.source_audit.audit import burst
from experiments.m4.source_audit.numerical import execute, integrate
from experiments.m4.source_audit.run import HERE, assess, read


class NumericalTests(unittest.TestCase):
    def test_equal_rate_limit_against_numerical_ode(self):
        times = np.linspace(0, 8, 161)
        p = {"f": 1.8, "p_minus": 0.2, "m": 2.0}
        settings = {"method": "DOP853", "rtol": 1e-11, "atol": 1e-13, "max_step": 0.05}
        numerical = integrate(times, [3, 0, 0, 0], p, settings)
        exact = np.array([burst(t, 3, 1.8, 0.2, 2) for t in times])
        np.testing.assert_allclose(numerical, exact, rtol=1e-9, atol=1e-11)

    def test_incomplete_solver_rejected(self):
        result = SimpleNamespace(success=True, y=np.zeros((4, 1)), t=np.array([0]))
        with patch("experiments.m4.source_audit.numerical.solve_ivp", return_value=result):
            with self.assertRaises(RuntimeError):
                integrate(np.array([0, 1]), [1, 0, 0, 0], {"f": 1, "m": 1, "p_minus": 1}, {})

    def test_recorded_states_are_reassessed(self):
        p = read(HERE / "protocol.json")
        n = execute(p)
        self.assertTrue(assess(p, n)["passed"])
        bad = copy.deepcopy(n)
        bad["burst_states"][0][-1][2] += 0.1
        self.assertFalse(assess(p, bad)["passed"])
        bad = copy.deepcopy(n)
        bad["reduced_states"]["author_explicit"][-1][10][0] += 1
        self.assertFalse(assess(p, bad)["passed"])
        bad = copy.deepcopy(n)
        bad["burst_analytic"][-1][2] += 1
        with self.assertRaises(ValueError):
            assess(p, bad)
