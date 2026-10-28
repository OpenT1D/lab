"""Run in the locked BC-008 simglucose environment, not root tooling."""

import unittest
from types import SimpleNamespace

import numpy as np

from experiments.m4.feedback import coupled as bc008_coupled
from experiments.m4.feedback import secretion as bc008_secretion
from experiments.m4.feedback.contract import baseline
from experiments.m4.kinetic_inlet.native import Action, T1DPatient, load
from experiments.m4.paired_kinetics.common import read

from . import coupled
from .common import HERE, load_model, protocol


class CausalCouplingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.bc = read(HERE.parent / "feedback/protocol.json")
        cls.task = protocol(read(HERE / "protocol.json"), cls.bc)
        native, _ = load()
        cls.params = {k: (str(v) if k == "Name" else float(v)) for k, v in native.to_dict().items()}
        cls.basal = baseline(cls.params, [float(v) for v in native.iloc[2:15]], 0.25, 0.5)
        cls.source = bc008_secretion.parameters(cls.bc, cls.basal, 1)
        cls.model = staticmethod(load_model(HERE / "example_model.py"))
        cls.model_params = read(HERE / "example_model.json")["parameters"]

    def test_independent_adapter_matches_unchanged_bc008_rhs(self):
        state = np.r_[
            self.basal["state"], self.basal["Z_pmol_kg_min"], self.basal["P_pmol_kg"], np.zeros(5)
        ]
        state[0], state[2], state[3], state[5], state[14] = 30000, 1000, 320, 8, 7
        candidate = coupled.rhs_factory(
            self.params,
            self.basal,
            0.5,
            30000,
            self.model,
            self.model_params,
            self.task,
            "candidate",
        )(3, state)
        original = bc008_coupled.rhs_factory(self.params, self.basal, self.source, 30000)(3, state)
        np.testing.assert_array_equal(candidate, original)

    def test_host_owns_portal_liver_and_constant_basal(self):
        p = SimpleNamespace(**self.params)
        state = np.r_[
            self.basal["state"], self.basal["Sb_pmol_kg_min"], self.basal["P_pmol_kg"], np.zeros(5)
        ]
        state[14] = 7
        rhs = coupled.rhs_factory(
            self.params,
            self.basal,
            0.5,
            0,
            self.model,
            self.model_params,
            self.task,
            "host_constant_basal",
        )
        actual = rhs(5, state)
        native = T1DPatient.model(
            5, state[:13], Action(CHO=0, insulin=self.basal["action_insulin_u_min"]), p, 0, 0
        )
        self.assertEqual(actual[3], native[3])
        self.assertEqual(actual[9], native[9] + 0.5 * state[14])
        self.assertEqual(actual[13], 0)
        self.assertEqual(actual[14], self.basal["Sb_pmol_kg_min"] - 0.5 * state[14])
        self.assertEqual(actual[16], self.basal["Sb_pmol_kg_min"])
        self.assertEqual(actual[17], 0.5 * state[14])


if __name__ == "__main__":
    unittest.main()
