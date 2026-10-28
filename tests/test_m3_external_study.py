"""Synthetic external execution, immutable transfer and artifact failure boundaries."""

import copy
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from test_m3_external_model import declared_fixture

from experiments.m0.simglucose.recording import RunInterrupted
from experiments.m3.azt1d.analysis import _expected
from experiments.m3.common import ROOT, digest, read, save
from experiments.m3.external.analysis import reconstruct
from experiments.m3.external.common import SCHEMA, provenance
from experiments.m3.external.fixtures import generate
from experiments.m3.external.model import export_model
from experiments.m3.external.study import (
    freeze,
    init_ledger,
    inventory,
    observations,
    plan_read,
    registry_check,
    run_study,
    seal,
    supervise,
    validate_plan,
)
from experiments.m3.external.worker import evaluate


class ExternalStudy(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        source = self.root / "source"
        source.mkdir()
        plan, fit, verified = declared_fixture(source)
        self.bundle = self.root / "bundle"
        with patch("experiments.m3.external.model.learned_read", return_value=verified):
            export_model(plan, fit, self.bundle)
        self.registry = generate(self.root / "input", people=2, days=2)
        self.registry_path = self.root / "input/registry.json"
        self.plan = self.root / "plan/plan.json"

    def frozen(self):
        save(self.registry_path, self.registry)
        freeze(self.registry_path, self.bundle, self.plan.parent)
        init_ledger(self.plan)

    def execute(self):
        self.frozen()
        with patch("experiments.m3.estimator.fit", side_effect=AssertionError("No external fit")):
            report = run_study(self.plan, self.root / "study")
        return self.root / "study", report

    def test_complete_cohort_without_fit_and_portable_stdlib_reconstruction(self):
        study, report = self.execute()
        self.assertEqual(report["evaluation"]["contributing_people"], 2)
        self.assertTrue(report["evaluation"]["complete_cohort"])
        self.assertFalse(report["refitted_on_external_cohort"])
        self.assertEqual(
            (study / "model/model.json").read_bytes(), (self.bundle / "model.json").read_bytes()
        )
        for name in ("input", "source", "plan", "bundle"):
            shutil.rmtree(self.root / name)
        # Even a later symlink loop at an original path must not affect reconstruction.
        (self.root / "input").symlink_to(self.root / "input")
        target = self.root / "reconstructed.json"
        result = subprocess.run(
            [
                sys.executable,
                "-S",
                "-m",
                "experiments.m3.external",
                "report",
                "--study",
                str(study),
                "--output",
                str(target),
            ],
            cwd=ROOT,
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(target.read_bytes(), (study / "report.json").read_bytes())

    def test_human_registry_refused_before_model_access(self):
        self.registry["kind"] = "human"
        save(self.registry_path, self.registry)
        with patch("experiments.m3.external.study.load_model") as model:
            with self.assertRaisesRegex(ValueError, "Human external intake"):
                freeze(self.registry_path, self.bundle, self.plan.parent)
            model.assert_not_called()
        self.assertFalse(self.plan.parent.exists())

    def test_bad_deadline_refused_before_any_plan_access(self):
        with patch("experiments.m3.external.study.plan_read") as access:
            for timeout in (0, -1, True, float("nan"), float("inf")):
                with self.subTest(timeout=timeout), self.assertRaises(ValueError):
                    run_study(self.plan, self.root / "forbidden", timeout)
            access.assert_not_called()

    def test_reserved_alias_duplicate_source_and_development_flags_rejected(self):
        for change in ("alias", "path", "hash", "development", "prior"):
            registry = copy.deepcopy(self.registry)
            a, b = registry["people"]
            if change == "alias":
                a["id"] = "model"
            elif change in ("path", "hash"):
                key = "file" if change == "path" else "sha256"
                b["input"][key] = a["input"][key]
            elif change == "development":
                a["development_eligible"] = True
            else:
                registry["prior_access"]["status"] = "none"
            with self.subTest(change=change), self.assertRaises(ValueError):
                registry_check(registry)

    def test_freeze_without_source_records_and_full_missing_input_accounting(self):
        for person in self.registry["people"]:
            Path(person["input"]["file"]).unlink()
        self.frozen()
        report = run_study(self.plan, self.root / "study")
        self.assertEqual(report["evaluation"]["planned_people"], 2)
        self.assertEqual(report["evaluation"]["contributing_people"], 0)
        self.assertEqual(report["evaluation"]["execution_status_counts"], {"failed": 2})
        self.assertEqual(report["evaluation_access"]["snapshot_event_count"], 2)
        for person in report["evaluation"]["people"].values():
            self.assertEqual(person["attempted"], 0)
            self.assertEqual(person["planned"], 576)
            self.assertIsNotNone(person["access"]["input"])
            self.assertIsNone(person["access"]["execution"])

    def test_modified_registry_and_model_fail_before_new_access(self):
        self.frozen()
        plan, _ = read(self.plan)
        plan["registry"]["source"]["reference"] = "changed"
        plan["identity"]["source"]["reference"] = "changed"
        with self.assertRaisesRegex(ValueError, "registry identity"):
            validate_plan(plan)
        ledger = Path(self.registry["ledger"])
        before = ledger.read_bytes()
        (self.plan.parent / "model/model.json").write_text("{}")
        with self.assertRaises(ValueError):
            run_study(self.plan, self.root / "study")
        self.assertEqual(ledger.read_bytes(), before)
        self.assertFalse((self.root / "study").exists())

    def test_changed_trace_rejected_even_with_consistent_hash_inventories(self):
        study, _ = self.execute()
        pid = self.registry["people"][0]["id"]
        folder = study / pid / "run"
        trace = folder / "trace.jsonl"
        lines = trace.read_text().splitlines()
        row = json.loads(lines[12])
        row["forecasts"]["ridge"] += 1
        lines[12] = json.dumps(row)
        trace.write_text("\n".join(lines) + "\n")
        result, _ = read(folder / "result.json")
        result["trace_sha256"] = digest(trace.read_bytes())
        save(folder / "result.json", result)
        state, _ = read(folder / "state.json")
        seal(folder, state)
        inventory(study)
        with self.assertRaises(ValueError):
            reconstruct(study)

    def test_reused_worker_receipt_is_refused_before_observation_read(self):
        study, _ = self.execute()
        pid = self.registry["people"][0]["id"]
        folder = study / pid / "run"
        state, _ = read(folder / "state.json")
        state["status"] = "started"
        save(folder / "state.json", state)
        (study / pid / "observations.json").unlink()
        with self.assertRaises(FileExistsError):
            evaluate(study, pid, folder)

    def test_partial_failure_preserved_and_other_person_still_evaluated(self):
        self.frozen()
        plan, _, model = plan_read(self.plan)
        person = self.registry["people"][0]
        rows = observations(Path(person["input"]["file"]).read_bytes(), person)
        expected = [
            _expected(rows, person["id"], "evaluation", person["bounds_us"], model, t)
            for t in person["origins_us"][:20]
        ]

        def failed_first(command, folder, timeout):
            if folder.parent.name != person["id"]:
                return supervise(command, folder, timeout)
            folder.mkdir()
            receipt, _ = read(folder.parent / "execution-access.json")
            save(folder / "worker-access.json", {"execution_event_sha256": receipt["event_sha256"]})
            (folder / "trace.jsonl").write_text(
                "".join(json.dumps(row) + "\n" for row in expected) + "{"
            )
            seal(
                folder,
                {
                    "schema": SCHEMA,
                    "status": "failed",
                    "provenance": provenance(),
                    "elapsed_seconds": 0.1,
                    "error": {"type": "ValueError"},
                },
            )
            raise ValueError("Synthetic failure")

        with patch("experiments.m3.external.study.supervise", side_effect=failed_first):
            report = run_study(self.plan, self.root / "study")
        self.assertEqual(
            report["evaluation"]["execution_status_counts"], {"completed": 1, "failed": 1}
        )
        failed = report["evaluation"]["people"][person["id"]]
        self.assertEqual(failed["attempted"], 20)
        self.assertEqual(failed["not_attempted"], 556)
        self.assertTrue(failed["partial_fragment"])
        self.assertFalse(report["evaluation"]["complete_cohort"])
        self.assertEqual(reconstruct(self.root / "study"), report)
        state_path = self.root / "study" / person["id"] / "run/state.json"
        state, _ = read(state_path)
        del state["error"]
        save(state_path, state)
        inventory(self.root / "study")
        with self.assertRaisesRegex(ValueError, "original external failure"):
            reconstruct(self.root / "study")

    def test_interruption_preserves_remaining_unattempted_people(self):
        self.frozen()
        with patch("experiments.m3.external.study.supervise", side_effect=KeyboardInterrupt):
            with self.assertRaises(KeyboardInterrupt):
                run_study(self.plan, self.root / "study")
        report = reconstruct(self.root / "study")
        self.assertEqual(report["study_status"], "interrupted")
        self.assertEqual(
            report["evaluation"]["execution_status_counts"], {"interrupted": 1, "not_attempted": 1}
        )
        self.assertEqual(report["evaluation"]["planned_people"], 2)

    def test_repeated_evaluation_keeps_old_snapshot_and_discloses_new_access(self):
        study, first = self.execute()
        second = run_study(self.plan, self.root / "repeat")
        self.assertEqual(first["evaluation_access"]["snapshot_event_count"], 4)
        self.assertEqual(second["evaluation_access"]["snapshot_event_count"], 8)
        for person in second["evaluation"]["people"].values():
            self.assertTrue(person["access"]["input"]["repeated_event"])
            self.assertTrue(person["access"]["execution"]["repeated_event"])
        self.assertEqual(reconstruct(study), first)

    def test_omitting_a_planned_case_fails_even_after_rehash(self):
        study, _ = self.execute()
        document, _ = read(study / "study.json")
        document["cases"].pop()
        save(study / "study.json", document)
        inventory(study)
        with self.assertRaisesRegex(ValueError, "cohort changed"):
            reconstruct(study)

    def test_real_worker_deadline_seals_partial_output_and_safe_error(self):
        output = self.root / "timeout"
        code = (
            "import pathlib,sys,time; p=pathlib.Path(sys.argv[1]); "
            "(p/'trace.jsonl').write_text('partial'); time.sleep(10)"
        )
        with self.assertRaises((RunInterrupted, subprocess.TimeoutExpired)):
            supervise([sys.executable, "-c", code], output, 0.2)
        state, _ = read(output / "state.json")
        self.assertEqual(state["status"], "interrupted")
        self.assertEqual((output / "trace.jsonl").read_text(), "partial")
        self.assertEqual(state["files"]["trace.jsonl"], digest(b"partial"))
        self.assertIn("type", state["error"])
