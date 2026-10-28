"""GUI ownership and trust boundaries; controlled receipts are not native evidence."""

import http.client
import json
import os
import sys
import tempfile
import threading
import time
import types
import unittest
from pathlib import Path
from unittest.mock import patch

from experiments import durable_archives
from experiments.gui import durable_worker
from experiments.gui.durable import store_identity
from experiments.gui.server import Server
from experiments.gui.service import Service, digest, encode, inventory, read_json


class DurableGUIBoundaryTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.base = Path(self.temporary.name).resolve()
        self.workspace = self.base / "workspace"
        self.store = self.base / "store"
        self.workspace.mkdir()
        self.store.mkdir()
        self.package = self.store / "package-existing"
        self.package.mkdir()
        (self.package / "manifest.json").write_text("{}")
        self.sentinel = self.base / "executed"
        (self.package / "reader.py").write_text(
            f"from pathlib import Path\nPath({str(self.sentinel)!r}).touch()\n"
        )
        self.service = Service(self.workspace, archive_store=self.store)
        self.controller = self.service.durable
        self.root_id = next(
            root["id"]
            for root in self.controller.bootstrap()["roots"]
            if root["directory"] == str(self.store)
        )
        self.calls = []
        self.revision = "a" * 40
        self.report_raw = encode(
            {"passed": False, "planned_slots": 2, "accepted_slots": 1, "slots": []}
        )
        self.markdown_raw = b"Failed numerical coverage retained.\n"
        manifest_raw = encode(
            {
                "reconstruction": {
                    "artifacts": {
                        "report.json": {
                            "sha256": digest(self.report_raw),
                            "size": len(self.report_raw),
                        },
                        "report.md": {
                            "sha256": digest(self.markdown_raw),
                            "size": len(self.markdown_raw),
                        },
                    }
                }
            }
        )
        (self.package / "manifest.json").write_bytes(manifest_raw)
        self.native = {
            "schema": "opent1d.durable-archive-result/1",
            "operation": "verify",
            "status": "completed",
            "task": "maintained-campaign",
            "package_identity": digest(manifest_raw),
            "integrity_verified": True,
            "reconstruction_verified": False,
            "complete": False,
            "reader_revision": self.revision,
        }

    def tearDown(self):
        self.service.close()
        self.temporary.cleanup()

    def registered(self):
        return self.controller.register({"root_id": self.root_id, "path": self.package.name})

    def job(self, request):
        identity = "job-" + str(len(self.calls) + 1).zfill(32)
        folder = self.service.data / identity
        folder.mkdir()
        job = {
            "id": identity,
            "request": request,
            "operation": request["operation"],
            "exit_code": None,
            "cancel_requested": False,
            "cleanup_forced": False,
            "error": None,
            "result": None,
        }
        self.service.jobs[identity] = job
        self.controller.commands(job)
        self.calls.append(request["operation"])
        return job, folder

    def controlled_verify(self, _package):
        self.calls.append("core_verify")
        return dict(self.native)

    def controlled_reconstruct(self, _package, _checkout, _revision, output):
        self.calls.append("core_reconstruct")
        report = output / "evidence/reconstructed"
        report.mkdir(parents=True)
        (report / "report.json").write_bytes(self.report_raw)
        (report / "report.md").write_bytes(self.markdown_raw)
        return self.native | {"operation": "reconstruct", "reconstruction_verified": True}

    def execute(self, request, *, revision=None, owner_error=None):
        job, folder = self.job(request)
        core = types.SimpleNamespace(
            verify_package=self.controlled_verify, reconstruct_package=self.controlled_reconstruct
        )
        with (
            patch.dict(sys.modules, {"experiments.durable_archives.core": core}),
            patch.object(durable_archives, "core", core, create=True),
            patch.object(
                durable_worker, "current_revision", return_value=revision or self.revision
            ),
        ):
            result = durable_worker.execute(request, folder)
        job["exit_code"] = 0 if result["status"] == "completed" else 1
        job["error"] = owner_error
        self.controller.finish(job)
        return job, folder

    def test_store_is_explicit_canonical_external_and_read_only_to_workspace_paths(self):
        self.assertTrue(self.controller.bootstrap()["can_export"])
        self.assertEqual(self.controller.bootstrap()["store"], str(self.store))
        self.assertEqual(
            self.service.library.browse(self.root_id)["entries"][0]["path"], self.package.name
        )
        with self.assertRaisesRegex(ValueError, "inside the workspace"):
            self.service.safe_path(self.store)
        for candidate in (
            self.workspace,
            self.workspace / "results",
            self.base,
            self.store / "absent",
            self.package / "manifest.json",
        ):
            with self.subTest(candidate=candidate), self.assertRaises((OSError, ValueError)):
                store_identity(self.workspace, candidate)
        link = self.base / "linked"
        link.symlink_to(self.store, target_is_directory=True)
        with self.assertRaisesRegex(ValueError, "canonical"):
            store_identity(self.workspace, link)
        with self.assertRaisesRegex(ValueError, "canonical"):
            store_identity(self.workspace, link / self.package.name)

    def test_unconfigured_export_and_browser_supplied_paths_are_refused(self):
        self.service.close()
        self.service = Service(self.workspace, archive_roots=(self.store,))
        self.controller = self.service.durable
        self.assertFalse(self.controller.bootstrap()["can_export"])
        with self.assertRaisesRegex(ValueError, "archive-store"):
            self.controller.export({"kind": "study", "id": "job-" + "a" * 32})
        for body in (
            {"kind": "study", "id": "unknown", "checkout": str(self.workspace)},
            {"archive": str(self.package)},
            {"kind": "command", "id": "unknown"},
        ):
            with self.subTest(body=body), self.assertRaises(ValueError):
                self.controller.export(body)

    def test_terminal_study_export_uses_only_fresh_opaque_store_children(self):
        identity = "job-" + "f" * 32
        archive = self.service.data / identity / "archive"
        archive.mkdir(parents=True)
        (archive / "manifest.json").write_text("{}")
        self.service.jobs[identity] = {
            "id": identity,
            "operation": "run",
            "state": "failed",
            "verification": "not_requested",
        }
        for body in (
            {"kind": "study", "id": str(archive)},
            {"kind": "study", "id": identity, "output": str(self.package)},
            {"kind": "campaign", "id": identity},
        ):
            with self.subTest(body=body), self.assertRaises(ValueError):
                self.controller.export(body)
        before = inventory(self.store)
        request = self.controller.export({"kind": "study", "id": identity})
        entry = self.controller.get(request["entry_id"])
        self.assertEqual(request["source"]["path"], str(archive))
        self.assertEqual(request["source"]["task"], "m4-study-secure")
        self.assertEqual(request["checkout"], str(self.workspace))
        self.assertRegex(entry["path"], r"^package-[0-9a-f]{32}$")
        self.assertEqual(Path(entry["directory"]).parent, self.store)
        self.assertFalse(Path(entry["directory"]).exists())
        self.assertEqual(entry["availability"], "awaiting_export")
        self.assertNotIn("availability_error", entry)
        self.assertFalse(entry["can_verify"])
        self.assertFalse(entry["can_view_report"])
        self.assertEqual(inventory(self.store), before)

    def test_registration_refuses_traversal_links_and_gui_administration(self):
        before = dict(self.controller.registered)
        for path in (
            "../store",
            str(self.package),
            ".hidden",
            "package-existing/../package-existing",
        ):
            with self.subTest(path=path), self.assertRaises(ValueError):
                self.controller.register({"root_id": self.root_id, "path": path})
        (self.store / "link").symlink_to(self.package, target_is_directory=True)
        with self.assertRaises(ValueError):
            self.controller.register({"root_id": self.root_id, "path": "link"})
        workspace_id = self.controller.bootstrap()["roots"][0]["id"]
        for path in ("", "results", "results/gui", "results/gui/durable"):
            with self.subTest(path=path), self.assertRaisesRegex(ValueError, "administration"):
                self.controller.register({"root_id": workspace_id, "path": path})
        self.assertEqual(self.controller.registered, before)
        self.assertEqual(list(self.controller.data.glob("durable-*.json")), [])

    def test_passive_http_helpers_do_not_inventory_or_dispatch_archives(self):
        with (
            patch("experiments.gui.service.inventory", side_effect=AssertionError),
            patch("experiments.gui.durable_worker.execute", side_effect=AssertionError),
        ):
            request = self.registered()
            self.controller.get(request["entry_id"])
            self.controller.entries()
            self.controller.bootstrap()
        self.assertFalse(self.sentinel.exists())

    def test_fixed_worker_command_and_frozen_pointer_tamper_refusal(self):
        request = self.registered()
        job, _folder = self.job(request)
        command = read_json(self.service.data / job["id"] / "worker-request.json")
        self.assertEqual(command, request)
        request["path"] = "other"
        with self.assertRaisesRegex(ValueError, "Frozen durable request"):
            self.controller.commands(job)

    def test_integrity_only_is_separate_from_recorded_failed_numerical_coverage(self):
        before = inventory(self.package)
        request = self.registered()
        job, _folder = self.execute(request)
        entry = self.controller.get(request["entry_id"])
        self.assertIsNone(job["error"])
        self.assertEqual(entry["integrity"], "verified_snapshot")
        self.assertEqual(entry["reconstruction"], "not_requested")
        self.assertFalse(entry["complete"])
        self.assertFalse(entry["can_view_report"])
        self.assertEqual(inventory(self.package), before)
        self.assertFalse(self.sentinel.exists())

    def test_coherently_changed_package_cannot_repin_a_registered_identity(self):
        request = self.registered()
        self.execute(request)
        identity = request["entry_id"]
        original = self.controller.get(identity)["package_identity"]
        self.native["package_identity"] = "d" * 64
        operation = self.controller.operation("durable_verify", identity)
        job, _folder = self.execute(operation)
        self.assertIn("identity changed since registration", job["error"])
        entry = self.controller.get(identity)
        self.assertEqual(entry["package_identity"], original)
        self.assertEqual(entry["integrity"], "verification_failed")
        self.assertFalse(entry["can_view_report"])
        second = self.controller.operation("durable_verify", identity)
        self.assertEqual(second["expected_identity"], original)
        job, _folder = self.execute(second)
        self.assertIsNotNone(job["error"])
        self.assertEqual(self.controller.get(identity)["package_identity"], original)

    def test_reader_mismatch_verifies_bytes_but_never_dispatches_reconstruction(self):
        request = self.registered()
        self.execute(request)
        operation = self.controller.operation("durable_reconstruct", request["entry_id"])
        job, _folder = self.execute(operation, revision="c" * 40)
        entry = self.controller.get(request["entry_id"])
        self.assertIn("caller-trusted clean checkout", job["error"])
        self.assertNotIn("core_reconstruct", self.calls)
        self.assertEqual(entry["integrity"], "verified_snapshot")
        self.assertEqual(entry["reconstruction"], "reader_mismatch")
        self.assertFalse(entry["can_view_report"])
        self.assertFalse(entry["complete"])

    def test_failed_native_snapshot_download_and_cached_tamper_withdrawal(self):
        request = self.registered()
        self.execute(request)
        operation = self.controller.operation("durable_reconstruct", request["entry_id"])
        job, folder = self.execute(operation)
        entry = self.controller.get(request["entry_id"])
        self.assertIsNone(job["error"])
        self.assertEqual(entry["reconstruction"], "verified_snapshot")
        self.assertFalse(entry["complete"])
        self.assertEqual(
            self.controller.report_bytes(entry["id"], "report.md"),
            b"Failed numerical coverage retained.\n",
        )
        (folder / "native-report/report.md").write_text("tampered")
        with self.assertRaisesRegex(ValueError, "snapshot changed"):
            self.controller.report_bytes(entry["id"], "report.md")
        self.assertFalse(self.controller.get(entry["id"])["can_view_report"])
        self.assertEqual(
            self.controller.get(entry["id"])["reconstruction"], "changed_since_verification"
        )

    def test_post_reader_artifact_change_cannot_be_captured_as_verified(self):
        request = self.registered()
        self.execute(request)
        operation = self.controller.operation("durable_reconstruct", request["entry_id"])
        original = self.controlled_reconstruct

        def changed_after_reader(package, checkout, revision, output):
            result = original(package, checkout, revision, output)
            (output / "evidence/reconstructed/report.md").write_text("changed after native reader")
            return result

        with patch.object(self, "controlled_reconstruct", side_effect=changed_after_reader):
            job, _folder = self.execute(operation)
        entry = self.controller.get(request["entry_id"])
        self.assertIn("authoritative descriptor", job["error"])
        self.assertEqual(entry["reconstruction"], "verification_failed")
        self.assertFalse(entry["can_view_report"])

    def test_owned_cleanup_failure_cannot_promote_verified_reconstruction(self):
        request = self.registered()
        self.execute(request)
        identity = request["entry_id"]
        operation = self.controller.operation("durable_reconstruct", identity)
        job, _folder = self.execute(
            operation, owner_error="Entry owner exited with live descendants"
        )
        entry = self.controller.get(identity)
        self.assertIsNotNone(job["error"])
        self.assertEqual(entry["integrity"], "verification_failed")
        self.assertEqual(entry["reconstruction"], "verification_failed")
        self.assertFalse(entry["can_view_report"])

    def test_returned_directory_clears_stale_error_without_restoring_verification(self):
        request = self.registered()
        self.execute(request)
        identity = request["entry_id"]
        old = self.store / "temporarily-unavailable"
        self.package.rename(old)
        absent = self.controller.get(identity)
        self.assertEqual(absent["availability"], "unavailable")
        self.assertIn("availability_error", absent)
        old.rename(self.package)
        available = self.controller.get(identity)
        self.assertEqual(available["availability"], "available")
        self.assertNotIn("availability_error", available)
        self.assertEqual(available["integrity"], "changed_since_verification")
        self.assertEqual(available["reconstruction"], "changed_since_verification")
        self.assertFalse(available["can_view_report"])
        operation = self.controller.operation("durable_verify", identity)
        job, _folder = self.execute(operation)
        checked = self.controller.get(identity)
        self.assertIsNone(job["error"])
        self.assertEqual(checked["integrity"], "verified_snapshot")
        self.assertEqual(checked["availability"], "available")
        self.assertNotIn("availability_error", checked)

    def test_restart_restores_only_recorded_verification_and_replaced_directory_withdraws(self):
        request = self.registered()
        self.execute(request)
        self.service.close()
        self.service = Service(self.workspace, archive_store=self.store)
        self.controller = self.service.durable
        self.assertEqual(
            self.controller.get(request["entry_id"])["integrity"], "recorded_verification"
        )
        self.package.rename(self.store / "old")
        self.package.mkdir()
        entry = self.controller.get(request["entry_id"])
        self.assertEqual(entry["availability"], "unavailable")
        self.assertEqual(entry["integrity"], "changed_since_verification")


