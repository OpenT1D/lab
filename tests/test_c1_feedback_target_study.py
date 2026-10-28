"""C1/0.9 roster preservation and prespecified development gate."""

import tempfile
import unittest
from pathlib import Path

from experiments.c1.feedback_target_plan import DECLARATION, plan
from experiments.c1.feedback_target_study import (
    advancement_criteria,
    assess,
    reconstruct,
)
from experiments.m0.simglucose.recording import write_json


class FeedbackTargetStudyTest(unittest.TestCase):
    def test_unstarted_roster_retains_all_attempts_and_fails_screen(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "inputs").mkdir()
            (root / "attempts").mkdir()
            specification = plan()
            write_json(root / "plan.json", specification)
            (root / "settings.json").write_bytes(DECLARATION.read_bytes())
            for case in specification["cases"]:
                write_json(root / "inputs" / f"{case['id']}.json", case["config"])
            report = reconstruct(root)
            write_json(root / "report.json", report)
            result = assess(root)
            self.assertEqual(result["planned"], 48)
            self.assertEqual(len(result["pairs"]), 16)
            self.assertFalse(result["development_screen_pass"])
            self.assertTrue(all(not pair["complete"] for pair in result["pairs"]))
            with (root / "inputs" / f"{specification['cases'][0]['id']}.json").open("w") as file:
                file.write("{}")
            with self.assertRaises(ValueError):
                reconstruct(root)

    def test_b_and_a_gates_keep_equality_and_strict_b_benefit_distinct(self):
        delta = {
            "in_70_180_percent": 0,
            "below_70_percent": 0,
            "below_54_percent": 0,
            "above_250_percent": 0,
        }
        self.assertFalse(all(advancement_criteria("B", delta).values()))
        self.assertTrue(all(advancement_criteria("A", delta).values()))
        self.assertTrue(all(advancement_criteria("B", dict(delta, in_70_180_percent=0.2)).values()))
        self.assertFalse(
            all(
                advancement_criteria(
                    "B", dict(delta, in_70_180_percent=0.2, below_54_percent=0.2)
                ).values()
            )
        )
        self.assertFalse(all(advancement_criteria("A", dict(delta, below_70_percent=0.2)).values()))


if __name__ == "__main__":
    unittest.main()
