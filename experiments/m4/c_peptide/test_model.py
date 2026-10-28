"""Numerical and recorder failure tests, run in the isolated scientific environment."""

import json
import tempfile
import unittest
from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import numpy as np
from scipy.linalg import expm

from experiments.m4.c_peptide.identify import analyze, sensitivity
from experiments.m4.c_peptide.model import (
    Parameters,
    concentration_to_pmol_l,
    initial_state,
    insulin_mass_to_molar_input,
    simulate,
)
from experiments.m4.c_peptide.reference import bolus, constant_schedule
from experiments.m4.c_peptide.report import read_json, validate_protocol
from experiments.m4.c_peptide.run import HERE, execute
from experiments.m4.kinetic_inlet.forcing import Forcing

P = Parameters(0.037, 0.031, 0.052, 0.0655)
SETTINGS = {"method": "DOP853", "rtol": 1e-11, "atol": 1e-13, "max_step": 0.125}


class KineticsTests(unittest.TestCase):
    def test_original_bolus_vs_independent_matrix_exponential(self):
        times = np.array([0, 0.01, 2, 10, 60, 180])
        matrix = np.array([[-P.k1 - P.k3, P.k2], [P.k1, -P.k2]])
        expected = [(expm(matrix * t) @ [100, 0])[0] / P.volume_l_kg for t in times]
        np.testing.assert_allclose(bolus(times, P, 100), expected, rtol=1e-12, atol=1e-12)

    def test_off_grid_input_jump_mass_and_source_formula(self):
        forcing = Forcing([0, 0.37, 1.19, 4], [0, 7, 2], [0, 7, 2])
        times = np.array([0, 0.5, 1, 2, 4])
        initial = [10, 3, 0, 0]
        actual = simulate(times, P, forcing, initial, SETTINGS)
        np.testing.assert_allclose(
            actual[:, 0] / P.volume_l_kg, constant_schedule(times, P, forcing, initial), atol=1e-8
        )
        np.testing.assert_allclose(actual[:, :3].sum(axis=1) - actual[:, 3], 13, atol=1e-10)
        np.testing.assert_allclose(
            actual[:, 3], [forcing.integral(0, t) for t in times], atol=1e-10
        )
        self.assertEqual(initial, [10, 3, 0, 0])

    def test_linear_input_one_compartment_closed_form(self):
        # q(t)=a*t: Q(t)=a*(t/k-(1-exp(-k*t))/k**2), zero initial state.
        params = replace(P, k1=0)
        times = np.linspace(0, 10, 31)
        state = simulate(times, params, Forcing([0, 10], [0], [20]), [0] * 4, SETTINGS)
        expected = 2 * (times / P.k3 + np.expm1(-P.k3 * times) / P.k3**2)
        np.testing.assert_allclose(state[:, 0], expected, atol=1e-9)
        np.testing.assert_allclose(state[:, 3], times**2, atol=1e-10)

    def test_equilibrium_and_zero_are_exact(self):
        times = np.arange(11)
        initial = initial_state({"kind": "equilibrium", "basal_q_pmol_kg_min": 1.5}, P)
        state = simulate(times, P, Forcing([0, 10], [1.5], [1.5]), initial, SETTINGS)
        np.testing.assert_allclose(state[:, :2], np.tile(initial[:2], (11, 1)), atol=1e-12)
        zero = simulate(times, P, Forcing([0, 10], [0], [0]), [0] * 4, SETTINGS)
        np.testing.assert_array_equal(zero, np.zeros((11, 4)))

    def test_degenerate_decay_rates(self):
        p = Parameters(0, 0.05, 0.05, 0.1)
        t = np.linspace(0, 10, 11)
        force = Forcing([0, 10], [0], [0])
        initial = [0, 100, 0, 0]
        expected = 100 * 0.05 * t * np.exp(-0.05 * t) / 0.1
        np.testing.assert_allclose(constant_schedule(t, p, force, initial), expected)
        actual = simulate(t, p, force, initial, SETTINGS)
        np.testing.assert_allclose(actual[:, 0] / 0.1, expected, atol=1e-8)

    def test_units(self):
        self.assertEqual(concentration_to_pmol_l(1, "pmol/mL"), 1000)
        self.assertAlmostEqual(concentration_to_pmol_l(3.021, "ng/mL"), 1000)
        self.assertAlmostEqual(insulin_mass_to_molar_input(5.808, 80), 12.5)
        for args in ((1, "nmol/mL"), (-1, "pmol/L"), (True, "pmol/L")):
            with self.assertRaises(ValueError):
                concentration_to_pmol_l(*args)

    def test_invalid_parameters_and_initial_states(self):
        for key in ("k1", "k2", "k3", "volume_l_kg"):
            for value in (-1, float("nan"), float("inf"), True, "0.1"):
                with self.subTest(key=key, value=value), self.assertRaises(ValueError):
                    replace(P, **{key: value})
        for value in (0, -1, float("inf")):
            with self.assertRaises(ValueError):
                insulin_mass_to_molar_input(1, value)
        for spec in ({"kind": "bolus"}, {"kind": "zero", "dose": 1}, {"kind": "guess"}):
            with self.assertRaises(ValueError):
                initial_state(spec, P)

    def test_invalid_grids_states_and_solver(self):
        force = Forcing([0, 1], [0], [0])
        for grid in ([0], [0, 0.5], [0, 1, 1], [0.1, 1], [0, float("nan"), 1]):
            with self.assertRaises(ValueError):
                simulate(grid, P, force, [0] * 4, SETTINGS)
        for initial in ([0] * 3, [-1, 0, 0, 0], [0, 0, 1, 0], [float("nan"), 0, 0, 0]):
            with self.assertRaises(ValueError):
                simulate([0, 1], P, force, initial, SETTINGS)
        for settings in ({}, {**SETTINGS, "rtol": 1}, {**SETTINGS, "method": "unknown"}):
            with self.assertRaises(ValueError):
                simulate([0, 1], P, force, [0] * 4, settings)

    def test_incomplete_and_nonfinite_solves_rejected(self):
        for result in (
            SimpleNamespace(success=False, message="forced failure"),
            SimpleNamespace(success=True, y=np.zeros((4, 0)), message="missing"),
            SimpleNamespace(
                success=True, y=np.full((4, 1), np.nan), t=np.array([1]), message="nan"
            ),
        ):
            with patch("experiments.m4.c_peptide.model.solve_ivp", return_value=result):
                with self.assertRaises(RuntimeError):
                    simulate([0, 1], P, Forcing([0, 1], [0], [0]), [0] * 4, SETTINGS)

    def test_unknown_dose_volume_null_direction(self):
        joint = sensitivity(np.array([2, 10, 60, 180]), P, 100, 1e-5, free_dose=True)
        np.testing.assert_allclose(joint[:, 3] + joint[:, 4], 0, atol=1e-7)

    def test_independent_synthetic_recovery(self):
        result = analyze(read_json(HERE / "protocol.json"))
        self.assertTrue(all(f["max_relative_parameter_error"] < 1e-4 for f in result["fits"]))
        self.assertEqual(result["designs"]["full_known_input"]["rank"], 4)
        self.assertEqual(result["designs"]["full_unknown_amplitude"]["rank"], 4)
        self.assertEqual(result["designs"]["sparse_known_input"]["rank"], 3)


