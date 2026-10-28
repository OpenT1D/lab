"""Observation boundaries independent of the pending estimator/source decision."""

import copy
import json
import shutil
import tempfile
import unittest
from pathlib import Path

from experiments.catalogue.storage import dump, seal
from experiments.observation_analysis.fixtures import csv_bytes, package
from experiments.observation_analysis.intake import import_observations, verify_import
from experiments.observation_analysis.observations import parse_csv, validate_package


class ObservationImportTests(unittest.TestCase):
    def test_sealed_import_relocates_reconstructs_and_refuses_tampered_diagnostics(self):
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            (directory / "package.json").write_text(json.dumps(package()))
            (directory / "observations.csv").write_bytes(csv_bytes())
            record = import_observations(
                directory / "package.json", directory / "observations.csv", directory / "imported"
            )
            self.assertEqual(record["status"], "valid")
            shutil.move(directory / "imported", directory / "relocated")
            declared, checked = verify_import(directory / "relocated")
            self.assertEqual(declared, package())
            self.assertEqual(checked, record["validation"])
            with self.assertRaisesRegex(ValueError, "fresh"):
                import_observations(
                    directory / "package.json",
                    directory / "observations.csv",
                    directory / "relocated",
                )
            (directory / "relocated/manifest.json").unlink()
            record["validation"]["visits"][0]["rows"][0]["cpeptide_nmol_l"] = 999
            dump(directory / "relocated/import.json", record)
            seal(directory / "relocated")
            with self.assertRaisesRegex(ValueError, "diagnostics differ"):
                verify_import(directory / "relocated")

    def test_missing_source_and_invalid_metadata_have_reconstructible_failures(self):
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            (directory / "observations.csv").write_bytes(csv_bytes())
            record = import_observations(
                directory / "absent.json",
                directory / "observations.csv",
                directory / "missing-meta",
            )
            self.assertEqual(record["status"], "invalid")
            self.assertEqual(set(record["inputs"]), {"observations.csv"})
            self.assertEqual(verify_import(directory / "missing-meta"), (None, None))
            for index, raw in enumerate((None, b'{"schema": "bad"}', b'{"secret": "private",')):
                if raw is not None:
                    (directory / "package.json").write_bytes(raw)
                record = import_observations(
                    directory / "package.json", directory / "absent.csv", directory / str(index)
                )
                self.assertEqual(record["status"], "invalid")
                self.assertEqual(verify_import(directory / str(index)), (None, None))
                self.assertNotIn("private", record.get("error", ""))
            (directory / "observations.csv").write_bytes(csv_bytes())
            record = import_observations(
                directory / "package.json", directory / "observations.csv", directory / "bad-json"
            )
            self.assertEqual(record["error"], "Invalid JSON encoding or framing")
            self.assertEqual(verify_import(directory / "bad-json"), (None, None))

    def test_exact_linkage_units_context_and_participant_split(self):
        result = parse_csv(csv_bytes(), package())
        self.assertTrue(result["valid"])
        self.assertEqual(len(result["visits"]), 2)
        self.assertEqual(len(result["visits"][0]["rows"]), 5)
        self.assertEqual(result["visits"][0]["metadata"]["assay"]["id"], "invented-assay")
        for alteration, message in (
            (lambda p: p.update(data_kind="human"), "synthetic"),
            (lambda p: p["units"].update(cpeptide="pmol/L"), "convert"),
            (lambda p: p["participants"].append(copy.deepcopy(p["participants"][0])), "Duplicate"),
            (lambda p: p["participants"][0]["visits"][0].update(allocation="evaluation"), "fields"),
            (lambda p: p["participants"][0]["context"].update(weight_kg=float("nan")), "Finite"),
        ):
            with self.subTest(message=message):
                p = package()
                alteration(p)
                with self.assertRaisesRegex(ValueError, message):
                    validate_package(p)

    def test_missing_censored_and_low_values_remain_explicit(self):
        rows = [
            ["invented-01", "before", "meal-01", 0, "", "missing", "", "below_loq"],
            ["invented-01", "before", "meal-01", 120, 5, "observed", "", "missing"],
        ]
        result = parse_csv(csv_bytes(rows), package())
        visit = result["visits"][0]
        self.assertTrue(visit["valid"])
        self.assertIsNone(visit["rows"][0]["cpeptide_nmol_l"])
        self.assertEqual(visit["rows"][0]["cpeptide_status"], "below_loq")
        self.assertFalse(result["valid"])  # second declared visit retained and invalid
        rows[0][-2:] = [0.001, "observed"]
        result = parse_csv(csv_bytes(rows), package())
        self.assertIn("LOQ", result["visits"][0]["errors"][0]["reason"])

    def test_unknown_rows_duplicates_bad_values_and_empty_visits_keep_accounting(self):
        rows = [
            ["invented-01", "before", "meal-01", 0, 5, "observed", 0.2, "observed"],
            ["invented-01", "before", "meal-01", 0, 5, "observed", 0.2, "observed"],
            ["unknown", "before", "meal-01", 120, 5, "observed", 0.2, "observed"],
            ["invented-01", "after", "meal-01", 120, "SECRET", "observed", 0.2, "observed"],
        ]
        result = parse_csv(csv_bytes(rows), package())
        self.assertFalse(result["valid"])
        self.assertEqual(len(result["visits"]), 2)
        self.assertEqual(result["errors"][0]["row"], 4)
        self.assertIn("Duplicate", result["visits"][0]["errors"][0]["reason"])
        self.assertNotIn("SECRET", str(result))

    def test_framing_and_nonfinite_and_time_boundaries(self):
        for raw in (b"wrong,header\n", b"\xff", b'"unclosed'):
            result = parse_csv(raw, package())
            self.assertFalse(result["valid"])
            self.assertTrue(result["errors"])
            self.assertEqual(len(result["visits"]), 2)
        for time, glucose, peptide in (
            (-1, 5, 0.2),
            (121, 5, 0.2),
            (float("nan"), 5, 0.2),
            (0, float("inf"), 0.2),
            (0, 5, -1),
        ):
            result = parse_csv(
                csv_bytes(
                    [
                        [
                            "invented-01",
                            "before",
                            "meal-01",
                            time,
                            glucose,
                            "observed",
                            peptide,
                            "observed",
                        ]
                    ]
                ),
                package(),
            )
            self.assertFalse(result["valid"])
            self.assertTrue(result["visits"][0]["errors"])


if __name__ == "__main__":
    unittest.main()
