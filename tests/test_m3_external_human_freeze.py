"""Pre-scoring transfer boundaries, exclusively with self-authored inputs.

The donor declares test coefficients and historical metadata; it is not evidence
that a human model was fitted. The conversion fixture creates invented records.
No local health-data path is opened and no predictions or scores are computed.
"""

import copy
import shutil
import subprocess
import sys
import unittest
from contextlib import ExitStack
from pathlib import Path
from unittest.mock import patch

import test_m3_physiocgm_human as conversion_fixture
from test_m3_external_model import declared_fixture

from experiments.m3.azt1d.analysis import _Snapshot
from experiments.m3.azt1d.common import SCHEMA as SOURCE_SCHEMA
from experiments.m3.azt1d.ledger import _identity_sha
from experiments.m3.common import ROOT, digest, encoded, read, save
from experiments.m3.external import human_freeze
from experiments.m3.external.study import run_study, validate_plan
from experiments.m3.physiocgm import human
from experiments.m3.physiocgm.access import verify_log


class ExternalHumanFreeze(unittest.TestCase):
    def setUp(self):
        fixture = conversion_fixture.PhysioCGMHumanConversion()
        fixture.setUp()
        self.addCleanup(fixture.doCleanups)
        self.root = fixture.root
        fixture._prepare()
        self.converted = fixture.converted
        self.reconstructed = self.root / "conversion-reconstructed"
        human.verify(self.converted, self.reconstructed)
        self.source = self.root / "donor"
        self.source.mkdir(mode=0o700)
        self.donor_plan, self.fit, _ = declared_fixture(self.source, kind="human")
        plan, _ = read(self.donor_plan)
        frozen, _ = read(self.fit / "freeze.json")
        registry = {
            "schema": SOURCE_SCHEMA,
            "kind": "human",
            "people": copy.deepcopy(plan["identity"]["people"]),
        }
        registry_raw = encoded(registry)
        plan.update(
            schema=SOURCE_SCHEMA,
            registry=registry,
            registry_source_utf8=registry_raw.decode(),
            registry_sha256=digest(registry_raw),
            provenance=copy.deepcopy(frozen["provenance"]),
        )
        save(self.donor_plan, plan)
        frozen["plan_sha256"] = digest(self.donor_plan.read_bytes())
        save(self.fit / "freeze.json", frozen)
        state = {
            "schema": SOURCE_SCHEMA,
            "status": "completed",
            "elapsed_seconds": 0.0,
            "provenance": copy.deepcopy(frozen["provenance"]),
            "files": {
                "model.json": frozen["model_sha256"],
                "freeze.json": digest((self.fit / "freeze.json").read_bytes()),
                "trace.jsonl": frozen["validation_sha256"],
                "inputs.json": frozen["inputs_sha256"],
                "result.json": frozen["result_sha256"],
            },
        }
        save(self.fit / "state.json", state)
        for path in (self.source, *self.source.rglob("*")):
            path.chmod(0o700 if path.is_dir() else 0o600)
        self.request = {
            "schema": human_freeze.SCHEMA,
            "kind": "human",
            "authorization": {
                "confirmed": True,
                "scope": "local-external-freeze-only",
                "reference": "Invented test authorization, not a real consent record",
            },
            "donor": {
                name: {
                    "file": str(path),
                    "sha256": digest(path.read_bytes()),
                }
                for name, path in {
                    "plan": self.donor_plan,
                    "model": self.fit / "model.json",
                    "freeze": self.fit / "freeze.json",
                    "state": self.fit / "state.json",
                }.items()
            },
            "conversion": self._conversion_reference(self.converted),
            "reconstruction": self._conversion_reference(self.reconstructed),
            "prior_access": {
                "reviewed": True,
                "status": "present",
                "reference": "Invented inputs generated, converted and reconstructed in this test",
            },
            "overlap": {
                "assessment": "different-source-studies-person-overlap-unverified",
                "reference": "Separate invented study sources; no cross-study identity claim",
            },
        }
        self.request_path = self.root / "external-request.json"
        self.bundle = self.root / "external-frozen"
        self._save_request()

    @staticmethod
    def _conversion_reference(folder):
        return {
            "directory": str(folder),
            "manifest_sha256": digest((folder / "manifest.json").read_bytes()),
        }

    def _save_request(self):
        save(self.request_path, self.request)
        self.request_path.chmod(0o600)

    def _freeze(self):
        return human_freeze.freeze(self.request_path, self.bundle)

    def _repin(self, name):
        ref = self.request["donor"][name]
        Path(ref["file"]).chmod(0o600)
        ref["sha256"] = digest(Path(ref["file"]).read_bytes())
        self._save_request()

    def _rebind_donor_plan(self):
        """Refresh ordinary hashes so donor semantic checks are exercised."""
        frozen_path = self.fit / "freeze.json"
        frozen, _ = read(frozen_path)
        frozen["plan_sha256"] = digest(self.donor_plan.read_bytes())
        save(frozen_path, frozen)
        state_path = self.fit / "state.json"
        state, _ = read(state_path)
        state["files"]["freeze.json"] = digest(frozen_path.read_bytes())
        save(state_path, state)
        for name in ("plan", "freeze", "state"):
            self._repin(name)

    @staticmethod
    def _no_scoring():
        stack = ExitStack()
        for target in (
            "experiments.m3.azt1d.study.learned_read",
            "experiments.m3.external.model.learned_read",
            "experiments.m3.estimator.fit",
            "experiments.m3.estimator.predict",
            "experiments.m3.azt1d.data.forecast_rows",
            "experiments.m3.worker.forecast_rows",
            "experiments.m3.azt1d.analysis._expected",
            "experiments.m3.external.analysis._expected",
            "experiments.m3.external.metrics.summarize_case",
            "experiments.m3.external.metrics.summarize_study",
        ):
            stack.enter_context(patch(target, side_effect=AssertionError("No scoring in freeze")))
        return stack

    def test_complete_transfer_and_portable_verification_never_predict_or_score(self):
        with self._no_scoring():
            summary = self._freeze()
            self.assertEqual(summary["planned_people"], 10)
            self.assertGreater(summary["registered_origins"], 0)
            self.assertFalse(summary["model_fit_or_evaluation"])
            for name in ("plan", "model", "freeze", "state"):
                self.assertEqual(
                    (self.bundle / "model" / f"{name}.json").read_bytes(),
                    Path(self.request["donor"][name]["file"]).read_bytes(),
                )
            plan, _ = read(self.bundle / "plan.json")
            self.assertEqual(plan["schema"], human_freeze.SCHEMA)
            self.assertEqual(plan["kind"], "human")
            self.assertFalse(plan["evaluation_enabled"])
            self.assertFalse(plan["execution_supported"])
            self.assertEqual(len(list((self.bundle / "inputs").glob("*.json"))), 10)
            for folder in (self.source, self.converted, self.reconstructed):
                shutil.rmtree(folder)
            self.request_path.unlink()
            self.assertEqual(human_freeze.verify(self.bundle, self.root / "verified"), summary)
        for path in (self.bundle, *self.bundle.rglob("*")):
            self.assertEqual(path.stat().st_mode & 0o077, 0)

    def test_donor_observations_traces_and_scores_are_never_read_or_copied(self):
        original = _Snapshot.read
        forbidden = {"trace.jsonl", "result.json", "inputs.json"}

        def guarded(snapshot, name):
            self.assertNotIn(name, forbidden)
            return original(snapshot, name)

        with patch.object(_Snapshot, "read", guarded), self._no_scoring():
            self._freeze()
        self.assertFalse(any(path.name in forbidden for path in self.bundle.rglob("*")))

    def test_invalid_authorization_overlap_or_prior_access_fail_before_donor_read(self):
        changes = (
            ("authorization", "confirmed", False),
            ("authorization", "scope", "evaluate-now"),
            ("authorization", "reference", ""),
            ("prior_access", "status", "none"),
            ("prior_access", "reviewed", False),
            ("overlap", "assessment", "verified-no-overlap"),
        )
        original = copy.deepcopy(self.request)
        for section, key, value in changes:
            with self.subTest(section=section, key=key):
                self.request = copy.deepcopy(original)
                self.request[section][key] = value
                self.request["donor"]["model"]["file"] = str(self.root / "absent-model.json")
                self._save_request()
                with self.assertRaises(ValueError):
                    self._freeze()
                self.assertFalse(self.bundle.exists())

    def test_changed_donor_model_or_inconsistent_completed_state_is_rejected(self):
        model_path = self.fit / "model.json"
        original_model = model_path.read_bytes()
        model, _ = read(model_path)
        model["intercept"] += 1
        save(model_path, model)
        model_path.chmod(0o600)
        with self.assertRaises(ValueError):
            self._freeze()
        self._repin("model")
        with self.assertRaises(ValueError):
            human_freeze.freeze(self.request_path, self.root / "rehashed-model")
        model_path.write_bytes(original_model)
        self._repin("model")
        state_path = self.fit / "state.json"
        state, _ = read(state_path)
        state["files"]["inputs.json"] = "0" * 64
        save(state_path, state)
        self._repin("state")
        with self.assertRaises(ValueError):
            human_freeze.freeze(self.request_path, self.root / "inconsistent-state")

    def test_source_registry_bytes_cannot_be_substituted(self):
        plan, _ = read(self.donor_plan)
        plan["registry_source_utf8"] = "{}"
        save(self.donor_plan, plan)
        self._rebind_donor_plan()
        with self.assertRaises(ValueError):
            self._freeze()

    def test_donor_registry_kind_schema_and_ordered_aliases_must_match_identity(self):
        original, _ = read(self.donor_plan)
        mutations = (
            ("kind", "synthetic"),
            ("schema", "unrecognized-study/1"),
            ("people", list(reversed(original["registry"]["people"]))),
            ("people", [{"id": "different-invented-person"}]),
        )
        for index, (field, value) in enumerate(mutations):
            plan = copy.deepcopy(original)
            plan["registry"][field] = value
            raw = encoded(plan["registry"])
            plan["registry_source_utf8"] = raw.decode()
            plan["registry_sha256"] = digest(raw)
            save(self.donor_plan, plan)
            self._rebind_donor_plan()
            with self.subTest(field=field, variant=index), self.assertRaises(ValueError):
                human_freeze.freeze(self.request_path, self.root / f"registry-mismatch-{index}")

    def test_original_native_source_hash_overlap_is_rejected(self):
        conversion_plan, _ = read(self.converted / "plan.json")
        source_hash = conversion_plan["request"]["people"][0]["input"]["sha256"]
        plan, _ = read(self.donor_plan)
        plan["identity"]["people"][1]["source_sha256"] = source_hash
        plan["registry"]["people"][1]["source_sha256"] = source_hash
        registry_raw = encoded(plan["registry"])
        plan["registry_source_utf8"] = registry_raw.decode()
        plan["registry_sha256"] = digest(registry_raw)
        save(self.donor_plan, plan)
        frozen_path = self.fit / "freeze.json"
        frozen, _ = read(frozen_path)
        frozen["ledger_anchor"]["identity_sha256"] = _identity_sha(plan["identity"])
        save(frozen_path, frozen)
        self._rebind_donor_plan()
        with self.assertRaisesRegex(ValueError, "overlap"):
            self._freeze()

    def test_each_normalized_source_has_an_existing_durable_read_receipt(self):
        cohort, _ = read(self.converted / "cohort.json")
        expected = {person["id"]: person["sha256"] for person in cohort["people"]}
        read_aliases = []
        original = human._read_private
        request_sha = digest(self.request_path.read_bytes())

        def guarded(path):
            path = Path(path)
            if path.name == "observations.json":
                pid = path.parent.name
                entries = verify_log((self.bundle / "access.jsonl").read_bytes(), request_sha)
                payload = entries[-1]["payload"]
                self.assertEqual(payload["action"], "before_bundle_read")
                self.assertEqual(payload["subject"], pid)
                self.assertEqual(payload["source_sha256"], expected[pid])
                read_aliases.append(pid)
            return original(path)

        with patch.object(human, "_read_private", guarded), self._no_scoring():
            self._freeze()
        self.assertEqual(read_aliases, list(expected))
        entries = verify_log((self.bundle / "access.jsonl").read_bytes(), request_sha)
        self.assertEqual(
            [entry["payload"]["subject"] for entry in entries],
            ["donor", "conversion", *expected],
        )
        self.assertEqual(len(entries), 12)
        state, _ = read(self.bundle / "state.json")
        self.assertEqual(
            state["cases"],
            [
                {"id": pid, "status": "completed", "access_sha256": entry["sha256"]}
                for pid, entry in zip(expected, entries[2:], strict=True)
            ],
        )
        registry, _ = read(self.bundle / "registry.json")
        conversion_plan, _ = read(self.converted / "plan.json")
        self.assertEqual(
            [person["native_sha256"] for person in registry["people"]],
            [person["input"]["sha256"] for person in conversion_plan["request"]["people"]],
        )

    def test_failed_individual_receipt_prevents_that_normalized_source_read(self):
        cohort, _ = read(self.converted / "cohort.json")
        rejected = cohort["people"][0]
        read_aliases = []
        original_access = human_freeze.record_access
        original_read = human._read_private

        def reject_one(path, identity, action, subject, source):
            if subject == rejected["id"]:
                raise OSError("Invented receipt failure")
            return original_access(path, identity, action, subject, source)

        def guarded(path):
            path = Path(path)
            if path.name == "observations.json":
                read_aliases.append(path.parent.name)
                self.assertNotEqual(path.parent.name, rejected["id"])
            return original_read(path)

        with (
            patch("experiments.m3.external.human_freeze.record_access", reject_one),
            patch.object(human, "_read_private", guarded),
        ):
            with self.assertRaises((OSError, ValueError)):
                self._freeze()
        self.assertNotIn(rejected["id"], read_aliases)
        self.assertFalse((self.bundle / "inputs" / (rejected["id"] + ".json")).exists())
        self.assertFalse((self.bundle / "plan.json").exists())
        state, _ = read(self.bundle / "state.json")
        self.assertEqual(state["status"], "failed")

    def test_modified_normalized_input_is_rejected(self):
        path = next(self.converted.glob("*/observations.json"))
        document, _ = read(path)
        document["rows"][0]["value"] += 1
        save(path, document)
        path.chmod(0o600)
        with self.assertRaises(ValueError):
            self._freeze()

    def test_unrecognized_conversion_files_are_rejected(self):
        path = self.converted / "unexpected.json"
        save(path, {"invented": True})
        path.chmod(0o600)
        with self.assertRaises(ValueError):
            self._freeze()

    def test_reconstruction_receipt_must_still_match_pinned_conversion(self):
        state_path = self.reconstructed / "state.json"
        state, _ = read(state_path)
        state["bundle_manifest_sha256"] = "0" * 64
        save(state_path, state)
        state_path.chmod(0o600)
        (self.reconstructed / "manifest.json").unlink()
        human._seal(self.reconstructed)
        self.request["reconstruction"] = self._conversion_reference(self.reconstructed)
        self._save_request()
        with self.assertRaises(ValueError):
            self._freeze()

    def test_request_cannot_enable_execution_or_override_frozen_rules(self):
        original = copy.deepcopy(self.request)
        for key, value in (("evaluation_enabled", True), ("rules", {"matching": "nearest"})):
            self.request = copy.deepcopy(original)
            self.request[key] = value
            self._save_request()
            with self.subTest(key=key), self.assertRaises(ValueError):
                self._freeze()
            self.assertFalse(self.bundle.exists())

    def test_frozen_artifact_tampering_and_extra_files_are_rejected(self):
        self._freeze()
        for index, change in enumerate(("model", "input", "extra", "symlink")):
            bundle = self.root / f"tamper-{index}"
            shutil.copytree(self.bundle, bundle)
            with self.subTest(change=change):
                if change == "model":
                    (bundle / "model/model.json").write_text("{}")
                elif change == "input":
                    next((bundle / "inputs").glob("*.json")).write_text("{}")
                elif change == "extra":
                    (bundle / "unexpected").write_text("invented extra file")
                    (bundle / "unexpected").chmod(0o600)
                else:
                    target = bundle / "model/model.json"
                    target.unlink()
                    target.symlink_to(self.bundle / "model/model.json")
                with self.assertRaises(ValueError):
                    human_freeze.verify(bundle, self.root / f"tamper-check-{index}")

    def test_rehashed_plan_cannot_change_matching_or_enable_execution(self):
        self._freeze()
        for index, field in enumerate(("rules", "evaluation_enabled", "execution_supported")):
            bundle = self.root / f"plan-tamper-{index}"
            shutil.copytree(self.bundle, bundle)
            plan_path = bundle / "plan.json"
            plan, _ = read(plan_path)
            if field == "rules":
                plan["rules"]["matching"] = "nearest"
            else:
                plan[field] = True
            save(plan_path, plan)
            plan_path.chmod(0o600)
            (bundle / "manifest.json").unlink()
            human_freeze._seal(bundle)
            with self.subTest(field=field), self.assertRaisesRegex(ValueError, "plan changed"):
                human_freeze.verify(bundle, self.root / f"plan-check-{index}")

    def test_failed_read_receipt_blocks_donor_and_normalized_input_access(self):
        failed = self.root / "receipt-failed"
        with (
            patch("experiments.m3.external.human_freeze.record_access", side_effect=OSError),
            patch.object(human, "_read_private", wraps=human._read_private) as access,
        ):
            with self.assertRaises(OSError):
                human_freeze.freeze(self.request_path, failed)
            access.assert_called_once_with(self.request_path)
        state, _ = read(failed / "state.json")
        self.assertEqual(state["status"], "failed")
        self.assertFalse((failed / "model").exists())
        self.assertFalse((failed / "inputs").exists())
        self.assertTrue((failed / "manifest.json").exists())

        self._freeze()
        original = _Snapshot.read

        def guarded(snapshot, name):
            self.assertFalse(name.startswith(("inputs/", "model/")))
            self.assertNotEqual(name, "plan.json")
            return original(snapshot, name)

        with (
            patch("experiments.m3.external.human_freeze.record_access", side_effect=OSError),
            patch.object(_Snapshot, "read", guarded),
        ):
            with self.assertRaises(OSError):
                human_freeze.verify(self.bundle, self.root / "verify-receipt-failed")

    def test_current_runner_refuses_new_freeze_even_after_boolean_kind_flip(self):
        self._freeze()
        plan, _ = read(self.bundle / "plan.json")
        with patch("experiments.m3.external.study.load_model") as load:
            with self.assertRaises(ValueError):
                run_study(self.bundle / "plan.json", self.root / "forbidden-study")
            load.assert_not_called()
        for changed in (False, True):
            altered = copy.deepcopy(plan)
            altered["kind"] = "synthetic"
            altered["evaluation_enabled"] = changed
            altered["execution_supported"] = changed
            with self.subTest(enabled=changed), self.assertRaises(ValueError):
                validate_plan(altered)

    def test_standard_library_subprocess_verifies_without_training_runtime(self):
        self._freeze()
        code = (
            "import sys; from experiments.m3.external.human_freeze import verify; "
            "verify(sys.argv[1], sys.argv[2]); "
            "assert 'numpy' not in sys.modules; assert 'sklearn' not in sys.modules"
        )
        result = subprocess.run(
            [sys.executable, "-S", "-c", code, str(self.bundle), str(self.root / "stdlib-check")],
            cwd=ROOT,
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
