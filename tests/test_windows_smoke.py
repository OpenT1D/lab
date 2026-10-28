"""Protect smoke evidence and exercise real authenticated loopback HTTP requests."""

import contextlib
import hashlib
import io
import json
import os
import sys
import tempfile
import threading
import unittest
import zipfile
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from scripts.windows_smoke import (
    Desktop,
    compare_reports,
    extract_report_fixture,
    isolated_environment,
    main,
    read_state,
    running_analysis,
    workflow_observation_seconds,
)


class WindowsSmokeTests(unittest.TestCase):
    def test_packaged_check_observation_covers_actual_product_command_and_cleanup(self):
        from experiments.gui.service import Service

        source = Path(__file__).resolve().parents[1]
        with patch(
            "experiments.desktop.admission.packaged_manifest", return_value={"fixture": True}
        ):
            for task in ("m3-forecast", "m3-compare"):
                self.assertEqual(
                    workflow_observation_seconds(task, "check", 900, source_root=source), 1410
                )
            service = Service.__new__(Service)
            service.source_root, service.data, service.python = source, source, "private-python"
            _, product_seconds = service.commands(
                {"id": "job-example", "operation": "check"}, {"id": "config-example"}, None
            )[0]
            observed = workflow_observation_seconds(
                "m4-study-secure", "check", 900, source_root=source
            )
            self.assertEqual(observed, 3060)
            self.assertEqual(observed, product_seconds + 60 + 30)

    def test_original_numerical_reader_and_rehearsal_caps_never_gain_audit_time(self):
        with patch(
            "experiments.desktop.admission.admission_allowance",
            side_effect=AssertionError("No audit time may extend these smoke limits"),
        ):
            for task in ("m3-forecast", "m3-compare", "m4-study-secure"):
                for operation, original in (
                    ("run", 1800 if task == "m4-study-secure" else 900),
                    ("reconstruct", 900),
                    ("install", 900),
                ):
                    self.assertEqual(
                        workflow_observation_seconds(task, operation, original), original
                    )
                self.assertEqual(
                    workflow_observation_seconds(task, "check", 900, source_rehearsal=True), 900
                )
        with patch("experiments.desktop.admission.packaged_manifest", return_value=None):
            self.assertEqual(workflow_observation_seconds("m3-forecast", "check", 900), 900)

    def test_operation_deadline_includes_submission_and_cannot_be_renewed_by_progress(self):
        desktop = Desktop(None, None, None, None)
        replies = [
            {"id": "job-example"},
            {
                "id": "job-example",
                "state": "running",
                "phase": {"allowance_seconds": 999999, "started_at": "now"},
            },
        ]
        # Submission already took 80 seconds; a progress update cannot restart the clock.
        with (
            patch.object(desktop, "request", side_effect=replies) as request,
            patch("scripts.windows_smoke.time.monotonic", side_effect=[100, 180, 201]),
            patch("scripts.windows_smoke.time.sleep"),
        ):
            with self.assertRaisesRegex(ValueError, "smoke-test deadline"):
                desktop.operation("example", timeout=100)
        self.assertEqual(request.call_count, 2)
        self.assertEqual(
            desktop.observations,
            [
                {
                    "job_id": "job-example",
                    "ceiling_seconds": 100,
                    "policy": "fixed-from-operation-start",
                }
            ],
        )

    def test_direct_wait_records_its_own_observation_start(self):
        desktop = Desktop(None, None, None, None)
        completed = {"id": "job-example", "state": "completed", "pid": None}
        with (
            patch.object(desktop, "request", return_value=completed),
            patch("scripts.windows_smoke.time.monotonic", side_effect=[100, 101]),
        ):
            self.assertEqual(desktop.wait(completed, timeout=90), completed)
        self.assertEqual(desktop.observations[0]["policy"], "fixed-from-wait-start")
        self.assertEqual(desktop.observations[0]["ceiling_seconds"], 90)

    def test_real_saved_m5_fixture_extracts_exact_bytes_without_execution(self):
        fixtures = Path(__file__).parent / "fixtures"
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary) / "report-only"
            with patch("subprocess.Popen", side_effect=AssertionError("No snapshot execution")):
                manifest = extract_report_fixture(fixtures, output)
            self.assertEqual(set(manifest["files"]), {item.name for item in output.iterdir()})
            for name, record in manifest["files"].items():
                self.assertEqual(
                    hashlib.sha256((output / name).read_bytes()).hexdigest(), record["sha256"]
                )
            report = json.loads((output / "report.json").read_bytes())
            self.assertEqual(report["paired_count"], 7)
            self.assertFalse(report["human_execution_authorized"])

    def test_fixture_rejects_traversal_links_and_changed_member_bytes(self):
        for name, mode, declared in (
            ("../outside", 0o100644, b"content"),
            ("linked", 0o120777, b"content"),
            ("report.json", 0o100644, b"changed"),
        ):
            with self.subTest(name=name), tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary)
                archive = root / "m5-report-only.zip"
                with zipfile.ZipFile(archive, "x") as stream:
                    info = zipfile.ZipInfo(name)
                    info.external_attr = mode << 16
                    stream.writestr(info, b"content")
                raw = archive.read_bytes()
                value = {
                    "schema": "opent1d.synthetic-report-fixture/1",
                    "archive": {
                        "path": archive.name,
                        "sha256": hashlib.sha256(raw).hexdigest(),
                        "bytes": len(raw),
                    },
                    "files": {
                        name: {
                            "sha256": hashlib.sha256(declared).hexdigest(),
                            "bytes": len(declared),
                        }
                    },
                }
                (root / "m5-report-only.json").write_text(json.dumps(value))
                output = root / "output"
                with self.assertRaises(ValueError):
                    extract_report_fixture(root, output)
                self.assertFalse(output.exists())
                self.assertFalse((root.parent / "outside").exists())

    def test_installed_acceptance_cannot_skip_durable_or_inherit_path(self):
        with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit) as raised:
            main(["--source", "/unused/app", "--skip-durable", "--output", "/unused/output"])
        self.assertEqual(raised.exception.code, 2)
        with patch.dict(os.environ, {"PATH": "/test/developer/tools"}):
            installed = Desktop(None, None, None, None)
            source = Desktop(None, None, None, None, source_rehearsal=True)
        self.assertEqual(installed.env["PATH"], "")
        self.assertEqual(source.env["PATH"], "/test/developer/tools")

    def test_actual_launcher_reuses_session_refuses_wrong_token_and_recovers_stale_state(self):
        source = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary).resolve()
            data = output / "user data"
            desktop = Desktop(Path(sys.executable), source, data, output, source_rehearsal=True)
            try:
                desktop.start()
                desktop.reopen()
                saved = json.loads((data / "application-session.json").read_text())
                original_token = desktop.state["token"]
                desktop.state["token"] = "0" * 64
                try:
                    desktop.request("POST", "/api/desktop/shutdown", {}, expected=403)
                finally:
                    desktop.state["token"] = original_token
                self.assertIsNone(desktop.process.poll())
                desktop.request("GET", "/api/v1/observations/bootstrap")
                desktop.stop(cli=True)
                self.assertFalse((data / "application-session.json").exists())
                (data / "application-session.json").write_text(json.dumps(saved))
                desktop.start()
                self.assertNotEqual(desktop.state["token"], original_token)
                self.assertIsNone(desktop.process.poll())
                desktop.stop()
                self.assertEqual(len(desktop.shutdowns), 2)
                self.assertTrue(all(item["clean"] for item in desktop.shutdowns))
            finally:
                if desktop.process is not None:
                    desktop.stop()

    def test_readiness_refuses_foreign_origin_credentials_and_different_process(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "ready.json"
            state = {"url": "http://127.0.0.1:8123/", "token": "a" * 64, "pid": 42}
            path.write_text(json.dumps(state))
            self.assertEqual(read_state(path, SimpleNamespace(pid=42))["url"], state["url"][:-1])
            for change in (
                {"url": "http://example.com:8123/"},
                {"url": "https://127.0.0.1:8123/"},
                {"url": "http://name:secret@127.0.0.1:8123/"},
                {"url": "http://127.0.0.1:8123/?next=example.com"},
                {"pid": 43},
                {"pid": True},
                {"token": "secret\r\nInjected: value"},
            ):
                with self.subTest(change=change), self.assertRaises(ValueError):
                    path.write_text(json.dumps({**state, **change}))
                    read_state(path, SimpleNamespace(pid=42))

    def test_runtime_environment_cannot_inherit_checkout_tools_or_python_overrides(self):
        original = {
            "PATH": "/external/tools",
            "PYTHONPATH": "/untrusted/modules",
            "PYTHONHOME": "/other/python",
            "UV_PROJECT": "/other/project",
            "VIRTUAL_ENV": "/other/env",
            "SystemRoot": "C:\\Windows",
        }
        with patch.dict(os.environ, original, clear=True):
            env = isolated_environment()
        self.assertEqual(env["PATH"], "")
        self.assertEqual(env["SystemRoot"], "C:\\Windows")
        for name in ("PYTHONPATH", "PYTHONHOME", "VIRTUAL_ENV", "UV_PROJECT"):
            self.assertNotIn(name, env)
        self.assertEqual(env["UV_PYTHON_DOWNLOADS"], "never")

    def test_report_mismatch_cannot_be_recorded_as_equal(self):
        original = {"report.json": b'{"answer":1}\n', "report.md": b"One\n"}
        self.assertEqual(len(compare_reports(original, original)["report.json"]), 64)
        for changed in (
            {"report.json": original["report.json"]},
            {**original, "report.md": b"Two\n"},
        ):
            with self.assertRaises(ValueError):
                compare_reports(changed, original)

    def test_cancellation_waits_for_native_analysis_and_refuses_external_output(self):
        with tempfile.TemporaryDirectory() as temporary:
            data = Path(temporary) / "data"
            archive = data / "archive"
            archive.mkdir(parents=True)
            job = {"commands": [{"argv": ["python", "run", "--output", str(archive)]}]}
            self.assertFalse(running_analysis(job, data))
            path = archive / "execution.json"
            path.write_text(json.dumps({"phase": "loading", "schedules": {"full": "masking"}}))
            self.assertFalse(running_analysis(job, data))
            path.write_text(json.dumps({"phase": "full", "schedules": {"full": "analysis"}}))
            self.assertTrue(running_analysis(job, data))
            job["commands"][0]["argv"][-1] = str(Path(temporary) / "unrelated")
            with self.assertRaisesRegex(ValueError, "escapes"):
                running_analysis(job, data)

    def test_http_preserves_binary_reports_and_binds_session_headers(self):
        seen = []

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *_args):
                pass

            def do_POST(self):
                seen.append(
                    (self.path, self.headers, self.rfile.read(int(self.headers["Content-Length"])))
                )
                payload = b' {"report":"raw bytes"}\r\n'
                self.send_response(201)
                self.send_header("Content-Length", str(len(payload)))
                self.end_headers()
                self.wfile.write(payload)

        server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        desktop = Desktop(None, None, None, None)
        desktop.state = {"url": f"http://127.0.0.1:{server.server_port}", "token": "abc123"}
        try:
            actual = desktop.request(
                "POST", "/api/example", {"case": "invented"}, expected=201, raw=True
            )
            self.assertEqual(actual, b' {"report":"raw bytes"}\r\n')
            self.assertEqual(seen[0][1]["X-OpenT1D-Token"], "abc123")
            self.assertEqual(seen[0][1]["Origin"], desktop.state["url"])
            self.assertEqual(json.loads(seen[0][2]), {"case": "invented"})
            with self.assertRaisesRegex(ValueError, "returned 201"):
                desktop.request("POST", "/api/example", {})
        finally:
            server.shutdown()
            server.server_close()
            thread.join(2)
