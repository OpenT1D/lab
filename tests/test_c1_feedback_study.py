"""Simulator-free C1/0.7 roster, native-audit and reconstruction checks."""

import tempfile
import unittest
from pathlib import Path

from experiments.c1.feedback import FeedbackController
from experiments.c1.feedback_study import plan, reconstruct
from experiments.c1.report import replay_commands, validate_command
from experiments.c1.simglucose_dev import Config
from experiments.m0.simglucose.recording import write_json
from experiments.m1.contracts import Row


class FeedbackStudyTest(unittest.TestCase):
    def test_matched_single_attempt_roster(self):
        specification = plan()
        cases = specification["cases"]
        self.assertEqual(len(cases), 48)
        self.assertEqual(len({case["id"] for case in cases}), 48)
        self.assertEqual(specification["max_setting_attempts_per_method"], 1)
        by_id = {case["id"]: case for case in cases}
        for profile in ("adult#001", "adult#002"):
            for seed in (101, 102):
                for condition in "ABCD":
                    stem = f"{profile}-{seed}-{condition}"
                    candidate = by_id[f"{stem}-feedback_trend"]["config"]
                    comparator = by_id[f"{stem}-feedback_no_rise"]["config"]
                    self.assertEqual(Config.parse(candidate).method, "feedback_trend")
                    self.assertEqual(Config.parse(comparator).method, "feedback_no_rise")
                    for key, value in candidate["settings"].items():
                        self.assertEqual(
                            comparator["settings"][key],
                            0 if key == "rise_gain_u_h_per_mg_dl_min" else value,
                        )

    def test_no_unrecorded_case_gets_an_outcome(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "inputs").mkdir()
            (root / "attempts").mkdir()
            specification = plan()
            write_json(root / "plan.json", specification)
            source = (
                Path(__file__).resolve().parents[1] / "experiments/c1/feedback-development.json"
            )
            (root / "settings.json").write_bytes(source.read_bytes())
            for case in specification["cases"]:
                write_json(root / "inputs" / f"{case['id']}.json", case["config"])
            report = reconstruct(root)
            self.assertEqual(report["planned"], 48)
            self.assertTrue(all(row["status"] == "attempt_unrecorded" for row in report["cases"]))
            self.assertTrue(all(row["delta_percent_points"] is None for row in report["paired"]))

    def test_feedback_action_replay_detects_tampering(self):
        config = plan()["cases"][1]["config"]
        cfg = Config.parse(config)
        decision = FeedbackController(cfg.settings).command(
            time_min=0,
            glucose_mg_dl=160,
            source_time_min=0,
            available=True,
            base_u_h=1,
        )
        row = Row(0, 3, 160, 160, True, 160, 0, 0, 0, 1 / 60, 0, 1 / 60, False)
        command = {
            "time_min": 0,
            "controller_source_min": 0,
            "controller_cgm_mg_dl": 160,
            "sensor_available": True,
            "announced_g": 0,
            "base_basal_u_h": 1,
            "base_bolus_u_min": 0,
            "final_basal_u_h": decision.final_u_h,
            "final_bolus_u_min": 0,
            "raw_total_u_h": decision.raw_total_u_h,
            "requested_total_u_h": decision.requested_total_u_h,
            "correction_u_h": decision.correction_u_h,
            "integral_mg_dl_min": decision.integral_mg_dl_min,
            "rise_mg_dl_min": decision.rise_mg_dl_min,
            "integral_frozen": decision.integral_frozen,
            "total_clamped": decision.total_clamped,
            "slew_limited": decision.slew_limited,
            "reason": decision.reason,
        }
        validate_command(command, row, cfg)
        replay_commands([row], [command], cfg)
        with self.assertRaises(ValueError):
            validate_command(dict(command, final_bolus_u_min=0.01), row, cfg)
        with self.assertRaises(ValueError):
            replay_commands([row], [dict(command, integral_mg_dl_min=1)], cfg)
        with self.assertRaises(ValueError):
            validate_command(dict(command, total_clamped=True), row, cfg)
        mismatch = dict(config)
        mismatch["method"] = "feedback_no_rise"
        with self.assertRaises(ValueError):
            Config.parse(mismatch)


if __name__ == "__main__":
    unittest.main()
