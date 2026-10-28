"""Real HTTP task flows with a separate workspace and explicit checkout interpreter."""

import copy
import http.client
import json
import os
import sys
import tempfile
import threading
import unittest
from pathlib import Path
from unittest.mock import patch

from experiments.gui.server import Server
from experiments.gui.service import ROOT, Service, inventory


class HTTPTaskSmoke(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix="opent1d-public-smoke-")
        self.addCleanup(temporary.cleanup)
        self.workspace = Path(temporary.name).resolve()
        self.service = self.server = self.thread = None
        if os.name == "nt":
            from experiments.gui.windows_process import WindowsOwnership
            from tests.windows_job_probe import inspect_job_processes

            original = WindowsOwnership.observe

            def observe(owner):
                live = original(owner)
                if live and owner.process.poll() is not None:
                    frame = sys._getframe(1)
                    row = inspect_job_processes(owner.process, list(live))
                    row["caller"] = f"{Path(frame.f_code.co_filename).name}:{frame.f_lineno}"
                    print(
                        "OPENT1D_WINDOWS_EXIT_INVENTORY=" + json.dumps(row, sort_keys=True),
                        flush=True,
                    )
                return live

            observer = patch.object(WindowsOwnership, "observe", observe)
            observer.start()
            self.addCleanup(observer.stop)
        self.addCleanup(self.stop)
        self.start()

    def start(self):
        self.service = Service(self.workspace, source_root=ROOT, python=sys.executable)
        self.server = Server(self.service)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()

    def stop(self):
        service, server, thread = self.service, self.server, self.thread
        self.service = self.server = self.thread = None
        try:
            if server is not None:
                server.shutdown()
        finally:
            try:
                if service is not None:
                    service.close()
                    self.assertIsNone(service.active)
                    self.assertIsNone(service.process)
            finally:
                if server is not None:
                    server.server_close()
                if thread is not None:
                    thread.join(2)
                    self.assertFalse(thread.is_alive())

    def request(self, method, route, body=None, *, raw=False):
        connection = http.client.HTTPConnection("127.0.0.1", self.server.server_port, timeout=10)
        headers = {
            "X-OpenT1D-Token": self.server.token,
            "Origin": f"http://127.0.0.1:{self.server.server_port}",
        }
        if body is not None:
            headers["Content-Type"] = "application/json"
            body = json.dumps(body)
        try:
            connection.request(method, "/api/v1/" + route, body, headers)
            response = connection.getresponse()
            payload = response.read()
            return response.status, payload if raw else json.loads(payload)
        finally:
            connection.close()

    def wait(self, job):
        self.service.thread.join(30)
        final = self.service.get_job(job["id"])
        self.assertFalse(self.service.thread.is_alive(), final)
        self.assertEqual(final["state"], "completed", final)
        self.assertFalse(final.get("remaining_owned_processes"), final)
        self.assertFalse(final["cleanup_forced"], final)
        return final

    def flow(self, route, case, task, entry_key):
        status, job = self.request("POST", route + "/example", {"case": case})
        self.assertEqual(status, 202, job)
        prepared = self.wait(job)
        paths = prepared["result"]["input_paths"]
        status, inspected = self.request("POST", route + "/inspect", paths)
        self.assertEqual(status, 201, inspected)
        settings = copy.deepcopy(inspected["settings"])
        settings["uncertainty"]["draws"] = 32
        body = {**paths, "settings": settings, "input_sha256": inspected["input_sha256"]}
        if route == "observations":
            body = {key: body[key] for key in ("package", "csv", "settings", "input_sha256")}
        status, config = self.request("POST", route + "/configurations", body)
        self.assertEqual(status, 201, config)
        prefix = route + "/configurations/" + config["id"]
        status, job = self.request("POST", prefix + "/freeze", {})
        self.assertEqual(status, 202, job)
        self.wait(job)
        status, job = self.request("POST", prefix + "/run", {})
        self.assertEqual(status, 202, job)
        completed = self.wait(job)
        identity = completed[entry_key]
        entry = route + "/entries/" + identity
        status, wrapper = self.request("GET", entry + "/report")
        self.assertEqual(status, 200, wrapper)
        report = wrapper["native_report"]
        self.assertEqual(report["task"], task)
        self.assertEqual(report["kind"], "synthetic")
        self.assertFalse(report["human_evaluation"])
        self.assertEqual(report["execution_status"], "completed")
        self.assertTrue(report["coverage"]["complete_cohort"])
        archive = self.service.data / route / "archives" / identity / "archive"
        before = inventory(archive)
        saved = {}
        for name in ("report.json", "report.md"):
            status, saved[name] = self.request("GET", entry + "/artifacts/" + name, raw=True)
            self.assertEqual(status, 200)
            self.assertEqual(saved[name], (archive / name).read_bytes())
        self.stop()
        self.start()
        self.assertIsNone(self.service.active)
        status, job = self.request("POST", entry + "/reconstruct", {})
        self.assertEqual(status, 202, job)
        self.wait(job)
        status, wrapper = self.request("GET", entry + "/report")
        self.assertEqual(status, 200, wrapper)
        self.assertEqual(wrapper["native_report"], report)
        self.assertEqual(wrapper["verification"], "native_reader_verified")
        for name in saved:
            status, raw = self.request("GET", entry + "/artifacts/" + name, raw=True)
            self.assertEqual(status, 200)
            self.assertEqual(raw, saved[name])
        self.assertEqual(inventory(archive), before)
        self.assertFalse((self.workspace / ".venv").exists())

    def repeated_flow(self, route, case, task, entry_key):
        repetitions = 3 if os.name == "nt" else 1
        for repetition in range(repetitions):
            with self.subTest(task=task, repetition=repetition):
                if repetition:
                    temporary = tempfile.TemporaryDirectory(prefix="opent1d-public-smoke-")
                    self.addCleanup(temporary.cleanup)
                    self.workspace = Path(temporary.name).resolve()
                    self.start()
                if os.name == "nt":
                    print(
                        "OPENT1D_WINDOWS_HTTP_PROBE="
                        + json.dumps({"task": task, "repetition": repetition}),
                        flush=True,
                    )
                try:
                    self.flow(route, case, task, entry_key)
                finally:
                    self.stop()

    def test_paired_task_http_and_reopen(self):
        self.repeated_flow("observations", "increase", "mmtt-sensitivity", "observation_entry_id")

    def test_sampling_task_http_and_reopen(self):
        self.repeated_flow("sampling", "information-loss", "mmtt-sampling", "sampling_entry_id")
