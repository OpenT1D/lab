import json
import subprocess
import sys
import tempfile
import unittest
from dataclasses import dataclass
from pathlib import Path

from experiments.m0.simglucose.recording import write_json
from experiments.m1.artifacts import digest, execute, read_run, strict_json
from experiments.m1.contracts import MEALS, Config, Row
from experiments.m1.report import paired


@dataclass
class Initial:
    time_min: int = 0
    glucose_mg_dl: float = 100
    cgm_mg_dl: float = 101
    true_meal_g: float = 0
    delivered_u_min: float = 0
    terminal: bool = False


def native_metadata(manifest):
    """Labeled synthetic provenance for injected test traces; no engine execution claim."""
    import hashlib

    mapping = {"synthetic-test-source.py": "a" * 64}
    manifest.update(
        upstream_revision="a" * 40,
        upstream_files_sha256=mapping,
        upstream_files_digest=hashlib.sha256(
            json.dumps(mapping, sort_keys=True, separators=(",", ":")).encode()
        ).hexdigest(),
        packages={
            k: "synthetic-fixture" for k in ("simglucose", "numpy", "scipy", "pandas", "setuptools")
        },
        effective_settings={
            "basal_u_min": 0.02,
            "CR_g_U": 10,
            "CF_mg_dl_U": 40,
            "controller_target_mg_dl": 140,
            "sensor": "synthetic",
            "pump": "synthetic",
            "sensor_seed": manifest["config"]["seed"],
            "patient_random_initialization": False,
            "patient_seed": None,
            "pid": {"P": 0.001, "I": 0.00001, "D": 0.001},
            "solver": {"method": "synthetic", "rtol": 1e-6, "atol": 1e-12},
            "pump_parameters": {
                "Name": "synthetic",
                "min_basal": 0,
                "min_bolus": 0,
                "max_basal": 30,
                "max_bolus": 30,
                "inc_basal": 0.05,
                "inc_bolus": 0.05,
                "sample_time": 1,
            },
        },
    )


def fixture(config, checkpoint, initial, output, manifest):
    (output / "native-diagnostic.csv").write_text("synthetic fixture; no native history\n")
    native_metadata(manifest)
    initial(Initial())
    held = 0
    for t in range(0, 2880, 3):
        present = not (config.condition == "D" and 2160 <= t + 3 < 2190)
        fraction = 1 if t < 1440 else {"A": 1, "B": 0, "C": 0.5, "D": 1}[config.condition]
        meal = dict(MEALS).get(t, 0)
        checkpoint(
            Row(t, t + 3, 100, 101, present, 101, held, meal * fraction, meal, 0.02, 0, 0.02, False)
        )
        if present:
            held = t + 3
    return "completed"


