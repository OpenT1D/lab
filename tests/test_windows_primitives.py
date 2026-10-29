"""Native file/lock checks, real pipe-worker cancellation and Windows Job gates."""

import errno
import json
import os
import shutil
import signal
import subprocess
import sys
import tempfile
import time
import unittest
from contextlib import contextmanager
from pathlib import Path
from unittest.mock import Mock, patch

from experiments import platform_files
from experiments.catalogue.storage import ROOT, dump
from experiments.desktop.installation_gate import InstallationGate
from experiments.gui import windows_worker
from experiments.gui.locking import WorkspaceLock
from experiments.gui.windows_process import WindowsOwnership, WindowsProcess
from experiments.gui.windows_worker import CANCEL, START
from experiments.m0.simglucose import recording
from experiments.observation_analysis.fixtures import export_example
from experiments.observation_analysis.plan import freeze
from experiments.observation_analysis.run import reconstruct
from experiments.platform_files import extended_windows_path, is_link, native_absolute, open_regular


@contextmanager
def publication_descriptors():
    """Observe real Windows file-handle transfers without replacing native I/O."""
    descriptors = []
    if os.name != "nt":
        yield descriptors
        return
    import msvcrt

    convert = msvcrt.open_osfhandle

    def observe(*args, **kwargs):
        descriptor = convert(*args, **kwargs)
        descriptors.append(descriptor)
        return descriptor

    with patch.object(msvcrt, "open_osfhandle", side_effect=observe):
        yield descriptors


