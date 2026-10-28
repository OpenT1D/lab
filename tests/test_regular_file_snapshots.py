"""Stable reads keep descriptor timestamps and reject concurrent replacement."""

import errno
import hashlib
import os
import stat
import tempfile
import time
import unittest
import uuid
from contextlib import contextmanager
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from experiments.durable_archives import storage
from experiments.m3.researcher import intake
from experiments.platform_files import open_regular, regular_info


@contextmanager
def after_read(action):
    original = os.fdopen
    changed = False

    class Stream:
        def __init__(self, stream):
            self.stream = stream

        def __getattr__(self, name):
            return getattr(self.stream, name)

        def read(self, *args):
            nonlocal changed
            raw = self.stream.read(*args)
            if not changed:
                changed = True
                action()
            return raw

    @contextmanager
    def opened(*args, **kwargs):
        with original(*args, **kwargs) as stream:
            yield Stream(stream)

    with patch.object(os, "fdopen", opened):
        yield


class RegularFileSnapshotTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name).resolve()
        self.path = self.root / "synthetic input.json"
        self.raw = b'{"synthetic": true}\n'
        self.path.write_bytes(self.raw)

    def replace_live_path(self, replacement):
        # Windows ordinary replace refuses an existing open destination even
        # with delete sharing. Move that name aside, retaining the old open fd,
        # then put a different inode at the original path. Neither step is skipped.
        retired = self.root / ("retired-" + uuid.uuid4().hex)
        self.path.rename(retired)
        replacement.rename(self.path)

    def test_open_uses_one_fresh_snapshot_for_link_policy_and_identity(self):
        original_lstat, original_fstat = Path.lstat, os.fstat
        for change in ("symlink", "reparse"):
            with self.subTest(change=change):
                calls, descriptors = [], []

                def observed_lstat(path, *args, **kwargs):
                    value = original_lstat(path, *args, **kwargs)
                    if path == self.path:
                        calls.append(value)
                        if len(calls) == 2:
                            attributes = {
                                name: getattr(value, name)
                                for name in dir(value)
                                if name.startswith("st_")
                            }
                            if change == "symlink":
                                attributes["st_mode"] = stat.S_IFLNK | 0o600
                            else:
                                attributes["st_file_attributes"] = 0x400
                            # A subsequent pathname observation would be ordinary
                            # again. Identity and link policy may not mix snapshots.
                            return SimpleNamespace(**attributes)
                    return value

                def observed_fstat(descriptor):
                    descriptors.append(descriptor)
                    return original_fstat(descriptor)

                opened = None
                try:
                    with (
                        patch.object(Path, "lstat", observed_lstat),
                        patch.object(os, "fstat", observed_fstat),
                        self.assertRaisesRegex(ValueError, "stable regular file"),
                    ):
                        opened = open_regular(self.path, os.O_RDWR | os.O_TRUNC)
                finally:
                    if opened is not None:
                        os.close(opened)
                self.assertEqual(self.path.read_bytes(), self.raw)
                self.assertTrue(descriptors)
                for descriptor in descriptors:
                    with self.assertRaises(OSError) as closed:
                        original_fstat(descriptor)
                    self.assertEqual(closed.exception.errno, errno.EBADF)

    def test_replacement_around_open_snapshot_is_refused_by_the_bounded_reader(self):
        original_lstat, original_fstat = Path.lstat, os.fstat
        for boundary in ("after handle snapshot", "after pathname snapshot"):
            with self.subTest(boundary=boundary):
                replacement = self.root / "replacement"
                replacement.write_bytes(self.raw)
                before = self.path.stat()
                os.utime(replacement, ns=(before.st_atime_ns, before.st_mtime_ns))
                descriptors, observations = [], []
                changed = False

                def replace():
                    nonlocal changed
                    changed = True
                    self.replace_live_path(replacement)

                def observed_fstat(descriptor):
                    value = original_fstat(descriptor)
                    descriptors.append(descriptor)
                    if not changed and boundary == "after handle snapshot":
                        replace()
                    return value

                def observed_lstat(path, *args, **kwargs):
                    value = original_lstat(path, *args, **kwargs)
                    if path == self.path:
                        observations.append(value)
                        if len(observations) == 2 and boundary == "after pathname snapshot":
                            replace()
                    return value

                # Select Windows' path-based stream/reopen policy on any host;
                # open_regular and both replacement renames still use real files.
                parent = object.__new__(storage.WindowsDirectory)
                parent.path = self.root
                with (
                    patch.object(Path, "lstat", observed_lstat),
                    patch.object(os, "fstat", observed_fstat),
                    self.assertRaisesRegex(ValueError, "stable regular|replaced|changed"),
                ):
                    storage.stream_file(parent, self.path.name, budget=storage.Budget())
                self.assertTrue(changed)
                self.assertEqual(self.path.read_bytes(), self.raw)
                self.assertTrue(descriptors)
                for descriptor in set(descriptors):
                    with self.assertRaises(OSError) as closed:
                        original_fstat(descriptor)
                    self.assertEqual(closed.exception.errno, errno.EBADF)

    def test_stream_keeps_fresh_reopen_without_duplicate_path_snapshots(self):
        original_lstat, original_fstat = Path.lstat, os.fstat
        calls, descriptors = [], []

        def observed_fstat(descriptor):
            descriptors.append(descriptor)
            return original_fstat(descriptor)

        def observed_lstat(path, *args, **kwargs):
            if path == self.path:
                calls.append(path)
            return original_lstat(path, *args, **kwargs)

        parent = object.__new__(storage.WindowsDirectory)
        parent.path = self.root
        for raw in (self.raw, b" " * len(self.raw)):
            self.path.write_bytes(raw)
            calls.clear()
            descriptors.clear()
            with (
                patch.object(Path, "lstat", observed_lstat),
                patch.object(os, "fstat", observed_fstat),
            ):
                record, _ = storage.stream_file(parent, self.path.name, budget=storage.Budget())
            self.assertEqual(record, {"size": len(raw), "sha256": hashlib.sha256(raw).hexdigest()})
            # Both the initial open and final fresh reopen have pre/post snapshots.
            self.assertEqual(len(calls), 4)
            # Checked initial open, post-read check, checked final fresh reopen.
            self.assertEqual(len(descriptors), 3)

    def test_reopen_snapshot_observes_mutation_during_pathname_validation(self):
        original_lstat, original_fstat = Path.lstat, os.fstat
        for change in ("size", "same size and mtime"):
            with self.subTest(change=change):
                before = regular_info(self.path)
                calls, descriptors = [], []
                raw = self.raw + b"changed" if change == "size" else b" " * before.st_size

                def observed_lstat(path, *args, **kwargs):
                    value = original_lstat(path, *args, **kwargs)
                    if path == self.path:
                        calls.append(value)
                        if len(calls) == 2:
                            time.sleep(0.02)
                            self.path.write_bytes(raw)
                            os.utime(self.path, ns=(before.st_atime_ns, before.st_mtime_ns))
                    return value

                def observed_fstat(descriptor):
                    descriptors.append(descriptor)
                    return original_fstat(descriptor)

                with (
                    patch.object(Path, "lstat", observed_lstat),
                    patch.object(os, "fstat", observed_fstat),
                ):
                    after = regular_info(self.path)
                self.assertEqual(after.st_size, len(raw))
                self.assertEqual(after.st_mtime_ns, before.st_mtime_ns)
                self.assertNotEqual(after.st_ctime_ns, before.st_ctime_ns)
                self.assertEqual(len(descriptors), 1)
                with self.assertRaises(OSError) as closed:
                    original_fstat(descriptors[0])
                self.assertEqual(closed.exception.errno, errno.EBADF)

    def test_stream_refuses_mutation_around_shared_handle_snapshot(self):
        original_lstat, original_fstat = Path.lstat, os.fstat
        for boundary in ("after initial handle snapshot", "before final handle snapshot"):
            with self.subTest(boundary=boundary):
                self.path.write_bytes(self.raw)
                before = regular_info(self.path)
                paths, descriptors = [], []
                changed = False

                def mutate():
                    nonlocal changed
                    changed = True
                    time.sleep(0.02)
                    self.path.write_bytes(b" " * before.st_size)
                    os.utime(self.path, ns=(before.st_atime_ns, before.st_mtime_ns))

                def observed_fstat(descriptor):
                    value = original_fstat(descriptor)
                    descriptors.append(descriptor)
                    if not changed and boundary == "after initial handle snapshot":
                        mutate()
                    return value

                def observed_lstat(path, *args, **kwargs):
                    value = original_lstat(path, *args, **kwargs)
                    if path == self.path:
                        paths.append(value)
                        if len(paths) == 4 and boundary == "before final handle snapshot":
                            mutate()
                    return value

                parent = object.__new__(storage.WindowsDirectory)
                parent.path = self.root
                with (
                    patch.object(Path, "lstat", observed_lstat),
                    patch.object(os, "fstat", observed_fstat),
                    self.assertRaisesRegex(ValueError, "changed|replaced"),
                ):
                    storage.stream_file(parent, self.path.name, budget=storage.Budget())
                self.assertTrue(changed)
                for descriptor in set(descriptors):
                    with self.assertRaises(OSError) as closed:
                        original_fstat(descriptor)
                    self.assertEqual(closed.exception.errno, errno.EBADF)

    def test_created_then_rewritten_file_reads_with_descriptor_identity(self):
        time.sleep(0.02)
        self.path.write_bytes(self.raw + b" ")
        self.assertEqual(intake.read_regular(self.path, 1024, "input"), self.raw + b" ")
        with storage.root_fd(self.root) as parent:
            record, _ = storage.stream_file(parent, self.path.name, budget=storage.Budget())
        self.assertEqual(record["size"], len(self.raw) + 1)
        self.assertEqual(
            storage.read_file(self.root, self.path.name, storage.Budget()), self.raw + b" "
        )

    def test_path_creation_clock_is_not_compared_with_descriptor_change_clock(self):
        original = Path.stat

        def path_clock(path, *args, **kwargs):
            value = original(path, *args, **kwargs)
            attributes = {
                name: getattr(value, name) for name in dir(value) if name.startswith("st_")
            }
            attributes["st_ctime_ns"] -= 1_000_000_000
            return SimpleNamespace(**attributes)

        # Exercise the Windows path-vs-handle policy on every host. No Win32 API
        # is mocked or claimed to run: open_regular still uses the actual host.
        parent = object.__new__(storage.WindowsDirectory)
        parent.path = self.root
        with patch.object(Path, "stat", path_clock):
            self.assertEqual(intake.read_regular(self.path, 1024, "input"), self.raw)
            record, _ = storage.stream_file(parent, self.path.name, budget=storage.Budget())
            self.assertEqual(record["size"], len(self.raw))

    def test_content_change_with_restored_size_and_mtime_is_refused(self):
        before = self.path.stat()

        def mutate():
            time.sleep(0.02)
            self.path.write_bytes(b" " * len(self.raw))
            os.utime(self.path, ns=(before.st_atime_ns, before.st_mtime_ns))

        with after_read(mutate), self.assertRaisesRegex(ValueError, "changed during read"):
            intake.read_regular(self.path, 1024, "input")

    def test_replacement_with_identical_bytes_and_mtime_is_refused(self):
        before = self.path.stat()
        replacement = self.root / "replacement"
        replacement.write_bytes(self.raw)
        os.utime(replacement, ns=(before.st_atime_ns, before.st_mtime_ns))
        with after_read(lambda: self.replace_live_path(replacement)):
            with self.assertRaisesRegex(ValueError, "changed during read"):
                intake.read_regular(self.path, 1024, "input")

    def test_change_after_first_descriptor_snapshot_is_refused(self):
        original = intake.regular_info

        def mutate_then_reopen(path):
            self.path.write_bytes(self.raw + b"changed")
            return original(path)

        with patch.object(intake, "regular_info", mutate_then_reopen):
            with self.assertRaisesRegex(ValueError, "changed during read"):
                intake.read_regular(self.path, 1024, "input")

    def test_durable_stream_and_metadata_refuse_replacement(self):
        for operation in ("stream", "metadata"):
            with self.subTest(operation=operation):
                replacement = self.root / "replacement"
                replacement.write_bytes(self.raw)
                with after_read(lambda: self.replace_live_path(replacement)):
                    with self.assertRaisesRegex(ValueError, "replaced|changed"):
                        if operation == "stream":
                            with storage.root_fd(self.root) as parent:
                                storage.stream_file(parent, self.path.name, budget=storage.Budget())
                        else:
                            storage.read_file(self.root, self.path.name, storage.Budget())

    def test_durable_hardlinks_and_intake_byte_limits_remain_refused(self):
        with self.assertRaisesRegex(ValueError, "byte limit"):
            intake.read_regular(self.path, len(self.raw) - 1, "input")
        linked = self.root / "hardlink"
        os.link(self.path, linked)
        with self.assertRaisesRegex(ValueError, "Hardlinked"):
            with storage.root_fd(self.root) as parent:
                storage.stream_file(parent, self.path.name, budget=storage.Budget())
        with self.assertRaisesRegex(ValueError, "bounded regular"):
            storage.read_file(self.root, self.path.name, storage.Budget())

    def test_snapshot_closes_descriptor_and_refuses_nonregular_path(self):
        with patch("experiments.platform_files.os.close", wraps=os.close) as close:
            self.assertEqual(regular_info(self.path).st_size, len(self.raw))
            close.assert_called_once()
            descriptor = close.call_args.args[0]
            with self.assertRaises(OSError) as caught:
                os.fstat(descriptor)
            self.assertEqual(caught.exception.errno, errno.EBADF)
        with self.assertRaises((OSError, ValueError)):
            regular_info(self.root)
        moved = self.root / "moved"
        self.path.rename(moved)
        moved.unlink()


if __name__ == "__main__":
    unittest.main()
