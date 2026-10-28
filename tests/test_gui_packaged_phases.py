"""Packaged GUI clocks and display records cannot change scientific authority."""

import copy
import json
import tempfile
import threading
import unittest
from pathlib import Path
from unittest import mock

from experiments.gui import packaged_phases
from experiments.gui.service import Service


class PackagedGUIPhaseTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name).resolve()
        self.addCleanup(self.temporary.cleanup)
        self.service = Service.__new__(Service)
        self.service.source_root = self.root
        self.service.data = self.root
        self.service.python = "bundled-python"

    def manifest(self, packaged):
        return mock.patch(
            "experiments.desktop.admission.packaged_manifest",
            return_value={"fixture": True} if packaged else None,
        )

    def test_checkout_commands_keep_original_arguments_and_allowances(self):
        configuration = {
            "id": "config-test",
            "config": {
                "sources": ["one", "two"],
                "source_timeout_seconds": 123,
            },
        }
        with self.manifest(False):
            for operation, expected in (("check", 30), ("run", 7446), ("reconstruct", 600)):
                argv, seconds = self.service.commands(
                    {"id": "job-test", "operation": operation}, configuration, self.root / "archive"
                )[0]
                self.assertEqual(seconds, expected)
                self.assertNotIn("--phase-state", argv)
                self.assertNotIn("--operation-seconds", argv)
            for operation in ("m3_fixture", "m3_check", "m3_run", "m3_reconstruct"):
                self.assertEqual(packaged_phases.m3_extra("m3-forecast", operation, 321), 0)

    def test_m4_packaged_commands_keep_native_budget_separate_from_audit(self):
        configuration = {
            "id": "config-test",
            "config": {
                "sources": ["one", "two"],
                "source_timeout_seconds": 123,
            },
        }
        with self.manifest(True):
            for operation, ceiling, native in (
                ("check", 2970, None),
                ("run", 10446, 7446),
                ("reconstruct", 1680, 600),
            ):
                argv, seconds = self.service.commands(
                    {"id": "job-test", "operation": operation}, configuration, self.root / "archive"
                )[0]
                self.assertEqual(seconds, ceiling)
                self.assertEqual(argv[argv.index("--admission-prepare-seconds") + 1], "30")
                self.assertEqual(
                    Path(argv[argv.index("--phase-state") + 1]).parent, self.root / "job-test"
                )
                if native is None:
                    self.assertNotIn("--operation-seconds", argv)
                else:
                    self.assertEqual(argv[argv.index("--operation-seconds") + 1], str(native))

    def test_m3_outer_slack_covers_each_separately_owned_phase(self):
        with self.manifest(True):
            for task in ("m3-forecast", "m3-compare"):
                self.assertEqual(packaged_phases.m3_extra(task, "m3_check"), 1020)
                self.assertEqual(packaged_phases.m3_extra(task, "m3_reconstruct"), 1170)
                self.assertEqual(packaged_phases.m3_extra(task, "m3_run", 321), 3360)
                self.assertEqual(packaged_phases.m3_extra(task, "m3_fixture"), 0)

    def test_cleanup_grace_is_reserved_only_for_packaged_phase_owners(self):
        with self.manifest(False):
            self.assertEqual(packaged_phases.cleanup_seconds([], "m3-forecast", "m3_run", 30), 30)
        with self.manifest(True):
            self.assertEqual(packaged_phases.cleanup_seconds([], "m3-forecast", "m3_run", 30), 60)
            self.assertEqual(
                packaged_phases.cleanup_seconds([], "m3-forecast", "m3_fixture", 30), 30
            )
            self.assertEqual(
                packaged_phases.cleanup_seconds([], "m4-study-secure", "campaign_run", 90), 90
            )
        self.assertEqual(
            packaged_phases.cleanup_seconds(
                ["--admission-prepare-seconds"], "m4-study-secure", "run", 30
            ),
            60,
        )

    def test_close_waits_for_current_recorded_cleanup_and_retains_lock_if_still_live(self):
        self.service.lock = threading.RLock()
        self.service.active = "job-test"
        self.service.jobs = {
            "job-test": {
                "operation": "m3_run",
                "commands": [{"argv": [], "timeout_seconds": 5000, "cleanup_seconds": 60}],
            }
        }
        self.service.cancel = mock.Mock()
        self.service.manager = mock.Mock()
        self.service.thread = mock.Mock()
        self.service.thread.is_alive.return_value = True
        with self.assertRaisesRegex(ValueError, "manager lock retained"):
            self.service.close()
        self.service.thread.join.assert_called_once_with(70)
        self.service.manager.close.assert_not_called()
        self.service.thread.is_alive.return_value = False
        self.service.close()
        self.service.manager.close.assert_called_once_with()

    def record(self, name, *, task="m3-forecast", operation="check", phase="auditing"):
        value = {
            "schema": "opent1d.packaged-admission/1",
            "task": task,
            "operation": operation,
            "phase": phase,
            "project": ".",
            "sequence": 2,
            "phase_limit_seconds": 930,
            "phase_started_monotonic": 100,
            "elapsed_seconds": 0,
            "error_type": None,
        }
        (self.root / name).write_bytes(json.dumps(value).encode())
        return value

    def test_display_uses_current_operation_without_changing_job_authority(self):
        self.record("m3-check-phase.json", phase="complete")
        expected = self.record("m3-run-phase.json", operation="run")
        job = {
            "id": self.root.name,
            "state": "running",
            "operation": "m3_run",
            "task": "m3-forecast",
            "result": {"ready": False},
        }
        original = copy.deepcopy(job)
        self.service.data = self.root.parent
        value = self.service.public(job)
        self.assertEqual(value["phase"], expected)
        self.assertEqual(job, original)
        self.assertFalse(value["result"]["ready"])
        job["state"] = "cancelling"
        self.assertNotIn("phase", self.service.public(job))
        job["state"] = "completed"
        self.assertNotIn("phase", self.service.public(job))

    def test_invalid_or_unrelated_display_record_never_breaks_job_polling(self):
        job = {"state": "running", "operation": "m3_check", "task": "m3-forecast"}
        self.record("m3-check-phase.json", task="m3-compare")
        self.assertIsNone(packaged_phases.public_phase(job, self.root))
        self.record("m3-check-phase.json", operation="run")
        self.assertIsNone(packaged_phases.public_phase(job, self.root))
        for raw in (b"{", b"x" * 8193, b'{"schema":"other"}'):
            (self.root / "m3-check-phase.json").write_bytes(raw)
            self.assertIsNone(packaged_phases.public_phase(job, self.root))


if __name__ == "__main__":
    unittest.main()
