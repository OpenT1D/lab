"""Counterexamples for the new point metric and process artifact contract."""

import copy
import json
import tempfile
import unittest
from pathlib import Path

from experiments.m0.simglucose.recording import write_json
from experiments.m1.artifacts import digest, strict_json
from experiments.m2.analysis import read_run, summarize, validate_points
from experiments.m2.run import execute, validate_config

CFG = {
    "engine": "lt1_cambridge",
    "profile": "reference",
    "controller": "lt1_mpc",
    "condition": "A",
    "seed": 101,
}


def point(t, glucose=120, rate=1, raw=120, present=True):
    return {
        "time_min": t,
        "glucose_mg_dl": glucose,
        "delivered_u_h": rate,
        "raw_cgm_mg_dl": raw,
        "sensor_available": present,
    }


class M2Tests(unittest.TestCase):
    def test_amounts_variable_intervals_endpoints_and_unobserved_day(self):
        points = [point(1439, 69, 60), point(1440.5, 180, 120), point(1442, 250, 999)]
        metrics = summarize(points)
        self.assertEqual(metrics["observed_minutes"], 2)
        self.assertEqual(metrics["delivered_insulin_u"], 3.5)
        self.assertEqual(metrics["glucose"]["in_range_percent"], 75)
        self.assertEqual(metrics["glucose"]["below_70_percent"], 25)
        self.assertEqual(metrics["glucose"]["mean_mg_dl"], (69 * 0.5 + 180 * 1.5) / 2)
        self.assertIsNone(summarize(points[:1])["delivered_insulin_u"])
        self.assertIsNone(summarize([])["glucose"]["in_range_percent"])

    def test_sensor_missingness_is_not_held_controller_data(self):
        points = [point(1440, raw=100), point(1445, raw=200, present=False), point(1450, raw=150)]
        metrics = summarize(points)
        self.assertEqual(metrics["sensor"]["observed_minutes"], 5)
        self.assertEqual(metrics["sensor"]["mean_mg_dl"], 100)
        self.assertEqual(metrics["glucose"]["observed_minutes"], 10)

    def test_invalid_numeric_values_and_configuration(self):
        for value in (None, True, "1", float("inf"), float("nan"), {}, []):
            with self.subTest(value=value), self.assertRaises(ValueError):
                summarize([point(1440, glucose=value), point(1441)])
        for change in (
            {"seed": True},
            {"seed": 0},
            {"profile": "adult#001"},
            {"controller": "pid"},
            {"extra": 1},
        ):
            with self.assertRaises(ValueError):
                validate_config(CFG | change)
        for text in ('{"x":1e999}', '{"x":1,"x":2}'):
            with self.assertRaises(ValueError):
                strict_json(text)

    def test_failed_initialization_and_missing_input_are_retained(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            bad = root / "bad.json"
            bad.write_text(json.dumps(CFG | {"controller": "basal_bolus"}))
            for i, path in enumerate((bad, root / "absent.json")):
                out = root / str(i)
                with self.assertRaises((ValueError, FileNotFoundError)):
                    execute(path, out)
                result = read_run(out)
                self.assertEqual(result["manifest"]["status"], "failed")
                self.assertEqual(result["manifest"]["completed_rows"], 0)
                self.assertIsNone(result["metrics"]["delivered_insulin_u"])
                with self.assertRaises(FileExistsError):
                    execute(path, out)
                (out / "unlisted.log").touch()
                with self.assertRaisesRegex(ValueError, "inventory|uninventoried"):
                    read_run(out)

    def test_started_trace_identity_false_completion_and_missing_provenance(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            write_json(
                root / "manifest.json",
                {
                    "schema": "opent1d.cambridge/1",
                    "status": "started",
                    "config": None,
                    "completed_rows": 0,
                    "files_sha256": {},
                },
            )
            trace = root / "trace.jsonl"
            trace.write_bytes(b'{"partial":')
            first = read_run(root)
            trace.write_bytes(b'{"partial":1')
            second = read_run(root)
            self.assertNotEqual(first["input_sha256"], second["input_sha256"])
            self.assertTrue(second["discarded_trailing_fragment"])
            manifest = strict_json((root / "manifest.json").read_bytes())
            manifest.update(
                status="completed", elapsed_seconds=0, files_sha256={"trace.jsonl": digest(trace)}
            )
            write_json(root / "manifest.json", manifest)
            with self.assertRaises(ValueError):
                read_run(root)

    def test_observation_schema_and_information_constraints(self):
        good = {
            "time_min": 0,
            "controller_cgm_mg_dl": 120,
            "controller_source_min": 0,
            "new_announcements": [],
            "announced_history": {},
            "glucose_mg_dl": 120,
            "raw_cgm_mg_dl": 120,
            "sensor_available": True,
            "command_u_h": 1,
            "delivered_u_h": 1,
            "intake_g_min": 0,
            "true_meal_g": 0,
        }
        validate_points([good], CFG)
        for change in (
            {"raw_cgm_mg_dl": None},
            {"sensor_available": 1},
            {"controller_source_min": 1},
            {"announced_history": {"future": {}}},
            {"new_announcements": {}},
            {"true_meal_g": True},
        ):
            with self.assertRaises(ValueError):
                validate_points([good | change], CFG)
        missing = copy.copy(good)
        del missing["delivered_u_h"]
        with self.assertRaises(ValueError):
            validate_points([missing], CFG)
