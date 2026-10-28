"""Model boundary verification in the unchanged locked simglucose runtime."""

import copy
import unittest

import numpy as np
from scipy.linalg import expm

from experiments.m4.feedback import coupled, secretion
from experiments.m4.feedback.contract import baseline
from experiments.m4.kinetic_inlet.native import load

from .common import HERE, ROOT, read
from .model import anchors, terms
from .numerical import integrate, rhs_factory
from .report import assess_preflight
from .worker import preflight


class HepaticTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.p = read(HERE / "protocol.json")
        cls.parent = read(ROOT / cls.p["parent"])
        native, _ = load()
        cls.params = {k: (str(v) if k == "Name" else float(v)) for k, v in native.to_dict().items()}
        cls.initial = [float(v) for v in native.iloc[2:15]]
        cls.b = baseline(cls.params, cls.initial, 0.25, 0.5)
        cls.source = secretion.parameters(cls.parent, cls.b, 1)
        cls.h = cls.p["source"] | {"gamma": 0.5}
        cls.x = np.r_[cls.b["state"], cls.b["Z_pmol_kg_min"], cls.b["P_pmol_kg"], np.zeros(5)]

    def test_independent_preflight_and_disabled_equivalence(self):
        probe = preflight(self.p, self.parent, self.params, self.initial)
        errors = assess_preflight(self.p, self.parent, self.params, self.initial, probe)
        self.assertEqual(errors["disabled_rhs_error"], 0)
        for name, value in errors.items():
            self.assertLessEqual(value, self.p["verification"][name])

    def test_extraction_uses_liver_arrival_not_rate_state(self):
        x = self.x.copy()
        v = self.p["variants"][1]
        original = terms(x, self.params, self.b, self.h, v)
        x[13] += 100
        self.assertEqual(terms(x, self.params, self.b, self.h, v), original)
        x[14] += 2
        self.assertAlmostEqual(terms(x, self.params, self.b, self.h, v)["HE"], 0.6 - 0.0304)

    def test_portal_changes_source_slope_at_same_stage(self):
        x = self.x.copy()
        x[2] = 1000
        x[14] += 2
        v = self.p["variants"][2]
        old = coupled.rhs_factory(self.params, self.b, self.source, 30000)(0, x)
        new = rhs_factory(self.params, self.b, self.source, self.h, 30000, v)(0, x)
        self.assertAlmostEqual(new[3] - old[3], -0.0618 * 2)
        self.assertGreater(new[3], 0)
        self.assertAlmostEqual(
            new[16] - old[16], self.source.K * (new[3] - old[3]) / self.params["Vg"]
        )
        self.assertEqual(new[9], old[9])
        self.assertEqual(new[18], old[18])

    def test_liver_loss_changes_inventory_and_matching_ledger_only(self):
        x = self.x.copy()
        x[14] += 2
        v = self.p["variants"][1]
        old = coupled.rhs_factory(self.params, self.b, self.source, 0)(0, x)
        new = rhs_factory(self.params, self.b, self.source, self.h, 0, v)(0, x)
        np.testing.assert_allclose(new[9] - old[9], -(new[18] - old[18]), atol=1e-15)
        for i in set(range(20)) - {9, 18}:
            self.assertEqual(old[i], new[i])
        self.assertAlmostEqual(
            sum(new[i] for i in (5, 9, 10, 11, 14)), new[15] + new[16] - new[18] - new[19]
        )

    def test_no_clipping_invalid_extraction(self):
        x = self.x.copy()
        x[14] = 100
        with self.assertRaisesRegex(ValueError, "Extraction"):
            terms(x, self.params, self.b, self.h, self.p["variants"][1])

    def test_kinetic_perturbation_against_matrix_exponential(self):
        # Constant source and portal inventory make HE constant. Perturb liver
        # insulin only: independent 2x2 homogeneous transient, SC remains basal.
        parent = copy.deepcopy(self.parent)
        parent["horizon_min"] = 10
        b = copy.deepcopy(self.b)
        b["state"][9] += 1
        source = secretion.parameters(parent, b, 0)
        v = self.p["variants"][3]
        data = integrate(parent, self.p, self.params, b, source, 0, v, parent["solvers"][-1])
        m = self.params
        matrix = np.array([[-m["m2"] - m["m4"], m["m1"]], [m["m2"], -m["m1"] - m["m30"]]])
        expected = np.array(self.b["state"])[[5, 9]] + expm(matrix * 10) @ np.array([0, 1])
        np.testing.assert_allclose(
            np.array(data["states"])[-1, [5, 9]], expected, atol=1e-9, rtol=0
        )

    def test_HE_exit_has_stop_time_and_last_state(self):
        parent = copy.deepcopy(self.parent)
        parent["horizon_min"] = 5
        p = copy.deepcopy(self.p)
        # Fault injection changes only the computational test envelope.
        p["HE_computational_envelope"] = [0.6 - 1e-6, 0.999999]
        data = integrate(
            parent,
            p,
            self.params,
            self.b,
            self.source,
            30000,
            self.p["variants"][1],
            parent["solvers"][-1],
        )
        self.assertEqual(data["status"], "failed")
        self.assertIn("HE_low", data["failure"]["terminal_events"])
        self.assertLess(data["failure"]["time"], 5)
        self.assertEqual(len(data["failure"]["last_state"]), 20)
        self.assertLess(data["times"][-1], 5)

    def test_published_intercept_identity(self):
        a = anchors(self.params, self.b, self.h)
        self.assertAlmostEqual(a["m6_effective"] - 0.0304 * self.b["Sb_pmol_kg_min"], 0.6)
        self.assertAlmostEqual(
            a["kp1_effective"] - 0.0618 * self.b["P_pmol_kg"], self.params["kp1"]
        )


if __name__ == "__main__":
    unittest.main()
