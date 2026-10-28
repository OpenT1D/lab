"""Exercise real Windows directory handles, sharing and reparse checks."""

import ctypes
import hashlib
import importlib.util
import os
import subprocess
import tempfile
import threading
import unittest
from contextlib import contextmanager
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

from experiments import platform_files
from experiments.durable_archives import storage


@unittest.skipUnless(os.name == "nt", "Actual Windows directory handles required")
class WindowsDirectoryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # A native probe can use a reviewed new module beside the unchanged
        # installed runtime, without changing the installed application bytes.
        prepared = os.environ.get("OPENT1D_WINDOWS_DIRECTORY_SOURCE")
        if prepared:
            path = Path(prepared).resolve(strict=True)
            spec = importlib.util.spec_from_file_location("opent1d_directory_probe", path)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
        else:
            from experiments.durable_archives import storage as module

        cls.Directory = module.WindowsDirectory

    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)

    def test_open_query_and_idempotent_close(self):
        directory = self.root / "één map 日本語"
        directory.mkdir()
        pinned = self.Directory(directory)
        self.addCleanup(pinned.close)
        self.assertIsNotNone(pinned.handle)
        self.assertEqual(pinned.initial.st_ino, directory.stat().st_ino)
        pinned.close()
        self.assertIsNone(pinned.handle)
        pinned.close()

    def test_pin_prevents_rename_until_closed(self):
        directory = self.root / "directory"
        directory.mkdir()
        (directory / "preserved.txt").write_bytes(b"preserved")
        destination = self.root / "renamed"
        pinned = self.Directory(directory)
        self.addCleanup(pinned.close)
        with self.assertRaises(PermissionError):
            directory.rename(destination)
        self.assertTrue(directory.is_dir())
        self.assertFalse(destination.exists())
        pinned.close()
        directory.rename(destination)
        self.assertEqual((destination / "preserved.txt").read_bytes(), b"preserved")

    def test_repeated_nonempty_directory_inventory_keeps_file_lengths(self):
        directory = self.root / "nonempty directory 日本語"
        directory.mkdir()
        expected = {}
        for index in range(32):
            path = directory / ("synthetic-" + str(index) + ".txt")
            raw = ("synthetic " + str(index)).encode()
            path.write_bytes(raw)
            expected[path.relative_to(self.root).as_posix()] = {
                "size": len(raw),
                "sha256": hashlib.sha256(raw).hexdigest(),
            }
        before = storage.inventory(self.root, storage.Budget())
        after = storage.inventory(self.root, storage.Budget())
        self.assertEqual(before, after)
        self.assertEqual(before[0]["files"], expected)
        self.assertEqual(before[0]["directories"], [directory.name])

    def test_regular_file_and_junction_are_refused_without_retained_handles(self):
        ordinary = self.root / "ordinary.txt"
        ordinary.write_bytes(b"preserved")
        with self.assertRaises(ValueError):
            self.Directory(ordinary)
        ordinary.rename(self.root / "renamed.txt")
        target = self.root / "target"
        target.mkdir()
        junction = self.root / "junction"
        subprocess.run(
            ["cmd.exe", "/d", "/c", "mklink", "/J", str(junction), str(target)],
            capture_output=True,
            check=True,
            timeout=10,
        )
        try:
            with self.assertRaises(ValueError):
                self.Directory(junction)
        finally:
            junction.rmdir()
        self.assertTrue(target.is_dir())


