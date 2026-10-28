"""Prevent source, protocol and archive mixups in the sourced worked example."""

import copy
import json
import shutil
import tempfile
import unittest
from pathlib import Path

from experiments.m4.paired_kinetics.common import read
from experiments.m4.ultradian_basal_equivalence.report import HERE, bind, plan


class UltradianBasalIdentityTests(unittest.TestCase):
    def setUp(self):
        self.specification = read(HERE / "plan.json")
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.search = Path(self.temporary.name) / "search"
        self.causal = Path(self.temporary.name) / "causal"
        for folder in (self.search, self.causal):
            (folder / "reference").mkdir(parents=True)
            shutil.copyfile(
                "experiments/m4/feedback/protocol.json", folder / "reference/protocol.json"
            )
            (folder / "reference/manifest.json").write_text('{"synthetic_fixture": true}\n')
        shutil.copyfile(
            "experiments/m4/basal_equivalence/protocol.json", self.search / "protocol.json"
        )
        shutil.copyfile(
            "experiments/m4/causal_secretion/protocol.json", self.causal / "protocol.json"
        )
        for slot, folder, name in (
            ("reference_adapter", "causal_secretion", "example_model"),
            ("synthetic_variant", "ultradian_secretion", "model"),
        ):
            for suffix in ("json", "py"):
                shutil.copyfile(
                    f"experiments/m4/{folder}/{name}.{suffix}", self.search / f"{slot}.{suffix}"
                )
        for suffix in ("json", "py"):
            shutil.copyfile(
                self.search / f"synthetic_variant.{suffix}", self.causal / f"model.{suffix}"
            )

    def test_plan_freezes_the_named_sources_and_diagnostic_boundary(self):
        self.assertEqual(plan(self.specification), self.specification)
        changed = copy.deepcopy(self.specification)
        changed["additional_diagnostics"]["fasting"] = "Estimate fasting at an unsolved rate"
        with self.assertRaisesRegex(ValueError, "frozen"):
            plan(changed)

    def test_original_parameter_variant_cannot_be_relabelled_as_the_ultradian_example(self):
        bind(self.search, self.causal, self.specification)
        changed = read("experiments/m4/causal_secretion/example_variant_model.json")
        changed["model_id"] = self.specification["sources"]["synthetic_variant"]["model_id"]
        (self.search / "synthetic_variant.json").write_text(json.dumps(changed))
        with self.assertRaisesRegex(ValueError, "identity"):
            bind(self.search, self.causal, self.specification)

    def test_same_protocol_does_not_make_reference_archives_interchangeable(self):
        (self.causal / "reference/manifest.json").write_text(
            '{"synthetic_fixture": "another run"}\n'
        )
        with self.assertRaisesRegex(ValueError, "same fresh BC-008"):
            bind(self.search, self.causal, self.specification)

    def test_changed_search_domain_cannot_enter_the_worked_example(self):
        changed = read(self.search / "protocol.json")
        changed["sc_rate_multipliers_of_native_u2ss"] = [0.5, 0.75, 1.5]
        (self.search / "protocol.json").write_text(json.dumps(changed))
        with self.assertRaisesRegex(ValueError, "identity"):
            bind(self.search, self.causal, self.specification)


if __name__ == "__main__":
    unittest.main()
