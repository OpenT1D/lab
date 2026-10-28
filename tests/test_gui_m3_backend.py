"""Synthetic native CLI parity and bounded M3 ownership/intake regressions."""

import copy
import os
import shutil
import signal
import sys
import tempfile
import threading
import time
import unittest
import uuid
from pathlib import Path
from unittest.mock import patch

from experiments.gui import m3, m3_worker
from experiments.gui.service import Service, digest, encode, inventory, read_json
from experiments.m3.comparison.fixtures import fixture


class M3BackendTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name).resolve(strict=True)
        self.service = Service(self.root, python=sys.executable)
        self.controller = self.service.m3
        self.fixture = self.root / "fixture"
        fixture(self.fixture)
        self.root_id = self.controller.policy.listing()[0]["id"]

    def tearDown(self):
        self.service.close()
        self.temporary.cleanup()

    def inspect(self):
        return self.controller.inspect({"root_id": self.root_id, "path": "fixture/comparison.json"})

    def configure(self, *, task="m3-compare", timeout=120):
        inspected = self.inspect()
        candidates = [item["id"] for item in inspected["candidates"]]
        return self.controller.configure(
            {
                "input_id": inspected["id"],
                "task": task,
                "candidate_ids": candidates if task == "m3-compare" else candidates[:1],
                "timeout_seconds": timeout,
            }
        )

    def job(self, operation, *, configuration_id=None, entry_id=None):
        request = self.controller.request(
            operation, configuration_id=configuration_id, entry_id=entry_id
        )
        value = "job-" + uuid.uuid4().hex
        folder = self.service.data / value
        folder.mkdir()
        job = {
            "schema": "opent1d.gui-job/1",
            "id": value,
            "task": request["task"],
            "operation": operation,
            "state": "completed",
            "request": request,
            "exit_code": None,
            "cancel_requested": False,
            "cleanup_forced": False,
            "error": None,
            "result": None,
            "verification": "not_requested",
            "commands": [],
        }
        self.service.jobs[value] = job
        self.controller.started(job)
        (folder / "job.json").write_bytes(encode(job))
        self.controller.commands(job)
        return job, folder

    def execute(self, job, folder, runner=None):
        result = m3_worker.execute(job["request"], folder, **({"runner": runner} if runner else {}))
        job["exit_code"] = 0 if result["status"] == "completed" else 1
        self.controller.finish(job)
        job["state"] = result["status"]
        self.service.persist(job)
        return result

    def check(self, config):
        job, folder = self.job("m3_check", configuration_id=config["id"])
        result = self.execute(job, folder)
        self.assertEqual(result["status"], "completed", result)
        self.assertTrue(self.controller.get_configuration(config["id"])["ready"])
        self.assertFalse(result["metadata_check"]["observation_bytes_verified"])
        return job

    def controlled_check(self, argv, log, _budget, _control):
        log.write_bytes(encode({"fixture": "metadata only; no numerical result"}))
        return (
            0,
            None,
            {
                "schema": "opent1d.workflow-entry/1",
                "task": argv[argv.index("check") + 1],
                "ready": True,
                "metadata_valid": True,
                "observation_bytes_verified": False,
                "metadata": {"controlled": True},
                "runtimes": [],
                "uv": {"ready": True},
                "observation_path_issues": [],
            },
        )

    def ready_controlled(self, config):
        job, folder = self.job("m3_check", configuration_id=config["id"])
        self.execute(job, folder, self.controlled_check)
        self.assertTrue(self.controller.get_configuration(config["id"])["ready"])

    def test_preparation_is_explicit_byte_copy_with_full_roster_and_no_candidate_import(self):
        marker = self.root / "imported"
        source = self.fixture / "trend/source.py"
        source.write_text(
            f"from pathlib import Path\nPath({str(marker)!r}).touch()\n" + source.read_text()
        )
        declaration = read_json(self.fixture / "trend/declaration.json")
        declaration["source"]["sha256"] = digest(source.read_bytes())
        (self.fixture / "trend/declaration.json").write_bytes(encode(declaration))
        config = self.configure()
        self.assertFalse(marker.exists())
        self.assertFalse(config["ready"])
        frozen = self.controller.configuration_path(config["id"])
        original = read_json(self.fixture / "comparison.json")
        copied = read_json(frozen / "config.json")
        self.assertEqual(
            (frozen / "original-config.json").read_bytes(),
            (self.fixture / "comparison.json").read_bytes(),
        )
        for lhs, rhs in zip(original["people"], copied["people"], strict=True):
            self.assertEqual(lhs["origins_us"], rhs["origins_us"])
            self.assertEqual(lhs["bounds_us"], rhs["bounds_us"])
            self.assertEqual(
                Path(lhs["input"]["file"]).read_bytes(), Path(rhs["input"]["file"]).read_bytes()
            )
        self.assertEqual(
            len(read_json(frozen / "preparation-access.json")), config["planned_people"]
        )
        self.ready_controlled(config)
        self.assertFalse(marker.exists())

    def test_native_forecast_and_comparison_keep_exact_cli_report_bytes(self):
        for task in m3.TASKS:
            with self.subTest(task=task):
                config = self.configure(task=task)
                self.check(config)
                job, folder = self.job("m3_run", configuration_id=config["id"])
                result = self.execute(job, folder)
                self.assertEqual(result["status"], "completed", result)
                entry = self.controller.get(job["m3_entry_id"])
                self.assertTrue(entry["complete"])
                self.assertEqual(entry["verification"], "native_reader_verified")
                archive = self.controller.archive_path(entry["id"])
                before = inventory(archive, files=True)
                for name in m3.ARTIFACTS:
                    self.assertEqual(
                        self.controller.report_bytes(entry["id"], name),
                        (archive / name).read_bytes(),
                    )
                reconstructed, output = self.job("m3_reconstruct", entry_id=entry["id"])
                replay = self.execute(reconstructed, output)
                self.assertEqual(replay["status"], "completed", replay)
                self.assertEqual(inventory(archive, files=True), before)
                self.assertEqual(self.controller.get(entry["id"])["execution_state"], "completed")

    def test_native_comparison_cancel_retains_unattempted_tail_and_incomplete_reader(self):
        source = self.fixture / "trend/source.py"
        source.write_text(
            "import time\ndef predict(request, settings):\n"
            "    time.sleep(60)\n    return request['values_mg_dl'][-1]\n"
        )
        declaration = read_json(self.fixture / "trend/declaration.json")
        declaration["source"]["sha256"] = digest(source.read_bytes())
        (self.fixture / "trend/declaration.json").write_bytes(encode(declaration))
        config = self.configure()
        self.check(config)
        job, folder = self.job("m3_run", configuration_id=config["id"])
        observed = []

        def runner(argv, logfile, seconds, control):
            if "run" not in argv:
                return m3_worker.invoke(argv, logfile, seconds, control)
            archive = Path(argv[argv.index("--output") + 1])
            waiting = threading.Event()

            def cancel():
                deadline = time.monotonic() + 10
                state_path = archive / "children" / config["candidate_ids"][0] / "cases"
                while not waiting.is_set() and time.monotonic() < deadline:
                    for path in state_path.glob("*/state.json"):
                        try:
                            if read_json(path).get("status") == "started":
                                observed.append(str(path))
                                os.kill(os.getpid(), signal.SIGTERM)
                                return
                        except (OSError, ValueError):
                            pass
                    time.sleep(0.01)

            watcher = threading.Thread(target=cancel, daemon=True)
            watcher.start()
            try:
                return m3_worker.invoke(argv, logfile, seconds, control)
            finally:
                waiting.set()
                watcher.join(2)

        result = self.execute(job, folder, runner)
        self.assertTrue(observed)
        self.assertEqual(result["status"], "cancelled", result)
        entry = self.controller.get(job["m3_entry_id"])
        self.assertEqual(entry["execution_state"], "cancelled")
        self.assertFalse(entry["complete"])
        self.assertTrue(entry["sealed"])
        report = self.controller.report(entry["id"])["report"]
        self.assertEqual(report["candidate_order"], config["candidate_ids"])
        self.assertEqual(
            report["candidates"][config["candidate_ids"][1]]["coordinator"]["status"],
            "not_attempted",
        )
        self.assertEqual(report["common"]["planned_people"], config["planned_people"])
        for person, detail in report["common"]["people"].items():
            self.assertEqual(detail["planned_origins"], config["planned_origins"][person])
            self.assertEqual(
                detail["candidate_statuses"][config["candidate_ids"][1]], "not_attempted"
            )

    def test_native_failed_candidate_retains_complete_planned_denominators(self):
        source = self.fixture / "trend/source.py"
        source.write_text(
            "def predict(request, settings):\n    raise RuntimeError('Synthetic failure fixture')\n"
        )
        declaration = read_json(self.fixture / "trend/declaration.json")
        declaration["source"]["sha256"] = digest(source.read_bytes())
        (self.fixture / "trend/declaration.json").write_bytes(encode(declaration))
        config = self.configure()
        self.check(config)
        job, folder = self.job("m3_run", configuration_id=config["id"])
        result = self.execute(job, folder)
        self.assertEqual(result["status"], "failed", result)
        entry = self.controller.get(job["m3_entry_id"])
        self.assertFalse(entry["complete"])
        self.assertEqual(entry["verification"], "native_reader_verified")
        report = self.controller.report(entry["id"])["report"]
        self.assertEqual(report["candidate_order"], config["candidate_ids"])
        self.assertEqual(report["common"]["planned_people"], config["planned_people"])
        self.assertEqual(set(report["common"]["people"]), set(config["planned_origins"]))
        for person, detail in report["common"]["people"].items():
            self.assertEqual(detail["planned_origins"], config["planned_origins"][person])
            self.assertEqual(detail["candidate_statuses"][config["candidate_ids"][0]], "failed")
            self.assertEqual(detail["candidate_statuses"][config["candidate_ids"][1]], "completed")
            self.assertEqual(detail["common_scored"], 0)

    def test_run_requires_check_and_refuses_modified_frozen_observations(self):
        config = self.configure()
        with self.assertRaisesRegex(ValueError, "Check this M3"):
            self.job("m3_run", configuration_id=config["id"])
        self.ready_controlled(config)
        frozen = self.controller.configuration_path(config["id"])
        native = read_json(frozen / "config.json")
        observed = Path(native["people"][0]["input"]["file"])
        observed.write_bytes(observed.read_bytes() + b"\n")
        with self.assertRaisesRegex(ValueError, "Frozen M3"):
            self.job("m3_run", configuration_id=config["id"])
        self.assertFalse(self.controller.list())

    def test_inspect_and_prepare_refuse_unsafe_paths_and_changed_source(self):
        for path in (
            "../fixture/comparison.json",
            str(self.fixture / "comparison.json"),
            "fixture/../comparison.json",
        ):
            with self.subTest(path=path), self.assertRaises(ValueError):
                self.controller.inspect({"root_id": self.root_id, "path": path})
        self.root.joinpath("linked").symlink_to(self.fixture, target_is_directory=True)
        with self.assertRaises((OSError, ValueError)):
            self.controller.inspect({"root_id": self.root_id, "path": "linked/comparison.json"})
        inspected = self.inspect()
        source = self.fixture / "trend/source.py"
        source.write_bytes(source.read_bytes() + b"\n")
        with self.assertRaisesRegex(ValueError, "hash mismatch"):
            self.controller.configure(
                {
                    "input_id": inspected["id"],
                    "task": "m3-compare",
                    "candidate_ids": [item["id"] for item in inspected["candidates"]],
                    "timeout_seconds": 120,
                }
            )

    def test_intake_refuses_hardlinks_external_paths_and_non_synthetic_configuration(self):
        source = self.fixture / "trend/source.py"
        os.link(source, self.root / "second-source.py")
        with self.assertRaisesRegex(ValueError, "regular file"):
            self.inspect()
        self.root.joinpath("second-source.py").unlink()
        config = read_json(self.fixture / "comparison.json")
        config["kind"] = "human"
        (self.fixture / "comparison.json").write_bytes(encode(config))
        with self.assertRaisesRegex(ValueError, "Synthetic"):
            self.inspect()
        config["kind"] = "synthetic"
        config["candidates"][0]["declaration"] = "/private/not-enabled/model.json"
        (self.fixture / "comparison.json").write_bytes(encode(config))
        with self.assertRaisesRegex(ValueError, "outside"):
            self.inspect()

    def test_frozen_predictor_selection_and_budget_are_bounded(self):
        inspected = self.inspect()
        original = {
            "input_id": inspected["id"],
            "task": "m3-compare",
            "candidate_ids": [item["id"] for item in inspected["candidates"]],
            "timeout_seconds": 120,
        }
        for fields in (
            {"candidate_ids": original["candidate_ids"][:1]},
            {"candidate_ids": ["unknown", "unknown"]},
            {"timeout_seconds": True},
            {"timeout_seconds": 1801},
            {"timeout_seconds": float("nan")},
            {"command": "arbitrary"},
        ):
            with self.subTest(fields=fields), self.assertRaises(ValueError):
                self.controller.configure(original | fields)
        self.service.active = "job-" + "1" * 32
        with self.assertRaisesRegex(ValueError, "One active"):
            self.controller.configure(original)
        self.service.active = None

    def test_mutated_administration_cannot_change_frozen_worker_budget(self):
        config = self.configure(task="m3-forecast")
        self.ready_controlled(config)
        job, folder = self.job("m3_run", configuration_id=config["id"])
        path = self.controller.configuration_path(config["id"]).parent / "record.json"
        record = read_json(path)
        record["timeout_seconds"] = 121
        path.write_bytes(encode(record))
        calls = []

        def runner(argv, log, seconds, control):
            calls.append(argv)
            return self.controlled_check(argv, log, seconds, control)

        result = self.execute(job, folder, runner)
        self.assertEqual(result["status"], "failed")
        self.assertTrue(result["readiness_changed"])
        self.assertFalse(calls)
        self.assertFalse(self.controller.get_configuration(config["id"])["ready"])

    def test_runtime_or_scientific_identity_changed_after_check_refuses_execution(self):
        config = self.configure()
        self.ready_controlled(config)
        job, folder = self.job("m3_run", configuration_id=config["id"])
        calls = []

        def changed(argv, log, seconds, control):
            calls.append(argv)
            code, error, report = self.controlled_check(argv, log, seconds, control)
            report["runtimes"] = [{"identity": "changed"}]
            return code, error, report

        result = self.execute(job, folder, changed)
        self.assertEqual(result["status"], "failed")
        self.assertTrue(result["readiness_changed"])
        self.assertEqual(len(calls), 1)
        self.assertFalse(self.controller.get_configuration(config["id"])["ready"])
        self.assertFalse(self.controller.archive_path(job["m3_entry_id"], exists=False).exists())

    def test_packaged_cancellation_after_native_exit_defers_reader_and_preserves_archive(self):
        config = self.configure(task="m3-forecast")
        self.ready_controlled(config)
        job, folder = self.job("m3_run", configuration_id=config["id"])
        calls = []

        def stop_before_reader(argv, log, seconds, control):
            if "check" in argv:
                return self.controlled_check(argv, log, seconds, control)
            self.assertIn("run", argv, "Cancellation must not start another audit or reader")
            calls.append(argv)
            # Execute the real native workflow on the test checkout; only the
            # packaged orchestration flags are removed from this controlled call.
            native = list(argv)
            for flag in ("--admission-prepare-seconds", "--operation-seconds", "--phase-state"):
                index = native.index(flag)
                del native[index : index + 2]
            code, error, result = m3_worker.invoke(native, log, seconds, control)
            self.assertEqual((code, error), (0, None))
            control.stop(signal.SIGTERM)
            return code, "GlobalInterruption", result

        with patch(
            "experiments.desktop.admission.packaged_manifest", return_value={"fixture": True}
        ):
            result = self.execute(job, folder, stop_before_reader)
        self.assertEqual(len(calls), 1)
        self.assertEqual(result["status"], "cancelled")
        self.assertEqual(result["verification"], "not_requested")
        entry = self.controller.get(job["m3_entry_id"])
        self.assertTrue(entry["sealed"])
        self.assertFalse(entry["report_available"])
        before = inventory(self.controller.archive_path(entry["id"]), files=True)
        reader, reader_folder = self.job("m3_reconstruct", entry_id=entry["id"])
        replay = self.execute(reader, reader_folder)
        self.assertEqual(replay["verification"], "native_reader_verified")
        self.assertEqual(inventory(self.controller.archive_path(entry["id"]), files=True), before)
        self.assertEqual(self.controller.get(entry["id"])["execution_state"], "cancelled")

    def test_cancelled_unsealed_parent_stays_forensic_and_has_no_report_claim(self):
        config = self.configure()
        self.ready_controlled(config)
        job, folder = self.job("m3_run", configuration_id=config["id"])

        def unsealed(argv, log, seconds, control):
            if "check" in argv:
                return self.controlled_check(argv, log, seconds, control)
            log.write_text("Controlled interrupted run; no numerical claim\n")
            archive = Path(argv[argv.index("--output") + 1])
            archive.mkdir()
            (archive / "raw-prefix.jsonl").write_text('{"unfinished":')
            signal.raise_signal(signal.SIGTERM)
            return -15, "GlobalInterruption", None

        result = self.execute(job, folder, unsealed)
        self.assertEqual(result["status"], "cancelled")
        entry = self.controller.get(job["m3_entry_id"])
        self.assertTrue(entry["forensic_unsealed"])
        self.assertFalse(entry["sealed"])
        self.assertFalse(entry["report_available"])
        self.assertIsNone(entry["complete"])
        self.assertEqual(entry["verification"], "verification_failed")
        self.assertTrue(self.controller.archive_path(entry["id"]).is_dir())

    def test_cache_mutation_withdraws_reports_and_reader_failure_keeps_execution_on_restart(self):
        config = self.configure(task="m3-forecast")
        self.check(config)
        job, folder = self.job("m3_run", configuration_id=config["id"])
        self.execute(job, folder)
        entry_id = job["m3_entry_id"]
        original_md = (folder / "snapshot/report.md").read_bytes()
        (folder / "snapshot/report.md").write_bytes(original_md + b"\n")
        with self.assertRaisesRegex(ValueError, "Cached M3"):
            self.controller.report_bytes(entry_id, "report.json")
        self.assertFalse(self.controller.get(entry_id)["can_view_report"])
        rebuilt, output = self.job("m3_reconstruct", entry_id=entry_id)
        self.execute(rebuilt, output)
        self.assertEqual(self.controller.report_bytes(entry_id, "report.md"), original_md)
        failed, output = self.job("m3_reconstruct", entry_id=entry_id)

        def refusal(argv, log, _seconds, _control):
            log.write_text("Controlled reader refusal\n")
            return 2, "WorkerExit", None

        self.execute(failed, output, refusal)
        self.assertEqual(self.controller.get(entry_id)["execution_state"], "completed")
        self.service.close()
        self.service = Service(self.root, python=sys.executable)
        self.controller = self.service.m3
        self.assertEqual(self.controller.get(entry_id)["execution_state"], "completed")
        self.assertFalse(self.controller.get_configuration(config["id"])["ready"])
        self.assertEqual(self.controller.get(entry_id)["verification"], "verification_failed")

    def test_fixture_uses_one_fixed_cli_and_registers_metadata_after_completion(self):
        job, folder = self.job("m3_fixture")
        result = self.execute(job, folder)
        self.assertEqual(result["status"], "completed", result)
        inspected = self.controller.get_input(job["result"]["input_id"])
        self.assertEqual(inspected["task"], "m3-compare")
        self.assertEqual(len(inspected["candidates"]), 2)
        request = copy.deepcopy(job["request"])
        request["task"] = "m3-forecast"
        with self.assertRaises(ValueError):
            m3.validate_request(request)

    def test_reinspection_binds_coherently_changed_declaration_without_stale_pointer(self):
        old = self.inspect()
        settings = self.fixture / "trend/settings.json"
        settings.write_bytes(encode({"limit_mg_dl": 29.0}))
        declaration = read_json(self.fixture / "trend/declaration.json")
        declaration["settings"]["sha256"] = digest(settings.read_bytes())
        (self.fixture / "trend/declaration.json").write_bytes(encode(declaration))
        new = self.inspect()
        self.assertNotEqual(new["id"], old["id"])
        self.assertNotEqual(new["candidates"], old["candidates"])
        config = self.controller.configure(
            {
                "input_id": new["id"],
                "task": "m3-compare",
                "candidate_ids": [item["id"] for item in new["candidates"]],
                "timeout_seconds": 120,
            }
        )
        self.assertFalse(config["ready"])

    def test_saved_reconstruction_requires_no_original_preparation_model_or_observations(self):
        config = self.configure(task="m3-forecast")
        self.check(config)
        job, folder = self.job("m3_run", configuration_id=config["id"])
        result = self.execute(job, folder)
        self.assertEqual(result["status"], "completed", result)
        original = {
            name: self.controller.report_bytes(job["m3_entry_id"], name) for name in m3.ARTIFACTS
        }
        shutil.rmtree(self.controller.configuration_path(config["id"]))
        shutil.rmtree(self.fixture)
        replay, output = self.job("m3_reconstruct", entry_id=job["m3_entry_id"])
        rebuilt = self.execute(replay, output)
        self.assertEqual(rebuilt["status"], "completed", rebuilt)
        for name in m3.ARTIFACTS:
            self.assertEqual(self.controller.report_bytes(job["m3_entry_id"], name), original[name])

    def test_m3_job_task_binding_cannot_be_confused_with_m4_on_restart(self):
        job, folder = self.job("m3_fixture")
        invalid = dict(job, task="m4-study-secure")
        (folder / "job.json").write_bytes(encode(invalid))
        self.service.close()
        self.service = Service(self.root, python=sys.executable)
        self.controller = self.service.m3
        self.assertNotIn(job["id"], self.service.jobs)


if __name__ == "__main__":
    unittest.main()
