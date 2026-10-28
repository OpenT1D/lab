"""The actual shared intake and selection chain, including retained invalid imports."""

import shutil
import tempfile
import unittest
from pathlib import Path

from experiments.catalogue.storage import dump, read, seal
from experiments.ot056_pilot.preflight import preflight, verify_preflight


class PreflightTests(unittest.TestCase):
    def test_actual_imports_failures_and_relocated_development_selection(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            result = preflight(root / "preflight")
            self.assertEqual(len(result["records"]), 9)
            self.assertEqual(sum(r["import_status"] == "valid" for r in result["records"]), 6)
            self.assertEqual(sum(r["selection"] is not None for r in result["records"]), 6)
            self.assertEqual(result["human_sessions"], 0)
            self.assertEqual({r["planned_visits"] for r in result["records"]}, {10})
            shutil.copytree(root / "preflight", root / "relocated")
            shutil.rmtree(root / "preflight")
            self.assertEqual(verify_preflight(root / "relocated"), result)
            (root / "relocated/manifest.json").unlink()
            forged = read(root / "relocated/preflight.json")
            forged["records"][0]["planned_visits"] = 8
            dump(root / "relocated/preflight.json", forged)
            seal(root / "relocated")
            with self.assertRaisesRegex(ValueError, "Visit accounting"):
                verify_preflight(root / "relocated")


if __name__ == "__main__":
    unittest.main()
