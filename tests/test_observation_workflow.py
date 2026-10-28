"""Real local CLI, fresh repeats, moved archives and resealed arithmetic failures."""

import copy
import json
import shutil
import signal
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path

from experiments.catalogue import core as catalogue
from experiments.catalogue.storage import ROOT, dump, seal
from experiments.observation_analysis.fixtures import analysis_settings, csv_bytes, package
from experiments.observation_analysis.plan import freeze
from experiments.observation_analysis.run import reconstruct, run


class ObservationWorkflowTests(unittest.TestCase):
    def test_common_entry_and_catalogue_use_the_explicit_native_reader(self):
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            self.frozen(directory)
            for operation, arguments in (
                ("check", ["--config", directory / "frozen"]),
                ("run", ["--config", directory / "frozen", "--output", directory / "result"]),
                (
                    "reconstruct",
                    ["--archive", directory / "result", "--output", directory / "rebuilt"],
                ),
            ):
                result = subprocess.run(
                    [
                        sys.executable,
                        "-B",
                        "-S",
                        "-m",
                        "experiments.workflows",
                        operation,
                        "mmtt-sensitivity",
                        *map(str, arguments),
                    ],
                    cwd=ROOT,
                    capture_output=True,
                    text=True,
                    check=True,
                )
                recorded = json.loads(result.stdout)
                self.assertNotIn("entry_error", recorded)
                if operation == "check":
                    self.assertTrue(recorded["ready"])
                    self.assertFalse(recorded["metadata"]["estimation_performed"])
                else:
                    self.assertEqual(recorded["report_completeness"], "complete")
            request = directory / "catalogue-request.json"
            dump(
                request,
                {
                    "schema": catalogue.REQUEST,
                    "entries": [
                        {
                            "id": "observation-case",
                            "task": "mmtt-sensitivity",
                            "archive": str(directory / "result"),
                            "tags": ["synthetic"],
                        }
                    ],
                },
            )
            indexed = catalogue.index(request, directory / "catalogue")
            self.assertEqual(indexed["entries"][0]["metadata_status"], "metadata_read")
            verified = catalogue.verify(directory / "catalogue", directory / "verified")
            self.assertEqual(
                verified["entries"][0]["verification"]["status"], "verified_reconstruction"
            )
            self.assertTrue(verified["entries"][0]["verification"]["complete"])

    def test_real_sigterm_retains_the_declared_roster_and_verifies_interrupted_archive(self):
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            people, rows = package(), []
            base = people["participants"][0]
            people["participants"] = []
            for i in range(8):
                person = copy.deepcopy(base)
                person["id"] = f"invented-{i:02d}"
                people["participants"].append(person)
                rows.extend(
                    [
                        [person["id"], visit, "meal-01", t, 5.5, "observed", 0.2, "observed"]
                        for visit in ("before", "after")
                        for t in (0, 30, 60, 90, 120)
                    ]
                )
            settings = analysis_settings()
            settings["uncertainty"]["draws"] = 1024
            dump(directory / "package.json", people)
            dump(directory / "settings.json", settings)
            (directory / "observations.csv").write_bytes(csv_bytes(rows))
            freeze(
                directory / "package.json",
                directory / "observations.csv",
                directory / "settings.json",
                directory / "frozen",
            )
            process = subprocess.Popen(
                [
                    sys.executable,
                    "-B",
                    "-S",
                    "-m",
                    "experiments.observation_analysis",
                    "run",
                    "--config",
                    str(directory / "frozen"),
                    "--output",
                    str(directory / "interrupted"),
                ],
                cwd=ROOT,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
            try:
                deadline, phase = time.monotonic() + 10, None
                while process.poll() is None and time.monotonic() < deadline:
                    try:
                        phase = json.loads((directory / "interrupted/execution.json").read_text())[
                            "phase"
                        ]
                    except (OSError, ValueError, KeyError):
                        pass
                    if phase == "analysis":
                        break
                    time.sleep(0.005)
                self.assertEqual(phase, "analysis")
                process.send_signal(signal.SIGTERM)
                stdout, stderr = process.communicate(timeout=10)
                self.assertEqual(process.returncode, 1, (stdout, stderr))
            finally:
                if process.poll() is None:
                    process.kill()
                    process.communicate(timeout=10)
            execution = json.loads((directory / "interrupted/execution.json").read_text())
            self.assertEqual(execution["status"], "interrupted")
            self.assertEqual(execution["interruption_signal"], signal.SIGTERM)
            report = reconstruct(
                directory / "interrupted", directory / "rebuilt", allow_failed=True
            )
            self.assertEqual(report["coverage"]["planned_people"], 8)
            self.assertEqual(len(report["unavailable_participants"]), 8)
            self.assertFalse(report["coverage"]["complete_cohort"])

    def test_complete_local_cli_and_fresh_process_repeat_after_relocation(self):
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)

            def cli(*arguments):
                result = subprocess.run(
                    [
                        sys.executable,
                        "-B",
                        "-S",
                        "-m",
                        "experiments.observation_analysis",
                        *map(str, arguments),
                    ],
                    cwd=ROOT,
                    text=True,
                    capture_output=True,
                    check=True,
                )
                return json.loads(result.stdout)

            cli("example", "--output", directory / "input")
            cli(
                "freeze",
                "--package",
                directory / "input/package.json",
                "--csv",
                directory / "input/observations.csv",
                "--settings",
                directory / "input/settings.json",
                "--output",
                directory / "frozen",
            )
            self.assertEqual(cli("check", "--config", directory / "frozen")["status"], "ready")
            for target in ("first", "repeat"):
                result = cli(
                    "run", "--config", directory / "frozen", "--output", directory / target
                )
                self.assertTrue(result["coverage"]["complete_cohort"])
            for name in ("report.json", "report.md", "attempts.json"):
                self.assertEqual(
                    (directory / "first" / name).read_bytes(),
                    (directory / "repeat" / name).read_bytes(),
                )
            shutil.move(directory / "first", directory / "relocated")
            shutil.rmtree(directory / "frozen")
            shutil.rmtree(directory / "input")
            result = cli(
                "reconstruct",
                "--archive",
                directory / "relocated",
                "--output",
                directory / "reconstructed",
            )
            self.assertEqual(result["status"], "verified")
            for name in ("report.json", "report.md"):
                self.assertEqual(
                    (directory / "relocated" / name).read_bytes(),
                    (directory / "reconstructed" / name).read_bytes(),
                )
            markdown = (directory / "reconstructed/report.md").read_text()
            for phrase in (
                "consistent within investigated assumptions",
                "C-peptide AUC",
                "glucose AUC",
                "128",
                "pmol·min/L",
                "Frozen engineering assumptions",
                "Total-secretion interval",
            ):
                self.assertIn(phrase, markdown)

    def frozen(self, directory, rows=None):
        dump(directory / "package.json", package())
        dump(directory / "settings.json", analysis_settings())
        (directory / "observations.csv").write_bytes(csv_bytes(rows))
        return freeze(
            directory / "package.json",
            directory / "observations.csv",
            directory / "settings.json",
            directory / "frozen",
        )

    def test_failures_reconstruct_and_all_attempts_survive(self):
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            rows = [
                ["invented-01", visit, "meal-01", time, 5.5, "observed", 0.2, "observed"]
                for visit in ("before", "after")
                for time in (0, 30, 60, 90, 120)
            ]
            rows[2][-2:] = ["", "below_loq"]
            self.frozen(directory, rows)
            result = run(directory / "frozen", directory / "failed")
            self.assertFalse(result["coverage"]["complete_cohort"])
            with self.assertRaisesRegex(ValueError, "allow-failed"):
                reconstruct(directory / "failed", directory / "refused")
            rebuilt = reconstruct(directory / "failed", directory / "rebuilt", allow_failed=True)
            self.assertEqual(result, rebuilt)
            self.assertEqual(len(rebuilt["people"]["invented-01"]["variants"]), 3)
            self.assertIn(
                "missing_or_censored_cpeptide", (directory / "rebuilt/report.md").read_text()
            )

    def test_resealed_forged_attempt_is_refused_by_independent_replay(self):
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            self.frozen(directory)
            run(directory / "frozen", directory / "result")
            path = directory / "result/attempts.json"
            attempts = json.loads(path.read_text())
            attempts["people"]["invented-01"]["variants"]["nominal"]["point"]["change_pmol"] = (
                999999
            )
            dump(path, attempts)
            (directory / "result/manifest.json").unlink()
            seal(directory / "result")
            with self.assertRaisesRegex(ValueError, "attempts differ"):
                reconstruct(directory / "result", directory / "forged")
            self.assertFalse((directory / "forged").exists())

    def test_unavailable_plan_is_retained_as_failure_without_invented_roster(self):
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            report = run(directory / "absent", directory / "failed")
            self.assertEqual(report["execution_status"], "failed")
            self.assertIsNone(report["coverage"]["planned_people"])
            self.assertEqual(
                report, reconstruct(directory / "failed", directory / "rebuilt", allow_failed=True)
            )


if __name__ == "__main__":
    unittest.main()
