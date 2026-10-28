"""Admission and route semantics for the synthetic multiple-source M4 task."""

import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from experiments.workflows.__main__ import parser
from experiments.workflows.checks import check, runtime_requirements
from experiments.workflows.dispatch import command_for, execute
from experiments.workflows.registry import NATIVE_PROJECT, OBSERVER_PROJECT, ROOT, TASKS


def arguments(*values):
    return parser().parse_args(values)


class M4ComparisonEntryTests(unittest.TestCase):
    def fixture(self, directory):
        marker = directory / "imported"
        source = f"from pathlib import Path\nPath({str(marker)!r}).touch()\n".encode()
        (directory / "model.py").write_bytes(source)
        declared = json.loads(
            (ROOT / "experiments/m4/causal_secretion/example_model.json").read_bytes()
        )
        declared["source_sha256"] = hashlib.sha256(source).hexdigest()
        (directory / "model.json").write_text(json.dumps(declared))
        config = {
            "schema": "m4-source-comparison-config/1",
            "sources": [
                {"id": identity, "model": "model.py", "declaration": "model.json"}
                for identity in ("first", "second")
            ],
            "timeout_seconds": 600,
            "source_timeout_seconds": 3600,
        }
        path = directory / "comparison.json"
        path.write_text(json.dumps(config))
        return path, marker

    def test_passive_intake_checks_all_sources_without_importing_them(self):
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            config, marker = self.fixture(directory)
            args = arguments("check", "m4-compare", "--config", str(config))
            with (
                patch("experiments.workflows.checks.probe_runtime", return_value={"ready": True}),
                patch("experiments.workflows.checks.uv_ready", return_value={"ready": True}),
            ):
                result = check(TASKS[args.task], args)
            self.assertTrue(result["ready"])
            self.assertEqual(result["metadata"]["source_order"], ["first", "second"])
            self.assertEqual(set(result["metadata"]["source_sha256"]), {"first", "second"})
            self.assertFalse(result["metadata"]["source_executed"])
            self.assertFalse(marker.exists())

    def test_changed_source_refuses_before_dispatch_and_archive_creation(self):
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            config, marker = self.fixture(directory)
            (directory / "model.py").write_bytes(b"changed")
            output = directory / "output"
            args = arguments("run", "m4-compare", "--config", str(config), "--output", str(output))
            with patch("experiments.workflows.dispatch.run_process") as child:
                with self.assertRaisesRegex(ValueError, "hash"):
                    execute(TASKS[args.task], args)
            child.assert_not_called()
            self.assertFalse(output.exists())
            self.assertFalse(marker.exists())

    def test_route_preserves_reference_and_explicit_failed_reconstruction(self):
        task = TASKS["m4-compare"]
        run = arguments(
            "run",
            "m4-compare",
            "--config",
            "/config",
            "--output",
            "/output",
            "--reference",
            "/reference",
        )
        argv = command_for(task, run)
        self.assertIn("run", argv)
        self.assertIn("/reference", argv)
        self.assertEqual(Path(argv[0]), ROOT / ".venv/bin/python")
        self.assertEqual(set(runtime_requirements(task)), {".", NATIVE_PROJECT, OBSERVER_PROJECT})
        rebuild = arguments(
            "reconstruct",
            "m4-compare",
            "--archive",
            "/archive",
            "--output",
            "/rebuilt",
            "--allow-failed",
        )
        argv = command_for(task, rebuild, operation="reconstruct")
        self.assertIn("-S", argv)
        self.assertIn("--archive", argv)
        self.assertIn("--allow-failed", argv)
        self.assertEqual(runtime_requirements(task, reconstruction=True), {".": {}})

    def test_failed_report_remains_failed_when_reconstruction_succeeds(self):
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            output = directory / "rebuilt"
            args = arguments(
                "reconstruct",
                "m4-compare",
                "--archive",
                str(directory / "archive"),
                "--output",
                str(output),
                "--allow-failed",
            )

            def child(_argv, _env):
                output.mkdir()
                (output / "report.json").write_text(json.dumps({"passed": False}))
                (output / "report.md").touch()
                return 0, None

            with (
                patch(
                    "experiments.workflows.dispatch.check",
                    return_value={"runtimes_ready": True, "observation_path_issues": []},
                ),
                patch("experiments.workflows.dispatch.run_process", side_effect=child),
            ):
                result = execute(TASKS[args.task], args, operation="reconstruct")
            self.assertEqual(result["child_exit_code"], 0)
            self.assertEqual(result["report_completeness"], "failed")
            self.assertEqual(result["report_status_scope"], "native_reader_verified")


if __name__ == "__main__":
    unittest.main()
