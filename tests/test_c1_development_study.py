"""Known-case study declarations and action/low timing need no simulator."""

import json
import tempfile
import unittest
from pathlib import Path

from experiments.c1.development_study import _diagnostic, plan, reconstruct
from experiments.m0.simglucose.recording import write_json


class C1KnownDevelopmentTest(unittest.TestCase):
    def test_unstarted_plan_retains_all_64_cases_in_denominator(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "inputs").mkdir()
            (root / "attempts").mkdir()
            specification = plan()
            write_json(root / "plan.json", specification)
            for case in specification["cases"]:
                write_json(root / "inputs" / f"{case['id']}.json", case["config"])
            result = reconstruct(root)
            self.assertEqual(result["planned"], 64)
            self.assertEqual({row["status"] for row in result["cases"]}, {"attempt_unrecorded"})
            self.assertTrue(all(pair["delta_percent_points"] is None for pair in result["paired"]))

    def test_roster_is_complete_and_adjustment_changes_one_setting(self):
        cases = plan()["cases"]
        self.assertEqual(len(cases), 64)
        self.assertEqual(len({case["id"] for case in cases}), 64)
        self.assertEqual(
            {case["method"] for case in cases},
            {"basal_bolus", "trend_overlay", "bounded_pid", "trend_overlay_high_target"},
        )
        by_id = {case["id"]: case for case in cases}
        for profile in ("adult#001", "adult#002"):
            for seed in (101, 102):
                for condition in "ABCD":
                    stem = f"{profile}-{seed}-{condition}"
                    regular = by_id[f"{stem}-trend_overlay"]["config"]
                    adjusted = by_id[f"{stem}-trend_overlay_high_target"]["config"]
                    self.assertEqual(regular["settings"]["target_mg_dl"], 140)
                    self.assertEqual(adjusted["settings"]["target_mg_dl"], 180)
                    self.assertEqual(
                        {k: v for k, v in regular["settings"].items() if k != "target_mg_dl"},
                        {k: v for k, v in adjusted["settings"].items() if k != "target_mg_dl"},
                    )

    def test_diagnostic_separates_warmup_action_from_later_scored_action(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            overlay = root / "overlay"
            base = root / "base"
            overlay.mkdir()
            base.mkdir()
            commands = []
            rows = []
            base_rows = []
            for minute in range(0, 2880, 3):
                extra = 0.2 if minute in (1200, 1920) else 0.0
                commands.append({"time_min": minute, "extra_u_h": extra})
                base_rows.append(
                    {"start_min": minute, "glucose_mg_dl": 70.01 if minute == 1740 else 100}
                )
                rows.append(
                    {"start_min": minute, "glucose_mg_dl": 69.99 if minute == 1740 else 100}
                )
            for path, name, data in (
                (overlay, "commands.jsonl", commands),
                (overlay, "trace.jsonl", rows),
                (base, "trace.jsonl", base_rows),
            ):
                (path / name).write_text("".join(json.dumps(item) + "\n" for item in data))
            finding = _diagnostic(root, "overlay", "base")
            self.assertEqual(finding["added_below_70_starts_min"], [1740])
            self.assertEqual(finding["first_scored_extra_min"], 1920)
            self.assertEqual(finding["warmup_active_intervals"], 1)
            self.assertEqual(finding["scored_active_intervals"], 1)
            self.assertEqual(finding["removed_below_70_starts_min"], [])


if __name__ == "__main__":
    unittest.main()
