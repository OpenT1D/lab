"""M3 shared freeze binds bytes and preserves native causal/failure semantics."""

import copy
import json
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from experiments.catalogue.storage import encoded
from experiments.m3.comparison import fixtures, study
from experiments.m3.researcher.fixtures import write_predictor
from experiments.shared_services import execution, forecasting, routes, store, workbench


class M3Services(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="m3-services-")
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name).resolve()
        self.config = fixtures.fixture(self.root / "fixture")
        self.inputs = {"config.json": self.root / "fixture/comparison.json"}

    def save(self):
        self.inputs["config.json"].write_bytes(encoded(self.config))

    def capture(self, name="plan"):
        folder = self.root / name
        descriptor = routes.capture("m3-compare", self.inputs, folder)
        return folder, descriptor

    def test_passive_intake_freezes_all_bytes_and_export_survives_original_removal(self):
        sentinel = self.root / "must-not-execute"
        declaration = write_predictor(
            self.root / "passive",
            f"from pathlib import Path\nPath({str(sentinel)!r}).touch()\n"
            "def predict(request, settings): return 1.0\n",
            {},
            name="passive",
            reference="Invented passive-intake counterexample",
        )
        self.config["candidates"][0] = {"id": "passive", "declaration": str(declaration)}
        self.save()
        folder, descriptor = self.capture()
        self.assertFalse(sentinel.exists())
        self.assertEqual(len(descriptor["boundary"]["planned_slots"]), 4)
        self.assertEqual(forecasting.read(folder / "original/config.json"), self.config)
        shutil.rmtree(self.root / "fixture")
        shutil.rmtree(self.root / "passive")
        routes.validate_freeze(folder, descriptor, current=False)
        exported = forecasting.materialize(folder, self.root / "export")
        recaptured = routes.capture("m3-compare", exported["inputs"], self.root / "recaptured")
        self.assertEqual(
            recaptured["boundary"],
            descriptor["boundary"]
            | {
                "binding": descriptor["boundary"]["binding"]
                | {"predictors": recaptured["boundary"]["binding"]["predictors"]}
            },
        )
        self.assertFalse(sentinel.exists())
        (folder / "original/candidates/passive/source.py").write_text("changed")
        with self.assertRaisesRegex(ValueError, "originals differ"):
            routes.validate_freeze(folder, descriptor, current=False)

    def test_refuses_changed_source_future_features_and_unknown_reader(self):
        original = copy.deepcopy(self.config)
        candidate = Path(self.config["candidates"][0]["declaration"])
        declaration = json.loads(candidate.read_bytes())
        declaration["contract"]["future_carbs"] = True
        candidate.write_bytes(encoded(declaration))
        with self.assertRaisesRegex(ValueError, "contract fields"):
            self.capture()
        declaration["contract"].pop("future_carbs")
        candidate.write_bytes(encoded(declaration))
        Path(declaration["source"]["file"]).write_text("def predict(request, settings): return 0\n")
        with self.assertRaisesRegex(ValueError, "Source hash mismatch"):
            self.capture()
        self.assertEqual(self.config, original)

    def test_unavailable_and_hash_mismatched_observations_keep_full_plan(self):
        Path(self.config["people"][0]["input"]["file"]).unlink()
        Path(self.config["people"][1]["input"]["file"]).write_text("{}")
        folder, descriptor = self.capture()
        self.assertEqual(len(descriptor["boundary"]["planned_slots"]), 4)
        access = store.read(folder / "original/capture.json")
        self.assertEqual([row["status"] for row in access.values()], ["unavailable", "captured"])
        invocation = forecasting.materialize(folder, self.root / "invocation")["inputs"]
        study.run_study(invocation["config.json"], self.root / "native")
        result = routes.native_result(self.root / "native", descriptor, folder)
        self.assertEqual(result["completeness"], "incomplete")
        self.assertEqual(set(result["slot_statuses"].values()), {"failed"})
        report = store.read(self.root / "native/report.json")
        self.assertEqual(report["common"]["planned_people"], 2)
        self.assertEqual(report["common"]["contributing_people"], 0)
        for pid, person in report["common"]["people"].items():
            planned = next(p for p in self.config["people"] if p["id"] == pid)
            self.assertEqual(person["planned_origins"], len(planned["origins_us"]))
        unknown = copy.deepcopy(descriptor)
        unknown["reader"]["report_schema"] += "-unknown"
        (folder / "descriptor.json").write_bytes(encoded(unknown))
        with self.assertRaisesRegex(ValueError, "trusted M3 reader"):
            routes.validate_freeze(folder, unknown, current=False)

    def test_failed_long_prefix_remains_ineligible_and_binds_original_source(self):
        cutoff = self.config["people"][0]["origins_us"][-20]
        source = (
            "def predict(request, settings):\n"
            f"    if request['origin_us'] >= {cutoff}: raise ValueError('invented failure')\n"
            "    return request['values_mg_dl'][-1]\n"
        )
        declaration = write_predictor(
            self.root / "failed",
            source,
            {},
            name="failed-prefix",
            reference="Invented long failed prefix",
        )
        self.config["candidates"][0] = {"id": "failed-prefix", "declaration": str(declaration)}
        self.save()
        folder, descriptor = self.capture()
        invocation = forecasting.materialize(folder, self.root / "invocation")["inputs"]
        study.run_study(invocation["config.json"], self.root / "native")
        result = routes.native_result(self.root / "native", descriptor, folder)
        report = store.read(self.root / "native/report.json")
        self.assertEqual(result["completeness"], "incomplete")
        self.assertEqual(report["common"]["contributing_people"], 0)
        self.assertTrue(
            all(
                p["candidate_scored"]["failed-prefix"] > 288 and not p["eligible_for_primary"]
                for p in report["common"]["people"].values()
            )
        )
        # A fully valid different native comparison cannot be imported under this freeze.
        altered = copy.deepcopy(descriptor)
        altered["boundary"]["binding"]["implementation_sha256"] = {}
        with self.assertRaisesRegex(ValueError, "implementation differs"):
            routes.native_result(self.root / "native", altered, folder)
        (self.root / "native/report.md").write_text("resealed invented report")
        study.seal(self.root / "native")
        with self.assertRaisesRegex(ValueError, "Saved M3 report differs"):
            routes.native_result(self.root / "native", descriptor, folder)

    def test_inspection_changes_when_referenced_bytes_change(self):
        before = workbench.inspect("m3-compare", self.inputs, self.root / "before")
        person = Path(self.config["people"][0]["input"]["file"])
        person.write_bytes(person.read_bytes() + b"\n")
        after = workbench.inspect("m3-compare", self.inputs, self.root / "after")
        self.assertNotEqual(before["input_sha256"], after["input_sha256"])
        self.assertFalse(after["observation_bytes_verified"])
        store.create(self.root / "project", "Changed since validation")
        with store.opened(self.root / "project", write_access=True) as project:
            with self.assertRaisesRegex(ValueError, "Inputs changed since validation"):
                routes.freeze(
                    project, "m3-compare", self.inputs, expected_input_sha256=before["input_sha256"]
                )
            self.assertFalse(project.plans)

    def test_unfinished_recovery_preserves_all_slots_and_never_adopts_pids(self):
        store.create(self.root / "project", "M3 interrupted start")
        with store.opened(self.root / "project", write_access=True) as project:
            plan = routes.freeze(project, "m3-compare", self.inputs)
            attempt, work = execution.begin(project, plan)
            (work / "diagnostic").write_bytes(b"incomplete owned work")
            with self.assertRaisesRegex(ValueError, "Recover unfinished"):
                execution.begin(project, plan)
            with self.assertRaisesRegex(ValueError, "Explicit confirmation"):
                execution.recover(project, attempt)
            with patch(
                "experiments.shared_services.execution.supervise", side_effect=AssertionError
            ):
                execution.recover(project, attempt, execution_stopped=True)
            data, evidence = project.finishes[attempt]
            self.assertEqual(len(data["result"]["slot_statuses"]), 4)
            self.assertEqual((evidence / "diagnostic").read_bytes(), b"incomplete owned work")
            self.assertEqual(data["receipt"]["remaining_owned_processes"], [])


if __name__ == "__main__":
    unittest.main()
