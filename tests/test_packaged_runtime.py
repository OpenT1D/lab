"""Installed runtime admission and offline setup never fall back to host tools."""

import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from experiments.desktop import runtime
from experiments.durable_archives import storage
from experiments.setup import core
from scripts.windows_dependencies import selected_packages, wheel_score


class PackagedRuntimeTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.base = Path(self.temporary.name).resolve()
        self.root = self.base / "app"
        self.root.mkdir()
        self.python = self.base / "runtime/python.exe"
        self.python.parent.mkdir()
        self.python.write_bytes(b"synthetic interpreter")
        for name in ("pyproject.toml", "uv.lock"):
            (self.root / name).write_bytes(b"synthetic locked source")
        self.actual = {
            "python": "3.12.15",
            "implementation": "CPython",
            "packages": {"example": "1.0"},
            "direct_urls": {"example": None},
        }
        self.manifest = {
            "schema": runtime.SCHEMA,
            "build_id": "test-candidate",
            "runtime": {"version": "3.12.15"},
            "source": {"revision": "a" * 40, "dirty": False, "files": {}},
            "runtime_paths": {".": "runtime/python.exe"},
            "runtime_projects": {
                ".": {
                    "directory": "runtime",
                    "python": "runtime/python.exe",
                    "selectors": {
                        name: runtime._digest(self.root / name)
                        for name in ("uv.lock", "pyproject.toml")
                    },
                    "distributions": {"example": "1.0"},
                    "upstream_revisions": {},
                }
            },
            "payload_files": {
                "runtime/python.exe": {
                    "sha256": runtime._digest(self.python),
                    "bytes": self.python.stat().st_size,
                }
            },
        }
        self.save()

    def save(self):
        (self.base / "package-manifest.json").write_text(json.dumps(self.manifest))

    def probe(self):
        class Result:
            stdout = json.dumps(self.actual)

        return patch.object(runtime.subprocess, "run", return_value=Result())

    def test_private_interpreter_is_exact_and_all_metadata_matches(self):
        self.assertEqual(runtime.interpreter(source_root=self.root), self.python)
        for host, flags in (("posix", 0), ("nt", 0x00000008)):
            with (
                self.subTest(host=host),
                patch.object(runtime, "os", SimpleNamespace(name=host, fdopen=os.fdopen)),
                self.probe() as process,
            ):
                self.assertEqual(runtime.verify_packaged_project(".", self.root), self.actual)
            self.assertEqual(process.call_args.args[0][:4], [str(self.python), "-I", "-B", "-c"])
            self.assertEqual(process.call_args.kwargs["creationflags"], flags)
            self.assertEqual(process.call_args.kwargs["stdin"], subprocess.DEVNULL)
            self.assertTrue(process.call_args.kwargs["capture_output"])

    def test_tampered_or_added_runtime_bytes_are_rejected_before_probe(self):
        for name in ("unexpected.py", "__pycache__/injected.pyc"):
            path = self.python.parent / name
            path.parent.mkdir(exist_ok=True)
            path.write_bytes(b"changed")
            with self.probe() as process, self.assertRaisesRegex(ValueError, "inventory"):
                runtime.verify_packaged_project(".", self.root)
            process.assert_not_called()
            path.unlink()
        self.python.write_bytes(b"changed")
        with self.probe() as process, self.assertRaisesRegex(ValueError, "bytes"):
            runtime.verify_packaged_project(".", self.root)
        process.assert_not_called()

    def test_wrong_distribution_or_vcs_identity_is_refused(self):
        self.actual["packages"]["example"] = "2.0"
        with self.probe(), self.assertRaisesRegex(ValueError, "distribution"):
            runtime.verify_packaged_project(".", self.root)
        self.actual["packages"]["example"] = "1.0"
        self.manifest["runtime_projects"]["."]["upstream_revisions"] = {"example": "b" * 40}
        self.save()
        with self.probe(), self.assertRaisesRegex(ValueError, "upstream"):
            runtime.verify_packaged_project(".", self.root)

    def test_missing_file_and_external_hardlink_are_refused_before_probe(self):
        original = self.python.read_bytes()
        self.python.unlink()
        with self.probe() as process, self.assertRaisesRegex(ValueError, "inventory"):
            runtime.verify_packaged_project(".", self.root)
        process.assert_not_called()
        self.python.write_bytes(original)
        os.link(self.python, self.base / "outside-runtime-hardlink")
        with self.probe() as process, self.assertRaisesRegex(ValueError, "read safely"):
            runtime.verify_packaged_project(".", self.root)
        process.assert_not_called()

    def test_each_admission_rehashes_same_size_bytes_with_restored_mtime(self):
        with self.probe():
            runtime.verify_packaged_project(".", self.root)
        before = self.python.stat()
        self.python.write_bytes(b"x" * before.st_size)
        os.utime(self.python, ns=(before.st_atime_ns, before.st_mtime_ns))
        with self.probe() as process, self.assertRaisesRegex(ValueError, "bytes"):
            runtime.verify_packaged_project(".", self.root)
        process.assert_not_called()

    def test_linked_file_and_directory_are_not_traversed(self):
        outside = self.base / "outside"
        outside.mkdir()
        (outside / "data").write_bytes(b"not part of this runtime")
        link = self.python.parent / "linked"
        for target in (outside / "data", outside):
            with self.subTest(target=target.name):
                try:
                    link.symlink_to(target, target_is_directory=target.is_dir())
                except OSError as error:
                    if os.name == "nt" and getattr(error, "winerror", None) == 1314:
                        self.skipTest("Standard Windows account cannot create symbolic links")
                    raise
                try:
                    with self.probe() as process, self.assertRaisesRegex(ValueError, "read safely"):
                        runtime.verify_packaged_project(".", self.root)
                    process.assert_not_called()
                finally:
                    link.unlink()

    def test_mutation_at_final_file_snapshot_refuses_admission(self):
        original = storage.regular_entry_info

        def mutate_then_snapshot(parent, name):
            self.python.write_bytes(b"changed during the inventory")
            return original(parent, name)

        with (
            patch.object(storage, "regular_entry_info", mutate_then_snapshot),
            self.probe() as process,
            self.assertRaisesRegex(ValueError, "read safely"),
        ):
            runtime.verify_packaged_project(".", self.root)
        process.assert_not_called()

    def test_deep_runtime_inventory_does_not_rescan_absolute_ancestors_per_file(self):
        nested = self.python.parent / "Lib/site-packages/synthetic/deep/package"
        nested.mkdir(parents=True)
        for index in range(80):
            path = nested / f"file-{index:03}.py"
            path.write_bytes(f"# synthetic file {index}\n".encode())
            self.manifest["payload_files"][path.relative_to(self.base).as_posix()] = {
                "sha256": runtime._digest(path),
                "bytes": path.stat().st_size,
            }
        self.save()
        with (
            patch.object(runtime, "_path", wraps=runtime._path) as checked_path,
            self.probe(),
        ):
            self.assertEqual(runtime.verify_packaged_project(".", self.root), self.actual)
        # Validate the runtime directory and selected interpreter once each;
        # additional files are checked through the bound traversal, not _path.
        self.assertLessEqual(checked_path.call_count, 4)
        changed = nested / "file-079.py"
        changed.write_bytes(b"# changed nested source\n")
        with self.probe() as process, self.assertRaisesRegex(ValueError, "bytes"):
            runtime.verify_packaged_project(".", self.root)
        process.assert_not_called()

    def test_missing_project_and_outside_interpreter_cannot_use_host(self):
        with self.assertRaisesRegex(ValueError, "not included"):
            runtime.interpreter("unpackaged", self.root)
        self.manifest["runtime_paths"]["."] = "../host/python.exe"
        self.save()
        with self.assertRaisesRegex(ValueError, "path"):
            runtime.interpreter(source_root=self.root)

    def test_packaged_setup_uses_verification_and_bound_manifest(self):
        with patch.object(core, "ROOT", self.root), patch.object(core.shutil, "which") as host:
            self.assertEqual(core.install_argv("."), ["verify-bundled-runtime", "."])
            self.assertEqual(core.uv_identity()["kind"], "bundled-locked-runtimes")
        host.assert_not_called()


