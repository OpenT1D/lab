"""Thin transport/convenience boundaries; numerical authority remains the SDK."""

import http.client
import importlib
import json
import os
import socket
import sys
import tempfile
import threading
import time
import types
import unittest
import uuid
from pathlib import Path
from unittest.mock import patch

from experiments.shared_services import store

ROOT = Path(__file__).resolve().parents[1]
PACKAGE = "_opent1d_gui_test_facade"
if PACKAGE not in sys.modules:
    package = types.ModuleType(PACKAGE)
    package.__path__ = [str(ROOT / "packaging/sdk/opent1d_lab")]
    sys.modules[PACKAGE] = package
state = importlib.import_module(PACKAGE + "._gui_state")
transport = importlib.import_module(PACKAGE + "._gui_http")
files = importlib.import_module(PACKAGE + "._gui_files")


class ControlledSDK:
    """Only controlled GUI unit behavior; actual SDK tests live separately."""

    def __init__(self):
        self.calls = []
        self.gate = None
        self.entered = threading.Event()
        self.report_files = {
            "report.json": b'{"controlled":true}\n',
            "report.md": b"# Controlled report\n",
        }

    def installation(self):
        return {"build_label": "controlled", "source": {"revision": "a" * 40, "dirty": True}}

    def create_project(self, path, name):
        self.calls.append("create")
        store.create(path, name)
        return self.Project(path)

    def Project(self, path):
        sdk = self

        class Project:
            def __init__(self):
                self.path = str(path)

            def info(self):
                sdk.calls.append("info")
                sdk.entered.set()
                if sdk.gate is not None:
                    sdk.gate.wait(5)
                return {"plans": [], "attempts": [], "head": {"count": 1}}

            def plan(self, _identity):
                return {"task": "mmtt-sensitivity"}

            def check(self, identity, *, runtime_attachment):
                sdk.calls.append(("check", identity, runtime_attachment))
                return {
                    "task": "mmtt-sensitivity",
                    "metadata_valid": True,
                    "runtimes_ready": True,
                    "native_policy": "controlled",
                    "setup_performed": False,
                }

            def run(self, _identity, *, cancel, **_kwargs):
                sdk.calls.append("run")
                sdk.entered.set()
                if not cancel.wait(5):
                    raise RuntimeError("Controlled run was not cancelled")
                return {
                    "attempt": "b" * 64,
                    "result": {"completeness": "incomplete", "execution_status": "interrupted"},
                    "receipt": {"remaining_owned_processes": []},
                }

            def reconstruct(self, _identity, output, *, allow_failed):
                sdk.calls.append("reconstruct")
                output.mkdir()
                for name, raw in sdk.report_files.items():
                    (output / name).write_bytes(raw)
                (output / "manifest.json").write_text('{"controlled_seal": true}')
                return {
                    "completeness": "complete",
                    "report_sha256": {
                        name: files.sha256(raw) for name, raw in sdk.report_files.items()
                    },
                }

        return Project()


