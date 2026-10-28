"""Recorded native claims use their declared roots and retain honest failure states."""

import json
import tempfile
import unittest
from pathlib import Path

from experiments.catalogue import core
from experiments.catalogue.claims import LAYOUTS
from experiments.catalogue.storage import ROOT, digest, dump, inventory, seal


class CatalogueClaimTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.archive = Path(self.temp.name) / "archive"
        self.archive.mkdir()

    def file(self, name, raw=b"original evidence"):
        path = self.archive / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(raw)
        return digest(raw)

    def reference_seal(self, prefix="", files=None):
        name = prefix + "reference-manifest.json"
        files = (
            files
            if files is not None
            else {"nested/trace.jsonl": self.file(prefix + "reference/nested/trace.jsonl")}
        )
        dump(self.archive / name, {"schema": "m4-initial-load-reference-seal/1", "files": files})
        return name

    def check(self):
        before = inventory(self.archive)
        result = core.hash_checks(self.archive, before)
        self.assertEqual(inventory(self.archive), before)
        return result

    def test_reference_seal_matches_its_declared_child_without_rewriting(self):
        self.reference_seal()
        self.file("nested/trace.jsonl", b"wrong directory decoy")
        result = self.check()
        self.assertEqual(result["status"], "matched")
        self.assertEqual(result["checked_files"], 1)
        self.assertEqual(result["mismatches"], [])
        self.assertEqual(result["manifests"][0]["base"], "reference")

    def test_nested_reference_seal_remains_relative_to_its_own_declared_child(self):
        self.file("children/source/reference/nested/trace.jsonl")
        self.reference_seal("children/source/")
        result = self.check()
        self.assertEqual(result["status"], "matched")
        self.assertEqual(result["manifests"][0]["base"], "children/source/reference")

    def test_tampered_reference_is_changed_even_when_manifest_parent_decoy_matches(self):
        self.reference_seal()
        self.file("reference/nested/trace.jsonl", b"tampered")
        self.file("nested/trace.jsonl")
        result = self.check()
        self.assertEqual(result["status"], "mismatch")
        self.assertEqual(result["mismatches"], ["reference/nested/trace.jsonl"])
        self.assertEqual(result["manifests"][0]["changed_files"], result["mismatches"])
        self.assertEqual(result["manifests"][0]["missing_files"], [])

    def test_missing_reference_is_missing_even_when_manifest_parent_decoy_matches(self):
        self.reference_seal()
        (self.archive / "reference/nested/trace.jsonl").unlink()
        self.file("nested/trace.jsonl")
        result = self.check()
        self.assertEqual(result["status"], "mismatch")
        self.assertEqual(result["manifests"][0]["missing_files"], ["reference/nested/trace.jsonl"])
        self.assertEqual(result["manifests"][0]["changed_files"], [])

    def test_regular_child_manifest_retains_parent_base(self):
        sha = self.file("children/predictor/trace.jsonl")
        dump(
            self.archive / "children/predictor/manifest.json",
            {"schema": "opent1d.m3.researcher/1", "files": {"trace.jsonl": sha}},
        )
        self.file("reference/trace.jsonl", b"wrong base")
        result = self.check()
        self.assertEqual(result["status"], "matched")
        self.assertEqual(result["manifests"][0]["base"], "children/predictor")

    def test_m1_digest_field_is_selected_without_files_fallback(self):
        sha = self.file("trace.jsonl")
        dump(
            self.archive / "manifest.json",
            {"schema": "opent1d.simglucose/1", "files_sha256": {"trace.jsonl": sha}},
        )
        self.assertEqual(self.check()["status"], "matched")
        dump(
            self.archive / "manifest.json",
            {"schema": "opent1d.simglucose/1", "files": {"trace.jsonl": sha}},
        )
        self.assertEqual(self.check()["status"], "malformed")

    def test_local_tool_claim_checks_digest_and_size(self):
        self.file("evidence.json")
        seal(self.archive)
        self.assertEqual(self.check()["status"], "matched")
        manifest = json.loads((self.archive / "manifest.json").read_bytes())
        manifest["files"]["evidence.json"]["size"] += 1
        dump(self.archive / "manifest.json", manifest)
        result = self.check()
        self.assertEqual(result["status"], "mismatch")
        self.assertEqual(result["mismatches"], ["evidence.json"])

    def test_local_tool_malformed_record_does_not_become_digest_mismatch(self):
        sha = self.file("evidence.json")
        for claim in (
            sha,
            {"sha256": sha},
            {"sha256": sha, "size": True},
            {"sha256": sha, "size": -1},
            {"sha256": sha, "size": 1, "extra": 1},
        ):
            with self.subTest(claim=claim):
                dump(
                    self.archive / "manifest.json",
                    {"schema": "opent1d.local-tool-archive/1", "files": {"evidence.json": claim}},
                )
                result = self.check()
                self.assertEqual(result["status"], "malformed")
                self.assertEqual(result["checked_files"], 0)
                self.assertEqual(result["mismatches"], [])
                self.assertTrue(result["manifests"][0]["errors"])

    def test_unknown_matching_inventory_never_becomes_a_match(self):
        sha = self.file("trace.jsonl")
        dump(
            self.archive / "manifest.json",
            {"schema": "unknown-future-seal/42", "files": {"trace.jsonl": sha}},
        )
        result = self.check()
        self.assertEqual(result["status"], "unsupported")
        self.assertEqual(result["checked_files"], 0)
        self.assertIsNone(result["manifests"][0]["base"])
        self.assertIsNone(result["manifests"][0]["claim_shape"])

    def test_mixed_known_matches_and_unknown_schema_cannot_claim_aggregate_match(self):
        self.reference_seal()
        sha = self.file("trace.jsonl")
        dump(
            self.archive / "manifest.json",
            {"schema": "unknown-future-seal/42", "files": {"trace.jsonl": sha}},
        )
        result = self.check()
        self.assertEqual(result["status"], "unsupported")
        self.assertEqual(result["checked_files"], 1)
        self.assertEqual(
            {item["status"] for item in result["manifests"]}, {"matched", "unsupported"}
        )

    def test_unknown_schema_cannot_hide_known_missing_claims(self):
        self.reference_seal()
        (self.archive / "reference/nested/trace.jsonl").unlink()
        dump(self.archive / "manifest.json", {"schema": "future-seal/1", "files": {}})
        result = self.check()
        self.assertEqual(result["status"], "mismatch")
        self.assertEqual(result["mismatches"], ["reference/nested/trace.jsonl"])
        self.assertEqual(
            {item["status"] for item in result["manifests"]}, {"mismatch", "unsupported"}
        )

    def test_malformed_claim_keeps_other_missing_claims_visible(self):
        self.reference_seal(files={"missing.json": "0" * 64, "invalid.json": "bad"})
        result = self.check()
        self.assertEqual(result["status"], "malformed")
        self.assertEqual(result["checked_files"], 1)
        self.assertEqual(result["mismatches"], ["reference/missing.json"])
        self.assertTrue(result["manifests"][0]["errors"])

    def test_unsafe_or_noncanonical_claim_paths_never_select_or_normalize_bytes(self):
        sha = self.file("reference/evidence.json")
        for relative in (
            "../evidence.json",
            "/evidence.json",
            "a/../../evidence.json",
            "./evidence.json",
            "a//evidence.json",
            "a/./evidence.json",
            "evidence.json/",
            ".",
            "",
            "a\\evidence.json",
            "C:/evidence.json",
            "a\0b",
        ):
            with self.subTest(relative=relative):
                self.reference_seal(files={relative: sha})
                result = self.check()
                self.assertEqual(result["status"], "malformed")
                self.assertEqual(result["checked_files"], 0)
                self.assertEqual(result["mismatches"], [])

    def test_malformed_digests_and_mappings_are_distinct_from_changed_bytes(self):
        for claims in (
            {"evidence.json": "not-a-sha"},
            {"evidence.json": {"sha256": "0" * 64, "size": 1}},
            [],
            None,
        ):
            with self.subTest(claims=claims):
                dump(
                    self.archive / "reference-manifest.json",
                    {"schema": "m4-initial-load-reference-seal/1", "files": claims},
                )
                result = self.check()
                self.assertEqual(result["status"], "malformed")
                self.assertEqual(result["mismatches"], [])

    def test_malformed_manifest_json_and_schema_are_explicit(self):
        for raw in (
            b"{",
            b"[]",
            b'{"files":{}}',
            b'{"schema":[],"files":{}}',
            b'{"schema":"x","schema":"y"}',
        ):
            with self.subTest(raw=raw):
                self.file("manifest.json", raw)
                result = self.check()
                self.assertEqual(result["status"], "malformed")
                self.assertTrue(result["manifests"][0]["errors"])

    def test_empty_supported_claims_and_no_manifest_are_unavailable(self):
        self.file("trace.jsonl")
        self.assertEqual(self.check()["status"], "unavailable")
        dump(self.archive / "manifest.json", {"schema": "opent1d.m3.researcher/1", "files": {}})
        self.assertEqual(self.check()["status"], "unavailable")

    def test_reference_schema_in_wrong_named_manifest_is_malformed(self):
        sha = self.file("reference/trace.jsonl")
        dump(
            self.archive / "manifest.json",
            {"schema": "m4-initial-load-reference-seal/1", "files": {"trace.jsonl": sha}},
        )
        self.assertEqual(self.check()["status"], "malformed")

    def test_additive_contract_layouts_and_helper_identity_are_bound(self):
        contract = json.loads((ROOT / "experiments/catalogue/contract.json").read_bytes())
        self.assertEqual(
            contract["recorded_digest_schemas"],
            {
                schema: {"field": field, "base_relative_to_manifest": base, "claim_shape": shape}
                for schema, (field, base, shape) in LAYOUTS.items()
            },
        )
        self.assertIn("experiments/catalogue/claims.py", core.SOURCES)


if __name__ == "__main__":
    unittest.main()
