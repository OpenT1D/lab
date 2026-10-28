"""The registered start, owned CLI and catalogue use the same native Task 2 reader."""

import json
import os
import signal
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path

from experiments.catalogue.storage import ROOT, dump
from experiments.mmtt_sampling.fixtures import export_example
from experiments.mmtt_sampling.plan import freeze
from experiments.mmtt_sampling.run import reconstruct
from experiments.observation_analysis.intake import import_observations
from experiments.workflows.checks import safe_environment


class SamplingPlatformTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        full = export_example(self.root / "input", case="constant")
        dev = export_example(self.root / "dev", True, case="constant")
        import_observations(
            dev / "package.json", dev / "observations.csv", self.root / "dev-import"
        )
        settings = json.loads((full / "settings.json").read_text())
        settings["uncertainty"]["draws"] = 32
        dump(full / "settings.json", settings)
        self.full = full
        self.config = self.root / "plan"
        freeze(
            full / "package.json",
            full / "observations.csv",
            full / "settings.json",
            full / "sampling-design.json",
            self.root / "dev-import",
            self.config,
        )

    def command(self, module, *args):
        completed = subprocess.run(
            [sys.executable, "-B", "-E", "-s", "-m", module, *map(str, args)],
            cwd=ROOT,
            env=safe_environment(),
            capture_output=True,
            text=True,
            timeout=60,
        )
        self.assertEqual(completed.returncode, 0, completed.stderr + completed.stdout[-300:])
        return json.loads(completed.stdout)

    def test_common_start_and_catalogue_verify_native_reports_without_source_changes(self):
        check = self.command(
            "experiments.workflows", "check", "mmtt-sampling", "--config", self.config
        )
        self.assertTrue(check["ready"])
        result = self.command(
            "experiments.workflows",
            "run",
            "mmtt-sampling",
            "--config",
            self.config,
            "--output",
            self.root / "result",
        )
        self.assertEqual(result["report_completeness"], "complete")
        report = (self.root / "result/report.json").read_bytes()
        self.command(
            "experiments.workflows",
            "reconstruct",
            "mmtt-sampling",
            "--archive",
            self.root / "result",
            "--output",
            self.root / "reader",
        )
        self.assertEqual((self.root / "reader/report.json").read_bytes(), report)
        request = {
            "schema": "opent1d.catalogue-request/1",
            "entries": [
                {
                    "id": "sampling",
                    "task": "mmtt-sampling",
                    "archive": str(self.root / "result"),
                    "tags": ["invented"],
                }
            ],
        }
        dump(self.root / "catalogue-request.json", request)
        indexed = self.command(
            "experiments.catalogue",
            "index",
            "--config",
            self.root / "catalogue-request.json",
            "--output",
            self.root / "catalogue",
        )
        self.assertEqual(indexed["entries"][0]["metadata_status"], "metadata_read")
        verified = self.command(
            "experiments.catalogue",
            "verify",
            "--catalogue",
            self.root / "catalogue",
            "--output",
            self.root / "verified",
        )
        self.assertEqual(
            verified["entries"][0]["verification"]["status"], "verified_reconstruction"
        )
        self.assertEqual((self.root / "result/report.json").read_bytes(), report)

    def test_actual_sigterm_keeps_unknown_atomic_work_and_all_future_schedules(self):
        settings = json.loads((self.full / "settings.json").read_text())
        settings["uncertainty"]["draws"] = 1024
        dump(self.full / "settings.json", settings)
        config = self.root / "long-plan"
        freeze(
            self.full / "package.json",
            self.full / "observations.csv",
            self.full / "settings.json",
            self.full / "sampling-design.json",
            self.root / "dev-import",
            config,
        )
        archive = self.root / "interrupted"
        process = subprocess.Popen(
            [
                sys.executable,
                "-B",
                "-E",
                "-s",
                "-m",
                "experiments.mmtt_sampling",
                "run",
                "--config",
                str(config),
                "--output",
                str(archive),
            ],
            cwd=ROOT,
            env=safe_environment(),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            start_new_session=True,
        )
        try:
            deadline = time.monotonic() + 20
            while time.monotonic() < deadline:
                try:
                    state = json.loads((archive / "studies/full/execution.json").read_text())
                    if state["phase"] == "analysis":
                        break
                except (OSError, ValueError, KeyError):
                    pass
                self.assertIsNone(process.poll(), "native analysis finished before signal test")
                time.sleep(0.005)
            else:
                self.fail("native analysis phase not observed")
            os.kill(process.pid, signal.SIGTERM)
            stdout, stderr = process.communicate(timeout=30)
            self.assertEqual(process.returncode, 1, stdout + stderr)
        finally:
            if process.poll() is None:
                process.kill()
                process.communicate()
        report = json.loads((archive / "report.json").read_text())
        self.assertEqual(report["execution_status"], "interrupted")
        self.assertEqual(report["coverage"]["planned_variant_pairs"], 60)
        self.assertGreater(report["coverage"]["unavailable_draw_pairs"], 0)
        self.assertGreater(report["coverage"]["not_attempted_draw_pairs"], 0)
        self.assertFalse(report["coverage"]["complete_cohort"])
        self.assertEqual(len(report["visit_comparisons"]), 90)
        self.assertEqual(
            reconstruct(archive, self.root / "interrupted-reader", allow_failed=True), report
        )


if __name__ == "__main__":
    unittest.main()
