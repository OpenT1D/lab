"""Actual M3 library HTTP jobs and task-specific native report downloads."""

import http.client
import json
import shutil
import subprocess
import tempfile
import threading
import time
import unittest
from pathlib import Path

from experiments.gui.server import Server
from experiments.gui.service import Service, encode, inventory
from experiments.m3.comparison.study import run_study as compare
from experiments.m3.researcher.study import run_study as forecast
from tests.test_gui_m3_library import FAILURE
from tests.test_m3_comparison_study import configuration as comparison_config
from tests.test_m3_researcher_study import configuration as forecast_config


class M3LibraryTransportTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.base = Path(self.temporary.name).resolve()
        self.workspace = self.base / "workspace"
        self.external = self.base / "external"
        self.workspace.mkdir()
        self.external.mkdir()
        repository = Path(__file__).resolve().parents[1]
        # Owned workers execute the current trusted checkout, never the archive.
        # Supply its reader closure in this isolated workspace, with no runtimes.
        shutil.copytree(
            repository / "experiments",
            self.workspace / "experiments",
            ignore=shutil.ignore_patterns(".venv", "__pycache__", "results"),
        )
        shutil.copytree(repository / "docs/research", self.workspace / "docs/research")
        shutil.copyfile(repository / "uv.lock", self.workspace / "uv.lock")
        subprocess.run(["git", "init", "-q"], cwd=self.workspace, check=True)
        subprocess.run(
            [
                "git",
                "-c",
                "user.email=fixture@example.invalid",
                "-c",
                "user.name=Fixture",
                "commit",
                "--allow-empty",
                "-qm",
                "Trusted reader boundary fixture",
            ],
            cwd=self.workspace,
            check=True,
        )
        self.service = Service(self.workspace, archive_roots=(self.external,))
        self.server = Server(self.service)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.origin = f"http://127.0.0.1:{self.server.server_port}"
        self.root_id = next(
            item["id"]
            for item in self.service.library.roots()
            if item["directory"] == str(self.external)
        )

    def tearDown(self):
        self.server.shutdown()
        self.service.close()
        self.server.server_close()
        self.thread.join(2)
        self.temporary.cleanup()

    def request(self, method, path, body=None, *, token=True, origin=True):
        headers = {}
        if token:
            headers["X-OpenT1D-Token"] = self.server.token
        if origin:
            headers["Origin"] = self.origin
        if body is not None:
            headers["Content-Type"] = "application/json"
            body = json.dumps(body)
        connection = http.client.HTTPConnection("127.0.0.1", self.server.server_port, timeout=10)
        try:
            connection.request(method, "/api/v1/" + path, body, headers)
            response = connection.getresponse()
            raw = response.read()
            return response.status, raw
        finally:
            connection.close()

    def terminal(self, identity):
        deadline = time.monotonic() + 20
        while True:
            code, raw = self.request("GET", "jobs/" + identity)
            self.assertEqual(code, 200)
            job = json.loads(raw)
            if job["state"] in {"completed", "cancelled", "failed"}:
                self.assertFalse(job.get("remaining_owned_processes"))
                return job
            self.assertLess(time.monotonic(), deadline)
            time.sleep(0.02)

    def test_actual_owned_m3_http_jobs_bind_task_and_native_bytes_without_svg(self):
        for task in ("m3-forecast", "m3-compare"):
            with self.subTest(task=task):
                archive = self.external / task
                if task == "m3-forecast":
                    config, _ = forecast_config(self.base / "forecast-prepare", days=2)
                    native = forecast(config, archive, timeout=10)
                else:
                    config, _ = comparison_config(
                        self.base / "comparison-prepare", second_source=FAILURE
                    )
                    native = compare(config, archive)
                shutil.rmtree(config.parent)
                before = inventory(archive, files=True)
                body = {"root_id": self.root_id, "path": task, "task": task}
                code, raw = self.request("POST", "library/entries", body)
                self.assertEqual(code, 202, raw)
                indexed = json.loads(raw)
                self.assertEqual(indexed["task"], task)
                terminal = self.terminal(indexed["id"])
                self.assertEqual(terminal["state"], "completed", terminal)
                identity = indexed["request"]["entry"]["id"]
                code, raw = self.request("POST", "library/entries/" + identity + "/verify", {})
                self.assertEqual(code, 202, raw)
                verifying = json.loads(raw)
                self.assertEqual(verifying["task"], task)
                terminal = self.terminal(verifying["id"])
                self.assertEqual(terminal["state"], "completed", terminal)
                self.assertEqual(terminal["verification"], "native_reader_verified")
                self.service.load_journals()
                restored = self.service.get_job(verifying["id"])
                self.assertEqual(restored["task"], task)
                self.assertEqual(restored["verification"], "recorded_verification")
                prefix = "library/entries/" + identity
                code, raw = self.request("GET", prefix + "/report")
                self.assertEqual(code, 200, raw)
                view = json.loads(raw)
                self.assertEqual(view["task"], task)
                self.assertEqual(view["native_report"], native)
                self.assertEqual(
                    view["report_completeness"],
                    "complete" if task == "m3-forecast" else "incomplete",
                )
                for name in ("report.json", "report.md"):
                    code, raw = self.request("GET", prefix + "/artifacts/" + name)
                    self.assertEqual(code, 200, raw)
                    self.assertEqual(raw, (archive / name).read_bytes())
                code, raw = self.request("GET", prefix + "/artifacts/figure.svg")
                self.assertEqual(code, 400, raw)
                self.assertIn("registered task", json.loads(raw)["error"])
                self.assertEqual(inventory(archive, files=True), before)

    def test_m3_pointer_mutations_require_existing_session_and_safe_root(self):
        archive = self.external / "raw"
        archive.mkdir()
        (archive / "partial.txt").write_text("retained interrupted raw evidence")
        body = {"root_id": self.root_id, "path": "raw", "task": "m3-compare"}
        for headers in ({"token": False}, {"origin": False}):
            code, _ = self.request("POST", "library/entries", body, **headers)
            self.assertEqual(code, 403)
        code, _ = self.request("POST", "library/entries", {**body, "path": "../workspace"})
        self.assertEqual(code, 400)
        self.assertIsNone(self.service.active)
        code, raw = self.request("POST", "library/entries", body)
        self.assertEqual(code, 202, raw)
        indexed = json.loads(raw)
        self.assertEqual(indexed["task"], "m3-compare")
        terminal = self.terminal(indexed["id"])
        self.assertEqual(terminal["state"], "completed", terminal)
        identity = indexed["request"]["entry"]["id"]
        code, raw = self.request("GET", "library/entries/" + identity)
        self.assertEqual(code, 200)
        self.assertEqual(json.loads(raw)["metadata_status"], "unavailable")
        self.assertFalse(json.loads(raw)["can_view_report"])
        for suffix in (
            "report",
            "artifacts/report.json",
            "artifacts/report.md",
            "artifacts/figure.svg",
        ):
            code, _ = self.request("GET", "library/entries/" + identity + "/" + suffix)
            self.assertEqual(code, 400)

    def test_reload_normalizes_legacy_task_and_refuses_changed_nonlegacy_bindings(self):
        archive = self.external / "raw"
        archive.mkdir()
        request = self.service.library.add(
            {"root_id": self.root_id, "path": "raw", "task": "m3-compare"}
        )
        cases = (
            ("legacy", "m4-study-secure", "library_index", request, True),
            ("changed-task", "m3-forecast", "library_index", request, False),
            ("changed-operation", "m3-compare", "library_verify", request, False),
        )
        for index, (name, task, operation, frozen, accepted) in enumerate(cases):
            identity = "job-" + str(index + 100).zfill(32)
            directory = self.service.data / identity
            directory.mkdir()
            job = {
                "schema": "opent1d.gui-job/1",
                "id": identity,
                "task": task,
                "operation": operation,
                "request": frozen,
                "state": "completed",
                "verification": "native_reader_verified",
                "commands": [],
                "result": {},
                "pid": 99999999,
            }
            (directory / "job.json").write_bytes(encode(job))
            self.service.load_journals()
            with self.subTest(name=name):
                self.assertEqual(identity in self.service.jobs, accepted)
                if accepted:
                    self.assertEqual(self.service.jobs[identity]["task"], "m3-compare")
                    self.assertEqual(
                        self.service.jobs[identity]["verification"], "recorded_verification"
                    )
        self.assertIsNone(self.service.active)


if __name__ == "__main__":
    unittest.main()
