"""Source-specific host/portal checks in the locked BC-008 scientific runtime."""

import unittest

import numpy as np
from scipy.integrate import solve_ivp

from experiments.m4.causal_secretion import coupled
from experiments.m4.causal_secretion.common import protocol
from experiments.m4.feedback.contract import baseline
from experiments.m4.kinetic_inlet.native import load
from experiments.m4.paired_kinetics.common import read

from .model import evaluate
from .verify import HERE


class UltradianCouplingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.bc = read(HERE.parent / "feedback/protocol.json")
        cls.task = protocol(read(HERE.parent / "causal_secretion/protocol.json"), cls.bc)
        native, _ = load()
        cls.params = {k: (str(v) if k == "Name" else float(v)) for k, v in native.to_dict().items()}
        cls.basal = baseline(cls.params, [float(v) for v in native.iloc[2:15]], 0.25, 0.5)
        cls.source_params = read(HERE / "model.json")["parameters"]

    def state(self):
        return np.r_[
            self.basal["state"], self.basal["Z_pmol_kg_min"], self.basal["P_pmol_kg"], np.zeros(5)
        ]

    def rhs(self, mode="candidate"):
        return coupled.rhs_factory(
            self.params, self.basal, 0.5, 0, evaluate, self.source_params, self.task, mode
        )

    def test_source_changes_only_portal_input_and_pancreatic_ledger_at_fixed_state(self):
        state = self.state()
        state[3] = 198 * self.params["Vg"]
        candidate = self.rhs()(7, state)
        control = self.rhs("host_constant_basal")(7, state)
        # Source is upstream of portal transit; held P gives identical liver/native RHS.
        np.testing.assert_array_equal(candidate[:14], control[:14])
        np.testing.assert_array_equal(candidate[17:], control[17:])
        self.assertEqual(candidate[15], control[15])
        delta = candidate[16] - control[16]
        self.assertGreater(delta, 0)
        self.assertAlmostEqual(candidate[14] - control[14], delta, places=14)

    def test_preserved_initial_basal_without_new_secretion_state(self):
        derivative = self.rhs()(0, self.state())
        self.assertLess(np.max(np.abs(derivative[:13])), 1e-8)
        self.assertEqual(derivative[13], 0)
        self.assertEqual(derivative[14], 0)

    def test_constant_glucose_portal_response_matches_closed_form(self):
        # Isolate the actual host portal/ledger RHS with native G held at 198 mg/dL.
        state = self.state()
        state[3] = 198 * self.params["Vg"]
        rhs = self.rhs()
        rate = rhs(0, state)[16]
        p0, gamma = state[14], 0.5

        def isolated(t, y):
            fixed = state.copy()
            fixed[14] = y[0]
            dx = rhs(t, fixed)
            return dx[[14, 16, 17]]

        times = np.linspace(0, 20, 41)
        result = solve_ivp(
            isolated, (0, 20), [p0, 0, 0], t_eval=times, rtol=1e-11, atol=1e-12, max_step=0.1
        )
        self.assertTrue(result.success)
        decay = np.exp(-gamma * times)
        expected = np.array(
            [
                rate / gamma + (p0 - rate / gamma) * decay,
                rate * times,
                rate * times + (p0 - rate / gamma) * (1 - decay),
            ]
        )
        np.testing.assert_allclose(result.y, expected, rtol=0, atol=1e-9)
        self.assertLess(np.max(np.abs(result.y[0] + result.y[2] - p0 - result.y[1])), 1e-10)


if __name__ == "__main__":
    unittest.main()
