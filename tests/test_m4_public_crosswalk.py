"""Public-dictionary extraction and conservative same-challenge inference."""

import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from zipfile import ZipFile

from experiments.m4.measurement_readiness import public_crosswalk


class PublicCrosswalkTests(unittest.TestCase):
    def test_shared_strings_and_exact_time_field_are_read(self):
        with tempfile.TemporaryDirectory() as root:
            path = Path(root) / "dictionary.xlsx"
            strings = [
                "Table Name",
                "Variable Name",
                "Variable Description",
                "Fsigt_Raw",
                "Time ",
                "Time (min)",
            ]
            with ZipFile(path, "w") as workbook:
                workbook.writestr(
                    "xl/sharedStrings.xml",
                    '<sst xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
                    + "".join(f"<si><t>{value}</t></si>" for value in strings)
                    + "</sst>",
                )
                workbook.writestr(
                    "xl/worksheets/sheet1.xml",
                    '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"><sheetData>'
                    '<row r="1"><c r="A1" t="s"><v>0</v></c><c r="B1" t="s"><v>1</v></c>'
                    '<c r="C1" t="s"><v>2</v></c></row>'
                    '<row r="2"><c r="A2" t="s"><v>3</v></c><c r="B2" t="s"><v>4</v></c>'
                    '<c r="C2" t="s"><v>5</v></c></row></sheetData></worksheet>',
                )
            tables, variables = public_crosswalk.fields(path)
            self.assertEqual(tables, {"Fsigt_Raw"})
            self.assertEqual(variables, {"Time ": "Time (min)"})
            self.assertNotIn("Time", variables)

    def test_subject_and_day_fields_do_not_establish_same_challenge(self):
        common = {"ACCESSION": "Masked Subject ID", "NumDaysInitial": "Day"}
        inventories = {
            "fsigt.xlsx": common
            | {"Time ": "Time (min)", "glu": "Glucose", "ins_tosoh": "Insulin"},
            "cpeptide.xlsx": common
            | {
                "Fasting_cpeptide": "Fasting",
                "Stimulated_cpeptide_60": "60 min",
                "Stimulated_cpeptide_90": "90 min",
            },
            "rudbeck.xlsx": common | {"Sample": "Sample", "C_Peptid": "C-peptide"},
            "insulin_use.xlsx": {"Insulin": "Insulin Use (Units/Day)"},
            "mean_insulin.xlsx": {"Mean_Insulin": "Mean Insulin (units/day) over 7 days"},
        }
        findings = public_crosswalk.interpret(inventories)
        self.assertTrue(findings["shared_subject_key_documented"])
        self.assertTrue(findings["shared_transplant_day_field_documented"])
        self.assertFalse(findings["verified_same_challenge_gic_crosswalk"])
        self.assertFalse(findings["human_execution_authorized"])
        self.assertFalse(findings["fsigt_raw_has_cpeptide_column"])

    def test_unpinned_dictionary_is_rejected_before_reading(self):
        with tempfile.TemporaryDirectory() as root:
            directory = Path(root)
            (directory / "fsigt.xlsx").write_bytes(b"not a dictionary")
            manifest = directory / "manifest.json"
            manifest.write_text(
                json.dumps(
                    {
                        "schema": "bc015-public-dictionaries/1",
                        "files": {
                            "fsigt.xlsx": {
                                "sha256": hashlib.sha256(b"other bytes").hexdigest(),
                                "table": "Fsigt_Raw",
                                "required_variables": ["glu"],
                            }
                        },
                    }
                )
            )
            with patch.object(public_crosswalk, "MANIFEST", manifest):
                with self.assertRaisesRegex(ValueError, "Unexpected source bytes"):
                    public_crosswalk.assess(directory)


if __name__ == "__main__":
    unittest.main()