@unittest.skipUnless(os.name == "posix", "Installed SDK GUI uses POSIX ownership")
class GUIStateTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="sdk-gui-unit-")
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name).resolve()
        self.sdk = ControlledSDK()
        self.controller = state.Controller(self.root / "workspace", sdk=self.sdk)
        self.addCleanup(self.controller.close)

    def request(self, operation, args, project=None):
        return {
            "request_id": uuid.uuid4().hex,
            "operation": operation,
            "arguments": args,
            "project": project,
        }

    def finish(self, job):
        deadline = time.monotonic() + 8
        while time.monotonic() < deadline:
            value = self.controller.get_job(job["id"])
            if value["status"] != "running":
                return value
            time.sleep(0.01)
        self.fail("Controlled GUI action did not finish")

    def project(self):
        job = self.finish(
            self.controller.submit(self.request("create", {"name": "Controlled project"}))
        )
        self.assertEqual(job["status"], "done", job)
        return job["project"]

    def test_reserved_child_projects_are_refused_without_any_write(self):
        for name in ("projects", "inputs", "reports", "attachments", "journal"):
            workspace = self.root / name
            workspace.mkdir()
            store.create(workspace / name, "Do not modify")
            before = {
                p.relative_to(workspace).as_posix(): p.read_bytes()
                for p in workspace.rglob("*")
                if p.is_file()
            }
            with self.assertRaisesRegex(ValueError, "existing project"):
                state.Controller(workspace, sdk=self.sdk)
            after = {
                p.relative_to(workspace).as_posix(): p.read_bytes()
                for p in workspace.rglob("*")
                if p.is_file()
            }
            self.assertEqual(before, after)
            with store.opened(workspace / name) as original:
                self.assertEqual(original.head["count"], 1)

    def test_idempotency_concurrency_and_failed_submission_rollback(self):
        handle = self.project()
        self.sdk.entered.clear()
        self.sdk.gate = threading.Event()
        request = self.request("refresh", {}, handle)
        job = self.controller.submit(request)
        self.assertTrue(self.sdk.entered.wait(2))
        self.assertEqual(self.controller.submit(request)["id"], job["id"])
        with self.assertRaises(state.Busy):
            self.controller.submit(self.request("refresh", {}, handle))
        with self.assertRaisesRegex(ValueError, "different content"):
            self.controller.submit(
                {**request, "operation": "check", "arguments": {"plan": "b" * 64}}
            )
        self.sdk.gate.set()
        self.assertEqual(self.finish(job)["status"], "done")
        self.sdk.gate = None
        request = self.request("refresh", {}, handle)
        with patch.object(
            threading.Thread, "start", side_effect=RuntimeError("controlled start error")
        ):
            with self.assertRaises(RuntimeError):
                self.controller.submit(request)
        self.assertIsNone(self.controller.active)
        self.assertEqual(self.finish(self.controller.submit(request))["status"], "done")

    def test_close_drains_metadata_and_holds_lease_until_join(self):
        handle = self.project()
        self.sdk.entered.clear()
        self.sdk.gate = threading.Event()
        job = self.controller.submit(self.request("refresh", {}, handle))
        self.assertTrue(self.sdk.entered.wait(2))
        closing = threading.Thread(target=self.controller.close)
        closing.start()
        try:
            time.sleep(0.05)
            self.assertTrue(closing.is_alive())
            with self.assertRaises(ValueError):
                state.Controller(self.controller.root, sdk=self.sdk)
            with self.assertRaises(state.Busy):
                self.controller.submit(self.request("refresh", {}, handle))
        finally:
            self.sdk.gate.set()
            closing.join(3)
        self.assertFalse(closing.is_alive())
        self.assertEqual(self.finish(job)["status"], "done")
        other = state.Controller(self.controller.root, sdk=self.sdk)
        other.close()

    def test_check_context_survives_all_later_runtime_selections(self):
        handle = self.project()
        attachment_a = self.root / "a.json"
        attachment_b = self.root / "b.json"
        for attachment in (attachment_a, attachment_b):
            attachment.write_text("{}")
        plan = "a" * 64
        for revision, attachment in enumerate(
            (None, attachment_a, attachment_b, attachment_a, attachment_a, None, None)
        ):
            if revision:
                operation = "clear_attachment" if attachment is None else "select_attachment"
                args = {} if attachment is None else {"path": str(attachment)}
                selected = self.finish(self.controller.submit(self.request(operation, args)))
                self.assertEqual(selected["status"], "done", selected)
            snapshot = self.controller.state()
            self.assertEqual(snapshot["runtime_revision"], revision)
            self.assertEqual(
                snapshot["runtime_attachment"], str(attachment) if attachment else None
            )
            checked = self.finish(
                self.controller.submit(self.request("check", {"plan": plan}, handle))
            )
            self.assertEqual(checked["status"], "done", checked)
            expected = {
                "project": handle,
                "plan": plan,
                "runtime_attachment": str(attachment) if attachment else None,
                "runtime_revision": revision,
            }
            self.assertEqual(checked["check_context"], expected)
            self.assertIn(("check", plan, expected["runtime_attachment"]), self.sdk.calls)
            if revision == 1:
                original = checked
        self.assertEqual(
            self.controller.get_job(original["id"])["check_context"], original["check_context"]
        )
        with patch.object(
            self.sdk, "attach_runtimes", create=True, return_value={"attachment": str(attachment_a)}
        ):
            attached = self.finish(
                self.controller.submit(
                    self.request("attach", {"native_site": "/native", "observer_site": "/observer"})
                )
            )
        self.assertEqual(attached["status"], "done", attached)
        self.assertEqual(self.controller.state()["runtime_revision"], 7)
        self.assertEqual(self.controller.state()["runtime_attachment"], str(attachment_a))
        refused = self.finish(
            self.controller.submit(
                self.request("select_attachment", {"path": str(self.root / "missing.json")})
            )
        )
        self.assertEqual(refused["status"], "error", refused)
        self.assertEqual(self.controller.state()["runtime_revision"], 7)
        self.assertEqual(self.controller.state()["runtime_attachment"], str(attachment_a))

    def test_cancel_uses_sdk_event_and_keeps_incomplete_outcome(self):
        handle = self.project()
        self.sdk.entered.clear()
        job = self.controller.submit(
            self.request("run", {"plan": "a" * 64, "retry_of": None}, handle)
        )
        self.assertTrue(self.sdk.entered.wait(2))
        self.controller.cancel(job["id"])
        done = self.finish(job)
        self.assertEqual(done["result"]["result"]["execution_status"], "interrupted")
        self.assertEqual(done["result"]["receipt"]["remaining_owned_processes"], [])
        self.assertTrue(done["cancel_requested"])

    def test_task_specific_report_rosters_and_tampering(self):
        handle = self.project()
        for figure in (False, True):
            if figure:
                self.sdk.report_files["figure.svg"] = b'<svg xmlns="http://www.w3.org/2000/svg"/>'
            done = self.finish(
                self.controller.submit(
                    self.request("verify", {"attempt": "a" * 64, "allow_failed": False}, handle)
                )
            )
            self.assertEqual(done["status"], "done", done)
            key = done["result"]["report"]
            record = next(r for r in self.controller.state()["reports"] if r["id"] == key)
            self.assertEqual(set(record["files"]), set(self.sdk.report_files))
            self.assertEqual(
                self.controller.report(key, "report.md")[0], self.sdk.report_files["report.md"]
            )
            if not figure:
                with self.assertRaises(ValueError):
                    self.controller.report(key, "figure.svg")
            output = Path(self.controller.reports[key]["directory"])
            (output / "report.md").write_bytes(b"altered")
            with self.assertRaisesRegex(ValueError, "changed"):
                self.controller.report(key, "report.md")
            self.assertFalse(self.controller.reports[key]["valid"])

    def test_terminal_journal_failure_surfaces_without_losing_sdk_state(self):
        original = self.controller.journal

        def fail_terminal(job):
            if job["status"] != "running":
                raise OSError("controlled fsync failure")
            return original(job)

        with patch.object(self.controller, "journal", side_effect=fail_terminal):
            done = self.finish(
                self.controller.submit(self.request("create", {"name": "Preserved"}))
            )
        self.assertEqual(done["status"], "error")
        self.assertIn("metadata could not be saved", done["error"])
        self.assertIn(done["project"], self.controller.infos)
        with store.opened(self.controller.catalog["projects"][done["project"]]["path"]) as project:
            self.assertEqual(project.head["count"], 1)


