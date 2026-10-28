"""Native numerical tests; run with `uv run --locked python -m unittest -v`."""

import json
import unittest
from dataclasses import replace
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
from unittest.mock import patch

import numpy as np
from model import (
    GlucoseInput,
    Parameters,
    algebraic,
    initial_state,
    mg_dl_to_mmol_l,
    simulate,
)
from verify import constant_solution, reference_rates, time_grid, verify

PROTOCOL = json.loads((Path(__file__).resolve().parents[1] / "protocol.json").read_text())


class NumericalTests(unittest.TestCase):
    def setUp(self):
        self.p = Parameters(**PROTOCOL["parameters"])
        self.input = GlucoseInput(**PROTOCOL["input"])
        self.times = np.linspace(0, 100, 401)

    def test_printed_initialization_and_declared_discrepancy(self):
        # Source-based anchor from literal printed 4.13, not author X0=92.7.
        state = initial_state(self.p, self.input)
        self.assertAlmostEqual(state[0], 0.154652145525, places=11)
        self.assertEqual(state[1], 0)
        self.assertGreater(abs(state[0] - 92.7), 90)
        np.testing.assert_array_equal(initial_state(self.p, self.input, 0), [0, 0])

    def test_published_delay_and_provision_anchors(self):
        rho, provision = algebraic(np.array([0.0, 5.0, 10.0, 1e100]), self.p)
        self.assertEqual(provision[0], 0)
        self.assertEqual(provision[1], 0)
        self.assertAlmostEqual(provision[2], 3.7939887636, places=9)
        self.assertEqual(1 / rho[1], 12.5)
        self.assertAlmostEqual(1 / rho[-1], 12.0488940629, places=9)
        self.assertTrue(np.all(np.isfinite(provision)))

    def test_constant_forcing_against_convolution_solution(self):
        forcing = GlucoseInput(g_max=10, g_b=10, tau_min=30)
        rho, provision = reference_rates(10, self.p)
        for m in (0.62, float(rho), float(rho) * (1 - 1e-12), 0.01):
            with self.subTest(m=m):
                p = replace(self.p, m=m)
                actual = simulate(
                    self.times,
                    p,
                    forcing,
                    x0_override=1.7,
                    method="DOP853",
                    rtol=1e-11,
                    atol=1e-13,
                    max_step=0.125,
                )
                expected = constant_solution(self.times, m=m, rho=rho, y_infinity=provision, x0=1.7)
                np.testing.assert_allclose(actual, expected, atol=1e-9, rtol=1e-10)

    def test_constant_solution_equal_rates_known_polynomial_exponential(self):
        # For m=rho=1, Yinf=1, X0=Y0=0: X=1-(1+t)e^-t, Y=1-e^-t.
        t = np.array([0.0, 0.1, 1.0, 10.0])
        actual = constant_solution(t, m=1, rho=1, y_infinity=1, x0=0)
        expected = np.column_stack((1 - (1 + t) * np.exp(-t), 1 - np.exp(-t)))
        np.testing.assert_allclose(actual, expected, atol=1e-15)

    def test_pool_balance_independent_of_y_equation(self):
        # Integrated dX/dt=Y-SR catches state ordering, m application, and output units.
        t = np.linspace(0, 25, 2501)
        states = simulate(t, self.p, self.input)
        net_provision = np.trapezoid(states[:, 1] - self.p.m * states[:, 0], t)
        delta_pool = states[-1, 0] - states[0, 0]
        self.assertLess(abs(net_provision - delta_pool), 1e-5)

    def test_no_recruitment_and_no_mobilization_limits(self):
        for p in (replace(self.p, p_plus=0), replace(self.p, c=0, m0=0)):
            with self.subTest(parameters=p):
                actual = simulate(self.times, p, self.input)
                np.testing.assert_array_equal(actual, np.zeros((len(self.times), 2)))

    def test_basal_is_zero_evoked_secretion(self):
        forcing = GlucoseInput(g_max=5, g_b=5, tau_min=30)
        np.testing.assert_array_equal(
            simulate(self.times, self.p, forcing), np.zeros((len(self.times), 2))
        )

    def test_suprathreshold_baseline_requires_explicit_numerical_override(self):
        forcing = GlucoseInput(g_max=10, g_b=10, tau_min=30)
        with self.assertRaises(ValueError):
            initial_state(self.p, forcing)
        with self.assertRaises(ValueError):
            simulate([0, 1], self.p, forcing)
        actual = simulate([0, 1], self.p, forcing, x0_override=0)
        np.testing.assert_array_equal(actual[0], [0, 0])
        self.assertGreater(actual[1, 0], 0)

    def test_capacity_scales_initial_pool_and_dynamics(self):
        nominal = simulate(self.times, self.p, self.input, x0_override=92.7)
        scaled = simulate(self.times, self.p, self.input, capacity=0.25, x0_override=92.7)
        self.assertEqual(scaled[0, 0], 0.25 * 92.7)
        np.testing.assert_allclose(scaled, nominal * 0.25, rtol=1e-8, atol=1e-8)
        np.testing.assert_array_equal(
            simulate(self.times, self.p, self.input, capacity=0, x0_override=92.7),
            np.zeros_like(nominal),
        )

    def test_same_amplitude_product_is_not_identifiable(self):
        nominal = simulate(self.times, self.p, self.input)
        other = simulate(
            self.times, replace(self.p, c=2 * self.p.c, m0=2 * self.p.m0), self.input, capacity=0.5
        )
        np.testing.assert_array_equal(nominal, other)

    def test_unit_conversion_source_convention(self):
        np.testing.assert_array_equal(mg_dl_to_mmol_l([0, 90, 180]), [0, 5, 10])
        with self.assertRaises(ValueError):
            mg_dl_to_mmol_l(-10)

    def test_invalid_model_parameters(self):
        for key, bad in (
            ("r", 0),
            ("m", -1),
            ("k_m", 0),
            ("n", 0),
            ("f", float("inf")),
            ("c", float("nan")),
            ("m0", -1),
            ("p_plus", -1),
            ("p_minus", -1),
            ("k_phi", 5),
            ("k_phi", 4),
            ("g_b", -1),
            ("r", True),
            ("r", "0.08"),
        ):
            with self.subTest(key=key, value=bad), self.assertRaises(ValueError):
                replace(self.p, **{key: bad})

    def test_invalid_glucose_scenarios(self):
        for changes in (
            {"g_max": 4},
            {"g_b": 0},
            {"tau_min": 0},
            {"g_max": float("nan")},
            {"kind": "meal"},
            {"tau_min": float("inf")},
        ):
            with self.subTest(changes=changes), self.assertRaises(ValueError):
                replace(self.input, **changes)
        for glucose in (-1, float("nan"), float("inf")):
            with self.subTest(glucose=glucose), self.assertRaises(ValueError):
                algebraic(glucose, self.p)

    def test_input_units_and_origin(self):
        self.assertEqual(float(self.input(0)), 17.2)
        self.assertAlmostEqual(float(self.input(30)), 5 + 12.2 / np.e)
        self.assertAlmostEqual(float(self.input(1e10)), 5)
        with self.assertRaises(ValueError):
            self.input(-1)

    def test_invalid_time_grids(self):
        for grid in ([], [0], [1, 2], [0, 0], [0, 2, 1], [0, np.nan], [0, np.inf], [[0, 1]]):
            with self.subTest(grid=grid), self.assertRaises(ValueError):
                simulate(grid, self.p, self.input)

    def test_invalid_solver_settings_and_capacity(self):
        for settings in (
            {"rtol": 0},
            {"rtol": 1},
            {"atol": -1},
            {"max_step": np.inf},
            {"method": "typo"},
            {"capacity": -1},
            {"capacity": np.nan},
            {"x0_override": -1},
            {"x0_override": np.inf},
        ):
            with self.subTest(settings=settings), self.assertRaises(ValueError):
                simulate([0, 1], self.p, self.input, **settings)

    def test_failed_and_truncated_solver_cannot_look_complete(self):
        results = [
            SimpleNamespace(success=False, message="selected failure"),
            SimpleNamespace(success=True, y=np.zeros((2, 1)), t=np.array([0]), message="truncated"),
            SimpleNamespace(
                success=True, y=np.zeros((2, 2)), t=np.array([0, 0.9]), message="wrong times"
            ),
            SimpleNamespace(
                success=True,
                y=np.array([[0, np.nan], [0, 1]]),
                t=np.array([0, 1]),
                message="nonfinite",
            ),
        ]
        for result in results:
            with self.subTest(message=result.message):
                with patch("model.solve_ivp", return_value=result), self.assertRaises(RuntimeError):
                    simulate([0, 1], self.p, self.input)

    def test_time_grid_refuses_silent_horizon_change(self):
        grid = time_grid(PROTOCOL)
        self.assertEqual(grid[-1], 100)
        self.assertEqual(len(grid), 401)
        with self.assertRaises(ValueError):
            time_grid({**PROTOCOL, "sample_step_min": 0.3})

    def test_prespecified_verification_campaign(self):
        evidence = verify(PROTOCOL)
        failed = [name for name, check in evidence["checks"].items() if not check["passed"]]
        self.assertEqual(failed, [])
        self.assertTrue(evidence["passed"])
        self.assertEqual(evidence["human_validation"], "not performed")
        self.assertEqual(set(evidence["sensitivity"]), set(PROTOCOL["sensitivity"]["parameters"]))
        # Pure linear amplitude parameters have sensitivities adding to one.
        s = evidence["sensitivity"]
        self.assertAlmostEqual(
            s["c"]["normalized_central_sensitivity"] + s["m0"]["normalized_central_sensitivity"],
            1.0,
            places=9,
        )


