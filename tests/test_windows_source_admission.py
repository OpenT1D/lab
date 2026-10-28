"""Windows source admission is bounded to the two stdlib MMTT task routes."""

import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from experiments.workflows import checks, dispatch
from experiments.workflows.registry import TASKS


class WindowsSourceAdmissionTests(unittest.TestCase):
    def assemble(self, task, *, host="nt", packaged=False, ready=True, uv=True, issues=()):
        with (
            patch.object(checks, "os", SimpleNamespace(name=host)),
            patch.object(checks, "packaged_manifest", return_value={} if packaged else None),
            patch.object(checks, "uv_ready", return_value={"ready": uv}),
        ):
            return checks.assemble_check(
                TASKS[task], {}, list(issues), [{"project": ".", "ready": ready}]
            )

    def test_only_the_two_stdlib_tasks_admit_a_ready_windows_source_environment(self):
        for task in TASKS:
            expected = task in {"mmtt-sensitivity", "mmtt-sampling"}
            with self.subTest(task=task):
                result = self.assemble(task)
                self.assertEqual(result["runtimes_ready"], expected)
                self.assertEqual(result["ready"], expected)
                self.assertFalse(result["posix_host"])
                if expected:
                    self.assertEqual(checks.runtime_requirements(TASKS[task]), {".": {}})

    def test_stdlib_windows_admission_still_requires_runtime_uv_and_valid_input(self):
        for task in ("mmtt-sensitivity", "mmtt-sampling"):
            for ready, uv in ((False, True), (True, False), (False, False)):
                with self.subTest(task=task, runtime=ready, uv=uv):
                    result = self.assemble(task, ready=ready, uv=uv)
                    self.assertFalse(result["runtimes_ready"])
                    self.assertFalse(result["ready"])
            result = self.assemble(task, issues=[{"reason": "unavailable_input"}])
            self.assertTrue(result["runtimes_ready"])
            self.assertFalse(result["ready"])
            self.assertFalse(self.assemble(task, host="unsupported")["ready"])

    def test_posix_and_verified_package_host_admission_keep_the_existing_task_roster(self):
        for task in TASKS:
            with self.subTest(task=task):
                self.assertTrue(self.assemble(task, host="posix")["ready"])
                self.assertTrue(self.assemble(task, packaged=True)["ready"])
                self.assertFalse(self.assemble(task, packaged=True, ready=False)["ready"])

    def test_declared_root_readiness_cannot_authorize_an_unsupported_current_runtime(self):
        for implementation, version in (
            ("pypy", (3, 12, 13)),
            ("cpython", (3, 11, 9)),
            ("cpython", (3, 13, 1)),
        ):
            current = SimpleNamespace(
                implementation=SimpleNamespace(name=implementation),
                version_info=version,
                executable="unsupported-current-interpreter",
            )
            with patch.object(checks, "sys", current):
                for task in ("mmtt-sensitivity", "mmtt-sampling"):
                    with self.subTest(implementation=implementation, version=version, task=task):
                        result = self.assemble(task)
                        self.assertFalse(result["runtimes_ready"])
                        self.assertFalse(result["current_stdlib_runtime"]["ready"])
                        # The existing installed package and POSIX contracts are separate.
                        for control in (
                            self.assemble(task, packaged=True),
                            self.assemble(task, host="posix"),
                        ):
                            self.assertTrue(control["ready"])
                            self.assertNotIn("current_stdlib_runtime", control)
                        with (
                            patch.object(dispatch, "os", SimpleNamespace(name="nt")),
                            patch.object(dispatch, "packaged_manifest", return_value=None),
                            patch.object(dispatch, "interpreter", return_value="declared-root"),
                            self.assertRaisesRegex(ValueError, "current CPython 3.12"),
                        ):
                            dispatch.command_for(TASKS[task], SimpleNamespace())

    def test_unsupported_current_source_runtime_cannot_spawn_or_create_output(self):
        current = SimpleNamespace(
            implementation=SimpleNamespace(name="cpython"),
            version_info=(3, 13, 1),
            executable="unsupported-current-interpreter",
        )
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary) / "not-created"
            for task in ("mmtt-sensitivity", "mmtt-sampling"):
                with (
                    self.subTest(task=task),
                    patch.object(checks, "sys", current),
                    patch.object(checks, "os", SimpleNamespace(name="nt")),
                    patch.object(checks, "packaged_manifest", return_value=None),
                    patch.object(checks, "prepare_check", return_value=({}, [])),
                    patch.object(checks, "probe_runtime", return_value={"ready": True}),
                    patch.object(checks, "uv_ready", return_value={"ready": True}),
                    patch.object(dispatch, "run_process") as run,
                ):
                    result = dispatch.execute(TASKS[task], SimpleNamespace(output=output))
                    self.assertFalse(result["runtimes_ready"])
                    self.assertIsNone(result["child_exit_code"])
                    run.assert_not_called()
                    self.assertFalse(output.exists())

    def test_windows_mmtt_commands_use_current_no_site_runtime_only_in_source(self):
        current = checks.current_stdlib_runtime()
        args = SimpleNamespace(
            config="invented-plan",
            output="invented-output",
            archive="invented-archive",
            allow_failed=False,
        )
        for task in ("mmtt-sensitivity", "mmtt-sampling"):
            for operation in ("run", "reconstruct"):
                for host, packaged in (("nt", False), ("posix", False), ("nt", True)):
                    with self.subTest(task=task, operation=operation, host=host, packaged=packaged):
                        with (
                            patch.object(dispatch, "os", SimpleNamespace(name=host)),
                            patch.object(
                                dispatch, "packaged_manifest", return_value={} if packaged else None
                            ),
                            patch.object(dispatch, "interpreter", return_value="declared-root"),
                        ):
                            argv = dispatch.command_for(TASKS[task], args, operation=operation)
                        selected = host == "nt" and not packaged
                        self.assertEqual(
                            argv[0], current["executable"] if selected else "declared-root"
                        )
                        self.assertEqual(
                            "-S" in argv[: argv.index("-m")], selected or operation == "reconstruct"
                        )

    def test_other_windows_task_commands_keep_their_project_and_site_contract(self):
        args = SimpleNamespace(
            source="source",
            config="config",
            bundle="bundle",
            output="output",
            profile="profile",
            seed=101,
            timeout=30,
            timeout_seconds=30,
            reference=None,
        )
        for task in TASKS.values():
            if task.id in ("mmtt-sensitivity", "mmtt-sampling"):
                continue
            with self.subTest(task=task.id):
                with (
                    patch.object(dispatch, "os", SimpleNamespace(name="nt")),
                    patch.object(dispatch, "interpreter", return_value="declared-project"),
                    patch.object(
                        dispatch,
                        "current_stdlib_runtime",
                        side_effect=AssertionError("Unexpected current-runtime selection"),
                    ),
                ):
                    argv = dispatch.command_for(task, args)
                self.assertEqual(argv[:5], ["declared-project", "-B", "-E", "-s", "-m"])


if __name__ == "__main__":
    unittest.main()
