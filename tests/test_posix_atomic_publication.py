"""POSIX publication owns fresh pending files and preserves unrelated entries."""

import errno
import os
import tempfile
import unittest
from contextlib import contextmanager
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from experiments import platform_files


@contextmanager
def created_descriptors(action=None):
    """Observe real exclusive opens, optionally changing the created entry."""
    original = os.open
    descriptors = []

    def opened(path, flags, *args, **kwargs):
        descriptor = original(path, flags, *args, **kwargs)
        if flags & os.O_CREAT and flags & os.O_EXCL:
            descriptors.append(descriptor)
            if action is not None:
                action(Path(path))
        return descriptor

    with patch.object(platform_files.os, "open", side_effect=opened):
        yield descriptors


@unittest.skipUnless(os.name == "posix", "POSIX atomic publication contract")
class PosixAtomicPublicationTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.path = self.root / "journal.json"
        self.old = b"previous complete record\r\n\x00\xff"
        self.path.write_bytes(self.old)
        self.outside = self.root / "independent.txt"
        self.original = b"independent bytes\r\n\x00\xfe"
        self.outside.write_bytes(self.original)

    def pending(self, explicit):
        return (
            self.path.with_suffix(".tmp")
            if explicit
            else self.path.with_name(self.path.name + ".tmp")
        )

    def arguments(self, explicit):
        return {"temporary": self.pending(True)} if explicit else {}

    def assert_descriptors_closed(self, descriptors):
        self.assertTrue(descriptors, "Writer did not exclusively create a pending file")
        for descriptor in descriptors:
            with self.assertRaises(OSError) as closed:
                os.fstat(descriptor)
            self.assertEqual(closed.exception.errno, errno.EBADF)

    def test_bytes_ignore_existing_temporary_symlinks_without_following_or_publishing_them(self):
        for explicit in (False, True):
            with self.subTest(explicit=explicit):
                self.path.unlink(missing_ok=True)
                self.path.write_bytes(self.old)
                self.outside.write_bytes(self.original)
                pending = self.pending(explicit)
                pending.symlink_to(self.outside)
                with self.path.open("rb") as reader:
                    platform_files.atomic_write_bytes(
                        self.path, b"complete replacement\n", **self.arguments(explicit)
                    )
                    self.assertEqual(reader.read(), self.old)
                self.assertEqual(self.outside.read_bytes(), self.original)
                self.assertTrue(pending.is_symlink())
                self.assertEqual(pending.readlink(), self.outside)
                self.assertFalse(self.path.is_symlink())
                self.assertEqual(self.path.read_bytes(), b"complete replacement\n")
                pending.unlink()

    def test_text_refuses_existing_temporary_symlinks_without_following_or_publishing_them(self):
        for explicit in (False, True):
            with self.subTest(explicit=explicit):
                self.path.unlink(missing_ok=True)
                self.path.write_bytes(self.old)
                self.outside.write_bytes(self.original)
                pending = self.pending(explicit)
                pending.symlink_to(self.outside)
                with self.assertRaises((OSError, ValueError)):
                    platform_files.atomic_write_text(
                        self.path, "complete replacement\n", **self.arguments(explicit)
                    )
                self.assertEqual(self.outside.read_bytes(), self.original)
                self.assertEqual(self.path.read_bytes(), self.old)
                self.assertFalse(self.path.is_symlink())
                self.assertTrue(pending.is_symlink())
                pending.unlink()

    def test_regular_publication_keeps_exact_bytes_text_defaults_and_existing_readers(self):
        expected = self.root / "expected.txt"
        text = "first β\r\nsecond\nthird\r"
        expected.write_text(text)
        for text_mode in (False, True):
            writer = (
                platform_files.atomic_write_text if text_mode else platform_files.atomic_write_bytes
            )
            content = text if text_mode else b"new\r\nbytes\x00\xfe"
            raw = expected.read_bytes() if text_mode else content
            for explicit in (False, True):
                with self.subTest(text=text_mode, explicit=explicit):
                    self.path.write_bytes(self.old)
                    with self.path.open("rb") as reader, created_descriptors() as descriptors:
                        writer(self.path, content, **self.arguments(explicit))
                        self.assertEqual(reader.read(), self.old)
                    self.assertEqual(self.path.read_bytes(), raw)
                    self.assertFalse(self.path.is_symlink())
                    self.assertFalse(self.pending(explicit).exists())
                    self.assertEqual(list(self.root.glob("*.tmp*")), [])
                    self.assert_descriptors_closed(descriptors)

    def test_bytes_preserve_stale_regular_hardlinked_directory_and_fifo_templates(self):
        for kind in ("regular", "hardlink", "directory", "fifo", "dangling"):
            with self.subTest(kind=kind):
                pending = self.pending(True)
                if kind == "regular":
                    pending.write_bytes(self.original)
                elif kind == "hardlink":
                    os.link(self.outside, pending)
                elif kind == "directory":
                    pending.mkdir()
                    (pending / "sentinel").write_bytes(self.original)
                elif kind == "fifo":
                    os.mkfifo(pending)
                else:
                    pending.symlink_to(self.root / "missing")
                before = pending.lstat()
                platform_files.atomic_write_bytes(self.path, b"updated\n", temporary=pending)
                self.assertEqual(self.path.read_bytes(), b"updated\n")
                self.assertEqual(pending.lstat(), before)
                self.assertEqual(self.outside.read_bytes(), self.original)
                if kind in {"regular", "hardlink"}:
                    self.assertEqual(pending.read_bytes(), self.original)
                if kind == "directory":
                    self.assertEqual((pending / "sentinel").read_bytes(), self.original)
                    (pending / "sentinel").unlink()
                    pending.rmdir()
                else:
                    pending.unlink()

    def test_text_refuses_all_existing_fixed_pending_entries(self):
        for kind in ("regular", "hardlink", "directory", "fifo", "dangling"):
            with self.subTest(kind=kind):
                pending = self.pending(False)
                if kind == "regular":
                    pending.write_bytes(self.original)
                elif kind == "hardlink":
                    os.link(self.outside, pending)
                elif kind == "directory":
                    pending.mkdir()
                elif kind == "fifo":
                    os.mkfifo(pending)
                else:
                    pending.symlink_to(self.root / "missing")
                before = pending.lstat()
                with self.assertRaises((OSError, ValueError)):
                    platform_files.atomic_write_text(self.path, "updated\n")
                self.assertEqual(self.path.read_bytes(), self.old)
                self.assertEqual(pending.lstat(), before)
                self.assertEqual(self.outside.read_bytes(), self.original)
                if kind in {"regular", "hardlink"}:
                    self.assertEqual(pending.read_bytes(), self.original)
                pending.rmdir() if kind == "directory" else pending.unlink()

    def test_publication_failure_preserves_target_and_closes_and_removes_owned_pending(self):
        for text_mode in (False, True):
            writer = (
                platform_files.atomic_write_text if text_mode else platform_files.atomic_write_bytes
            )
            content = "replacement\n" if text_mode else b"replacement\n"
            for existing in (False, True):
                with self.subTest(text=text_mode, existing=existing):
                    if existing:
                        self.path.write_bytes(self.old)
                    else:
                        self.path.unlink(missing_ok=True)
                    with created_descriptors() as descriptors:
                        with (
                            patch.object(
                                Path, "replace", side_effect=OSError(errno.EIO, "fixture")
                            ),
                            self.assertRaises(OSError) as failure,
                        ):
                            writer(self.path, content)
                    self.assertEqual(failure.exception.errno, errno.EIO)
                    self.assertEqual(
                        self.path.read_bytes() if existing else None, self.old if existing else None
                    )
                    self.assertEqual(self.path.exists(), existing)
                    self.assertEqual(list(self.root.glob("*.tmp*")), [])
                    self.assert_descriptors_closed(descriptors)

    def test_partial_write_failure_or_interruption_preserves_target_and_cleans_owned_pending(self):
        original = os.fdopen
        for text_mode in (False, True):
            writer = (
                platform_files.atomic_write_text if text_mode else platform_files.atomic_write_bytes
            )
            content = "replacement\n" if text_mode else b"replacement\n"
            for failure in (OSError(errno.EIO, "fixture"), KeyboardInterrupt("fixture")):
                with self.subTest(text=text_mode, failure=type(failure).__name__):

                    class PartialWriter:
                        def __init__(self, *args, **kwargs):
                            self.stream = original(*args, **kwargs)

                        def __enter__(self):
                            return self

                        def __exit__(self, *args):
                            self.stream.close()

                        def write(self, value):
                            self.stream.write(value[:3])
                            self.stream.flush()
                            raise failure

                    with created_descriptors() as descriptors:
                        with (
                            patch.object(platform_files.os, "fdopen", side_effect=PartialWriter),
                            self.assertRaises(type(failure)),
                        ):
                            writer(self.path, content)
                    self.assertEqual(self.path.read_bytes(), self.old)
                    self.assertEqual(list(self.root.glob("*.tmp*")), [])
                    self.assert_descriptors_closed(descriptors)

    def test_open_interference_never_writes_or_removes_a_substituted_pending_entry(self):
        for text_mode in (False, True):
            writer = (
                platform_files.atomic_write_text if text_mode else platform_files.atomic_write_bytes
            )
            content = "replacement\n" if text_mode else b"replacement\n"
            for kind in ("regular", "symlink", "hardlink"):
                with self.subTest(text=text_mode, kind=kind):
                    retained = self.root / "retained-created-file"
                    pending_paths = []

                    def substitute(pending):
                        pending_paths.append(pending)
                        if kind == "hardlink":
                            os.link(pending, retained)
                        else:
                            pending.rename(retained)
                            if kind == "symlink":
                                pending.symlink_to(self.outside)
                            else:
                                pending.write_bytes(b"foreign pending")

                    with created_descriptors(substitute) as descriptors:
                        with self.assertRaises((OSError, ValueError)):
                            writer(self.path, content)
                    self.assertEqual(self.path.read_bytes(), self.old)
                    self.assertEqual(self.outside.read_bytes(), self.original)
                    self.assertEqual(retained.read_bytes(), b"")
                    self.assertEqual(len(pending_paths), 1)
                    pending = pending_paths[0]
                    self.assertEqual(
                        pending.read_bytes(),
                        self.original
                        if kind == "symlink"
                        else b""
                        if kind == "hardlink"
                        else b"foreign pending",
                    )
                    self.assert_descriptors_closed(descriptors)
                    pending.unlink()
                    retained.unlink()

    def test_after_write_interference_does_not_publish_or_remove_foreign_pending(self):
        original = os.fdopen
        for text_mode in (False, True):
            writer = (
                platform_files.atomic_write_text if text_mode else platform_files.atomic_write_bytes
            )
            content = "replacement\n" if text_mode else b"replacement\n"
            for kind in ("regular", "symlink", "hardlink"):
                with self.subTest(text=text_mode, kind=kind):
                    retained = self.root / "retained-complete-file"
                    pending_paths = []

                    @contextmanager
                    def substitute_after_write(*args, **kwargs):
                        with original(*args, **kwargs) as stream:
                            yield stream
                        pending = pending_paths[0]
                        if kind == "hardlink":
                            os.link(pending, retained)
                        else:
                            pending.rename(retained)
                            if kind == "symlink":
                                pending.symlink_to(self.outside)
                            else:
                                pending.write_bytes(b"foreign pending")

                    with created_descriptors(pending_paths.append) as descriptors:
                        with (
                            patch.object(
                                platform_files.os, "fdopen", side_effect=substitute_after_write
                            ),
                            self.assertRaises((OSError, ValueError)),
                        ):
                            writer(self.path, content)
                    self.assertEqual(self.path.read_bytes(), self.old)
                    self.assertEqual(self.outside.read_bytes(), self.original)
                    self.assertEqual(retained.read_bytes(), b"replacement\n")
                    pending = pending_paths[0]
                    expected = {
                        "regular": b"foreign pending",
                        "symlink": self.original,
                        "hardlink": b"replacement\n",
                    }
                    self.assertEqual(pending.read_bytes(), expected[kind])
                    self.assert_descriptors_closed(descriptors)
                    pending.unlink()
                    retained.unlink()

    def test_generated_byte_pending_collision_never_follows_or_removes_existing_entry(self):
        pending = self.pending(True)
        collision = pending.with_name(pending.name + ".collision.tmp")
        collision.symlink_to(self.outside)
        with (
            patch("uuid.uuid4", return_value=SimpleNamespace(hex="collision")),
            self.assertRaises(FileExistsError),
        ):
            platform_files.atomic_write_bytes(self.path, b"replacement\n", temporary=pending)
        self.assertEqual(self.path.read_bytes(), self.old)
        self.assertEqual(self.outside.read_bytes(), self.original)
        self.assertTrue(collision.is_symlink())
        self.assertFalse(pending.exists())

    def test_same_path_and_nonsibling_temporary_are_rejected_before_writing(self):
        other = self.root / "other"
        other.mkdir()
        for writer, content in (
            (platform_files.atomic_write_bytes, b"replacement\n"),
            (platform_files.atomic_write_text, "replacement\n"),
        ):
            for pending in (self.path, other / "pending"):
                with self.subTest(writer=writer.__name__, pending=pending):
                    with self.assertRaises(ValueError):
                        writer(self.path, content, temporary=pending)
                    self.assertEqual(self.path.read_bytes(), self.old)
                    self.assertEqual(list(other.iterdir()), [])


if __name__ == "__main__":
    unittest.main()
