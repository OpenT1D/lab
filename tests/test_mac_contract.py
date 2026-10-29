"""The Mac candidate admits only two stdlib tasks without weakening Windows v1."""

import http.client
import json
import sys
import tempfile
import threading
import unittest
from pathlib import Path
from unittest.mock import patch

from experiments.desktop import __main__ as desktop
from experiments.desktop import runtime
from experiments.gui.server import Server
from experiments.gui.service import Service

ROOT = Path(__file__).resolve().parents[1]


class MacRuntimeContractTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.base = Path(self.temporary.name).resolve()
        self.root = self.base / "app"
        self.root.mkdir()
        self.python = self.base / "runtime/bin/python3.12"
        self.python.parent.mkdir(parents=True)
        self.python.write_bytes(b"synthetic interpreter bytes")
        selector = self.root / "packaging/mac/runtime-lock.json"
        selector.parent.mkdir(parents=True)
        selector.write_bytes(b"synthetic locked runtime selector")
        self.manifest = {
            "schema": runtime.SCHEMA_V2,
            "source": {"revision": "a" * 40, "dirty": False},
            "runtime": {"version": "3.12.16"},
            "platform": {"system": "Darwin", "architecture": "arm64", "minimum_release": "11.0"},
            "capabilities": {
                "schema": "opent1d.desktop-capabilities/2",
                "tasks": ["mmtt-sensitivity", "mmtt-sampling"],
            },
            "runtime_paths": {".": "runtime/bin/python3.12"},
            "runtime_projects": {
                ".": {
                    "directory": "runtime",
                    "python": "runtime/bin/python3.12",
                    "selectors": {"packaging/mac/runtime-lock.json": runtime._digest(selector)},
                    "distributions": {},
                    "upstream_revisions": {},
                }
            },
            "payload_files": {
                "runtime/bin/python3.12": {
                    "sha256": runtime._digest(self.python),
                    "bytes": self.python.stat().st_size,
                }
            },
        }
        self.save()

    def save(self):
        (self.base / "package-manifest.json").write_text(json.dumps(self.manifest))

    def test_stdlib_only_v2_uses_exact_private_interpreter_and_empty_inventory(self):
        actual = {
            "python": "3.12.16",
            "implementation": "CPython",
            "packages": {},
            "direct_urls": {},
        }
        with patch.object(runtime.subprocess, "run") as probe:
            probe.return_value.stdout = json.dumps(actual)
            self.assertEqual(runtime.verify_packaged_project(".", self.root), actual)
        self.assertEqual(runtime.interpreter(source_root=self.root), self.python)
        self.assertEqual(runtime.packaged_capabilities(self.root), runtime.MMTT_TASKS)
        with self.assertRaisesRegex(ValueError, "not included"):
            runtime.interpreter("experiments/m0/simglucose_secure", self.root)

    def test_v2_cannot_widen_tasks_or_add_runtime_projects(self):
        self.manifest["capabilities"]["tasks"].append("m4-study-secure")
        self.save()
        with self.assertRaisesRegex(ValueError, "capabilities"):
            runtime.packaged_manifest(self.root)
        self.manifest["capabilities"]["tasks"].pop()
        self.manifest["runtime_projects"]["native"] = {}
        self.save()
        with self.assertRaisesRegex(ValueError, "capabilities"):
            runtime.packaged_manifest(self.root)

    def test_v2_empty_inventory_is_not_an_exception_for_windows_v1(self):
        self.manifest["schema"] = runtime.SCHEMA
        record = self.manifest["runtime_projects"]["."]
        record["selectors"] = {"uv.lock": "a" * 64, "pyproject.toml": "b" * 64}
        self.save()
        with self.assertRaisesRegex(ValueError, "lock inventory"):
            runtime.packaged_runtime(source_root=self.root)

    def test_v2_rejects_added_distributions_and_changed_runtime_bytes(self):
        self.manifest["runtime_projects"]["."]["distributions"] = {"root-tool": "1.0"}
        self.save()
        with self.assertRaisesRegex(ValueError, "lock inventory"):
            runtime.packaged_runtime(source_root=self.root)
        self.manifest["runtime_projects"]["."]["distributions"] = {}
        self.save()
        self.python.write_bytes(b"tampered runtime")
        with patch.object(runtime.subprocess, "run") as probe:
            with self.assertRaisesRegex(ValueError, "bytes"):
                runtime.verify_packaged_project(".", self.root)
            probe.assert_not_called()

    def test_mac_workspace_is_outside_the_entire_app_bundle(self):
        application = self.base / "OpenT1D.app"
        source = application / "Contents/Resources/payload/app"
        source.mkdir(parents=True)
        with (
            patch.object(desktop, "SOURCE", source),
            patch.object(desktop, "packaged_capabilities", return_value=runtime.MMTT_TASKS),
        ):
            with self.assertRaisesRegex(ValueError, "outside the Mac application"):
                desktop.directory(application / "Contents/research")
            self.assertEqual(desktop.directory(self.base / "user-data"), self.base / "user-data")


class MacCapabilityHTTPTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.workspace = Path(self.temporary.name).resolve()
        with (
            patch.object(runtime, "packaged_capabilities", return_value=runtime.MMTT_TASKS),
            patch(
                "experiments.desktop.examples.prepare", side_effect=AssertionError("native seed")
            ),
        ):
            self.service = Service(self.workspace, profile="desktop", source_root=ROOT)
        self.server = Server(self.service)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.addCleanup(self.close)

    def close(self):
        self.server.shutdown()
        self.service.close()
        self.server.server_close()
        self.thread.join(2)

    def request(self, method, path):
        connection = http.client.HTTPConnection("127.0.0.1", self.server.server_port, timeout=5)
        headers = {
            "X-OpenT1D-Token": self.server.token,
            "Origin": f"http://127.0.0.1:{self.server.server_port}",
            "Content-Type": "application/json",
        }
        try:
            connection.request(
                method, path, body="{}" if method == "POST" else None, headers=headers
            )
            response = connection.getresponse()
            return response.status, response.read()
        finally:
            connection.close()

    def test_only_the_two_real_mmtt_controllers_and_bootstraps_are_available(self):
        self.assertFalse((self.workspace / "examples").exists())
        for name in ("m3", "campaigns", "library", "durable"):
            self.assertIsNone(getattr(self.service, name))
        status, raw = self.request("GET", "/api/v1/bootstrap")
        self.assertEqual(status, 200)
        self.assertEqual(json.loads(raw)["capabilities"], list(runtime.MMTT_TASKS))
        for route in ("observations", "sampling"):
            self.assertEqual(self.request("GET", f"/api/v1/{route}/bootstrap")[0], 200)
        self.assertIn(b"mmtt-sensitivity,mmtt-sampling", self.request("GET", "/")[1])

    def test_native_library_campaign_setup_and_generic_dispatch_are_refused(self):
        for route in (
            "m3/bootstrap",
            "campaigns/configurations",
            "durable/bootstrap",
            "library/roots",
            "files",
            "configurations/example",
            "jobs/unknown/reconstruct",
        ):
            for method in ("GET", "POST"):
                with self.subTest(route=route, method=method):
                    self.assertEqual(self.request(method, "/api/v1/" + route)[0], 403)


class MacCapabilityJournalTests(unittest.TestCase):
    def test_foreign_operations_are_ignored_before_legacy_imports_and_left_unchanged(self):
        with tempfile.TemporaryDirectory() as temporary:
            workspace = Path(temporary).resolve()
            retained = {}
            for i, (task, operation) in enumerate(
                (
                    ("mmtt-sensitivity", "library_index"),
                    ("mmtt-sampling", "library_verify"),
                    ("mmtt-sensitivity", "m3_run"),
                    ("mmtt-sensitivity", "sampling_run"),
                    ("m4-study-secure", "observation_run"),
                )
            ):
                identity = f"job-foreign-{i}"
                journal = workspace / "results/gui" / identity / "job.json"
                journal.parent.mkdir(parents=True)
                raw = json.dumps(
                    {
                        "schema": "opent1d.gui-job/1",
                        "id": identity,
                        "task": task,
                        "operation": operation,
                        "state": "running",
                    }
                ).encode()
                journal.write_bytes(raw)
                retained[journal] = raw
            with (
                patch.object(runtime, "packaged_capabilities", return_value=runtime.MMTT_TASKS),
                patch.dict(sys.modules, {"experiments.catalogue.formats": None}),
            ):
                service = Service(workspace, profile="desktop", source_root=ROOT)
                try:
                    self.assertEqual(service.jobs, {})
                    for journal, raw in retained.items():
                        self.assertEqual(journal.read_bytes(), raw)
                finally:
                    service.close()


if __name__ == "__main__":
    unittest.main()
