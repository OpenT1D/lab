"""Bounded Concept lifecycle presentation and strict SDK recovery transport."""

import shutil
import subprocess
import tempfile
import time
import unittest
import uuid
from pathlib import Path

from test_installed_gui import ControlledSDK, state

ROOT = Path(__file__).resolve().parents[1]


class RecoverySDK(ControlledSDK):
    def Project(self, path):
        project = super().Project(path)

        def recover(attempt, *, execution_stopped=False):
            self.calls.append(("recover", attempt, execution_stopped))
            return {"attempt": attempt, "result": {"completeness": "incomplete"}}

        project.recover = recover
        return project


class ConceptRecoveryTransportTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="concept-recovery-")
        self.addCleanup(self.temporary.cleanup)
        self.sdk = RecoverySDK()
        self.controller = state.Controller(
            Path(self.temporary.name).resolve() / "workspace", sdk=self.sdk
        )
        self.addCleanup(self.controller.close)
        self.project = self.finish(self.submit("create", {"name": "Recovery fixture"}))["project"]

    def submit(self, operation, arguments, project=None):
        return self.controller.submit(
            {
                "request_id": uuid.uuid4().hex,
                "operation": operation,
                "arguments": arguments,
                "project": project,
            }
        )

    def finish(self, job):
        deadline = time.monotonic() + 5
        while time.monotonic() < deadline:
            value = self.controller.get_job(job["id"])
            if value["status"] != "running" and self.controller.active is None:
                return value
            time.sleep(0.005)
        self.fail("Controlled action did not release its action slot")

    def test_recovery_requires_exact_true_before_calling_sdk(self):
        attempt = "a" * 64
        for consent in (False, None, 1, "true"):
            with self.subTest(consent=consent):
                result = self.finish(
                    self.submit(
                        "recover", {"attempt": attempt, "execution_stopped": consent}, self.project
                    )
                )
                self.assertEqual(result["status"], "error")
                self.assertIn("Explicit confirmation", result["error"])
        self.assertFalse(
            any(isinstance(call, tuple) and call[0] == "recover" for call in self.sdk.calls)
        )
        result = self.finish(
            self.submit("recover", {"attempt": attempt, "execution_stopped": True}, self.project)
        )
        self.assertEqual(result["status"], "done", result)
        self.assertIn(("recover", attempt, True), self.sdk.calls)
        self.assertEqual(result["result"]["attempt"], attempt)

    def test_open_and_refresh_never_recover_an_attempt(self):
        project_path = self.controller.catalog["projects"][self.project]["path"]
        self.finish(self.submit("open", {"path": project_path}))
        self.finish(self.submit("refresh", {}, self.project))
        self.assertFalse(
            any(isinstance(call, tuple) and call[0] == "recover" for call in self.sdk.calls)
        )


@unittest.skipUnless(shutil.which("node"), "Node is required for controlled frontend checks")
class ConceptExecutionFrontendTests(unittest.TestCase):
    def test_saved_identity_attempt_preservation_and_owned_lifecycle(self):
        result = subprocess.run(
            [shutil.which("node"), str(ROOT / "tests/workbench_execution.mjs")],
            cwd=ROOT,
            text=True,
            capture_output=True,
            timeout=30,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
