"""Fixed M3 preservation boundaries and unchanged native-reader relocation."""

import copy
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from experiments.desktop.admission_sources import SOURCE_FILES as ADMISSION_SOURCES
from experiments.desktop.runtime import SOURCE_FILES as RUNTIME_SOURCES
from experiments.durable_archives import core, reader, storage

ROOT = Path(__file__).resolve().parents[1]
FIXED_M3_READER = """import argparse,json
from pathlib import Path
parser = argparse.ArgumentParser()
operation = "report" if Path(__file__).parent.name == "researcher" else "reconstruct"
parser.add_argument("operation", choices=[operation])
parser.add_argument("--study", type=Path, required=True)
parser.add_argument("--output", type=Path, required=True)
args = parser.parse_args()
if not (args.study / "manifest.json").is_file():
    raise ValueError("unsealed controlled archive")
record = json.loads((args.study / "state.json").read_text())
args.output.mkdir()
(args.output / "report.json").write_text(json.dumps(record, sort_keys=True, indent=2) + "\\n")
(args.output / "report.md").write_text(
    "# Controlled M3 reader\\n" + record["original_path"] + "\\n"
)
"""


def git(path, *args):
    return (
        subprocess.check_output(
            ["git", "-c", "user.email=fixture@example.invalid", "-c", "user.name=Fixture", *args],
            cwd=path,
            stderr=subprocess.DEVNULL,
        )
        .decode()
        .strip()
    )


def committed(path):
    git(path, "init", "-q")
    git(path, "add", ".")
    git(path, "commit", "-qm", "Trusted synthetic M3 reader fixture")
    return git(path, "rev-parse", "HEAD")


