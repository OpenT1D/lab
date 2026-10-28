"""Native inlet/forcing tests; execute with the unchanged locked M0 runtime."""

import json
import unittest
from dataclasses import FrozenInstanceError
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
from unittest.mock import patch

import numpy as np
from simglucose.patient.t1dpatient import Action, T1DPatient

from experiments.m4.kinetic_inlet import native
from experiments.m4.kinetic_inlet.forcing import Forcing, from_source_samples, interval_average

PROTOCOL = json.loads(Path(__file__).with_name("protocol.json").read_text())
SETTINGS = dict(PROTOCOL["solvers"][1])


class ForcingTests(unittest.TestCase):
    def test_constant_and_linear_integrals(self):
        constant = Forcing([0, 10], [2], [2])
        linear = Forcing([0, 10], [0], [2])
        self.assertEqual(constant.integral(), 20)
        self.assertEqual(constant.integral(2, 5), 6)
        self.assertEqual(linear.integral(), 10)
        self.assertAlmostEqual(linear.integral(2, 5), (5**2 - 2**2) / 10)
        self.assertEqual(linear.evaluate(5), 1)

    def test_pulse_jumps_have_no_triangle_or_double_count(self):
        pulse = Forcing([0, 5.3, 15.7, 100], [0, 2, 0], [0, 2, 0])
        self.assertAlmostEqual(pulse.integral(), 20.8)
        self.assertEqual(pulse.evaluate(5.3, side="left"), 0)
        self.assertEqual(pulse.evaluate(5.3), 2)
        self.assertEqual(pulse.evaluate(15.7, side="left"), 2)
        self.assertEqual(pulse.evaluate(15.7), 0)
        self.assertAlmostEqual(pulse.integral(5, 6), 1.4)
        self.assertEqual(pulse.integral(5.3, 5.3), 0)

    def test_interval_average_preserves_each_partial_and_total_amount(self):
        forcing = Forcing([0, 5.3, 15.7, 25.5], [0, 2, 3], [0, 2, 0])
        for dt in (2, 1, 0.5, 0.25, 0.125, 7.4, 100):
            with self.subTest(dt=dt):
                average = interval_average(forcing, dt)
                self.assertEqual(average.horizon, forcing.horizon)
                self.assertEqual(average.left, average.right)
                self.assertAlmostEqual(average.integral(), forcing.integral(), places=12)
                for start, stop in zip(average.edges, average.edges[1:]):
                    self.assertAlmostEqual(
                        average.integral(start, stop), forcing.integral(start, stop), places=12
                    )

    def test_source_interpolant_and_roundtrip(self):
        source = from_source_samples([0, 2, 5], [1, 3, 0])
        self.assertEqual(source.integral(), 8.5)
        self.assertEqual(source.evaluate(3), 2)
        self.assertEqual(Forcing(**source.to_dict()), source)

    def test_inputs_are_immutable_and_do_not_alias_mutable_arguments(self):
        values = [1]
        forcing = Forcing([0, 1], values, values)
        values[0] = 9
        self.assertEqual(forcing.evaluate(0.5), 1)
        with self.assertRaises(FrozenInstanceError):
            forcing.edges = (0, 2)

    def test_invalid_or_nonfinite_inputs_and_wrong_units(self):
        cases = [
            dict(edges=[1, 2], left=[1], right=[1]),
            dict(edges=[0, 0], left=[1], right=[1]),
            dict(edges=[0, 2, 1], left=[1, 1], right=[1, 1]),
            dict(edges=[0, float("inf")], left=[1], right=[1]),
            dict(edges=[0, 1], left=[float("nan")], right=[1]),
            dict(edges=[0, 1], left=[-1], right=[1]),
            dict(edges=[0, 1], left=[], right=[1]),
            dict(edges=[0, 1], left=[True], right=[1]),
            dict(edges=[0, 1], left=["1"], right=[1]),
            dict(edges=[0, 1], left=[1], right=[1], units="ug/min"),
        ]
        for case in cases:
            with self.subTest(case=case), self.assertRaises(ValueError):
                Forcing(**case)
        with self.assertRaises(ValueError):
            from_source_samples([0, 1], [1])

    def test_no_extrapolation_or_invalid_integrals(self):
        source = Forcing([0, 1], [1], [1])
        for time in (-1, float("nan"), float("inf"), 1.00001):
            with self.subTest(time=time), self.assertRaises(ValueError):
                source.evaluate(time)
        for limits in ((-1, 1), (0, 2), (0.5, 0.2)):
            with self.subTest(limits=limits), self.assertRaises(ValueError):
                source.integral(*limits)
        for dt in (0, -1, float("nan"), float("inf")):
            with self.subTest(dt=dt), self.assertRaises(ValueError):
                interval_average(source, dt)


class NativeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.params, cls.identity = native.load()

    def setUp(self):
        self.state = np.asarray(self.params.iloc[2:15], dtype=float)
        self.action = Action(CHO=0, insulin=0)

    def test_verified_native_revision_hashes_and_parameter_identity(self):
        self.assertEqual(self.identity["upstream_revision"], PROTOCOL["upstream"]["revision"])
        for key in ("patient_file_sha256", "parameter_file_sha256"):
            self.assertEqual(self.identity[key], PROTOCOL["upstream"][key])
        self.assertEqual(self.identity["kinetic_parameters"]["BW"], 102.32)
        self.assertEqual(self.identity["kinetic_parameters"]["Vi"], float(self.params.Vi))

    def test_pin_and_hash_failures_are_rejected(self):
        for key in ("revision", "patient_file_sha256", "parameter_file_sha256"):
            bad = {**PROTOCOL, "upstream": {**PROTOCOL["upstream"], key: "invalid"}}
            fake = SimpleNamespace(read_text=lambda: json.dumps(bad))
            with self.subTest(key=key), patch.object(native, "PROTOCOL_PATH", fake):
                with self.assertRaises(ValueError):
                    native.load()
        with self.assertRaises(ValueError):
            native.load("adult#002")

    def test_wrapper_changes_only_requested_native_derivative(self):
        original = T1DPatient.model(0, self.state, self.action, self.params, 0, 0)
        for route, index in (("liver", 9), ("peripheral", 5)):
            with self.subTest(route=route):
                actual = native.derivative(
                    0, self.state, self.action, self.params, q=2, route=route
                )
                expected = original.copy()
                expected[index] += 2
                np.testing.assert_array_equal(actual, expected)
                zero = native.derivative(0, self.state, self.action, self.params, q=0, route=route)
                np.testing.assert_array_equal(zero, original)

    def test_native_guard_owns_negative_and_zero_compartments(self):
        for route, index in (("liver", 9), ("peripheral", 5)):
            for value in (-1, 0):
                state = self.state.copy()
                state[index] = value
                original = T1DPatient.model(0, state, self.action, self.params, 0, 0)
                actual = native.derivative(0, state, self.action, self.params, q=2, route=route)
                expected = original.copy()
                expected[index] += 2 if value == 0 else 0
                np.testing.assert_array_equal(actual, expected)

    def test_no_added_subcutaneous_absorption_or_instant_extra_extraction(self):
        state = self.state.copy()
        state[[5, 9, 10, 11]] = 0
        for route, expected in (("liver", [0, 1]), ("peripheral", [1, 0])):
            with self.subTest(route=route):
                rate = native.derivative(0, state, self.action, self.params, q=1, route=route)
                np.testing.assert_array_equal(rate[[5, 9]], expected)
                np.testing.assert_array_equal(rate[[10, 11]], [0, 0])

    def test_solver_uses_original_derivative_and_no_exogenous_action(self):
        forcing = Forcing([0, 1], [1], [1])
        original = T1DPatient.model
        seen = []

        def observe(t, state, action, params, last_Qsto, last_foodtaken):
            seen.append((action.insulin, state[10], state[11]))
            return original(t, state, action, params, last_Qsto, last_foodtaken)

        with patch.object(T1DPatient, "model", side_effect=observe):
            native.simulate([0, 1], self.params, forcing, "liver", SETTINGS)
        self.assertGreater(len(seen), 1)
        self.assertTrue(all(values == (0, 0, 0) for values in seen))

    def test_non_grid_pulse_amount_and_mass_balance(self):
        forcing = Forcing([0, 5.3, 15.7, 20], [0, 2, 0], [0, 2, 0])
        times = [0, 5, 5.3, 6, 15.7, 20]
        for route in ("liver", "peripheral"):
            actual = native.simulate(times, self.params, forcing, route, SETTINGS)
            np.testing.assert_allclose(np.sum(actual[:, :4], axis=1), actual[:, 4], atol=1e-10)
            self.assertAlmostEqual(actual[-1, 4], 20.8, places=10)
            np.testing.assert_array_equal(actual[:3], np.zeros((3, 5)))
            self.assertGreater(actual[3, 0], 0)

    def test_short_source_segments_bound_all_solver_initial_probes(self):
        times = np.linspace(0, 100, 401)
        forcing = from_source_samples(times, 3 * np.exp(-times / 30))
        original = native.solve_ivp
        first_steps = []

        def observed(*args, **kwargs):
            first_steps.append(kwargs["first_step"])
            return original(*args, **kwargs)

        with patch.object(native, "solve_ivp", side_effect=observed):
            actual = native.simulate(times, self.params, forcing, "liver", SETTINGS)
        self.assertEqual(len(first_steps), 400)
        self.assertTrue(all(0 < value <= 0.25 for value in first_steps))
        self.assertTrue(np.all(np.isfinite(actual)))
        self.assertAlmostEqual(actual[-1, 4], forcing.integral(), places=10)

    def test_whole_native_zero_extension_fresh_and_reset(self):
        result = native.zero_extension(self.params, PROTOCOL)
        self.assertTrue(result["passed"])
        self.assertTrue(result["solver_successful"])
        self.assertEqual(result["samples"], 61)
        self.assertEqual(result["states_per_sample"], 13)
        for key in (
            "derivative_max_error",
            "trajectory_max_error",
            "fresh_max_error",
            "reset_max_error",
        ):
            self.assertEqual(result[key], 0)

    def test_rejects_invalid_time_grids_routes_and_solver_settings(self):
        forcing = Forcing([0, 1], [1], [1])
        for times in ([0], [0, 0], [0, 0.5], [0, 2], [0.1, 1], [0, np.nan], [[0, 1]]):
            with self.subTest(times=times), self.assertRaises(ValueError):
                native.simulate(times, self.params, forcing, "liver", SETTINGS)
        for change in (
            {"method": "bad"},
            {"rtol": 0},
            {"atol": -1},
            {"max_step": np.inf},
            {"rtol": 1},
            {"unknown": 2},
        ):
            with self.subTest(change=change), self.assertRaises(ValueError):
                native.simulate([0, 1], self.params, forcing, "liver", {**SETTINGS, **change})
        with self.assertRaises(ValueError):
            native.simulate([0, 1], self.params, forcing, "portal_magic", SETTINGS)
        for value in (-1, np.nan, np.inf, True):
            with self.subTest(value=value), self.assertRaises(ValueError):
                native.derivative(0, self.state, self.action, self.params, q=value)

    def test_failed_incomplete_or_nonfinite_solver_cannot_pass(self):
        forcing = Forcing([0, 1], [1], [1])
        results = [
            SimpleNamespace(success=False, message="selected failure"),
            SimpleNamespace(success=True, y=np.zeros((5, 0)), t=np.array([]), message="truncated"),
            SimpleNamespace(
                success=True, y=np.zeros((5, 1)), t=np.array([0.9]), message="wrong time"
            ),
            SimpleNamespace(
                success=True, y=np.full((5, 1), np.nan), t=np.array([1]), message="NaN"
            ),
        ]
        for result in results:
            with (
                self.subTest(message=result.message),
                patch.object(native, "solve_ivp", return_value=result),
            ):
                with self.assertRaises(RuntimeError):
                    native.simulate([0, 1], self.params, forcing, "liver", SETTINGS)

    def test_whole_native_solver_failure_is_checked_after_step(self):
        fake = SimpleNamespace(
            state=np.zeros(13), t=0, _odesolver=SimpleNamespace(successful=lambda: False)
        )
        fake.step = lambda action: setattr(fake, "t", 1)
        with self.assertRaises(RuntimeError):
            native._native_trajectory(fake, self.action, 1)


