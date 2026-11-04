"""Invented transport bytes and tooling Node; no native setup or selected runtime."""

import copy
import json
import shutil
import subprocess
import unittest
from unittest.mock import patch

import test_lt1_entry_readback as fixtures

from experiments.lt1_diagnostic import handoff_readback as handoff
from experiments.lt1_diagnostic import reader


@unittest.skipUnless(shutil.which("node"), "Node required for invented handoff frames")
class HandoffReadbackTests(unittest.TestCase):
    def setUp(self):
        self.fixture = fixtures.EntryReadbackTests()
        self.fixture.setUp()

    def args(self):
        frame_inputs = self.fixture.args()
        encoded = subprocess.run(
            [shutil.which("node"), "tests/lt1_entry_handoff.test.mjs", "--ack"],
            cwd=reader.ROOT,
            input=frame_inputs["raw"],
            capture_output=True,
            timeout=20,
            check=True,
        ).stdout
        return {
            "ack_raw": encoded,
            "expected_ack_sha256": reader.digest(encoded),
            "expected_reader_identity": handoff.source_identity(),
            **frame_inputs,
        }

    def assert_unqualified(self, result):
        self.assertTrue(result["entry_binding_consistent"])
        self.assertTrue(result["ack_binding_consistent"])
        for key in (
            *handoff.entry.AUTHORITY,
            "transport_execution_independently_proved",
            "endpoint_identity_verified",
            "endpoint_close_verified",
            "handoff_timing_verified",
            "phase_verified",
            "stdio_verified",
            "attempt_completion_checked",
            "live_owner_revalidated",
            "new_authority_granted",
            "effective_erasure_verified",
        ):
            self.assertIs(result[key], False, key)
        self.assertTrue(all(v["state"] == "not_run" for v in result["native_cases"].values()))

    def test_node_exchange_controls_and_closed_production_gate(self):
        result = subprocess.run(
            [shutil.which("node"), "--test", "tests/lt1_entry_handoff.test.mjs"],
            cwd=reader.ROOT,
            capture_output=True,
            timeout=20,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_exact_cross_language_ack_is_repeatable_without_execution_or_qualification(self):
        inputs = self.args()
        result = handoff.inspect_exchange(**inputs)
        self.assertEqual(result, handoff.inspect_exchange(**inputs))
        self.assertEqual(result["kind"], "invented")
        self.assert_unqualified(result)
        self.assertTrue(
            all(
                "experiments/lt1_diagnostic/" + name in result["reader_identity"]["implementation"]
                for name in handoff.JS_SOURCES
            )
        )

    def test_expected_ack_hash_bound_before_structural_readback(self):
        inputs = self.args()
        inputs["expected_ack_sha256"] = "a" * 64
        with self.assertRaisesRegex(ValueError, "expected acknowledgment"):
            handoff.inspect_exchange(**inputs)

    def test_torn_extra_duplicate_bad_utf8_and_promoted_ack_refuse_even_rehashed(self):
        inputs = self.args()
        raw = inputs["ack_raw"]
        variants = [
            b"",
            raw[:-1],
            raw + raw,
            b"\xff",
            raw.replace(b'"kind":"invented"', b'"kind":"observed","kind":"invented"'),
            raw.replace(b"{", b"{ ", 1),
            raw[:-2] + b',"native_host_qualified":true}\n',
            b"x" * (handoff.ACK_LIMIT + 1),
        ]
        for changed in variants:
            with self.subTest(changed=changed[:50]), self.assertRaises(ValueError):
                handoff.inspect_exchange(
                    **{**inputs, "ack_raw": changed, "expected_ack_sha256": reader.digest(changed)}
                )

    def test_rehashed_ack_identity_fields_cannot_cross_attempt_or_origin(self):
        inputs = self.args()
        value = reader.decode(inputs["ack_raw"].split(b"\n")[1])
        for key in ("kind", "frame_sha256", "grant_sha256", "attempt", "nonce_sha256"):
            changed = (
                handoff.ACK_MAGIC
                + json.dumps({**value, key: "wrong"}, separators=(",", ":")).encode()
                + b"\n"
            )
            with (
                self.subTest(key=key),
                self.assertRaisesRegex(ValueError, "canonical acknowledgment"),
            ):
                handoff.inspect_exchange(
                    **{**inputs, "ack_raw": changed, "expected_ack_sha256": reader.digest(changed)}
                )

    def test_expected_source_and_late_source_change_refuse(self):
        inputs = self.args()
        wrong = copy.deepcopy(inputs["expected_reader_identity"])
        name = "experiments/lt1_diagnostic/entry_handoff.mjs"
        wrong["implementation"][name] = "f" * 64
        with self.assertRaisesRegex(ValueError, "current handoff reader"):
            handoff.inspect_exchange(**{**inputs, "expected_reader_identity": wrong})
        with (
            patch.object(
                handoff, "source_identity", side_effect=[inputs["expected_reader_identity"], wrong]
            ),
            self.assertRaisesRegex(ValueError, "source changed"),
        ):
            handoff.inspect_exchange(**inputs)

    def test_consistent_observed_labels_still_supply_no_host_or_endpoint_proof(self):
        self.fixture.frame_changes = {"kind": "observed"}
        self.fixture.parent_changes = {"kind": "observed"}
        result = handoff.inspect_exchange(**self.args())
        self.assertEqual(result["kind"], "observed")
        self.assert_unqualified(result)

    def test_byte_valid_entry_frame_with_noncanonical_transport_form_refuses(self):
        self.fixture.raw_change = lambda raw: raw.replace(b"{", b"{ ", 1)
        inputs = self.fixture.args()
        # The old reader supports these bytes. New handoff requires its canonical form.
        self.assertTrue(handoff.entry.inspect_frame(**inputs)["entry_binding_consistent"])
        value = reader.decode(inputs["raw"].split(b"\n")[1])
        ack_value = {
            "schema": "opent1d.lt1-entry-ack/1",
            "kind": value["kind"],
            "frame_sha256": reader.digest(inputs["raw"]),
            "grant_sha256": value["grant_sha256"],
            "attempt": value["attempt"],
            "nonce_sha256": value["nonce_sha256"],
        }
        raw = handoff.ACK_MAGIC + json.dumps(ack_value, separators=(",", ":")).encode() + b"\n"
        with self.assertRaisesRegex(ValueError, "canonical transport frame"):
            handoff.inspect_exchange(
                raw,
                reader.digest(raw),
                expected_reader_identity=handoff.source_identity(),
                **inputs,
            )

    def test_canonical_utf8_frame_and_ack_roundtrip(self):
        f = self.fixture
        root = "/invented/étude-😀"
        path = root + "/runtime/bin/node"
        f.engine["staging_root"] = root
        f.grant["entry_executable"] = path
        f.grant["process_argv"] = [path, "/invented/entrée-😀.mjs"]
        f.facts["exec_path"] = path
        f.facts["process_argv"] = f.grant["process_argv"]
        f.receipt["argv"] = [
            str(handoff.entry.launch.SANDBOX),
            "-p",
            f.profile,
            *f.grant["process_argv"],
        ]
        f.raw_change = lambda raw: (
            handoff.entry.MAGIC
            + json.dumps(
                reader.decode(raw.split(b"\n")[1]), ensure_ascii=False, separators=(",", ":")
            ).encode()
            + b"\n"
        )
        self.assert_unqualified(handoff.inspect_exchange(**self.args()))
