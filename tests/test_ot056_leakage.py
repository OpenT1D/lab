"""Actual raw-file leakage trap setup, not a substitute for estimator execution."""

import tempfile
import unittest
from pathlib import Path

from experiments.ot056_pilot.cases import export_cases
from experiments.ot056_pilot.leakage import omitted_cell_controls, schedule_gap_control
from experiments.ot056_pilot.references import export_references


class OmittedCellControlsTests(unittest.TestCase):
    def test_all_actual_subsets_hide_poisoned_analytes_before_shared_parsing(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            export_cases(root / "cases")
            result = omitted_cell_controls(root / "cases/task2-A", root / "controls")
            self.assertEqual(len(result["records"]), 6)
            self.assertFalse(result["estimator_executed"])
            self.assertEqual({r["retained_import_status"] for r in result["records"]}, {"valid"})
            invalid = [r for r in result["records"] if r["control"] == "invalid-omitted-cells"]
            self.assertEqual({r["poisoned_full_import_status"] for r in invalid}, {"invalid"})
            self.assertTrue(all(len(r["visits"]) == 10 for r in result["records"]))

    def test_valid_shared_import_still_requires_the_frozen_schedule_gate(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            export_references(root / "references")
            result = schedule_gap_control(root / "references", root / "gap")
            self.assertEqual(result["shared_import_status"], "valid")
            self.assertEqual(len(result["outcomes"]["full"]["missing_visits"]), 1)
            self.assertEqual(len(result["outcomes"]["five-times"]["missing_visits"]), 1)
            self.assertEqual(result["outcomes"]["four-times"]["missing_visits"], [])
            self.assertEqual(result["outcomes"]["three-times"]["missing_visits"], [])


if __name__ == "__main__":
    unittest.main()