class Artifacts(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.config = self.root / "config.json"
        write_json(self.config, Config().to_dict())
        self.output = self.root / "run"

    def test_saved_fixture_and_overwrite(self):
        execute(self.config, self.output, _implementation=fixture)
        saved = read_run(self.output)
        self.assertEqual(saved["manifest"]["status"], "completed")
        self.assertEqual(saved["metrics"]["glucose"]["observed_minutes"], 1440)
        with self.assertRaises(FileExistsError):
            execute(self.config, self.output, _implementation=fixture)
        (self.output / "trace.jsonl").unlink()
        with self.assertRaises(FileNotFoundError):
            read_run(self.output)

    def test_missing_input_and_initialization_failure(self):
        self.config.unlink()
        with self.assertRaises(FileNotFoundError):
            execute(self.config, self.output, _implementation=fixture)
        saved = read_run(self.output)
        self.assertEqual(saved["manifest"]["status"], "failed")
        self.assertEqual(saved["metrics"]["completed_minutes"], 0)
        write_json(self.config, Config().to_dict())

        def fail(*_):
            raise RuntimeError("fresh initialization failed")

        other = self.root / "fresh"
        with self.assertRaises(RuntimeError):
            execute(self.config, other, _implementation=fail)
        self.assertEqual(read_run(other)["metrics"]["completed_minutes"], 0)

    def test_invalid_signal_preserves_valid_prefix_and_warnings(self):
        def fail(config, checkpoint, initial, output, manifest):
            native_metadata(manifest)
            import warnings

            initial(Initial())
            checkpoint(Row(0, 3, 100, 101, True, 101, 0, 0, 0, 0, 0, 0, False))
            warnings.warn("retained warning", stacklevel=1)
            checkpoint(Row(3, 6, float("nan"), 101, True, 101, 3, 0, 0, 0, 0, 0, False))

        with self.assertRaises(ValueError):
            execute(self.config, self.output, _implementation=fail)
        saved = read_run(self.output)
        self.assertEqual(saved["metrics"]["completed_minutes"], 3)
        self.assertEqual(saved["manifest"]["status"], "failed")
        self.assertIn("retained warning", (self.output / "warnings.json").read_text())

    def test_corruption_and_semantic_tampering(self):
        execute(self.config, self.output, _implementation=fixture)
        path = self.output / "trace.jsonl"
        rows = path.read_text().splitlines()
        first = json.loads(rows[0])
        first["controller_cgm_mg_dl"] = 555
        rows[0] = json.dumps(first)
        path.write_text("\n".join(rows) + "\n")
        with self.assertRaisesRegex(ValueError, "hash mismatch"):
            read_run(self.output)
        manifest = json.loads((self.output / "manifest.json").read_text())
        manifest["files_sha256"]["trace.jsonl"] = digest(path)
        write_json(self.output / "manifest.json", manifest)
        with self.assertRaisesRegex(ValueError, "available history"):
            read_run(self.output)

    def test_json_type_and_duplicate_rejection(self):
        for value in ('{"x": NaN}', '{"x": 1, "x": 2}', '{"x": Infinity}'):
            with self.assertRaises(ValueError):
                strict_json(value)

    def test_signals_timeout_and_hard_kill(self):
        script = """
import os, signal, sys, time
from dataclasses import dataclass
from experiments.m1.artifacts import execute
from experiments.m1.contracts import Row
@dataclass
class Initial:
    time_min: int = 0
    glucose_mg_dl: float = 100
    cgm_mg_dl: float = 101
    true_meal_g: float = 0
    delivered_u_min: float = 0
    terminal: bool = False
def run(config, checkpoint, initial, output, manifest):
    sys.path.insert(0, "tests")
    from test_m1_artifacts import native_metadata
    from experiments.m0.simglucose.recording import write_json
    native_metadata(manifest)
    write_json(output / "manifest.json", manifest)
    initial(Initial())
    checkpoint(Row(0, 3, 100, 101, True, 101, 0, 0, 0, 0, 0, 0, False))
    if sys.argv[3] == "timeout-after-checkpoint":
        # Exercise the production timeout handler after a guaranteed flushed checkpoint.
        signal.setitimer(signal.ITIMER_REAL, 0.05)
        time.sleep(10)
    elif sys.argv[3] == "timeout":
        time.sleep(10)
    else:
        os.kill(os.getpid(), getattr(signal, sys.argv[3]))
# Only the deadline case uses a short timeout; signal cases self-signal after a flush.
execute(sys.argv[1], sys.argv[2], 0.3 if sys.argv[3] == "timeout" else 30, _implementation=run)
"""
        for name in ("SIGTERM", "SIGINT", "timeout", "timeout-after-checkpoint", "SIGKILL"):
            output = self.root / name
            child = subprocess.run(
                [sys.executable, "-c", script, str(self.config), str(output), name],
                capture_output=True,
                timeout=10,
            )
            self.assertNotEqual(child.returncode, 0)
            saved = read_run(output)
            if name == "timeout":
                # The production deadline includes provenance/setup. On a loaded runner
                # it may expire before the injected implementation writes its first row.
                self.assertIn(saved["metrics"]["completed_minutes"], (0, 3))
                self.assertIn("timeout", saved["manifest"]["error"])
            else:
                self.assertEqual(saved["metrics"]["completed_minutes"], 3)
                if name == "timeout-after-checkpoint":
                    self.assertIn("timeout", saved["manifest"]["error"])
            self.assertEqual(
                saved["manifest"]["status"], "started" if name == "SIGKILL" else "interrupted"
            )
            if name == "SIGKILL":
                with (output / "trace.jsonl").open("a") as trace:
                    trace.write('{"unfinished":')
                self.assertTrue(read_run(output)["discarded_trailing_fragment"])

    def test_pairing_failures_seed_then_profile_weight(self):
        cases = []
        for profile, values in (("adult#001", (10, 30)), ("adult#002", (80, 100))):
            for seed, delta in zip((101, 102), values, strict=True):
                for controller in ("basal_bolus", "pid"):
                    cases.append(
                        {
                            "config": Config(profile, seed, controller).to_dict(),
                            "status": "completed",
                            "metrics": {
                                "glucose": {
                                    k: delta if controller == "pid" else 0
                                    for k in (
                                        "in_70_180_percent",
                                        "below_70_percent",
                                        "below_54_percent",
                                    )
                                }
                            },
                        }
                    )
        comparison = paired(cases, ("basal_bolus", "A"), ("pid", "A"))
        self.assertEqual(comparison["across_profiles"]["in_70_180_percent"]["median"], 55)
        cases[-1]["status"] = "failed"
        comparison = paired(cases, ("basal_bolus", "A"), ("pid", "A"))
        self.assertEqual(comparison["scheduled_pairs"], 4)
        self.assertEqual(len(comparison["excluded_pairs"]), 1)
        self.assertEqual(comparison["profiles"][1]["complete_pairs"], 1)

    def test_signal_between_disk_checkpoint_and_memory_accounting(self):
        def fail(config, checkpoint, initial, output, manifest):
            native_metadata(manifest)
            initial(Initial())
            checkpoint(Row(0, 3, 100, 101, True, 101, 0, 0, 0, 0, 0, 0, False))
            # Represent a completed disk write followed by interruption before callback return.
            with (output / "trace.jsonl").open("a") as trace:
                trace.write(
                    json.dumps(
                        {
                            "start_min": 3,
                            "end_min": 6,
                            "glucose_mg_dl": 100,
                            "raw_cgm_mg_dl": 101,
                            "sensor_available": True,
                            "controller_cgm_mg_dl": 101,
                            "controller_source_min": 3,
                            "announced_g": 0,
                            "true_meal_g": 0,
                            "basal_u_min": 0,
                            "bolus_u_min": 0,
                            "delivered_u_min": 0,
                            "terminal": False,
                        }
                    )
                    + "\n"
                )
                trace.write('{"partial":')
            raise KeyboardInterrupt()

        with self.assertRaises(KeyboardInterrupt):
            execute(self.config, self.output, _implementation=fail)
        saved = read_run(self.output)
        self.assertEqual(saved["manifest"]["completed_rows"], 2)
        self.assertEqual(saved["metrics"]["completed_minutes"], 6)
        self.assertTrue(saved["discarded_trailing_fragment"])

    def test_report_includes_unattempted_and_reconstructs(self):
        from experiments.m1.report import write_report

        study = self.root / "study"
        study.mkdir()
        cases = []
        for controller in ("basal_bolus", "pid"):
            for condition in "ABCD":
                config = Config(controller=controller, condition=condition)
                identifier = f"{controller}-{condition}"
                cases.append({"id": identifier, "config": config.to_dict()})
        write_json(
            study / "study.json",
            {
                "schema": "opent1d.study/1",
                "status": "started",
                "purpose": "synthetic fixture",
                "cases": cases,
            },
        )
        result = write_report(study, self.root / "scheduled-report")
        self.assertEqual(result["status_counts"], {"scheduled": 8})
        for case in cases:
            write_json(self.config, case["config"])
            execute(self.config, study / case["id"], _implementation=fixture)
        first = self.root / "first-report"
        second = self.root / "second-report"
        write_report(study, first)
        write_report(study, second)
        for name in ("report.json", "report.md"):
            self.assertEqual((first / name).read_bytes(), (second / name).read_bytes())
        with self.assertRaises(FileExistsError):
            write_report(study, second)