class RecorderTests(unittest.TestCase):
    def test_invalid_protocol_failure_is_durable(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "bad.json").write_text("{incomplete")
            with self.assertRaises(json.JSONDecodeError):
                execute(root / "bad.json", root / "run")
            saved = read_json(root / "run/manifest.json")
            self.assertEqual(saved["status"], "failed")
            self.assertIn("protocol.json", saved["files"])

    def test_interrupt_preserves_attempt(self):
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "run"
            with patch("experiments.m4.c_peptide.run.simulate", side_effect=KeyboardInterrupt):
                with self.assertRaises(KeyboardInterrupt):
                    execute(HERE / "protocol.json", output)
            self.assertEqual(
                read_json(output / "manifest.json")["error"]["type"], "KeyboardInterrupt"
            )

    def test_existing_directory_untouched(self):
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp)
            (target / "sentinel").write_text("preserve")
            with self.assertRaises(FileExistsError):
                execute(HERE / "protocol.json", target)
            self.assertEqual(list(target.iterdir()), [target / "sentinel"])

    def test_protocol_rejects_missing_criteria_and_invalid_units(self):
        for field, value in (("criteria", {}), ("units", {})):
            p = read_json(HERE / "protocol.json")
            p[field] = value
            with self.assertRaises(ValueError):
                validate_protocol(p)


if __name__ == "__main__":
    unittest.main()
