"""Invented-only authentication semantics and closed real trust boundary."""

import copy
import unittest
from unittest.mock import patch

from experiments.simglucose_audit import pbs_auth as a


class AuthTests(unittest.TestCase):
    def inputs(self):
        return a.invented_auth_inputs(
            a.digest(b"INVENTED compressed bytes"),
            25,
            a.digest(b"INVENTED request"),
            a.digest(b"INVENTED reader"),
        )

    def run_inputs(self, inputs):
        return a.qualify_invented_auth(*inputs[:3], **inputs[3])

    def modified(self, index, change):
        inputs = self.inputs()
        documents = [a.decode(raw) for raw in inputs[:3]]
        change(documents[index])
        raw = tuple(a.encode(v) for v in documents)
        held = {
            "held_" + name + "_sha256": a.digest(value)
            for name, value in zip(("bundle", "policy", "context"), raw, strict=True)
        }
        return *raw, held

    def test_actual_refuses_before_input_or_source(self):
        class Trap:
            def __bytes__(self):
                raise AssertionError("bytes touched")

            def __fspath__(self):
                raise AssertionError("path touched")

        with patch.object(a, "_identity", side_effect=AssertionError("source touched")):
            with self.assertRaises(PermissionError):
                a.verify_archive(Trap(), authenticated=True, verifier=Trap())

    def test_positive_semantics_remain_invented(self):
        report = self.run_inputs(self.inputs())
        self.assertTrue(report["semantic_correspondence"])
        self.assertTrue(report["fixture_controls_passed"])
        self.assertEqual(report["kind"], "invented")
        for key in (
            "actual_crypto_verified",
            "actual_authentication_admitted",
            "actual_archive_inspection_authorized",
            "runtime_use_authorized",
            "execution_ready",
        ):
            self.assertIs(report[key], False)
        self.assertTrue(all(v is None for v in report["missing_actual_bindings"].values()))

    def test_each_invented_control_can_refuse_without_authenticating(self):
        for control in a.CONTROLS:
            with self.subTest(control=control):
                inputs = self.modified(0, lambda d: d["controls"].update({control: False}))
                result = self.run_inputs(inputs)
                self.assertEqual(result["status"], "fixture-controls-refused")
                self.assertEqual(result["failed_invented_controls"], [control])
                self.assertFalse(result["actual_crypto_verified"])

    def test_controls_not_truthy_or_extra(self):
        for value in (1, "valid", None, []):
            inputs = self.modified(0, lambda d: d["controls"].update(signature=value))
            with self.subTest(value=value), self.assertRaises(ValueError):
                self.run_inputs(inputs)
        with self.assertRaises(ValueError):
            self.run_inputs(self.modified(0, lambda d: d["controls"].update(verify_command=True)))

    def test_wrong_identity_and_source_rehashed(self):
        for key, value in (
            ("repository", "invented/attacker"),
            ("repository_id", 1),
            ("release_id", True),
            ("source_commit", "0" * 40),
            ("tag", "latest"),
            ("builder", "https://example.invalid/workflow"),
        ):
            inputs = self.modified(0, lambda d: d["target"].update({key: value}))
            with self.subTest(key=key), self.assertRaises(ValueError):
                self.run_inputs(inputs)
        for key in ("issuer", "certificate_identity"):
            with self.subTest(key=key), self.assertRaises(ValueError):
                self.run_inputs(self.modified(0, lambda d: d.update({key: "untrusted"})))

    def test_subjects_predicates_and_build_name_not_silently_rewritten(self):
        changes = [
            lambda d: d["statements"].pop(),
            lambda d: d["statements"].append(copy.deepcopy(d["statements"][0])),
            lambda d: d["statements"][1].update(predicate=a.PREDICATES[0]),
            lambda d: d["statements"][0].update(subject_name=a.RELEASE_NAME),
            lambda d: d["statements"][1].update(subject_sha256="0" * 64),
        ]
        for index, change in enumerate(changes):
            with self.subTest(index=index), self.assertRaises(ValueError):
                self.run_inputs(self.modified(0, change))

    def test_actual_bundle_and_json_verification_claim_refused(self):
        for key, value in (
            ("kind", "actual"),
            ("actual_crypto_verified", True),
            ("verifier_command", "invented executable"),
        ):
            with self.subTest(key=key), self.assertRaises(ValueError):
                self.run_inputs(self.modified(0, lambda d: d.update({key: value})))

    def test_policy_cannot_select_real_verifier_or_bundle_trust(self):
        for key in a.MISSING_ACTUAL:
            inputs = self.modified(
                1, lambda d: d["missing_actual_bindings"].update({key: "0" * 64})
            )
            with self.subTest(key=key), self.assertRaises(ValueError):
                self.run_inputs(inputs)
        with self.assertRaises(ValueError):
            self.run_inputs(self.modified(1, lambda d: d.update(trust_bundle_certificate=True)))

    def test_policy_scope_and_retention_drift(self):
        changes = [
            lambda d: d.update(kind="actual"),
            lambda d: d.update(expected_issuer="invented-other"),
            lambda d: d["controls"].pop(),
            lambda d: d["retention"].update(not_after_utc="2026-12-06T00:00:00Z"),
            lambda d: d["retention"].update(old_origins_reset=True),
        ]
        for index, change in enumerate(changes):
            with self.subTest(index=index), self.assertRaises(ValueError):
                self.run_inputs(self.modified(1, change))

    def test_context_is_fixed_tiny_invented_metadata(self):
        for key, value in (
            ("kind", "actual"),
            ("artifact_bytes", 25172086),
            ("artifact_bytes", True),
            ("artifact_bytes", 0),
            ("artifact_sha256", "invalid"),
            ("request_sha256", None),
            ("reader_source_sha256", "not a pin"),
            ("path", "/invented"),
        ):
            with self.subTest(key=key, value=value), self.assertRaises(ValueError):
                self.run_inputs(self.modified(2, lambda d: d.update({key: value})))

    def test_source_and_request_context_changes_bind_report(self):
        inputs = self.inputs()
        report = self.run_inputs(inputs)
        raw = a.encode(report)
        changed = self.modified(2, lambda d: d.update(reader_source_sha256="0" * 64))
        with self.assertRaises(ValueError):
            a.inspect_auth_fixture_report(raw, a.digest(raw), *changed[:3], **changed[3])

    def test_held_hash_mismatch_and_byte_caps(self):
        inputs = self.inputs()
        for key in inputs[3]:
            held = dict(inputs[3], **{key: "0" * 64})
            with self.subTest(key=key), self.assertRaises(ValueError):
                a.qualify_invented_auth(*inputs[:3], **held)
        for index, size in enumerate((65537, 32769, 32769)):
            raw = list(inputs[:3])
            raw[index] = b" " * size
            held = dict(inputs[3])
            held["held_" + ("bundle", "policy", "context")[index] + "_sha256"] = a.digest(
                raw[index]
            )
            with self.subTest(index=index), self.assertRaises(ValueError):
                a.qualify_invented_auth(*raw, **held)

    def test_duplicate_JSON_fields_refused(self):
        inputs = self.inputs()
        raw = b'{"kind":"invented","kind":"invented"}'
        held = dict(inputs[3], held_bundle_sha256=a.digest(raw))
        with self.assertRaises(ValueError):
            a.qualify_invented_auth(raw, *inputs[1:3], **held)

    def test_source_drift_at_producer_and_cold_boundaries(self):
        inputs = self.inputs()
        report = self.run_inputs(inputs)
        raw = a.encode(report)
        identity = report["source_identity"]
        with patch.object(a, "_identity", side_effect=[identity, {"changed": "0" * 64}]):
            with self.assertRaises(ValueError):
                self.run_inputs(inputs)
        with patch.object(a, "_identity", side_effect=[identity, {"changed": "0" * 64}]):
            with self.assertRaises(ValueError):
                a.inspect_auth_fixture_report(raw, a.digest(raw), *inputs[:3], **inputs[3])

    def test_cold_reconstructs_without_public_producer(self):
        inputs = self.inputs()
        report = self.run_inputs(inputs)
        raw = a.encode(report)
        with patch.object(
            a, "qualify_invented_auth", side_effect=AssertionError("producer called")
        ):
            result = a.inspect_auth_fixture_report(raw, a.digest(raw), *inputs[:3], **inputs[3])
        self.assertTrue(result["fixture_controls_passed"])
        self.assertFalse(result["actual_authentication_admitted"])

    def test_rehashed_receipt_cannot_promote_trust_or_source(self):
        inputs = self.inputs()
        original = self.run_inputs(inputs)
        for key, value in (
            ("actual_crypto_verified", True),
            ("actual_authentication_admitted", True),
            ("actual_archive_inspection_authorized", True),
            ("execution_ready", True),
            ("artifact_sha256", "0" * 64),
            ("source_identity", {}),
            ("authority", {}),
            ("kind", "actual"),
        ):
            report = dict(original, **{key: value})
            raw = a.encode(report)
            with self.subTest(key=key), self.assertRaises(ValueError):
                a.inspect_auth_fixture_report(raw, a.digest(raw), *inputs[:3], **inputs[3])

    def test_refused_controls_cold_reconstruct_as_refused(self):
        inputs = self.modified(0, lambda d: d["controls"].update(transparency_log=False))
        report = self.run_inputs(inputs)
        raw = a.encode(report)
        cold = a.inspect_auth_fixture_report(raw, a.digest(raw), *inputs[:3], **inputs[3])
        self.assertFalse(cold["fixture_controls_passed"])
        self.assertFalse(cold["actual_crypto_verified"])


if __name__ == "__main__":
    unittest.main()
