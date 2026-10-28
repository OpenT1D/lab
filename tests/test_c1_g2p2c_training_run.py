"""Frozen training timing and non-destructive source execution boundary."""

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from experiments.c1 import g2p2c_training_run as training


class G2P2CTrainingRunTests(unittest.TestCase):
    def test_plan_rejects_changed_physical_day_or_interaction_total(self):
        original = json.loads(training.PLAN.read_text())
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "plan.json"
            for field, value in (
                ("max_test_episode_steps", 288),
                ("expected_completed_interactions", 800000),
                ("planning_horizon_steps", 6),
            ):
                plan = dict(original, **{field: value})
                path.write_text(json.dumps(plan))
                with self.assertRaisesRegex(ValueError, "physical-time mapping"):
                    training.validated_plan(path)

    def test_existing_output_is_rejected_before_source_training_import(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            output = root / "results" / "existing"
            output.mkdir(parents=True)
            plan = json.loads(training.PLAN.read_text())
            plan["profiles"][0]["output_directory"] = "results/existing"
            audit = {
                "g2p2c_source_commit": plan["source_commit"],
                "m1_simglucose_commit": plan["simglucose_commit"],
            }
            with (
                patch.object(training, "ROOT", root),
                patch.object(training, "validated_plan", return_value=plan),
                patch.object(training, "source_audit", return_value=audit),
                patch.object(training, "source_args") as source_args,
            ):
                with self.assertRaises(FileExistsError):
                    training.run(root / "source", "adult#001", mode="full")
                source_args.assert_not_called()


if __name__ == "__main__":
    unittest.main()
