"""P1 keeps a bounded schedule, failures, and byte-identical report checks."""

import importlib
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from experiments.m0.simglucose.recording import write_json

p1 = importlib.import_module("experiments.p1.__main__")


class P1WorkflowTests(unittest.TestCase):
    def test_plan_is_one_complete_development_grid(self):
        marker, study = p1.plan("adult#002", 101)
        self.assertEqual(marker["profile"], "adult#002")
        self.assertEqual(len(study["cases"]), 8)
        self.assertEqual(
            {
                (case["config"]["controller"], case["config"]["condition"])
                for case in study["cases"]
            },
            {
                (controller, condition)
                for controller in ("basal_bolus", "pid")
                for condition in "ABCD"
            },
        )
        with self.assertRaisesRegex(ValueError, "P1 supports"):
            p1.plan("adult#003", 101)
        with self.assertRaisesRegex(ValueError, "P1 supports"):
            p1.plan("adult#001", True)

    def test_all_cases_are_planned_before_attempts_and_termination_is_retained(self):
        attempted = []

        def fake_execute(config, output):
            output = Path(output)
            study = json.loads((output.parent / "study.json").read_text())
            self.assertEqual(study["status"], "started")
            self.assertEqual(len(study["cases"]), 8)
            self.assertEqual(len(list((output.parent / "inputs").glob("*.json"))), 8)
            output.mkdir()
            attempted.append(output.name)
            return {"status": "terminated" if output.name.endswith("pid-B") else "completed"}

        with tempfile.TemporaryDirectory() as root:
            path = Path(root) / "study"
            with (
                patch.object(p1, "require_runtime"),
                patch.object(p1, "execute", side_effect=fake_execute),
                patch.object(
                    p1,
                    "write_product_report",
                    return_value={"study_status": "finished_with_failures"},
                ),
            ):
                p1.run_study(path)
            self.assertEqual(len(attempted), 8)
            self.assertEqual(
                json.loads((path / "study.json").read_text())["status"], "finished_with_failures"
            )
            with self.assertRaises(FileExistsError):
                path.mkdir(exist_ok=False)

    def test_changed_schedule_is_rejected_before_reconstruction(self):
        with tempfile.TemporaryDirectory() as root:
            directory = Path(root)
            marker, study = p1.plan("adult#001", 101)
            write_json(directory / "workflow.json", marker)
            write_json(directory / "study.json", study)
            self.assertEqual(p1.validate_study(directory), marker)
            altered_marker = {**marker, "p1_source_sha256": "0" * 64}
            write_json(directory / "workflow.json", altered_marker)
            with self.assertRaisesRegex(ValueError, "workflow marker"):
                p1.validate_study(directory)
            write_json(directory / "workflow.json", marker)
            study["cases"][0]["config"]["profile"] = "adult#002"
            write_json(directory / "study.json", study)
            with self.assertRaisesRegex(ValueError, "schedule differs"):
                p1.validate_study(directory)

    def test_reconstruction_checks_all_three_original_report_files(self):
        with tempfile.TemporaryDirectory() as root:
            directory = Path(root) / "study"
            directory.mkdir()
            marker, study = p1.plan("adult#001", 101)
            study["status"] = "completed"
            write_json(directory / "workflow.json", marker)
            write_json(directory / "study.json", study)
            original = directory / "report"
            original.mkdir()
            for name in p1.REPORT_FILES:
                (original / name).write_text(name)

            def fake_report(_study, output):
                Path(output).mkdir()
                for name in p1.REPORT_FILES:
                    (Path(output) / name).write_text(name)
                return {"study_status": "completed"}

            with patch.object(p1, "write_product_report", side_effect=fake_report):
                p1.reconstruct(directory, Path(root) / "rebuilt")
                record = json.loads((Path(root) / "rebuilt" / "reconstruction.json").read_text())
                self.assertTrue(record["byte_identical_to_original"])
                (original / "overview.md").write_text("changed")
                with self.assertRaisesRegex(ValueError, "reconstruction differs"):
                    p1.reconstruct(directory, Path(root) / "changed")

    def test_overview_retains_undefined_terminal_outcome(self):
        marker, _ = p1.plan("adult#001", 102)
        cases = []
        for controller in ("basal_bolus", "pid"):
            for condition in "ABCD":
                complete = controller == "basal_bolus"
                cases.append(
                    {
                        "id": f"adult#001-102-{controller}-{condition}",
                        "config": {"controller": controller, "condition": condition},
                        "status": "completed" if complete else "terminated",
                        "error": None if complete else "native stop",
                        "metrics": {
                            "glucose": {"in_70_180_percent": 80, "below_70_percent": 10},
                            "delivered_interval_minutes": 1440,
                            "delivered_insulin_u": 40,
                        }
                        if complete
                        else None,
                    }
                )
        text = p1.overview(
            {
                "cases": cases,
                "comparisons": [],
                "study_status": "finished_with_failures",
                "status_counts": {"completed": 4, "terminated": 4},
            },
            marker,
        )
        self.assertIn("| pid | A | terminated | undefined", text)
        self.assertIn("native stop", text)
        self.assertIn("never a zero-dose claim", text)


if __name__ == "__main__":
    unittest.main()
