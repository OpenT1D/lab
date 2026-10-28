"""BC-011 checks in the separately locked native environment."""

import json
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import numpy as np

from .inference import jacobian
from .model import Model
from .verify import mass_errors, run


class JointNumericalTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.protocol = json.loads(Path(__file__).with_name("protocol.json").read_text())
        cls.model = Model(cls.protocol)

    def test_forward_gates(self):
        evidence = run(self.model)
        self.assertTrue(evidence["passed"], evidence["checks"])

    def test_bounded_jacobian_against_quadratic_derivatives(self):
        lower = np.log(np.array([0.5, 0.5, 0.5]))
        upper = np.log(np.array([1.5, 1.5, 1.5]))

        def quadratic(x):
            # Also verify that the one-sided boundary formula never probes
            # outside the permitted model domain.
            self.assertTrue(np.all(x >= lower) and np.all(x <= upper))
            a, b, c = x
            return np.array([a * a + 3 * b - 2 * c, a * b + 2 * c * c, 7 + a - b * b + 4 * c])

        cases = (
            np.zeros(3),
            lower + 1e-5,
            upper - 1e-5,
            lower,
            upper,
            np.array([lower[0], upper[1], 0]),
        )
        for x in cases:
            a, b, c = x
            analytic = np.array([[2 * a, 3, -2], [b, a, 4 * c], [1, -2 * b, 4]])
            with self.subTest(log_parameters=x.tolist()):
                calculated = jacobian(quadratic, x, 0.001, lower, upper)
                np.testing.assert_allclose(calculated, analytic, rtol=0, atol=1e-8)

    def test_fasting_and_unit_conversion(self):
        # Closed-form nonzero equilibrium, independent of transient integration.
        for theta in ([0.5, 0.5, 1.5], [1.5, 1.5, 0.5]):
            record = self.model.simulate(theta, load=0, solver="reference")
            cp = self.protocol["model"]["cpeptide"]
            expected_cp = record["baseline"]["Sb_pmol_kg_min"] / (
                cp["k3"] * theta[2] * cp["volume_l_kg"]
            )
            self.assertLess(np.max(np.abs(record["observations"][:, 2] - expected_cp)), 1e-7)
            self.assertLess(
                np.max(np.abs(record["observations"][:, :2] - record["observations"][0, :2])), 1e-7
            )
            self.assertAlmostEqual(record["observations"][0, 0], 138.56, places=8)
            self.assertAlmostEqual(record["observations"][0, 1], 100.25, places=8)

    def test_invalid_inputs_before_integration(self):
        invalid = (
            {"theta": [True, 1, 1]},
            {"theta": [1, np.nan, 1]},
            {"theta": [1, 0.49, 1]},
            {"theta": [1, 1, 1.51]},
            {"theta": [1, 1]},
            {"theta": [1, 1, 1], "load": -1},
            {"theta": [1, 1, 1], "load": np.inf},
            {"theta": [1, 1, 1], "times": [0, 239]},
            {"theta": [1, 1, 1], "times": [0, 10, 10, 240]},
            {"theta": [1, 1, 1], "solver": "unregistered"},
            {"theta": [1, 1, 1], "source_scale": 3},
        )
        with patch("experiments.m4.joint_identifiability.model.solve_ivp") as solver:
            for kwargs in invalid:
                with self.subTest(kwargs=kwargs), self.assertRaises(ValueError):
                    self.model.simulate(**kwargs)
            solver.assert_not_called()

    def test_incomplete_nonfinite_and_terminal_output_rejected(self):
        times = np.arange(241)
        outputs = (
            SimpleNamespace(status=0, y=np.zeros((24, 240)), t=times[:-1], message="short"),
            SimpleNamespace(status=1, y=np.zeros((24, 241)), t=times, message="event"),
            SimpleNamespace(status=-1, y=np.zeros((24, 241)), t=times, message="solver failure"),
            SimpleNamespace(status=0, y=np.full((24, 241), np.nan), t=times, message="nonfinite"),
        )
        for output in outputs:
            with (
                self.subTest(message=output.message),
                patch("experiments.m4.joint_identifiability.model.solve_ivp", return_value=output),
                self.assertRaises(RuntimeError),
            ):
                self.model.simulate([1, 1, 1])

    def test_inventory_check_detects_missing_cp_input(self):
        record = self.model.simulate([1, 1, 1])
        self.assertLess(mass_errors(record)["cpeptide_pmol_kg"], 1e-6)
        corrupt = {**record, "states": record["states"].copy()}
        corrupt["states"][:, 23] = 0
        self.assertGreater(mass_errors(corrupt)["cpeptide_pmol_kg"], 100)


if __name__ == "__main__":
    unittest.main()
