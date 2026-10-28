"""Frozen intake, causal worker and failure-aware reconstruction checks for M5."""

import copy
import os
import select
import shutil
import signal
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from experiments.m5.researcher_workflow import report, run
from experiments.m5.researcher_workflow.contract import (
    ARCHIVE_FILES,
    BUNDLE_FILES,
    INPUT_SCHEMA,
    decode,
    request,
    rows,
    sha,
    snapshot,
)
from experiments.m5.synthetic_prognosis.run import assess as original_assess
from experiments.m5.synthetic_prognosis.run import fixture


class M5ResearcherWorkflowTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temporary = tempfile.TemporaryDirectory(prefix="opent1d-m5-tests-")
        cls.root = Path(cls.temporary.name)
        cls.bundle = cls.root / "example"
        run.export_example(cls.bundle)
        cls.archive = cls.root / "successful"
        cls.successful = run.execute(cls.bundle, cls.archive)

    @classmethod
    def tearDownClass(cls):
        cls.temporary.cleanup()

    def setUp(self):
        self.temporary_case = tempfile.TemporaryDirectory(dir=self.root)
        self.addCleanup(self.temporary_case.cleanup)
        self.directory = Path(self.temporary_case.name)

    def copied_bundle(self):
        bundle = self.directory / "bundle"
        shutil.copytree(self.bundle, bundle)
        return bundle

    def copied_archive(self):
        archive = self.directory / "archive"
        shutil.copytree(self.archive, archive)
        return archive

    @staticmethod
    def read(directory, name):
        return decode((directory / name).read_bytes())

    @staticmethod
    def change_model(bundle, *, source=None, state=None):
        if source is not None:
            (bundle / "model.py").write_bytes(source)
        if state is not None:
            (bundle / "state.json").write_bytes(state)
        model = M5ResearcherWorkflowTests.read(bundle, "model.json")
        model["source_sha256"] = sha((bundle / "model.py").read_bytes())
        model["state_sha256"] = sha((bundle / "state.json").read_bytes())
        run.write(bundle / "model.json", model)
        return model

    @staticmethod
    def rehash(archive):
        manifest = M5ResearcherWorkflowTests.read(archive, "manifest.json")
        manifest["files"] = {
            name: sha((archive / name).read_bytes()) for name in sorted(ARCHIVE_FILES)
        }
        run.write(archive / "manifest.json", manifest)

    def test_real_fresh_workers_match_original_synthetic_numerics(self):
        result = self.successful
        original = original_assess(fixture())
        self.assertEqual(result["roster_count"], 32)
        self.assertEqual(result["development_eligible_count"], 20)
        self.assertEqual(result["evaluation_eligible_count"], 7)
        self.assertEqual(result["paired_count"], 7)
        self.assertEqual(result["candidate_coverage"], 1)
        self.assertEqual(result["comparison_status"], "complete")
        self.assertTrue(result["candidate_execution_complete"])
        self.assertFalse(result["human_execution_authorized"])
        self.assertFalse(result["treatment_effect_or_cure_estimated"])
        self.assertEqual(result["baseline_mae_all_eligible_u_day"], original["baseline_mae_u_day"])
        self.assertEqual(result["candidate_mae_paired_u_day"], original["added_mae_u_day"])
        self.assertEqual(
            result["mae_change_candidate_minus_baseline_u_day"],
            original["mae_change_added_minus_baseline_u_day"],
        )
        for saved, expected in zip(
            result["evaluation_predictions"], original["evaluation_predictions"], strict=True
        ):
            self.assertEqual(saved["alias"], expected["alias"])
            self.assertEqual(saved["candidate_status"], "completed")
            self.assertEqual(
                saved["candidate_prediction_u_day"], expected["added_prediction_u_day"]
            )
            self.assertEqual([attempt["attempt"] for attempt in saved["attempts"]], [1, 2])
            self.assertEqual(saved["attempts"][0]["runtime"], saved["attempts"][1]["runtime"])
        self.assertEqual(report.reconstruct(self.archive), result)

    def test_saved_requests_omit_identity_split_outcome_and_future_infusions(self):
        expected_keys = {
            "schema",
            "prior_insulin_u_day",
            "prior_glycemic_status_mg_dl",
            "landmark_day_after_first_infusion",
            "observed_function_index",
        }
        packet = {person["alias"]: person for person in fixture()["people"]}
        predictions = self.read(self.archive, "predictions.json")
        for saved in predictions:
            person = packet[saved["alias"]]
            record = saved["request"]
            self.assertEqual(set(record), expected_keys)
            self.assertEqual(record["schema"], INPUT_SCHEMA)
            self.assertEqual(
                record["prior_insulin_u_day"], person["prior_insulin"]["units_per_day"]
            )
            self.assertEqual(
                record["prior_glycemic_status_mg_dl"], person["glycemic_status"]["mg_dl"]
            )
            self.assertEqual(record["landmark_day_after_first_infusion"], person["mmtt"]["day"])
            self.assertEqual(
                record["observed_function_index"],
                person["mmtt"]["stimulated_c_peptide_90"]
                / (person["mmtt"]["stimulated_glucose_90"] / 100),
            )
        row = copy.deepcopy(rows()[1][0][1])
        original = request(row)
        row.update(alias="PRIVATE", split="evaluation", outcome=999, infusion_days=[0, 150])
        self.assertEqual(request(row), original)
        people = {person["alias"]: person for person in self.successful["people"]}
        self.assertEqual(people["SYN012"]["intervening_infusion_days"], [150])
        self.assertFalse(people["SYN020"]["eligible"])
        self.assertFalse(people["SYN020"]["y1_present"])
        self.assertTrue(people["SYN020"]["visit15_present"])
        self.assertIn("missing_or_ambiguous_first_infusion_y1", people["SYN020"]["issues"])

    def test_reconstruction_imports_no_candidate_and_never_refits(self):
        archive = self.copied_archive()
        self.change_model(archive, source=b'raise RuntimeError("Candidate must not execute")\n')
        with (
            patch.object(run, "fit", side_effect=AssertionError("Reconstruction refitted")),
            patch.object(run.subprocess, "Popen", side_effect=AssertionError("Worker launched")),
        ):
            sealed = run.seal(archive)
            result = report.reconstruct(archive)
        self.assertEqual(result, sealed)
        self.assertEqual(
            result["evaluation_predictions"], self.successful["evaluation_predictions"]
        )
        self.assertEqual(
            result["candidate_mae_paired_u_day"], self.successful["candidate_mae_paired_u_day"]
        )
        self.assertNotEqual(result["source_sha256"], self.successful["source_sha256"])

    def test_frozen_bundle_hashes_runtime_dependencies_and_training_are_enforced(self):
        mutations = {
            "source_hash": lambda model: model.update(source_sha256="0" * 64),
            "state_hash": lambda model: model.update(state_sha256="0" * 64),
            "dependency": lambda model: model["runtime"].update(dependencies=["numpy"]),
            "python": lambda model: model["runtime"].update(python_major_minor="0.0"),
            "evaluation_training": lambda model: model["training"]["participant_aliases"].append(
                "SYN004"
            ),
            "wrong_training_fixture": lambda model: model["training"].update(
                fixture_sha256="0" * 64
            ),
            "wrong_phase": lambda model: model["training"].update(phase="evaluation"),
            "unknown_field": lambda model: model.update(human_execution_authorized=True),
            "unsafe_identifier": lambda model: model.update(model_id="line\nbreak"),
        }
        for label, mutate in mutations.items():
            with self.subTest(label=label):
                bundle = self.directory / label
                shutil.copytree(self.bundle, bundle)
                model = self.read(bundle, "model.json")
                mutate(model)
                run.write(bundle / "model.json", model)
                output = self.directory / (label + "-output")
                with (
                    patch.object(run, "fit", side_effect=AssertionError("Rejected bundle fitted")),
                    self.assertRaises(ValueError),
                ):
                    run.execute(bundle, output)
                self.assertFalse(output.exists())

    def test_duplicate_nonfinite_and_nonobject_frozen_state_are_rejected(self):
        states = (b'{"value": 1, "value": 2}', b'{"value": NaN}', b'{"value": 1e999}', b"[]")
        for index, state in enumerate(states):
            with self.subTest(state=state):
                bundle = self.directory / str(index)
                shutil.copytree(self.bundle, bundle)
                self.change_model(bundle, state=state)
                output = self.directory / f"{index}-output"
                with self.assertRaises(ValueError):
                    run.execute(bundle, output)
                self.assertFalse(output.exists())
        with self.assertRaisesRegex(ValueError, "Duplicate JSON"):
            decode(b'{"outer": {"key": 1, "key": 2}}')

    def test_bundle_and_archive_reject_extra_files_and_symlinks(self):
        bundle = self.copied_bundle()
        (bundle / "unregistered.py").write_text("pass\n")
        with self.assertRaisesRegex(ValueError, "Unexpected or missing"):
            run.execute(bundle, self.directory / "output")
        (bundle / "unregistered.py").unlink()
        (bundle / "state.json").unlink()
        (bundle / "state.json").symlink_to(self.bundle / "state.json")
        with self.assertRaisesRegex(ValueError, "regular file"):
            snapshot(bundle, BUNDLE_FILES)
        linked_directory = self.directory / "linked"
        linked_directory.symlink_to(self.bundle, target_is_directory=True)
        with self.assertRaisesRegex(ValueError, "regular directory"):
            snapshot(linked_directory, BUNDLE_FILES)
        archive = self.copied_archive()
        (archive / "unregistered.txt").write_text("not part of the archive\n")
        with self.assertRaisesRegex(ValueError, "Unexpected or missing"):
            report.reconstruct(archive)
        (archive / "unregistered.txt").unlink()
        (archive / "predictions.json").unlink()
        (archive / "predictions.json").symlink_to(self.archive / "predictions.json")
        with self.assertRaisesRegex(ValueError, "regular file"):
            report.reconstruct(archive)

    def test_fresh_workers_retain_failures_invalid_output_and_nondeterminism(self):
        bundle = self.copied_bundle()
        self.change_model(
            bundle,
            source=b"""import os
import platform


def predict(record, state):
    expected = {"schema", "prior_insulin_u_day", "prior_glycemic_status_mg_dl",
                "landmark_day_after_first_infusion", "observed_function_index"}
    if set(record) != expected:
        raise RuntimeError("Unexpected candidate information")
    prior = record["prior_insulin_u_day"]
    if prior == 31:
        raise RuntimeError("Deliberate failure")
    if prior == 29:
        return True
    if prior == 27:
        return os.getpid() / 1000000
    if prior == 25:
        platform.python_implementation = lambda: "wrong implementation"
    return prior
""",
        )
        archive = self.directory / "mixed"
        result = run.execute(bundle, archive)
        by_alias = {item["alias"]: item for item in result["evaluation_predictions"]}
        self.assertEqual(by_alias["SYN004"]["candidate_status"], "failed")
        self.assertEqual(by_alias["SYN008"]["candidate_status"], "failed")
        self.assertEqual(by_alias["SYN012"]["candidate_status"], "not_reproducible")
        self.assertEqual(by_alias["SYN016"]["candidate_status"], "failed")
        for alias in ("SYN004", "SYN008"):
            self.assertEqual(
                [attempt["status"] for attempt in by_alias[alias]["attempts"]],
                ["worker_failed", "worker_failed"],
            )
        self.assertEqual(
            [attempt["status"] for attempt in by_alias["SYN016"]["attempts"]],
            ["invalid_output", "invalid_output"],
        )
        self.assertEqual(result["paired_count"], 3)
        self.assertEqual(result["candidate_coverage"], 3 / 7)
        self.assertEqual(result["comparison_status"], "incomplete")
        self.assertTrue(result["candidate_execution_complete"])
        self.assertEqual(
            result["baseline_mae_all_eligible_u_day"],
            self.successful["baseline_mae_all_eligible_u_day"],
        )
        self.assertEqual(report.reconstruct(archive), result)

    def test_worker_timeout_is_retained_without_a_prediction(self):
        bundle = self.copied_bundle()
        self.change_model(
            bundle,
            source=b"import time\ndef predict(record, state):\n    time.sleep(10)\n    return 1\n",
        )
        result = run.attempt(snapshot(bundle, BUNDLE_FILES), request(rows()[1][0][1]), 1, 0.05)
        self.assertEqual(
            result,
            {"attempt": 1, "status": "timeout", "prediction_u_day": None, "runtime": None},
        )

    def test_partial_pairs_and_zero_pairs_keep_the_complete_eligible_denominator(self):
        baseline = self.read(self.archive, "baseline.json")
        predictions = self.read(self.archive, "predictions.json")
        model = self.read(self.archive, "model.json")
        for saved in predictions[2:]:
            saved["attempts"] = [
                {
                    "attempt": index,
                    "status": "worker_failed",
                    "prediction_u_day": None,
                    "runtime": None,
                }
                for index in (1, 2)
            ]
        result = report.assess(fixture(), baseline, predictions, model)
        paired = result["evaluation_predictions"][:2]
        candidate_mae = (
            sum(
                abs(
                    item["candidate_prediction_u_day"]
                    - item["observed_reported_insulin_mean_u_day"]
                )
                for item in paired
            )
            / 2
        )
        baseline_mae = (
            sum(
                abs(
                    item["baseline_prediction_u_day"] - item["observed_reported_insulin_mean_u_day"]
                )
                for item in paired
            )
            / 2
        )
        self.assertEqual(result["paired_count"], 2)
        self.assertEqual(result["candidate_coverage"], 2 / 7)
        self.assertEqual(result["candidate_mae_paired_u_day"], candidate_mae)
        self.assertEqual(result["baseline_mae_paired_u_day"], baseline_mae)
        self.assertEqual(
            result["mae_change_candidate_minus_baseline_u_day"], candidate_mae - baseline_mae
        )
        self.assertEqual(
            result["baseline_mae_all_eligible_u_day"],
            self.successful["baseline_mae_all_eligible_u_day"],
        )
        for saved in predictions:
            saved["attempts"] = []
        result = report.assess(fixture(), baseline, predictions, model)
        self.assertEqual(result["paired_count"], 0)
        self.assertEqual(result["candidate_coverage"], 0)
        for metric in (
            "candidate_mae_paired_u_day",
            "baseline_mae_paired_u_day",
            "mae_change_candidate_minus_baseline_u_day",
        ):
            self.assertIsNone(result[metric])
        self.assertFalse(result["candidate_execution_complete"])
        self.assertIn(b"unavailable", report.markdown(result))

    def test_rehashed_tampering_does_not_bypass_reconstruction(self):
        mutations = {
            "report": ("report.json", lambda value: value.update(human_execution_authorized=True)),
            "prediction": ("predictions.json", lambda value: value[0].update(alias="SYN999")),
            "causal_request": (
                "predictions.json",
                lambda value: value[0]["request"].update(outcome=99),
            ),
            "baseline_prediction": (
                "predictions.json",
                lambda value: value[0].update(baseline_prediction_u_day=99),
            ),
            "baseline_coefficients": (
                "baseline.json",
                lambda value: value["coefficients"].__setitem__(0, value["coefficients"][0] + 1),
            ),
            "baseline_preprocessing": (
                "baseline.json",
                lambda value: value["means"].__setitem__(0, value["means"][0] + 1),
            ),
            "fixture": ("fixture.json", lambda value: value["people"][0].update(alias="SYN999")),
            "protocol": (
                "protocol.json",
                lambda value: value.update(human_execution_authorized=True),
            ),
            "provenance_revision": (
                "provenance.json",
                lambda value: value.update(git_revision="unknown"),
            ),
            "provenance_runtime": (
                "provenance.json",
                lambda value: value["host_runtime"].update(implementation="unexpected"),
            ),
            "provenance_deadline": (
                "provenance.json",
                lambda value: value.update(worker_timeout_seconds=True),
            ),
            "prediction_runtime": (
                "predictions.json",
                lambda value: value[0]["attempts"][0]["runtime"].update(
                    python_version=value[0]["attempts"][0]["runtime"]["python_major_minor"] + ".999"
                ),
            ),
            "attempt_identity": (
                "predictions.json",
                lambda value: value[0]["attempts"][0].update(attempt=True),
            ),
            "boolean_prediction": (
                "predictions.json",
                lambda value: value[0]["attempts"][0].update(prediction_u_day=True),
            ),
        }
        for label, (name, mutate) in mutations.items():
            with self.subTest(label=label):
                archive = self.directory / label
                shutil.copytree(self.archive, archive)
                value = self.read(archive, name)
                mutate(value)
                run.write(archive / name, value)
                self.rehash(archive)
                with self.assertRaises(ValueError):
                    report.reconstruct(archive)

    def test_interruption_preserves_completed_attempt_and_unattempted_roster(self):
        archive = self.directory / "interrupted"
        original_attempt = run.attempt
        calls = 0

        def interrupt_after_first(*args):
            nonlocal calls
            calls += 1
            if calls == 2:
                raise KeyboardInterrupt("Deliberate interruption")
            return original_attempt(*args)

        with (
            patch.object(run, "attempt", side_effect=interrupt_after_first),
            self.assertRaises(KeyboardInterrupt),
        ):
            run.execute(self.bundle, archive)
        result = report.reconstruct(archive)
        self.assertEqual(result["roster_count"], 32)
        self.assertEqual(result["paired_count"], 0)
        self.assertEqual(result["evaluation_predictions"][0]["candidate_status"], "interrupted")
        self.assertEqual(result["evaluation_predictions"][0]["attempts"][0]["status"], "completed")
        self.assertEqual(
            result["evaluation_predictions"][0]["attempts"][1]["status"], "interrupted"
        )
        self.assertTrue(
            all(
                item["candidate_status"] == "not_attempted"
                for item in result["evaluation_predictions"][1:]
            )
        )
        self.assertFalse(result["candidate_execution_complete"])

    def test_interrupted_atomic_prediction_write_preserves_completed_attempt(self):
        archive = self.directory / "interrupted-write"
        original_replace = Path.replace
        replacements = 0

        def interrupt_second_prediction_replace(path, target):
            nonlocal replacements
            if path.name == "predictions.json.tmp":
                replacements += 1
                if replacements == 2:
                    raise KeyboardInterrupt("Interrupted prediction replacement")
            return original_replace(path, target)

        first = self.read(self.archive, "predictions.json")[0]["attempts"][0]
        with (
            patch.object(run, "attempt", return_value=copy.deepcopy(first)),
            patch.object(
                Path, "replace", autospec=True, side_effect=interrupt_second_prediction_replace
            ),
            self.assertRaises(KeyboardInterrupt),
        ):
            run.execute(self.bundle, archive)
        self.assertFalse((archive / "predictions.json.tmp").exists())
        result = report.reconstruct(archive)
        self.assertEqual(result["roster_count"], 32)
        self.assertEqual(result["paired_count"], 0)
        self.assertEqual(result["evaluation_predictions"][0]["candidate_status"], "incomplete")
        self.assertEqual(result["evaluation_predictions"][0]["attempts"], [first])
        self.assertTrue(
            all(
                item["candidate_status"] == "not_attempted"
                for item in result["evaluation_predictions"][1:]
            )
        )

    def test_host_sigterm_cleans_up_worker_and_restores_handlers(self):
        bundle = self.copied_bundle()
        archive = self.directory / "terminated"
        readiness = self.directory / "worker-ready"
        os.mkfifo(readiness)
        descriptor = os.open(readiness, os.O_RDONLY | os.O_NONBLOCK)
        self.change_model(
            bundle,
            source=f"""import os
import time


def predict(record, state):
    with open({str(readiness)!r}, "w") as stream:
        stream.write(str(os.getpid()))
        stream.flush()
    time.sleep(10)
    return 1
""".encode(),
        )
        host_probe = """import signal
import sys
from experiments.m5.researcher_workflow import run
signals = [signal.SIGTERM, signal.SIGHUP]
previous = {sig: signal.getsignal(sig) for sig in signals}
try:
    run.execute(sys.argv[1], sys.argv[2])
except KeyboardInterrupt:
    assert previous == {sig: signal.getsignal(sig) for sig in signals}
    print("handlers restored")
else:
    raise AssertionError("Host was not interrupted")
"""
        worker_pid = None
        process = subprocess.Popen(
            [sys.executable, "-c", host_probe, str(bundle), str(archive)],
            cwd=Path(__file__).resolve().parents[1],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        try:
            ready, _, _ = select.select([descriptor], [], [], 3)
            self.assertTrue(ready, "Worker did not reach its prediction entrypoint")
            worker_pid = int(os.read(descriptor, 64))
            process.send_signal(signal.SIGTERM)
            stdout, stderr = process.communicate(timeout=3)
            self.assertEqual(process.returncode, 0, stderr.decode())
            self.assertEqual(stdout, b"handlers restored\n")
            with self.assertRaises(ProcessLookupError):
                os.kill(worker_pid, 0)
            result = report.reconstruct(archive)
            self.assertEqual(result["evaluation_predictions"][0]["candidate_status"], "interrupted")
            self.assertEqual(
                result["evaluation_predictions"][0]["attempts"][0]["status"], "interrupted"
            )
            self.assertTrue(
                all(
                    item["candidate_status"] == "not_attempted"
                    for item in result["evaluation_predictions"][1:]
                )
            )
            self.assertFalse(result["candidate_execution_complete"])
        finally:
            os.close(descriptor)
            if process.poll() is None:
                process.kill()
            process.communicate()
            if worker_pid is not None:
                try:
                    os.killpg(worker_pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass

    def test_rehashed_implementation_and_tooling_changes_are_rejected(self):
        for name in ("source-worker.py", "tooling-uv.lock"):
            with self.subTest(name=name):
                archive = self.directory / name
                shutil.copytree(self.archive, archive)
                path = archive / name
                path.write_bytes(path.read_bytes() + b"\n# Changed source identity\n")
                self.rehash(archive)
                with self.assertRaises(ValueError):
                    report.reconstruct(archive)

    def test_existing_directories_and_invalid_timeout_are_rejected_before_execution(self):
        with self.assertRaisesRegex(ValueError, "new example directory"):
            run.export_example(self.bundle)
        with self.assertRaisesRegex(ValueError, "new output directory"):
            run.execute(self.bundle, self.archive)
        for timeout in (True, 0, -1, 61, float("inf"), float("nan")):
            with (
                self.subTest(timeout=timeout),
                self.assertRaisesRegex(ValueError, "Worker timeout"),
            ):
                run.execute(self.bundle, self.directory / "unused", timeout_seconds=timeout)
        self.assertFalse((self.directory / "unused").exists())


if __name__ == "__main__":
    unittest.main()
