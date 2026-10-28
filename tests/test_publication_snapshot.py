"""Check that public source preparation cannot copy private Git history."""

import subprocess
import tempfile
import unittest
from pathlib import Path

from scripts.prepare_public_snapshot import git, prepare

PUBLIC_NAME = "Public Maintainer"
PUBLIC_EMAIL = "123+maintainer@users.noreply.github.com"


class PublicationSnapshotTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="opent1d-snapshot-test-")
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.source = self.root / "private source"
        self.source.mkdir()
        self.output = self.root / "public candidate"
        git(self.source, "init", "--initial-branch=main")
        (self.source / "private-only.txt").write_text("PRIVATE_HISTORY_ONLY\n")
        git(self.source, "add", "private-only.txt")
        self.commit("Private development")
        self.old = git(self.source, "rev-parse", "HEAD").decode().strip()
        git(self.source, "rm", "private-only.txt")
        (self.source / "README.md").write_text("# Synthetic public fixture\n")
        (self.source / ".gitignore").write_text(".private-cache/\n")
        git(self.source, "add", "README.md", ".gitignore")
        self.commit("Reviewed source")
        private = self.source / ".private-cache"
        private.mkdir()
        (private / "notes.txt").write_text("IGNORED_PRIVATE_NOTES\n")

    def commit(self, message):
        git(
            self.source,
            "commit",
            "-m",
            message,
            identity=("Private Author", "private-author@example.invalid"),
        )

    def prepare(self, **kwargs):
        return prepare(
            self.source,
            self.output,
            author_name=PUBLIC_NAME,
            author_email=kwargs.get("email", PUBLIC_EMAIL),
        )

    def test_export_has_one_portable_root_and_no_private_history_or_ignored_data(self):
        receipt = self.prepare()
        self.assertEqual(receipt["commit_count"], 1)
        self.assertEqual(git(self.source, "rev-list", "--all", "--count").strip(), b"2")
        self.assertFalse((self.output / "private-only.txt").exists())
        self.assertFalse((self.output / ".private-cache").exists())
        self.assertFalse((self.output / ".git/objects/info/alternates").exists())
        self.assertEqual(git(self.output, "remote"), b"")
        self.assertEqual(
            git(self.output, "for-each-ref", "--format=%(refname)").strip(), b"refs/heads/main"
        )
        self.assertEqual(
            git(self.output, "log", "--format=%ae %ce").decode().strip(),
            PUBLIC_EMAIL + " " + PUBLIC_EMAIL,
        )
        with self.assertRaises(subprocess.CalledProcessError):
            git(self.output, "cat-file", "-e", self.old + "^{commit}")
        bundle = self.root / "source.bundle"
        git(self.output, "bundle", "create", str(bundle), "HEAD", "main")
        clone = self.root / "receiving"
        git(self.root, "clone", str(bundle), str(clone))
        self.assertEqual(git(clone, "rev-list", "--all", "--count").strip(), b"1")
        self.assertEqual(
            (clone / "README.md").read_bytes(), (self.output / "README.md").read_bytes()
        )

    def test_unreviewed_changes_refused_before_output_is_created(self):
        (self.source / "unreviewed.txt").write_text("UNREVIEWED\n")
        with self.assertRaisesRegex(ValueError, "Commit and review"):
            self.prepare()
        self.assertFalse(self.output.exists())

    def test_existing_output_is_preserved(self):
        self.output.mkdir()
        keep = self.output / "existing.txt"
        keep.write_bytes(b"EXISTING_WORK")
        with self.assertRaisesRegex(ValueError, "new directory"):
            self.prepare()
        self.assertEqual(keep.read_bytes(), b"EXISTING_WORK")

    def test_personal_author_email_refused_before_output_is_created(self):
        with self.assertRaisesRegex(ValueError, "noreply"):
            self.prepare(email="private-author@example.invalid")
        self.assertFalse(self.output.exists())


if __name__ == "__main__":
    unittest.main()
