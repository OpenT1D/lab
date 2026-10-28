"""Run only in the separate locked simglucose environment."""

import json
import tempfile
import unittest
from dataclasses import asdict
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import Mock, patch

import numpy as np
from simglucose.actuator.pump import InsulinPump
from simglucose.controller.basal_bolus_ctrller import BBController
from simglucose.controller.pid_ctrller import PIDController
from simglucose.patient.t1dpatient import T1DPatient
from simglucose.sensor.cgm import CGMSensor
from simglucose.simulation.env import Observation as NativeObservation
from simglucose.simulation.env import T1DSimEnv
from simglucose.simulation.scenario import CustomScenario
from simglucose.simulation.sim_engine import SimObj

from experiments.m1.adapter import Simglucose
from experiments.m1.contracts import MEALS, START, Action, Config, Observation
from experiments.m1.control import Controller, Information
from experiments.m1.simulation import simulate


class NativeTests(unittest.TestCase):
    def test_direct_adapter_exact_reset_and_meals(self):
        # Independent native construction and native SimObj loop, original M0 fixture.
        meals = [(7, 45), (12, 70), (16, 15), (18, 80), (23, 10)]
        direct = T1DSimEnv(
            T1DPatient.withName("adolescent#001"),
            CGMSensor.withName("Dexcom", seed=1),
            InsulinPump.withName("Insulet"),
            CustomScenario(datetime.fromisoformat(START), meals),
        )
        obj = SimObj(direct, BBController(), timedelta(days=1), animate=False)
        obj.simulate()
        expected = obj.results()
        adapter = Simglucose("adolescent#001", 1, [(h * 60, g) for h, g in meals])
        for _ in range(2):
            snap = adapter.reset()
            controller = BBController()
            controller.reset()
            for _ in range(480):
                command = controller.policy(
                    NativeObservation(snap.cgm_mg_dl),
                    0,
                    False,
                    sample_time=3,
                    patient_name="adolescent#001",
                    meal=snap.true_meal_g / 3,
                )
                snap = adapter.step(Action(float(command.basal), float(command.bolus)))
            self.assertTrue(expected.equals(adapter.native_history()))
            self.assertEqual(snap.time_min, 1440)
        self.assertEqual(float(expected.CHO.iloc[:-1].sum() * 3), 220)
        # Independently preserved M0 digests, never self-enrolled by this test.
        import hashlib

        baseline = json.loads(
            (Path(__file__).parents[1] / "m0/simglucose/baseline.json").read_text()
        )
        hashes = {h for env in baseline["environments"].values() for h in env["output_sha256"]}
        self.assertIn(hashlib.sha256(expected.to_csv().encode()).hexdigest(), hashes)

    def test_controller_exact_formula_and_information_allowlist(self):
        for kind in ("pid", "basal_bolus"):
            wrapped = Controller(Config(controller=kind))
            direct = (
                BBController(target=140)
                if kind == "basal_bolus"
                else PIDController(P=0.001, I=0.00001, D=0.001, target=140)
            )
            for t, g, meal in ((0, 100, 0), (3, 200, 45), (6, 100, 0)):
                actual = wrapped.command(Observation(t, g, t, True), meal)
                expected = direct.policy(
                    NativeObservation(g),
                    0,
                    False,
                    sample_time=3,
                    patient_name="adult#001",
                    meal=meal / 3,
                )
                self.assertEqual((actual.basal_u_min, actual.bolus_u_min), tuple(expected))
            wrapped.reset()
            direct.reset()
            self.assertEqual(
                wrapped.command(Observation(0, 100, 0, True), 0).basal_u_min,
                float(
                    direct.policy(
                        NativeObservation(100),
                        0,
                        False,
                        sample_time=3,
                        patient_name="adult#001",
                        meal=0,
                    ).basal
                ),
            )
            wrapped._native.policy = Mock(return_value=type(expected)(0, 0))
            wrapped.command(Observation(2160, 100, 2157, False), 70)
            self.assertEqual(
                set(wrapped._native.policy.call_args.kwargs),
                {"sample_time", "patient_name", "meal"},
            )

    def test_condition_order_missingness_and_once_only(self):
        for condition, total in (("A", 440), ("B", 220), ("C", 330), ("D", 440)):
            information = Information(condition)
            announcements, missing = 0, 0
            for t in range(0, 2881, 3):
                obs = information.observe(t, float(t + 100))
                announcements += information.announce(t)
                self.assertEqual(information.announce(t), 0)
                missing += not obs.available
                if condition == "D" and 2160 <= t < 2190:
                    self.assertEqual(obs.source_time_min, 2157)
                    self.assertEqual(obs.age_min, t - 2157)
                    self.assertEqual(obs.glucose_mg_dl, 2257)
            self.assertEqual(announcements, total)
            self.assertEqual(missing, 10 if condition == "D" else 0)
            with self.assertRaises(ValueError):
                information.observe(2880, 100)
            information.reset()
            self.assertEqual(information.observe(0, 100).age_min, 0)

    def test_sensor_generation_and_randomness(self):
        traces = []
        for condition, seed in (("A", 101), ("D", 101), ("A", 102)):
            engine = Simglucose("adult#001", seed)
            sensor = engine._env.sensor
            sensor.measure = Mock(wraps=sensor.measure)
            snap = engine.reset()
            initial_calls = sensor.measure.call_count
            information = Information(condition)
            information.observe(0, snap.cgm_mg_dl)
            values = []
            for _ in range(735):
                snap = engine.step(Action(0.02, 0))
                information.observe(snap.time_min, snap.cgm_mg_dl)
                values.append(snap.cgm_mg_dl)
            self.assertEqual(sensor.measure.call_count - initial_calls, 735 * 3)
            traces.append(values)
        self.assertEqual(traces[0], traces[1])
        self.assertNotEqual(traces[0], traces[2])

    def test_native_invalid_state_and_negative_pump_command(self):
        engine = Simglucose("adult#001", 101)
        with self.assertRaises(ValueError):
            engine.step(Action(0, 0))
        engine.reset()
        self.assertEqual(engine.step(Action(-1, -1)).delivered_u_min, 0)
        original = engine._env.step

        def invalid(action):
            result = original(action)
            result.info["patient_state"] = np.array([float("nan")] * 13)
            return result

        engine._env.step = invalid
        with self.assertRaises(ValueError):
            engine.step(Action(0, 0))

    def test_terminal_and_initialization_failure_have_no_stale_rows(self):
        from experiments.m1.adapter import Snapshot

        engine = Mock()
        engine.reset.return_value = Snapshot(0, 100, 100, 0, 0, False)
        engine.step.return_value = Snapshot(3, 9, 40, 0, 0, True)
        controller = Mock()
        controller.command.return_value = Action(0, 0)
        rows = []
        self.assertEqual(
            simulate(Config(), rows.append, lambda _: None, engine=engine, controller=controller),
            "terminated",
        )
        self.assertEqual(len(rows), 1)
        engine.reset.side_effect = RuntimeError("initialization")
        fresh = []
        with self.assertRaises(RuntimeError):
            simulate(Config(), fresh.append, lambda _: None, engine=engine, controller=controller)
        self.assertEqual(fresh, [])
        self.assertTrue(asdict(rows[0])["terminal"])

    def test_protocol_constants_remain_canonical(self):
        settings = json.loads(
            (Path(__file__).parents[1] / "m0/simglucose/protocol-settings.json").read_text()
        )
        self.assertEqual(
            MEALS,
            tuple(
                (d * 1440 + h * 60, g)
                for d in range(2)
                for h, g in settings["daily_meals_hours_grams"]
            ),
        )
        self.assertEqual(START, settings["start"])

    def test_full_development_reset_and_warmup_continuity(self):
        for kind in ("basal_bolus", "pid"):
            config = Config(controller=kind, condition="D")
            engine, controller = Simglucose(config.profile, config.seed), Controller(config)
            histories = []
            for _ in range(2):
                rows = []
                status = simulate(
                    config, rows.append, lambda _: None, engine=engine, controller=controller
                )
                self.assertEqual(status, "completed")
                self.assertEqual(len(rows), 960)
                self.assertEqual(sum(r.true_meal_g for r in rows), 440)
                self.assertEqual(sum(r.announced_g for r in rows), 440)
                self.assertEqual(sum(not r.sensor_available for r in rows), 10)
                self.assertEqual(rows[720].controller_source_min, 2157)
                if kind == "pid":
                    # Match native sequential addition order, not Python's sum reduction.
                    integrated = 0
                    for row in rows:
                        integrated += (row.controller_cgm_mg_dl - 140) * 3
                    self.assertEqual(controller._native.integrated_state, integrated)
                histories.append(rows)
            self.assertEqual(histories[0], histories[1])

    def test_native_numeric_strings_and_flags_rejected(self):
        from experiments.m1.adapter import native_number

        for bad in (True, np.bool_(True), "1", None, [], float("nan")):
            with self.assertRaises(ValueError):
                native_number(bad, "signal")

    def test_native_pid_development_stop_matches_adapter(self):
        config = Config(seed=102, controller="pid", condition="D")
        direct = T1DSimEnv(
            T1DPatient.withName(config.profile),
            CGMSensor.withName("Dexcom", seed=config.seed),
            InsulinPump.withName("Insulet"),
            CustomScenario(datetime.fromisoformat(START), [(t / 60, g) for t, g in MEALS]),
        )
        controller = PIDController(P=0.001, I=0.00001, D=0.001, target=140)
        observation, reward, done, info = direct.reset()
        count = 0
        while not done and count < 960:
            command = controller.policy(observation, reward, done, **info)
            observation, reward, done, info = direct.step(command)
            count += 1
        engine = Simglucose(config.profile, config.seed)
        rows = []
        status = simulate(config, rows.append, lambda _: None, engine=engine)
        self.assertTrue(done)
        self.assertEqual(status, "terminated")
        self.assertEqual(len(rows), count)
        self.assertTrue(direct.show_history().equals(engine.native_history()))
        self.assertEqual(rows[-1].end_min, 1077)
        self.assertLess(rows[-1].glucose_mg_dl, 10)

    def test_nonfinite_pid_state_rejected_even_with_finite_action(self):
        controller = Controller(Config(controller="pid"))
        for field in ("integrated_state", "prev_state"):
            controller.reset()
            setattr(controller._native, field, float("nan"))
            controller._native.policy = Mock(
                return_value=type("Action", (), {"basal": 0, "bolus": 0})()
            )
            with self.assertRaises(ValueError):
                controller.command(Observation(0, 100, 0, True), 0)

    def test_diagnostic_export_does_not_mask_simulation_failure(self):
        from experiments.m1 import runtime

        original = RuntimeError("primary simulation failure")
        manifest = {}
        with tempfile.TemporaryDirectory() as directory:
            with (
                patch.object(runtime, "simulate", side_effect=original),
                patch.object(
                    Simglucose, "native_history", side_effect=OSError("diagnostic export failure")
                ),
            ):
                with self.assertRaises(RuntimeError) as caught:
                    runtime.native_run(Config(), Mock(), Mock(), Path(directory), manifest)
        self.assertIs(caught.exception, original)
        self.assertEqual(manifest["diagnostic_error"], "OSError: diagnostic export failure")
