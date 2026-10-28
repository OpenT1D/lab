"""Windows source admission is bounded to the two stdlib MMTT task routes."""

import unittest
from types import SimpleNamespace
from unittest.mock import patch

from experiments.workflows import checks
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


if __name__ == "__main__":
    unittest.main()
