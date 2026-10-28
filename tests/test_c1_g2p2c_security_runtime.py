"""Failure accounting, tamper refusal and process ownership without PyTorch."""

import os
import signal
import sys
import tempfile
import unittest
from pathlib import Path

from experiments.c1 import g2p2c_security_runtime as runtime


class SecurityRuntimeTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.archive = Path(self.temporary.name) / "archive"
        self.archive.mkdir()
        (self.archive / "protocol.json").write_bytes(runtime.PROTOCOL.read_bytes())
        runtime.save(
            self.archive / "plan.json",
            {
                "protocol": runtime.read(runtime.PROTOCOL),
                "protocol_sha256": runtime.PROTOCOL_SHA256,
                "git_revision": "synthetic-unit-fixture",
                "git_dirty": False,
                "historical_input_sha256": {},
            },
        )
        self.attempts = [
            {
                "profile": profile,
                "repetition": repetition,
                "exit_code": None,
                "error": "Unattempted",
                "duration_seconds": None,
            }
            for profile in ("adult#001", "adult#002")
            for repetition in ("primary", "repeat")
        ]
        runtime.save(self.archive / "attempts.json", self.attempts)
        self.seal()

    def seal(self):
        files = {
            str(path.relative_to(self.archive)): runtime.sha(path)
            for path in self.archive.rglob("*")
            if path.is_file() and path.name not in {"manifest.json", "report.json"}
        }
        runtime.save(
            self.archive / "manifest.json",
            {
                "schema": "opent1d.c1.g2p2c-security-manifest/1",
                "files_sha256": files,
            },
        )

    def test_unattempted_full_roster_reconstructs_as_failed(self):
        report = runtime.reconstruct(self.archive)
        self.assertFalse(report["passed"])
        self.assertEqual([case["profile"] for case in report["cases"]], ["adult#001", "adult#002"])
        self.assertEqual(sum(len(case["attempts"]) for case in report["cases"]), 4)

    def test_missing_and_reordered_resealed_roster_is_refused(self):
        for attempts in (self.attempts[:-1], self.attempts[::-1]):
            runtime.save(self.archive / "attempts.json", attempts)
            self.seal()
            with self.assertRaisesRegex(ValueError, "roster"):
                runtime.reconstruct(self.archive)

    def test_resealed_protocol_change_is_refused(self):
        protocol = runtime.read(self.archive / "protocol.json")
        protocol["runtime"]["torch"] = "2.2.0"
        runtime.save(self.archive / "protocol.json", protocol)
        self.seal()
        with self.assertRaisesRegex(ValueError, "protocol identity"):
            runtime.reconstruct(self.archive)

    def test_unsealed_extra_file_and_changed_derived_report_are_refused(self):
        report = runtime.reconstruct(self.archive)
        runtime.save(self.archive / "report.json", {**report, "passed": True})
        with self.assertRaisesRegex(ValueError, "Saved security report"):
            runtime.reconstruct(self.archive)
        (self.archive / "report.json").unlink()
        (self.archive / "undeclared.txt").write_text("synthetic extra")
        with self.assertRaisesRegex(ValueError, "inventory"):
            runtime.reconstruct(self.archive)

    def test_descriptive_cross_version_differences_are_not_acceptance(self):
        result = runtime.differences(
            [{"command": 1.0, "available": True}], [{"command": 1.25, "available": False}]
        )
        self.assertFalse(result["exact"])
        self.assertEqual(result["changed_values_by_field"], {"command": 1, "available": 1})
        self.assertEqual(result["max_absolute_difference_by_field"], {"command": 0.25})

    def test_historical_training_refuses_new_lock_before_source_training(self):
        from unittest.mock import patch

        from experiments.c1 import g2p2c_training_run as training

        plan = runtime.read(training.PLAN)
        audit = {
            "g2p2c_source_commit": plan["source_commit"],
            "m1_simglucose_commit": plan["simglucose_commit"],
        }
        with (
            patch.object(training, "source_audit", return_value=audit),
            patch.object(training, "ROOT", Path(self.temporary.name).resolve()),
            patch.object(training, "_sha", return_value="new-runtime-lock"),
            patch.object(training, "source_args") as source_args,
        ):
            with self.assertRaisesRegex(ValueError, "does not authorize retraining"):
                training.run(Path(self.temporary.name) / "source", "adult#001", mode="full")
            source_args.assert_not_called()

    @unittest.skipUnless(os.name == "posix", "process groups require POSIX")
    def test_deadline_kills_and_reaps_resistant_worker(self):
        marker = Path(self.temporary.name) / "pid.txt"
        script = (
            "import os,signal,time; signal.signal(signal.SIGTERM,signal.SIG_IGN); "
            f"open({str(marker)!r},'w').write(str(os.getpid())); time.sleep(60)"
        )
        code, error = runtime._supervise(
            [sys.executable, "-B", "-c", script],
            self.archive / "deadline.log",
            0.4,
            grace_seconds=0.2,
        )
        self.assertEqual((code, error), (-signal.SIGKILL, "WorkerDeadline"))
        pid = int(marker.read_text())
        with self.assertRaises(ProcessLookupError):
            os.kill(pid, 0)
        with self.assertRaises(ProcessLookupError):
            os.killpg(pid, 0)


if __name__ == "__main__":
    unittest.main()