class SlowDurableService(Service):
    def commands(self, job, configuration, archive):
        original = super().commands(job, configuration, archive)
        if job["operation"].startswith("durable_"):
            return [([sys.executable, "-B", "-S", "-c", "import time; time.sleep(60)"], 60)]
        return original


class DurableGUITransportTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        base = Path(self.temporary.name).resolve()
        self.workspace, self.store = base / "workspace", base / "store"
        self.workspace.mkdir()
        self.store.mkdir()
        (self.store / "package").mkdir()
        self.service = SlowDurableService(self.workspace, archive_store=self.store)
        self.server = Server(self.service)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.origin = f"http://127.0.0.1:{self.server.server_port}"
        self.root_id = next(
            value["id"]
            for value in self.service.durable.bootstrap()["roots"]
            if value["directory"] == str(self.store)
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

    def test_admission_absolute_path_refusal_and_global_owned_cancellation(self):
        self.assertEqual(self.request("GET", "durable/bootstrap", token=False)[0], 403)
        self.assertEqual(self.request("GET", "durable/bootstrap")[0], 200)
        body = {"root_id": self.root_id, "path": "package"}
        self.assertEqual(self.request("POST", "durable/register", body, origin=False)[0], 403)
        self.assertEqual(
            self.request("POST", "durable/register", body | {"checkout": "/arbitrary"})[0], 400
        )
        self.assertEqual(
            self.request(
                "POST",
                "durable/register",
                {"root_id": self.root_id, "path": str(self.store / "package")},
            )[0],
            400,
        )
        status, job = self.request("POST", "durable/register", body)
        self.assertEqual(status, 202, job)
        deadline = time.monotonic() + 5
        while self.service.get_job(job["id"])["pid"] is None:
            self.assertLess(time.monotonic(), deadline)
            time.sleep(0.01)
        pid = self.service.get_job(job["id"])["pid"]
        self.assertEqual(self.request("POST", "durable/register", body)[0], 400)
        self.assertEqual(
            self.request("POST", "library/entries", body | {"task": "m4-study-secure"})[0], 400
        )
        self.assertEqual(self.request("POST", "jobs/" + job["id"] + "/cancel", {})[0], 202)
        self.service.thread.join(5)
        final = self.service.get_job(job["id"])
        self.assertEqual(final["state"], "cancelled")
        self.assertFalse(final["cleanup_forced"])
        self.assertFalse(final.get("remaining_owned_processes"))
        with self.assertRaises(ProcessLookupError):
            os.kill(pid, 0)
        self.assertEqual(
            self.request("POST", "durable/entries/" + job["request"]["entry_id"] + "/resume", {})[
                0
            ],
            404,
        )
        self.assertEqual(
            self.request(
                "POST",
                "durable/entries/" + job["request"]["entry_id"] + "/verify",
                {"revision": "a" * 40},
            )[0],
            400,
        )


class DurableGUIFrontendTests(unittest.TestCase):
    def test_deferred_native_report_and_download_freshness(self):
        import shutil
        import subprocess

        node = shutil.which("node")
        if node is None:
            self.skipTest("Node is required for controlled frontend checks")
        result = subprocess.run(
            [node, "tests/gui_durable_frontend.mjs"],
            cwd=Path(__file__).resolve().parents[1],
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        receipt = json.loads(result.stdout)
        self.assertTrue(receipt["passed"])
        self.assertEqual(receipt["checks"], 8)


if __name__ == "__main__":
    unittest.main()
