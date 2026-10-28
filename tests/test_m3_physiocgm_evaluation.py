"""Human execution boundaries, exercised only with self-authored records.

The invented ten-person conversion and declared donor coefficients are software
fixtures. These tests neither access the local release nor establish human
predictive performance, lawful access, or independent training reproduction.
"""

import copy
import json
import os
import shutil
import subprocess
import sys
import unittest
from contextlib import ExitStack
from unittest.mock import patch

import test_m3_external_human_freeze as freeze_fixture

from experiments.m0.simglucose.recording import RunInterrupted
from experiments.m3.azt1d.analysis import _expected, _Snapshot
from experiments.m3.azt1d.data import validate_observations
from experiments.m3.common import ROOT, digest, read
from experiments.m3.common import save as save_json
from experiments.m3.physiocgm_evaluation import analysis, study, worker


def save(path, value):
    """Preserve private permissions while deliberately mutating invented artifacts."""
    save_json(path, value)
    path.chmod(0o600)


class PhysioCGMEvaluation(unittest.TestCase):
    def setUp(self):
        fixture = freeze_fixture.ExternalHumanFreeze()
        fixture.setUp()
        self.addCleanup(fixture.doCleanups)
        fixture._freeze()
        self.fixture = fixture
        self.root = fixture.root
        self.freeze = fixture.bundle
        self.request = {
            "schema": "opent1d.physiocgm.evaluation/1",
            "kind": "human",
            "freeze": {
                "directory": str(self.freeze),
                "manifest_sha256": digest((self.freeze / "manifest.json").read_bytes()),
            },
            "authorization": {
                "confirmed": True,
                "scope": "local-external-evaluation",
                "reference": "Invented test authorization, not a real consent record",
            },
            "prior_access": {
                "reviewed": True,
                "status": "present",
                "reference": "Invented observations converted and frozen in this test",
            },
        }
        self.request_path = self.root / "evaluation-request.json"
        self.prepared = self.root / "evaluation-plan"
        self.executed = self.root / "evaluation-study"
        self.reported = self.root / "evaluation-report"
        self._save_request()

    def _save_request(self):
        save(self.request_path, self.request)
        self.request_path.chmod(0o600)

    def _prepare(self):
        return study.prepare(self.request_path, self.prepared)

    def _execute(self):
        self._prepare()
        study.run(self.prepared / "plan.json", self.executed)
        return analysis.reconstruct(self.executed, self.reported)

    @staticmethod
    def _rehash(folder):
        # Exercise semantic checks after an attacker refreshes ordinary hashes.
        (folder / "inventory.json").unlink()
        study.inventory(folder)

    @staticmethod
    def _no_fit():
        stack = ExitStack()
        for target in (
            "experiments.m3.estimator.fit",
            "experiments.m3.azt1d.study.learned_read",
            "experiments.m3.external.model.learned_read",
        ):
            stack.enter_context(patch(target, side_effect=AssertionError("No donor fitting/read")))
        return stack

    def test_complete_cohort_unchanged_model_and_portable_stdlib_report(self):
        # Original donor paths are not part of the executable data boundary.
        shutil.rmtree(self.fixture.source)
        with self._no_fit():
            report = self._execute()
        self.assertEqual(report["evaluation"]["planned_people"], 10)
        self.assertEqual(report["evaluation"]["contributing_people"], 10)
        self.assertEqual(report["evaluation"]["execution_status_counts"], {"completed": 10})
        self.assertTrue(report["evaluation"]["complete_cohort"])
        self.assertFalse(report["refitted_on_external_cohort"])
        self.assertEqual(
            (self.executed / "prepared/freeze/model/model.json").read_bytes(),
            (self.freeze / "model/model.json").read_bytes(),
        )
        for path in (self.executed, *self.executed.rglob("*")):
            self.assertEqual(path.stat().st_mode & 0o077, 0)
        for original in self.root.iterdir():
            if original in {self.executed, self.reported}:
                continue
            if original.is_dir():
                shutil.rmtree(original)
            else:
                original.unlink()
        script = (
            "import sys; from experiments.m3.physiocgm_evaluation.analysis import reconstruct; "
            "reconstruct(sys.argv[1], sys.argv[2]); "
            "assert 'numpy' not in sys.modules; assert 'sklearn' not in sys.modules"
        )
        target = self.root / "isolated-report"
        reconstructed = subprocess.run(
            [sys.executable, "-S", "-c", script, str(self.executed), str(target)],
            cwd=ROOT,
            capture_output=True,
            text=True,
        )
        self.assertEqual(reconstructed.returncode, 0, reconstructed.stderr)
        self.assertEqual(
            (target / "report.json").read_bytes(), (self.reported / "report.json").read_bytes()
        )
        self.assertTrue((target / "access.jsonl").is_file())

    def test_preparation_only_copies_and_verifies_without_forecasts_or_scores(self):
        with self._no_fit(), ExitStack() as stack:
            for target in (
                "experiments.m3.estimator.predict",
                "experiments.m3.azt1d.data.forecast_rows",
                "experiments.m3.azt1d.analysis._expected",
                "experiments.m3.external.metrics.summarize_case",
                "experiments.m3.external.metrics.summarize_study",
            ):
                stack.enter_context(patch(target, side_effect=AssertionError("Prepare only")))
            self._prepare()
        self.assertTrue((self.prepared / "plan.json").is_file())
        self.assertFalse(any(self.prepared.rglob("trace.jsonl")))
        self.assertFalse(any(self.prepared.rglob("report.json")))

    def test_authorization_and_prior_access_rejected_before_freeze_read(self):
        original = copy.deepcopy(self.request)
        changes = (
            ("authorization", "confirmed", False),
            ("authorization", "scope", "local-external-freeze-only"),
            ("authorization", "reference", ""),
            ("prior_access", "reviewed", False),
            ("prior_access", "status", "none"),
            ("prior_access", "reference", ""),
        )
        original_read = _Snapshot.read

        def request_only(snapshot, name):
            self.assertEqual(name, self.request_path.name, "Freeze read before authorization")
            return original_read(snapshot, name)

        for section, key, value in changes:
            with self.subTest(section=section, key=key):
                self.request = copy.deepcopy(original)
                self.request[section][key] = value
                self._save_request()
                with patch.object(_Snapshot, "read", request_only):
                    with self.assertRaises(ValueError):
                        self._prepare()
                self.assertFalse(self.prepared.exists())

    def test_bad_timeout_rejected_before_plan_access(self):
        for timeout in (0, -1, True, float("nan"), float("inf")):
            with self.subTest(timeout=timeout), self.assertRaises(ValueError):
                study.run(self.root / "absent-plan.json", self.executed, timeout=timeout)
            self.assertFalse(self.executed.exists())

    def test_access_append_failure_prevents_model_observation_and_worker_access(self):
        self._prepare()
        original_read = _Snapshot.read

        def control_only(snapshot, name):
            self.assertFalse(name.endswith("model.json"), "Model opened before access receipt")
            self.assertNotIn("/inputs/", "/" + name)
            self.assertFalse(name.endswith("observations.json"))
            return original_read(snapshot, name)

        with (
            patch.object(study, "record_access", side_effect=PermissionError("Invented denial")),
            patch.object(_Snapshot, "read", control_only),
            patch.object(study, "supervise") as supervise,
        ):
            with self.assertRaises(PermissionError):
                study.run(self.prepared / "plan.json", self.executed)
            supervise.assert_not_called()

    def test_reconstruction_access_failure_prevents_forecast_arithmetic(self):
        self._execute()
        with (
            patch.object(analysis, "record_access", side_effect=OSError("Invented denial")),
            patch.object(analysis, "_expected") as arithmetic,
            patch.object(analysis, "_reconstruct") as contents,
        ):
            with self.assertRaises(OSError):
                analysis.reconstruct(self.executed, self.root / "failed-report")
            arithmetic.assert_not_called()
            contents.assert_not_called()
        state, _ = read(self.root / "failed-report/state.json")
        self.assertEqual(state["status"], "failed")
        self.assertNotIn("Invented denial", json.dumps(state))
        self.assertFalse((self.root / "failed-report/report.json").exists())

    def test_modified_source_model_rejected_before_execution(self):
        model_path = self.freeze / "model/model.json"
        model, _ = read(model_path)
        model["intercept"] += 1
        save(model_path, model)
        with self.assertRaises(ValueError):
            self._prepare()
        self.assertFalse(self.executed.exists())

    def test_changed_prepared_model_or_input_never_reaches_worker(self):
        for index, name in enumerate(("model/model.json", "inputs/invented-cgm-1.json")):
            with self.subTest(name=name):
                self.prepared = self.root / ("changed-plan-" + str(index))
                self._prepare()
                path = self.prepared / "freeze" / name
                original = path.read_bytes()
                path.write_bytes(original + b"\n")
                with patch.object(study, "supervise") as supervise:
                    with self.assertRaises(ValueError):
                        study.run(self.prepared / "plan.json", self.root / name.replace("/", "-"))
                    supervise.assert_not_called()
                path.write_bytes(original)

    def test_changed_plan_rules_rejected_before_worker(self):
        self._prepare()
        plan_path = self.prepared / "plan.json"
        plan, _ = read(plan_path)
        plan["rules"]["fitting"] = "allowed"
        save(plan_path, plan)
        with patch.object(study, "supervise") as supervise:
            with self.assertRaises(ValueError):
                study.run(plan_path, self.executed)
            supervise.assert_not_called()

    def test_output_directory_is_exclusive(self):
        self._prepare()
        before = (self.prepared / "plan.json").read_bytes()
        with self.assertRaises(FileExistsError):
            self._prepare()
        self.assertEqual((self.prepared / "plan.json").read_bytes(), before)
        self.executed.mkdir(mode=0o700)
        sentinel = self.executed / "existing"
        sentinel.write_text("preserve existing artifacts")
        with self.assertRaises(FileExistsError):
            study.run(self.prepared / "plan.json", self.executed)
        self.assertEqual(sentinel.read_text(), "preserve existing artifacts")

    def test_single_evaluation_claim_refuses_repeat_without_fresh_observation_read(self):
        self._execute()
        ledger_before = (self.prepared / "ledger.jsonl").read_bytes()
        with patch.object(study, "supervise") as supervise:
            with self.assertRaises(FileExistsError):
                study.run(self.prepared / "plan.json", self.root / "repeat-study")
            supervise.assert_not_called()
        self.assertEqual((self.prepared / "ledger.jsonl").read_bytes(), ledger_before)

    def test_trace_change_rejected_even_after_consistent_ordinary_rehash(self):
        self._execute()
        case = self.executed / "invented-cgm-1"
        run = case / "run"
        trace = run / "trace.jsonl"
        lines = trace.read_text().splitlines()
        for index, line in enumerate(lines):
            row = json.loads(line)
            if row["forecasts"] is not None:
                row["forecasts"]["ridge"] += 1
                lines[index] = json.dumps(row, sort_keys=True)
                break
        else:
            self.fail("Invented fixture produced no scored Ridge prediction")
        trace.write_text("\n".join(lines) + "\n")
        result, _ = read(run / "result.json")
        result["trace_sha256"] = digest(trace.read_bytes())
        save(run / "result.json", result)
        state, _ = read(run / "state.json")
        state["files"] = {name: digest((run / name).read_bytes()) for name in state["files"]}
        save(run / "state.json", state)
        self._rehash(self.executed)
        with self.assertRaises(ValueError):
            analysis.reconstruct(self.executed, self.root / "tampered-report")

    def test_omitted_case_rejected_even_with_rehashed_inventory(self):
        self._execute()
        document, _ = read(self.executed / "study.json")
        document["cases"].pop()
        save(self.executed / "study.json", document)
        self._rehash(self.executed)
        with self.assertRaises(ValueError):
            analysis.reconstruct(self.executed, self.root / "omitted-case-report")

    def test_forged_complete_prefix_or_worker_claim_rejected_after_rehash(self):
        self._execute()
        for change in ("complete-prefix", "worker-claim"):
            with self.subTest(change=change):
                altered = self.root / change
                shutil.copytree(self.executed, altered)
                run = altered / "invented-cgm-1/run"
                if change == "complete-prefix":
                    trace = run / "trace.jsonl"
                    trace.write_text("\n".join(trace.read_text().splitlines()[:20]) + "\n")
                    result, _ = read(run / "result.json")
                    result["trace_sha256"] = digest(trace.read_bytes())
                    save(run / "result.json", result)
                else:
                    save(run / "worker-access.json", {"execution_event_sha256": "0" * 64})
                state, _ = read(run / "state.json")
                state["files"] = {
                    name: digest((run / name).read_bytes()) for name in state["files"]
                }
                save(run / "state.json", state)
                self._rehash(altered)
                with self.assertRaises(ValueError):
                    analysis.reconstruct(altered, self.root / (change + "-report"))

    def test_worker_receipt_cannot_be_reused_after_first_claim(self):
        self._execute()
        case = self.executed / "invented-cgm-1"
        state, _ = read(case / "run/state.json")
        state["status"] = "started"
        save(case / "run/state.json", state)
        (case / "observations.json").unlink()
        with self.assertRaises(FileExistsError):
            worker.evaluate(self.executed, "invented-cgm-1", case / "run")

    def test_worker_trace_refuses_links_nonempty_and_nonprivate_files_without_truncation(self):
        target = self.root / "protected-invented-trace"
        target.write_bytes(b"retain existing trace")
        target.chmod(0o600)
        link = self.root / "symlink-trace"
        link.symlink_to(target)
        hardlink = self.root / "hardlink-trace"
        os.link(target, hardlink)
        for path in (link, hardlink, target):
            with self.subTest(path=path.name), self.assertRaises((OSError, ValueError)):
                worker._trace_stream(path)
            self.assertEqual(target.read_bytes(), b"retain existing trace")
        empty = self.root / "empty-trace"
        empty.touch(mode=0o600)
        empty.chmod(0o644)
        with self.assertRaises(ValueError):
            worker._trace_stream(empty)
        empty.chmod(0o600)
        with worker._trace_stream(empty) as stream:
            stream.write(b"invented new trace")
        with self.assertRaises(ValueError):
            worker._trace_stream(empty)
        self.assertEqual(empty.read_bytes(), b"invented new trace")

    def test_timeout_preserves_valid_trace_prefix_and_all_unattempted_people(self):
        self._prepare()
        registry, _ = read(self.freeze / "registry.json")
        person = registry["people"][0]
        document, _ = read(self.freeze / "inputs" / (person["id"] + ".json"))
        model, _ = read(self.freeze / "model/model.json")
        rows = validate_observations(document, person["id"], *person["bounds_us"])
        prefix = [
            _expected(rows, person["id"], "evaluation", person["bounds_us"], model, origin)
            for origin in person["origins_us"][:20]
        ]
        prefix_file = self.root / "invented-prefix.jsonl"
        prefix_file.write_text("".join(json.dumps(row) + "\n" for row in prefix) + "{")
        code = (
            "import json,pathlib,sys,time; p=pathlib.Path(sys.argv[2]); "
            "receipt=json.loads((p.parent/'execution-access.json').read_text()); "
            "(p/'worker-access.json').write_text(json.dumps("
            "{'execution_event_sha256':receipt['event_sha256']})); "
            "(p/'trace.jsonl').write_bytes(pathlib.Path(sys.argv[1]).read_bytes()); "
            "time.sleep(10)"
        )
        original = study.supervise

        def deadline(command, folder, timeout):
            return original([sys.executable, "-c", code, str(prefix_file)], folder, 0.5)

        with patch.object(study, "supervise", side_effect=deadline):
            with self.assertRaises((RunInterrupted, subprocess.TimeoutExpired)):
                study.run(self.prepared / "plan.json", self.executed)
        report = analysis.reconstruct(self.executed, self.reported)
        self.assertEqual(report["study_status"], "interrupted")
        self.assertEqual(report["evaluation"]["planned_people"], 10)
        self.assertEqual(
            report["evaluation"]["execution_status_counts"],
            {"interrupted": 1, "not_attempted": 9},
        )
        failed = report["evaluation"]["people"][person["id"]]
        self.assertEqual(failed["attempted"], 20)
        self.assertEqual(failed["not_attempted"], len(person["origins_us"]) - 20)
        self.assertTrue(failed["partial_fragment"])
        self.assertFalse(report["evaluation"]["complete_cohort"])


if __name__ == "__main__":
    unittest.main()