class WindowsBindingTests(unittest.TestCase):
    """API fakes exercise cache boundaries on every host, not native Windows."""

    def setUp(self):
        platform_files._windows_file_api.cache_clear()
        self.addCleanup(platform_files._windows_file_api.cache_clear)
        self.next_handle = 100
        self.attributes = 0
        self.buffers = []

        def create(*arguments):
            self.next_handle += 1
            return self.next_handle

        def query(handle, kind, information, size):
            self.buffers.append(information._obj)
            information._obj.attributes = self.attributes
            return True

        self.kernel = SimpleNamespace(
            CreateFileW=Mock(side_effect=create),
            CloseHandle=Mock(return_value=True),
            GetFileInformationByHandleEx=Mock(side_effect=query),
        )
        self.loader = Mock(return_value=self.kernel)
        self.convert = Mock(side_effect=lambda handle, flags: handle + 1000)
        self.enterContext(patch.object(ctypes, "WinDLL", self.loader, create=True))
        self.enterContext(patch.object(os, "O_BINARY", 0x8000, create=True))
        self.enterContext(
            patch.dict("sys.modules", {"msvcrt": SimpleNamespace(open_osfhandle=self.convert)})
        )

    @contextmanager
    def directory_inventory(self, root):
        # Real paths/stat/scandir, with this class's fake Windows API handles.
        # Native Windows tests separately exercise actual no-delete pins.
        self.attributes = 0x10

        @contextmanager
        def opened_root(path):
            directory = storage.WindowsDirectory(storage.safe_path(path))
            try:
                yield directory
            finally:
                directory.close()

        def opened_child(name, *, dir_fd):
            return storage.WindowsDirectory(dir_fd.path / name)

        with (
            patch.object(storage, "root_fd", opened_root),
            patch.object(storage, "_open_directory", opened_child),
        ):
            yield

    @staticmethod
    def changed_info(info, **changes):
        return SimpleNamespace(
            **{
                **{name: getattr(info, name) for name in dir(info) if name.startswith("st_")},
                **changes,
            }
        )

    def test_inventory_accepts_only_windows_directory_size_variation(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve()
            (root / "child").mkdir()
            original_entry, original_directory = storage.entry_info, storage.directory_info

            def entry(parent, name):
                return self.changed_info(original_entry(parent, name), st_size=4096)

            def pinned(directory):
                return self.changed_info(original_directory(directory), st_size=0)

            with self.directory_inventory(root), patch.object(storage, "entry_info", entry):
                with patch.object(storage, "directory_info", pinned):
                    first = storage.inventory(root, storage.Budget())
                # The recorded directory signatures also remain comparable across
                # inventory boundaries; no result or metadata is cached.
                second = storage.inventory(root, storage.Budget())
            self.assertEqual(first, second)
            self.assertEqual(first[0]["directories"], ["child"])
            self.assertEqual(first[0]["files"], {})
            info = root.stat()
            changed = self.changed_info(info, st_size=info.st_size + 1)
            self.assertNotEqual(storage.signature(info), storage.signature(changed))
            self.assertNotEqual(
                storage.directory_signature(info, 123),
                storage.directory_signature(changed, 123),
            )  # POSIX directory size remains checked too.
        self.assertEqual(self.kernel.CreateFileW.call_count, self.kernel.CloseHandle.call_count)

    def test_inventory_refuses_directory_identity_timestamp_and_reparse_changes(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve()
            (root / "child").mkdir()
            original = storage.entry_info
            for boundary in (1, 2):
                for field in ("st_dev", "st_ino", "st_mtime_ns", "st_ctime_ns") + (
                    ("reparse",) if boundary == 1 else ()
                ):
                    with self.subTest(boundary=boundary, field=field):
                        observations = 0

                        def changed(parent, name):
                            nonlocal observations
                            info = original(parent, name)
                            observations += 1
                            if observations != boundary:
                                return info
                            if field == "reparse":
                                return self.changed_info(info, st_file_attributes=0x400)
                            return self.changed_info(info, **{field: getattr(info, field) + 1})

                        with (
                            self.directory_inventory(root),
                            patch.object(storage, "entry_info", changed),
                            self.assertRaisesRegex(ValueError, "Directory|Linked/reparse"),
                        ):
                            storage.inventory(root, storage.Budget())
                        self.assertEqual(
                            self.kernel.CreateFileW.call_count,
                            self.kernel.CloseHandle.call_count,
                        )

    def test_binding_reuse_keeps_each_file_handle_and_query_buffer_fresh(self):
        first = platform_files._windows_open(Path("first"), os.O_RDONLY)
        second = platform_files._windows_open(Path("second"), os.O_RDONLY)
        self.assertEqual((first, second), (1101, 1102))
        self.loader.assert_called_once_with("kernel32", use_last_error=True)
        self.assertEqual(self.kernel.CreateFileW.call_count, 2)
        self.assertEqual(self.kernel.GetFileInformationByHandleEx.call_count, 2)
        self.assertIsNot(self.buffers[0], self.buffers[1])
        self.kernel.CloseHandle.assert_not_called()  # Each descriptor now owns its handle.
        self.attributes = 0x400
        with self.assertRaisesRegex(ValueError, "Reparse"):
            platform_files._windows_open(Path("changed"), os.O_RDONLY)
        self.kernel.CloseHandle.assert_called_once_with(103)
        self.assertEqual(self.convert.call_count, 2)

    def test_warmed_bindings_close_failed_file_queries_and_descriptor_conversions(self):
        platform_files._windows_file_api()
        failure = OSError("synthetic native query failure")
        self.kernel.GetFileInformationByHandleEx.side_effect = None
        self.kernel.GetFileInformationByHandleEx.return_value = False
        with patch.object(ctypes, "get_last_error", return_value=5, create=True):
            with patch.object(ctypes, "WinError", return_value=failure, create=True):
                with self.assertRaises(OSError) as caught:
                    platform_files._windows_open(Path("query"), os.O_RDONLY)
        self.assertIs(caught.exception, failure)
        self.kernel.CloseHandle.assert_called_once_with(101)
        self.kernel.GetFileInformationByHandleEx.return_value = True
        self.convert.side_effect = ValueError("synthetic conversion failure")
        with self.assertRaisesRegex(ValueError, "conversion"):
            platform_files._windows_open(Path("conversion"), os.O_RDONLY)
        self.assertEqual(
            [call.args[0] for call in self.kernel.CloseHandle.call_args_list], [101, 102]
        )
        self.loader.assert_called_once()

    def test_shared_directory_bindings_preserve_fresh_attributes_and_handle_ownership(self):
        platform_files._windows_file_api()
        self.attributes = 0x10
        with tempfile.TemporaryDirectory() as directory:
            first = storage.WindowsDirectory(directory)
            second = storage.WindowsDirectory(directory)
            self.assertNotEqual(first.handle, second.handle)
            self.assertIsNot(self.buffers[0], self.buffers[1])
            for call in self.kernel.CreateFileW.call_args_list:
                self.assertEqual(call.args[1:3], (0x81, 3))
            first.close()
            first.close()
            second.close()
            self.attributes = 0x410
            with self.assertRaisesRegex(ValueError, "linked"):
                storage.WindowsDirectory(directory)
        self.assertEqual(
            [call.args[0] for call in self.kernel.CloseHandle.call_args_list], [101, 102, 103]
        )
        self.loader.assert_called_once()


@unittest.skipUnless(os.name == "nt", "Actual Windows thread-local errors required")
class WindowsConcurrentBindingTests(unittest.TestCase):
    def test_cold_callers_have_distinct_live_handles_buffers_and_last_errors(self):
        platform_files._windows_file_api.cache_clear()
        self.addCleanup(platform_files._windows_file_api.cache_clear)
        barriers = [threading.Barrier(4, timeout=30) for _ in range(3)]
        records, errors = [], []
        lock = threading.Lock()
        invalid = ctypes.c_void_p(-1).value
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "existing synthetic file"
            path.write_bytes(b"synthetic")

            def worker(index):
                handle = None
                close = None
                try:
                    barriers[0].wait()
                    _, create, close, query, Attributes = platform_files._windows_file_api()
                    info = Attributes()
                    handle = create(str(path), 0x80000000, 7, None, 3, 0x00200000, None)
                    if handle == invalid or not query(
                        handle, 9, ctypes.byref(info), ctypes.sizeof(info)
                    ):
                        raise AssertionError("Synthetic open/query failed")
                    record = {"handle": handle, "buffer": info}
                    with lock:
                        records.append(record)
                    barriers[1].wait()  # All four handles and buffers remain live here.
                    if index % 2:
                        unexpected = create(str(path), 0x80000000, 7, None, 1, 0, None)
                        if unexpected != invalid:
                            close(unexpected)
                            raise AssertionError("CREATE_NEW accepted an existing file")
                        expected = 80
                    else:
                        if query(None, 9, ctypes.byref(info), ctypes.sizeof(info)):
                            raise AssertionError("Invalid-handle query succeeded")
                        expected = 6
                    barriers[2].wait()  # Other threads set different ctypes last-error values.
                    record["error"] = ctypes.get_last_error()
                    if record["error"] != expected:
                        raise AssertionError("LastError crossed threads")
                except Exception as error:
                    with lock:
                        errors.append(repr(error))
                    for barrier in barriers:
                        barrier.abort()
                finally:
                    if handle is not None and handle != invalid and not close(handle):
                        with lock:
                            errors.append("CloseHandle failed")

            threads = [
                threading.Thread(target=worker, args=(index,), daemon=True) for index in range(4)
            ]
            for thread in threads:
                thread.start()
            for thread in threads:
                thread.join(40)
            self.assertFalse(any(thread.is_alive() for thread in threads))
            self.assertFalse(errors, errors)
            self.assertEqual(len(records), 4)
            self.assertEqual(len({item["handle"] for item in records}), 4)
            self.assertEqual(len({id(item["buffer"]) for item in records}), 4)
            self.assertEqual(sorted(item["error"] for item in records), [6, 6, 80, 80])
            # lru_cache may evaluate more than once during concurrent cold calls.
            self.assertEqual(platform_files._windows_file_api.cache_info().currsize, 1)


if __name__ == "__main__":
    unittest.main()
