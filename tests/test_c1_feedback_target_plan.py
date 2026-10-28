"""The next C1 development budget is fixed before any new native scoring."""

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from experiments.c1 import feedback_target_plan


class FeedbackTargetPlanTest(unittest.TestCase):
    def test_exact_one_factor_matched_roster(self):
        result = feedback_target_plan.plan()
        self.assertEqual(len(result["cases"]), 48)
        self.assertEqual(len({item["id"] for item in result["cases"]}), 48)
        self.assertEqual(result["new_setting_attempts_per_feedback_method"], 1)
        self.assertEqual(result["cumulative_setting_attempts_per_feedback_method"], 2)
        by_id = {item["id"]: item for item in result["cases"]}
        for profile in ("adult#001", "adult#002"):
            for seed in (101, 102):
                for condition in "ABCD":
                    stem = f"{profile}-{seed}-{condition}"
                    candidate = by_id[f"{stem}-feedback_trend"]["config"]["settings"]
                    comparator = by_id[f"{stem}-feedback_no_rise"]["config"]["settings"]
                    self.assertEqual(candidate["target_mg_dl"], 140)
                    self.assertGreater(candidate["rise_gain_u_h_per_mg_dl_min"], 0)
                    self.assertEqual(
                        {k: v for k, v in candidate.items() if k != "rise_gain_u_h_per_mg_dl_min"},
                        {k: v for k, v in comparator.items() if k != "rise_gain_u_h_per_mg_dl_min"},
                    )
                    self.assertEqual(comparator["rise_gain_u_h_per_mg_dl_min"], 0)

    def test_second_parameter_change_is_rejected(self):
        declaration = json.loads(feedback_target_plan.DECLARATION.read_text())
        declaration["candidate_settings"]["kp_u_h_per_mg_dl"] *= 2
        with tempfile.TemporaryDirectory() as directory:
            file = Path(directory) / "altered.json"
            file.write_text(json.dumps(declaration))
            with patch.object(feedback_target_plan, "DECLARATION", file):
                with self.assertRaises(ValueError):
                    feedback_target_plan.plan()


if __name__ == "__main__":
    unittest.main()
