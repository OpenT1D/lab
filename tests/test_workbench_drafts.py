"""Concept persistence is separate from immutable SDK experiment evidence."""

import importlib
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from tests.test_installed_gui import PACKAGE

drafts = importlib.import_module(PACKAGE + "._gui_drafts")
files = importlib.import_module(PACKAGE + "._gui_files")


class WorkbenchDrafts(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="workbench-drafts-")
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name).resolve()
        self.store = drafts.Drafts(self.root / "drafts")
        self.project = "a" * 32
        self.raw = {
            "package.json": "{unfinished",
            "observations.csv": "\ufeffa,b\r\n1,2\r\n",
            "settings.json": "{\n invalid on purpose\n",
        }

    def create(self):
        return self.store.create(self.project, "mmtt-sensitivity", "Invented concept", self.raw)

    def save(self, record, **changes):
        return self.store.save(
            record["id"],
            record["revision"],
            self.project,
            changes.get("name", record["name"]),
            changes.get("parent", record["parent"]),
            changes.get("inputs", record["files"]),
        )

    def test_invalid_text_exact_bytes_restart_cas_and_restore(self):
        first = self.create()
        self.assertEqual(first["name"], "Invented concept")
        changed = self.save(first, inputs={**self.raw, "settings.json": "{}\r\n"})
        with self.assertRaisesRegex(ValueError, "another tab"):
            self.save(first, name="Stale overwrite")
        restarted = drafts.Drafts(self.root / "drafts")
        self.assertEqual(restarted.get(first["id"])["files"], changed["files"])
        restored = restarted.restore(first["id"], changed["revision"], self.project, 1)
        self.assertEqual(restored["files"], self.raw)
        self.assertEqual(
            restored["files"]["observations.csv"].encode(), self.raw["observations.csv"].encode()
        )
        self.assertEqual(restored["revision"], 3)
        self.assertIsNone(restored["validation"])
        self.assertEqual(len(restored["history"]), 3)
        self.assertNotIn("files", restarted.summaries()[0])

    def test_scientific_or_parent_edit_clears_validation_and_frozen_edits_derive(self):
        first = self.create()
        stamp = {"valid": True, "application": "b" * 64, "result": {}, "error": None}
        checked = self.store.annotate(first["id"], 1, self.project, stamp)
        self.assertEqual(checked["validation"]["content_sha256"], checked["content_sha256"])
        self.assertEqual(self.save(checked)["revision"], checked["revision"])
        parent_change = self.save(checked, parent="c" * 64)
        self.assertIsNone(parent_change["validation"])
        frozen = self.store.annotate(
            parent_change["id"], parent_change["revision"], self.project, stamp, "d" * 64
        )
        edited = self.save(frozen, inputs={**self.raw, "settings.json": "changed"})
        self.assertEqual(edited["parent"], "d" * 64)
        self.assertIsNone(edited["frozen_plan"])
        self.assertIsNone(edited["validation"])

    def test_interrupted_head_keeps_commit_and_diagnoses_orphan(self):
        first = self.create()
        with patch.object(files, "write", side_effect=OSError("controlled interrupted head")):
            with self.assertRaisesRegex(OSError, "interrupted"):
                self.save(first, inputs={**self.raw, "settings.json": "new uncommitted text"})
        recovered = drafts.Drafts(self.root / "drafts").get(first["id"])
        self.assertEqual(recovered["files"], first["files"])
        self.assertEqual(recovered["revision"], 1)
        self.assertEqual(recovered["uncommitted_versions"], 1)
        self.assertEqual(self.save(recovered, name="Retry safely")["revision"], 2)

    def test_corrupt_blob_and_head_refuse_without_losing_other_concepts(self):
        first, second = self.create(), self.create()
        folder, chain = self.store.chain(first["id"])
        digest = chain[0][1]["files"]["observations.csv"]["sha256"]
        (folder / "blobs" / digest).write_text("changed saved bytes")
        restarted = drafts.Drafts(self.root / "drafts")
        self.assertEqual(len(restarted.issues), 1)
        self.assertEqual(restarted.get(second["id"])["files"], self.raw)
        with self.assertRaisesRegex(ValueError, "bytes changed"):
            self.store.get(first["id"])
        other_head = self.root / "drafts" / second["id"] / "head.json"
        value = json.loads(other_head.read_bytes())
        value["sha256"] = "0" * 64
        other_head.write_text(json.dumps(value))
        with self.assertRaisesRegex(ValueError, "revision changed"):
            self.store.get(second["id"])

    def test_unsupported_intake_and_bad_unicode_do_not_publish(self):
        first = self.create()
        for invalid in (
            {**self.raw, "../private": "no"},
            {**self.raw, "settings.json": "\ud800"},
            {**self.raw, "settings.json": "é" * (128 * 1024)},
        ):
            with self.assertRaises(ValueError):
                self.save(first, inputs=invalid)
            self.assertEqual(self.store.get(first["id"])["revision"], 1)
        with self.assertRaises(ValueError):
            self.store.current(first["id"], 1, "e" * 32)

    def test_gui_project_copy_retains_revision_history_and_clears_validation(self):
        first = self.create()
        changed = self.save(first, name="Changed title")
        self.assertEqual(changed["name"], "Changed title")
        stamp = {"valid": True, "application": "b" * 64, "result": {}, "error": None}
        self.store.annotate(changed["id"], changed["revision"], self.project, stamp, "d" * 64)
        self.store.clone_project(self.project, "f" * 32)
        copied = next(s for s in self.store.summaries() if s["project"] == "f" * 32)
        reopened = self.store.get(copied["id"])
        self.assertEqual(reopened["revision"], 3)
        self.assertEqual(len(reopened["history"]), 3)
        self.assertEqual(reopened["files"], self.raw)
        self.assertEqual(reopened["name"], "Changed title")
        self.assertIsNone(reopened["validation"])
        self.assertEqual(reopened["frozen_plan"], "d" * 64)

    def test_large_diagnostics_are_bounded_before_head_publication(self):
        from experiments.shared_services.workbench import observations

        package = (
            Path(__file__).resolve().parents[1]
            / "experiments/shared_contracts/fixtures/mmtt-package.json"
        )
        csv = (
            "participant_id,visit_id,challenge_id,time_min,glucose_mmol_l,glucose_status,cpeptide_nmol_l,cpeptide_status\n"
            + "x,x,x,0,1,o,1,o\n" * 20000
        )
        result = observations(
            {"package.json": package.read_bytes(), "observations.csv": csv.encode()}
        )
        self.assertGreater(result["error_count"], 10000)
        self.assertTrue(result["errors_truncated"])
        self.assertLess(len(files.encoded(result)), 256 * 1024)
        first = self.create()
        huge = {"valid": False, "result": "x" * (1024 * 1024)}
        with self.assertRaisesRegex(ValueError, "last saved revision"):
            self.store.annotate(first["id"], 1, self.project, huge)
        self.assertEqual(self.store.get(first["id"])["revision"], 1)
        kept = self.store.annotate(first["id"], 1, self.project, {"valid": False, "result": result})
        self.assertEqual(
            drafts.Drafts(self.root / "drafts").get(first["id"])["revision"], kept["revision"]
        )


if __name__ == "__main__":
    unittest.main()