class M3DurableBoundaryTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.base = Path(self.temporary.name).resolve()
        self.checkout = self.base / "checkout"
        self.checkout.mkdir()
        (self.checkout / ".gitignore").write_text("__pycache__/\nresults/\n")
        for module in ("researcher", "comparison"):
            folder = self.checkout / "experiments/m3" / module
            folder.mkdir(parents=True)
            (folder / "__main__.py").write_text(FIXED_M3_READER)
        self.revision = committed(self.checkout)
        self.archive = self.base / "original"
        self.archive.mkdir()
        (self.archive / "manifest.json").write_text("controlled native seal\n")
        (self.archive / "empty-diagnostic").mkdir()
        (self.archive / "children/raw-child").mkdir(parents=True)
        (self.archive / "children/raw-child/prefix.jsonl").write_bytes(b'{"partial":true}\n\xff')
        self.sentinel = self.base / "archived-predictor-executed"
        (self.archive / "predictor.py").write_text(
            "from pathlib import Path\n" + f"Path({str(self.sentinel)!r}).touch()\n"
        )
        self.package = self.base / "package"

    def tearDown(self):
        self.temporary.cleanup()

    def report(self, task, complete=True):
        section = "evaluation" if task == "m3-forecast" else "common"
        return {
            "schema": reader.SCHEMAS[task],
            "kind": "synthetic",
            "human_evaluation": False,
            "original_path": str(self.archive),
            section: {"complete_cohort": complete, "planned_people": 2, "contributing_people": 2},
            "history": ["completed", "interrupted", "not_attempted"],
        }

    def save_report(self, report, *, originals=True):
        (self.archive / "state.json").write_bytes(storage.encoded(report))
        if originals:
            (self.archive / "report.json").write_bytes(storage.encoded(report))
            (self.archive / "report.md").write_text(
                "# Controlled M3 reader\n" + str(self.archive) + "\n"
            )

    def export(self, task):
        return core.export_archive(task, self.archive, self.checkout, self.revision, self.package)

    def test_exact_m3_routes_and_m4_allow_failed_remain_explicit(self):
        for task, module, operation in (
            ("m3-forecast", "experiments.m3.researcher", "report"),
            ("m3-compare", "experiments.m3.comparison", "reconstruct"),
        ):
            with self.subTest(task=task):
                command = reader.command(task, self.archive, self.checkout, self.package)
                self.assertEqual(command[:5], [sys.executable, "-B", "-E", "-s", "-S"])
                self.assertEqual(command[5:9], ["-m", module, operation, "--study"])
                self.assertNotIn("--allow-failed", command)
                self.assertNotIn("run", command)
        for task in ("m4-study-secure", "maintained-campaign"):
            self.assertEqual(reader.command(task, "a", "c", "o")[-1], "--allow-failed")
        with self.assertRaises(ValueError):
            reader.command("experiments.m3.researcher.worker", "a", "c", "o")

    def test_complete_is_native_cohort_not_successful_process_or_coordinator(self):
        for task in reader.M3_TASKS:
            with self.subTest(task=task):
                report = self.report(task, complete=False)
                report["execution_status_counts"] = {"completed": 2}
                report["coordinator"] = {"status": "finished"}
                self.save_report(report)
                result = self.export(task)
                self.assertTrue(result["reconstruction_verified"])
                self.assertFalse(result["complete"])
                passive = core.verify_package(self.package)
                self.assertFalse(passive["reconstruction_verified"])
                self.assertFalse(passive["complete"])
                manifest = json.loads((self.package / "manifest.json").read_bytes())
                self.assertTrue(manifest["reconstruction"]["allow_failed"])
                self.assertNotIn("--allow-failed", manifest["reconstruction"]["reader_command"])
                shutil.rmtree(self.package)

    def test_m3_schema_synthetic_scope_and_cohort_boolean_are_strict(self):
        for task in reader.M3_TASKS:
            section = "evaluation" if task == "m3-forecast" else "common"
            malformed = []
            for value in (None, 0, 1, "true", [], {}):
                report = self.report(task)
                report[section]["complete_cohort"] = value
                malformed.append(report)
            for key, value in (
                ("schema", "unrelated/1"),
                ("kind", "human"),
                ("human_evaluation", True),
            ):
                report = self.report(task)
                report[key] = value
                malformed.append(report)
            report = self.report(task)
            report.pop(section)
            malformed.append(report)
            for report in malformed:
                with self.subTest(task=task, report=report):
                    self.save_report(report)
                    with self.assertRaisesRegex(ValueError, "unsupported"):
                        self.export(task)
                    self.assertFalse(self.package.exists())
                    self.assertFalse(any(self.base.glob(".opent1d-durable-*")))

    def test_any_changed_original_m3_report_refuses_publication(self):
        for task in reader.M3_TASKS:
            for name in reader.REPORTS[task]:
                with self.subTest(task=task, name=name):
                    self.save_report(self.report(task))
                    path = self.archive / name
                    path.write_bytes(path.read_bytes() + b" ")
                    with self.assertRaisesRegex(ValueError, "Saved M3 native report differs"):
                        self.export(task)
                    self.assertFalse(self.package.exists())
                    self.assertFalse(any(self.base.glob(".opent1d-durable-*")))

    def test_sealed_missing_original_reports_do_not_synthesize_archive_members(self):
        for task in reader.M3_TASKS:
            with self.subTest(task=task):
                self.save_report(self.report(task), originals=False)
                original, _ = storage.inventory(self.archive, storage.Budget())
                self.assertTrue(self.export(task)["reconstruction_verified"])
                self.assertEqual(
                    storage.inventory(self.package / "archive", storage.Budget())[0], original
                )
                for name in reader.REPORTS[task]:
                    self.assertFalse((self.package / "archive" / name).exists())
                    self.assertTrue((self.package / "evidence/reconstructed" / name).is_file())
                self.assertFalse(self.sentinel.exists())
                shutil.rmtree(self.package)

    def test_unsealed_parent_refuses_even_if_raw_reports_exist(self):
        (self.archive / "manifest.json").unlink()
        for task in reader.M3_TASKS:
            with self.subTest(task=task):
                self.save_report(self.report(task, complete=False))
                with self.assertRaisesRegex(ValueError, "authoritative reconstruction failed"):
                    self.export(task)
                self.assertFalse(self.package.exists())
                self.assertFalse(any(self.base.glob(".opent1d-durable-*")))

    def test_saved_m3_report_binding_remains_required_by_manifest_validation(self):
        self.save_report(self.report("m3-forecast"))
        self.export("m3-forecast")
        manifest = json.loads((self.package / "manifest.json").read_bytes())
        changed = copy.deepcopy(manifest)
        changed["files"]["archive/report.md"]["sha256"] = "0" * 64
        with self.assertRaisesRegex(ValueError, "Saved M3 native report differs"):
            core._validate_manifest(changed)
        changed = copy.deepcopy(manifest)
        changed["reconstruction"]["artifacts"]["figure.svg"] = {"sha256": "0" * 64, "size": 0}
        with self.assertRaisesRegex(ValueError, "recorded reconstruction"):
            core._validate_manifest(changed)

    def test_restore_full_child_bytes_and_dirs_from_second_checkout_without_original_paths(self):
        self.save_report(self.report("m3-compare", complete=False))
        before, _ = storage.inventory(self.archive, storage.Budget())
        self.export("m3-compare")
        restored = self.base / "restored"
        with patch.object(reader, "reconstruct", side_effect=AssertionError("Passive operation")):
            core.restore_package(self.package, restored)
        self.assertEqual(storage.inventory(restored / "archive", storage.Budget())[0], before)
        second = self.base / "second"
        git(self.base, "clone", "-q", str(self.checkout), str(second))
        shutil.rmtree(self.archive)
        shutil.rmtree(self.checkout)
        output = self.base / "reconstructed"
        result = core.reconstruct_package(restored, second, self.revision, output)
        self.assertTrue(result["reconstruction_verified"])
        self.assertFalse(result["complete"])
        for name in reader.REPORTS["m3-compare"]:
            self.assertEqual(
                (restored / "evidence/reconstructed" / name).read_bytes(),
                (output / "evidence/reconstructed" / name).read_bytes(),
            )
        self.assertFalse(self.sentinel.exists())
        with self.assertRaisesRegex(ValueError, "revision differs"):
            core.reconstruct_package(restored, second, "f" * 40, self.base / "wrong-reader")
        target = restored / "archive/children/raw-child/prefix.jsonl"
        target.write_bytes(target.read_bytes() + b"changed")
        with patch.object(
            reader, "reconstruct", side_effect=AssertionError("Tamper before dispatch")
        ):
            with self.assertRaises(ValueError):
                core.reconstruct_package(restored, second, self.revision, self.base / "tampered")


