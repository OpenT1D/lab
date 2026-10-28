"""The M1 integration smoke has a fixed, non-comparative roster."""

import json
import sys
import tempfile
import unittest
from dataclasses import dataclass, replace
from hashlib import sha256
from pathlib import Path
from types import ModuleType
from unittest.mock import patch

import experiments.c1.g2p2c_native_smoke as smoke
from experiments.c1.g2p2c_native_smoke import replay_commands, validated_plan
from experiments.m1.contracts import Action, Observation, Row


class G2P2CNativeSmokeTests(unittest.TestCase):
    def test_native_failure_keeps_partial_trace_and_refuses_replacement(self):
        @dataclass(frozen=True)
        class Snapshot:
            time_min: int = 0
            glucose_mg_dl: float = 119.0
            cgm_mg_dl: float = 118.0
            true_meal_g: float = 0.0
            delivered_u_min: float = 0.0
            terminal: bool = False

        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            plan_path = root / "plan.json"
            training_path = root / "training.json"
            output = root / "results/native"
            plan = {
                "source_commit": "pinned",
                "simglucose_commit": "m1-pin",
                "actor_sampling_seed": 24,
                "cases": [
                    {
                        "profile": "adult#001",
                        "seed": 101,
                        "condition": "D",
                        "output_directory": "results/native",
                    }
                ],
            }
            plan_path.write_text(json.dumps(plan) + "\n")
            training_path.write_text(
                json.dumps(
                    {"profiles": [{"name": "adult#001", "output_directory": "results/training"}]}
                )
            )
            source_report = {
                "g2p2c_source_commit": "pinned",
                "m1_simglucose_commit": "m1-pin",
            }
            trained_report = {"checkpoint_sha256": "a" * 64}
            basal = smoke.PROFILE_BASAL_U_MIN["adult#001"]

            class Actor:
                def reset(self):
                    pass

                def command(self, observation, announced_g):
                    return Action(basal, 0.0)

            def fail_after_one_interval(config, checkpoint, initial, *, controller):
                controller.reset()
                initial(Snapshot())
                action = controller.command(Observation(0, 118.0, 0, True), 0.0)
                checkpoint(
                    Row(
                        0,
                        3,
                        120.0,
                        119.0,
                        True,
                        118.0,
                        0,
                        0.0,
                        0.0,
                        action.basal_u_min,
                        action.bolus_u_min,
                        0.0,
                        False,
                    )
                )
                raise RuntimeError("native solver stopped")

            adapter = ModuleType("experiments.c1.g2p2c_policy_adapter")
            adapter.load_source_state_dict = lambda *args, **kwargs: Actor()
            simulation = ModuleType("experiments.m1.simulation")
            simulation.simulate = fail_after_one_interval
            with (
                patch.object(smoke, "ROOT", root),
                patch.object(smoke, "PLAN", plan_path),
                patch.object(smoke, "TRAINING_PLAN", training_path),
                patch.object(smoke, "validated_plan", return_value=plan),
                patch.object(smoke, "engine_audit", return_value=source_report),
                patch(
                    "experiments.c1.g2p2c_trained_preflight.audit",
                    return_value=trained_report,
                ),
                patch.dict(
                    sys.modules,
                    {
                        "experiments.c1.g2p2c_policy_adapter": adapter,
                        "experiments.m1.simulation": simulation,
                    },
                ),
            ):
                with self.assertRaisesRegex(RuntimeError, "native solver stopped"):
                    smoke.run(root, "adult#001")
                self.assertEqual(
                    json.loads((output / "failure.json").read_text()),
                    {"type": "RuntimeError", "message": "native solver stopped"},
                )
                self.assertEqual(len((output / "trace.jsonl").read_text().splitlines()), 1)
                self.assertTrue((output / "initial.json").is_file())
                self.assertFalse((output / "report.json").exists())
                with self.assertRaises(FileExistsError):
                    smoke.run(root, "adult#001")

    def test_saved_trace_reconstructs_without_native_simulation(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            plan_path = root / "plan.json"
            plan_path.write_text("{}\n")
            training_path = root / "training.json"
            training_path.write_text(
                json.dumps(
                    {"profiles": [{"name": "adult#001", "output_directory": "results/training"}]}
                )
            )
            output = root / "results/native"
            output.mkdir(parents=True)
            plan = {
                "cases": [
                    {
                        "profile": "adult#001",
                        "seed": 101,
                        "condition": "D",
                        "output_directory": "results/native",
                    }
                ],
                "actor_sampling_seed": 24,
                "planned_intervals_per_case": 2,
                "expected_masked_command_intervals": 1,
            }
            basal = smoke.PROFILE_BASAL_U_MIN["adult#001"]
            rows = [
                Row(0, 3, 120.0, 119.0, True, 118.0, 0, 12.0, 0.0, 0.1, 0.0, 0.3, False),
                Row(3, 6, 121.0, 120.0, False, 118.0, 0, 0.0, 0.0, basal, 0.0, 0.06, True),
            ]
            initial = {
                "time_min": 0,
                "glucose_mg_dl": 119.0,
                "cgm_mg_dl": 118.0,
                "true_meal_g": 0.0,
                "delivered_u_min": 0.0,
                "terminal": False,
            }
            source_report = {"source": "pinned"}
            trained_report = {"checkpoint_sha256": "a" * 64}
            for name, value in (
                ("native-smoke-plan.json", {}),
                ("source-preflight.json", source_report),
                ("trained-preflight.json", trained_report),
                ("initial.json", initial),
            ):
                (output / name).write_text(json.dumps(value) + "\n")
            (output / "trace.jsonl").write_text(
                "".join(json.dumps(row.__dict__) + "\n" for row in rows)
            )

            def digest(name):
                return sha256((output / name).read_bytes()).hexdigest()

            report = {
                "schema": "opent1d.c1.g2p2c-native-smoke/1",
                "profile": "adult#001",
                "seed": 101,
                "condition": "D",
                "plan_sha256": sha256(plan_path.read_bytes()).hexdigest(),
                "source_preflight_sha256": digest("source-preflight.json"),
                "trained_preflight_sha256": digest("trained-preflight.json"),
                "checkpoint_sha256": "a" * 64,
                "initial_snapshot_sha256": digest("initial.json"),
                "trace_sha256": digest("trace.jsonl"),
                "simulator_free_action_replay_intervals": 2,
                "native_status": "terminated",
                "intervals": 2,
                "endpoint_min": 6,
                "masked_command_intervals": 1,
                "masked_commands_equal_profile_basal": True,
                "max_basal_u_min": 0.1,
                "actions_bounded": True,
                "integration_gate_pass": False,
                "efficacy_metrics_computed": False,
                "eligible_m1_comparator": False,
            }
            (output / "report.json").write_text(json.dumps(report) + "\n")

            class Actor:
                def reset(self):
                    pass

                def command(self, observation, announced_g):
                    return Action(0.1 if observation.available else basal, 0.0)

            adapter = ModuleType("experiments.c1.g2p2c_policy_adapter")

            def fake_load(*args, **kwargs):
                return Actor()

            adapter.load_source_state_dict = fake_load
            with (
                patch.object(smoke, "ROOT", root),
                patch.object(smoke, "PLAN", plan_path),
                patch.object(smoke, "TRAINING_PLAN", training_path),
                patch.object(smoke, "validated_plan", return_value=plan),
                patch.object(smoke, "engine_audit", return_value=source_report),
                patch(
                    "experiments.c1.g2p2c_trained_preflight.audit",
                    return_value=trained_report,
                ),
                patch.dict(sys.modules, {"experiments.c1.g2p2c_policy_adapter": adapter}),
            ):
                self.assertEqual(smoke.verify_saved(root, "adult#001"), report)
                (output / "trace.jsonl").write_text(
                    "".join(
                        json.dumps((replace(rows[1], basal_u_min=0.03) if i else row).__dict__)
                        + "\n"
                        for i, row in enumerate(rows)
                    )
                )
                with self.assertRaisesRegex(ValueError, "minute 3"):
                    smoke.verify_saved(root, "adult#001")

    def test_simulator_free_replay_checks_saved_commands(self):
        rows = [
            Row(0, 3, 120.0, 119.0, True, 118.0, 0, 12.0, 0.0, 0.1, 0.0, 0.3, False),
            Row(3, 6, 121.0, 120.0, False, 118.0, 0, 0.0, 0.0, 0.02, 0.0, 0.06, False),
        ]

        class Actor:
            def reset(self):
                self.calls = []

            def command(self, observation, announced_g):
                self.calls.append((observation, announced_g))
                return Action(0.1 if observation.available else 0.02, 0.0)

        actor = Actor()
        self.assertEqual(replay_commands(rows, actor), 2)
        self.assertEqual(actor.calls[0][0].time_min, 0)
        self.assertEqual(actor.calls[0][1], 12.0)
        self.assertFalse(actor.calls[1][0].available)
        with self.assertRaisesRegex(ValueError, "minute 3"):
            replay_commands([rows[0], replace(rows[1], basal_u_min=0.03)], actor)

    def test_frozen_roster_and_no_efficacy_authorization(self):
        plan = validated_plan()
        self.assertEqual(
            [(case["profile"], case["seed"], case["condition"]) for case in plan["cases"]],
            [("adult#001", 101, "D"), ("adult#002", 101, "D")],
        )
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "plan.json"
            for changed in (
                dict(plan, expected_masked_command_intervals=9),
                dict(plan, efficacy_metrics_authorized=True),
                dict(plan, actor_sampling_seed=25),
            ):
                path.write_text(json.dumps(changed))
                with self.assertRaisesRegex(ValueError, "not bounded"):
                    validated_plan(path)


if __name__ == "__main__":
    unittest.main()
