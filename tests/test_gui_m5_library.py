"""Native M5 in-place verification, bounded snapshots and declared provenance."""

import copy
import json
import shutil
import signal
import subprocess
import sys
import tempfile
import time
import unittest
import uuid
from pathlib import Path
from unittest.mock import patch

from experiments.catalogue import core, formats
from experiments.gui import library_m5, library_worker
from experiments.gui.library import Library
from experiments.gui.service import Service, bounded_bytes, digest, encode, inventory
from experiments.m5.researcher_workflow import report as native_report
from experiments.m5.researcher_workflow import run
from tests import test_m5_researcher_workflow as native_tests

ROOT = Path(__file__).resolve().parents[1]


def prepare_cases(root):
    """Execute trusted invented examples before exercising any GUI reader."""
    marker = root / "candidate-imported"
    cases = {}
    for name in ("complete", "mixed", "zero", "interrupted"):
        bundle = root / (name + "-bundle")
        run.export_example(bundle)
        prefix = f"from pathlib import Path\nPath({str(marker)!r}).touch()\n"
        if name == "complete":
            source = prefix + (bundle / "model.py").read_text()
        elif name == "mixed":
            source = (
                prefix
                + """import os

def predict(record, state):
    prior = record['prior_insulin_u_day']
    if prior == 31:
        raise RuntimeError('deliberate synthetic failure')
    if prior == 29:
        return True
    if prior == 27:
        return os.getpid() / 1000000
    return prior
"""
            )
        elif name == "zero":
            source = prefix + "def predict(record, state):\n    raise RuntimeError('no pairs')\n"
        else:
            source = (
                prefix
                + "import time\ndef predict(record, state):\n    time.sleep(30)\n    return 1\n"
            )
        native_tests.M5ResearcherWorkflowTests.change_model(bundle, source=source.encode())
        archive = root / name
        if name != "interrupted":
            cases[name] = run.execute(bundle, archive)
        else:
            marker.unlink()
            process = subprocess.Popen(
                [
                    sys.executable,
                    "-B",
                    "-E",
                    "-s",
                    "-S",
                    "-m",
                    "experiments.m5.researcher_workflow.run",
                    "run",
                    str(bundle),
                    str(archive),
                    "--timeout-seconds",
                    "30",
                ],
                cwd=ROOT,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            try:
                deadline = time.monotonic() + 10
                while not marker.exists():
                    if process.poll() is not None or time.monotonic() >= deadline:
                        raise AssertionError("Synthetic M5 worker did not become active")
                    time.sleep(0.02)
                process.send_signal(signal.SIGTERM)
                if process.wait(timeout=10) == 0:
                    raise AssertionError("Interrupted M5 runner unexpectedly succeeded")
            finally:
                if process.poll() is None:
                    process.kill()
                    process.wait()
            cases[name] = native_report.reconstruct(archive)
        shutil.rmtree(bundle)
    marker.unlink()
    return cases, marker


class M5Fixtures:
    @classmethod
    def setUpClass(cls):
        cls.fixtures = tempfile.TemporaryDirectory(prefix="opent1d-gui-m5-")
        cls.fixture_root = Path(cls.fixtures.name)
        cls.cases, cls.marker = prepare_cases(cls.fixture_root)

    @classmethod
    def tearDownClass(cls):
        cls.fixtures.cleanup()


class M5LibraryTests(M5Fixtures, unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.base = Path(self.temporary.name).resolve()
        self.workspace, self.external = self.base / "workspace", self.base / "external"
        self.workspace.mkdir()
        self.external.mkdir()
        for name in self.cases:
            shutil.copytree(self.fixture_root / name, self.external / name)
        self.service = Service(self.workspace, archive_roots=(self.external,))
        self.library = self.service.library
        self.root_id = next(
            item["id"] for item in self.library.roots() if item["directory"] == str(self.external)
        )

    def tearDown(self):
        self.service.close()
        self.temporary.cleanup()

    def operation(self, request, *, cancel=False):
        identity = "job-" + uuid.uuid4().hex
        folder = self.service.data / identity
        folder.mkdir()
        job = {
            "id": identity,
            "request": request,
            "operation": request["operation"],
            "state": "running",
            "exit_code": None,
            "error": None,
            "cancel_requested": cancel,
            "cleanup_forced": False,
            "result": None,
        }
        self.library.commands(job)
        if not cancel:
            result = library_worker.execute(request, folder)
            job["exit_code"] = 0 if result["status"] == "completed" else 1
        self.library.finish(job)
        return job

    def index(self, name="complete"):
        request = self.library.add({"root_id": self.root_id, "path": name, "task": "m5-prognosis"})
        job = self.operation(request)
        self.assertIsNone(job["error"], job)
        return request["entry"]["id"]

    def verified(self, name="complete"):
        identity = self.index(name)
        job = self.operation(self.library.verify(identity))
        self.assertIsNone(job["error"], job)
        self.assertEqual(job["verification"], "native_reader_verified")
        return identity

    def test_actual_native_rosters_failures_nulls_and_original_bytes(self):
        for name, native in self.cases.items():
            with self.subTest(name=name):
                source = self.external / name
                before = inventory(source, files=True)
                identity = self.verified(name)
                view = self.library.report(identity)
                self.assertEqual(view["native_report"], native)
                self.assertEqual(
                    view["report_completeness"], "complete" if name == "complete" else "incomplete"
                )
                self.assertEqual(view["source_freshness"], "not_rechecked_since_worker")
                self.assertEqual(len(native["people"]), 32)
                self.assertEqual(len(native["evaluation_predictions"]), 7)
                declaration = json.loads((source / "model.json").read_bytes())
                self.assertEqual(view["model_declaration"], declaration)
                self.assertEqual(view["model_declaration_sha256"], digest(encode(declaration)))
                self.assertEqual(
                    self.library.get(identity)["model_declaration_sha256"],
                    view["model_declaration_sha256"],
                )
                for artifact in ("report.json", "report.md"):
                    self.assertEqual(
                        self.library.report_bytes(identity, artifact),
                        (source / artifact).read_bytes(),
                    )
                self.assertEqual(before, inventory(source, files=True))
                self.assertFalse(self.marker.exists(), "Reader executed retained candidate")
        zero = self.cases["zero"]
        self.assertTrue(zero["candidate_execution_complete"])
        self.assertEqual(zero["paired_count"], 0)
        self.assertIsNone(zero["candidate_mae_paired_u_day"])
        interrupted = self.cases["interrupted"]
        self.assertFalse(interrupted["candidate_execution_complete"])
        self.assertIn(
            "interrupted",
            [item["candidate_status"] for item in interrupted["evaluation_predictions"]],
        )
        self.assertIn(
            "not_attempted",
            [item["candidate_status"] for item in interrupted["evaluation_predictions"]],
        )

    def test_fixed_native_reader_has_no_output_argument(self):
        self.assertEqual(
            formats.reconstruction_args("m5-prognosis", Path("/source"), Path("/fresh"), True),
            ["-m", "experiments.m5.researcher_workflow.run", "reconstruct", "/source"],
        )
        self.assertEqual(
            library_worker.ARTIFACTS_BY_TASK["m5-prognosis"], ("report.json", "report.md")
        )
        identity = self.verified()
        for name in ("figure.svg", "model.json", "model.py", "../report.json"):
            with self.assertRaisesRegex(ValueError, "artifact"):
                self.library.report_bytes(identity, name)
        self.assertTrue(self.library.get(identity)["can_view_report"])

    def test_missing_reports_unsealed_tamper_extra_oversize_and_reader_identity_refused(self):
        mutations = {
            "missing-json": lambda p: (p / "report.json").unlink(),
            "missing-md": lambda p: (p / "report.md").unlink(),
            "unsealed": lambda p: (p / "manifest.json").unlink(),
            "tamper": lambda p: (p / "report.md").write_text("changed"),
            "extra": lambda p: (p / "extra.txt").write_text("opaque extra"),
            "oversize": lambda p: (p / "model.py").write_bytes(b"#" * 500_001),
            "reader": lambda p: (p / "source-report.py").write_text("# incompatible reader\n"),
            "lock": lambda p: (p / "tooling-uv.lock").write_text("# incompatible lock\n"),
        }
        for name, mutate in mutations.items():
            with self.subTest(name=name):
                archive = self.external / name
                shutil.copytree(self.fixture_root / "complete", archive)
                mutate(archive)
                if name in {"reader", "lock"}:
                    native_tests.M5ResearcherWorkflowTests.rehash(archive)
                before = inventory(archive, files=True)
                identity = self.index(name)
                job = self.operation(self.library.verify(identity))
                self.assertIsNotNone(job["error"], job)
                self.assertFalse(self.library.get(identity)["can_view_report"])
                self.assertNotIn("model_declaration", self.library.get(identity))
                with self.assertRaises(ValueError):
                    self.library.report(identity)
                self.assertEqual(before, inventory(archive, files=True))
        archive = self.external / "linked"
        shutil.copytree(self.fixture_root / "complete", archive)
        (archive / "state.json").unlink()
        (archive / "state.json").symlink_to(self.fixture_root / "complete/state.json")
        request = self.library.add(
            {"root_id": self.root_id, "path": "linked", "task": "m5-prognosis"}
        )
        self.assertIsNotNone(self.operation(request)["error"])
        identity = request["entry"]["id"]
        self.assertFalse(self.library.get(identity)["can_verify"])
        with self.assertRaises(ValueError):
            self.library.verify(identity)

    def test_source_change_before_or_after_reader_withdraws_snapshot(self):
        identity = self.verified()
        (self.external / "complete/report.md").write_text("changed since indexing")
        with patch.object(core, "verify_one", side_effect=AssertionError("Must not launch reader")):
            job = self.operation(self.library.verify(identity))
        self.assertEqual(job["result"]["verification"], "changed_since_verification")
        self.assertFalse(self.library.get(identity)["can_view_report"])
        identity = self.index("mixed")
        original = core.verify_one

        def changing(item, output, allow_failed):
            result = original(item, output, allow_failed)
            (self.external / "mixed/report.md").write_text("changed after native reader")
            return result

        with patch.object(core, "verify_one", side_effect=changing):
            job = self.operation(self.library.verify(identity))
        self.assertEqual(job["result"]["verification"], "changed_since_verification")
        self.assertFalse(self.library.get(identity)["can_view_report"])

    def test_transient_copy_substitution_restored_source_cannot_publish(self):
        for artifact in ("report.json", "report.md", "model.json"):
            with self.subTest(artifact=artifact):
                identity = self.index()
                source = self.external / "complete" / artifact
                before = inventory(source.parent, files=True)
                original = library_worker.bounded_bytes

                def substituted(path, maximum):
                    raw = original(path, maximum)
                    if path == source and maximum == library_m5.MAX_NATIVE_FILE:
                        source.write_bytes(b"substitution")
                        forged = original(path, maximum)
                        source.write_bytes(raw)
                        return forged
                    return raw

                with patch.object(library_worker, "bounded_bytes", side_effect=substituted):
                    job = self.operation(self.library.verify(identity))
                self.assertEqual(job["result"]["verification"], "changed_since_verification")
                self.assertFalse(self.library.get(identity)["can_view_report"])
                self.assertEqual(before, inventory(source.parent, files=True))

    def test_post_write_target_substitution_cannot_publish_native_snapshot(self):
        for artifact in ("report.json", "report.md"):
            with self.subTest(artifact=artifact):
                identity = self.index()
                original = library_worker.file_digest

                def substituted(path, maximum=67108864):
                    if path.name == artifact and path.parent.name == "reconstructed":
                        path.write_bytes(b"changed after copy")
                    return original(path, maximum)

                with patch.object(library_worker, "file_digest", side_effect=substituted):
                    job = self.operation(self.library.verify(identity))
                self.assertIn("snapshot artifact changed", job["error"])
                self.assertFalse(self.library.get(identity)["can_view_report"])
                self.assertNotIn("model_declaration", self.library.get(identity))

    def test_report_and_declaration_tamper_withdraw_every_artifact(self):
        for target in ("report.json", "report.md", "declaration", "receipt"):
            with self.subTest(target=target):
                identity = self.verified()
                entry = self.library.registered[identity]
                if target.startswith("report"):
                    self.library.report_file(identity, target).write_text("changed")
                elif target == "declaration":
                    entry["model_declaration"]["rights_basis"] = "changed declaration"
                    entry["model_declaration_sha256"] = digest(encode(entry["model_declaration"]))
                else:
                    receipt = self.service.data / entry["verified_job"] / "worker-result.json"
                    value = json.loads(receipt.read_bytes())
                    value["model_declaration"]["rights_basis"] = "changed receipt"
                    receipt.write_bytes(encode(value))
                with self.assertRaises(ValueError):
                    self.library.report_bytes(
                        identity, "report.md" if target != "report.json" else "report.json"
                    )
                self.assertFalse(self.library.get(identity)["can_view_report"])
                self.assertNotIn("model_declaration", self.library.get(identity))
                for name in ("report.json", "report.md"):
                    with self.assertRaises(ValueError):
                        self.library.report_bytes(identity, name)

    def test_changed_artifact_digest_and_missing_catalogue_cannot_forge_bindings(self):
        identity = self.verified()
        path = self.library.report_file(identity, "report.md")
        path.write_bytes(b"changed but coherently rehashed")
        self.library.registered[identity]["artifacts_sha256"]["report.md"] = digest(
            path.read_bytes()
        )
        with self.assertRaisesRegex(ValueError, "artifact binding changed"):
            self.library.report(identity)
        self.assertFalse(self.library.get(identity)["can_view_report"])
        identity = self.index()
        original = library_worker.execute

        def missing(request, output):
            result = original(request, output)
            result["catalogue_sha256"] = None
            (output / "worker-result.json").write_bytes(encode(result))
            return result

        with patch.object(library_worker, "execute", side_effect=missing):
            job = self.operation(self.library.verify(identity))
        self.assertIn("declaration differs from verified catalogue", job["error"])
        self.assertFalse(self.library.get(identity)["can_view_report"])

    def test_http_report_reads_owned_snapshot_only_and_restart_is_recorded(self):
        identity = self.verified()
        restored = Library(self.service, (self.external,))
        self.assertEqual(restored.get(identity)["verification"], "recorded_verification")
        with patch.object(
            library_worker, "inventory", side_effect=AssertionError("HTTP source scan")
        ):
            original = bounded_bytes

            def owned_only(path, maximum):
                if self.external in path.parents:
                    raise AssertionError("HTTP reopened original input")
                return original(path, maximum)

            with patch("experiments.gui.library.bounded_bytes", side_effect=owned_only):
                self.assertEqual(restored.report(identity)["native_report"], self.cases["complete"])
                restored.report_bytes(identity, "report.md")
        self.assertIsNone(self.service.active)
        with patch.object(run, "fit", side_effect=AssertionError("Reader refitted")):
            native_report.reconstruct(self.external / "complete")

    def test_malformed_scope_accounting_and_declaration_refused(self):
        original = self.cases["complete"]
        mutations = {
            "human": lambda r: r.update(human_execution_authorized=True),
            "treatment": lambda r: r.update(treatment_effect_or_cure_estimated=True),
            "count": lambda r: r.update(roster_count=True),
            "missing-person": lambda r: r["people"].pop(),
            "paired": lambda r: r.update(paired_count=0),
            "execution": lambda r: r.update(candidate_execution_complete=False),
            "attempt": lambda r: r["evaluation_predictions"][0]["attempts"].pop(),
            "wrong-status": lambda r: r["evaluation_predictions"][0].update(
                candidate_status="failed"
            ),
            "wrong-unit": lambda r: r.update(metric="mg/dL"),
        }
        for name, mutate in mutations.items():
            value = copy.deepcopy(original)
            mutate(value)
            with self.subTest(name=name), self.assertRaises(ValueError):
                library_m5.validate_report(value)
        declared = json.loads((self.external / "complete/model.json").read_bytes())
        for key, value in (
            ("source_sha256", "0" * 64),
            ("output_unit", "mg/dL"),
            ("rights_basis", ""),
            ("training", {}),
        ):
            changed = copy.deepcopy(declared)
            changed[key] = value
            with self.subTest(key=key), self.assertRaises(ValueError):
                library_m5.validate_declaration(changed, original)

    def test_reader_completeness_and_receipt_binding_cannot_be_forged(self):
        identity = self.index()
        original = core.verify_one

        def disagreement(item, output, allow_failed):
            value = original(item, output, allow_failed)
            value["complete"] = False
            return value

        with patch.object(core, "verify_one", side_effect=disagreement):
            job = self.operation(self.library.verify(identity))
        self.assertIn("completeness differ", job["error"])
        self.assertFalse(self.library.get(identity)["can_view_report"])
        execute = library_worker.execute

        def forged(request, output):
            value = execute(request, output)
            value["model_declaration_sha256"] = "0" * 64
            (output / "worker-result.json").write_bytes(encode(value))
            return value

        with patch.object(library_worker, "execute", side_effect=forged):
            job = self.operation(self.library.verify(identity))
        self.assertIn("declaration digest", job["error"])
        self.assertFalse(self.library.get(identity)["can_view_report"])

    def test_rehashed_target_receipt_cannot_replace_initial_native_report_bytes(self):
        identity = self.index()
        original = library_worker.execute

        def forged(request, output):
            result = original(request, output)
            target = output / "reconstructed/report.md"
            target.write_bytes(b"coherently substituted after worker completion")
            result["artifacts_sha256"]["report.md"] = digest(target.read_bytes())
            (output / "worker-result.json").write_bytes(encode(result))
            return result

        with patch.object(library_worker, "execute", side_effect=forged):
            job = self.operation(self.library.verify(identity))
        self.assertIn("copied artifacts differ from frozen source inventory", job["error"])
        self.assertFalse(self.library.get(identity)["can_view_report"])
        self.assertNotIn("model_declaration", self.library.get(identity))

    def test_rehashed_valid_receipt_declaration_cannot_replace_verified_catalogue(self):
        identity = self.index()
        original = library_worker.execute

        def forged(request, output):
            result = original(request, output)
            result["model_declaration"]["rights_basis"] = "different valid supplier declaration"
            result["model_declaration_sha256"] = digest(encode(result["model_declaration"]))
            (output / "worker-result.json").write_bytes(encode(result))
            return result

        with patch.object(library_worker, "execute", side_effect=forged):
            job = self.operation(self.library.verify(identity))
        self.assertIn("declaration differs from verified catalogue", job["error"])
        self.assertFalse(self.library.get(identity)["can_view_report"])
        self.assertNotIn("model_declaration", self.library.get(identity))

    def test_cancelled_verification_cannot_grant_a_new_snapshot(self):
        identity = self.index()
        self.operation(self.library.verify(identity), cancel=True)
        self.assertFalse(self.library.get(identity)["can_view_report"])
        identity = self.verified()
        self.operation(self.library.verify(identity), cancel=True)
        self.assertEqual(self.library.get(identity)["verification"], "recorded_verification")
        self.assertEqual(self.library.report(identity)["native_report"], self.cases["complete"])
        request = self.library.verify(identity)
        self.library.registered[identity]["tags"] = ["changed"]
        with self.assertRaisesRegex(ValueError, "Frozen library request"):
            self.library.commands({"request": request, "operation": "library_verify"})


if __name__ == "__main__":
    unittest.main()
