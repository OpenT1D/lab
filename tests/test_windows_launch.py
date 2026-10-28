"""No-site Windows launches retain the current interpreter's base identity."""

import os
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

from experiments.gui import windows_process


class WindowsLaunchTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name).resolve()
        self.base = self.root / "base" / "python.exe"
        self.current = self.root / "venv" / "Scripts" / "python.exe"
        self.foreign = self.root / "foreign" / "python.exe"
        for executable in (self.base, self.current, self.foreign):
            executable.parent.mkdir(parents=True)
            executable.write_bytes(b"Invented executable identity; never executed")
        self.runtime = SimpleNamespace(
            executable=str(self.current),
            _base_executable=str(self.base),
            base_prefix=str(self.base.parent),
            implementation=SimpleNamespace(name="cpython"),
            version_info=(3, 12, 13),
        )
        self.native, self.job = Mock(pid=123), Mock()
        self.job.pids.return_value = [123]
        self.launch = Mock(return_value=self.native)
        for target, value in (
            ("os", SimpleNamespace(**{**vars(os), "name": "nt"})),
            ("sys", self.runtime),
            ("Job", Mock(return_value=self.job)),
        ):
            context = patch.object(windows_process, target, value)
            context.start()
            self.addCleanup(context.stop)
        context = patch.object(windows_process.subprocess, "Popen", self.launch)
        context.start()
        self.addCleanup(context.stop)

    def spawn(self, python=None, flags=("-B", "-E", "-s", "-S"), **kwargs):
        requested = [
            str(python or self.current),
            *flags,
            "-m",
            "experiments.observation_analysis",
            "example",
        ]
        process, owner = windows_process.spawn_owned(requested, **kwargs)
        self.addCleanup(owner.close)
        return requested, process

    def test_no_site_current_venv_launches_its_base_and_records_actual_bootstrap(self):
        requested, process = self.spawn()
        actual = self.launch.call_args.args[0]
        self.assertEqual(actual[0], str(self.base))
        self.assertEqual(actual[1:6], ["-B", "-E", "-s", "-S", "-m"])
        self.assertEqual(actual[6:], ["experiments.gui.windows_worker", *requested[6:]])
        self.assertEqual(
            process.launch_record,
            {
                "requested_argv": requested,
                "argv": actual,
                "selection": "current-cpython-stdlib-base",
            },
        )
        self.job.assign.assert_called_once_with(self.native)
        self.native.stdin.write.assert_called_once_with(windows_process.START)
        self.assertEqual(self.launch.call_args.kwargs["creationflags"], 0x00000008)

    def test_foreign_and_site_enabled_interpreters_are_never_substituted(self):
        self.runtime._base_executable = None
        for executable, flags in (
            (self.foreign, ("-B", "-S")),
            (self.foreign, ("-B",)),
            (self.current, ("-B", "-E", "-s")),
            (self.current, ("-I",)),
        ):
            with self.subTest(executable=executable, flags=flags):
                requested, process = self.spawn(executable, flags)
                actual = self.launch.call_args.args[0]
                self.assertEqual(
                    actual,
                    requested[: requested.index("-m") + 1]
                    + ["experiments.gui.windows_worker", *requested[requested.index("-m") + 1 :]],
                )
                self.assertEqual(process.launch_record["selection"], "requested")

    def test_direct_packaged_current_interpreter_keeps_exact_argv_and_path_configuration(self):
        self.runtime.executable = str(self.base)
        (self.base.parent / "python312._pth").write_text("import site\n", encoding="utf-8")
        requested, process = self.spawn(self.base)
        self.assertEqual(self.launch.call_args.args[0][0], requested[0])
        self.assertEqual(process.launch_record["selection"], "current-cpython-direct")

    def test_foreign_hardlinked_venv_retains_its_own_path_and_configuration(self):
        self.foreign.unlink()
        os.link(self.current, self.foreign)
        self.assertTrue(os.path.samefile(self.current, self.foreign))
        (self.foreign.parent / "pyvenv.cfg").write_text(
            "home = another-interpreter-installation\n", encoding="utf-8"
        )
        requested, process = self.spawn(self.foreign)
        self.assertEqual(self.launch.call_args.args[0][0], requested[0])
        self.assertEqual(process.launch_record["selection"], "requested")

    def test_current_wrong_implementation_or_minor_version_cannot_launch(self):
        for implementation, version in (
            ("pypy", (3, 12, 13)),
            ("cpython", (3, 11, 9)),
            ("cpython", (3, 13, 1)),
        ):
            with self.subTest(implementation=implementation, version=version):
                self.runtime.implementation.name = implementation
                self.runtime.version_info = version
                with self.assertRaisesRegex(ValueError, "CPython 3.12"):
                    self.spawn()
        self.launch.assert_not_called()
        windows_process.Job.assert_not_called()

    def test_invalid_base_identity_is_rejected_before_job_or_process_creation(self):
        for base in (
            None,
            "relative.exe",
            str(self.root / "missing.exe"),
            str(self.base.parent),
            str(self.foreign),
        ):
            with self.subTest(base=base):
                self.runtime._base_executable = base
                with self.assertRaises((OSError, ValueError)):
                    self.spawn()
        self.launch.assert_not_called()
        windows_process.Job.assert_not_called()

    def test_venv_or_path_overrides_cannot_be_mistaken_for_direct_base(self):
        for path in (
            self.base.parent / "pyvenv.cfg",
            self.root / "pyvenv.cfg",
            self.current.parent / "python._pth",
            self.base.parent / "python312._pth",
        ):
            with self.subTest(path=path):
                path.write_text("Invented path override\n", encoding="utf-8")
                try:
                    with self.assertRaisesRegex(ValueError, "unsupported virtual/path"):
                        self.spawn()
                finally:
                    path.unlink()
        self.launch.assert_not_called()
        windows_process.Job.assert_not_called()

    def test_executable_override_cannot_bypass_recorded_selection(self):
        with self.assertRaises(ValueError):
            self.spawn(executable=str(self.foreign))
        self.launch.assert_not_called()
        windows_process.Job.assert_not_called()

    def test_failed_assignment_never_sends_start_and_closes_retained_authorities(self):
        self.job.assign.side_effect = OSError("Invented assignment failure")
        self.native.poll.return_value = None
        with self.assertRaisesRegex(OSError, "Invented assignment failure"):
            self.spawn()
        self.native.stdin.write.assert_not_called()
        self.native.stdin.close.assert_called_once_with()
        self.native.kill.assert_called_once_with()
        self.native.wait.assert_called_once_with(timeout=2)
        self.job.close.assert_called_once_with()


if __name__ == "__main__":
    unittest.main()
