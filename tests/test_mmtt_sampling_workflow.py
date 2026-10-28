"""Native shared child execution, uncertainty, failures and relocation/tamper checks."""

import csv
import io
import json
import shutil
import tempfile
import unittest
from pathlib import Path

from experiments.catalogue.storage import dump, seal
from experiments.mmtt_sampling.fixtures import export_example
from experiments.mmtt_sampling.plan import freeze
from experiments.mmtt_sampling.report import render
from experiments.mmtt_sampling.run import reconstruct, run
from experiments.observation_analysis.fixtures import csv_bytes
from experiments.observation_analysis.intake import import_observations
from experiments.observation_analysis.plan import load_plan as load_native_plan


class SamplingWorkflowTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temporary = tempfile.TemporaryDirectory()
        cls.root = Path(cls.temporary.name)
        cls.full = export_example(cls.root / "input", case="information-loss")
        dev = export_example(cls.root / "dev", True, case="information-loss")
        cls.development = cls.root / "development-import"
        import_observations(dev / "package.json", dev / "observations.csv", cls.development)
        settings = json.loads((cls.full / "settings.json").read_text())
        settings["uncertainty"]["draws"] = 32
        dump(cls.full / "settings.json", settings)
        cls.config = cls.root / "plan"
        cls.freeze_config(cls.config)
        cls.archive = cls.root / "result"
        cls.result = run(cls.config, cls.archive)

    @classmethod
    def tearDownClass(cls):
        cls.temporary.cleanup()

    @classmethod
    def freeze_config(cls, target):
        return freeze(
            cls.full / "package.json",
            cls.full / "observations.csv",
            cls.full / "settings.json",
            cls.full / "sampling-design.json",
            cls.development,
            target,
        )

    def altered(self, name):
        target = self.root / name
        shutil.copytree(self.archive, target)
        (target / "manifest.json").unlink()
        return target

    def test_all_native_calls_keep_settings_and_every_planned_attempt(self):
        c = self.result["coverage"]
        self.assertTrue(c["complete_cohort"])
        self.assertEqual(c["planned_variant_pairs"], 60)
        self.assertEqual(c["planned_visit_points"], 120)
        self.assertEqual(c["planned_draw_pairs"], 1920)
        self.assertEqual(c["attempted_draw_pairs"], c["planned_draw_pairs"])
        base = self.result["plan"]["settings"]
        for name, record in self.result["schedules"].items():
            native, _, raw = load_native_plan(self.archive / "plans" / name)
            settings = dict(native["settings"])
            required = settings.pop("required_times_min")
            self.assertEqual(settings, base)
            self.assertEqual(required, record["times_min"])
            times = {
                float(row[3])
                for row in list(csv.reader(io.StringIO(raw["observations.csv"].decode())))[1:]
            }
            self.assertEqual(times, set(required))
        d = self.result["comparisons"]["evaluation"]["three-times"]["nominal"]["directions"]
        self.assertEqual(d["planned_count"], 3)
        self.assertEqual(d["direction_reversal"], 3)
        self.assertEqual(d["unavailable"], 0)
        self.assertEqual(len(self.result["visit_comparisons"]), 90)
        self.assertEqual(len(self.result["paired_comparisons"]), 45)
        self.assertIn(
            b"not a blinded empirical evaluation", (self.archive / "report.md").read_bytes()
        )

    def test_relocation_rebuilds_parent_and_native_reports(self):
        relocated = self.root / "relocated"
        shutil.copytree(self.archive, relocated)
        result = reconstruct(relocated, self.root / "reader")
        self.assertEqual(result, self.result)
        self.assertEqual(
            (self.root / "reader/report.md").read_bytes(), (self.archive / "report.md").read_bytes()
        )
        self.assertEqual(
            (self.root / "reader/studies/full/report.json").read_bytes(),
            (self.archive / "studies/full/report.json").read_bytes(),
        )

    def test_resealed_parent_bias_and_native_attempt_forgery_are_rejected(self):
        parent = self.altered("forged-parent")
        result = json.loads((parent / "report.json").read_text())
        result["comparisons"]["evaluation"]["three-times"]["nominal"]["paired_changes"][
            "bias_pmol"
        ] += 1
        dump(parent / "report.json", result)
        (parent / "report.md").write_bytes(render(result))
        seal(parent)
        with self.assertRaisesRegex(ValueError, "Saved sampling report differs"):
            reconstruct(parent, self.root / "forged-parent-reader")
        native = self.altered("forged-native")
        child = native / "studies/three-times"
        (child / "manifest.json").unlink()
        attempts = json.loads((child / "attempts.json").read_text())
        person = next(iter(attempts["people"].values()))
        person["variants"]["nominal"]["point"]["change_pmol"] += 1
        dump(child / "attempts.json", attempts)
        seal(child)
        seal(native)
        with self.assertRaisesRegex(ValueError, "Saved analysis attempts differ"):
            reconstruct(native, self.root / "forged-native-reader")

    def test_journal_cannot_inject_reports_or_drop_mask_inventory(self):
        for name, mutate in (
            ("injected-report", lambda j: j["full"].update(report={})),
            ("missing-mask", lambda j: j["full"].update(inventory=None)),
        ):
            archive = self.altered(name)
            journal = json.loads((archive / "schedules.json").read_text())
            mutate(journal)
            dump(archive / "schedules.json", journal)
            seal(archive)
            with self.subTest(name=name), self.assertRaises(ValueError):
                reconstruct(archive, self.root / (name + "-reader"))

    def test_poisoned_omitted_evaluation_cells_do_not_change_reduced_native_results(self):
        original = (self.full / "observations.csv").read_bytes()
        rows = list(csv.reader(io.StringIO(original.decode())))[1:]
        for row in rows:
            if row[0] == "invented-evaluation-01" and row[3] == "15":
                row[4:] = ["NaN", "bad status", "bad C-peptide", "bad status"]
        try:
            (self.full / "observations.csv").write_bytes(csv_bytes(rows))
            self.freeze_config(self.root / "poisoned-plan")
        finally:
            (self.full / "observations.csv").write_bytes(original)
        result = run(self.root / "poisoned-plan", self.root / "poisoned-result")
        self.assertFalse(result["coverage"]["complete_cohort"])
        for schedule in self.result["plan"]["design"]["subsets"]:
            self.assertEqual(
                result["schedules"][schedule]["report"],
                self.result["schedules"][schedule]["report"],
            )
            comparison = result["comparisons"]["evaluation"][schedule]["nominal"]["paired_changes"]
            self.assertEqual(comparison["planned_count"], 3)
            self.assertEqual(comparison["compared_count"], 2)
            self.assertEqual(comparison["reference_unavailable_count"], 1)
        self.assertEqual(
            reconstruct(
                self.root / "poisoned-result", self.root / "poisoned-reader", allow_failed=True
            ),
            result,
        )

    def test_missing_requested_interior_time_is_a_retained_failure_not_a_smaller_fit(self):
        original = (self.full / "observations.csv").read_bytes()
        rows = [
            row
            for row in list(csv.reader(io.StringIO(original.decode())))[1:]
            if not (row[0] == "invented-evaluation-01" and row[1] == "before" and row[3] == "60")
        ]
        try:
            (self.full / "observations.csv").write_bytes(csv_bytes(rows))
            self.freeze_config(self.root / "missing-plan")
        finally:
            (self.full / "observations.csv").write_bytes(original)
        result = run(self.root / "missing-plan", self.root / "missing-result")
        self.assertEqual(result["coverage"]["planned_visit_points"], 120)
        self.assertEqual(result["coverage"]["failed_visit_points"], 12)
        for record in result["schedules"].values():
            person = record["report"]["people"]["invented-evaluation-01"]
            self.assertEqual(
                person["variants"]["nominal"]["point"]["visits"]["before"]["status"], "failed"
            )
            self.assertEqual(person["variants"]["nominal"]["attempted_draws"], 0)
        self.assertFalse(result["coverage"]["complete_cohort"])
        self.assertEqual(
            reconstruct(
                self.root / "missing-result", self.root / "missing-reader", allow_failed=True
            ),
            result,
        )


if __name__ == "__main__":
    unittest.main()
