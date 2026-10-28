"""M3 HTTP admission and live owned cancellation share the existing GUI lock."""

import http.client
import json
import os
import sys
import tempfile
import threading
import time
import unittest
from pathlib import Path

from experiments.gui.server import Server
from experiments.gui.service import Service
from experiments.m3.comparison.fixtures import fixture


class SlowM3Service(Service):
    def commands(self, job, configuration, archive):
        commands = super().commands(job, configuration, archive)
        if job["operation"].startswith("m3_"):
            return [([sys.executable, "-B", "-S", "-c", "import time; time.sleep(60)"], 60)]
        return commands


class M3TransportTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name).resolve(strict=True)
        fixture(self.root / "fixture")
        self.service = SlowM3Service(self.root, python=sys.executable)
        self.server = Server(self.service)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.origin = f"http://127.0.0.1:{self.server.server_port}"

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
        connection = http.client.HTTPConnection("127.0.0.1", self.server.server_port, timeout=5)
        try:
            connection.request(method, "/api/v1/" + path, body, headers)
            response = connection.getresponse()
            return response.status, json.loads(response.read())
        finally:
            connection.close()

    def configure(self):
        _, bootstrap = self.request("GET", "m3/bootstrap")
        root = bootstrap["roots"][0]["id"]
        status, inspected = self.request(
            "POST", "m3/inspect", {"root_id": root, "path": "fixture/comparison.json"}
        )
        self.assertEqual(status, 201, inspected)
        status, config = self.request(
            "POST",
            "m3/configurations",
            {
                "input_id": inspected["id"],
                "task": "m3-compare",
                "candidate_ids": [item["id"] for item in inspected["candidates"]],
                "timeout_seconds": 120,
            },
        )
        self.assertEqual(status, 201, config)
        return config

    def test_admission_fixed_routes_and_configuration_metadata(self):
        self.assertEqual(self.request("GET", "m3/bootstrap", token=False)[0], 403)
        self.assertEqual(self.request("POST", "m3/fixture", {}, origin=False)[0], 403)
        self.assertEqual(self.request("POST", "m3/fixture", {"command": "arbitrary"})[0], 400)
        self.assertEqual(
            self.request("POST", "m3/inspect", {"root_id": "unknown", "path": "../file.json"})[0],
            400,
        )
        config = self.configure()
        self.assertFalse(config["ready"])
        self.assertEqual(self.request("GET", "m3/configurations")[1], {"configurations": [config]})
        self.assertEqual(self.request("GET", "m3/configurations/" + config["id"])[1], config)
        self.assertEqual(self.request("GET", "m3/entries")[1], {"entries": []})
        self.assertEqual(
            self.request("POST", "m3/configurations/" + config["id"] + "/run", {})[0], 400
        )
        self.assertIsNone(self.service.active)

    def test_m3_check_owns_global_slot_and_cancellation_is_observed(self):
        config = self.configure()
        path = "m3/configurations/" + config["id"] + "/check"
        self.assertEqual(self.request("POST", path, {"script": "arbitrary"})[0], 400)
        status, job = self.request("POST", path, {})
        self.assertEqual(status, 202, job)
        self.assertEqual(job["task"], "m3-compare")
        self.assertEqual(job["m3_configuration_id"], config["id"])
        deadline = time.monotonic() + 5
        while self.service.get_job(job["id"])["pid"] is None:
            self.assertLess(time.monotonic(), deadline)
            time.sleep(0.01)
        pid = self.service.get_job(job["id"])["pid"]
        self.assertEqual(self.request("POST", "m3/fixture", {})[0], 400)
        self.assertEqual(self.request("POST", "configurations/unknown/check", {})[0], 400)
        self.assertEqual(self.request("POST", "campaigns/configurations", {})[0], 400)
        self.assertEqual(self.request("POST", "durable/register", {})[0], 400)
        status, _ = self.request("POST", "jobs/" + job["id"] + "/cancel", {})
        self.assertEqual(status, 202)
        self.service.thread.join(5)
        self.assertFalse(self.service.thread.is_alive())
        finished = self.service.get_job(job["id"])
        self.assertEqual(finished["state"], "cancelled", finished)
        self.assertFalse(finished.get("remaining_owned_processes"))
        self.assertFalse(finished["cleanup_forced"])
        self.assertIsNone(self.service.active)
        with self.assertRaises(ProcessLookupError):
            os.kill(pid, 0)
        self.assertFalse(self.service.m3.get_configuration(config["id"])["ready"])

    def test_fixture_is_owned_and_cannot_be_dispatched_during_another_operation(self):
        status, job = self.request("POST", "m3/fixture", {})
        self.assertEqual(status, 202, job)
        self.assertEqual(job["operation"], "m3_fixture")
        self.assertEqual(self.request("POST", "m3/fixture", {})[0], 400)
        self.assertEqual(self.request("POST", "jobs/" + job["id"] + "/cancel", {})[0], 202)
        self.service.thread.join(5)
        self.assertFalse(self.service.thread.is_alive())
        self.assertEqual(self.service.get_job(job["id"])["state"], "cancelled")
        self.assertEqual(self.service.m3.input_list(), [])


if __name__ == "__main__":
    unittest.main()