@unittest.skipUnless(os.name == "posix", "Installed SDK GUI uses POSIX ownership")
class GUIHTTPTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="sdk-gui-http-")
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name).resolve()
        self.controller = state.Controller(self.root / "workspace", sdk=ControlledSDK())
        self.server = transport.Server(
            self.controller,
            assets={"index.html": b"__SESSION_TOKEN__", "app.js": b"", "app.css": b""},
        )
        self.thread = threading.Thread(
            target=self.server.serve_forever, kwargs={"poll_interval": 0.02}
        )
        self.thread.start()
        self.addCleanup(self.close)

    def close(self):
        self.server.shutdown()
        self.thread.join(3)
        self.server.server_close()
        self.controller.close()

    def call(self, route, *, body=None, headers=None):
        connection = http.client.HTTPConnection("127.0.0.1", self.server.server_port, timeout=8)
        try:
            raw = json.dumps(body) if body is not None else None
            defaults = {"X-OpenT1D-Token": self.server.token}
            if body is not None:
                defaults.update(Origin=self.server.origin, **{"Content-Type": "application/json"})
            connection.request(
                "POST" if body is not None else "GET",
                route,
                raw,
                headers={**defaults, **(headers or {})},
            )
            response = connection.getresponse()
            return response.status, response.read(), dict(response.getheaders())
        finally:
            connection.close()

    def test_real_http_positive_controls_and_authentication(self):
        status, raw, headers = self.call("/")
        self.assertEqual(status, 200)
        self.assertEqual(raw, self.server.token.encode())
        self.assertEqual(headers["Cache-Control"], "no-store")
        self.assertIn("frame-ancestors 'none'", headers["Content-Security-Policy"])
        self.assertEqual(self.call("/api/state")[0], 200)
        for headers in (
            {"Host": "attacker.invalid"},
            {"Origin": "null"},
            {"Origin": "http://attacker.invalid"},
            {"X-OpenT1D-Token": "stale"},
        ):
            self.assertEqual(self.call("/api/state", headers=headers)[0], 403)
        action = {
            "request_id": uuid.uuid4().hex,
            "operation": "create",
            "project": None,
            "arguments": {"name": "HTTP control"},
        }
        self.assertEqual(self.call("/api/actions", body=action)[0], 202)
        self.assertEqual(self.call("/api/actions", body=action, headers={"Origin": "null"})[0], 403)

    def raw(self, headers, body=b"{}"):
        with socket.create_connection(
            ("127.0.0.1", self.server.server_port), timeout=8
        ) as connection:
            connection.sendall(
                ("POST /api/actions HTTP/1.0\r\n" + headers + "\r\n").encode() + body
            )
            return connection.recv(4096)

    def test_duplicate_headers_transfer_encoding_and_json_refuse(self):
        valid = (
            f"Host: 127.0.0.1:{self.server.server_port}\r\nOrigin: {self.server.origin}\r\n"
            f"X-OpenT1D-Token: {self.server.token}\r\n"
            "Content-Type: application/json\r\nContent-Length: 2\r\n"
        )
        for extra in (
            "Host: attacker.invalid\r\n",
            "Origin: null\r\n",
            "X-OpenT1D-Token: bad\r\n",
            "Content-Length: 2\r\n",
            "Transfer-Encoding: chunked\r\n",
        ):
            raw = self.raw(valid + extra)
            self.assertRegex(raw.split(b"\r\n")[0].decode(), r" (400|403) ")
        for payload in (b'{"a":1,"a":2}', b'{"a":NaN}', b'{"a":1e999}'):
            headers = valid.replace("Content-Length: 2\r\n", f"Content-Length: {len(payload)}\r\n")
            self.assertRegex(self.raw(headers, payload).split(b"\r\n")[0].decode(), r" (400|403) ")
        self.assertEqual(self.controller.sdk.calls, [])

    def test_continuous_body_drip_has_a_total_deadline(self):
        with socket.create_connection(
            ("127.0.0.1", self.server.server_port), timeout=8
        ) as connection:
            headers = (
                f"POST /api/actions HTTP/1.0\r\nHost: 127.0.0.1:{self.server.server_port}\r\n"
                f"Origin: {self.server.origin}\r\nX-OpenT1D-Token: {self.server.token}\r\n"
                "Content-Type: application/json\r\nContent-Length: 600\r\n\r\n"
            )
            connection.sendall(headers.encode())
            started = time.monotonic()
            while time.monotonic() - started < 6:
                try:
                    connection.sendall(b" ")
                except OSError:
                    break
                time.sleep(0.2)
            response = connection.recv(4096)
            self.assertLess(time.monotonic() - started, 7)
            self.assertIn(b"400", response)
        self.assertEqual(self.call("/api/state")[0], 200)

    def test_shutdown_does_not_depend_on_response_delivery(self):
        original = transport.Handler.send

        def disconnect(handler, status, value, *args, **kwargs):
            if handler.path == "/api/shutdown":
                raise BrokenPipeError("controlled disconnected response")
            return original(handler, status, value, *args, **kwargs)

        with patch.object(transport.Handler, "send", disconnect):
            with self.assertRaises((http.client.RemoteDisconnected, ConnectionResetError)):
                self.call("/api/shutdown", body={})
        self.thread.join(3)
        self.assertFalse(self.thread.is_alive())
        self.assertTrue(self.controller.closing)
