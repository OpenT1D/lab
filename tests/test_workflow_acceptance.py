"""Acceptance must reject changed archives and misleading completion evidence."""

import contextlib
import io
import json
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from experiments.workflow_acceptance.__main__ import (
    CONTROLS,
    TASKS,
    Commands,
    inventory,
    native_complete,
    provenance,
    reports_equal,
    unchanged,
)


class WorkflowAcceptanceTests(unittest.TestCase):
    def test_discovery_matches_the_actual_entry_contract(self):
        from experiments.workflows.__main__ import main

        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            self.assertEqual(main(["list"]), 0)
        result = json.loads(output.getvalue())
        self.assertEqual(result["schema"], "opent1d.workflow-entry/1")
        self.assertTrue(set(TASKS) <= {task["task"] for task in result["tasks"]})

    def test_child_archive_changes_are_detected(self):
        with tempfile.TemporaryDirectory() as temporary:
            archive = Path(temporary)
            (archive / "model.py").write_text("opaque candidate source")
            before = inventory(archive)
            unchanged(archive, before)
            (archive / "launcher.json").write_text("{}")
            with self.assertRaisesRegex(ValueError, "modified child archive"):
                unchanged(archive, before)
            (archive / "launcher.json").unlink()
            (archive / "model.py").write_text("changed candidate source")
            with self.assertRaisesRegex(ValueError, "modified child archive"):
                unchanged(archive, before)

    def test_archive_symlinks_are_not_followed(self):
        with tempfile.TemporaryDirectory() as temporary:
            parent = Path(temporary)
            archive = parent / "archive"
            archive.mkdir()
            source = parent / "source.py"
            source.write_text("outside candidate source")
            (archive / "model.py").symlink_to(source)
            with self.assertRaisesRegex(ValueError, "symlink"):
                inventory(archive)

    def test_native_incompleteness_is_not_a_successful_child_exit(self):
        report = {
            "comparison_status": "complete",
            "roster_count": 32,
            "people": [{}] * 32,
            "evaluation_eligible_count": 7,
            "paired_count": 6,
        }
        with self.assertRaisesRegex(ValueError, "incomplete"):
            native_complete("m5-prognosis", report)
        report["paired_count"] = 7
        native_complete("m5-prognosis", report)
        report["comparison_status"] = "incomplete"
        with self.assertRaisesRegex(ValueError, "incomplete"):
            native_complete("m5-prognosis", report)

    def test_m4_accounting_requires_both_complete_processes(self):
        report = {
            "passed": True,
            "status": "completed",
            "accepted_observation_cases": 6,
            "case_accounting": {
                label: {str(i): "completed" for i in range(6)} for label in ("primary", "repeat")
            },
        }
        native_complete("m4-secretion", report)
        report["case_accounting"]["repeat"]["5"] = "not_attempted"
        with self.assertRaisesRegex(ValueError, "incomplete"):
            native_complete("m4-secretion", report)

    def test_p1_reconstruction_uses_native_report_location(self):
        with tempfile.TemporaryDirectory() as temporary:
            parent = Path(temporary)
            archive, rebuilt = parent / "archive", parent / "rebuilt"
            (archive / "report").mkdir(parents=True)
            rebuilt.mkdir()
            for name in ("report.json", "report.md"):
                (archive / "report" / name).write_bytes(b"native report\n")
                (rebuilt / name).write_bytes(b"native report\n")
            reports_equal("p1-controller", archive, rebuilt)
            (rebuilt / "report.md").write_bytes(b"altered report\n")
            with self.assertRaisesRegex(ValueError, "report differs"):
                reports_equal("p1-controller", archive, rebuilt)

    def test_receipts_capture_scoped_controls_without_inherited_secrets(self):
        def child(command, *, cwd, env, stdout, stderr, check):
            self.assertFalse(check)
            for key, value in CONTROLS.items():
                self.assertEqual(env[key], value)
            stdout.write(json.dumps({"schema": "opent1d.workflow-entry/1"}).encode())
            return subprocess.CompletedProcess(command, 0)

        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary)
            commands = Commands(output)
            with (
                patch.dict("os.environ", {"PRIVATE_ACCESS_TOKEN": "do-not-log"}),
                patch("experiments.workflow_acceptance.__main__.subprocess.run", side_effect=child),
            ):
                commands.run("passive-check", ["experiments.workflows", "list"], launcher=True)
            receipt = (output / "commands/passive-check.json").read_text()
            self.assertNotIn("PRIVATE_ACCESS_TOKEN", receipt)
            self.assertNotIn("do-not-log", receipt)
            self.assertEqual(json.loads(receipt)["uv_controls"], CONTROLS)

    def test_dirty_sources_refuse_definitive_acceptance(self):
        with (
            patch(
                "experiments.workflow_acceptance.__main__.subprocess.check_output",
                return_value=b"?? changed-source.py\n",
            ),
            self.assertRaisesRegex(ValueError, "clean execution commit"),
        ):
            provenance()


if __name__ == "__main__":
    unittest.main()
