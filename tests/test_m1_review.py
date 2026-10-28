"""Counterexamples missed by the initial M1 implementation and self-replay checks."""

import copy
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from test_m1_artifacts import fixture

from experiments.m0.simglucose.recording import write_json
from experiments.m1 import artifacts
from experiments.m1.artifacts import digest, execute, read_run, strict_json
from experiments.m1.contracts import Config
from experiments.m1.report import paired, reconstruct, render


class ReviewTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        self.config = self.root / "config.json"
        write_json(self.config, Config().to_dict())
        self.run = self.root / "run"
        execute(self.config, self.run, _implementation=fixture)
        self.original = strict_json((self.run / "manifest.json").read_bytes())

    def manifest(self, value):
        write_json(self.run / "manifest.json", value)

    def test_required_provenance_cannot_be_omitted_or_empty(self):
        for key in (
            "revision",
            "source_sha256",
            "python",
            "platform",
            "worktree_dirty",
            "upstream_revision",
            "upstream_files_sha256",
            "upstream_files_digest",
            "packages",
            "effective_settings",
        ):
            for invalid in (None, {}):
                with self.subTest(key=key, invalid=invalid):
                    m = copy.deepcopy(self.original)
                    m[key] = invalid
                    self.manifest(m)
                    with self.assertRaises(ValueError):
                        read_run(self.run)
        self.manifest(self.original)
        self.assertEqual(read_run(self.run)["manifest"]["status"], "completed")

    def test_metadata_types_and_configuration_ownership(self):
        for key, value in (
            ("completed_rows", True),
            ("elapsed_seconds", "1"),
            ("elapsed_seconds", -1),
            ("worktree_dirty", 0),
        ):
            m = copy.deepcopy(self.original)
            m[key] = value
            self.manifest(m)
            with self.assertRaises(ValueError):
                read_run(self.run)
        m = copy.deepcopy(self.original)
        m.update(status="failed", config=None, error="synthetic failure")
        self.manifest(m)
        with self.assertRaisesRegex(ValueError, "owning configuration"):
            read_run(self.run)

    def test_failed_trace_cannot_escape_inventory(self):
        m = copy.deepcopy(self.original)
        m.update(status="failed", error="synthetic failure")
        m["files_sha256"].pop("trace.jsonl")
        self.manifest(m)
        with self.assertRaisesRegex(ValueError, "inventory"):
            read_run(self.run)
        m = copy.deepcopy(self.original)
        self.manifest(m)
        (self.run / "untracked-output.txt").write_text("changed artifact set")
        with self.assertRaisesRegex(ValueError, "Uninventoried"):
            read_run(self.run)

    def test_all_json_numbers_and_warning_records_are_validated(self):
        for value in ('{"elapsed_seconds":1e999}', '{"nested":[-1e999]}'):
            with self.assertRaises(ValueError):
                strict_json(value)
        for value in (
            None,
            {},
            [None],
            [{"category": "Warning", "message": "test", "filename": "x", "line": True}],
        ):
            write_json(self.run / "warnings.json", value)
            m = copy.deepcopy(self.original)
            m["files_sha256"]["warnings.json"] = digest(self.run / "warnings.json")
            self.manifest(m)
            with self.assertRaises(ValueError):
                read_run(self.run)

    def test_unsealed_metrics_identify_the_actual_consumed_trace(self):
        m = copy.deepcopy(self.original)
        m.update(status="started", completed_rows=0, files_sha256={})
        self.manifest(m)
        first = read_run(self.run)
        trace = self.run / "trace.jsonl"
        trace.write_text(
            trace.read_text().replace('"glucose_mg_dl": 100,', '"glucose_mg_dl": 130,')
        )
        second = read_run(self.run)
        self.assertEqual(
            first["input_sha256"]["manifest.json"], second["input_sha256"]["manifest.json"]
        )
        self.assertNotEqual(
            first["input_sha256"]["trace.jsonl"], second["input_sha256"]["trace.jsonl"]
        )
        self.assertEqual(first["metrics"]["glucose"]["mean_mg_dl"], 100)
        self.assertEqual(second["metrics"]["glucose"]["mean_mg_dl"], 130)

    def test_concurrent_trace_change_and_symlink_are_rejected(self):
        original_validate = artifacts.validate_rows

        def changed(rows):
            with (self.run / "trace.jsonl").open("a") as trace:
                trace.write(" ")
            return original_validate(rows)

        with patch.object(artifacts, "validate_rows", changed):
            with self.assertRaisesRegex(ValueError, "changed during reconstruction"):
                read_run(self.run)
        target = self.run / "trace.jsonl"
        outside = self.root / "external-trace"
        target.rename(outside)
        target.symlink_to(outside)
        with self.assertRaisesRegex(ValueError, "symlink"):
            read_run(self.run)

    def test_protocol_changes_are_rejected_before_execution_and_on_read(self):
        protocol = artifacts.ROOT / "experiments/m0/simglucose/protocol-settings.json"
        read_bytes = Path.read_bytes
        altered = protocol.read_bytes().replace(b'"target": 140', b'"target": 150')
        self.assertNotEqual(altered, protocol.read_bytes())

        def read(path):
            return altered if path == protocol else read_bytes(path)

        implementation = Mock()
        with patch.object(Path, "read_bytes", read):
            with self.assertRaisesRegex(ValueError, "Protocol differs"):
                execute(self.config, self.root / "wrong-protocol", _implementation=implementation)
        implementation.assert_not_called()
        (self.run / "protocol-settings.json").write_bytes(altered)
        m = copy.deepcopy(self.original)
        m["files_sha256"]["protocol-settings.json"] = digest(self.run / "protocol-settings.json")
        self.manifest(m)
        with self.assertRaisesRegex(ValueError, "Saved protocol differs"):
            read_run(self.run)

    def test_unknown_and_false_study_completion_are_rejected(self):
        study = self.root / "study"
        study.mkdir()
        cases = []
        for controller in ("basal_bolus", "pid"):
            for condition in "ABCD":
                config = Config(controller=controller, condition=condition)
                identifier = f"{controller}-{condition}"
                write_json(self.config, config.to_dict())
                execute(self.config, study / identifier, _implementation=fixture)
                cases.append({"id": identifier, "config": config.to_dict()})
        schedule = {"schema": "opent1d.study/1", "purpose": "synthetic fixture", "cases": cases}
        for status in (None, "unknown", "finished_with_failures"):
            write_json(study / "study.json", dict(schedule, status=status))
            with self.assertRaises(ValueError):
                reconstruct(study)
        write_json(study / "study.json", dict(schedule, status="completed"))
        victim = study / cases[0]["id"] / "manifest.json"
        m = strict_json(victim.read_bytes())
        m.update(status="interrupted", error="synthetic interruption")
        write_json(victim, m)
        with self.assertRaisesRegex(ValueError, "completion contradicts"):
            reconstruct(study)

    def test_unobserved_day_and_unassessable_signs_are_explicit(self):
        cases = []
        for profile in ("adult#001", "adult#002"):
            for controller in ("basal_bolus", "pid"):
                cases.append(
                    {
                        "config": Config(profile=profile, controller=controller).to_dict(),
                        "status": "failed" if profile == "adult#001" else "completed",
                        "metrics": {
                            "glucose": {
                                k: 0
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
        self.assertIsNone(comparison["across_profiles"]["below_70_percent"]["sign_reversal"])
        from experiments.m1.metrics import summarize

        report = {
            "purpose": "fixture",
            "study_status": "started",
            "scheduled": 1,
            "status_counts": {"interrupted": 1},
            "comparisons": [comparison],
            "cases": [
                {
                    "id": "interrupted",
                    "status": "interrupted",
                    "metrics": summarize([]),
                    "elapsed_seconds": 1,
                    "error": "test interruption",
                }
            ],
        }
        rendered = render(report)
        self.assertIn(
            "| interrupted | interrupted | undefined | undefined | undefined | undefined | "
            "0 | 0 | 0 | 1 |",
            rendered,
        )
        self.assertIn("not assessable", rendered)
        self.assertIn("Observed scored min", rendered)

    def test_historical_reference_rejects_repeatably_wrong_output(self):
        from experiments.m1.historical import check_record

        expected = {
            "first": {
                "config": {"seed": 101},
                "status": "completed",
                "trace_sha256": "a" * 64,
                "initial_sha256": "d" * 64,
            },
            "second": {
                "config": {"seed": 102},
                "status": "terminated",
                "trace_sha256": "b" * 64,
                "initial_sha256": "e" * 64,
            },
        }
        baseline = {
            "cases": {
                k: {f: v for f, v in case.items() if f not in ("trace_sha256", "initial_sha256")}
                for k, case in expected.items()
            },
            "collections": [
                {
                    "name": "historical",
                    "origin": "synthetic labeled reference",
                    "outputs_sha256": {
                        k: {f: c[f] for f in ("trace_sha256", "initial_sha256")}
                        for k, c in expected.items()
                    },
                }
            ],
        }
        self.assertTrue(check_record(expected, baseline)["matched"])
        wrong = copy.deepcopy(expected)
        wrong["first"]["trace_sha256"] = "c" * 64
        repeated = copy.deepcopy(wrong)
        self.assertEqual(wrong, repeated)  # Self-replay would pass.
        with self.assertRaisesRegex(ValueError, "trajectories differ"):
            check_record(repeated, baseline)
        wrong = copy.deepcopy(expected)
        wrong["first"]["config"]["seed"] = 103
        with self.assertRaisesRegex(ValueError, "context differs"):
            check_record(wrong, baseline)

    def test_historical_collections_cannot_be_mixed(self):
        from experiments.m1.historical import check_record

        first = {
            k: {"trace_sha256": c * 64, "initial_sha256": c * 64}
            for k, c in (("a", "a"), ("b", "b"))
        }
        second = {
            k: {"trace_sha256": c * 64, "initial_sha256": c * 64}
            for k, c in (("a", "c"), ("b", "d"))
        }
        baseline = {
            "cases": {"a": {}, "b": {}},
            "collections": [
                {"name": "first", "origin": "synthetic", "outputs_sha256": first},
                {"name": "second", "origin": "synthetic", "outputs_sha256": second},
            ],
        }
        self.assertTrue(check_record(second, baseline)["matched"])
        with self.assertRaisesRegex(ValueError, "trajectories differ"):
            check_record({"a": first["a"], "b": second["b"]}, baseline)

    def test_verification_failure_is_recorded_before_replay(self):
        from experiments.m1.verify import verify

        output = self.root / "verification"
        with patch("experiments.m1.verify.check_historical", side_effect=ValueError("changed")):
            with patch("experiments.m1.verify.subprocess.run") as run:
                with self.assertRaisesRegex(ValueError, "changed"):
                    verify(self.root, output)
        run.assert_not_called()
        result = strict_json((output / "verification.json").read_bytes())
        self.assertEqual(result["status"], "failed")
        self.assertEqual(result["error"], "ValueError: changed")
        self.assertFalse(result["replay"])

    def test_completed_diagnostic_and_partial_reference_inputs_required(self):
        for name, status in (("native-diagnostic.csv", "completed"), ("uv.lock", "failed")):
            data = (self.run / name).read_bytes()
            m = copy.deepcopy(self.original)
            m.update(status=status, error="synthetic failure")
            m["files_sha256"].pop(name)
            (self.run / name).unlink()
            self.manifest(m)
            with self.assertRaises((ValueError, FileNotFoundError)):
                read_run(self.run)
            (self.run / name).write_bytes(data)
        self.manifest(self.original)

    def test_empty_warning_message_is_retained(self):
        value = [{"category": "UserWarning", "message": "", "filename": "fixture.py", "line": 1}]
        write_json(self.run / "warnings.json", value)
        m = copy.deepcopy(self.original)
        m["files_sha256"]["warnings.json"] = digest(self.run / "warnings.json")
        self.manifest(m)
        self.assertEqual(read_run(self.run)["warnings"], value)

    def test_started_runtime_and_pump_parameter_schema(self):
        m = copy.deepcopy(self.original)
        m.update(status="started", elapsed_seconds="not a number")
        self.manifest(m)
        with self.assertRaises(ValueError):
            read_run(self.run)
        m = copy.deepcopy(self.original)
        m["effective_settings"]["pump_parameters"].pop("max_basal")
        self.manifest(m)
        with self.assertRaisesRegex(ValueError, "pump parameters"):
            read_run(self.run)
