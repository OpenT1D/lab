"""The configurable study stays passive at intake and uses the explicit route."""

import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from experiments.workflows.__main__ import parser
from experiments.workflows.checks import check, runtime_requirements
from experiments.workflows.dispatch import command_for
from experiments.workflows.registry import NATIVE_PROJECT, OBSERVER_PROJECT, ROOT, TASKS


class StudyEntryTests(unittest.TestCase):
    def test_metadata_does_not_import_sources_and_preserves_selected_loads(self):
        with tempfile.TemporaryDirectory() as temporary:
            folder = Path(temporary)
            marker = folder / "executed"
            source = f"raise RuntimeError({str(marker)!r})\n".encode()
            (folder / "source.py").write_bytes(source)
            declaration = json.loads(
                (ROOT / "experiments/m4/causal_secretion/example_model.json").read_bytes()
            )
            declaration["source_sha256"] = hashlib.sha256(source).hexdigest()
            (folder / "source.json").write_text(json.dumps(declaration))
            config = {
                "schema": "m4-initial-load-config/1",
                "sources": [
                    {"id": identity, "model": "source.py", "declaration": "source.json"}
                    for identity in ("first", "second")
                ],
                "scenarios": ["gastric_load_15g", "fasting"],
                "timeout_seconds": 600,
                "source_timeout_seconds": 3600,
            }
            path = folder / "config.json"
            path.write_text(json.dumps(config))
            args = parser().parse_args(["check", "m4-study", "--config", str(path)])
            with (
                patch(
                    "experiments.workflows.checks.probe_runtime",
                    side_effect=lambda project, packages: {"project": project, "ready": True},
                ),
                patch("experiments.workflows.checks.uv_ready", return_value={"ready": True}),
            ):
                result = check(TASKS[args.task], args)
            self.assertTrue(result["ready"])
            self.assertFalse(result["metadata"]["source_executed"])
            self.assertEqual(result["metadata"]["scenario_order"], config["scenarios"])
            self.assertEqual(result["metadata"]["source_order"], ["first", "second"])
            self.assertFalse(marker.exists())
            config["scenarios"] = ["announced_meal"]
            path.write_text(json.dumps(config))
            with self.assertRaises(ValueError):
                check(TASKS[args.task], args)

    def test_locked_runtimes_and_explicit_run_reconstruction_dispatch(self):
        task = TASKS["m4-study"]
        self.assertEqual(set(runtime_requirements(task)), {".", NATIVE_PROJECT, OBSERVER_PROJECT})
        self.assertEqual(runtime_requirements(task, reconstruction=True), {".": {}})
        run = parser().parse_args(
            [
                "run",
                "m4-study",
                "--config",
                "/tmp/config",
                "--reference",
                "/tmp/ref",
                "--output",
                "/tmp/study",
            ]
        )
        self.assertEqual(
            command_for(task, run)[4:],
            [
                "-m",
                "experiments.m4.initial_load",
                "run",
                "--config",
                "/tmp/config",
                "--output",
                "/tmp/study",
                "--reference",
                "/tmp/ref",
            ],
        )
        saved = parser().parse_args(
            [
                "reconstruct",
                "m4-study",
                "--archive",
                "/tmp/study",
                "--output",
                "/tmp/reconstructed",
                "--allow-failed",
            ]
        )
        arguments = command_for(task, saved, operation="reconstruct")
        self.assertIn("-S", arguments)
        self.assertEqual(arguments[-1], "--allow-failed")
        self.assertIn("experiments.m4.initial_load", arguments)


if __name__ == "__main__":
    unittest.main()
