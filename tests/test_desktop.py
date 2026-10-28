"""Installed source identity and full desktop workspace separation."""

import hashlib
import json
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from experiments.desktop.examples import FILES, prepare
from experiments.desktop.provenance import source_version
from experiments.gui.service import Service
from experiments.m3.researcher import common as researcher
from experiments.platform_files import native_absolute

ROOT = Path(__file__).resolve().parents[1]


class DesktopWorkspaceTests(unittest.TestCase):
    def test_all_controllers_and_supplied_inputs_use_separate_data_workspace(self):
        with tempfile.TemporaryDirectory() as temporary:
            workspace = native_absolute(temporary).resolve()
            service = Service(workspace, profile="desktop", source_root=ROOT)
            try:
                for name in ("m3", "campaigns", "durable", "library", "observations", "sampling"):
                    self.assertTrue(hasattr(service, name), name)
                for source in service.defaults()["sources"]:
                    for kind in ("model", "declaration"):
                        path = service.safe_path(source[kind])
                        self.assertTrue(path.is_relative_to(workspace))
                        self.assertFalse(path.is_relative_to(ROOT))
                        original = next(name for name in FILES if source[kind].endswith(name))
                        self.assertEqual(path.read_bytes(), (ROOT / original).read_bytes())
                listing = service.browse()
                self.assertTrue(listing["directory"].startswith("examples/"))
                self.assertNotIn("\\", listing["directory"])
            finally:
                service.close()

    def test_restart_preserves_examples_and_never_overwrites_user_edits(self):
        with tempfile.TemporaryDirectory() as temporary:
            workspace = Path(temporary).resolve()
            prefix = prepare(ROOT, workspace)
            self.assertEqual(prepare(ROOT, workspace), prefix)
            model = workspace / prefix / FILES[0]
            changed = model.read_bytes() + b"\n# User's retained edits\n"
            model.write_bytes(changed)
            with self.assertRaisesRegex(ValueError, "supplied example was changed"):
                prepare(ROOT, workspace)
            self.assertEqual(model.read_bytes(), changed)


class InstalledProvenanceTests(unittest.TestCase):
    def test_m3_provenance_binds_the_runtime_inventory_dependency(self):
        identity = {"revision": "1" * 40, "dirty": False}
        with patch.object(researcher, "source_version", return_value=identity):
            before = researcher.provenance()["sources"]
        helper = "experiments/durable_archives/storage.py"
        self.assertIn(helper, before)
        self.assertIn("experiments/durable_archives/__init__.py", before)
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve()
            for name in before:
                path = root / name
                path.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(ROOT / name, path)
            (root / helper).write_bytes((root / helper).read_bytes() + b"\n# changed inventory\n")
            with (
                patch.object(researcher, "ROOT", root),
                patch.object(researcher, "source_version", return_value=identity),
            ):
                after = researcher.provenance()["sources"]
        self.assertEqual(set(after), set(before))
        self.assertEqual([name for name in before if before[name] != after[name]], [helper])

    def test_no_git_needed_and_changed_missing_or_extra_source_marks_dirty(self):
        with tempfile.TemporaryDirectory() as temporary:
            payload = Path(temporary).resolve()
            root = payload / "app"
            root.mkdir()
            source = root / "source.py"
            source.write_bytes(b"# trusted original\n")
            manifest = {
                "schema": "opent1d.windows-package/1",
                "runtime_paths": {".": "runtime/python.exe"},
                "source": {
                    "revision": "1" * 40,
                    "dirty": False,
                    "files": {
                        "source.py": {
                            "bytes": source.stat().st_size,
                            "sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
                        }
                    },
                },
            }
            (payload / "package-manifest.json").write_text(json.dumps(manifest))
            with patch(
                "experiments.desktop.provenance.subprocess.check_output",
                side_effect=AssertionError("Git must not be called for an installed source"),
            ):
                self.assertEqual(source_version(root), {"revision": "1" * 40, "dirty": False})
                original = source.read_bytes()
                source.write_bytes(b"# altered\n")
                self.assertTrue(source_version(root)["dirty"])
                source.write_bytes(original)
                (root / "extra.py").write_bytes(b"# extra\n")
                self.assertTrue(source_version(root)["dirty"])
                (root / "extra.py").unlink()
                source.unlink()
                self.assertTrue(source_version(root)["dirty"])


if __name__ == "__main__":
    unittest.main()
