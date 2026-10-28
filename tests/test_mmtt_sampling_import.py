"""OT-055 reuses the checked OT-054 importer and archive verifier."""

import hashlib
import json
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from experiments.mmtt_sampling.__main__ import freeze_import
from experiments.mmtt_sampling.design import project_samples
from experiments.mmtt_sampling.fixtures import example, export_example
from experiments.mmtt_sampling.intake import development_inventory
from experiments.observation_analysis.intake import import_observations, verify_import
from experiments.observation_analysis.observations import parse_csv


class SamplingImportTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)

    def imported(self, development_only=True):
        source = export_example(self.root / "source", development_only)
        archive = self.root / "import"
        record = import_observations(source / "package.json", source / "observations.csv", archive)
        self.assertEqual(record["status"], "valid")
        return source, archive

    def test_full_case_roster_preserves_low_censoring_and_glucose_context(self):
        package, raw, _ = example()
        parsed = parse_csv(raw, package)
        self.assertTrue(parsed["valid"])
        self.assertEqual(len(parsed["visits"]), 10)
        self.assertEqual(sum(len(v["rows"]) for v in parsed["visits"]), 60)
        low = [v for v in parsed["visits"] if v["participant_id"].endswith("low")]
        self.assertTrue(all(r["cpeptide_nmol_l"] < 0.03 for v in low for r in v["rows"]))
        censored = [
            r for v in parsed["visits"] for r in v["rows"] if r["cpeptide_status"] == "below_loq"
        ]
        self.assertEqual(len(censored), 1)
        self.assertIsNone(censored[0]["cpeptide_nmol_l"])
        self.assertNotEqual(
            parsed["visits"][0]["rows"][0]["glucose_mmol_l"],
            parsed["visits"][1]["rows"][0]["glucose_mmol_l"],
        )

    def test_shared_import_and_relocation_bind_selection_to_source(self):
        source, archive = self.imported()
        relocated = self.root / "relocated"
        shutil.move(archive, relocated)
        receipt = freeze_import(
            source / "sampling-design.json", relocated, self.root / "selection.json"
        )
        self.assertEqual(len(receipt["development_times"]), 4)
        self.assertEqual(
            receipt["development_import_seal_sha256"],
            hashlib.sha256((relocated / "manifest.json").read_bytes()).hexdigest(),
        )
        saved = json.loads((self.root / "selection.json").read_text())
        self.assertEqual(saved, receipt)

    def test_evaluation_roster_rejected_before_shared_csv_reader(self):
        source, archive = self.imported(False)
        design = json.loads((source / "sampling-design.json").read_text())
        with patch("experiments.mmtt_sampling.intake.verify_import") as reader:
            with self.assertRaisesRegex(ValueError, "development-only"):
                development_inventory(archive, design)
            reader.assert_not_called()

    def test_modified_archive_is_not_used_for_selection(self):
        source, archive = self.imported()
        (archive / "observations.csv").write_bytes(b"modified")
        with self.assertRaisesRegex(ValueError, "bytes changed"):
            freeze_import(source / "sampling-design.json", archive, self.root / "selection.json")
        self.assertFalse((self.root / "selection.json").exists())

    def test_project_shared_rows_before_any_future_estimation(self):
        _, archive = self.imported()
        _, validation = verify_import(archive)
        rows = validation["visits"][0]["rows"]
        retained = project_samples(rows, [0, 60, 120], time_key="time_min")
        self.assertEqual([r["time_min"] for r in retained], [0, 60, 120])
        self.assertEqual(retained[0], rows[0])
        self.assertEqual(len(rows), 6)


if __name__ == "__main__":
    unittest.main()
