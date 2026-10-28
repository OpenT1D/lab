"""A completed actor is bound to the frozen plan before policy inference."""

import csv
import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from experiments.c1 import g2p2c_trained_preflight as trained


class G2P2CTrainedPreflightTests(unittest.TestCase):
    def test_trained_intake_requires_matching_actor_constructor(self):
        plan = json.loads(trained.PLAN.read_text())
        attempt = {"plan_sha256": "frozen-plan"}
        actor = {
            "profile": "adult#001",
            "actor_settings": {"planning_n_step": plan["planning_horizon_steps"]},
            "exact_constructor_tensor_and_forward_parity": True,
            "source_state_dict_weights_only_roundtrip": True,
            "initialized_actor_tensor_sha256": "a" * 64,
        }
        architecture = {
            "source_commit": plan["source_commit"],
            "training_plan_sha256": attempt["plan_sha256"],
            "profiles": [actor],
        }
        self.assertIs(
            trained.validate_architecture(plan, attempt, "adult#001", architecture), actor
        )
        changed = {
            **architecture,
            "profiles": [{**actor, "actor_settings": {"planning_n_step": 6}}],
        }
        with self.assertRaisesRegex(ValueError, "constructor parity"):
            trained.validate_architecture(plan, attempt, "adult#001", changed)
        with self.assertRaisesRegex(ValueError, "constructor parity"):
            trained.validate_architecture(plan, attempt, "adult#002", architecture)
        changed = {
            **architecture,
            "profiles": [{**actor, "source_state_dict_weights_only_roundtrip": False}],
        }
        with self.assertRaisesRegex(ValueError, "constructor parity"):
            trained.validate_architecture(plan, attempt, "adult#001", changed)

    def test_changed_checkpoint_or_incomplete_attempt_is_rejected(self):
        plan = json.loads(trained.PLAN.read_text())
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            output = root / plan["profiles"][0]["output_directory"]
            output.mkdir(parents=True)
            declaration = root / "plan.json"
            declaration.write_text(json.dumps(plan))
            (output / "training-plan.json").write_bytes(declaration.read_bytes())
            checkpoint = output / "actor-final-state-dict.pt"
            checkpoint.write_bytes(b"synthetic test checkpoint")
            source_preflight = output / "source-preflight.json"
            source_preflight.write_text(
                json.dumps(
                    {
                        "g2p2c_source_commit": plan["source_commit"],
                        "m1_simglucose_commit": plan["simglucose_commit"],
                        "training_engine_matches_m1_pin": True,
                    }
                )
            )
            profile = plan["profiles"][0]
            args = {
                "debug": 0,
                "sensor": "Dexcom",
                "patient_id": profile["source_patient_id"],
                "seed": profile["seed"],
                "feature_history": plan["feature_history_steps"],
                "calibration": plan["calibration_steps"],
                "max_test_epi_len": plan["max_test_episode_steps"],
                "max_epi_length": plan["max_training_episode_steps"],
                "planning_n_step": plan["planning_horizon_steps"],
                "n_training_workers": plan["training_workers"],
                "n_testing_workers": plan["testing_workers"],
                "n_features": 2,
                "use_meal_announcement": False,
                "use_carb_announcement": False,
                "use_tod_announcement": False,
                "expert_bolus": False,
                "expert_cf": False,
                "experiment_dir": str(output.resolve()),
            }
            (output / "args.json").write_text(json.dumps(args))
            with (output / "experiment_summary.csv").open("w") as stream:
                writer = csv.writer(stream)
                writer.writerow(("status", "rollout"))
                writer.writerow((1, 0))
                for index in range(plan["expected_final_rollout"] + 1):
                    writer.writerow((2 if index == plan["expected_final_rollout"] else 1, index))
            lock = root / "experiments/c1/g2p2c_training_source/uv.lock"
            lock.parent.mkdir(parents=True)
            lock.write_bytes(b"synthetic test lock")

            def digest(data):
                return hashlib.sha256(data).hexdigest()

            attempt = {
                "schema": "opent1d.c1.g2p2c-training-attempt/1",
                "mode": "full",
                "profile": "adult#001",
                "source_commit": plan["source_commit"],
                "simglucose_commit": plan["simglucose_commit"],
                "plan_sha256": digest(declaration.read_bytes()),
                "training_lock_sha256": digest(lock.read_bytes()),
                "source_preflight_sha256": digest(source_preflight.read_bytes()),
                "seed_before_actor_initialization": True,
                "torch_deterministic_algorithms": True,
                "m1_development_matrix_run": False,
                "source_completed": True,
                "completed_interactions": plan["expected_completed_interactions"],
                "checkpoint_sha256": digest(checkpoint.read_bytes()),
                "actor_tensor_sha256": "a" * 64,
            }
            (output / "attempt.json").write_text(json.dumps(attempt))
            with patch.object(trained, "ROOT", root), patch.object(trained, "PLAN", declaration):
                self.assertEqual(
                    trained.validate_attempt(plan, "adult#001", output)[1], checkpoint.resolve()
                )
                checkpoint.write_bytes(b"altered checkpoint")
                with self.assertRaisesRegex(ValueError, "checkpoint bytes changed"):
                    trained.validate_attempt(plan, "adult#001", output)
                checkpoint.write_bytes(b"synthetic test checkpoint")
                attempt["source_completed"] = False
                (output / "attempt.json").write_text(json.dumps(attempt))
                with self.assertRaisesRegex(ValueError, "full-run contract"):
                    trained.validate_attempt(plan, "adult#001", output)
                attempt["source_completed"] = True
                (output / "attempt.json").write_text(json.dumps(attempt))
                args["max_test_epi_len"] = 288
                (output / "args.json").write_text(json.dumps(args))
                with self.assertRaisesRegex(ValueError, "source arguments differ"):
                    trained.validate_attempt(plan, "adult#001", output)


if __name__ == "__main__":
    unittest.main()