class NativeM3DurableTests(unittest.TestCase):
    """Actual saved M3 readers, separate from the controlled boundary fixtures."""

    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.base = Path(self.temporary.name).resolve()
        self.checkout = self.base / "trusted"
        self.checkout.mkdir()
        paths = list((ROOT / "experiments/m3").rglob("*.py"))
        paths += list((ROOT / "experiments/m1").glob("*.py"))
        paths += list((ROOT / "experiments/desktop").glob("*.py"))
        paths += [ROOT / name for name in (*RUNTIME_SOURCES, *ADMISSION_SOURCES)]
        paths += [
            ROOT / name
            for name in (
                "experiments/platform_files.py",
                "experiments/platform_process.py",
                "experiments/gui/windows_process.py",
                "experiments/gui/windows_worker.py",
                "experiments/m0/simglucose/recording.py",
                "experiments/m3/runtime/uv.lock",
                "experiments/m3/runtime/pyproject.toml",
                "uv.lock",
                "docs/research/m3-researcher-protocol.md",
                "docs/research/m3-candidate-comparison-protocol.md",
            )
        ]
        for source in paths:
            target = self.checkout / source.relative_to(ROOT)
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(source.read_bytes())
        (self.checkout / ".gitignore").write_text("__pycache__/\nresults/\n")
        self.revision = committed(self.checkout)
        self.preparation = self.base / "preparation"
        self.archive = self.base / "native"
        self.package = self.base / "package"

    def tearDown(self):
        self.temporary.cleanup()

    def native(self, task, *, failed=False):
        module = reader.TASKS[task][0]
        call = subprocess.run(
            [
                sys.executable,
                "-B",
                "-E",
                "-s",
                "-S",
                "-m",
                module,
                "fixture",
                "--output",
                str(self.preparation),
            ],
            cwd=self.checkout,
            capture_output=True,
            timeout=30,
            check=False,
        )
        self.assertEqual(call.returncode, 0, call.stderr.decode())
        config = self.preparation / ("config.json" if task == "m3-forecast" else "comparison.json")
        if failed:
            record = json.loads(config.read_bytes())
            Path(record["people"][0]["input"]["file"]).unlink()
        call = subprocess.run(
            [
                sys.executable,
                "-B",
                "-E",
                "-s",
                "-S",
                "-m",
                module,
                "run",
                "--config",
                str(config),
                "--output",
                str(self.archive),
            ],
            cwd=self.checkout,
            capture_output=True,
            timeout=30,
            check=False,
        )
        self.assertEqual(call.returncode, 1 if failed else 0, call.stderr.decode())
        report = json.loads((self.archive / "report.json").read_bytes())
        self.assertEqual(reader.completeness(task, report), not failed)
        return report

    def relocation(self, task, *, failed=False, missing_originals=False):
        report = self.native(task, failed=failed)
        originals = {name: (self.archive / name).read_bytes() for name in reader.REPORTS[task]}
        if missing_originals:
            for name in originals:
                (self.archive / name).unlink()
        (self.archive / "empty-diagnostic").mkdir()
        original, _ = storage.inventory(self.archive, storage.Budget())
        result = core.export_archive(task, self.archive, self.checkout, self.revision, self.package)
        self.assertEqual(result["complete"], not failed)
        self.assertTrue(result["reconstruction_verified"])
        helper = "experiments/platform_files.py"
        preserved = self.package / "reader" / helper
        self.assertEqual(preserved.read_bytes(), (ROOT / helper).read_bytes())
        manifest = json.loads((self.package / "manifest.json").read_bytes())
        self.assertIn(helper, manifest["reader"]["files"])
        for name, raw in originals.items():
            self.assertEqual((self.package / "evidence/reconstructed" / name).read_bytes(), raw)
        restored = self.base / "restored"
        core.restore_package(self.package, restored)
        self.assertEqual(storage.inventory(restored / "archive", storage.Budget())[0], original)
        second = self.base / "second"
        git(self.base, "clone", "-q", str(self.checkout), str(second))
        shutil.rmtree(self.preparation)
        shutil.rmtree(self.archive)
        shutil.rmtree(self.checkout)
        output = self.base / "reconstructed"
        result = core.reconstruct_package(restored, second, self.revision, output)
        self.assertEqual(result["complete"], not failed)
        self.assertTrue(result["reconstruction_verified"])
        for name, raw in originals.items():
            self.assertEqual((output / "evidence/reconstructed" / name).read_bytes(), raw)
        rebuilt = json.loads((output / "evidence/reconstructed/report.json").read_bytes())
        self.assertEqual(rebuilt, report)
        self.assertEqual(storage.inventory(restored / "archive", storage.Budget())[0], original)
        return rebuilt

    def test_native_forecast_full_cohort_byte_identical_after_original_checkout_and_inputs_removed(
        self,
    ):
        report = self.relocation("m3-forecast")
        self.assertEqual(report["evaluation"]["planned_people"], 2)
        self.assertEqual(report["evaluation"]["contributing_people"], 2)
        self.assertEqual(report["evaluation"]["execution_status_counts"], {"completed": 2})

    def test_native_two_candidate_common_report_and_all_children_survive_relocation(self):
        report = self.relocation("m3-compare")
        self.assertEqual(len(report["candidate_order"]), 2)
        self.assertEqual(report["common"]["planned_people"], 2)
        self.assertEqual(report["common"]["contributing_people"], 2)
        self.assertEqual(set(report["candidates"]), set(report["candidate_order"]))
        for candidate in report["candidates"].values():
            self.assertEqual(candidate["single_candidate"]["evaluation"]["planned_people"], 2)

    def test_native_failed_forecast_preserves_planned_coverage_and_failure_after_relocation(self):
        report = self.relocation("m3-forecast", failed=True)
        self.assertEqual(report["evaluation"]["planned_people"], 2)
        self.assertEqual(report["evaluation"]["contributing_people"], 1)
        self.assertEqual(
            report["evaluation"]["execution_status_counts"], {"completed": 1, "failed": 1}
        )

    def test_native_parent_reader_retains_unsealed_child_as_diagnostics(self):
        # Construct a declared failed-parent fixture from unchanged native bytes;
        # this checks saved-reader semantics, not a real cancellation claim.
        report = self.native("m3-compare")
        second_id = report["candidate_order"][1]
        child = self.archive / "children" / second_id
        (child / "manifest.json").unlink()
        state_path = self.archive / "state.json"
        state = json.loads(state_path.read_bytes())
        state["status"] = "failed"
        state["candidates"][second_id].update(
            status="failed", error_type="ChildArchiveUnavailable", exit_code=1
        )
        state_path.write_bytes(storage.encoded(state))
        call = subprocess.run(
            [
                sys.executable,
                "-B",
                "-E",
                "-s",
                "-S",
                "-c",
                "from pathlib import Path; from experiments.m3.comparison.study import seal; "
                + f"seal(Path({str(self.archive)!r}))",
            ],
            cwd=self.checkout,
            capture_output=True,
            timeout=30,
            check=False,
        )
        self.assertEqual(call.returncode, 0, call.stderr.decode())
        rewritten = self.base / "rewritten"
        call = subprocess.run(
            reader.command("m3-compare", self.archive, self.checkout, rewritten),
            cwd=self.checkout,
            capture_output=True,
            timeout=30,
            check=False,
        )
        self.assertEqual(call.returncode, 0, call.stderr.decode())
        for name in reader.REPORTS["m3-compare"]:
            (self.archive / name).write_bytes((rewritten / name).read_bytes())
        raw_child, _ = storage.inventory(child, storage.Budget())
        exported = core.export_archive(
            "m3-compare", self.archive, self.checkout, self.revision, self.package
        )
        self.assertTrue(exported["reconstruction_verified"])
        self.assertFalse(exported["complete"])
        preserved = self.package / "archive/children" / second_id
        self.assertEqual(storage.inventory(preserved, storage.Budget())[0], raw_child)
        reconstructed = json.loads(
            (self.package / "evidence/reconstructed/report.json").read_bytes()
        )
        self.assertIsNone(reconstructed["candidates"][second_id]["single_candidate"])
        self.assertIn(
            "diagnostic only", reconstructed["candidates"][second_id]["missing_archive_reason"]
        )
        self.assertEqual(reconstructed["common"]["planned_people"], 2)
        self.assertEqual(reconstructed["common"]["contributing_people"], 0)

    def test_native_sealed_failed_comparison_with_missing_parent_reports_reconstructs(self):
        report = self.relocation("m3-compare", failed=True, missing_originals=True)
        self.assertFalse(report["common"]["complete_cohort"])
        self.assertEqual(report["common"]["planned_people"], 2)
        self.assertEqual(report["common"]["contributing_people"], 1)
        self.assertTrue(
            all(candidate["single_candidate"] for candidate in report["candidates"].values())
        )


if __name__ == "__main__":
    unittest.main()
