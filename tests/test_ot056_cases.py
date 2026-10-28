"""Real shared-import checks on invented cases, not human pilot observations."""

import shutil
import tempfile
import unittest
from collections import Counter
from pathlib import Path

from experiments.catalogue.storage import dump, seal
from experiments.mmtt_sampling.masking import mask_csv
from experiments.observation_analysis.analysis import evaluate, report_from_attempts
from experiments.observation_analysis.fixtures import analysis_settings, csv_bytes
from experiments.ot056_pilot.cases import (
    MAIN_CLASSIFICATIONS,
    SCHEDULE_CLASSIFICATIONS,
    case_documents,
    check_main_report,
    export_cases,
    verify_cases,
)


class PilotCaseTests(unittest.TestCase):
    def test_main_packages_cover_resolved_assumption_and_failure_interpretations(self):
        settings = analysis_settings()
        for label, scale in (("A", 0.95), ("B", 1.0), ("C", 1.05)):
            with self.subTest(label=label):
                package, rows, design = case_documents(scale, label)
                attempts = evaluate(settings, package, csv_bytes(rows))
                report = report_from_attempts({"settings": settings}, attempts)
                self.assertEqual(check_main_report(report), MAIN_CLASSIFICATIONS)
                for person in report["people"].values():
                    self.assertGreater(
                        person["references"]["after"]["glucose_auc_mmol_min_l"],
                        person["references"]["before"]["glucose_auc_mmol_min_l"],
                    )
                for schedule, times in design["subsets"].items():
                    retained, _ = mask_csv(csv_bytes(rows), package, times)
                    reduced = report_from_attempts(
                        {"settings": settings}, evaluate(settings, package, retained)
                    )
                    self.assertEqual(
                        check_main_report(reduced, schedule), SCHEDULE_CLASSIFICATIONS[schedule]
                    )

    def test_structural_matching_faults_relocation_and_tampering(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            receipt = export_cases(root / "cases")
            self.assertEqual(
                Counter(c["expected_import_valid"] for c in receipt["cases"]), {True: 6, False: 3}
            )
            complete = [case for case in receipt["cases"] if case["expected_import_valid"]]
            self.assertEqual({(case["participants"], case["rows"]) for case in complete}, {(5, 60)})
            shutil.copytree(root / "cases", root / "relocated")
            self.assertEqual(verify_cases(root / "relocated"), receipt)
            with self.assertRaises(ValueError):
                export_cases(root / "cases")
            with (root / "relocated/task1-A/observations.csv").open("a") as stream:
                stream.write("changed\n")
            with self.assertRaisesRegex(ValueError, "bytes changed"):
                verify_cases(root / "relocated")
            (root / "cases/manifest.json").unlink()
            receipt["human_sessions"] = 6
            dump(root / "cases/cases.json", receipt)
            seal(root / "cases")
            with self.assertRaisesRegex(ValueError, "trusted synthetic construction"):
                verify_cases(root / "cases")


if __name__ == "__main__":
    unittest.main()
