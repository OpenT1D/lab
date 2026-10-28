"""Controlled CLI receipts test GUI contracts; these are not numerical results."""

import copy
import os
import shutil
import signal
import sys
import tempfile
import threading
import unittest
import uuid
from pathlib import Path
from unittest.mock import patch

from experiments.gui import campaign_worker, campaigns
from experiments.gui.service import Service, encode, read_json
from experiments.maintained_campaigns import common


class LocalService:
    safe_path = Service.safe_path
    unchanged = Service.unchanged

    def __init__(self, root):
        self.root = root
        self.python = sys.executable
        self.data = root / "results/gui"
        self.data.mkdir(parents=True)
        self.lock = threading.RLock()
        self.configurations, self.jobs = {}, {}

    def resolve_configuration(self, value):
        record = self.configurations[value]
        self.unchanged(record)
        return copy.deepcopy(record)

    def add_study(self, scenario="fasting", *, marker=None):
        value = "config-" + uuid.uuid4().hex
        folder = self.data / value
        folder.mkdir()
        config = {
            "schema": "m4-secure-study-config/1",
            "sources": [],
            "scenarios": [scenario],
            "timeout_seconds": 600,
            "source_timeout_seconds": 3600,
        }
        hashes = {}
        for name, model in (
            ("dalla_man", common.ROOT / "experiments/m4/causal_secretion/example_model.py"),
            ("ultradian", common.ROOT / "experiments/m4/ultradian_secretion/model.py"),
        ):
            target = folder / "sources" / name
            target.mkdir(parents=True)
            raw = (
                model.read_bytes()
                if marker is None
                else f"from pathlib import Path\nPath({str(marker)!r}).touch()\n".encode()
            )
            (target / "model.py").write_bytes(raw)
            declaration = common.read(model.with_suffix(".json")) | {
                "source_sha256": common.digest(raw)
            }
            (target / "model.json").write_bytes(encode(declaration))
            for path in target.iterdir():
                hashes[str(path)] = common.digest(path.read_bytes())
            config["sources"].append(
                {
                    "id": name,
                    "model": str(target / "model.py"),
                    "declaration": str(target / "model.json"),
                }
            )
        raw = encode(config)
        (folder / "config.json").write_bytes(raw)
        self.configurations[value] = {
            "id": value,
            "config": config,
            "sha256": common.digest(raw),
            "source_sha256": hashes,
            "ready": False,
        }
        return value


class GUICampaignBackendTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.service = LocalService(self.root)
        self.controller = campaigns.Campaigns(self.service)
        self.calls = []
        self.outcome = "completed"
        self.drift = False

    def tearDown(self):
        self.temporary.cleanup()

    def configure(self, *, cells=2, repeats=2, marker=None):
        first = self.service.add_study(marker=marker)
        second = self.service.add_study("gastric_load_15g", marker=marker)
        body = {
            "cells": [
                {"id": f"c{index}", "configuration_id": first if index % 2 == 0 else second}
                for index in range(cells)
            ],
            "repeats": repeats,
            "timeout_seconds": 1800,
        }
        return self.controller.configure(body)

    def job(self, operation, *, configuration_id=None, campaign_id=None):
        request = self.controller.request(
            operation, configuration_id=configuration_id, campaign_id=campaign_id
        )
        value = "job-" + uuid.uuid4().hex
        folder = self.service.data / value
        folder.mkdir()
        job = {
            "id": value,
            "operation": operation,
            "request": request,
            "exit_code": None,
            "cancel_requested": False,
            "cleanup_forced": False,
            "error": None,
        }
        self.service.jobs[value] = job
        self.controller.started(job)
        (folder / "job.json").write_bytes(encode(job))
        self.controller.commands(job)
        return job, folder

    def runner(self, argv, log, budget, control):
        self.calls.append(argv)
        log.write_bytes(encode({"argv": argv, "timeout_seconds": budget}))
        if "experiments.setup" in argv:
            return 0, None, {"ready": True}
        operation = argv[argv.index("experiments.maintained_campaigns") + 1]
        if operation == "check":
            prepared = common.prepare(Path(argv[argv.index("--config") + 1]))
            prepared.update(
                ready=True,
                runtime_identity={"controlled_fixture": "changed" if self.drift else "original"},
            )
            return 0, None, prepared
        if operation in {"run", "resume"}:
            archive = (
                Path(argv[argv.index("--output") + 1])
                if operation == "run"
                else Path(argv[argv.index("--campaign") + 1])
            )
            if operation == "run":
                archive.mkdir()
                matrix_path = Path(argv[argv.index("--config") + 1])
                (archive / "config.json").write_bytes(matrix_path.read_bytes())
                matrix = common.read(matrix_path)
                for cell in matrix["cells"]:
                    original = matrix_path.parent / cell["config"]
                    target = archive / "frozen" / cell["id"]
                    target.mkdir(parents=True)
                    (target / "original-config.json").write_bytes(original.read_bytes())
                    shutil.copytree(original.parent / "sources", target / "sources")
            else:
                matrix = common.read(archive / "config.json")
            sessions = archive / "sessions"
            sessions.mkdir(exist_ok=True)
            number = len(list(sessions.iterdir())) + 1
            session = sessions / f"session-{number:04d}"
            session.mkdir()
            if self.outcome != "hard_kill":
                (session / "manifest.json").write_bytes(encode({"controlled_fixture": True}))
            counts = {
                cell["id"]: len(
                    common.read(archive / "frozen" / cell["id"] / "original-config.json")["sources"]
                )
                * len(
                    common.read(archive / "frozen" / cell["id"] / "original-config.json")[
                        "scenarios"
                    ]
                )
                for cell in matrix["cells"]
            }
            slots = [
                {
                    **slot,
                    "accepted": self.outcome == "completed",
                    "attempts": [
                        {
                            "session": number,
                            "outcome": {
                                "status": "completed"
                                if self.outcome == "completed"
                                else "interrupted"
                            },
                        }
                    ],
                    "planned_source_scenarios": counts[slot["cell"]],
                }
                for slot in common.slots(matrix)
            ]
            report = {
                "schema": common.REPORT_SCHEMA,
                "task": common.TASK,
                "protocol": "MAINTAINED-CAMPAIGN/1",
                "status": "completed" if self.outcome == "completed" else "interrupted",
                "passed": self.outcome == "completed",
                "planned_slots": len(slots),
                "accepted_slots": len(slots) if self.outcome == "completed" else 0,
                "planned_source_scenarios": sum(slot["planned_source_scenarios"] for slot in slots),
                "accepted_source_scenarios": sum(slot["planned_source_scenarios"] for slot in slots)
                if self.outcome == "completed"
                else 0,
                "slots": slots,
                "sessions": [{"number": number}],
                "interpretation": "Controlled CLI fixture, no numerical evidence",
                "limitations": "Controlled CLI fixture",
            }
            (archive / "fixture-report.json").write_bytes(encode(report))
            if self.outcome == "cancelled":
                signal.raise_signal(signal.SIGTERM)
            return (
                (0, None, report)
                if self.outcome == "completed"
                else (-9 if self.outcome == "hard_kill" else 1, "WorkerExit", report)
            )
        archive = Path(argv[argv.index("--campaign") + 1])
        if self.outcome == "hard_kill":
            return 2, "WorkerExit", {"error": "Unsealed session cannot be verified"}
        output = Path(argv[argv.index("--output") + 1])
        output.mkdir()
        raw = (archive / "fixture-report.json").read_bytes()
        (output / "report.json").write_bytes(raw)
        (output / "report.md").write_text("Controlled CLI fixture report\n")
        return 0, None, read_json(output / "report.json")

    def execute(self, job, folder):
        result = campaign_worker.execute(job["request"], folder, runner=self.runner)
        job["exit_code"] = 0 if result["status"] == "completed" else 1
        self.controller.finish(job)
        return result

    def ready(self, configuration):
        job, folder = self.job("campaign_check", configuration_id=configuration["id"])
        result = self.execute(job, folder)
        self.assertTrue(result["ready"])
        return job

    def test_passive_standalone_matrix_freezes_sources_without_importing_and_needs_check(self):
        marker = self.root / "source-imported"
        configuration = self.configure(marker=marker)
        self.assertEqual(configuration["planned_slots"], 4)
        self.assertEqual(configuration["planned_source_scenarios"], 8)
        self.assertFalse(marker.exists())
        with self.assertRaisesRegex(ValueError, "Check this campaign"):
            self.job("campaign_run", configuration_id=configuration["id"])
        for value in self.service.configurations:
            shutil.rmtree(self.service.data / value)
        self.ready(configuration)
        self.assertFalse(marker.exists())

    def test_ready_run_report_get_and_json_md_are_exact_cached_snapshots(self):
        configuration = self.configure()
        self.ready(configuration)
        job, folder = self.job("campaign_run", configuration_id=configuration["id"])
        result = self.execute(job, folder)
        self.assertEqual(result["verification"], "native_reader_verified")
        value = job["campaign_id"]
        with patch.object(campaigns, "inventory", side_effect=AssertionError("HTTP must not scan")):
            entry = self.controller.get(value)
            view = self.controller.report(value)
            self.assertEqual(entry["accepted_slots"], 4)
            self.assertEqual(view["report"]["planned_source_scenarios"], 8)
            self.assertEqual(len(view["report"]["slots"]), 4)
            for name in campaigns.ARTIFACTS:
                self.assertEqual(
                    self.controller.report_bytes(value, name),
                    (folder / "snapshot" / name).read_bytes(),
                )
        self.assertEqual(
            self.calls[-1][self.calls[-1].index("experiments.maintained_campaigns") + 1],
            "reconstruct",
        )
        self.assertIn("--allow-failed", self.calls[-1])
        self.assertIn("-S", self.calls[-1])

    def test_runtime_drift_refuses_native_dispatch_and_invalidates_readiness(self):
        configuration = self.configure()
        self.ready(configuration)
        self.calls.clear()
        self.drift = True
        job, folder = self.job("campaign_run", configuration_id=configuration["id"])
        result = self.execute(job, folder)
        self.assertTrue(result["readiness_changed"])
        self.assertEqual(len(self.calls), 1)
        self.assertIsNone(result["native_exit_code"])
        self.assertFalse(self.controller.get_configuration(configuration["id"])["ready"])

    def test_cancelled_sealed_evidence_stays_failed_and_can_be_reconstructed(self):
        configuration = self.configure()
        self.ready(configuration)
        self.outcome = "cancelled"
        job, folder = self.job("campaign_run", configuration_id=configuration["id"])
        result = self.execute(job, folder)
        self.assertEqual(result["status"], "cancelled")
        self.assertEqual(result["report_completeness"], "failed")
        self.assertEqual(result["verification"], "native_reader_verified")
        self.assertEqual(len(self.controller.report(job["campaign_id"])["report"]["slots"]), 4)
        self.outcome = "completed"
        reconstruct, other = self.job("campaign_reconstruct", campaign_id=job["campaign_id"])
        repeated = self.execute(reconstruct, other)
        self.assertEqual(repeated["status"], "completed")
        self.assertEqual(repeated["report_completeness"], "failed")

    def test_unsealed_hard_kill_is_forensic_and_never_promoted(self):
        configuration = self.configure()
        self.ready(configuration)
        self.outcome = "hard_kill"
        job, folder = self.job("campaign_run", configuration_id=configuration["id"])
        result = self.execute(job, folder)
        self.assertTrue(result["forensic_unsealed"])
        self.assertEqual(result["verification"], "verification_failed")
        self.assertFalse(self.controller.get(job["campaign_id"])["can_view_report"])

    def test_restart_resets_ready_and_verification_without_adopting_processes(self):
        configuration = self.configure()
        self.ready(configuration)
        job, folder = self.job("campaign_run", configuration_id=configuration["id"])
        self.execute(job, folder)
        with patch.object(
            campaigns, "inventory", side_effect=AssertionError("Restart must not scan native")
        ):
            restarted = campaigns.Campaigns(self.service)
        self.assertFalse(restarted.get_configuration(configuration["id"])["ready"])
        self.assertEqual(restarted.get(job["campaign_id"])["verification"], "recorded_verification")
        self.assertEqual(restarted.report(job["campaign_id"])["report"]["accepted_slots"], 4)
        with self.assertRaisesRegex(ValueError, "Check this campaign"):
            restarted.request("campaign_resume", campaign_id=job["campaign_id"])

    def test_install_invalidation_opaque_ids_and_external_adoption_refusal(self):
        configuration = self.configure()
        self.ready(configuration)
        self.controller.invalidate_readiness()
        self.assertFalse(self.controller.get_configuration(configuration["id"])["ready"])
        job, folder = self.job("campaign_install", configuration_id=configuration["id"])
        self.assertEqual(self.execute(job, folder)["status"], "completed")
        self.assertFalse(self.controller.get_configuration(configuration["id"])["ready"])
        self.assertTrue(all("experiments.setup" in args for args in self.calls[-2:]))
        with self.assertRaises(ValueError):
            self.controller.request("campaign_resume", campaign_id="archive-" + "a" * 32)
        with self.assertRaises(ValueError):
            self.controller.request("campaign_resume", campaign_id="campaign-" + "a" * 32)
        with self.assertRaises(ValueError):
            campaigns.validate_request(job["request"] | {"archive": "/outside"})

    def test_frozen_source_and_cached_artifact_tampering_are_refused(self):
        configuration = self.configure()
        self.ready(configuration)
        job, folder = self.job("campaign_run", configuration_id=configuration["id"])
        self.execute(job, folder)
        artifact = folder / "snapshot/report.md"
        artifact.write_text("changed")
        with self.assertRaisesRegex(ValueError, "Cached campaign artifact"):
            self.controller.report_bytes(job["campaign_id"], "report.md")
        source = (
            self.controller.folder(configuration["id"])
            / "frozen/cells/c0/sources/dalla_man/model.py"
        )
        source.write_text("changed")
        next_job, other = self.job("campaign_check", configuration_id=configuration["id"])
        self.calls.clear()
        result = self.execute(next_job, other)
        self.assertEqual(result["status"], "failed")
        self.assertFalse(self.calls)

    def test_full_128_slot_snapshot_has_every_row_without_aggregate_figure(self):
        configuration = self.configure(cells=32, repeats=4)
        self.ready(configuration)
        job, folder = self.job("campaign_run", configuration_id=configuration["id"])
        self.execute(job, folder)
        view = self.controller.report(job["campaign_id"])
        self.assertEqual(
            (view["report"]["planned_slots"], len(view["report"]["slots"])), (128, 128)
        )
        self.assertEqual(view["report"]["planned_source_scenarios"], 256)
        with self.assertRaises(ValueError):
            self.controller.report_bytes(job["campaign_id"], "figure.svg")

    def test_stable_valid_source_substitution_after_resolve_is_rejected(self):
        original_resolve = self.service.resolve_configuration

        def replace(value):
            original = original_resolve(value)
            path = Path(original["config"]["sources"][0]["model"])
            raw = path.read_bytes() + b"\n# valid but different supplied source\n"
            path.write_bytes(raw)
            declaration = path.with_suffix(".json")
            metadata = read_json(declaration)
            declaration.write_bytes(encode(metadata | {"source_sha256": common.digest(raw)}))
            return original

        with patch.object(self.service, "resolve_configuration", side_effect=replace):
            with self.assertRaisesRegex(ValueError, "Saved study source changed"):
                self.configure()
        self.assertEqual(self.controller.configurations(), [])

    def test_copy_parses_the_exact_hash_checked_native_configuration_buffer(self):
        original_read = campaigns.bounded_bytes
        changed = False

        def substitute(path, maximum):
            nonlocal changed
            raw = original_read(path, maximum)
            if (
                path.name == "config.json"
                and path.parent.name.startswith("config-")
                and not changed
            ):
                changed = True
                value = campaigns.decode_json(raw)
                path.write_bytes(encode(value | {"scenarios": ["gastric_load_30g"]}))
            return raw

        with patch.object(campaigns, "bounded_bytes", side_effect=substitute):
            with self.assertRaisesRegex(ValueError, "Frozen configuration changed"):
                self.configure()
        self.assertEqual(self.controller.configurations(), [])
        retained = next(
            (self.controller.data / "configurations").glob(
                "campaign-config-*/frozen/cells/c0/config.json"
            )
        )
        self.assertEqual(read_json(retained)["scenarios"], ["fasting"])

    def test_late_frozen_input_failure_resets_success_and_readiness(self):
        configuration = self.configure()
        job, folder = self.job("campaign_check", configuration_id=configuration["id"])

        def late_change(argv, log, budget, control):
            answer = self.runner(argv, log, budget, control)
            source = (
                self.controller.folder(configuration["id"])
                / "frozen/cells/c0/sources/dalla_man/model.py"
            )
            source.write_text("changed after a successful check")
            return answer

        result = campaign_worker.execute(job["request"], folder, runner=late_change)
        self.assertEqual(result["status"], "failed")
        self.assertFalse(result["ready"])
        job["exit_code"] = 1
        self.controller.finish(job)
        self.assertFalse(self.controller.get_configuration(configuration["id"])["ready"])
        self.assertIn("Frozen campaign", job["error"])

    def test_malformed_successful_cli_results_are_classified_as_failures(self):
        configuration = self.configure()
        for operation in ("campaign_check", "campaign_install"):
            with self.subTest(operation=operation):
                job, folder = self.job(operation, configuration_id=configuration["id"])
                result = campaign_worker.execute(
                    job["request"], folder, runner=lambda *_: (0, None, None)
                )
                self.assertEqual(result["status"], "failed")
                self.assertFalse(result["ready"])
        self.ready(configuration)
        job, folder = self.job("campaign_run", configuration_id=configuration["id"])

        def malformed_reconstruct(argv, log, budget, control):
            if "reconstruct" in argv:
                return 0, None, []
            return self.runner(argv, log, budget, control)

        result = campaign_worker.execute(job["request"], folder, runner=malformed_reconstruct)
        self.assertEqual(result["status"], "failed")
        self.assertEqual(result["verification"], "verification_failed")

    def test_replaced_owned_archives_ancestor_refuses_dispatch_and_external_writes(self):
        configuration = self.configure()
        self.ready(configuration)
        job, folder = self.job("campaign_run", configuration_id=configuration["id"])
        archives = self.controller.data / "archives"
        archives.rmdir()
        external = self.root / "external"
        external.mkdir()
        archives.symlink_to(external, target_is_directory=True)
        self.calls.clear()
        result = campaign_worker.execute(job["request"], folder, runner=self.runner)
        self.assertEqual(result["status"], "failed")
        self.assertIn("symlink", result["error"])
        self.assertFalse(self.calls)
        self.assertEqual(list(external.iterdir()), [])

    def test_ownership_error_cannot_enable_check_or_promote_snapshot(self):
        configuration = self.configure()
        job, folder = self.job("campaign_check", configuration_id=configuration["id"])
        result = campaign_worker.execute(job["request"], folder, runner=self.runner)
        self.assertTrue(result["ready"])
        job.update(exit_code=0, error="Observed worker escaped cleanup")
        self.controller.finish(job)
        self.assertFalse(self.controller.get_configuration(configuration["id"])["ready"])
        self.assertEqual(job["error"], "Observed worker escaped cleanup")
        self.ready(configuration)
        job, folder = self.job("campaign_run", configuration_id=configuration["id"])
        campaign_worker.execute(job["request"], folder, runner=self.runner)
        job.update(exit_code=0, error="Observed worker escaped cleanup")
        self.controller.finish(job)
        self.assertEqual(
            self.controller.get(job["campaign_id"])["verification"], "verification_failed"
        )
        self.assertFalse(self.controller.get(job["campaign_id"])["can_view_report"])
        self.assertEqual(job["error"], "Observed worker escaped cleanup")

    def test_cancelled_worker_missing_receipt_preserves_original_ownership_error(self):
        configuration = self.configure()
        self.ready(configuration)
        job, _ = self.job("campaign_run", configuration_id=configuration["id"])
        job.update(
            exit_code=-9,
            cancel_requested=True,
            cleanup_forced=True,
            error="Owned worker forcibly terminated",
        )
        self.controller.finish(job)
        self.assertEqual(job["error"], "Owned worker forcibly terminated")
        self.assertEqual(
            self.controller.get(job["campaign_id"])["verification"], "verification_failed"
        )
        self.assertFalse(self.controller.get(job["campaign_id"])["can_view_report"])

    def test_missing_or_nonregular_snapshot_withdraws_verified_badge(self):
        configuration = self.configure()
        self.ready(configuration)
        for nonregular in (False, True):
            job, folder = self.job("campaign_run", configuration_id=configuration["id"])
            self.execute(job, folder)
            path = folder / "snapshot/report.json"
            path.unlink()
            if nonregular:
                os.mkfifo(path)
            with self.assertRaisesRegex(ValueError, "Cached campaign artifact"):
                self.controller.report(job["campaign_id"])
            self.assertEqual(
                self.controller.get(job["campaign_id"])["verification"],
                "changed_since_verification",
            )

    def test_malformed_matching_hash_saved_record_is_skipped_on_restart(self):
        configuration = self.configure()
        folder = self.controller.folder(configuration["id"])
        record = read_json(folder / "record.json")
        (folder / "record.json").write_bytes(encode(record | {"cells": None}))
        restarted = campaigns.Campaigns(self.service)
        self.assertEqual(restarted.configurations(), [])

    def test_resume_appends_session_without_mutating_previous_files(self):
        configuration = self.configure()
        self.ready(configuration)
        job, folder = self.job("campaign_run", configuration_id=configuration["id"])
        self.execute(job, folder)
        archive = self.controller.archive(job["campaign_id"], exists=True)
        previous = (archive / "sessions/session-0001/manifest.json").read_bytes()
        resume, other = self.job("campaign_resume", campaign_id=job["campaign_id"])
        self.execute(resume, other)
        self.assertEqual((archive / "sessions/session-0001/manifest.json").read_bytes(), previous)
        self.assertTrue((archive / "sessions/session-0002/manifest.json").exists())
        self.assertEqual(self.controller.get(job["campaign_id"])["last_job"], resume["id"])

    def test_report_read_holds_lock_against_concurrent_finish(self):
        configuration = self.configure()
        self.ready(configuration)
        job, folder = self.job("campaign_run", configuration_id=configuration["id"])
        self.execute(job, folder)
        entered, released = threading.Event(), threading.Event()
        original = campaigns.bounded_bytes

        def pause(path, maximum):
            if path == folder / "snapshot/report.json":
                entered.set()
                self.assertTrue(released.wait(3))
            return original(path, maximum)

        errors = []

        def read():
            try:
                self.controller.report(job["campaign_id"])
            except BaseException as error:
                errors.append(error)

        with patch.object(campaigns, "bounded_bytes", side_effect=pause):
            thread = threading.Thread(target=read)
            thread.start()
            self.assertTrue(entered.wait(3))
            self.assertFalse(self.service.lock.acquire(blocking=False))
            released.set()
            thread.join(3)
        self.assertFalse(thread.is_alive())
        self.assertEqual(errors, [])

    def test_new_operation_dispatch_exposes_new_last_job_and_recorded_snapshot(self):
        configuration = self.configure()
        self.ready(configuration)
        job, folder = self.job("campaign_run", configuration_id=configuration["id"])
        self.execute(job, folder)
        reconstruct, _ = self.job("campaign_reconstruct", campaign_id=job["campaign_id"])
        entry = self.controller.get(job["campaign_id"])
        self.assertEqual(entry["last_job"], reconstruct["id"])
        self.assertEqual(entry["verification"], "recorded_verification")
        self.assertTrue(entry["can_view_report"])

    def test_clean_queued_and_precheck_cancellation_have_diagnostics_without_ownership_error(self):
        configuration = self.configure()
        self.ready(configuration)
        job, _ = self.job("campaign_run", configuration_id=configuration["id"])
        job.update(cancel_requested=True)
        self.controller.finish(job)
        self.assertIsNone(job["error"])
        self.assertEqual(job["result"]["status"], "cancelled")
        self.assertFalse(self.controller.get(job["campaign_id"])["can_view_report"])
        job, folder = self.job("campaign_run", configuration_id=configuration["id"])

        def cancel(*_args):
            signal.raise_signal(signal.SIGTERM)
            return 1, "GlobalInterruption", None

        result = campaign_worker.execute(job["request"], folder, runner=cancel)
        self.assertEqual(result["status"], "cancelled")
        self.assertIsNone(result["error"])
        self.assertIn("interrupted", result["diagnostic"])
        job.update(exit_code=1, cancel_requested=True)
        self.controller.finish(job)
        self.assertIsNone(job["error"])

    def test_repeated_term_is_forwarded_once_and_handlers_remain_until_receipt(self):
        configuration = self.configure()
        job, folder = self.job("campaign_check", configuration_id=configuration["id"])
        before = signal.getsignal(signal.SIGTERM)
        actual_stop = campaign_worker.Control.stop
        forwarded = []

        def counted(control, signum, frame=None):
            forwarded.append(signum)
            actual_stop(control, signum, frame)

        def cancelled(*_args):
            signal.raise_signal(signal.SIGTERM)
            signal.raise_signal(signal.SIGTERM)
            return 1, "GlobalInterruption", None

        with patch.object(campaign_worker.Control, "stop", counted):
            result = campaign_worker.execute(job["request"], folder, runner=cancelled)
        self.assertEqual(forwarded, [signal.SIGTERM])
        self.assertEqual(result["status"], "cancelled")
        self.assertEqual(
            read_json(folder / "campaign-result.json")["interruption_signal"], signal.SIGTERM
        )
        self.assertIs(signal.getsignal(signal.SIGTERM), before)

    def test_native_archive_graft_with_valid_roster_but_different_bytes_is_refused(self):
        configuration = self.configure()
        self.ready(configuration)
        job, folder = self.job("campaign_run", configuration_id=configuration["id"])
        self.execute(job, folder)
        source = (
            self.controller.archive(job["campaign_id"], exists=True)
            / "frozen/c0/sources/dalla_man/model.py"
        )
        source.write_bytes(source.read_bytes() + b"\n# stable alternative bytes\n")
        job, folder = self.job("campaign_reconstruct", campaign_id=job["campaign_id"])
        self.calls.clear()
        result = self.execute(job, folder)
        self.assertEqual(result["status"], "failed")
        self.assertIn("source differs", result["error"])
        self.assertFalse(self.calls)
