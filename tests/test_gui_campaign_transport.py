"""Same-origin campaign routes share the existing live GUI process owner."""

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
from experiments.gui.service import ROOT, Service


class SlowCampaignService(Service):
    def commands(self, job, configuration, archive):
        commands = super().commands(job, configuration, archive)
        if job["operation"].startswith("campaign_"):
            return [([sys.executable, "-B", "-S", "-c", "import time; time.sleep(60)"], 60)]
        return commands


class CampaignTransportTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.workspace = Path(self.temporary.name).resolve(strict=True)
        for source in ("model.py", "model.json"):
            original = ROOT / "experiments/m4/causal_secretion/example_model"
            (self.workspace / source).write_bytes(
                original.with_suffix(Path(source).suffix).read_bytes()
            )
        self.service = SlowCampaignService(self.workspace)
        study = self.service.defaults()
        study.update(
            sources=[
                {"id": name, "model": "model.py", "declaration": "model.json"}
                for name in ("left", "right")
            ],
            scenarios=["fasting"],
        )
        self.study = self.service.configure(study)
        self.body = {
            "cells": [{"id": "fasting", "configuration_id": self.study["id"]}],
            "repeats": 1,
            "timeout_seconds": 1800,
        }
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

    def test_campaign_configuration_and_reads_require_session_admission(self):
        self.assertEqual(self.request("GET", "campaigns", token=False)[0], 403)
        self.assertEqual(
            self.request("POST", "campaigns/configurations", self.body, origin=False)[0], 403
        )
        code, saved = self.request("POST", "campaigns/configurations", self.body)
        self.assertEqual(code, 201, saved)
        self.assertFalse(saved["ready"])
        self.assertEqual(saved["planned_slots"], 1)
        self.assertEqual(saved["planned_source_scenarios"], 2)
        code, restored = self.request("GET", "campaigns/configurations/" + saved["id"])
        self.assertEqual(code, 200, restored)
        self.assertEqual(restored, saved)
        self.assertEqual(self.request("GET", "campaigns")[1], {"campaigns": []})
        self.assertEqual(
            self.request("POST", "campaigns/configurations/" + saved["id"] + "/run", {})[0], 400
        )
        self.assertIsNone(self.service.active)

    def test_campaign_check_shares_global_owner_and_observed_cancellation(self):
        code, saved = self.request("POST", "campaigns/configurations", self.body)
        self.assertEqual(code, 201, saved)
        path = "campaigns/configurations/" + saved["id"] + "/check"
        self.assertEqual(self.request("POST", path, {"command": "arbitrary"})[0], 400)
        code, job = self.request("POST", path, {})
        self.assertEqual(code, 202, job)
        deadline = time.monotonic() + 5
        while self.service.get_job(job["id"])["pid"] is None:
            self.assertLess(time.monotonic(), deadline)
            time.sleep(0.01)
        pid = self.service.get_job(job["id"])["pid"]
        self.assertEqual(self.request("POST", "campaigns/configurations", self.body)[0], 400)
        self.assertEqual(
            self.request("POST", "configurations/" + self.study["id"] + "/check", {})[0], 400
        )
        self.assertEqual(self.request("POST", "jobs/" + job["id"] + "/cancel", {})[0], 202)
        self.service.thread.join(5)
        self.assertFalse(self.service.thread.is_alive())
        finished = self.service.get_job(job["id"])
        self.assertIn(finished["state"], {"cancelled", "failed"})
        self.assertFalse(finished.get("remaining_owned_processes"))
        self.assertIsNone(self.service.active)
        with self.assertRaises(ProcessLookupError):
            os.kill(pid, 0)


if __name__ == "__main__":
    unittest.main()
