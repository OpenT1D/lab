"""Independent small arithmetic fixtures and IV-001 artifact failure checks."""

import copy
import json
import tempfile
import unittest
from pathlib import Path

from experiments.m0.simglucose.recording import write_json
from experiments.m1.artifacts import strict_json
from experiments.verification.analysis import compare, read_run, summarize, validate_trace
from experiments.verification.campaign import schedule
from experiments.verification.common import configurations, meals, sha, validate
from experiments.verification.run import execute


class VerificationTests(unittest.TestCase):
    def test_bounded_schedule_and_invalid_combinations(self):
        self.assertEqual(len(schedule("pilot")), 12)
        self.assertEqual(len(schedule("numerical")), 80)
        for cfg in configurations():
            validate(cfg)
        for change in (
            {"profile": "adult#003"},
            {"seed": True},
            {"factor": True},
            {"factor": 0.1},
            {"warmup": None},
            {"mode": "unknown"},
            {"schema": None},
            {"extra": 1},
        ):
            with self.assertRaises(ValueError):
                validate(configurations()[0] | change)
        with self.assertRaises(ValueError):
            validate(configurations()[8] | {"controller": "pid"})

    def test_duration_weights_terminal_exclusion_and_no_data(self):
        cfg = configurations()[8]
        run = dict(
            config=cfg,
            status="failed",
            rows=[
                dict(time_min=t, glucose_mg_dl=g, delivered_u_h=u, intake_g_min=0)
                for t, g, u in ((1439, 69, 60), (1440.5, 180, 120), (1442, 250, 999))
            ],
        )
        got = summarize(run)
        self.assertEqual(got["observed_minutes"], 2)
        self.assertEqual(got["delivered_insulin_u"], 3.5)
        self.assertEqual(got["glucose"]["in_range_percent"], 75)
        self.assertEqual(got["glucose"]["below_70_percent"], 25)
        run["rows"] = run["rows"][:1]
        self.assertIsNone(summarize(run)["delivered_insulin_u"])

    def test_partial_fixed_input_and_cross_track_comparisons(self):
        cfg = configurations()[8]
        a = dict(
            config=cfg,
            status="failed",
            rows=[
                dict(time_min=t, glucose_mg_dl=g, delivered_u_h=60, intake_g_min=0)
                for t, g in ((1440, 100), (1441, 110), (1442, 120))
            ],
        )
        b = copy.deepcopy(a)
        b["rows"][0]["glucose_mg_dl"] = 102
        report = compare(a, b, fixed=True)
        self.assertEqual(report["mean_abs_glucose_mg_dl"], 1)
        self.assertEqual(report["max_abs_glucose_mg_dl"], 2)
        self.assertEqual(report["classification"], "inconclusive")
        b["rows"][0]["delivered_u_h"] = 61
        with self.assertRaisesRegex(ValueError, "delivery"):
            compare(a, b, fixed=True)
        b["config"] = configurations()[0]
        with self.assertRaisesRegex(ValueError, "pooling"):
            compare(a, b)

    def test_required_signals_and_overflow(self):
        cfg = configurations()[0]
        p = dict(
            start_min=0,
            end_min=3,
            glucose_mg_dl=120,
            raw_cgm_mg_dl=120,
            sensor_available=True,
            controller_cgm_mg_dl=120,
            controller_source_min=0,
            announced_g=0,
            true_meal_g=0,
            basal_u_min=0,
            bolus_u_min=0,
            delivered_u_min=0,
            terminal=False,
        )
        validate_trace([p], cfg, {"cgm_mg_dl": 120})
        for key in ("glucose_mg_dl", "delivered_u_min", "end_min", "controller_cgm_mg_dl"):
            for value in (None, True, "120", [], {}, float("inf"), float("nan")):
                with self.assertRaises(ValueError):
                    validate_trace([p | {key: value}], cfg, {"cgm_mg_dl": 120})
        with self.assertRaises(ValueError):
            strict_json('{"x":1e999}')
        with self.assertRaises(ValueError):
            strict_json('{"x":1,"x":2}')
        self.assertEqual(sum(g for _, g in meals(cfg)), 440)

    def test_failed_init_inventory_and_consumed_bytes(self):
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "failed"
            execute({"invalid": True}, output)
            run = read_run(output)
            self.assertEqual(run["status"], "failed")
            self.assertEqual(run["rows"], [])
            self.assertEqual(
                run["inputs_sha256"]["config.json"], sha((output / "config.json").read_bytes())
            )
            (output / "config.json").write_text("{}")
            with self.assertRaisesRegex(ValueError, "Artifact changed"):
                read_run(output)
            with self.assertRaises(FileExistsError):
                execute({}, output)

    def test_started_trace_identifies_unfinished_bytes(self):
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp)
            write_json(
                output / "manifest.json",
                {"schema": "iv001.run/1", "status": "started", "files_sha256": {}},
            )
            (output / "trace.jsonl").write_bytes(b'{"unfinished":')
            result = read_run(output)
            self.assertEqual(result["unfinished_bytes"], 14)
            self.assertEqual(result["inputs_sha256"]["trace.jsonl"], sha(b'{"unfinished":'))

    def test_completed_without_provenance_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp)
            files = {
                "config.json": json.dumps(configurations()[0]).encode(),
                "trace.jsonl": b"",
                "native.jsonl": b"",
                "run.log": b"",
            }
            for name, raw in files.items():
                (output / name).write_bytes(raw)
            write_json(
                output / "manifest.json",
                dict(
                    schema="iv001.run/1",
                    status="completed",
                    elapsed_seconds=1,
                    files_sha256={k: sha(v) for k, v in files.items()},
                ),
            )
            with self.assertRaisesRegex(ValueError, "source"):
                read_run(output)

    def test_missing_and_invalid_input_attempts_survive(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            execute(None, root / "missing", config_path=root / "absent.json")
            self.assertEqual(read_run(root / "missing")["status"], "failed")
            for i, value in enumerate((None, True, [], {}, float("inf"))):
                execute(value, root / str(i))
                self.assertEqual(read_run(root / str(i))["status"], "failed")

    def test_interrupted_fragment_keeps_valid_prefix_and_identity(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            raw = b'{"partial":'
            files = {
                "config.json": b"null",
                "trace.jsonl": raw,
                "native.jsonl": b"",
                "run.log": b"",
            }
            for name, data in files.items():
                (root / name).write_bytes(data)
            write_json(
                root / "manifest.json",
                dict(
                    schema="iv001.run/1",
                    status="interrupted",
                    error="SIGTERM",
                    elapsed_seconds=1,
                    files_sha256={k: sha(v) for k, v in files.items()},
                ),
            )
            result = read_run(root)
            self.assertEqual(result["unfinished_bytes"], len(raw))
            self.assertEqual(result["inputs_sha256"]["trace.jsonl"], sha(raw))
