"""Library boundary tests; native-reader execution remains integrated acceptance."""

import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from experiments.catalogue import core
from experiments.gui.library import Library
from experiments.gui.library_worker import ARTIFACTS, execute
from experiments.gui.service import Service, digest, encode, inventory


class ArchiveLibraryTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.base = Path(self.temporary.name).resolve()
        self.workspace = self.base / "workspace"
        self.external = self.base / "external"
        self.workspace.mkdir()
        self.external.mkdir()
        self.archive = self.external / "archive"
        self.archive.mkdir()
        self.sentinel = self.base / "imported"
        source = f"raise RuntimeError({str(self.sentinel)!r})\n"
        (self.archive / "controller.py").write_text(source)
        (self.archive / "workflow.json").write_bytes(
            encode(
                {
                    "schema": "opent1d.p1-external-workflow/1",
                    "profile": "adult#001",
                    "seed": 101,
                    "controller": {"name": "opaque", "source_sha256": digest(source.encode())},
                    "implementation_sha256": {"native": "0" * 64},
                }
            )
        )
        (self.archive / "study.json").write_bytes(
            encode(
                {
                    "schema": "opent1d.p1-external-workflow/1",
                    "cases": ["A"],
                    "status": "completed",
                }
            )
        )
        self.service = Service(self.workspace, archive_roots=(self.external,))
        self.library = self.service.library
        self.root_id = next(
            r["id"] for r in self.library.roots() if r["directory"] == str(self.external)
        )
        self.counter = 0

    def tearDown(self):
        self.service.close()
        self.temporary.cleanup()

    def add(self, task="p1-controller"):
        return self.library.add(
            {"root_id": self.root_id, "path": "archive", "task": task, "tags": ["synthetic"]}
        )

    def operation(self, request, *, cancel=False, error=None):
        self.counter += 1
        identity = "job-" + str(self.counter).zfill(32)
        folder = self.service.data / identity
        folder.mkdir()
        job = {
            "id": identity,
            "request": request,
            "operation": request["operation"],
            "state": "running",
            "exit_code": None,
            "error": error,
            "cancel_requested": cancel,
            "cleanup_forced": False,
            "result": None,
        }
        self.library.commands(job)
        if not cancel:
            result = execute(request, folder)
            job["exit_code"] = 0 if result["status"] == "completed" else 1
        self.library.finish(job)
        return job

    def test_explicit_roots_browse_and_no_workspace_output_relaxation(self):
        self.assertEqual(self.library.browse(self.root_id)["entries"][0]["path"], "archive")
        with self.assertRaisesRegex(ValueError, "inside the workspace"):
            self.service.safe_path(self.archive)
        with self.assertRaises(ValueError):
            self.library.browse("root-does-not-exist")
        for path in ("../outside", "/absolute", ".hidden", "archive/../archive"):
            with self.subTest(path=path), self.assertRaises(ValueError):
                self.library.browse(self.root_id, path)

    def test_hide_restore_survives_restart_and_never_changes_archive_bytes(self):
        request = self.add()
        identity = request["entry"]["id"]
        before = inventory(self.archive)
        self.assertTrue(self.library.set_hidden(identity, True)["hidden"])
        self.assertFalse(self.library.get(identity)["can_verify"])
        self.assertFalse(self.library.get(identity)["can_view_report"])
        with self.assertRaisesRegex(ValueError, "Restore"):
            self.library.verify(identity)
        # An unavailable root must still allow pointer cleanup, without granting access.
        self.service.close()
        self.service = Service(self.workspace)
        self.library = self.service.library
        self.assertTrue(self.library.get(identity)["hidden"])
        self.assertEqual(self.library.get(identity)["availability"], "unavailable")
        restored = self.library.set_hidden(identity, False)
        self.assertFalse(restored["hidden"])
        self.assertEqual(restored["availability"], "unavailable")
        self.assertFalse(restored["can_view_report"])
        self.assertEqual(inventory(self.archive), before)
        self.service.close()
        self.service = Service(self.workspace, archive_roots=(self.external,))
        self.library = self.service.library
        reconnected = self.library.get(identity)
        self.assertEqual(reconnected["availability"], "available")
        self.assertNotIn("availability_error", reconnected)
        self.assertFalse(reconnected["can_view_report"])

    def test_hide_is_strict_bounded_and_shares_operation_ownership(self):
        identity = self.add()["entry"]["id"]
        for value in (0, 1, "true", None, {}):
            with self.subTest(value=value), self.assertRaises(ValueError):
                self.library.set_hidden(identity, value)
        with self.assertRaisesRegex(ValueError, "Unknown"):
            self.library.set_hidden("unknown", True)
        self.service.active = "owned-operation"
        try:
            with self.assertRaisesRegex(ValueError, "One active operation"):
                self.library.set_hidden(identity, True)
        finally:
            self.service.active = None
        self.assertFalse(self.library.get(identity).get("hidden", False))

    def test_admin_ancestors_and_descendants_cannot_be_registered(self):
        own_root = self.library.roots()[0]["id"]
        for path in ("", "results", "results/gui", "results/gui/library"):
            with (
                self.subTest(path=path),
                self.assertRaisesRegex(ValueError, "overlap|administration"),
            ):
                self.library.add({"root_id": own_root, "path": path, "task": "m4-study-secure"})

    def test_symlink_components_and_nonregular_archive_entries_are_refused(self):
        (self.external / "link").symlink_to(self.archive, target_is_directory=True)
        with self.assertRaises(ValueError):
            self.library.add({"root_id": self.root_id, "path": "link", "task": "p1-controller"})
        os.mkfifo(self.archive / "pipe")
        job = self.operation(self.add())
        self.assertEqual(job["result"]["status"], "failed")
        self.assertIsNotNone(job["error"])

    def test_index_uses_real_passive_catalogue_and_never_imports_archived_python(self):
        before = inventory(self.archive)
        with patch("experiments.catalogue.core.subprocess.Popen", side_effect=AssertionError):
            request = self.add()
            job = self.operation(request)
        item = self.library.get(request["entry"]["id"])
        self.assertEqual(item["metadata_status"], "metadata_read")
        self.assertEqual(item["metadata"]["recorded_status"], "completed")
        self.assertEqual(item["verification"], "not_requested")
        self.assertEqual(job["exit_code"], 0)
        self.assertEqual(inventory(self.archive), before)
        self.assertFalse(self.sentinel.exists())
        self.assertFalse(item["can_verify"])

    def test_all_registered_routes_accept_explicit_pointer_and_retain_metadata_errors(self):
        for task in core.TASKS:
            with self.subTest(task=task):
                request = self.add(task)
                job = self.operation(request)
                item = self.library.get(request["entry"]["id"])
                self.assertEqual(job["exit_code"], 0)
                self.assertIn(item["metadata_status"], {"metadata_read", "unavailable"})
                if task != "p1-controller":
                    self.assertIsNotNone(item["metadata_error"])
        self.assertEqual(len(self.library.entries()), len(core.TASKS))
        self.assertEqual(len(self.library.entries({"task": "m3-forecast", "tag": "synthetic"})), 1)

    def test_registration_and_listing_never_hash_whole_archives_on_http_paths(self):
        with patch("experiments.gui.library_worker.inventory", side_effect=AssertionError):
            request = self.add()
            self.library.get(request["entry"]["id"])
            self.library.entries({"text": "archive"})
            self.library.browse(self.root_id)

    def test_replaced_archive_or_removed_startup_root_withdraws_previous_verification(self):
        request = self.add()
        item = self.library.registered[request["entry"]["id"]]
        item.update(verification="native_reader_verified", verified_job="job-previous")
        self.library.persist(item)
        self.archive.rename(self.external / "old")
        self.archive.mkdir()
        self.assertEqual(self.library.get(item["id"])["verification"], "changed_since_verification")
        library = Library(self.service)
        self.assertEqual(library.get(item["id"])["availability"], "unavailable")

    def test_root_identity_is_stable_when_startup_root_order_changes(self):
        request = self.add()
        extra = self.base / "second-root"
        extra.mkdir()
        other = Library(self.service, (extra, self.external))
        self.assertEqual(other.get(request["entry"]["id"])["availability"], "available")

    def test_restart_withdraws_live_verification_and_does_not_adopt_pid(self):
        request = self.add()
        entry = self.library.registered[request["entry"]["id"]]
        entry.update(verification="native_reader_verified", verified_job="job-historical")
        self.library.persist(entry)
        restored = Library(self.service, (self.external,))
        self.assertEqual(restored.get(entry["id"])["verification"], "recorded_verification")

    def test_cancelled_or_missing_worker_receipt_cannot_grant_verification(self):
        request = self.add("m4-study-secure")
        cancelled = self.operation(request, cancel=True)
        self.assertIsNone(cancelled["error"])
        item = self.library.get(request["entry"]["id"])
        self.assertEqual(item["verification"], "not_requested")
        self.assertFalse(item["can_view_report"])

    def test_in_place_mutation_after_index_is_refused_before_native_reader_dispatch(self):
        request = self.add("m4-study-secure")
        self.operation(request)
        identity = request["entry"]["id"]
        (self.archive / "controller.py").write_text("changed in place")
        verify = self.library.verify(identity)
        with patch("experiments.catalogue.core.verify_one", side_effect=AssertionError):
            job = self.operation(verify)
        self.assertEqual(job["exit_code"], 1)
        self.assertEqual(self.library.get(identity)["verification"], "changed_since_verification")
        self.assertIn("changed since indexing", job["error"])

    def simulated_verified_report(self, passed=False):
        request = self.add("m4-study-secure")
        self.operation(request)
        identity = request["entry"]["id"]

        def native(_item, output, allow_failed):
            self.assertTrue(allow_failed)
            output.mkdir()
            report = {
                "schema": "m4-secure-study-report/1",
                "protocol": "M4-STUDY/2",
                "passed": passed,
                "denominators": {
                    "sources": 2,
                    "accepted_sources": 0,
                    "source_scenarios": 2,
                    "accepted_source_scenarios": 0,
                    "pairs": 1,
                    "accepted_pairs": 0,
                },
                "sources": {},
                "pairs": [
                    {
                        "left": "left",
                        "right": "right",
                        "accepted": False,
                        "reason": "sources not fully accepted",
                        "scenarios": {},
                    }
                ],
            }
            (output / "report.json").write_bytes(encode(report))
            (output / "report.md").write_text("synthetic stubbed reader boundary\n")
            (output / "figure.svg").write_text("<svg/>")
            return {"status": "verified_reconstruction", "complete": passed, "error": None}

        with patch("experiments.catalogue.core.verify_one", side_effect=native):
            job = self.operation(self.library.verify(identity))
        self.assertIsNone(job["error"])
        return identity

    def test_stubbed_reader_separates_successful_reconstruction_and_failed_study(self):
        identity = self.simulated_verified_report()
        report = self.library.report(identity)
        self.assertEqual(report["verification"], "native_reader_verified")
        self.assertEqual(report["report_completeness"], "failed")
        self.assertFalse(report["passed"])
        self.assertEqual(report["denominators"]["source_scenarios"], 2)
        self.assertEqual(report["source_freshness"], "not_rechecked_since_worker")
        self.assertEqual(report["pairs"][0]["left"], "left")
        self.assertFalse(report["pairs"][0]["accepted"])

    def test_modified_snapshot_bytes_withdraw_verification_for_every_artifact(self):
        for name in ARTIFACTS:
            with self.subTest(name=name):
                identity = self.simulated_verified_report()
                self.library.report_file(identity, name).write_text("replacement")
                with self.assertRaisesRegex(ValueError, "artifact changed"):
                    self.library.report_bytes(identity, name)
                self.assertEqual(
                    self.library.get(identity)["verification"], "changed_since_verification"
                )

    def test_forged_saved_receipt_with_malformed_report_shapes_raises_value_error(self):
        identity = self.simulated_verified_report()
        path = self.library.report_file(identity, "report.json")
        original = self.library.report(identity)
        malformed = (
            ("sources", []),
            ("sources", None),
            ("sources", {"left": None}),
            ("sources", {"left": []}),
            ("sources", {"left": {"declaration": []}}),
            ("sources", {"left": {"declaration": None}}),
            ("pairs", {}),
            ("pairs", None),
            ("pairs", [None]),
            ("pairs", [[]]),
            ("limitations", {}),
            ("limitations", None),
            ("limitations", [None]),
        )
        for field, value in malformed:
            with self.subTest(field=field, value=value):
                raw = encode({**original, field: value})
                path.write_bytes(raw)
                entry = self.library.registered[identity]
                entry["artifacts_sha256"]["report.json"] = digest(raw)
                self.library.persist(entry)
                restored = Library(self.service, (self.external,))
                with self.assertRaisesRegex(ValueError, "Malformed maintained M4 report"):
                    restored.report(identity)

    def test_valid_report_source_declaration_pair_and_limitations_remain_visible(self):
        identity = self.simulated_verified_report()
        path = self.library.report_file(identity, "report.json")
        report = self.library.report(identity)
        report.update(
            sources={
                "left": {
                    "status": "failed",
                    "accepted": False,
                    "declaration": {"ancestry": "synthetic reader-boundary fixture"},
                }
            },
            limitations=["Stubbed reader; no native scientific execution"],
        )
        raw = encode(report)
        path.write_bytes(raw)
        self.library.registered[identity]["artifacts_sha256"]["report.json"] = digest(raw)
        view = self.library.report(identity)
        self.assertEqual(view["sources"]["left"]["ancestry"], "synthetic reader-boundary fixture")
        self.assertFalse(view["pairs"][0]["accepted"])
        self.assertEqual(view["limitations"], report["limitations"])

    def test_archive_mutation_during_index_is_not_a_successful_snapshot(self):
        original = core.index

        def changing(*args):
            data = original(*args)
            (self.archive / "controller.py").write_text("mutated after metadata")
            return data

        with patch("experiments.catalogue.core.index", side_effect=changing):
            job = self.operation(self.add())
        self.assertEqual(job["exit_code"], 1)
        self.assertIn("changed during", job["error"])
        entry = self.library.get(job["request"]["entry"]["id"])
        self.assertEqual(entry["metadata_status"], "unavailable")
        self.assertIn("changed during", entry["metadata_error"])


if __name__ == "__main__":
    unittest.main()
