"""Preservation/security fixtures; these do not substitute for native acceptance."""

import hashlib
import json
import os
import shutil
import signal
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import patch

from experiments.durable_archives import core, reader, storage

ROOT = Path(__file__).resolve().parents[1]
FIXED_READER = """import argparse,json
from pathlib import Path
parser=argparse.ArgumentParser()
parser.add_argument("operation")
parser.add_argument("--archive",type=Path)
parser.add_argument("--campaign",type=Path)
parser.add_argument("--output",type=Path)
parser.add_argument("--allow-failed",action="store_true")
args=parser.parse_args()
archive=args.archive or args.campaign
record=json.loads((archive/"state.json").read_text())
record["schema"]=("m4-secure-study-report/1" if args.archive
    else "opent1d.maintained-campaign-report/1")
args.output.mkdir()
(args.output/"report.json").write_text(json.dumps(record,sort_keys=True))
(args.output/"report.md").write_text("# Fixture\\n"+record["original_path"]+"\\n")
if args.archive:
    (args.output/"figure.svg").write_text("<svg xmlns='http://www.w3.org/2000/svg'/>")
print(str(args.output))
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


class DurableArchiveTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.base = Path(self.temporary.name).resolve()
        self.checkout = self.base / "checkout"
        self.checkout.mkdir()
        (self.checkout / ".gitignore").write_text("results/\n__pycache__/\n")
        for module in ("experiments/m4/secure_study", "experiments/maintained_campaigns"):
            directory = self.checkout / module
            directory.mkdir(parents=True)
            (directory / "__main__.py").write_text(FIXED_READER)
        (self.checkout / "LICENSE").write_text("Synthetic fixture reader only\n")
        git(self.checkout, "init", "-q")
        git(self.checkout, "add", ".")
        git(self.checkout, "commit", "-qm", "Controlled fixed reader")
        self.revision = git(self.checkout, "rev-parse", "HEAD")
        self.archive = self.base / "original"
        self.archive.mkdir()
        (self.archive / "empty-directory").mkdir()
        (self.archive / "attempts").mkdir()
        (self.archive / "attempts" / "interrupted.log").write_bytes(b"partial attempt\x00\xff\n")
        self.state = {
            "passed": True,
            "original_path": str(self.archive),
            "planned_slots": 2,
            "accepted_slots": 2,
            "history": ["interrupted", "completed", "completed"],
        }
        self.save_state()
        self.package = self.base / "package"
        self.sentinel = self.base / "archived-code-executed"
        (self.archive / "model.py").write_text(
            "from pathlib import Path\n" + f"Path({str(self.sentinel)!r}).touch()\n"
        )

    def tearDown(self):
        self.temporary.cleanup()

    def save_state(self):
        (self.archive / "state.json").write_bytes(storage.encoded(self.state))

    def export(self, task="m4-study-secure", output=None):
        return core.export_archive(
            task, self.archive, self.checkout, self.revision, output or self.package
        )

    def manifest(self):
        return json.loads((self.package / "manifest.json").read_bytes())

    def test_whole_native_and_reader_tree_including_failed_history_and_empty_directories(self):
        original, original_signatures = storage.inventory(self.archive, storage.Budget())
        result = self.export()
        self.assertTrue(result["integrity_verified"])
        self.assertTrue(result["reconstruction_verified"])
        self.assertTrue(result["complete"])
        self.assertEqual(result["reader_revision"], self.revision)
        preserved, _ = storage.inventory(self.package / "archive", storage.Budget())
        self.assertEqual(preserved, original)
        self.assertEqual(
            storage.inventory(self.archive, storage.Budget()), (original, original_signatures)
        )
        self.assertEqual(
            set(self.manifest()["reader"]["files"]),
            set(git(self.checkout, "ls-files").splitlines()),
        )
        self.assertFalse(self.sentinel.exists())

    def test_failed_campaign_integrity_is_separate_from_numerical_completeness(self):
        self.state.update(passed=False, accepted_slots=1)
        self.save_state()
        result = self.export("maintained-campaign")
        self.assertTrue(result["reconstruction_verified"])
        self.assertFalse(result["complete"])
        passive = core.verify_package(self.package)
        self.assertTrue(passive["integrity_verified"])
        self.assertFalse(passive["reconstruction_verified"])
        self.assertFalse(passive["complete"])
        self.assertIn("Hashes do not establish authenticity", passive["interpretation"])
        self.assertEqual(
            self.manifest()["reconstruction"]["artifacts"].keys(), {"report.json", "report.md"}
        )

    def test_restore_is_byte_exact_passive_and_reconstructs_without_original_paths(self):
        self.export()
        before, _ = storage.inventory(self.package, storage.Budget())
        destination = self.base / "restored"
        with patch.object(reader, "reconstruct", side_effect=AssertionError("No execution")):
            self.assertFalse(core.verify_package(self.package)["reconstruction_verified"])
            restored = core.restore_package(self.package, destination)
        self.assertEqual(storage.inventory(destination, storage.Budget())[0], before)
        self.assertFalse(restored["reconstruction_verified"])
        second = self.base / "second-checkout"
        git(self.base, "clone", "-q", str(self.checkout), str(second))
        shutil.rmtree(self.archive)
        shutil.rmtree(self.checkout)
        output = self.base / "reconstructed"
        result = core.reconstruct_package(destination, second, self.revision, output)
        self.assertTrue(result["reconstruction_verified"])
        for name in reader.REPORTS["m4-study-secure"]:
            self.assertEqual(
                (destination / "evidence/reconstructed" / name).read_bytes(),
                (output / "evidence/reconstructed" / name).read_bytes(),
            )
        report = json.loads((output / "evidence/reconstructed/report.json").read_text())
        self.assertEqual(report["original_path"], str(self.archive))
        self.assertEqual(report["history"], self.state["history"])
        self.assertFalse(self.sentinel.exists())

    def test_saved_reader_code_is_data_and_inherited_python_selector_is_ignored(self):
        poison = self.base / "poison"
        poison.mkdir()
        (poison / "sitecustomize.py").write_text(f"open({str(self.sentinel)!r},'w').close()\n")
        with patch.dict(os.environ, {"PYTHONPATH": str(poison), "PYTHONHOME": str(poison)}):
            self.export()
        with patch.object(subprocess, "Popen", side_effect=AssertionError("Passive verify")):
            core.verify_package(self.package)
        self.assertFalse(self.sentinel.exists())

    def test_modified_missing_or_additional_bytes_are_refused(self):
        self.export()
        target = self.package / "archive/state.json"
        original = target.read_bytes()
        target.write_bytes(original + b" ")
        with self.assertRaisesRegex(ValueError, "inventory differs"):
            core.verify_package(self.package)
        target.unlink()
        with self.assertRaises(ValueError):
            core.verify_package(self.package)
        target.write_bytes(original)
        (self.package / "extra.txt").write_text("unlisted")
        with self.assertRaises(ValueError):
            core.verify_package(self.package)

    def test_manifest_traversal_duplicate_keys_and_invalid_rosters_are_refused(self):
        self.export()
        path = self.package / "manifest.json"
        original = path.read_bytes()
        manifest = self.manifest()
        manifest["files"]["archive/../outside"] = {"size": 0, "sha256": "0" * 64}
        path.write_bytes(storage.encoded(manifest))
        with self.assertRaises(ValueError):
            core.verify_package(self.package)
        path.write_bytes(original.replace(b'"schema":', b'"schema":"duplicate","schema":', 1))
        with self.assertRaises(ValueError):
            core.verify_package(self.package)
        path.write_bytes(original)
        manifest = self.manifest()
        manifest["reader"]["files"].clear()
        path.write_bytes(storage.encoded(manifest))
        with self.assertRaises(ValueError):
            core.verify_package(self.package)

    def test_symlink_file_directory_ancestor_and_hardlinks_are_refused(self):
        self.export()
        target = self.package / "archive/model.py"
        raw = target.read_bytes()
        target.unlink()
        target.symlink_to(self.archive / "model.py")
        with self.assertRaises(ValueError):
            core.verify_package(self.package)
        target.unlink()
        target.write_bytes(raw)
        link = self.base / "package-link"
        link.symlink_to(self.package, target_is_directory=True)
        with self.assertRaises(ValueError):
            core.verify_package(link)
        parent_link = self.base / "parent-link"
        parent_link.symlink_to(self.base, target_is_directory=True)
        with self.assertRaises(ValueError):
            core.verify_package(parent_link / "package")
        os.link(target, self.package / "archive/hardlink")
        with self.assertRaisesRegex(ValueError, "Hardlinked"):
            core.verify_package(self.package)

    def test_special_files_aliases_and_noncanonical_unicode_are_refused_before_reader(self):
        with patch.object(reader, "reconstruct", side_effect=AssertionError("Must not dispatch")):
            fifo = self.archive / "pipe"
            os.mkfifo(fifo)
            with self.assertRaises(ValueError):
                self.export()
            fifo.unlink()
            # On a case-insensitive host the filesystem itself collapses ASCII
            # aliases; use manifest aliases to exercise portable admission.
            fake = {
                "schema": core.SCHEMA,
                "task": "m4-study-secure",
                "origin": {},
                "reader": {},
                "reconstruction": {},
                "files": {
                    "archive/model.py": {"size": 0, "sha256": "0" * 64},
                    "archive/Model.py": {"size": 0, "sha256": "0" * 64},
                },
                "directories": ["archive", "evidence", "reader"],
                "totals": {},
            }
            with self.assertRaisesRegex(ValueError, "alias"):
                core._validate_manifest(fake)
            (self.archive / "e\u0301.txt").write_text("decomposed")
            with self.assertRaisesRegex(ValueError, "noncanonical"):
                self.export()

    def test_existing_overlapping_and_portable_case_alias_destinations_are_refused(self):
        self.export()
        for output in (
            self.package,
            self.archive / "nested",
            self.package / "nested",
            self.base / "PACKAGE",
        ):
            with self.subTest(output=output), self.assertRaises(ValueError):
                core.restore_package(self.package, output)
        (self.checkout / "results").mkdir()
        with self.assertRaises(ValueError):
            self.export(output=self.checkout / "results/package")
        self.assertFalse(any(self.base.glob(".opent1d-durable-*")))

    def test_full_revision_dirty_reader_and_hidden_index_changes_are_refused(self):
        for revision in ("HEAD", "f" * 40):
            with self.assertRaises(ValueError):
                core.export_archive(
                    "m4-study-secure", self.archive, self.checkout, revision, self.package
                )
        source = self.checkout / "LICENSE"
        git(self.checkout, "update-index", "--assume-unchanged", "LICENSE")
        source.write_text("hidden working change\n")
        self.assertEqual(git(self.checkout, "status", "--porcelain"), "")
        with self.assertRaisesRegex(ValueError, "differ from recorded Git revision"):
            self.export()
        self.assertFalse(self.package.exists())

    def test_reconstruction_rejects_wrong_or_mutated_checkout_without_dispatch(self):
        self.export()
        output = self.base / "report"
        with patch.object(reader, "reconstruct", side_effect=AssertionError("No dispatch")):
            with self.assertRaisesRegex(ValueError, "revision differs"):
                core.reconstruct_package(self.package, self.checkout, "f" * 40, output)
            (self.checkout / "LICENSE").write_text("changed")
            with self.assertRaisesRegex(ValueError, "clean"):
                core.reconstruct_package(self.package, self.checkout, self.revision, output)
        self.assertFalse(output.exists())

    def test_copy_and_reader_failures_never_publish_or_leave_staging(self):
        with patch.object(
            reader, "reconstruct", side_effect=ValueError("controlled reader failure")
        ):
            with self.assertRaisesRegex(ValueError, "controlled"):
                self.export()
        self.assertFalse(self.package.exists())
        self.assertFalse(any(self.base.glob(".opent1d-durable-*")))
        self.export()
        output = self.base / "restored"
        with patch.object(
            storage, "exclusive_rename", side_effect=ValueError("controlled publish race")
        ):
            with self.assertRaisesRegex(ValueError, "publish race"):
                core.restore_package(self.package, output)
        self.assertFalse(output.exists())
        self.assertFalse(any(self.base.glob(".opent1d-durable-*")))

    def test_source_change_while_reader_operates_is_refused(self):
        actual = reader.reconstruct

        def changed(*args, **kwargs):
            result = actual(*args, **kwargs)
            (self.archive / "attempts/interrupted.log").write_text("changed evidence")
            return result

        with patch.object(reader, "reconstruct", side_effect=changed):
            with self.assertRaisesRegex(ValueError, "Source archive changed"):
                self.export()
        self.assertFalse(self.package.exists())

    def test_streaming_file_entry_total_and_operation_limits(self):
        for setting, maximum, error in (
            ("FILE_LIMIT", 1, "byte limit"),
            ("TOTAL_LIMIT", 1, "byte limit"),
            ("FILES_LIMIT", 1, "File count"),
            ("ENTRIES_LIMIT", 1, "entry limit"),
            ("OPERATION_SECONDS", 0, "deadline"),
        ):
            with self.subTest(setting=setting), patch.object(storage, setting, maximum):
                with self.assertRaisesRegex(ValueError, error):
                    storage.inventory(self.archive, storage.Budget())

    def test_cancel_during_stream_copy_unwinds_staging_and_restores_signal_handler(self):
        self.export()
        actual = storage.stream_file
        handler = signal.getsignal(signal.SIGTERM)
        output = self.base / "cancelled-restore"

        def cancel(*args, **kwargs):
            if kwargs.get("destination") is not None:
                os.kill(os.getpid(), signal.SIGTERM)
            return actual(*args, **kwargs)

        with patch.object(storage, "stream_file", side_effect=cancel):
            with self.assertRaises(KeyboardInterrupt):
                core.restore_package(self.package, output)
        self.assertEqual(signal.getsignal(signal.SIGTERM), handler)
        self.assertFalse(output.exists())
        self.assertFalse(any(self.base.glob(".opent1d-durable-*")))
        self.assertTrue(core.verify_package(self.package)["integrity_verified"])

    def test_hangup_during_stream_copy_unwinds_staging_and_restores_signal_handler(self):
        self.export()
        actual = storage.stream_file
        handler = signal.getsignal(signal.SIGHUP)
        output = self.base / "hangup-restore"

        def cancel(*args, **kwargs):
            if kwargs.get("destination") is not None:
                os.kill(os.getpid(), signal.SIGHUP)
            return actual(*args, **kwargs)

        with patch.object(storage, "stream_file", side_effect=cancel):
            with self.assertRaises(KeyboardInterrupt):
                core.restore_package(self.package, output)
        self.assertEqual(signal.getsignal(signal.SIGHUP), handler)
        self.assertFalse(output.exists())
        self.assertFalse(any(self.base.glob(".opent1d-durable-*")))
        self.assertTrue(core.verify_package(self.package)["integrity_verified"])

    def test_second_tracked_open_rejects_fifo_swap_without_blocking(self):
        target = self.checkout / "LICENSE"
        actual = storage.stream_file

        def swapped(parent, name, **kwargs):
            value = actual(parent, name, **kwargs)
            if name == "LICENSE":
                target.unlink()
                os.mkfifo(target)
            return value

        start = time.monotonic()
        with patch.object(storage, "stream_file", side_effect=swapped):
            with self.assertRaisesRegex(ValueError, "replaced before"):
                reader.checkout_identity(self.checkout, self.revision, storage.Budget())
        self.assertLess(time.monotonic() - start, 2)

    def test_actual_reader_deadline_reaps_owned_process_and_removes_partial_staging(self):
        target = self.checkout / "experiments/m4/secure_study/__main__.py"
        pid_file = self.base / "reader.pid"
        target.write_text(
            "import os,time\nfrom pathlib import Path\n"
            + f"Path({str(pid_file)!r}).write_text(str(os.getpid()))\n"
            + "time.sleep(60)\n"
        )
        git(self.checkout, "add", ".")
        git(self.checkout, "commit", "-qm", "Controlled blocking reader")
        self.revision = git(self.checkout, "rev-parse", "HEAD")
        with self.assertRaisesRegex(ValueError, "reader deadline"):
            core.export_archive(
                "m4-study-secure",
                self.archive,
                self.checkout,
                self.revision,
                self.package,
                timeout_seconds=1,
            )
        self.assertTrue(pid_file.exists())
        with self.assertRaises(ProcessLookupError):
            os.kill(int(pid_file.read_text()), 0)
        self.assertFalse(self.package.exists())
        self.assertFalse(any(self.base.glob(".opent1d-durable-*")))

    def test_whole_budget_caps_requested_reader_deadline_and_records_effective_budget(self):
        budget = storage.Budget()
        budget.deadline = time.monotonic() + 2
        evidence = self.base / "bounded-evidence"
        result = reader.reconstruct(
            "m4-study-secure", self.archive, self.checkout, evidence, budget, 1800
        )
        self.assertEqual(result["requested_timeout_seconds"], 1800)
        self.assertLessEqual(result["effective_timeout_seconds"], 2)
        self.assertGreater(result["effective_timeout_seconds"], 0)

    def test_derived_reconstruction_allows_only_fresh_git_ignored_results_subtree(self):
        self.export()
        results = self.checkout / "results"
        results.mkdir()
        output = results / "derived"
        self.assertTrue(
            core.reconstruct_package(self.package, self.checkout, self.revision, output)[
                "reconstruction_verified"
            ]
        )
        self.assertEqual(git(self.checkout, "status", "--porcelain"), "")
        with self.assertRaisesRegex(ValueError, "under results"):
            core.reconstruct_package(
                self.package, self.checkout, self.revision, self.checkout / "derived"
            )
        with self.assertRaises(ValueError):
            core.reconstruct_package(self.package, self.checkout, self.revision, output)

    def test_combined_package_limit_is_checked_before_native_or_reader_copy(self):
        actual = storage.inventory
        copied = []

        def monitored(*args, **kwargs):
            if kwargs.get("destination") is not None:
                copied.append(kwargs["destination"])
            return actual(*args, **kwargs)

        # Each input subtree fits separately; the whole package plus its own
        # manifest exceeds ten files. No native/reader copy should begin.
        with (
            patch.object(storage, "FILES_LIMIT", 10),
            patch.object(storage, "inventory", side_effect=monitored),
        ):
            with self.assertRaisesRegex(ValueError, "inventory|totals"):
                self.export()
        self.assertEqual(copied, [])
        self.assertFalse(self.package.exists())
        self.assertFalse(any(self.base.glob(".opent1d-durable-*")))

    def test_real_manifest_and_native_file_byte_limits_are_refused_before_large_reads(self):
        self.export()
        with (self.package / "manifest.json").open("wb") as handle:
            handle.truncate(storage.MANIFEST_LIMIT + 1)
        with self.assertRaisesRegex(ValueError, "bounded regular"):
            core.verify_package(self.package)
        shutil.rmtree(self.package)
        with (self.archive / "model.py").open("wb") as handle:
            handle.truncate(storage.FILE_LIMIT + 1)
        with patch.object(
            reader, "reconstruct", side_effect=AssertionError("Oversize must not dispatch")
        ):
            with self.assertRaisesRegex(ValueError, "File exceeds"):
                self.export()

    def test_atomic_exclusive_publish_does_not_replace_competing_directory(self):
        source, target = self.base / "stage", self.base / "winner"
        source.mkdir()
        target.mkdir()
        (target / "sentinel").write_text("winner")
        with self.assertRaises(ValueError):
            storage.exclusive_rename(source, target)
        self.assertEqual((target / "sentinel").read_text(), "winner")
        self.assertTrue(source.is_dir())

    def test_cli_always_emits_bounded_result_shape_for_integrity_and_failure(self):
        self.export()
        argv = [
            sys.executable,
            "-B",
            "-E",
            "-s",
            "-S",
            "-m",
            "experiments.durable_archives",
            "verify",
            "--package",
        ]
        for package, expected in ((self.package, 0), (self.base / "missing", 2)):
            call = subprocess.run([*argv, str(package)], cwd=ROOT, capture_output=True, check=False)
            self.assertEqual(call.returncode, expected, call.stderr.decode())
            result = json.loads(call.stdout)
            self.assertEqual(result["schema"], core.RESULT_SCHEMA)
            self.assertEqual(result["operation"], "verify")
            self.assertFalse(result["reconstruction_verified"])
            self.assertLess(len(call.stdout), 1024 * 1024)
        self.assertEqual(self.manifest()["reader"]["revision"], self.revision)
        self.assertEqual(
            core.verify_package(self.package)["package_identity"],
            hashlib.sha256((self.package / "manifest.json").read_bytes()).hexdigest(),
        )


if __name__ == "__main__":
    unittest.main()
