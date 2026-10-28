"""Real M5 HTTP jobs, bounded ownership and original native report downloads."""

import http.client
import json
import shutil
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from pathlib import Path
from unittest.mock import patch

from experiments.gui.server import Server
from experiments.gui.service import Service, encode, inventory
from tests import test_gui_m5_library as m5_tests


class M5LibraryTransportTests(m5_tests.M5Fixtures, unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.base = Path(self.temporary.name).resolve()
        self.workspace, self.external = self.base / "workspace", self.base / "external"
        self.workspace.mkdir()
        self.external.mkdir()
        for name in self.cases:
            shutil.copytree(self.fixture_root / name, self.external / name)
        repository = Path(__file__).resolve().parents[1]
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
                "Trusted M5 reader closure",
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
            return response.status, response.read()
        finally:
            connection.close()

    def terminal(self, identity):
        deadline = time.monotonic() + 20
        while True:
            code, raw = self.request("GET", "jobs/" + identity)
            self.assertEqual(code, 200, raw)
            job = json.loads(raw)
            if job["state"] in {"completed", "cancelled", "failed"}:
                self.assertFalse(job.get("remaining_owned_processes"), job)
                return job
            self.assertLess(time.monotonic(), deadline)
            time.sleep(0.02)

    def index(self, name="complete"):
        code, raw = self.request(
            "POST",
            "library/entries",
            {"root_id": self.root_id, "path": name, "task": "m5-prognosis"},
        )
        self.assertEqual(code, 202, raw)
        job = json.loads(raw)
        self.assertEqual(job["task"], "m5-prognosis")
        self.assertEqual(self.terminal(job["id"])["state"], "completed")
        return job["request"]["entry"]["id"]

    def verify(self, identity):
        code, raw = self.request("POST", "library/entries/" + identity + "/verify", {})
        self.assertEqual(code, 202, raw)
        job = json.loads(raw)
        self.assertEqual(job["task"], "m5-prognosis")
        return self.terminal(job["id"])

    def test_real_cli_worker_http_native_parity_all_four_cases_and_downloads(self):
        for name, native in self.cases.items():
            with self.subTest(name=name):
                archive = self.external / name
                before = inventory(archive, files=True)
                cli = subprocess.run(
                    [
                        sys.executable,
                        "-B",
                        "-E",
                        "-s",
                        "-S",
                        "-m",
                        "experiments.m5.researcher_workflow.run",
                        "reconstruct",
                        str(archive),
                    ],
                    cwd=self.workspace,
                    capture_output=True,
                    check=True,
                )
                self.assertEqual(json.loads(cli.stdout), native)
                identity = self.index(name)
                terminal = self.verify(identity)
                self.assertEqual(terminal["state"], "completed", terminal)
                self.assertEqual(terminal["verification"], "native_reader_verified")
                prefix = "library/entries/" + identity
                code, raw = self.request("GET", prefix + "/report")
                self.assertEqual(code, 200, raw)
                view = json.loads(raw)
                self.assertEqual(view["task"], "m5-prognosis")
                self.assertEqual(view["native_report"], native)
                self.assertEqual(
                    view["report_completeness"], "complete" if name == "complete" else "incomplete"
                )
                self.assertEqual(
                    view["model_declaration"], json.loads((archive / "model.json").read_bytes())
                )
                code, raw = self.request("GET", prefix)
                self.assertEqual(code, 200, raw)
                self.assertEqual(
                    json.loads(raw)["model_declaration_sha256"], view["model_declaration_sha256"]
                )
                for artifact in ("report.json", "report.md"):
                    code, raw = self.request("GET", prefix + "/artifacts/" + artifact)
                    self.assertEqual(code, 200, raw)
                    self.assertEqual(raw, (archive / artifact).read_bytes())
                for artifact in ("figure.svg", "model.json", "source-run.py"):
                    code, _ = self.request("GET", prefix + "/artifacts/" + artifact)
                    self.assertEqual(code, 400)
                self.assertEqual(before, inventory(archive, files=True))
                self.assertFalse(self.marker.exists(), "Verification executed retained model")

    def test_http_refuses_missing_reports_unsealed_and_wrong_session_or_root(self):
        for name, missing in (("missing", "report.json"), ("unsealed", "manifest.json")):
            shutil.copytree(self.fixture_root / "complete", self.external / name)
            (self.external / name / missing).unlink()
            identity = self.index(name)
            terminal = self.verify(identity)
            self.assertEqual(terminal["state"], "failed", terminal)
            prefix = "library/entries/" + identity
            code, _ = self.request("GET", prefix + "/report")
            self.assertEqual(code, 400)
            code, raw = self.request("GET", prefix)
            self.assertEqual(code, 200)
            self.assertFalse(json.loads(raw)["can_view_report"])
            self.assertNotIn("model_declaration", json.loads(raw))
        body = {"root_id": self.root_id, "path": "complete", "task": "m5-prognosis"}
        for headers in ({"token": False}, {"origin": False}):
            code, _ = self.request("POST", "library/entries", body, **headers)
            self.assertEqual(code, 403)
        code, _ = self.request("POST", "library/entries", {**body, "path": "../workspace"})
        self.assertEqual(code, 400)

    def test_http_declaration_and_report_tamper_withdraw_snapshot_and_downloads(self):
        for name in ("declaration", "report.json", "report.md"):
            with self.subTest(name=name):
                identity = self.index()
                self.assertEqual(self.verify(identity)["state"], "completed")
                entry = self.service.library.registered[identity]
                if name == "declaration":
                    receipt = self.service.data / entry["verified_job"] / "worker-result.json"
                    result = json.loads(receipt.read_bytes())
                    result["model_declaration"]["rights_basis"] = "changed projection"
                    receipt.write_bytes(encode(result))
                else:
                    self.service.library.report_file(identity, name).write_text("changed report")
                prefix = "library/entries/" + identity
                code, _ = self.request(
                    "GET",
                    prefix + "/artifacts/" + (name if name != "declaration" else "report.json"),
                )
                self.assertEqual(code, 400)
                code, raw = self.request("GET", prefix)
                self.assertEqual(code, 200)
                self.assertFalse(json.loads(raw)["can_view_report"])
                self.assertNotIn("model_declaration", json.loads(raw))
                for suffix in ("/report", "/artifacts/report.json", "/artifacts/report.md"):
                    code, _ = self.request("GET", prefix + suffix)
                    self.assertEqual(code, 400)

    def test_actual_owned_cancellation_deadline_and_shared_exclusion(self):
        identity = self.index()
        # Slow only the trusted GUI coordinator, never archived/native scientific code.
        worker = self.workspace / "experiments/gui/library_worker.py"
        source = worker.read_text()
        worker.write_text(
            source.replace(
                "    result = execute(read_json(args.request), output)",
                "    request = read_json(args.request)\n"
                '    if request["operation"] == "library_verify":\n'
                "        import time\n"
                '        (output / "paused").touch()\n'
                "        time.sleep(30)\n"
                "    result = execute(request, output)",
            )
        )
        for stopping in ("cancel", "deadline"):
            with self.subTest(stopping=stopping):
                commands = self.service.library.commands

                def limited(job):
                    return [(argv, 0.5) for argv, _ in commands(job)]

                with patch.object(
                    self.service.library,
                    "commands",
                    side_effect=limited if stopping == "deadline" else commands,
                ):
                    code, raw = self.request("POST", "library/entries/" + identity + "/verify", {})
                    self.assertEqual(code, 202, raw)
                    job = json.loads(raw)
                    deadline = time.monotonic() + 10
                    paused = self.service.data / job["id"] / "paused"
                    while not paused.exists():
                        self.assertLess(time.monotonic(), deadline)
                        time.sleep(0.02)
                    code, raw = self.request("POST", "library/entries/" + identity + "/verify", {})
                    self.assertEqual(code, 400, raw)
                    self.assertIn("active operation", json.loads(raw)["error"])
                    if stopping == "cancel":
                        code, raw = self.request("POST", "jobs/" + job["id"] + "/cancel", {})
                        self.assertEqual(code, 202, raw)
                    terminal = self.terminal(job["id"])
                self.assertEqual(
                    terminal["state"], "cancelled" if stopping == "cancel" else "failed", terminal
                )
                if stopping == "deadline":
                    self.assertIn("deadline", terminal["error"])
                self.assertIsNone(self.service.active)
                self.assertFalse(self.service.library.get(identity)["can_view_report"])
        worker.write_text(source)
        self.assertEqual(self.verify(identity)["state"], "completed")


if __name__ == "__main__":
    unittest.main()
