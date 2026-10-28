"""Check source-vector conversion without substituting a new inverse estimator."""

import tempfile
import unittest
from pathlib import Path

from experiments.catalogue.storage import dump, load_sealed, read, seal
from experiments.observation_analysis.intake import import_observations, verify_import
from experiments.ot056_pilot.references import export_references, verify_references


class ReferenceInputTests(unittest.TestCase):
    def test_exact_units_order_and_actual_shared_import(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            expected = export_references(root / "inputs")
            self.assertEqual(len(expected["answers"]), 4)
            self.assertEqual(expected["answers"][0]["paired_change_pmol"].split(".")[0], "2160")
            self.assertTrue(expected["answers"][-1]["negative_terminal_rate_expected"])
            self.assertTrue(load_sealed(root / "inputs").is_dir())
            imported = import_observations(
                root / "inputs/package.json", root / "inputs/observations.csv", root / "import"
            )
            self.assertEqual(imported["status"], "valid")
            _, validation = verify_import(root / "import")
            self.assertEqual(len(validation["visits"]), 8)
            first = validation["visits"][0]["rows"][0]
            self.assertEqual(first["cpeptide_nmol_l"], 0.2)
            (root / "inputs/manifest.json").unlink()
            forged = read(root / "inputs/expected.json")
            forged["answers"][0]["paired_change_pmol"] = "0"
            dump(root / "inputs/expected.json", forged)
            seal(root / "inputs")
            with self.assertRaisesRegex(ValueError, "controlled vectors"):
                verify_references(root / "inputs")


if __name__ == "__main__":
    unittest.main()