class WindowsWheelSelectionTests(unittest.TestCase):
    def test_target_python_and_platform_wheels_only(self):
        self.assertGreater(wheel_score("x-1-cp312-cp312-win_amd64.whl"), 0)
        self.assertGreater(wheel_score("x-1-py312-none-any.whl"), 0)
        self.assertGreater(wheel_score("x-1-cp39-abi3-win_amd64.whl"), 0)
        for name in (
            "x-1-cp313-cp313-win_amd64.whl",
            "x-1-cp313-abi3-win_amd64.whl",
            "x-1-cp312-cp312-win_arm64.whl",
            "x-1-cp312-cp312-manylinux.whl",
        ):
            self.assertEqual(wheel_score(name), 0)

    def test_root_markers_select_windows_dependencies(self):
        lock = {
            "manifest": {"dependency-groups": {"dev": [{"name": "root"}]}},
            "package": [
                {
                    "name": "root",
                    "source": {},
                    "dependencies": [
                        {"name": "windows", "marker": "sys_platform == 'win32'"},
                        {"name": "unix", "marker": "sys_platform != 'win32'"},
                    ],
                },
                {"name": "windows", "source": {}},
                {"name": "unix", "source": {}},
            ],
        }
        self.assertEqual(set(selected_packages(lock, root=True)), {"root", "windows"})
