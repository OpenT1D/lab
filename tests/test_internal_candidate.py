"""Actual installed two-task capability gates, readonly reports and GUI lifecycle."""

import functools
import json
import os
import subprocess
import sys
import unittest
from unittest.mock import patch

from experiments.shared_services import store
from tests import test_installed_sampling as installed
from tests import test_workbench_installed as editable


@unittest.skipUnless(
    os.name == "posix" and sys.version_info[:2] == (3, 12), "POSIX CPython 3.12 candidate"
)
class InternalCandidate(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        builder = functools.partial(installed.build_sdk.build, mmtt_only=True)
        with patch.object(installed.build_sdk, "build", builder):
            installed.InstalledSampling.setUpClass.__func__(cls)

    setUp = installed.InstalledSampling.setUp
    call = installed.InstalledSampling.call
    server = editable.EditableWorkbench.server

    def test_enforced_manifest_facade_and_bootstrap_native_refusals(self):
        metadata = self.call("installation")
        self.assertEqual(metadata["schema"], "opent1d.installed-sdk/4")
        self.assertEqual(metadata["tasks"], ["mmtt-sensitivity", "mmtt-sampling"])
        self.assertEqual(metadata["native_execution"], "unavailable-public-policy")
        refused = self.call(
            "example", "--task", "m4-study-installed", "--output", self.root / "native", expected=2
        )
        self.assertIn("not admitted", refused["error"])
        self.assertFalse((self.root / "native").exists())
        package = self.environment / "lib/python3.12/site-packages/opent1d_lab"
        result = subprocess.run(
            [
                str(self.environment / "bin/python"),
                "-I",
                "-B",
                "-S",
                str(package / "_bootstrap.py"),
                "--native",
                "m4-study-installed",
                "reconstruct",
            ],
            cwd=self.root,
            env=self.env,
            capture_output=True,
            text=True,
            timeout=20,
        )
        self.assertEqual(result.returncode, 2, result.stdout + result.stderr)
        self.assertIn("not an admitted installed capability", json.loads(result.stdout)["error"])

    def test_workbench_native_actions_refuse_before_creating_concepts(self):
        with self.server() as app:
            handle = app.action("create", {"name": "Bounded candidate"})["project"]
            for operation, arguments in (
                ("prepare", {"task": "m4-study-installed", "case": "fasting"}),
                ("select_attachment", {"path": "/unsupported/native.json"}),
                (
                    "study_freeze",
                    {
                        "name": "Unavailable",
                        "question": "No native capability",
                        "forward_plan": None,
                        "observation_case": "complete",
                    },
                ),
            ):
                job = app.action(
                    operation,
                    arguments,
                    handle if operation != "select_attachment" else None,
                    expected="error",
                )
                self.assertIn("not admit", job["error"])
            self.assertEqual(app.state()["drafts"], [])
            app.restart()
            self.assertEqual(len(app.state()["projects"]), 1)
            self.assertEqual(
                app.state()["installation"]["tasks"], ["mmtt-sensitivity", "mmtt-sampling"]
            )

    def test_actual_native_read_is_readonly_and_exact_after_gui_restart(self):
        inputs = self.call(
            "example", "--task", "mmtt-sensitivity", "--output", self.root / "inputs"
        )["inputs"]
        project = self.root / "project"
        self.call("create", "--project", project, "--name", "Preserved original")
        plan = self.call(
            "freeze",
            "--project",
            project,
            "--task",
            "mmtt-sensitivity",
            "--package",
            inputs["package.json"],
            "--csv",
            inputs["observations.csv"],
            "--settings",
            inputs["settings.json"],
        )["plan"]
        attempt = self.call("run", "--project", project, "--plan", plan)
        before = store.inventory(project, store.Budget())
        rebuilt = self.call(
            "reconstruct",
            "--project",
            project,
            "--attempt",
            attempt["attempt"],
            "--output",
            self.root / "report",
        )
        self.assertEqual(rebuilt["report_sha256"], attempt["result"]["report_sha256"])
        with self.server() as app:
            handle = app.action("open", {"path": str(project)})["project"]
            result = app.action(
                "verify", {"attempt": attempt["attempt"], "allow_failed": False}, handle
            )
            raw = app.request("/api/reports/" + result["report"] + "/report.json")
            self.assertEqual(raw, (self.root / "report/report.json").read_bytes())
            app.restart()
            app.action("refresh", {}, handle)
            self.assertEqual(
                app.state()["projects"][0]["info"]["head"],
                self.call("info", "--project", project)["head"],
            )
        self.assertEqual(store.inventory(project, store.Budget()), before)


if __name__ == "__main__":
    unittest.main()
