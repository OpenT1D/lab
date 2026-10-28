"""Actual HTTP admission and global ownership for external read-only archives."""

import http.client
import json
import sys
import tempfile
import threading
import time
import unittest
from pathlib import Path
from unittest.mock import patch

from experiments.gui.server import Server
from experiments.gui.service import Service


class SlowLibraryService(Service):
    def commands(self, job, configuration, archive):
        if job["operation"].startswith("library_"):
            return [([sys.executable, "-B", "-S", "-c", "import time; time.sleep(60)"], 60)]
        return super().commands(job, configuration, archive)


class ArchiveTransportTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.folder = Path(self.temporary.name).resolve(strict=True)
        self.workspace = self.folder / "workspace"
        self.external = self.folder / "external"
        self.workspace.mkdir()
        self.external.mkdir()
        (self.external / "archive").mkdir()
        (self.external / "archive" / "original.txt").write_text("preserve these bytes")
        self.service = SlowLibraryService(self.workspace, archive_roots=[self.external])
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
        connection = http.client.HTTPConnection("127.0.0.1", self.server.server_port, timeout=5)
        try:
            connection.request(method, "/api/v1/" + path, body, headers)
            response = connection.getresponse()
            return response.status, json.loads(response.read())
        finally:
            connection.close()

    def registration(self):
        return {"root_id": self.root_id, "path": "archive", "task": "m4-study-secure"}

    def test_draft_script_is_served_as_executable_javascript(self):
        connection = http.client.HTTPConnection("127.0.0.1", self.server.server_port, timeout=5)
        try:
            connection.request("GET", "/draft.js")
            response = connection.getresponse()
            self.assertEqual(response.status, 200)
            self.assertIn("text/javascript", response.getheader("Content-Type"))
            self.assertIn(b"function initializeStudyDraft()", response.read())
        finally:
            connection.close()

    def test_reference_visibility_requires_same_origin_token_and_exact_boolean(self):
        entry = self.service.library.add(self.registration())["entry"]
        path = "library/entries/" + entry["id"] + "/visibility"
        self.assertEqual(self.request("POST", path, {"hidden": True}, token=False)[0], 403)
        self.assertEqual(self.request("POST", path, {"hidden": True}, origin=False)[0], 403)
        for body in ({}, {"hidden": 1}, {"hidden": True, "delete": True}):
            self.assertEqual(self.request("POST", path, body)[0], 400)
        code, hidden = self.request("POST", path, {"hidden": True})
        self.assertEqual(code, 200)
        self.assertTrue(hidden["hidden"])
        code, restored = self.request("POST", path, {"hidden": False})
        self.assertEqual(code, 200)
        self.assertFalse(restored["hidden"])
        self.assertEqual(
            (self.external / "archive" / "original.txt").read_text(), "preserve these bytes"
        )

    def test_archive_reads_and_registration_require_the_session_and_origin(self):
        self.assertEqual(self.request("GET", "library/roots", token=False)[0], 403)
        self.assertEqual(self.request("GET", "library/roots")[0], 200)
        self.assertEqual(
            self.request("POST", "library/entries", self.registration(), origin=False)[0], 403
        )
        self.assertIsNone(self.service.active)

    def test_archive_worker_shares_global_owner_and_keeps_external_bytes(self):
        original = (self.external / "archive" / "original.txt").read_bytes()
        code, job = self.request("POST", "library/entries", self.registration())
        self.assertEqual(code, 202, job)
        self.assertEqual(job["operation"], "library_index")
        deadline = time.monotonic() + 5
        while self.service.get_job(job["id"])["pid"] is None:
            self.assertLess(time.monotonic(), deadline)
            time.sleep(0.01)
        blocked, error = self.request("POST", "library/entries", self.registration())
        self.assertEqual(blocked, 400)
        self.assertIn("One active operation", error["error"])
        self.assertEqual(self.request("POST", "jobs/" + job["id"] + "/cancel", {})[0], 202)
        self.service.thread.join(5)
        self.assertFalse(self.service.thread.is_alive())
        self.assertEqual((self.external / "archive" / "original.txt").read_bytes(), original)
        self.assertEqual(
            sorted(p.name for p in (self.external / "archive").iterdir()), ["original.txt"]
        )
        self.assertFalse(self.service.get_job(job["id"]).get("remaining_owned_processes"))

    def test_launch_failure_finalizes_index_and_preserves_its_cause(self):
        with patch(
            "experiments.gui.service.subprocess.Popen", side_effect=OSError("runner unavailable")
        ):
            job = self.service.add_archive(self.registration())
            self.service.thread.join(5)
        self.assertFalse(self.service.thread.is_alive())
        finished = self.service.get_job(job["id"])
        entry = self.service.library.get(job["request"]["entry"]["id"])
        self.assertEqual(finished["state"], "failed")
        self.assertEqual(finished["error"], "runner unavailable")
        self.assertEqual(entry["metadata_status"], "unavailable")
        self.assertNotEqual(entry["verification"], "verifying")
        self.assertIsNone(self.service.active)

    def test_external_archive_permissions_do_not_expand_workspace_input_permissions(self):
        with self.assertRaisesRegex(ValueError, "inside the workspace"):
            self.service.safe_path(self.external / "archive" / "original.txt")
        body = {**self.registration(), "path": "../workspace"}
        code, _ = self.request("POST", "library/entries", body)
        self.assertEqual(code, 400)
        self.assertIsNone(self.service.active)


if __name__ == "__main__":
    unittest.main()