class PlatformFileTests(unittest.TestCase):
    def test_atomic_json_publication_preserves_held_reader_on_long_unicode_path(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = native_absolute(Path(temporary).resolve())
            try:
                folder = root / ("long-" * 22) / ("archive-" * 15)
                folder.mkdir(parents=True)
                path = folder / "state-\U0001f52c-\u03b2.json"
                self.assertGreater(len(str(path)), 260)
                if os.name == "nt":
                    self.assertTrue(str(path).startswith("\\\\?\\"))
                recording.write_json(path, {"status": "initial"})
                recording.write_json(path, {"status": "started"})
                old = path.read_bytes()
                with os.fdopen(open_regular(path), "rb") as reader:
                    self.assertEqual(reader.read(), old)
                    with publication_descriptors() as descriptors:
                        recording.write_json(path, {"status": "finished"})
                    self.assertEqual(json.loads(path.read_bytes()), {"status": "finished"})
                    reader.seek(0)
                    self.assertEqual(reader.read(), old)
                    if os.name == "nt":
                        self.assertTrue(descriptors, "Writer did not own a fresh native handle")
                    for descriptor in descriptors:
                        with self.assertRaises(OSError) as closed:
                            os.fstat(descriptor)
                        self.assertEqual(closed.exception.errno, errno.EBADF)
                self.assertFalse(path.with_name(path.name + ".tmp").exists())
                self.assertEqual(list(folder.iterdir()), [path])
            finally:
                shutil.rmtree(root)

    def test_atomic_text_keeps_platform_text_bytes_and_rejects_invalid_json(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            expected = root / "expected.txt"
            expected.write_text("first\nsecond\n")
            path = root / "progress.txt"
            recording.atomic_text(path, "first\nsecond\n")
            self.assertEqual(path.read_bytes(), expected.read_bytes())
            before = path.read_bytes()
            with self.assertRaises(ValueError):
                recording.write_json(path, {"invalid": float("nan")})
            self.assertEqual(path.read_bytes(), before)
            self.assertFalse(path.with_name(path.name + ".tmp").exists())

    def test_atomic_bytes_with_explicit_sibling_preserve_exact_payload(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            path = root / "journal.json"
            pending = path.with_suffix(".tmp")
            old = b"old\r\nbytes\x00\xff"
            new = b"new\nbytes\x00\xfe"
            platform_files.atomic_write_bytes(path, old, temporary=pending)
            with os.fdopen(open_regular(path), "rb") as reader:
                platform_files.atomic_write_bytes(path, new, temporary=pending)
                self.assertEqual(reader.read(), old)
                self.assertEqual(path.read_bytes(), new)
            self.assertFalse(pending.exists())
            self.assertFalse(path.with_name(path.name + ".tmp").exists())
            self.assertEqual(list(root.iterdir()), [path])

    @unittest.skipUnless(os.name == "nt", "Windows atomic publication ownership contract")
    def test_windows_atomic_publication_refuses_linked_targets_and_preserves_stale_pending(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve()
            outside = root / "outside.txt"
            outside.write_bytes(b"preserve independent bytes")
            original = outside.read_bytes()
            target = root / "hardlinked-target.json"
            os.link(outside, target)
            with self.assertRaises((OSError, ValueError)):
                recording.write_json(target, {"new": 1})
            self.assertEqual(outside.read_bytes(), original)
            self.assertEqual(target.read_bytes(), original)
            self.assertFalse(target.with_name(target.name + ".tmp").exists())
            for kind in ("ordinary", "hardlinked"):
                with self.subTest(pending=kind):
                    path = root / (kind + ".json")
                    recording.write_json(path, {"old": 1})
                    before = path.read_bytes()
                    pending = path.with_name(path.name + ".tmp")
                    if kind == "hardlinked":
                        os.link(outside, pending)
                    else:
                        pending.write_bytes(original)
                    # Scientific archive schemas retain their exact .tmp names.
                    with self.assertRaises((OSError, ValueError)):
                        recording.write_json(path, {"new": 2})
                    self.assertEqual(path.read_bytes(), before)
                    # GUI journals can recover using a new uniquely owned sibling.
                    platform_files.atomic_write_bytes(path, b'{"new": 2}\n', temporary=pending)
                    self.assertNotEqual(path.read_bytes(), before)
                    self.assertEqual(json.loads(path.read_bytes()), {"new": 2})
                    self.assertEqual(pending.read_bytes(), original)
                    self.assertEqual(outside.read_bytes(), original)
            # Junctions require neither Developer Mode nor symbolic-link privilege.
            # A directory/reparse target is refused. A stale pending junction
            # is left intact while the writer uses a new owned sibling.
            directory = root / "independent-directory"
            directory.mkdir()
            sentinel = directory / "sentinel.txt"
            sentinel.write_bytes(original)
            for suffix in ("", ".tmp"):
                with self.subTest(junction=suffix):
                    path = root / ("junction" + ("-pending" if suffix else "") + ".json")
                    link = path.with_name(path.name + suffix)
                    command = Path(os.environ["SystemRoot"]) / "System32/cmd.exe"
                    created = subprocess.run(
                        [str(command), "/d", "/c", "mklink", "/J", str(link), str(directory)],
                        capture_output=True,
                        timeout=30,
                    )
                    self.assertEqual(created.returncode, 0, created.stderr)
                    try:
                        self.assertTrue(is_link(link))
                        if suffix:
                            with self.assertRaises((OSError, ValueError)):
                                recording.write_json(path, {"new": 3})
                            platform_files.atomic_write_bytes(path, b'{"new": 3}\n', temporary=link)
                            self.assertEqual(json.loads(path.read_bytes()), {"new": 3})
                        else:
                            with self.assertRaises((OSError, ValueError)):
                                recording.write_json(path, {"new": 3})
                        self.assertTrue(is_link(link))
                        self.assertEqual(sentinel.read_bytes(), original)
                        self.assertEqual(
                            sorted(p.name for p in directory.iterdir()), ["sentinel.txt"]
                        )
                    finally:
                        os.rmdir(link)

    @unittest.skipUnless(os.name == "nt", "Windows atomic publication ownership contract")
    def test_windows_atomic_publication_failure_preserves_bytes_and_closes_handles(self):
        import ctypes

        with tempfile.TemporaryDirectory() as temporary:
            root = native_absolute(Path(temporary).resolve())
            for existing in (False, True):
                with self.subTest(existing=existing):
                    path = root / ("existing.json" if existing else "new.json")
                    if existing:
                        recording.write_json(path, {"old": 1})
                    before = path.read_bytes() if existing else None
                    with publication_descriptors() as descriptors:
                        with (
                            patch.object(
                                platform_files,
                                "replace_windows_handle",
                                side_effect=ctypes.WinError(5),
                            ) as publish,
                            self.assertRaises(OSError) as failure,
                        ):
                            recording.write_json(path, {"new": 2})
                    self.assertEqual(failure.exception.winerror, 5)
                    publish.assert_called_once()
                    self.assertEqual(path.read_bytes() if path.exists() else None, before)
                    self.assertFalse(path.with_name(path.name + ".tmp").exists())
                    self.assertEqual(list(root.glob("*.tmp")), [])
                    self.assertTrue(descriptors, "Failed writer did not own its temporary handle")
                    for descriptor in descriptors:
                        with self.assertRaises(OSError) as closed:
                            os.fstat(descriptor)
                        self.assertEqual(closed.exception.errno, errno.EBADF)
            # A new temporary pathname is not authority to follow a replacement
            # or to delete it after the original inode acquires another link.
            real_open = platform_files._windows_open
            for interference in ("replacement", "hardlink"):
                with self.subTest(interference=interference):
                    path = root / (interference + ".json")
                    recording.write_json(path, {"old": 3})
                    before = path.read_bytes()
                    pending_paths = []

                    def change_pending(name, flags, **kwargs):
                        descriptor = real_open(name, flags, **kwargs)
                        try:
                            if kwargs.get("delete_access"):
                                pending = Path(name)
                                pending_paths.append(pending)
                                if interference == "replacement":
                                    pending.rename(root / "retained-replaced-pending")
                                    pending.write_bytes(b"foreign pending bytes")
                                else:
                                    os.link(pending, root / "retained-pending-link")
                        except BaseException:
                            os.close(descriptor)
                            raise
                        return descriptor

                    with publication_descriptors() as descriptors:
                        with (
                            patch.object(
                                platform_files, "_windows_open", side_effect=change_pending
                            ),
                            self.assertRaises((OSError, ValueError)),
                        ):
                            recording.write_json(path, {"new": 4})
                    self.assertEqual(path.read_bytes(), before)
                    self.assertEqual(len(pending_paths), 1)
                    expected = b"foreign pending bytes" if interference == "replacement" else b""
                    self.assertEqual(pending_paths[0].read_bytes(), expected)
                    retained = (
                        "retained-replaced-pending"
                        if interference == "replacement"
                        else "retained-pending-link"
                    )
                    self.assertEqual((root / retained).read_bytes(), b"")
                    self.assertTrue(descriptors)
                    for descriptor in descriptors:
                        with self.assertRaises(OSError) as closed:
                            os.fstat(descriptor)
                        self.assertEqual(closed.exception.errno, errno.EBADF)

    def test_windows_namespace_normalizes_before_disabling_win32_parsing(self):
        for original, expected in (
            (r"C:\Users\Researcher\workspace\..\archives", r"\\?\C:\Users\Researcher\archives"),
            (r"\\?\C:\data\.\workspace\..\archives", r"\\?\C:\data\archives"),
            (r"\\server\share\work\..\archive", r"\\?\UNC\server\share\archive"),
            (r"\\?\UNC\server\share\work\..\archive", r"\\?\UNC\server\share\archive"),
        ):
            with self.subTest(original=original):
                self.assertEqual(extended_windows_path(original), expected)
                self.assertEqual(extended_windows_path(expected), expected)
        for original in (
            "relative",
            "C:relative",
            r"\rooted",
            r"\\.\C:\device",
            r"\\?\GLOBALROOT\Device\disk",
        ):
            with self.subTest(original=original), self.assertRaises(ValueError):
                extended_windows_path(original)

    @unittest.skipUnless(os.name == "nt", "Actual Windows long-path filesystem required")
    def test_desktop_workspace_beyond_max_path_uses_canonical_owned_paths(self):
        from experiments.desktop.__main__ import directory
        from experiments.gui.service import Service

        with tempfile.TemporaryDirectory() as temporary:
            root = native_absolute(temporary)
            try:
                # Deliberately exceed MAX_PATH, independent of the host's policy.
                workspace = directory(root / ("nested-" * 15) / ("analysis-" * 15) / "workspace")
                self.assertGreater(len(str(workspace)), 260)
                self.assertTrue(str(workspace).startswith("\\\\?\\"))
                service = Service(workspace, profile="desktop", source_root=ROOT)
                try:
                    configured = service.defaults()["sources"][0]["model"]
                    path = service.safe_path(configured)
                    self.assertEqual(service.safe_path(str(path)[4:]), path)
                    descriptor = open_regular(path)
                    try:
                        self.assertEqual(os.read(descriptor, 1024), path.read_bytes()[:1024])
                    finally:
                        os.close(descriptor)
                    with self.assertRaisesRegex(ValueError, "separate"):
                        directory(native_absolute(ROOT))
                finally:
                    service.close()
            finally:
                # Cleanup also keeps the explicit long-path namespace.
                shutil.rmtree(root)

    def test_regular_bytes_noninheritance_and_no_link_truncation(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            path = root / "observations.txt"
            path.write_bytes(b"preserve")
            descriptor = open_regular(path)
            try:
                self.assertFalse(os.get_inheritable(descriptor))
                self.assertEqual(os.read(descriptor, 100), b"preserve")
            finally:
                os.close(descriptor)
            link = root / "linked.txt"
            try:
                link.symlink_to(path)
            except OSError:
                self.skipTest("Creating Windows symlinks requires Developer Mode or permission")
            self.assertTrue(is_link(link))
            with self.assertRaises(OSError):
                open_regular(link, os.O_RDWR | os.O_TRUNC)
            self.assertEqual(path.read_bytes(), b"preserve")

    def test_lock_is_exclusive_and_reusable_without_replacing_file(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "manager.lock"
            lock = WorkspaceLock(path)
            identity = path.stat().st_ino
            try:
                with self.assertRaisesRegex(ValueError, "already manages"):
                    WorkspaceLock(path)
            finally:
                lock.close()
            acquired = WorkspaceLock(path)
            acquired.close()
            self.assertEqual(path.stat().st_ino, identity)


class InstallationGateTests(unittest.TestCase):
    def test_close_is_idempotent_and_invalid_wait_is_refused(self):
        gate = InstallationGate()
        gate.close()
        gate.close()
        for timeout in (-1, 10001, True):
            with self.subTest(timeout=timeout), self.assertRaises(ValueError):
                InstallationGate(timeout)

    @unittest.skipUnless(os.name == "nt", "Actual Windows kernel required")
    def test_independent_launcher_waits_for_installer_and_then_can_start(self):
        script = (
            "from experiments.desktop.installation_gate import InstallationGate; "
            "gate=InstallationGate(timeout_ms=50); gate.close()"
        )

        def attempt():
            return subprocess.run(
                [sys.executable, "-B", "-S", "-c", script],
                cwd=ROOT,
                capture_output=True,
                timeout=10,
            )

        with InstallationGate():
            blocked = attempt()
            self.assertNotEqual(blocked.returncode, 0)
            self.assertIn(b"installation or launch is in progress", blocked.stderr)
        ready = attempt()
        self.assertEqual(ready.returncode, 0, ready.stderr)


class WorkerPipeTests(unittest.TestCase):
    def test_readiness_keeps_framing_and_never_reads_an_empty_pipe(self):
        counts = iter((0, 0, 1, 1, 1))
        parts = iter((b"O", b"K", b"\n"))
        available = Mock(side_effect=lambda: next(counts))
        with patch.object(windows_worker.os, "read", side_effect=lambda *_: next(parts)) as read:
            with patch.object(windows_worker.time, "sleep") as sleep:
                self.assertEqual(windows_worker.read_command(7, available), b"OK\n")
                self.assertEqual(sleep.call_count, 2)
                self.assertEqual(read.call_count, 3)
        for payload, expected in ((b"x" * 80, b"x" * 64), (b"partial", b"partial")):
            with self.subTest(payload=payload):
                parts = iter(bytes((x,)) for x in payload)
                with patch.object(
                    windows_worker.os, "read", side_effect=lambda *_: next(parts, b"")
                ):
                    self.assertEqual(windows_worker.read_command(7, lambda: 1), expected)
        with patch.object(windows_worker.os, "read") as read:
            self.assertEqual(windows_worker.read_command(7, lambda: None), b"")
            read.assert_not_called()

    def test_watch_cancels_on_eof_and_pipe_error_but_preserves_unknown_command(self):
        for command in (CANCEL, b"", b"unknown\n", OSError("control pipe failed")):
            with self.subTest(command=command):
                thread = Mock()
                with (
                    patch.object(windows_worker.sys, "argv", ["worker", "experiments.synthetic"]),
                    patch.object(windows_worker.sys, "stdin", Mock(fileno=lambda: 7)),
                    patch.object(windows_worker, "_windows_pipe_available", return_value=Mock()),
                    patch.object(windows_worker, "read_command", side_effect=[START, command]),
                    patch.object(windows_worker.threading, "Thread", thread),
                    patch.object(windows_worker.runpy, "run_module") as run,
                    patch.object(windows_worker._thread, "interrupt_main") as interrupt,
                ):
                    self.assertEqual(windows_worker.main(), 0)
                    run.assert_called_once_with(
                        "experiments.synthetic", run_name="__main__", alter_sys=True
                    )
                    watch = thread.call_args.kwargs["target"]
                    if isinstance(command, OSError):
                        with self.assertRaises(OSError) as failure:
                            watch()
                        self.assertIs(failure.exception, command)
                    else:
                        watch()
                    if command == b"unknown\n":
                        interrupt.assert_not_called()
                    else:
                        interrupt.assert_called_once_with(signal.SIGINT)

    @unittest.skipUnless(os.name == "nt", "Actual Windows NumPy import under owned control pipe")
    def test_numpy_import_under_job_and_live_control_pipe(self):
        from experiments.desktop.runtime import interpreter, packaged_manifest
        from experiments.m4.initial_load import process as supervisor
        from experiments.m4.secure_study.common import NATIVE_PROJECT

        python = interpreter(NATIVE_PROJECT)
        if not python.is_file() and packaged_manifest() is None:
            self.skipTest("Separate native interpreter is absent from this source checkout")
        self.assertTrue(python.is_file(), "Bundled native interpreter is required")
        roots = []
        original_spawn = supervisor.spawn

        def observe_spawn(*args, **kwargs):
            process = original_spawn(*args, **kwargs)
            roots.append(process)
            self.addCleanup(process._opent1d_ownership.close)
            return process

        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            package = root / "experiments"
            package.mkdir()
            # A synthetic module, with the unchanged real gate found through
            # this explicit package path. No scientific function is invoked.
            (package / "__init__.py").write_text(
                "__path__.append(" + repr(str(ROOT / "experiments")) + ")\n"
            )
            (package / "control_import_probe.py").write_text(
                "import json,threading\n"
                "import numpy\n"
                "print(json.dumps({'numpy':numpy.__version__,'watch_alive':any("
                "t.name=='opent1d-control' and t.is_alive() "
                "for t in threading.enumerate())}),flush=True)\n"
            )
            log = root / "worker.log"
            with (
                patch.object(supervisor, "ROOT", root),
                patch.object(supervisor, "spawn", side_effect=observe_spawn),
            ):
                code, error = supervisor.supervise(
                    [str(python), "-B", "-E", "-s", "-m", "experiments.control_import_probe"],
                    log,
                    600,
                    supervisor.Control(),
                    grace_seconds=20,
                )
            output = log.read_text()
            self.assertEqual((code, error), (0, None), output)
            self.assertEqual(
                json.loads(output.splitlines()[-1]), {"numpy": "1.26.4", "watch_alive": True}
            )
            self.assertEqual(len(roots), 1)
            self.assertEqual(roots[0].returncode, 0)
            self.assertTrue(roots[0]._opent1d_ownership.closed)

    def worker(self, *args):
        return subprocess.Popen(
            [
                sys.executable,
                "-B",
                "-S",
                "-m",
                "experiments.gui.windows_worker",
                "experiments.observation_analysis",
                *map(str, args),
            ],
            cwd=ROOT,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )

    def test_eof_before_admission_does_not_run_the_module(self):
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary) / "never-created"
            process = self.worker("example", "--output", output)
            stdout, stderr = process.communicate(timeout=10)
            self.assertEqual(process.returncode, 2, (stdout, stderr))
            self.assertFalse(output.exists())

    def test_normal_completion_does_not_wait_for_control_pipe_or_abort_at_exit(self):
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary) / "created"
            process = self.worker("example", "--output", output)
            try:
                process.stdin.write(START)
                process.stdin.flush()
                process.wait(timeout=10)
                stdout, stderr = process.communicate(timeout=10)
                self.assertEqual(process.returncode, 0, (stdout, stderr))
                self.assertTrue((output / "observations.csv").is_file())
            finally:
                if process.poll() is None:
                    process.kill()
                    process.communicate(timeout=10)

    def test_private_cancel_seals_a_reconstructible_interrupted_analysis(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            inputs = export_example(root / "input", "increase")
            settings = json.loads((inputs / "settings.json").read_text())
            settings["uncertainty"]["draws"] = 1024
            dump(inputs / "settings.json", settings)
            freeze(
                inputs / "package.json",
                inputs / "observations.csv",
                inputs / "settings.json",
                root / "plan",
            )
            output = root / "interrupted"
            process = self.worker("run", "--config", root / "plan", "--output", output)
            try:
                process.stdin.write(START)
                process.stdin.flush()
                # Match the Windows smoke's 30 s analysis-entry observer;
                # snapshot preparation is separate from the 10 s CANCEL wait.
                deadline, phase = time.monotonic() + 30, None
                while process.poll() is None and time.monotonic() < deadline:
                    try:
                        phase = json.loads((output / "execution.json").read_text())["phase"]
                    except (OSError, ValueError, KeyError):
                        pass
                    if phase == "analysis":
                        break
                    time.sleep(0.005)
                self.assertEqual(phase, "analysis", (phase, process.poll()))
                process.stdin.write(CANCEL)
                process.stdin.flush()
                # Keep control stdin open until the process exits: communicate()
                # closes it and would be an additional EOF cancellation source.
                process.wait(timeout=10)
                stdout, stderr = process.communicate(timeout=10)
                self.assertEqual(process.returncode, 1, (stdout, stderr))
            finally:
                if process.poll() is None:
                    process.kill()
                    process.communicate(timeout=10)
            execution = json.loads((output / "execution.json").read_text())
            self.assertEqual(execution["status"], "interrupted")
            self.assertEqual(execution["interruption_signal"], signal.SIGINT)
            report = reconstruct(output, root / "rebuilt", allow_failed=True)
            self.assertFalse(report["coverage"]["complete_cohort"])


class WindowsOwnershipTests(unittest.TestCase):
    def test_detached_worker_is_admitted_only_after_job_assignment(self):
        from experiments.gui.windows_process import spawn_owned

        events = []
        native, job = Mock(pid=123), Mock()
        job.pids.return_value = [123]
        job.assign.side_effect = lambda process: events.append(("assigned", process))
        native.stdin.write.side_effect = lambda message: events.append(("admitted", message))
        with (
            patch("experiments.gui.windows_process.os.name", "nt"),
            patch("experiments.gui.windows_process.Job", return_value=job),
            patch(
                "experiments.gui.windows_process.subprocess.Popen", return_value=native
            ) as launch,
        ):
            process, owner = spawn_owned(
                [sys.executable, "-B", "-S", "-m", "experiments.observation_analysis", "example"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
        try:
            self.assertEqual(events, [("assigned", native), ("admitted", START)])
            options = launch.call_args.kwargs
            self.assertEqual(options["creationflags"], 0x00000008)
            self.assertEqual(options["stdin"], subprocess.PIPE)
            self.assertEqual(options["stdout"], subprocess.PIPE)
            self.assertEqual(options["stderr"], subprocess.PIPE)
            self.assertIs(process.process, native)
            native.stdin.flush.assert_called_once_with()
        finally:
            owner.close()

    def test_private_cancel_once_and_forced_cleanup_uses_only_job_authority(self):
        native, job = Mock(pid=123), Mock()
        native.poll.return_value = None
        job.pids.side_effect = [[123, 456], [123, 456], []]
        process = WindowsProcess(native, job)
        owner = WindowsOwnership(process)
        owner.observe()
        process.send_signal(signal.SIGTERM)
        process.send_signal(signal.SIGTERM)
        native.stdin.write.assert_called_once_with(CANCEL)
        with patch("experiments.gui.windows_process.time.sleep"):
            forced, remaining = owner.cleanup(0)
        self.assertTrue(forced)
        self.assertEqual(remaining, [])
        job.terminate.assert_called_once_with()
        job.close.assert_called_once_with()
        self.assertEqual([item["pid"] for item in owner.receipt()], [123, 456])
        owner.close()
        owner.signal(signal.SIGTERM)
        self.assertEqual(owner.observe(), {})
        job.close.assert_called_once_with()

    @unittest.skipUnless(os.name == "nt", "Actual Windows kernel required")
    def test_job_close_removes_descendant_after_direct_child_exits(self):
        import ctypes
        from ctypes import wintypes

        from experiments.gui.windows_process import Job

        script = (
            "import subprocess,sys; sys.stdin.buffer.readline(); "
            "p=subprocess.Popen([sys.executable,'-c','import time;time.sleep(60)'],"
            "stdin=subprocess.DEVNULL,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL);"
            "print(p.pid,flush=True)"
        )
        job = Job()
        process = subprocess.Popen(
            [sys.executable, "-B", "-S", "-c", script],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            creationflags=subprocess.CREATE_NO_WINDOW,
        )
        kernel = ctypes.WinDLL("kernel32", use_last_error=True)
        kernel.OpenProcess.argtypes = (wintypes.DWORD, wintypes.BOOL, wintypes.DWORD)
        kernel.OpenProcess.restype = wintypes.HANDLE
        kernel.WaitForSingleObject.argtypes = (wintypes.HANDLE, wintypes.DWORD)
        kernel.WaitForSingleObject.restype = wintypes.DWORD
        kernel.CloseHandle.argtypes = (wintypes.HANDLE,)
        kernel.CloseHandle.restype = wintypes.BOOL
        child_handle = None
        try:
            job.assign(process)
            stdout, stderr = process.communicate(START, timeout=10)
            self.assertEqual(process.returncode, 0, stderr)
            child = int(stdout)
            self.assertIn(child, job.pids())
            child_handle = kernel.OpenProcess(0x00100000, False, child)  # SYNCHRONIZE
            self.assertTrue(child_handle)
            self.assertEqual(kernel.WaitForSingleObject(child_handle, 0), 258)  # WAIT_TIMEOUT
            job.close()
            self.assertEqual(kernel.WaitForSingleObject(child_handle, 5000), 0)  # exited
        finally:
            job.close()
            if child_handle:
                kernel.CloseHandle(child_handle)
            if process.poll() is None:
                process.kill()
                process.communicate(timeout=10)

    @unittest.skipUnless(os.name == "nt", "Actual Windows kernel required")
    def test_detached_worker_cleanup_still_reaps_a_live_descendant(self):
        import ctypes
        from ctypes import wintypes

        from experiments.gui.windows_process import Job

        script = (
            "import subprocess,sys; sys.stdin.buffer.readline(); "
            "p=subprocess.Popen([sys.executable,'-c','import time;time.sleep(60)'],"
            "stdin=subprocess.DEVNULL,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,"
            "creationflags=subprocess.DETACHED_PROCESS);print(p.pid,flush=True)"
        )
        job = Job()
        native = subprocess.Popen(
            [sys.executable, "-B", "-S", "-c", script],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            creationflags=subprocess.DETACHED_PROCESS,
        )
        process = WindowsProcess(native, job)
        owner = WindowsOwnership(process)
        kernel = ctypes.WinDLL("kernel32", use_last_error=True)
        kernel.OpenProcess.argtypes = (wintypes.DWORD, wintypes.BOOL, wintypes.DWORD)
        kernel.OpenProcess.restype = wintypes.HANDLE
        kernel.WaitForSingleObject.argtypes = (wintypes.HANDLE, wintypes.DWORD)
        kernel.WaitForSingleObject.restype = wintypes.DWORD
        kernel.CloseHandle.argtypes = (wintypes.HANDLE,)
        kernel.CloseHandle.restype = wintypes.BOOL
        child_handle = None
        try:
            job.assign(native)
            owner.observe()
            stdout, stderr = native.communicate(START, timeout=10)
            self.assertEqual(native.returncode, 0, stderr)
            child = int(stdout)
            self.assertIn(child, owner.observe())
            child_handle = kernel.OpenProcess(0x00100000, False, child)  # SYNCHRONIZE only
            self.assertTrue(child_handle)
            self.assertEqual(kernel.WaitForSingleObject(child_handle, 0), 258)
            forced, remaining = owner.cleanup(0)
            self.assertTrue(forced)
            self.assertEqual(remaining, [])
            self.assertEqual(kernel.WaitForSingleObject(child_handle, 0), 0)
        finally:
            owner.close()
            if child_handle:
                kernel.CloseHandle(child_handle)
            if native.poll() is None:
                native.kill()  # This retained Popen handle only, never a saved PID.
                native.communicate(timeout=10)

    @unittest.skipUnless(os.name == "nt", "Actual Windows kernel required")
    def test_real_job_launch_gates_and_reaps_example(self):
        with self.subTest(boundary="actual worker membership before START"):
            self._probe_membership_before_start()
        for repetition in range(5):
            with self.subTest(repetition=repetition):
                self._probe_real_job_completion(repetition)

    def _probe_membership_before_start(self):
        import ctypes
        from ctypes import wintypes

        from experiments.gui.windows_process import Job, spawn_owned
        from experiments.workflows.checks import safe_environment
        from tests.windows_job_probe import kernel

        api = kernel()
        inner_handle, process, owner = None, None, None
        observed = {}
        original_assign = Job.assign
        with tempfile.TemporaryDirectory(prefix="opent1d-before-assign-") as temporary:
            root = Path(temporary).resolve()
            ready, work = root / "ready.json", root / "work-started"
            package = root / "experiments"
            package.mkdir()
            (package / "__init__.py").write_text(
                "import json,os,sys,threading\n"
                "from pathlib import Path\n"
                f"__path__.append({str(ROOT / 'experiments')!r})\n"
                "from experiments.platform_files import atomic_write_bytes\n"
                "backstop=threading.Timer(10,lambda:os._exit(97))\n"
                "backstop.daemon=True\nbackstop.start()\n"
                f"atomic_write_bytes(Path({str(ready)!r}),json.dumps({{'pid':os.getpid(),"
                "'base':sys._base_executable,'version':sys.version}).encode())\n",
                encoding="utf-8",
            )
            (package / "synthetic_gate_probe.py").write_text(
                "from pathlib import Path\n"
                f"Path({str(work)!r}).write_bytes(b'Only admitted module work')\n",
                encoding="utf-8",
            )

            def delayed_assign(job, native):
                nonlocal inner_handle
                deadline = time.monotonic() + 5
                actual = None
                while time.monotonic() < deadline:
                    try:
                        candidate = json.loads(ready.read_text(encoding="utf-8"))
                        if isinstance(candidate, dict) and set(candidate) == {
                            "pid",
                            "base",
                            "version",
                        }:
                            if (
                                type(candidate["pid"]) is int
                                and candidate["pid"] > 0
                                and isinstance(candidate["base"], str)
                                and isinstance(candidate["version"], str)
                            ):
                                actual = candidate["pid"]
                                break
                    except (FileNotFoundError, PermissionError, json.JSONDecodeError):
                        # Publication may still hold its Windows DELETE handle.
                        pass
                    time.sleep(0.01)
                self.assertIsNotNone(actual, "Actual worker did not publish bounded readiness")
                self.assertFalse(work.exists(), "Module ran before START admission")
                inner_handle = api.OpenProcess(0x00100000 | 0x1000, False, actual)
                self.assertTrue(inner_handle, "Actual ready worker query handle is unavailable")
                original_assign(job, native)
                member = wintypes.BOOL()
                if not api.IsProcessInJob(inner_handle, job.handle, ctypes.byref(member)):
                    raise ctypes.WinError(ctypes.get_last_error())
                observed.update(
                    leader_pid=native.pid,
                    actual_worker_pid=actual,
                    actual_worker_in_job=bool(member.value),
                    actual_worker_wait=api.WaitForSingleObject(inner_handle, 0),
                    work_started=work.exists(),
                    actual_matches_launched_base=os.path.samefile(
                        candidate["base"], native.args[0]
                    ),
                    same_current_base=os.path.samefile(candidate["base"], sys._base_executable),
                    same_current_version=candidate["version"] == sys.version,
                )
                print(
                    "OPENT1D_WINDOWS_BEFORE_START=" + json.dumps(observed, sort_keys=True),
                    flush=True,
                )
                self.assertFalse(work.exists(), "Module ran while its START gate was closed")
                self.assertTrue(observed["actual_matches_launched_base"], observed)
                self.assertTrue(observed["same_current_base"], observed)
                self.assertTrue(observed["same_current_version"], observed)
                self.assertEqual(actual, native.pid, "No-site worker still used a redirector")
                self.assertTrue(
                    member.value, "Actual worker is outside the assigned Job: " + repr(observed)
                )

            try:
                with open(os.devnull, "wb") as log, patch.object(Job, "assign", delayed_assign):
                    process, owner = spawn_owned(
                        [
                            sys.executable,
                            "-B",
                            "-E",
                            "-s",
                            "-S",
                            "-m",
                            "experiments.synthetic_gate_probe",
                        ],
                        cwd=root,
                        env=safe_environment(),
                        stdout=log,
                        stderr=log,
                    )
                    self.assertEqual(process.wait(timeout=5), 0)
                    self.assertTrue(work.is_file(), "Admitted module work did not run")
            finally:
                try:
                    try:
                        if owner is not None:
                            _forced, remaining = owner.cleanup(0)
                            self.assertEqual(remaining, [])
                    finally:
                        if inner_handle:
                            # Failed assignment closes private stdin (EOF); the
                            # fixture also exits itself after ten seconds. This is
                            # synchronization only, never termination by a saved PID.
                            result = api.WaitForSingleObject(inner_handle, 12000)
                            print("OPENT1D_WINDOWS_BEFORE_START_CLEANUP=" + str(result), flush=True)
                            self.assertEqual(result, 0, "Actual private fixture did not exit")
                        if not observed.get("actual_worker_in_job", False):
                            self.assertFalse(work.exists(), "Failed admission ran module work")
                finally:
                    if inner_handle and not api.CloseHandle(inner_handle):
                        raise ctypes.WinError(ctypes.get_last_error())

    def _probe_real_job_completion(self, repetition):
        from experiments.gui.windows_process import spawn_owned
        from tests.windows_job_probe import inspect_job_processes

        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary) / "invented"
            with open(os.devnull, "wb") as log:
                process, owner = spawn_owned(
                    [
                        sys.executable,
                        "-B",
                        "-S",
                        "-m",
                        "experiments.observation_analysis",
                        "example",
                        "--output",
                        str(output),
                    ],
                    cwd=ROOT,
                    stdout=log,
                    stderr=log,
                )
                observations, completed_at, image_cache = [], None, {}
                original_pids = process.job.pids

                def observe_cleanup_inventory():
                    # Diagnose only the current live Job's returned IDs. Query
                    # and synchronization rights confer no termination authority.
                    pids = original_pids()
                    row = inspect_job_processes(process, pids, image_cache=image_cache)
                    row["seconds_after_wait"] = (
                        None if completed_at is None else time.monotonic() - completed_at
                    )
                    observations.append(row)
                    return pids  # Preserve the exact production inventory/result.

                try:
                    deadline = time.monotonic() + 15
                    while True:
                        before = dict(image_cache)
                        row = inspect_job_processes(
                            process, original_pids(), image_cache=image_cache
                        )
                        if image_cache != before:
                            print(
                                "OPENT1D_WINDOWS_RUNNING_JOB_PROBE="
                                + json.dumps({"repetition": repetition, **row}, sort_keys=True),
                                flush=True,
                            )
                        try:
                            code = process.wait(
                                timeout=max(0, min(0.005, deadline - time.monotonic()))
                            )
                            break
                        except subprocess.TimeoutExpired:
                            if time.monotonic() >= deadline:
                                raise
                    completed_at = time.monotonic()
                    self.assertEqual(code, 0)
                    self.assertTrue((output / "observations.csv").is_file())
                finally:
                    with patch.object(process.job, "pids", side_effect=observe_cleanup_inventory):
                        forced, remaining = owner.cleanup(0)
                print(
                    "OPENT1D_WINDOWS_JOB_PROBE="
                    + json.dumps(
                        {
                            "repetition": repetition,
                            "forced": forced,
                            "remaining": remaining,
                            "observations": observations,
                        },
                        sort_keys=True,
                    ),
                    flush=True,
                )
                self.assertFalse(forced, observations)
                self.assertEqual(remaining, [], observations)


if __name__ == "__main__":
    unittest.main()
