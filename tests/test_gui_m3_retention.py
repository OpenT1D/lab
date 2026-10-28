"""Actual bounded raw copies retain unsealed M3 bytes without a reader claim."""

import json
import os
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from experiments.durable_archives import storage
from experiments.gui import forensic
from experiments.gui.library_paths import directory_identity


class RawM3RetentionTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.base = Path(self.temp.name).resolve()
        self.store = self.base / "store"
        self.archive = self.base / "unsealed"
        self.preparation = self.base / "preparation"
        self.administration = self.base / "job"
        for path in (self.store, self.archive, self.preparation, self.administration):
            path.mkdir()
        (self.archive / "empty").mkdir()
        (self.archive / "stderr.log").write_bytes(b"synthetic worker cancelled\x00\n")
        (self.preparation / "original-config.json").write_bytes(b'{"synthetic":true}\n')
        (self.administration / "command-1.log").write_bytes(b"Original outer CLI log\n")
        self.request = {
            "schema": forensic.REQUEST,
            "entry_id": "forensic-" + "a" * 32,
            "operation": "durable_forensic",
            "path": "forensic-" + "a" * 32,
            "root_identity": directory_identity(self.store),
            "source": {"path": str(self.archive), "identity": directory_identity(self.archive)},
            "preparation": {
                "path": str(self.preparation),
                "identity": directory_identity(self.preparation),
            },
            "administration": {
                "path": str(self.administration),
                "identity": directory_identity(self.administration),
            },
            "provenance": {
                "task": "m3-forecast",
                "execution_state": "cancelled",
                "recorded_pid": 123,
                "process_authority": "never adopted",
            },
        }

    def tearDown(self):
        self.temp.cleanup()

    def test_unsealed_source_survives_deletion_with_exact_empty_dirs_and_bytes(self):
        expected = storage.inventory(self.archive, storage.Budget())[0]
        result = forensic.retain(self.request)
        target = Path(result["output"])
        shutil.rmtree(self.archive)
        shutil.rmtree(self.preparation)
        self.assertEqual(storage.inventory(target / "archive", storage.Budget())[0], expected)
        self.assertEqual(
            (target / "preparation/original-config.json").read_bytes(), b'{"synthetic":true}\n'
        )
        receipt = json.loads((target / "retention.json").read_bytes())
        self.assertEqual(receipt["schema"], forensic.RECEIPT)
        self.assertTrue(result["byte_copy_verified"])
        self.assertFalse(result["integrity_verified"])
        self.assertFalse(result["reconstruction_verified"])
        self.assertIsNone(result["complete"])
        self.assertFalse((target / "manifest.json").exists())
        self.assertFalse((target / "reader").exists())
        self.assertEqual(json.loads((target / "provenance.json").read_bytes())["recorded_pid"], 123)

    def test_existing_destination_is_never_replaced(self):
        target = self.store / self.request["path"]
        target.mkdir()
        (target / "sentinel").write_bytes(b"existing")
        with self.assertRaisesRegex(ValueError, "fresh"):
            forensic.retain(self.request)
        self.assertEqual((target / "sentinel").read_bytes(), b"existing")

    def test_links_and_hardlinks_are_refused_without_publication(self):
        for kind in ("symlink", "hardlink"):
            with self.subTest(kind=kind):
                target = self.archive / "unsafe"
                if kind == "symlink":
                    target.symlink_to(self.preparation / "original-config.json")
                else:
                    os.link(self.preparation / "original-config.json", target)
                with self.assertRaises(ValueError):
                    forensic.retain(self.request)
                target.unlink()
                self.assertFalse((self.store / self.request["path"]).exists())
                self.assertFalse(list(self.store.glob(".opent1d-durable-*")))

    def test_changed_source_and_root_identity_are_refused(self):
        self.request["source"]["identity"]["inode"] += 1
        with self.assertRaises(ValueError):
            forensic.retain(self.request)
        self.assertFalse(list(self.store.iterdir()))

    def test_during_copy_mutation_refuses_and_removes_staging(self):
        original = storage.inventory

        def changing(path, budget, **kwargs):
            result = original(path, budget, **kwargs)
            if Path(path) == self.archive and kwargs.get("destination"):
                (self.archive / "stderr.log").write_bytes(b"changed")
            return result

        with (
            patch.object(storage, "inventory", side_effect=changing),
            self.assertRaisesRegex(ValueError, "changed"),
        ):
            forensic.retain(self.request)
        self.assertFalse(list(self.store.iterdir()))

    def test_unsafe_task_or_output_alias_is_refused(self):
        for change in (
            {"path": "../escape"},
            {"provenance": {"task": "human-study"}},
            {"path": "package-other"},
        ):
            with self.subTest(change=change), self.assertRaises(ValueError):
                forensic.retain(self.request | change)
        self.assertFalse(list(self.store.iterdir()))

    def test_interruption_unwinds_owned_staging(self):
        original = storage.inventory

        def interrupted(path, budget, **kwargs):
            if kwargs.get("destination"):
                raise KeyboardInterrupt("cancelled")
            return original(path, budget, **kwargs)

        with (
            patch.object(storage, "inventory", side_effect=interrupted),
            self.assertRaises(KeyboardInterrupt),
        ):
            forensic.retain(self.request)
        self.assertFalse(list(self.store.iterdir()))


if __name__ == "__main__":
    unittest.main()
