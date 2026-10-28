"""Installed-reader byte trust fixtures; these are not Windows runtime acceptance."""

import hashlib
import json
import os
import shlex
import shutil
import sys
import tempfile
import unittest
from pathlib import Path, PureWindowsPath
from unittest.mock import patch

from experiments.durable_archives import core, installed, reader, storage

READER = """import argparse,json
from pathlib import Path
p=argparse.ArgumentParser()
p.add_argument('operation')
p.add_argument('--archive',type=Path)
p.add_argument('--output',type=Path)
p.add_argument('--allow-failed',action='store_true')
a=p.parse_args()
r=json.loads((a.archive/'state.json').read_text())
a.output.mkdir()
(a.output/'report.json').write_text(json.dumps(r,sort_keys=True))
(a.output/'report.md').write_text('# Controlled synthetic fixture\\n')
(a.output/'figure.svg').write_text('<svg/>')
"""


def descriptor(raw):
    return {"sha256": hashlib.sha256(raw).hexdigest(), "bytes": len(raw)}


class InstalledReaderTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.base = Path(self.temporary.name).resolve()
        self.payload = self.base / "payload"
        self.source = self.payload / "app"
        module = self.source / "experiments/m4/secure_study/__main__.py"
        module.parent.mkdir(parents=True)
        module.write_text(READER)
        self.runtime = self.payload / "runtime/python.exe"
        self.runtime.parent.mkdir()
        # POSIX integration uses an explicit absolute host interpreter wrapper;
        # Windows identity tests do not execute this fixture runtime.
        self.runtime.write_text("#!/bin/sh\nexec " + shlex.quote(sys.executable) + ' "$@"\n')
        self.runtime.chmod(0o700)
        self.revision = "a" * 40
        self.manifest = {
            "schema": "opent1d.windows-package/1",
            "source": {
                "revision": self.revision,
                "dirty": False,
                "files": {
                    module.relative_to(self.source).as_posix(): descriptor(module.read_bytes())
                },
            },
            "runtime_paths": {".": "runtime/python.exe"},
            "payload_files": {"runtime/python.exe": descriptor(self.runtime.read_bytes())},
        }
        self.save_manifest()

    def tearDown(self):
        self.temporary.cleanup()

    def save_manifest(self):
        (self.payload / "package-manifest.json").write_bytes(storage.encoded(self.manifest))

    def identity(self, revision=None):
        with patch.object(reader, "git", side_effect=AssertionError("Git must not be invoked")):
            return reader.checkout_identity(
                self.source, revision or self.revision, storage.Budget()
            )

    def test_clean_package_binds_source_and_runtime_without_git(self):
        identity, signatures = self.identity()
        self.assertEqual(identity["revision"], self.revision)
        self.assertEqual(identity["files"], installed.records(self.manifest["source"]["files"]))
        self.assertIn("/package-manifest.json", signatures)
        self.assertTrue(any(name.startswith("/runtime/") for name in signatures))
        argv = reader.command(
            "m4-study-secure", self.base / "archive", self.source, self.base / "out"
        )
        self.assertEqual(argv[0], str(self.runtime))
        self.assertIn("-S", argv)

    def test_interpreter_selection_hashes_each_tree_once_and_never_caches_bytes(self):
        with patch.object(storage, "inventory", wraps=storage.inventory) as inventory:
            self.assertEqual(installed.executable(self.source, storage.Budget()), self.runtime)
        self.assertEqual(
            [call.args[0] for call in inventory.call_args_list],
            [self.source, self.runtime.parent],
        )
        before = self.runtime.stat()
        self.runtime.write_bytes(b"x" * before.st_size)
        os.utime(self.runtime, ns=(before.st_atime_ns, before.st_mtime_ns))
        with self.assertRaisesRegex(ValueError, "runtime bytes changed"):
            reader.command("m4-study-secure", self.base / "archive", self.source, self.base / "out")

    def test_revision_selection_does_not_authorize_dirty_or_changed_installations(self):
        from experiments.gui.durable_worker import current_revision

        archive = self.base / "archive"
        archive.mkdir()
        (archive / "state.json").write_text("{}")
        module = self.source / next(iter(self.manifest["source"]["files"]))
        original_module, original_python = module.read_bytes(), self.runtime.read_bytes()
        for changed in ("dirty", "source", "runtime"):
            with self.subTest(changed=changed):
                self.manifest["source"]["dirty"] = changed == "dirty"
                self.save_manifest()
                module.write_bytes(
                    original_module + b"# changed" if changed == "source" else original_module
                )
                self.runtime.write_bytes(
                    b"changed runtime" if changed == "runtime" else original_python
                )
                with patch.object(storage, "inventory", wraps=storage.inventory) as inventory:
                    revision = current_revision(self.source)
                self.assertEqual(revision, self.revision)
                inventory.assert_not_called()  # Revision selection grants no byte trust.
                with (
                    patch.object(reader, "reconstruct") as reconstruct,
                    self.assertRaises(ValueError),
                ):
                    core.export_archive(
                        "m4-study-secure", archive, self.source, revision, self.base / "out"
                    )
                reconstruct.assert_not_called()
                self.assertFalse((self.base / "out").exists())

    @unittest.skipUnless(os.name == "posix", "Fixture uses a POSIX host-runtime wrapper")
    def test_final_reader_check_refuses_same_size_mutation_before_publication(self):
        archive = self.base / "archive"
        archive.mkdir()
        (archive / "state.json").write_text(
            json.dumps({"schema": "m4-secure-study-report/1", "passed": True})
        )
        module = self.source / next(iter(self.manifest["source"]["files"]))
        original_verify = core._verified
        for target in (module, self.runtime):
            with self.subTest(target=target.name):
                raw, before = target.read_bytes(), target.stat()

                def change_after_payload_verification(*args, **kwargs):
                    result = original_verify(*args, **kwargs)
                    target.write_bytes(b"x" * len(raw))
                    os.utime(target, ns=(before.st_atime_ns, before.st_mtime_ns))
                    return result

                try:
                    with patch.object(core, "_verified", change_after_payload_verification):
                        with self.assertRaisesRegex(ValueError, "bytes changed"):
                            core.export_archive(
                                "m4-study-secure",
                                archive,
                                self.source,
                                self.revision,
                                self.base / "out",
                            )
                    self.assertFalse((self.base / "out").exists())
                    self.assertFalse(list(self.base.glob(".opent1d-durable-*")))
                finally:
                    target.write_bytes(raw)

    def test_dirty_build_wrong_revision_and_changed_source_are_refused(self):
        self.manifest["source"]["dirty"] = True
        self.save_manifest()
        with self.assertRaisesRegex(ValueError, "clean committed"):
            self.identity()
        self.manifest["source"]["dirty"] = False
        self.save_manifest()
        with self.assertRaisesRegex(ValueError, "revision differs"):
            self.identity("b" * 40)
        module = self.source / next(iter(self.manifest["source"]["files"]))
        module.write_text(READER + "# changed\n")
        with self.assertRaisesRegex(ValueError, "source bytes changed"):
            self.identity()

    def test_extra_and_missing_source_and_changed_runtime_are_refused(self):
        extra = self.source / "unexpected.py"
        extra.write_text("# extra")
        with self.assertRaisesRegex(ValueError, "source bytes changed"):
            self.identity()
        extra.unlink()
        module = self.source / next(iter(self.manifest["source"]["files"]))
        original = module.read_bytes()
        module.unlink()
        with self.assertRaisesRegex(ValueError, "source bytes changed"):
            self.identity()
        module.write_bytes(original)
        self.runtime.write_text("# modified private runtime")
        with self.assertRaisesRegex(ValueError, "runtime bytes changed"):
            self.identity()

    def test_preserved_reader_snapshot_is_not_implicitly_trusted(self):
        archived = self.base / "reader"
        shutil.copytree(self.source, archived)
        self.assertIsNone(installed.package_manifest(archived, storage.Budget()))
        with patch.object(reader, "git", side_effect=ValueError("No explicit trusted checkout")):
            with self.assertRaisesRegex(ValueError, "explicit trusted checkout"):
                reader.checkout_identity(archived, self.revision, storage.Budget())

    def test_recorded_path_overlap_checks_are_cross_flavor_and_prefix_safe(self):
        for first, second in (
            (r"\\?\C:\Archive\new", r"c:\archive"),
            (r"C:\archive", r"\\?\C:\Archive\new"),
            (r"\\?\UNC\server\share\archive\new", r"\\SERVER\share\archive"),
            ("/archive/new", "/archive"),
        ):
            with self.subTest(first=first), self.assertRaisesRegex(ValueError, "overlap"):
                storage.separate_recorded(first, second)
        storage.separate_recorded("/local/output", r"C:\foreign\archive")
        storage.separate_recorded(r"C:\local\output", "/foreign/archive")
        with self.assertRaises(ValueError):
            storage.separate_recorded("/local/output", "relative/archive")

    @unittest.skipUnless(os.name == "posix", "Fixture uses a POSIX host-runtime wrapper")
    def test_export_restore_reconstruct_selects_explicit_retained_installation(self):
        archive = self.base / "archive"
        archive.mkdir()
        (archive / "state.json").write_text(
            json.dumps({"schema": "m4-secure-study-report/1", "passed": True})
        )
        sentinel = self.base / "archived-code-executed"
        (archive / "model.py").write_text(
            "from pathlib import Path\n" + f"Path({str(sentinel)!r}).touch()\n"
        )
        package = self.base / "durable"
        with (
            patch.dict(os.environ, {"PATH": ""}),
            patch.object(reader, "git", side_effect=AssertionError("Git must not be invoked")),
        ):
            exported = core.export_archive(
                "m4-study-secure", archive, self.source, self.revision, package
            )
            self.assertTrue(exported["reconstruction_verified"])
            restored = self.base / "restored"
            core.restore_package(package, restored)
            output = self.base / "reconstructed"
            result = core.reconstruct_package(restored, self.source, self.revision, output)
            self.assertTrue(result["reconstruction_verified"])
        for name in reader.REPORTS["m4-study-secure"]:
            self.assertEqual(
                (package / "evidence/reconstructed" / name).read_bytes(),
                (output / "evidence/reconstructed" / name).read_bytes(),
            )
        self.assertFalse(sentinel.exists())
        # Windows-origin metadata is inert on this POSIX host. Canonical package
        # inventory uses '/' even when the originating/live path flavor differs.
        manifest = json.loads((package / "manifest.json").read_bytes())
        manifest["origin"]["archive_path"] = r"\\?\C:\old-install\results\study"
        manifest["reader"]["checkout_path"] = r"C:\old-install\app"
        with patch.object(core, "Path", PureWindowsPath):
            core._validate_manifest(manifest)
        (package / "manifest.json").write_bytes(storage.encoded(manifest))
        self.assertTrue(core.verify_package(package)["integrity_verified"])
        restored_foreign = self.base / "restored-foreign-provenance"
        self.assertTrue(core.restore_package(package, restored_foreign)["integrity_verified"])
