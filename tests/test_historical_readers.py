"""Trusted-checkout boundaries, standard-library execution and immutable evidence."""

import json
import shutil
import signal
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import patch

from experiments.catalogue.storage import ROOT, inventory, load_sealed
from experiments.historical_readers import core


class HistoricalReaderTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.checkout = self.base / "trusted"
        self.checkout.mkdir()
        self.archive = self.base / "archive"
        self.archive.mkdir()
        (self.archive / "evidence.json").write_text('{"accepted": true}\n')

    def trusted(self, code):
        package = self.checkout / "experiments/campaigns"
        package.mkdir(parents=True)
        (package.parent / "__init__.py").write_text("")
        (package / "__init__.py").write_text("")
        (package / "__main__.py").write_text(code)
        (self.checkout / ".gitignore").write_text(".venv/\n")
        git = shutil.which("git")
        args = [git, "--no-optional-locks", "-C", str(self.checkout)]
        subprocess.run([*args, "init", "-q"], check=True, capture_output=True)
        subprocess.run([*args, "add", "."], check=True, capture_output=True)
        subprocess.run(
            [
                *args,
                "-c",
                "user.name=Test",
                "-c",
                "user.email=test@example.invalid",
                "commit",
                "-qm",
                "fixture",
            ],
            check=True,
            capture_output=True,
        )
        return subprocess.check_output([*args, "rev-parse", "HEAD"], text=True).strip()

    def success(self, passed=True, extra=""):
        return self.trusted(
            "import json, sys\nfrom pathlib import Path\n"
            + extra
            + "assert sys.flags.no_site and sys.flags.ignore_environment\n"
            + "assert sys.flags.no_user_site\n"
            + "assert not any(name in sys.modules for name in ('urllib3','requests','numpy'))\n"
            + "output = Path(sys.argv[sys.argv.index('--output') + 1])\n"
            + "output.mkdir()\n"
            + f"(output / 'report.json').write_text(json.dumps({{'passed': {passed!r}}}))\n"
        )

    def run_reader(self, revision, **kwargs):
        return core.reconstruct(
            "campaign", self.archive, self.checkout, revision, self.base / "output", **kwargs
        )

    def test_current_stdlib_python_ignores_old_environment_and_archive_code(self):
        revision = self.success()
        (self.archive / "__main__.py").write_text("raise RuntimeError('archived code executed')")
        historical_env = self.checkout / ".venv/bin"
        historical_env.mkdir(parents=True)
        (historical_env / "python").write_text("raise RuntimeError('old interpreter selected')")
        before = inventory(self.archive)
        with patch.dict(
            "os.environ", {"PYTHONPATH": str(self.archive), "VIRTUAL_ENV": str(self.archive)}
        ):
            result = self.run_reader(revision)
        self.assertTrue(result["verified_reconstruction"])
        self.assertTrue(result["complete"])
        self.assertEqual(result["argv"][:5], [sys.executable, "-B", "-E", "-s", "-S"])
        self.assertEqual(inventory(self.archive), before)
        self.assertTrue(result["archive_unchanged"] and result["checkout_unchanged"])
        load_sealed(self.base / "output")

    def test_failed_science_remains_incomplete_after_successful_reconstruction(self):
        result = self.run_reader(self.success(passed=False), allow_failed=True)
        self.assertTrue(result["verified_reconstruction"])
        self.assertFalse(result["complete"])
        self.assertIn("--allow-failed", result["argv"])

    def test_secure_successor_uses_only_its_fixed_registered_reader_command(self):
        output = self.base / "rebuilt"
        self.assertEqual(
            core.reader_args("m4-study-secure", self.archive, output, True),
            [
                "-m",
                "experiments.m4.secure_study",
                "reconstruct",
                "--archive",
                str(self.archive),
                "--output",
                str(output),
                "--allow-failed",
            ],
        )

    def test_wrong_revision_dirty_checkout_and_unknown_task_never_execute(self):
        revision = self.success()
        with patch(
            "experiments.historical_readers.core.supervise", side_effect=AssertionError("executed")
        ):
            with self.assertRaisesRegex(ValueError, "revision differs"):
                self.run_reader("0" * 40)
            (self.checkout / "untracked.py").write_text("bad")
            with self.assertRaisesRegex(ValueError, "clean"):
                self.run_reader(revision)
            with self.assertRaisesRegex(ValueError, "Unregistered"):
                core.reader_args("archive.module", self.archive, self.base / "unused", False)

    def test_overlap_existing_output_and_symlink_archive_refused(self):
        revision = self.success()
        with self.assertRaisesRegex(ValueError, "overlaps"):
            core.reconstruct(
                "campaign", self.archive, self.checkout, revision, self.checkout / "output"
            )
        with self.assertRaisesRegex(ValueError, "fresh"):
            core.reconstruct("campaign", self.archive, self.checkout, revision, self.archive)
        link = self.base / "link"
        link.symlink_to(self.archive, target_is_directory=True)
        with self.assertRaisesRegex(ValueError, "Symlink"):
            core.reconstruct("campaign", link, self.checkout, revision, self.base / "output")

    def test_mutating_reader_cannot_receive_verified_receipt(self):
        revision = self.success(
            extra="archive = Path(sys.argv[sys.argv.index('--campaign') + 1])\n"
            "(archive / 'evidence.json').write_text('changed')\n"
        )
        result = self.run_reader(revision)
        self.assertFalse(result["verified_reconstruction"])
        self.assertEqual(result["status"], "failed")
        self.assertFalse(result["archive_unchanged"])
        self.assertIn("archive: ValueError", result["errors"])
        load_sealed(self.base / "output")

    def test_reader_rejection_retains_log_and_receipt_without_installation(self):
        revision = self.trusted("raise SystemExit('Frozen archive inventory changed')\n")
        result = self.run_reader(revision)
        self.assertEqual(result["exit_code"], 1)
        self.assertFalse(result["verified_reconstruction"])
        self.assertIn(
            "Frozen archive inventory changed", (self.base / "output/reader.log").read_text()
        )
        self.assertFalse((self.checkout / ".venv").exists())
        self.assertTrue(result["archive_unchanged"])

    def test_timeout_reaps_reader_and_retains_failed_receipt(self):
        revision = self.trusted("import time\ntime.sleep(60)\n")
        result = self.run_reader(revision, timeout_seconds=1)
        self.assertFalse(result["verified_reconstruction"])
        self.assertIn("TimeoutExpired", result["errors"])
        self.assertTrue(result["checkout_unchanged"] and result["archive_unchanged"])
        load_sealed(self.base / "output")

    def test_sigterm_reaps_owned_reader_and_descendant(self):
        pids = self.base / "pids.json"
        revision = self.trusted(
            "import json, os, subprocess, sys, time\nfrom pathlib import Path\n"
            "child = subprocess.Popen([sys.executable, '-S', '-c',\n"
            "    'import time; time.sleep(60)'])\n"
            f"Path({str(pids)!r}).write_text(json.dumps([os.getpid(), child.pid]))\n"
            "time.sleep(60)\n"
        )
        process = subprocess.Popen(
            [
                sys.executable,
                "-B",
                "-S",
                "-m",
                "experiments.historical_readers",
                "reconstruct",
                "campaign",
                "--archive",
                str(self.archive),
                "--checkout",
                str(self.checkout),
                "--revision",
                revision,
                "--output",
                str(self.base / "output"),
            ],
            cwd=ROOT,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        self.addCleanup(lambda: process.poll() is None and process.kill())
        deadline = time.monotonic() + 10
        while not pids.exists() and process.poll() is None and time.monotonic() < deadline:
            time.sleep(0.025)
        self.assertTrue(pids.exists())
        process.send_signal(signal.SIGTERM)
        process.communicate(timeout=15)
        result = json.loads((self.base / "output/receipt.json").read_text())
        diagnostic = {
            key: result[key]
            for key in (
                "status",
                "interruption_signal",
                "exit_code",
                "errors",
                "archive_unchanged",
                "checkout_unchanged",
            )
        }
        self.assertEqual(result["status"], "interrupted", json.dumps(diagnostic, sort_keys=True))
        self.assertEqual(result["interruption_signal"], signal.SIGTERM)
        self.assertFalse(result["verified_reconstruction"])
        for pid in json.loads(pids.read_text()):
            state = subprocess.run(
                ["ps", "-o", "stat=", "-p", str(pid)], capture_output=True, text=True
            ).stdout.strip()
            self.assertTrue(not state or state.startswith("Z"), state)


if __name__ == "__main__":
    unittest.main()