class RunnerLifecycleTests(unittest.TestCase):
    def setUp(self):
        from experiments.m4.kinetic_inlet import run

        self.run = run
        self.temp = TemporaryDirectory(prefix=".bc002-test-", dir=Path(__file__).parent)
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.protocol_path = self.root / "protocol.json"
        self.protocol_path.write_text(json.dumps(PROTOCOL))
        self.source = self.root / "invalid-source"
        self.source.mkdir()
        (self.source / "manifest.json").write_text(
            json.dumps(
                {
                    "schema": "m4-beta-cell-run/1",
                    "status": "failed",
                    "files": {},
                }
            )
        )

    def failed_manifest(self, output, error_type):
        manifest = json.loads((output / "manifest.json").read_text())
        self.assertEqual(manifest["status"], "failed")
        self.assertEqual(manifest["error"]["type"], error_type)
        self.assertIn("protocol.json", manifest["files"])
        self.assertIn("source-native.py", manifest["files"])
        for name, expected_hash in manifest["files"].items():
            self.assertEqual(self.run.digest(output / name), expected_hash)
        self.assertFalse((output / "report.json").exists())
        return manifest

    def test_invalid_configuration_preserves_requested_protocol_and_error(self):
        self.protocol_path.write_text(json.dumps({**PROTOCOL, "horizon_min": -1}))
        output = self.root / "invalid-config"
        with self.assertRaises(ValueError):
            self.run.execute(self.protocol_path, self.source, output)
        self.failed_manifest(output, "ValueError")
        archived = json.loads((output / "protocol.json").read_text())
        self.assertEqual(archived["horizon_min"], -1)

    def test_supplied_protocol_native_identity_mismatch_is_rejected(self):
        for field in ("revision", "patient_file_sha256", "parameter_file_sha256"):
            bad_protocol = {**PROTOCOL, "upstream": {**PROTOCOL["upstream"], field: "wrong-pin"}}
            self.protocol_path.write_text(json.dumps(bad_protocol))
            output = self.root / f"mismatched-{field}"
            with self.subTest(field=field), patch.object(self.run, "source_input") as source:
                with self.assertRaisesRegex(ValueError, "Declared upstream identity"):
                    self.run.execute(self.protocol_path, self.source, output)
                source.assert_not_called()
            manifest = self.failed_manifest(output, "ValueError")
            self.assertIn("Declared upstream identity", manifest["error"]["message"])
            archived = json.loads((output / "protocol.json").read_text())
            self.assertEqual(archived["upstream"][field], "wrong-pin")

    def test_unusable_source_archive_fails_before_any_simulation(self):
        output = self.root / "invalid-source-attempt"
        with patch.object(self.run, "simulate") as solve:
            with self.assertRaises(ValueError):
                self.run.execute(self.protocol_path, self.source, output)
        solve.assert_not_called()
        self.failed_manifest(output, "ValueError")
        self.assertTrue((output / "native-identity.json").is_file())

    def test_existing_destination_is_not_changed(self):
        output = self.root / "existing"
        output.mkdir()
        marker = output / "do-not-replace.txt"
        marker.write_bytes(b"previous attempt")
        with self.assertRaises(FileExistsError):
            self.run.execute(self.protocol_path, self.source, output)
        self.assertEqual(marker.read_bytes(), b"previous attempt")
        self.assertEqual(list(output.iterdir()), [marker])

    def fake_source(self, source, output, protocol, identity):
        forcing = Forcing([0, protocol["horizon_min"]], [0], [0])
        self.run.dump(output / "source-forcing.json", forcing.to_dict())
        return forcing

    def test_interruption_keeps_completed_case_and_marks_failed(self):
        output = self.root / "interrupted"
        calls = 0

        def partial_then_interrupt(times, *args):
            nonlocal calls
            calls += 1
            if calls == 2:
                raise KeyboardInterrupt("selected interruption after first case")
            return np.zeros((len(times), 5))

        with patch.object(self.run, "source_input", side_effect=self.fake_source):
            with patch.object(self.run, "simulate", side_effect=partial_then_interrupt):
                with self.assertRaises(KeyboardInterrupt):
                    self.run.execute(self.protocol_path, self.source, output)
        manifest = self.failed_manifest(output, "KeyboardInterrupt")
        self.assertIn("source-liver.csv", manifest["files"])
        self.assertNotIn("source-peripheral.csv", manifest["files"])
        self.assertIn("selected interruption", manifest["error"]["message"])

    def test_incomplete_solver_failure_is_not_recorded_as_success(self):
        output = self.root / "incomplete"
        with patch.object(self.run, "source_input", side_effect=self.fake_source):
            with patch.object(
                self.run, "simulate", side_effect=RuntimeError("incomplete native solve")
            ):
                with self.assertRaises(RuntimeError):
                    self.run.execute(self.protocol_path, self.source, output)
        manifest = self.failed_manifest(output, "RuntimeError")
        self.assertIn("incomplete native solve", manifest["error"]["message"])
        self.assertIn("source-forcing.json", manifest["files"])

    def test_failed_verification_preserves_measurements_and_case_traces(self):
        output = self.root / "failed-verification"
        failure = {"passed": False, "checks": {"selected_fault": {"passed": False}}}
        with patch.object(self.run, "source_input", side_effect=self.fake_source):
            with patch.object(self.run, "verify", return_value=failure):
                with self.assertRaises(RuntimeError):
                    self.run.execute(self.protocol_path, self.source, output)
        manifest = self.failed_manifest(output, "RuntimeError")
        self.assertEqual(json.loads((output / "verification.json").read_text()), failure)
        for name in ("source-liver", "source-peripheral", "matched-constant-liver", "zero-liver"):
            self.assertIn(f"{name}.csv", manifest["files"])


if __name__ == "__main__":
    unittest.main()
