"""Run in the pinned M0 insulin environment."""

import unittest
from types import SimpleNamespace
from unittest.mock import patch

import numpy as np

from experiments.m4.kinetic_inlet import native
from experiments.m4.kinetic_inlet.forcing import Forcing
from experiments.m4.paired_kinetics import oracle
from experiments.m4.paired_kinetics.insulin import simulate

SETTINGS = {"method": "DOP853", "rtol": 1e-11, "atol": 1e-13, "max_step": 0.125}


class InsulinTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.params, _ = native.load()

    def test_zero_initial_exact_legacy_with_off_grid_jumps(self):
        force = Forcing([0, 0.37, 1.19, 2], [0, 7, 2], [0, 7, 2])
        t = np.linspace(0, 2, 9)
        a = simulate(t, self.params, force, [0] * 5, SETTINGS)
        b = native.simulate(t, self.params, force, "liver", SETTINGS)
        np.testing.assert_array_equal(a, b)

    def test_nonstationary_washout_conserves_initial_inventory(self):
        force = Forcing([0, 30], [0], [0])
        t = np.arange(31, dtype=float)
        initial = [2, 3, 0, 0, 0]
        actual = simulate(t, self.params, force, initial, SETTINGS)
        expected = oracle.insulin(t, self.params, force, initial)
        np.testing.assert_allclose(actual, expected, rtol=0, atol=1e-9)
        np.testing.assert_allclose(actual[:, :4].sum(axis=1), 5, atol=1e-10)
        np.testing.assert_array_equal(actual[:, 4], 0)
        self.assertGreater(actual[-1, 2] + actual[-1, 3], 4)
        self.assertEqual(initial, [2, 3, 0, 0, 0])

    def test_nonzero_forced_oracle_and_repeat(self):
        force = Forcing([0, 0.7, 5], [2, 4], [4, 1])
        t = np.array([0, 0.4, 1, 3, 5])
        initial = [3, 1, 0, 0, 0]
        actual = simulate(t, self.params, force, initial, SETTINGS)
        np.testing.assert_allclose(
            actual, oracle.insulin(t, self.params, force, initial), rtol=0, atol=1e-9
        )
        np.testing.assert_array_equal(actual, simulate(t, self.params, force, initial, SETTINGS))

    def test_baseline_stationary_and_losses_continue(self):
        p = self.params
        q = 1.5
        il = q / (p.m30 + p.m1 * p.m4 / (p.m2 + p.m4))
        ip = p.m1 * il / (p.m2 + p.m4)
        t = np.arange(11, dtype=float)
        out = simulate(t, p, Forcing([0, 10], [q], [q]), [ip, il, 0, 0, 0], SETTINGS)
        np.testing.assert_allclose(out[:, :2], np.tile([ip, il], (11, 1)), atol=1e-11)
        self.assertAlmostEqual(out[-1, 2] + out[-1, 3], 15, places=10)
        self.assertAlmostEqual(out[-1, 4], 15, places=10)

    def test_invalid_initial_inventories_and_ledgers(self):
        for initial in (
            [0] * 4,
            [-1, 0, 0, 0, 0],
            [0, 0, 1, 0, 0],
            [True] * 5,
            [float("nan"), 0, 0, 0, 0],
        ):
            with self.assertRaises(ValueError):
                simulate([0, 1], self.params, Forcing([0, 1], [0], [0]), initial, SETTINGS)

    def test_rejects_incomplete_solver(self):
        result = SimpleNamespace(success=False, message="forced incomplete solve")
        with patch("experiments.m4.paired_kinetics.insulin.solve_ivp", return_value=result):
            with self.assertRaises(RuntimeError):
                simulate([0, 1], self.params, Forcing([0, 1], [0], [0]), [2, 3, 0, 0, 0], SETTINGS)

    def test_native_guard_remains_owned_by_existing_inlet(self):
        state = np.asarray(self.params.iloc[2:15].values, dtype=float).copy()
        state[9] = -1
        action = native.Action(CHO=0, insulin=0)
        a = native.derivative(0, state, action, self.params, q=0, route="liver")
        b = native.derivative(0, state, action, self.params, q=2, route="liver")
        np.testing.assert_array_equal(a, b)


if __name__ == "__main__":
    unittest.main()
