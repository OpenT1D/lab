"""Run in the locked simglucose environment; root tooling has no SciPy."""

import math
import unittest
from unittest.mock import patch

import numpy as np

from . import secretion as s
from .source_oracle import advance


class SourceTests(unittest.TestCase):
    def setUp(self):
        self.p = s.Parameters(0.05, 0.11, 2.3, 0.5, 1.1, 100)
        self.solver = dict(method="DOP853", rtol=1e-11, atol=1e-13, max_step=0.0625)

    def test_portal_washout_and_distinct_arrival(self):
        g = s.GlucoseSignal((0, 10), (40, 40))
        y = s.simulate([0, 10], g, [0, 3], self.p, self.solver)
        self.assertAlmostEqual(y[-1, 1], 3 * math.exp(-5), places=11)
        self.assertEqual(y[-1, 2], 0)
        self.assertAlmostEqual(y[-1, 3], 3 * (1 - math.exp(-5)), places=11)

    def test_equal_rates_limit_independent_solution(self):
        # Zero target/dynamic, nonzero Z feeds portal: P=e^-at*(P0+Z0*t).
        actual = advance([2, 3, 0, 0], 10, 0, 0, 0, 0.05, 0.05)
        self.assertAlmostEqual(actual[0], 2 * math.exp(-0.5), places=12)
        self.assertAlmostEqual(actual[1], 23 * math.exp(-0.5), places=12)
        self.assertAlmostEqual(actual[2], 40 * (1 - math.exp(-0.5)), places=12)

    def test_literal_signed_y_equations(self):
        for g in (40, 90, 95, 100, 180):
            for gd in (-3, 0, 2):
                y, portal = -0.4, 3
                beta_delta = self.p.beta * (g - 100)
                ydot = (
                    -0.05 * y + 0.05 * beta_delta if beta_delta >= -1.1 else -0.05 * y - 0.05 * 1.1
                )
                dz, dp, spo, liver = s.rates(g, gd, y + 1.1, portal, self.p)
                self.assertAlmostEqual(dz, ydot)
                self.assertAlmostEqual(spo, y + 1.1 + 2.3 * max(gd, 0))
                self.assertAlmostEqual(dp, spo - liver)

    def test_invalid_input_and_incomplete_output(self):
        for edges, values in [
            ((0, 0), (10, 10)),
            ((1, 2), (10, 10)),
            ((0, 1), (True, 10)),
            ((0, 1), (10, math.nan)),
        ]:
            with self.assertRaises(ValueError):
                s.GlucoseSignal(edges, values)
        g = s.GlucoseSignal((0, 10), (100, 100))
        with self.assertRaises(ValueError):
            s.simulate([0, 9], g, [1.1, 2.2], self.p, self.solver)
        with patch.object(s, "solve_ivp") as solve:
            solve.return_value.success = True
            solve.return_value.y = np.zeros((4, 1))
            with self.assertRaises(RuntimeError):
                s.simulate([0, 10], g, [1.1, 2.2], self.p, self.solver)


class CouplingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from experiments.m4.kinetic_inlet.native import load

        from .common import HERE, read
        from .contract import baseline

        cls.protocol = read(HERE / "protocol.json")
        native, _ = load()
        cls.params = {k: (str(v) if k == "Name" else float(v)) for k, v in native.to_dict().items()}
        cls.basal = baseline(cls.params, [float(v) for v in native.iloc[2:15]], 0.25, 0.5)
        cls.source = s.parameters(cls.protocol, cls.basal, 1)

    def test_boundary_locality_and_two_independent_balances(self):
        from types import SimpleNamespace

        from experiments.m4.kinetic_inlet.native import Action, T1DPatient

        from .coupled import glucose_fluxes, rhs_factory

        b, p = self.basal, SimpleNamespace(**self.params)
        x = np.r_[b["state"], b["Z_pmol_kg_min"], b["P_pmol_kg"], np.zeros(5)]
        x[2], x[3], x[5], x[14] = 1000, 320, 8, 7
        dx = rhs_factory(self.params, b, self.source, 30000)(3, x)
        native = T1DPatient.model(3, x[:13], Action(0, b["action_insulin_u_min"]), p, 30000, 0)
        expected = native.copy()
        expected[9] += 0.5 * 7
        np.testing.assert_array_equal(dx[:13], expected)
        self.assertAlmostEqual(
            sum(dx[i] for i in (5, 9, 10, 11, 14)), dx[15] + dx[16] - dx[18] - dx[19]
        )
        f = glucose_fluxes(x, p)
        self.assertAlmostEqual(dx[3] + dx[4], f[0] + f[1] - sum(f[2:]))

    def test_terminal_exit_is_preserved_as_incomplete(self):
        from copy import deepcopy

        from .coupled import integrate

        p = deepcopy(self.protocol)
        p["horizon_min"] = 2
        p["glucose_envelope_mg_dl"] = [40, self.basal["h_mg_dl"] + 0.001]
        record, _ = integrate(p, self.params, self.basal, self.source, 30000, p["solvers"][-1])
        self.assertEqual(record["status"], "failed")
        self.assertIn("glucose_above_envelope", record["failure"]["terminal_events"])
        self.assertLess(record["failure"]["time"], 2)
        self.assertEqual(len(record["failure"]["last_state"]), 20)
        self.assertLess(record["times"][-1], 2)

    def test_signed_action_is_not_an_insulin_amount(self):
        from copy import deepcopy

        from .coupled import integrate

        p, b = deepcopy(self.protocol), deepcopy(self.basal)
        p["horizon_min"] = 0.5
        b["state"][6] = -0.001
        record, _ = integrate(p, self.params, b, self.source, 0, p["solvers"][-1])
        self.assertEqual(record["status"], "completed")
        self.assertLess(record["states"][0][6], 0)


if __name__ == "__main__":
    unittest.main()
