"""Sampling adapter parity, complete evidence and independent refusal cases."""

import json
import shutil
import tempfile
import unittest
from pathlib import Path

from experiments.catalogue.storage import dump, seal
from experiments.mmtt_sampling import run as native
from experiments.observation_analysis.intake import import_observations
from experiments.shared_services import execution, installed, routes, store


class SamplingServices(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temporary = tempfile.TemporaryDirectory(prefix="sampling-services-")
        cls.addClassCleanup(cls.temporary.cleanup)
        cls.root = Path(cls.temporary.name).resolve()
        cls.inputs = installed.example("mmtt-sampling", cls.root / "inputs", "information-loss")[
            "inputs"
        ]
        cls.project = store.create(cls.root / "project", "Invented sampling integration")
        with store.opened(cls.project, write_access=True) as project:
            cls.plan_id = routes.freeze(project, "mmtt-sampling", cls.inputs)
            cls.descriptor, cls.plan = project.plans[cls.plan_id]
            cls.attempt = execution.execute(project, cls.plan_id, timeout=120)
            cls.archive = project.finishes[cls.attempt][1] / "native"
            cls.result = project.finishes[cls.attempt][0]["result"]
        cls.direct = cls.root / "direct"
        native.run(cls.plan / "input", cls.direct)

    def test_native_byte_parity_and_complete_denominators(self):
        self.assertEqual(self.result["completeness"], "complete")
        self.assertEqual(len(self.result["slot_statuses"]), 60)
        self.assertEqual(set(self.result["slot_statuses"].values()), {"complete"})
        self.assertEqual(len(self.result["report_sha256"]), 10)
        for name in self.result["report_sha256"]:
            self.assertEqual((self.archive / name).read_bytes(), (self.direct / name).read_bytes())
        report = store.read(self.archive / "report.json")
        self.assertEqual(report["coverage"]["planned_draw_pairs"], 60 * 128)
        directions = report["comparisons"]["evaluation"]["three-times"]["nominal"]["directions"]
        self.assertEqual(directions["direction_reversal"], 3)

    def test_move_without_original_inputs_retains_parent_and_children(self):
        moved = self.root / "moved"
        with store.opened(self.project) as project:
            project.relocate(moved)
        source = self.root / "inputs"
        source.rename(self.root / "inputs-unavailable")
        try:
            with store.opened(moved, write_access=True) as project:
                result = execution.reconstruct(project, self.attempt, self.root / "rebuilt")
                self.assertEqual(result["report_sha256"], self.result["report_sha256"])
                self.assertEqual(len(project.attempts), 1)
                for name in result["report_sha256"]:
                    self.assertEqual(
                        (self.root / "rebuilt" / name).read_bytes(),
                        (self.archive / name).read_bytes(),
                    )
        finally:
            (self.root / "inputs-unavailable").rename(source)

    def test_wrong_development_or_changed_cells_refuse_before_freeze(self):
        original = Path(self.inputs["development"])
        for case in ("evaluation", "changed-cells"):
            copied = self.root / ("development-" + case)
            shutil.copytree(original, copied)
            if case == "evaluation":
                package = store.read(copied / "package.json")
                package["participants"][0]["allocation"] = "evaluation"
                dump(copied / "package.json", package)
            else:
                raw = (copied / "observations.csv").read_bytes().replace(b",0.2,", b",0.21,")
                self.assertNotEqual(raw, (copied / "observations.csv").read_bytes())
                (copied / "observations.csv").write_bytes(raw)
                rebuilt = self.root / "changed-cells-reimported"
                import_observations(copied / "package.json", copied / "observations.csv", rebuilt)
                copied = rebuilt
            inputs = {**self.inputs, "development": copied}
            with store.opened(self.project, write_access=True) as project:
                before = dict(project.head)
                message = (
                    "development-only"
                    if case == "evaluation"
                    else "Development observation cells differ"
                )
                with self.assertRaisesRegex(ValueError, message):
                    routes.freeze(project, "mmtt-sampling", inputs)
                self.assertEqual(project.head, before)

    def test_resealed_child_omissions_and_swaps_refuse_passive_intake(self):
        for case in ("missing-report", "missing-draws", "swapped-child"):
            copied = self.root / case
            shutil.copytree(self.archive, copied)
            child = copied / "studies/three-times"
            if case == "missing-report":
                (child / "report.json").unlink()
            elif case == "missing-draws":
                attempts = store.read(child / "attempts.json")
                first = next(iter(attempts["people"].values()))
                first["perturbations"].pop()
                dump(child / "attempts.json", attempts)
            else:
                shutil.rmtree(child)
                shutil.copytree(copied / "studies/full", child)
            (child / "manifest.json").unlink()
            seal(child)
            (copied / "manifest.json").unlink()
            seal(copied)
            with self.subTest(case=case), self.assertRaises((ValueError, OSError, KeyError)):
                routes.native_result(copied, self.descriptor, self.plan)

    def test_changed_development_snapshot_is_refused_even_after_resealing(self):
        copied = self.root / "changed-freeze"
        shutil.copytree(self.plan, copied)
        raw = json.loads((copied / "original/design.json").read_text())
        raw["selection_participants"] = ["invented-evaluation-01"]
        dump(copied / "original/design.json", raw)
        with self.assertRaises(ValueError):
            routes.validate_freeze(copied, self.descriptor, current=True)


if __name__ == "__main__":
    unittest.main()
