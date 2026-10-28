"""Installer supply-chain and payload boundaries, independent of a Windows host."""

import contextlib
import io
import json
import subprocess
import tarfile
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest.mock import patch

from scripts import build_windows_installer as build


class WindowsPackagingTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name).resolve()
        self.repo = self.root / "repository with spaces"
        self.repo.mkdir()
        self.command("init", "-q")
        self.command("config", "core.autocrlf", "false")
        for name, text in {
            "LICENSE": "Example license\n",
            "experiments/example.py": "print('synthetic')\n",
            "packaging/windows/THIRD-PARTY-NOTICES.txt": "Example notices\n",
            ".gitignore": "results/\n",
        }.items():
            path = self.repo / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(text.encode())
        self.command("add", ".")
        self.command(
            "-c", "user.name=Test", "-c", "user.email=test@example.invalid", "commit", "-qm", "test"
        )
        self.archive = self.root / "python.zip"
        with zipfile.ZipFile(self.archive, "w") as bundle:
            for name in ("python.exe", "pythonw.exe", "python314.zip", "LICENSE.txt"):
                bundle.writestr(name, b"synthetic runtime bytes")
        self.lock = {
            "version": "3.14.9",
            "license_file": "LICENSE.txt",
            "sha256": build.sha256(self.archive),
        }

    def command(self, *args):
        return subprocess.check_output(["git", *args], cwd=self.repo, stderr=subprocess.STDOUT)

    def test_public_snapshot_refuses_staging_before_source_or_runtime_access(self):
        (self.repo / "publication-snapshot.json").write_text("{}")
        output = self.root / "refused-public-payload"
        with (
            patch.object(build, "source_inventory") as inventory,
            patch.object(build, "extract_runtime") as extract,
            self.assertRaisesRegex(ValueError, "Public source snapshots exclude"),
        ):
            build.stage_payload(self.repo, output, self.archive, self.lock)
        inventory.assert_not_called()
        extract.assert_not_called()
        self.assertFalse(output.exists())

    def test_public_snapshot_cli_refuses_before_download_or_output_creation(self):
        (self.repo / "publication-snapshot.json").write_text("{}")
        output = self.root / "refused-public-build"
        stderr = io.StringIO()
        with (
            patch.object(
                build.sys,
                "argv",
                [
                    "build_windows_installer.py",
                    "--source-root",
                    str(self.repo),
                    "--output",
                    str(output),
                    "--stage-only",
                ],
            ),
            patch.object(build, "source_inventory") as inventory,
            patch.object(build, "download_runtime") as download,
            contextlib.redirect_stderr(stderr),
        ):
            self.assertEqual(build.main(), 1)
        self.assertIn("Public source snapshots exclude", stderr.getvalue())
        inventory.assert_not_called()
        download.assert_not_called()
        self.assertFalse(output.exists())

    def test_portable_runtime_preserves_normal_site_and_genuine_no_site_layout(self):
        archive = self.root / "portable.tar.gz"
        files = (
            "python.exe",
            "pythonw.exe",
            "python312.dll",
            "Lib/os.py",
            "LICENSE.txt",
            "Lib/__pycache__/os.cpython-312.pyc",
        )
        with tarfile.open(archive, "w:gz") as bundle:
            for name in files:
                item = tarfile.TarInfo("python/" + name)
                item.size = 3
                bundle.addfile(item, io.BytesIO(b"abc"))
        lock = {
            "archive_format": "tar.gz",
            "archive_prefix": "python/",
            "version": "3.12.15",
            "license_file": "LICENSE.txt",
            "sha256": build.sha256(archive),
        }
        destination = self.root / "portable"
        build.extract_runtime(archive, destination, lock)
        self.assertTrue((destination / "Lib/os.py").is_file())
        self.assertFalse(list(destination.glob("*._pth")))
        self.assertFalse(list(destination.rglob("__pycache__")))

    def test_portable_archive_links_and_outside_prefix_are_refused(self):
        for case in ("link", "outside"):
            archive = self.root / (case + ".tar.gz")
            with tarfile.open(archive, "w:gz") as bundle:
                item = tarfile.TarInfo("python/linked" if case == "link" else "outside/file")
                if case == "link":
                    item.type = tarfile.SYMTYPE
                    item.linkname = "../../outside"
                bundle.addfile(item)
            lock = {
                "archive_format": "tar.gz",
                "archive_prefix": "python/",
                "sha256": build.sha256(archive),
            }
            with self.assertRaisesRegex(ValueError, "Unsafe"):
                build.extract_runtime(archive, self.root / (case + "-output"), lock)

    def test_only_tracked_files_and_exact_bytes_are_staged(self):
        private = self.repo / "results/private/person.json"
        private.parent.mkdir(parents=True)
        private.write_text("DO NOT SHIP")
        destination = self.root / "payload"
        manifest = build.stage_payload(self.repo, destination, self.archive, self.lock)
        self.assertFalse(manifest["source"]["dirty"])
        self.assertFalse((destination / "app/results").exists())
        self.assertEqual(
            (destination / "app/experiments/example.py").read_bytes(),
            (self.repo / "experiments/example.py").read_bytes(),
        )
        self.assertEqual(
            (destination / "runtime/python314._pth").read_text(), "python314.zip\n.\n../app\n"
        )
        self.assertEqual(json.loads((destination / "package-manifest.json").read_text()), manifest)
        for name, record in manifest["payload_files"].items():
            self.assertEqual(build.sha256(destination / name), record["sha256"])

    def test_dirty_source_is_rejected_by_default_and_identified_for_local_tests(self):
        (self.repo / "experiments/example.py").write_text("changed = True\n")
        with self.assertRaisesRegex(ValueError, "Commit"):
            build.source_inventory(self.repo)
        self.assertTrue(build.source_inventory(self.repo, allow_dirty=True)["dirty"])

    def test_index_flags_cannot_hide_uncommitted_payload_bytes(self):
        target = self.repo / "experiments/example.py"
        original = target.read_bytes()
        for flag in ("assume-unchanged", "skip-worktree"):
            with self.subTest(flag=flag):
                self.command("update-index", "--" + flag, "experiments/example.py")
                target.write_bytes(b"changed = True\n")
                self.assertEqual(self.command("status", "--porcelain"), b"")
                with self.assertRaisesRegex(ValueError, "Commit"):
                    build.source_inventory(self.repo)
                self.assertTrue(build.source_inventory(self.repo, allow_dirty=True)["dirty"])
                target.write_bytes(original)
                self.command("update-index", "--no-" + flag, "experiments/example.py")

    def test_clean_filter_cannot_relabel_different_source_bytes_as_committed(self):
        self.command("config", "core.autocrlf", "true")
        target = self.repo / "experiments/example.py"
        target.write_bytes(target.read_bytes().replace(b"\n", b"\r\n"))
        self.command("add", "experiments/example.py")
        self.assertEqual(self.command("status", "--porcelain"), b"")
        with self.assertRaisesRegex(ValueError, "Commit"):
            build.source_inventory(self.repo)
        self.assertTrue(build.source_inventory(self.repo, allow_dirty=True)["dirty"])

    def test_missing_tracked_source_is_refused_even_for_a_local_dirty_build(self):
        (self.repo / "experiments/example.py").unlink()
        with self.assertRaisesRegex(ValueError, "missing"):
            build.source_inventory(self.repo, allow_dirty=True)

    def test_repeated_payloads_match_but_changed_bytes_cannot_reuse_reader_identity(self):
        first = build.stage_payload(
            self.repo, self.root / "first", self.archive, self.lock, build_id="candidate"
        )
        second = build.stage_payload(
            self.repo, self.root / "second", self.archive, self.lock, build_id="candidate"
        )
        self.assertEqual(first, second)
        self.assertEqual(
            (self.root / "first/runtime/python314._pth").stat().st_mtime_ns,
            (self.root / "second/runtime/python314._pth").stat().st_mtime_ns,
        )
        (self.repo / "experiments/example.py").write_text("changed = True\n")
        changed = build.stage_payload(
            self.repo,
            self.root / "changed",
            self.archive,
            self.lock,
            build_id="candidate",
            allow_dirty=True,
        )
        self.assertNotEqual(first["build_id"], changed["build_id"])

    def test_untracked_work_is_never_silently_shipped(self):
        (self.repo / "new.py").write_text("not reviewed\n")
        with self.assertRaisesRegex(ValueError, "Commit"):
            build.source_inventory(self.repo)
        record = build.source_inventory(self.repo, allow_dirty=True)
        self.assertNotIn("new.py", record["files"])

    def test_tracked_private_data_and_linked_files_are_rejected(self):
        private = self.repo / "data/private/example.csv"
        private.parent.mkdir(parents=True)
        private.write_text("private\n")
        self.command("add", str(private))
        with self.assertRaisesRegex(ValueError, "private/generated"):
            build.source_inventory(self.repo, allow_dirty=True)
        self.command("reset", "-q", "HEAD", str(private))
        target = self.repo / "experiments/example.py"
        target.unlink()
        try:
            target.symlink_to(self.repo / "LICENSE")
        except OSError:
            self.skipTest("Creating symbolic links requires permission on this host")
        with self.assertRaisesRegex(ValueError, "Linked"):
            build.source_inventory(self.repo, allow_dirty=True)

    def test_wrong_runtime_hash_is_rejected_before_extraction(self):
        self.archive.write_bytes(self.archive.read_bytes() + b"changed")
        target = self.root / "runtime"
        with self.assertRaisesRegex(ValueError, "runtime lock"):
            build.extract_runtime(self.archive, target, self.lock)
        self.assertFalse(target.exists())

    def test_archive_traversal_and_case_collisions_are_rejected(self):
        for names in (("../outside",), ("python.exe", "PYTHON.EXE"), ("C:/outside",)):
            with self.subTest(names=names):
                with zipfile.ZipFile(self.archive, "w") as bundle:
                    for name in names:
                        bundle.writestr(name, "unsafe")
                self.lock["sha256"] = build.sha256(self.archive)
                target = self.root / "runtime"
                with self.assertRaisesRegex(ValueError, "Unsafe or duplicate"):
                    build.extract_runtime(self.archive, target, self.lock)
                self.assertFalse(target.exists())

    def test_build_identifiers_cannot_inject_installer_directives(self):
        for value in ("../escape", 'bad"name', "bad\n!system command"):
            with self.subTest(value=value), self.assertRaisesRegex(ValueError, "Build id"):
                build.stage_payload(
                    self.repo,
                    self.root / "payload",
                    self.archive,
                    self.lock,
                    build_id=value,
                )
        with self.assertRaisesRegex(ValueError, "Invalid installer path"):
            build.nsis_literal("unsafe\n!system command")


if __name__ == "__main__":
    unittest.main()
