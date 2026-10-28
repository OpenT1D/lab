"""Fixed M3 library readers, honest coverage and withdrawal of stale snapshots."""

import json
import os
import shutil
import signal
import subprocess
import sys
import tempfile
import time
import unittest
import uuid
from pathlib import Path
from unittest.mock import patch

from experiments.catalogue import core, formats
from experiments.gui.library import Library
from experiments.gui.library_worker import ARTIFACTS_BY_TASK, REPORT_SCHEMAS, execute
from experiments.gui.service import Service, digest, encode, inventory
from experiments.m3.comparison.study import run_study as compare
from experiments.m3.researcher.study import run_study as forecast
from tests.test_m3_comparison_study import configuration as comparison_config
from tests.test_m3_researcher_study import configuration as forecast_config

ROOT = Path(__file__).resolve().parents[1]
PERSISTENCE = "def predict(request, settings):\n    return request['values_mg_dl'][-1]\n"
FAILURE = (
    "def predict(request, settings):\n"
    "    if request['origin_us'] >= 5_400_000_000: raise RuntimeError('controlled failure')\n"
    "    return request['values_mg_dl'][-1]\n"
)


class M3LibraryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.fixtures = tempfile.TemporaryDirectory()
        cls.fixture_root = Path(cls.fixtures.name).resolve()
        cls.marker = cls.fixture_root / "predictor-imported"
        cls.cases = {}
        for task in ("m3-forecast", "m3-compare"):
            for failed in (False, True):
                name = task + ("-failed" if failed else "-complete")
                preparation = cls.fixture_root / (name + "-prepare")
                source = f"open({str(cls.marker)!r}, 'a').write('imported\\n')\n" + (
                    FAILURE if failed else PERSISTENCE
                )
                if task == "m3-forecast":
                    config, _ = forecast_config(preparation, source=source, days=2)
                    report = forecast(config, cls.fixture_root / name, timeout=10)
                else:
                    config, _ = comparison_config(preparation, second_source=source)
                    report = compare(config, cls.fixture_root / name)
                shutil.rmtree(preparation)
                cls.cases[name] = (task, report)
        cls.marker.unlink()

    @classmethod
    def tearDownClass(cls):
        cls.fixtures.cleanup()

    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.base = Path(self.temporary.name).resolve()
        self.workspace = self.base / "workspace"
        self.external = self.base / "external"
        self.workspace.mkdir()
        self.external.mkdir()
        for name in self.cases:
            shutil.copytree(self.fixture_root / name, self.external / name)
        self.service = Service(self.workspace, archive_roots=(self.external,))
        self.library = self.service.library
        self.root_id = next(
            root["id"] for root in self.library.roots() if root["directory"] == str(self.external)
        )

    def tearDown(self):
        self.service.close()
        self.temporary.cleanup()

    def operation(self, request, *, cancel=False):
        identity = "job-" + uuid.uuid4().hex
        folder = self.service.data / identity
        folder.mkdir()
        job = {
            "id": identity,
            "request": request,
            "operation": request["operation"],
            "state": "running",
            "exit_code": None,
            "error": None,
            "cancel_requested": cancel,
            "cleanup_forced": False,
            "result": None,
        }
        self.library.commands(job)
        if not cancel:
            result = execute(request, folder)
            job["exit_code"] = 0 if result["status"] == "completed" else 1
        self.library.finish(job)
        return job

    def index(self, name):
        task, _ = self.cases[name]
        request = self.library.add({"root_id": self.root_id, "path": name, "task": task})
        job = self.operation(request)
        self.assertIsNone(job["error"], job)
        return request["entry"]["id"]

    def verified(self, name):
        identity = self.index(name)
        job = self.operation(self.library.verify(identity))
        self.assertIsNone(job["error"], job)
        self.assertEqual(job["verification"], "native_reader_verified")
        return identity

    def test_fixed_whitelist_artifact_rosters_and_native_argv(self):
        self.assertEqual(
            set(ARTIFACTS_BY_TASK),
            {
                "m3-forecast",
                "m3-compare",
                "m4-study-secure",
                "m5-prognosis",
                "mmtt-sensitivity",
                "mmtt-sampling",
            },
        )
        contract = json.loads((ROOT / "experiments/gui/contract.json").read_text())
        self.assertEqual(
            set(contract["archive_library"]["verification_tasks"]), set(ARTIFACTS_BY_TASK)
        )
        for task, module, operation in (
            ("m3-forecast", "experiments.m3.researcher", "report"),
            ("m3-compare", "experiments.m3.comparison", "reconstruct"),
        ):
            self.assertEqual(ARTIFACTS_BY_TASK[task], ("report.json", "report.md"))
            self.assertEqual(
                formats.reconstruction_args(task, Path("/source"), Path("/derived"), True),
                ["-m", module, operation, "--study", "/source", "--output", "/derived"],
            )

    def test_real_native_complete_and_failed_reports_keep_original_bytes_and_denominators(self):
        fields = {
            "task",
            "schema",
            "native_report",
            "verification",
            "verification_scope",
            "source_freshness",
            "report_completeness",
            "report_sha256",
        }
        for name, (task, original) in self.cases.items():
            with self.subTest(name=name):
                archive = self.external / name
                before = inventory(archive, files=True)
                identity = self.verified(name)
                entry = self.library.get(identity)
                view = self.library.report(identity)
                self.assertEqual(set(view), fields)
                self.assertEqual(view["task"], task)
                self.assertEqual(view["schema"], REPORT_SCHEMAS[task])
                self.assertEqual(view["native_report"], original)
                coverage = original["evaluation" if task == "m3-forecast" else "common"]
                self.assertEqual(
                    view["report_completeness"],
                    "complete" if coverage["complete_cohort"] else "incomplete",
                )
                self.assertEqual(coverage["planned_people"], 2)
                if name.endswith("failed"):
                    self.assertFalse(coverage["complete_cohort"])
                    self.assertEqual(coverage["contributing_people"], 0)
                self.assertTrue(entry["can_verify"])
                self.assertTrue(entry["can_view_report"])
                self.assertEqual(view["source_freshness"], "not_rechecked_since_worker")
                for artifact in ARTIFACTS_BY_TASK[task]:
                    self.assertEqual(
                        self.library.report_bytes(identity, artifact),
                        (archive / artifact).read_bytes(),
                    )
                self.assertEqual(inventory(archive, files=True), before)
                self.assertFalse(self.marker.exists(), "report reader imported retained predictor")

    def test_m3_cannot_leak_an_svg_or_an_arbitrary_snapshot_file(self):
        for task in ("m3-forecast", "m3-compare"):
            identity = self.verified(task + "-complete")
            folder = self.library.report_file(identity, "report.json").parent
            (folder / "figure.svg").write_text("must not be downloadable")
            for name in ("figure.svg", "../report.json", "source.py"):
                with (
                    self.subTest(task=task, name=name),
                    self.assertRaisesRegex(ValueError, "artifact"),
                ):
                    self.library.report_bytes(identity, name)
            self.assertTrue(self.library.get(identity)["can_view_report"])

    def test_changed_source_refuses_native_dispatch_and_withdraws_prior_snapshot(self):
        for task in ("m3-forecast", "m3-compare"):
            name = task + "-complete"
            identity = self.verified(name)
            (self.external / name / "report.md").write_text("changed externally")
            with patch("experiments.catalogue.core.verify_one", side_effect=AssertionError):
                job = self.operation(self.library.verify(identity))
            self.assertIn("changed since indexing", job["error"])
            self.assertEqual(
                self.library.get(identity)["verification"], "changed_since_verification"
            )
            self.assertFalse(self.library.get(identity)["can_view_report"])
            with self.assertRaises(ValueError):
                self.library.report_bytes(identity, "report.md")

    def test_mutation_during_owned_native_reconstruction_withdraws_snapshot(self):
        identity = self.index("m3-compare-complete")
        native = core.verify_one

        def changing(item, output, allow_failed):
            result = native(item, output, allow_failed)
            (self.external / "m3-compare-complete/report.md").write_text("changed during operation")
            return result

        with patch("experiments.catalogue.core.verify_one", side_effect=changing):
            job = self.operation(self.library.verify(identity))
        self.assertIn("changed during", job["error"])
        self.assertEqual(self.library.get(identity)["verification"], "changed_since_verification")
        self.assertFalse(self.library.get(identity)["can_view_report"])

    def test_snapshot_mutation_withdraws_all_downloads_and_does_not_reopen_old_snapshot(self):
        for artifact in ("report.json", "report.md"):
            identity = self.verified("m3-forecast-complete")
            self.library.report_file(identity, artifact).write_text("changed snapshot")
            with self.assertRaisesRegex(ValueError, "artifact changed"):
                self.library.report_bytes(identity, artifact)
            self.assertFalse(self.library.get(identity)["can_view_report"])
            with self.assertRaises(ValueError):
                self.library.report_bytes(identity, "report.md")

    def test_wrong_native_schema_is_not_returned_even_with_a_forged_saved_digest(self):
        identity = self.verified("m3-forecast-complete")
        path = self.library.report_file(identity, "report.json")
        report = json.loads(path.read_text())
        report["schema"] = REPORT_SCHEMAS["m3-compare"]
        raw = encode(report)
        path.write_bytes(raw)
        self.library.registered[identity]["artifacts_sha256"]["report.json"] = digest(raw)
        for operation in (
            lambda: self.library.report(identity),
            lambda: self.library.report_bytes(identity, "report.json"),
        ):
            with self.assertRaises(ValueError):
                operation()
        self.assertFalse(self.library.get(identity)["can_view_report"])

    def test_worker_refuses_non_boolean_or_disagreeing_completeness_and_wrong_schema(self):
        native = core.verify_one
        for field, value in (
            ("complete_cohort", "false"),
            ("complete_cohort", 1),
            ("human_evaluation", True),
            ("schema", REPORT_SCHEMAS["m3-compare"]),
        ):
            identity = self.index("m3-forecast-complete")

            def malformed(item, output, allow_failed):
                result = native(item, output, allow_failed)
                path = output / "report.json"
                report = json.loads(path.read_text())
                (report["evaluation"] if field == "complete_cohort" else report)[field] = value
                path.write_bytes(encode(report))
                return result

            with (
                self.subTest(field=field, value=value),
                patch("experiments.catalogue.core.verify_one", side_effect=malformed),
            ):
                job = self.operation(self.library.verify(identity))
            self.assertIsNotNone(job["error"])
            self.assertFalse(self.library.get(identity)["can_view_report"])
        identity = self.index("m3-forecast-complete")

        def disagreement(item, output, allow_failed):
            result = native(item, output, allow_failed)
            result["complete"] = False
            return result

        with patch("experiments.catalogue.core.verify_one", side_effect=disagreement):
            job = self.operation(self.library.verify(identity))
        self.assertIn("completeness differ", job["error"])
        self.assertFalse(self.library.get(identity)["can_view_report"])

    def test_missing_seal_remains_visible_and_cannot_receive_verified_report(self):
        name = "m3-compare-complete"
        (self.external / name / "manifest.json").unlink()
        identity = self.index(name)
        self.assertEqual(self.library.get(identity)["metadata_status"], "metadata_read")
        job = self.operation(self.library.verify(identity))
        self.assertIsNotNone(job["error"])
        self.assertEqual(self.library.get(identity)["verification"], "verification_failed")
        self.assertFalse(self.library.get(identity)["can_view_report"])
        with self.assertRaises(ValueError):
            self.library.report(identity)

    def test_missing_original_reports_keep_metadata_unavailable_but_use_the_sealed_native_reader(
        self,
    ):
        for name, (task, original) in self.cases.items():
            with self.subTest(name=name):
                archive = self.external / name
                expected = {
                    artifact: (archive / artifact).read_bytes()
                    for artifact in ("report.json", "report.md")
                }
                for artifact in expected:
                    (archive / artifact).unlink()
                before = inventory(archive, files=True)
                identity = self.index(name)
                self.assertEqual(self.library.get(identity)["metadata_status"], "unavailable")
                job = self.operation(self.library.verify(identity))
                self.assertIsNone(job["error"], job)
                self.assertTrue(self.library.get(identity)["can_view_report"])
                self.assertEqual(self.library.get(identity)["metadata_status"], "unavailable")
                self.assertEqual(self.library.report(identity)["native_report"], original)
                for artifact, raw in expected.items():
                    self.assertEqual(self.library.report_bytes(identity, artifact), raw)
                    self.assertFalse((archive / artifact).exists())
                self.assertEqual(inventory(archive, files=True), before)
                self.assertFalse(self.marker.exists())

    @unittest.skipUnless(os.name == "posix", "Native cancellation requires POSIX signals")
    def test_actual_cancelled_parent_with_no_original_report_preserves_unattempted_candidate(self):
        name = "m3-compare-cancelled"
        marker = self.base / "active-predictor"
        source = (
            "import time\nfrom pathlib import Path\n"
            f"Path({str(marker)!r}).touch()\n"
            "def predict(request, settings):\n"
            "    time.sleep(30)\n    return request['values_mg_dl'][-1]\n"
        )
        config_path, config = comparison_config(self.base / "cancel-prepare", second_source=source)
        config["candidates"].reverse()
        config_path.write_bytes(encode(config))
        archive = self.external / name
        process = subprocess.Popen(
            [
                sys.executable,
                "-B",
                "-E",
                "-s",
                "-S",
                "-m",
                "experiments.m3.comparison",
                "run",
                "--config",
                str(config_path),
                "--output",
                str(archive),
            ],
            cwd=ROOT,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        try:
            deadline = time.monotonic() + 10
            while not marker.exists():
                self.assertIsNone(process.poll())
                self.assertLess(time.monotonic(), deadline)
                time.sleep(0.02)
            process.send_signal(signal.SIGTERM)
            self.assertEqual(process.wait(timeout=15), 1)
        finally:
            if process.poll() is None:
                process.kill()
                process.wait()
        marker.unlink()
        shutil.rmtree(config_path.parent)
        for artifact in ("report.json", "report.md"):
            if (archive / artifact).exists():
                (archive / artifact).unlink()
        before = inventory(archive, files=True)
        request = self.library.add({"root_id": self.root_id, "path": name, "task": "m3-compare"})
        indexed = self.operation(request)
        self.assertIsNone(indexed["error"], indexed)
        identity = request["entry"]["id"]
        self.assertEqual(self.library.get(identity)["metadata_status"], "unavailable")
        job = self.operation(self.library.verify(identity))
        self.assertIsNone(job["error"], job)
        report = self.library.report(identity)
        self.assertEqual(report["report_completeness"], "incomplete")
        native = report["native_report"]
        self.assertEqual(native["candidates"]["first"]["coordinator"]["status"], "not_attempted")
        self.assertEqual(
            native["candidates"]["second"]["coordinator"]["comparison_status"], "interrupted"
        )
        self.assertEqual(native["common"]["planned_people"], 2)
        self.assertEqual(native["common"]["contributing_people"], 0)
        self.assertEqual(inventory(archive, files=True), before)
        self.assertFalse(marker.exists(), "verification reimported retained predictor")
        self.assertFalse((archive / "report.json").exists())

    def test_missing_report_unsealed_fallback_cannot_grant_a_native_snapshot(self):
        name = "m3-compare-complete"
        for artifact in ("manifest.json", "report.json", "report.md"):
            (self.external / name / artifact).unlink()
        identity = self.index(name)
        self.assertEqual(self.library.get(identity)["metadata_status"], "unavailable")
        job = self.operation(self.library.verify(identity))
        self.assertIn("sealed M3 reconstruction failed", job["error"])
        self.assertFalse(self.library.get(identity)["can_view_report"])

    def test_frozen_request_mismatch_cannot_launch_changed_pointer(self):
        identity = self.index("m3-forecast-complete")
        request = self.library.verify(identity)
        self.library.registered[identity]["tags"] = ["changed"]
        job = {"request": request, "operation": "library_verify"}
        with self.assertRaisesRegex(ValueError, "Frozen library request"):
            self.library.commands(job)

    def test_restart_retains_only_recorded_snapshot_and_never_adopts_execution(self):
        identity = self.verified("m3-compare-failed")
        restored = Library(self.service, (self.external,))
        entry = restored.get(identity)
        self.assertEqual(entry["verification"], "recorded_verification")
        self.assertTrue(entry["can_view_report"])
        self.assertEqual(restored.report(identity)["verification"], "recorded_verification")
        self.assertEqual(restored.report(identity)["report_completeness"], "incomplete")
        self.assertIsNone(self.service.active)

    def test_cancelled_or_wrong_binding_result_cannot_grant_m3_verification(self):
        identity = self.index("m3-forecast-complete")
        self.operation(self.library.verify(identity), cancel=True)
        self.assertFalse(self.library.get(identity)["can_view_report"])
        request = self.library.verify(identity)
        original = execute

        def forged(frozen, folder):
            result = original(frozen, folder)
            result["request_sha256"] = "0" * 64
            (folder / "worker-result.json").write_bytes(encode(result))
            return result

        with patch(__name__ + ".execute", side_effect=forged):
            job = self.operation(request)
        self.assertIn("bind the frozen request", job["error"])
        self.assertFalse(self.library.get(identity)["can_view_report"])


if __name__ == "__main__":
    unittest.main()
