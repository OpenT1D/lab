"""Real installed connected metadata/failure/replay, without native setup in root CI."""

import hashlib
import http.client
import json
import os
import subprocess
import sys
import unittest
from pathlib import Path

from tests import test_installed_sampling as installed
from tests import test_workbench_installed as editable


@unittest.skipUnless(
    os.name == "posix" and sys.version_info[:2] == (3, 12), "POSIX CPython3.12 installed SDK"
)
class InstalledConnectedStudies(unittest.TestCase):
    setUpClass = classmethod(installed.InstalledSampling.setUpClass.__func__)
    setUp = installed.InstalledSampling.setUp
    call = installed.InstalledSampling.call
    server = editable.EditableWorkbench.server

    def python(self, code):
        result = subprocess.run(
            [str(self.cli.parent / "python"), "-I", "-c", code],
            cwd=self.root,
            env=self.env,
            capture_output=True,
            text=True,
            timeout=120,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        return json.loads(result.stdout)

    def test_gui_cli_python_failed_forward_keeps_all_rows_and_old_prefix(self):
        with self.server() as app:
            handle = app.action("create", {"name": "Invented connected study"})["project"]
            frozen = app.action(
                "study_freeze",
                {
                    "name": "Known input | preserved chain",
                    "question": "Do matched inverse assumptions recover this synthetic input?",
                    "forward_plan": None,
                    "observation_case": "complete",
                },
                handle,
            )
            identity, plan = frozen["study"], frozen["forward_plan"]
            path = Path(next(p for p in app.state()["projects"] if p["id"] == handle)["path"])
            value = app.action("study_open", {"study": identity, "at": None}, handle)
            self.assertEqual(value["planned"]["truth_endpoint_rows"], 72)
            self.assertEqual(
                value["next"], {"action": "run", "plan": plan, "reason": "Run fixed forward plan"}
            )
            self.assertFalse(
                self.call("check", "--project", path, "--plan", plan)["runtimes_ready"]
            )
            original_head = (path / "HEAD.json").read_bytes()
            verified = app.action("study_verify", {"study": identity, "at": None}, handle)
            self.assertEqual((path / "HEAD.json").read_bytes(), original_head)
            pointer, tip = verified["report"], verified["snapshot"]["tip"]
            initial = app.request(f"/api/reports/{pointer}/report.json")
            csv = app.request(f"/api/reports/{pointer}/study.csv")
            report = json.loads(initial)
            self.assertEqual(report["coverage"]["planned_rows"], 72)
            self.assertEqual(report["coverage"]["unavailable_point_rows"], 72)
            self.assertTrue(all(row["value"] is None for row in report["rows"]))
            self.assertEqual(
                hashlib.sha256(csv).hexdigest(), verified["report_sha256"]["study.csv"]
            )
            self.assertEqual(len(csv.splitlines()), 73)
            connection = http.client.HTTPConnection("127.0.0.1", app.port, timeout=30)
            try:
                connection.request(
                    "GET",
                    f"/api/reports/{pointer}/study.csv",
                    headers={"X-OpenT1D-Token": app.token},
                )
                response = connection.getresponse()
                self.assertEqual(response.status, 200)
                self.assertEqual(response.getheader("Content-Type"), "text/csv; charset=utf-8")
                self.assertEqual(
                    response.getheader("Content-Disposition"), 'attachment; filename="study.csv"'
                )
                self.assertEqual(response.read(), csv)
            finally:
                connection.close()
            cli = self.call(
                "reconstruct-study",
                "--project",
                path,
                "--study",
                identity,
                "--at",
                tip,
                "--output",
                self.root / "cli-initial",
            )
            self.assertEqual(cli["report_sha256"], verified["report_sha256"])
            outcome = app.action("run", {"plan": plan, "retry_of": None}, handle)
            self.assertEqual(outcome["result"]["payload"], "forensic")
            self.assertEqual(outcome["result"]["completeness"], "incomplete")
            current = app.action("study_open", {"study": identity, "at": None}, handle)
            self.assertEqual(current["next"]["action"], "blocked")
            self.assertIsNone(current["sampling_plan"])
            self.assertEqual(current["stages"]["inverse_sampling"]["status"], "unmaterialized")
            refused = self.call(
                "materialize-study", "--project", path, "--study", identity, expected=2
            )
            self.assertIn("incomplete", refused["error"])
            failed = app.action("study_verify", {"study": identity, "at": None}, handle)
            failed_raw = app.request(f"/api/reports/{failed['report']}/report.json")
            self.assertEqual(json.loads(failed_raw)["coverage"]["unavailable_point_rows"], 72)
            app.restart()
            moved = self.root / "moved"
            copied = app.action("relocate", {"output": str(moved)}, handle)["project"]
            path.rename(path.with_name("original-unavailable"))
            replay = app.action("study_verify", {"study": identity, "at": tip}, copied)
            self.assertEqual(replay["report_sha256"], verified["report_sha256"])
            self.assertEqual(app.request(f"/api/reports/{replay['report']}/report.json"), initial)
            result = self.python(
                "import opent1d_lab as lab,json;print(json.dumps(lab.Project("
                + repr(str(moved))
                + ").study("
                + repr(identity)
                + ",at="
                + repr(tip)
                + ")))"
            )
            self.assertEqual(result["stages"]["forward"]["status"], "unattempted")
            self.assertEqual(len(self.call("info", "--project", moved)["plans"]), 1)

    def test_shared_unused_forward_plan_is_frozen_before_execution(self):
        path = self.root / "project"
        self.call("create", "--project", path, "--name", "Two prospectively declared controls")
        first = self.call(
            "freeze-study",
            "--project",
            path,
            "--name",
            "Complete",
            "--question",
            "Known source recovery",
        )
        second = self.call(
            "freeze-study",
            "--project",
            path,
            "--name",
            "Missing observation",
            "--question",
            "Retain declared failure",
            "--forward-plan",
            first["forward_plan"],
            "--observation-case",
            "missing-evaluation",
        )
        self.assertNotEqual(first["study"], second["study"])
        info = self.call("info", "--project", path)
        self.assertEqual(len(info["plans"]), 1)
        self.assertEqual(len(info["studies"]), 2)
        head = (path / "HEAD.json").read_bytes()
        self.call(
            "freeze-study", "--project", path, "--name", "", "--question", "Invalid", expected=2
        )
        self.assertEqual((path / "HEAD.json").read_bytes(), head)
        self.call("run", "--project", path, "--plan", first["forward_plan"], expected=1)
        head = (path / "HEAD.json").read_bytes()
        refused = self.call(
            "freeze-study",
            "--project",
            path,
            "--name",
            "Retrospective",
            "--question",
            "Must refuse",
            "--forward-plan",
            first["forward_plan"],
            expected=2,
        )
        self.assertIn("before forward execution", refused["error"])
        self.assertEqual((path / "HEAD.json").read_bytes(), head)
        for identity in (first["study"], second["study"]):
            self.assertEqual(
                self.call("study", "--project", path, "--study", identity)["next"]["action"],
                "blocked",
            )


if __name__ == "__main__":
    unittest.main()
