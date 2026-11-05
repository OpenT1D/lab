"""LT1 preparation acceptance and refusal controls; no native execution."""

import copy
import hashlib
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from experiments.adapter_audit.check import HERE
from experiments.adapter_audit.lt1_packet import inspect

ROOT = HERE.parents[1]


class LT1PreparationTests(unittest.TestCase):
    def setUp(self):
        self.raw = (HERE / "lt1-fixture-ledger.json").read_bytes()
        self.packet = json.loads(self.raw)
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name) / "packet.json"
        self.path.write_bytes(self.raw)

    def reject(self, mutate, reason):
        inspect(self.path)
        value = copy.deepcopy(self.packet)
        mutate(value)
        self.path.write_text(json.dumps(value))
        with self.assertRaisesRegex(ValueError, reason):
            inspect(self.path)

    def test_complete_support_first_failure_and_relocated_no_site_reader(self):
        result = inspect(self.path)
        self.assertEqual(result["planned_slots"], 3)
        self.assertEqual(result["unattempted"], ["unattempted"])
        self.assertEqual(result["first_attempt_status"]["failure-retry"], "failed")
        self.assertEqual(len(result["attempts"]), 3)
        run = subprocess.run(
            [sys.executable, "-S", "-m", "experiments.adapter_audit.lt1_packet", str(self.path)],
            cwd=ROOT,
            capture_output=True,
            text=True,
            timeout=20,
            check=True,
        )
        self.assertEqual(json.loads(run.stdout), result)

    def test_native_kind_cannot_claim_admission(self):
        self.reject(lambda p: p.update(kind="native"), "fixture-only")

    def test_passive_inventory_and_historical_protected_bytes(self):
        original = json.loads((HERE / "runtime-rights.json").read_bytes())
        candidate = json.loads((HERE / "lt1-candidate-review.json").read_bytes())
        self.assertTrue(all(value is False for value in candidate["authorizations"].values()))
        self.assertEqual(
            candidate["historical_lock_sha256"],
            original["protected_files"]["experiments/m0/lt1/package-lock.json"],
        )
        expected = {p["name"]: p for p in original["lt1"]["packages"]}
        self.assertEqual({p["name"] for p in candidate["npm_artifacts"]}, set(expected))
        for artifact in candidate["npm_artifacts"]:
            self.assertEqual(artifact["version"], expected[artifact["name"]]["version"])
            self.assertTrue(artifact["notices"])
        for name, digest in original["protected_files"].items():
            self.assertEqual(hashlib.sha256((ROOT / name).read_bytes()).hexdigest(), digest, name)

    def test_missing_planned_slot_or_changed_fixture_identity(self):
        self.reject(lambda p: p["slots"].pop(), "planned-support")
        self.path.write_bytes(self.raw)
        self.reject(lambda p: p.update(fixture_sha256="0" * 64), "fixture-identity")

    def test_missing_parent_with_unchanged_retry_lineage_refused(self):
        self.reject(lambda p: p["attempts"].pop(1), "retry-lineage")

    def test_consistently_rewritten_history_needs_external_trust(self):
        # Explicit limitation: a standalone invented file has no external seal.
        # The future native route must consume the existing immutable store.
        self.packet["attempts"].pop(1)
        self.packet["attempts"][-1].update(ordinal=1, retry_of=None)
        self.path.write_text(json.dumps(self.packet))
        result = inspect(self.path)
        self.assertEqual(result["first_attempt_status"]["failure-retry"], "completed")
        self.assertEqual(len(result["attempts"]), 2)

    def test_retry_cannot_skip_or_use_boolean_ordinal(self):
        self.reject(lambda p: p["attempts"][2].update(retry_of=None), "retry-lineage")
        self.path.write_bytes(self.raw)
        self.reject(lambda p: p["attempts"][0].update(ordinal=True), "retry-lineage")

    def test_unfinished_and_empty_failure_retained(self):
        value = self.packet
        attempt = value["attempts"][1]
        attempt["transcript"].update(status="started", error=None)
        value["attempts"].pop()
        self.path.write_text(json.dumps(value))
        result = inspect(self.path)
        self.assertEqual(result["first_attempt_status"]["failure-retry"], "started")
        self.assertEqual(result["attempts"][attempt["id"]]["completed_intervals"], 0)
        value["attempts"].append(copy.deepcopy(self.packet["attempts"][0]))
        value["attempts"][-1].update(
            id="invalid-retry", slot="failure-retry", ordinal=2, retry_of=attempt["id"]
        )
        self.path.write_text(json.dumps(value))
        with self.assertRaisesRegex(ValueError, "retry-lineage"):
            inspect(self.path)

    def test_truncated_completion_and_unknown_fields_refused(self):
        self.reject(lambda p: p["attempts"][0]["transcript"]["rows"].pop(), "completion")
        self.path.write_bytes(self.raw)
        self.reject(lambda p: p.update(source="execute-me.py"), "packet-fields")

    def test_duplicate_keys_and_symlink_refused(self):
        self.path.write_bytes(self.raw.replace(b'"kind": "invented"', b'"kind": 1, "kind": 2'))
        with self.assertRaisesRegex(ValueError, "Duplicate JSON key"):
            inspect(self.path)
        link = self.path.parent / "link.json"
        link.symlink_to(self.path)
        with self.assertRaisesRegex(ValueError, "Symlink"):
            inspect(link)

    @unittest.skipUnless(shutil.which("node"), "Node required for nonnative kernel checks")
    def test_sampled_kernel_against_decimal_controls_and_native_callback_shapes(self):
        run = subprocess.run(
            [shutil.which("node"), "--test", str(HERE / "test-lt1-sampled.mjs")],
            cwd=ROOT,
            capture_output=True,
            text=True,
            timeout=20,
        )
        self.assertEqual(run.returncode, 0, run.stdout + run.stderr)
