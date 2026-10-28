"""Artifact normalization and failure-retention checks without a native runtime."""

import contextlib
import csv
import importlib
import io
import json
import math
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

runner = importlib.import_module("experiments.literature.lit002.run")
report = importlib.import_module("experiments.literature.lit002.report")
verification = importlib.import_module("experiments.literature.lit002.verification")
cli = importlib.import_module("experiments.literature.lit002.__main__")


def protocol():
    return json.loads((runner.HERE / "protocol.json").read_text())


def read_impulse(directory):
    with (directory / "impulse.csv").open(newline="") as stream:
        result = {}
        for row in csv.DictReader(stream):
            arm = row.pop("arm")
            values = {name: float(value) for name, value in row.items()}
            result[(arm, values["time_min"])] = values
        return result


@contextlib.contextmanager
def mocked_native(effect):
    """Exercise the real supervisor and archival code; replace external execution."""
    original_is_file = Path.is_file

    def is_file(path):
        if path.as_posix().endswith("node_modules/ts-node/esm.mjs"):
            return True
        return original_is_file(path)

    def check_output(command, **_kwargs):
        if command[-1] == "--version":
            return "v22.22.2\n"
        return "mocked-test-provenance\n"

    def execute(command, **kwargs):
        if command[1].endswith("setup.mjs"):
            return subprocess.CompletedProcess(command, 0)
        return effect(command, **kwargs)

    def reconstructed(study, _output):
        manifest = json.loads((study / "manifest.json").read_text())
        return {"all_passed": all(case["status"] == "completed" for case in manifest["cases"])}

    with (
        patch.object(runner.shutil, "which", return_value="/mock/node"),
        patch.object(runner.subprocess, "check_output", side_effect=check_output),
        patch.object(runner.subprocess, "run", side_effect=execute),
        patch.object(Path, "is_file", autospec=True, side_effect=is_file),
        patch.object(verification, "verify_case", return_value={"all_passed": True}),
        patch.object(report, "write_report", side_effect=reconstructed),
        contextlib.redirect_stdout(io.StringIO()),
    ):
        yield


class LIT002RunnerTests(unittest.TestCase):
    def test_impulse_export_preserves_units_mass_and_delay_inventory(self):
        with tempfile.TemporaryDirectory() as temp:
            directory = Path(temp)
            runner.write_impulse(directory, protocol())
            rows = read_impulse(directory)
            self.assertEqual(len(rows), 3 * (720 * 4 + 1))
            for values in rows.values():
                self.assertTrue(all(math.isfinite(value) for value in values.values()))
                self.assertAlmostEqual(
                    values["cumulative_fraction"] + values["unabsorbed_fraction"], 1, places=12
                )
                remaining = sum(
                    values[key] for key in ("sc1_mU_per_kg", "sc2_mU_per_kg", "queue_mU_per_kg")
                )
                self.assertAlmostEqual(remaining / 200, values["unabsorbed_fraction"], places=13)
            native = rows[("cambridge_native", 55)]
            self.assertAlmostEqual(native["appearance_mU_per_kg_min"], 200 / math.e / 55)
            self.assertAlmostEqual(native["cumulative_fraction"], 1 - 2 / math.e)
            waiting = rows[("faggionato_sc", 5.5)]
            self.assertEqual(waiting["queue_mU_per_kg"], 200)
            self.assertEqual(waiting["appearance_mU_per_kg_min"], 0)
            self.assertEqual(waiting["cumulative_fraction"], 0)
            self.assertEqual(rows[("faggionato_sc", 5.75)]["queue_mU_per_kg"], 0)

    def test_impulse_arm_labels_do_not_depend_on_protocol_order(self):
        with tempfile.TemporaryDirectory() as temp:
            original, reordered = Path(temp) / "original", Path(temp) / "reordered"
            original.mkdir()
            reordered.mkdir()
            specification = protocol()
            runner.write_impulse(original, specification)
            specification["arms"] = list(reversed(specification["arms"]))
            runner.write_impulse(reordered, specification)
            self.assertEqual(read_impulse(original), read_impulse(reordered))
            self.assertEqual(
                json.loads((original / "impulse_metrics.json").read_text()),
                json.loads((reordered / "impulse_metrics.json").read_text()),
            )

    def test_timeout_retains_partial_case_and_completes_remaining_matrix(self):
        attempted = []

        def process(command, **_kwargs):
            case_dir = Path(command[-1])
            attempted.append(case_dir.name)
            (case_dir / "partial-native.txt").write_text("Preserved native diagnostic\n")
            if len(attempted) == 1:
                raise subprocess.TimeoutExpired(command, 180)
            return subprocess.CompletedProcess(command, 0)

        with tempfile.TemporaryDirectory() as temp, mocked_native(process):
            output = Path(temp) / "study"
            result = runner.run(output)
            manifest = json.loads((output / "manifest.json").read_text())
            self.assertFalse(result["all_passed"])
            self.assertEqual(len(attempted), 18)
            self.assertEqual(len(set(attempted)), 18)
            self.assertEqual(manifest["status"], "completed_with_failures")
            self.assertEqual(sum(case["status"] == "completed" for case in manifest["cases"]), 17)
            first = manifest["cases"][0]
            self.assertEqual(first["status"], "failed")
            self.assertIn("TimeoutExpired", first["error"])
            self.assertTrue((output / first["path"] / "partial-native.txt").is_file())
            self.assertIn(f"{first['path']}/partial-native.txt", manifest["artifacts"])
            self.assertIn(f"{first['path']}/supervisor_failure.json", manifest["artifacts"])

    def test_preparation_failure_seals_all_unexecuted_cases_as_failed(self):
        attempted = []

        def process(command, **_kwargs):
            attempted.append(command)
            return subprocess.CompletedProcess(command, 0)

        with (
            tempfile.TemporaryDirectory() as temp,
            mocked_native(process),
            patch.object(
                runner, "write_impulse", side_effect=ValueError("deliberate preparation fault")
            ),
        ):
            output = Path(temp) / "study"
            result = runner.run(output)
            manifest = json.loads((output / "manifest.json").read_text())
            self.assertFalse(result["all_passed"])
            self.assertEqual(attempted, [])
            self.assertEqual(len(manifest["cases"]), 18)
            self.assertTrue(all(case["status"] == "failed" for case in manifest["cases"]))
            self.assertEqual(manifest["status"], "completed_with_failures")
            self.assertIn("preparation_failure.json", manifest["artifacts"])
            for case in manifest["cases"]:
                self.assertIn(f"{case['path']}/config.json", manifest["artifacts"])
                self.assertIn(f"{case['path']}/supervisor_failure.json", manifest["artifacts"])
                self.assertIn("preparation", case["error"])

    def test_cli_returns_failure_status_when_reconstructed_checks_fail(self):
        with (
            patch("sys.argv", ["lit002", "report", "--study", "study", "--output", "report"]),
            patch.object(report, "write_report", return_value={"all_passed": False}),
            contextlib.redirect_stdout(io.StringIO()),
            self.assertRaises(SystemExit) as caught,
        ):
            cli.main()
        self.assertEqual(caught.exception.code, 1)


if __name__ == "__main__":
    unittest.main()
