"""Actual frozen plans, CLI execution, notebook agreement and analytic references."""

import shutil
import tempfile
import unittest
from pathlib import Path

from experiments.catalogue.storage import dump, read, seal
from experiments.observation_analysis.fixtures import export_example
from experiments.ot056_pilot.references import export_references
from experiments.ot056_pilot.technical import (
    check_reference_report,
    reference_settings,
    task1,
    task1_phase,
    verify_task1,
    verify_task1_phase,
)


class Task1RehearsalTests(unittest.TestCase):
    def test_actual_reports_match_for_each_controlled_interpretation_case(self):
        expected = {
            "increase": "consistent within investigated assumptions",
            "assumption-dependent": "assumption-dependent",
            "unresolved": "insufficiently determined",
            "censored": "insufficiently determined",
        }
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            for case, classification in expected.items():
                with self.subTest(case=case):
                    inputs = root / f"{case}-inputs"
                    export_example(inputs, case)
                    result = task1(inputs, inputs / "settings.json", root / case)
                    self.assertEqual(result["status"], "matched")
                    report = read(root / case / "native/report.json")
                    self.assertEqual(
                        report["people"]["invented-01"]["classification"], classification
                    )

    def test_known_whole_body_values_and_relocated_native_notebook_evidence(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            expected = export_references(root / "inputs")
            dump(root / "settings.json", reference_settings(expected))
            task1(root / "inputs", root / "settings.json", root / "original")
            reference = check_reference_report(read(root / "original/native/report.json"), expected)
            self.assertEqual(len(reference["checks"]), 4)
            shutil.move(root / "original", root / "relocated")
            result = verify_task1(root / "relocated", root / "fresh-reconstruction")
            self.assertEqual(result["status"], "matched")
            result["coverage"]["planned_visits"] += 1
            archive = root / "relocated"
            (archive / "manifest.json").unlink()
            dump(archive / "comparison.json", result)
            seal(archive)
            with self.assertRaisesRegex(ValueError, "coverage differs"):
                verify_task1(archive, root / "forged-coverage-check")

    def test_invalid_unit_input_is_refused_by_both_workflows(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            export_example(root / "inputs")
            package = read(root / "inputs/package.json")
            package["units"]["cpeptide"] = "unknown"
            dump(root / "inputs/package.json", package)
            result = task1(
                root / "inputs",
                root / "inputs/settings.json",
                root / "refused",
                expect_freeze_refusal=True,
            )
            self.assertEqual(result["status"], "expected-input-refusal")

    def test_eleven_case_rehearsal_relocates_and_rejects_wrong_case_inputs(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            result = task1_phase(root / "original")
            self.assertEqual(len(result["comparisons"]), 11)
            self.assertIsNone(result["product_decision"])
            shutil.move(root / "original", root / "relocated")
            self.assertEqual(verify_task1_phase(root / "relocated", root / "checked"), result)
            archive = root / "relocated"
            control = archive / "control-increase-inputs/observations.csv"
            original = control.read_bytes()
            control.write_bytes(original + b"changed\n")
            (archive / "manifest.json").unlink()
            seal(archive)
            with self.assertRaisesRegex(ValueError, "Named control inputs"):
                verify_task1_phase(archive, root / "wrong-control-check")
            control.write_bytes(original)
            (archive / "manifest.json").unlink()
            seal(archive)
            case = root / "relocated/task1-A"
            (case / "manifest.json").unlink()
            with (case / "inputs/observations.csv").open("a") as stream:
                stream.write("changed\n")
            seal(case)
            (root / "relocated/manifest.json").unlink()
            seal(root / "relocated")
            with self.assertRaisesRegex(ValueError, "named source case"):
                verify_task1_phase(root / "relocated", root / "wrong-case-check")


if __name__ == "__main__":
    unittest.main()