class RunnerFailureTests(unittest.TestCase):
    """Verify that failures and interruption remain reconstructibly unsuccessful."""

    def run_failed(self, *, malformed=False, solver_effect=None, solver_result=None):
        from report import reconstruct
        from run import execute

        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            protocol = root / "protocol.json"
            protocol.write_text("{bad json" if malformed else json.dumps(PROTOCOL))
            output = root / "attempt"
            with self.assertRaises(BaseException):
                if malformed:
                    execute(protocol, output)
                elif solver_effect is not None:
                    with patch("model.solve_ivp", side_effect=solver_effect):
                        execute(protocol, output)
                else:
                    with patch("model.solve_ivp", return_value=solver_result):
                        execute(protocol, output)
            manifest = json.loads((output / "manifest.json").read_text())
            self.assertEqual(manifest["status"], "failed")
            self.assertEqual((output / "protocol.json").read_bytes(), protocol.read_bytes())
            with self.assertRaises(ValueError):
                reconstruct(output)
            return manifest["error"]["type"]

    def test_malformed_config_preserved(self):
        self.assertEqual(self.run_failed(malformed=True), "JSONDecodeError")

    def test_incomplete_solver_preserved(self):
        result = SimpleNamespace(success=False, message="selected incomplete solve")
        self.assertEqual(self.run_failed(solver_result=result), "RuntimeError")

    def test_interruption_preserved(self):
        self.assertEqual(self.run_failed(solver_effect=KeyboardInterrupt()), "KeyboardInterrupt")

    def test_existing_output_never_overwritten(self):
        from run import execute

        with TemporaryDirectory() as temporary:
            output = Path(temporary)
            sentinel = output / "keep.txt"
            sentinel.write_text("existing work")
            with self.assertRaises(FileExistsError):
                execute(Path("unused-config.json"), output)
            self.assertEqual(sentinel.read_text(), "existing work")


if __name__ == "__main__":
    unittest.main()
