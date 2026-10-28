"""Freeze allocation, development evidence and explicit shared settings before fitting."""

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from experiments.catalogue.storage import dump
from experiments.mmtt_sampling.fixtures import export_example
from experiments.mmtt_sampling.plan import freeze, load_plan
from experiments.observation_analysis.intake import import_observations


class SamplingPlanTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.full = export_example(self.root / "full")
        self.development = export_example(self.root / "development", True)
        self.archive = self.root / "development-import"
        import_observations(
            self.development / "package.json", self.development / "observations.csv", self.archive
        )

    def freeze(self, output):
        return freeze(
            self.full / "package.json",
            self.full / "observations.csv",
            self.full / "settings.json",
            self.full / "sampling-design.json",
            self.archive,
            output,
        )

    def test_freeze_binds_all_inputs_and_selection_without_executing_estimator(self):
        with patch("experiments.observation_analysis.analysis.estimate") as estimator:
            plan = self.freeze(self.root / "plan")
            estimator.assert_not_called()
        loaded, package, raw = load_plan(self.root / "plan", check_runtime=True)
        self.assertEqual(plan, loaded)
        self.assertEqual(len(package["participants"]), 5)
        self.assertEqual(len(loaded["selection_times"]), 4)
        self.assertEqual(raw["observations.csv"], (self.full / "observations.csv").read_bytes())
        (self.root / "plan/observations.csv").write_bytes(b"altered")
        with self.assertRaises(ValueError):
            load_plan(self.root / "plan")

    def test_allocation_and_development_cells_cannot_be_silently_substituted(self):
        source = self.full / "observations.csv"
        original = source.read_bytes()
        source.write_bytes(original.replace(b"0.8", b"0.9", 1))
        with self.assertRaisesRegex(ValueError, "Development observation cells differ"):
            self.freeze(self.root / "changed-data")
        source.write_bytes(original)
        package_path = self.full / "package.json"
        package = json.loads(package_path.read_text())
        package["participants"][0]["allocation"] = "evaluation"
        dump(package_path, package)
        with self.assertRaisesRegex(ValueError, "roster/allocation"):
            self.freeze(self.root / "changed-allocation")


if __name__ == "__main__":
    unittest.main()
