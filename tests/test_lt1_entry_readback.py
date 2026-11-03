"""Invented cross-language frames, no native runtime, observer or private payload."""

import base64
import copy
import json
import shutil
import subprocess
import unittest
from unittest.mock import patch

from test_lt1_host_context import invented_context

from experiments.lt1_diagnostic import entry_readback as entry
from experiments.lt1_diagnostic import native_launcher as launch
from experiments.lt1_diagnostic import reader
from experiments.lt1_diagnostic.recovery_readback import encoded as wire


@unittest.skipUnless(shutil.which("node"), "Node required for invented frames")
class EntryReadbackTests(unittest.TestCase):
    def setUp(self):
        self.as_of = "2026-11-03T12:00:01Z"
        self.at = "2026-11-03T12:00:00.000Z"
        self.context = invented_context()
        self.context["observer"]["pid"] = 12345
        self.profile = "invented profile, never executed"
        self.packet = {n + ".json": wire({"kind": "invented", "name": n}) for n in launch.RECEIPTS}
        self.packet["plan.json"] = (reader.HERE / "plan.json").read_bytes()
        runtime = {
            k: launch.native_preflight.RUNTIME[k]
            for k in ("node", "platform", "arch", "executable_sha256")
        }
        self.engine = {
            "schema": "opent1d.lt1-native-grant/1",
            **{k: runtime[k] for k in ("node", "platform", "arch")},
            "staging_root": "/invented/stage",
            "files": {"runtime/bin/node": runtime["executable_sha256"]},
        }
        self.host = {
            "owner_context": self.context,
            "profile_sha256": reader.digest(self.profile.encode()),
        }
        self.integration = {
            "schema": "opent1d.lt1-integration-grant/1",
            "owner_pid": 12345,
            "attempt": "invented-attempt",
        }
        self.grant = {
            "schema": "opent1d.lt1-entry-observation-grant/1",
            "packet_sha256": {},
            "runtime": runtime,
            "entry_executable": "/invented/stage/runtime/bin/node",
            "owner_pid": 12345,
            "owner_start": self.context["observer"]["start"],
            "attempt": "invented-attempt",
            "nonce_sha256": "c" * 64,
            "profile_sha256": self.host["profile_sha256"],
            "producer_sha256": reader.digest(entry.PRODUCER.read_bytes()),
            "reader_identity": entry.identity(entry.__file__),
            "process_argv": ["/invented/stage/runtime/bin/node", "/invented/entry.mjs"],
        }
        self.facts = {
            "pid": 54321,
            "ppid": 12345,
            "exec_path": self.grant["entry_executable"],
            **runtime,
            "exec_argv": [],
            "environment_keys": sorted(launch.host_context.ENVIRONMENT),
            "environment": dict(launch.host_context.ENVIRONMENT),
            "producer_sha256": self.grant["producer_sha256"],
            "stdio": "unobserved",
            "process_argv": self.grant["process_argv"],
        }
        self.receipt = {
            "kind": "qualification-only",
            **launch.AUTHORITY,
            "argv": [str(launch.SANDBOX), "-p", self.profile, *self.grant["process_argv"]],
            "owned_processes": [{"pid": 54321, "ppid": 12345, "start": "darwin:3:4"}],
        }
        self.parent_changes = {}
        self.frame_changes = {}
        self.raw_change = lambda raw: raw

    def args(self):
        packet = dict(self.packet)
        engine = {
            **self.engine,
            "setup_receipt_sha256": reader.digest(packet["setup_receipt.json"]),
        }
        packet["grant.json"] = wire(engine)
        packet["integration_host_receipt.json"] = wire(self.host)
        integration = {
            **self.integration,
            "engine_grant_sha256": reader.digest(packet["grant.json"]),
            "host_receipt_sha256": reader.digest(packet["integration_host_receipt.json"]),
        }
        packet["integration-grant.json"] = wire(integration)
        grant = {**self.grant, "packet_sha256": {n: reader.digest(v) for n, v in packet.items()}}
        grant_raw = entry.encode_grant(grant)
        emitted = subprocess.run(
            [shutil.which("node"), "tests/lt1_entry_observation.test.mjs", "--emit"],
            cwd=reader.ROOT,
            input=wire(
                {"grant": base64.b64encode(grant_raw).decode(), "facts": self.facts, "at": self.at}
            ),
            capture_output=True,
            timeout=20,
            check=True,
        )
        frame = reader.decode(emitted.stdout.split(b"\n")[1])
        frame.update(self.frame_changes)
        raw = self.raw_change(entry.MAGIC + wire(frame) + b"\n")
        parent = {
            "schema": "opent1d.lt1-entry-parent-observation/1",
            "kind": "invented",
            "grant_sha256": reader.digest(grant_raw),
            "frame_sha256": reader.digest(raw),
            "attempt": grant["attempt"],
            "nonce_sha256": grant["nonce_sha256"],
            "profile_sha256": grant["profile_sha256"],
            "owner": {"pid": 12345, "start": grant["owner_start"]},
            "entry": {
                "pid": 54321,
                "ppid": 12345,
                "start": "darwin:3:4",
                "executable_path": grant["entry_executable"],
                "executable_sha256": grant["runtime"]["executable_sha256"],
            },
            "observed_from": self.at,
            "observed_to": self.at,
        }
        parent.update(self.parent_changes)
        parent_raw = wire(parent)
        receipt_raw = wire(self.receipt)
        return dict(
            raw=raw,
            expected_sha256=reader.digest(raw),
            grant_raw=grant_raw,
            expected_grant_sha256=reader.digest(grant_raw),
            packet_bytes=packet,
            parent_raw=parent_raw,
            expected_parent_sha256=reader.digest(parent_raw),
            receipt_raw=receipt_raw,
            expected_receipt_sha256=reader.digest(receipt_raw),
            as_of=self.as_of,
        )

    def inspect(self):
        return entry.inspect_frame(**self.args())

    def test_js_producer_controls_and_closed_observation_gate(self):
        result = subprocess.run(
            [shutil.which("node"), "--test", "tests/lt1_entry_observation.test.mjs"],
            cwd=reader.ROOT,
            capture_output=True,
            timeout=20,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_cross_language_frame_correlates_entry_and_parent_without_qualification(self):
        result = self.inspect()
        self.assertTrue(result["entry_binding_consistent"])
        self.assertEqual(result["kind"], "invented")
        for name in (
            *entry.AUTHORITY,
            "phase_verified",
            "stdio_verified",
            "live_owner_revalidated",
            "external_observations_independently_proved",
            "attempt_completion_checked",
        ):
            self.assertIs(result[name], False)
        self.assertTrue(all(v["state"] == "not_run" for v in result["native_cases"].values()))

    def test_torn_extra_duplicate_and_empty_frames_refuse(self):
        for change in (
            lambda b: b[:-1],
            lambda b: b + b,
            lambda b: b + b"tail",
            lambda b: b"",
            lambda b: b.replace(b'"kind":"invented"', b'"kind":"invented","kind":"invented"'),
        ):
            self.raw_change = change
            with self.assertRaises(ValueError):
                self.inspect()

    def test_replayed_nonce_attempt_grant_or_mixed_parent_kind_refuses(self):
        for change in (
            {"nonce_sha256": "e" * 64},
            {"attempt": "other"},
            {"grant_sha256": "a" * 64},
            {"kind": "observed"},
        ):
            self.parent_changes = change
            with self.assertRaises(ValueError):
                self.inspect()

    def test_foreign_entry_parent_or_start_cannot_match_owned_entry(self):
        original = {
            "pid": 54321,
            "ppid": 12345,
            "start": "darwin:3:4",
            "executable_path": self.grant["entry_executable"],
            "executable_sha256": self.grant["runtime"]["executable_sha256"],
        }
        for change in (
            {"pid": 54322},
            {"ppid": 99999},
            {"start": "darwin:other"},
            {"executable_path": "/invented/other"},
            {"executable_sha256": "e" * 64},
        ):
            self.parent_changes = {"entry": {**original, **change}}
            with self.assertRaises(ValueError):
                self.inspect()

    def test_wrong_frame_origin_phase_or_authority_refuses(self):
        for change in (
            {"phase": "before-model-imports"},
            {"kind": "actual-native"},
            {"native_host_qualified": True},
            {"stdio": "verified"},
        ):
            self.frame_changes = change
            with self.assertRaises(ValueError):
                self.inspect()

    def test_entry_cannot_be_parent_or_an_unrelated_descendant(self):
        self.receipt["owned_processes"] = [{"pid": 12345, "ppid": 12345, "start": "darwin:3:4"}]
        with self.assertRaises(ValueError):
            self.inspect()
        self.receipt["owned_processes"] = [
            {"pid": 54320, "ppid": 12345, "start": "darwin:1:1"},
            {"pid": 54321, "ppid": 54320, "start": "darwin:3:4"},
        ]
        with self.assertRaises(ValueError):
            self.inspect()

    def test_receipt_argv_or_profile_cannot_name_a_different_attempt(self):
        self.receipt["argv"][-1] = "/invented/other-entry.mjs"
        with self.assertRaises(ValueError):
            self.inspect()
        self.receipt["argv"] = [
            str(launch.SANDBOX),
            "-p",
            "other-profile",
            *self.grant["process_argv"],
        ]
        with self.assertRaises(ValueError):
            self.inspect()

    def test_input_hash_packet_and_current_source_binding_refuse(self):
        args = self.args()
        args["packet_bytes"] = dict(args["packet_bytes"])
        args["packet_bytes"]["security_receipt.json"] = b"changed"
        with self.assertRaises(ValueError):
            entry.inspect_frame(**args)
        args = self.args()
        args["expected_parent_sha256"] = "f" * 64
        with self.assertRaises(ValueError):
            entry.inspect_frame(**args)
        self.grant["reader_identity"] = {}
        with self.assertRaises(ValueError):
            self.inspect()

    def test_future_or_reversed_observation_time_refuses(self):
        self.parent_changes = {"observed_to": "2026-11-03T13:00:00Z"}
        with self.assertRaises(ValueError):
            self.inspect()
        self.parent_changes = {"observed_from": "2026-11-03T12:00:01Z", "observed_to": self.at}
        with self.assertRaises(ValueError):
            self.inspect()

    def test_reader_does_not_query_os_or_start_a_process(self):
        args = self.args()
        with (
            patch("subprocess.run", side_effect=AssertionError("spawn")),
            patch.object(launch.host_context, "capture", side_effect=AssertionError("capture")),
        ):
            self.assertTrue(entry.inspect_frame(**args)["entry_binding_consistent"])

    def test_parent_pid_fields_require_exact_integer_types(self):
        args = self.args()
        parent = json.loads(args["parent_raw"])
        for role, key in (("owner", "pid"), ("entry", "pid"), ("entry", "ppid")):
            changed = copy.deepcopy(parent)
            changed[role][key] = float(changed[role][key])
            raw = wire(changed)
            with self.subTest(role=role, key=key), self.assertRaises(ValueError):
                entry.inspect_frame(
                    **{**args, "parent_raw": raw, "expected_parent_sha256": reader.digest(raw)}
                )

    def test_noncanonical_frame_time_and_observation_grant_refuse(self):
        args = self.args()
        grant = json.loads(args["grant_raw"])
        grant["owner_pid"] = float(grant["owner_pid"])
        raw = wire(grant)
        with self.assertRaises(ValueError):
            entry.inspect_frame(
                **{**args, "grant_raw": raw, "expected_grant_sha256": reader.digest(raw)}
            )
        for at in (
            "2026-11-03T12:00:00Z",
            "2026-11-03T14:00:00.000+02:00",
            "2026-02-31T12:00:00.000Z",
        ):
            self.frame_changes = {"observed_at": at}
            with self.assertRaises(ValueError):
                self.inspect()

    def test_canonical_utf8_grant_preserves_unicode_entry_argv(self):
        root = "/invented/étude-😀"
        path = root + "/runtime/bin/node"
        self.engine["staging_root"] = root
        self.grant["entry_executable"] = path
        self.grant["process_argv"] = [path, "/invented/entrée-😀.mjs"]
        self.facts["exec_path"] = path
        self.facts["process_argv"] = self.grant["process_argv"]
        self.receipt["argv"] = [
            str(launch.SANDBOX),
            "-p",
            self.profile,
            *self.grant["process_argv"],
        ]
        self.assertTrue(self.inspect()["entry_binding_consistent"])
