"""Failure and recording tests using synthetic traces, not model validity tests."""

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import development
import numpy as np
import pandas as pd
import run


class ReferenceTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.path = self.root / "trace.csv"
        self.frame = pd.DataFrame(
            100.0,
            index=pd.date_range(run.CONFIG["start"], periods=481, freq="3min"),
            columns=["BG", "CGM", "CHO", "insulin", "LBGI", "HBGI", "Risk"],
        )
        self.frame.index.name = "Time"
        self.frame.CHO = 0.0
        self.frame.insulin = 0.01
        for hour, grams in run.CONFIG["meals_hours_grams"]:
            self.frame.iloc[int(hour * 20), 2] = grams / 3
        self.frame.iloc[-1, [2, 3]] = np.nan
        self.save()

    def save(self):
        self.frame.to_csv(self.path)

    def test_development_probe_rejects_evaluation_profiles(self):
        settings = run.json.loads((run.HERE / "protocol-settings.json").read_text())
        development.validate_settings(settings)
        settings["development_profiles"].append("adult#003")
        with self.assertRaisesRegex(ValueError, "development profiles"):
            development.validate_settings(settings)

    def test_duration_and_action_amounts(self):
        summary = run.validate(self.path)
        self.assertEqual(summary["meal_total_g"], 220)
        self.assertAlmostEqual(summary["delivered_insulin_U"], 14.4)

    def test_missing_output(self):
        with self.assertRaises(FileNotFoundError):
            run.validate(self.root / "absent.csv")

    def test_nonfinite_state_and_nonterminal_action(self):
        for column in ["BG", "insulin"]:
            with self.subTest(column=column):
                original = self.frame.iloc[4][column]
                self.frame.loc[self.frame.index[4], column] = np.nan
                self.save()
                with self.assertRaisesRegex(ValueError, "Non-finite"):
                    run.validate(self.path)
                self.frame.loc[self.frame.index[4], column] = original

    def test_wrong_cadence_and_meal(self):
        self.frame.index = self.frame.index + pd.Timedelta(minutes=1)
        self.save()
        with self.assertRaisesRegex(ValueError, "timestamps"):
            run.validate(self.path)
        self.frame.index = self.frame.index - pd.Timedelta(minutes=1)
        self.frame.iloc[140, 2] = 0
        self.save()
        with self.assertRaisesRegex(ValueError, "Meal events"):
            run.validate(self.path)

    def test_different_valid_glucose_is_reported_not_accepted(self):
        original = self.root / "original.csv"
        original.write_bytes(self.path.read_bytes())
        self.frame.iloc[2, 0] += 1.0
        self.save()
        with self.assertRaisesRegex(ValueError, "Replay differs"):
            run.compare(original, self.path)
        report = run.compare(original, self.path, report_only=True)
        self.assertFalse(report["exact_numeric_replay"])
        self.assertFalse(report["tolerance_applied"])
        self.assertEqual(report["max_absolute_by_column"]["BG"], 1.0)

    def test_historical_baseline_rejects_identical_wrong_replays(self):
        context = {"platform_key": "test", "lock_sha256": "locked"}
        baseline = {
            "environments": {
                "test": {"output_sha256": [run.digest(self.path)], "lock_sha256": "locked"}
            }
        }
        self.assertTrue(run.check_baseline(self.path, context, baseline)["matched"])
        self.frame["BG"] = 500
        self.frame.loc[self.frame.index[:-1], "insulin"] = 0
        self.save()
        self.assertTrue(run.compare(self.path, self.path)["exact_numeric_replay"])
        with self.assertRaisesRegex(ValueError, "Historical baseline"):
            run.check_baseline(self.path, context, baseline)
        with self.assertRaisesRegex(ValueError, "No reviewed baseline"):
            run.check_baseline(self.path, {"platform_key": "unknown"}, baseline)
        baseline["environments"]["test"]["output_sha256"] = [run.digest(self.path)]
        with self.assertRaisesRegex(ValueError, "lock_sha256"):
            run.check_baseline(self.path, {**context, "lock_sha256": "changed"}, baseline)

    def test_initialization_failure_never_reuses_previous_case_output(self):
        from simglucose.controller.pid_ctrller import PIDController

        output = self.root / "development"
        with patch.object(PIDController, "__init__", side_effect=RuntimeError("PID init failed")):
            with self.assertRaisesRegex(RuntimeError, "PID init failed"):
                development.execute(output)
        manifest = run.json.loads((output / "manifest.json").read_text())
        self.assertEqual([c["status"] for c in manifest["cases"]], ["completed", "failed"])
        self.assertFalse((output / "partial.csv").exists())
        self.assertFalse((output / "adult#001-pid").exists())
        self.assertTrue((output / "adult#001-basal_bolus/adult#001.csv").exists())

    def test_overwrite_rejected(self):
        with self.assertRaises(FileExistsError):
            run.execute(self.root)
        self.assertTrue(self.path.exists())

    def test_failed_run_manifest_and_partial_output(self):
        from simglucose.simulation.sim_engine import SimObj

        with patch.object(SimObj, "simulate", side_effect=RuntimeError("injected failure")):
            with self.assertRaisesRegex(RuntimeError, "injected failure"):
                run.execute(self.root / "failed")
        manifest = run.json.loads((self.root / "failed/manifest.json").read_text())
        self.assertEqual(manifest["status"], "failed")
        self.assertTrue((self.root / "failed/first/recording.json").exists())
        self.assertIn("injected failure", (self.root / "failed/failure.log").read_text())


if __name__ == "__main__":
    unittest.main()
