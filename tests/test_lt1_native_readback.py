"""Fresh invented evidence files, existing scripted rows; no LT1 runtime/collector."""

import copy
import json
import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from test_lt1_host_context import invented_context

from experiments.lt1_diagnostic import journal_reader, reader
from experiments.lt1_diagnostic import native_launcher as launch
from experiments.lt1_diagnostic import native_readback as readback
from experiments.lt1_diagnostic.recovery_readback import encoded as wire


@unittest.skipUnless(
    os.name == "posix" and shutil.which("node"), "POSIX scripted Node rows required"
)
class NativeReadbackTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        result = subprocess.run(
            [shutil.which("node"), "tests/lt1_diagnostic.test.mjs", "--emit"],
            cwd=reader.ROOT,
            capture_output=True,
            timeout=30,
            check=True,
        )
        cls.sessions = json.loads(result.stdout)

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.folder = Path(self.temp.name).resolve()
        self.folder.chmod(0o700)
        self.plan = self.folder / "plan.json"
        self.receipt_path = self.folder / "receipt.json"
        self.journal_path = self.folder / "events.jsonl"
        self.packet = {
            name + ".json": wire({"kind": "invented", "name": name}) for name in launch.RECEIPTS
        }
        self.packet["plan.json"] = (launch.HERE / "plan.json").read_bytes()
        self.context = invented_context()
        self.context["host"]["uid"] = os.getuid()
        self.context["observer"]["pid"] = 12345
        self.stage, self.packet_root, self.output, self.evidence = [
            Path("/invented/lt1") / role for role in ("stage", "packet", "output", "evidence")
        ]
        self.profile = launch.profile(self.stage, self.packet_root, self.output)
        self.host = {
            "schema": "opent1d.lt1-prestart-host/1",
            "purpose": "qualification-only",
            "owner_context": self.context,
            "launcher_identity": launch.identity(launch.__file__),
            "roots": {
                role: {
                    "path": str(path),
                    "identity": [
                        1,
                        i,
                        os.getuid(),
                        0o500 if role in ("stage", "packet") else 0o700,
                    ],
                }
                for i, (role, path) in enumerate(
                    zip(
                        ("stage", "packet", "output", "evidence"),
                        (self.stage, self.packet_root, self.output, self.evidence),
                    ),
                    1,
                )
            },
            "profile_sha256": reader.digest(self.profile.encode()),
            "sandbox_sha256": "a" * 64,
            "dyld_sha256": "b" * 64,
            "timeout_seconds": 10,
            "grace_seconds": 1,
            "max_context_age_seconds": 60,
            "materialization_request_sha256": "c" * 64,
            "materialization_manifest_sha256": "d" * 64,
        }
        files = dict.fromkeys(launch.ENTRIES, "e" * 64)
        files["runtime/bin/node"] = launch.native_preflight.RUNTIME["executable_sha256"]
        self.engine = {
            "schema": "opent1d.lt1-native-grant/1",
            "source_revision": launch.native_preflight.REVISION,
            **{k: launch.native_preflight.RUNTIME[k] for k in ("node", "platform", "arch")},
            "host": "invented-host",
            "staging_root": str(self.stage),
            "mode": "wrapped",
            **{
                name + "_sha256": reader.digest(self.packet[name + ".json"])
                for name in launch.RECEIPTS
            },
            "files": files,
            "worker_files": launch._worker(launch.WORKER),
        }
        self.integration = {
            "schema": "opent1d.lt1-integration-grant/1",
            "engine_grant_sha256": None,
            "host_receipt_sha256": None,
            "output_root": str(self.output),
            "attempt": "invented-attempt",
            "owner_pid": 12345,
            "reader_identity": journal_reader.identity(self.packet["plan.json"]),
            "implementation": launch._worker(launch.INTEGRATION),
        }
        self.receipt = {
            "argv": [
                str(launch.SANDBOX),
                "-p",
                self.profile,
                str(self.stage / "runtime/bin/node"),
                str(launch.HERE / "integration_worker.mjs"),
                str(self.stage),
                str(self.packet_root),
                str(self.output),
            ],
            "status": "completed",
            "exit_code": 0,
            "error": None,
            "cleanup_forced": False,
            "owned_processes": [{"pid": 54321, "ppid": 12345, "start": "darwin:54321:123"}],
            "remaining_owned_processes": [],
            "received_signals": [],
            "kind": "qualification-only",
            **launch.AUTHORITY,
        }
        self.session = copy.deepcopy(self.sessions["wrapped"])
        self.footer = True
        self.tail = b""
        self.header_changes = {}

    def args(self):
        self.packet["grant.json"] = wire(self.engine)
        self.integration["engine_grant_sha256"] = reader.digest(self.packet["grant.json"])
        self.packet["integration_host_receipt.json"] = wire(self.host)
        self.integration["host_receipt_sha256"] = reader.digest(
            self.packet["integration_host_receipt.json"]
        )
        self.packet["integration-grant.json"] = wire(self.integration)
        header = {
            "type": "start",
            "schema": journal_reader.SCHEMA,
            "kind": "invented",
            "mode": "wrapped",
            "identity": journal_reader.identity(self.packet["plan.json"]),
            "attempt": self.integration["attempt"],
            "output_root": str(self.output),
            "owner_pid": 12345,
            "engine_grant_sha256": self.integration["engine_grant_sha256"],
            "integration_sha256": reader.digest(self.packet["integration-grant.json"]),
        }
        header.update(self.header_changes)
        rows = [{"type": "row", "ordinal": i, "row": r} for i, r in enumerate(self.session["rows"])]
        records = [header, *rows]
        if self.footer:
            records.append(
                {
                    "type": "finish",
                    "rows_in_memory": len(rows),
                    **{
                        k: self.session[k]
                        for k in ("status", "primary_error", "diagnostic_error", "diagnostic_tail")
                    },
                }
            )
        journal_raw = b"".join(wire(row) + b"\n" for row in records) + self.tail
        for path, raw in (
            (self.plan, self.packet["plan.json"]),
            (self.receipt_path, wire(self.receipt)),
            (self.journal_path, journal_raw),
        ):
            path.write_bytes(raw)
            path.chmod(0o600)
        capsule = {
            "schema": "opent1d.lt1-native-attempt-readback/1",
            "kind": "invented",
            "reader_identity": readback.identity(readback.__file__),
            "packet_sha256": {name: reader.digest(raw) for name, raw in self.packet.items()},
            "packet_root": str(self.packet_root),
            "journal_sha256": reader.digest(journal_raw),
            "plan_sha256": reader.digest(self.packet["plan.json"]),
            "receipt_sha256": reader.digest(wire(self.receipt)),
        }
        raw = wire(capsule)
        return dict(
            journal_path=self.journal_path,
            plan_path=self.plan,
            receipt_path=self.receipt_path,
            expected_journal_sha256=capsule["journal_sha256"],
            expected_plan_sha256=capsule["plan_sha256"],
            expected_receipt_sha256=capsule["receipt_sha256"],
            capsule_raw=raw,
            expected_capsule_sha256=reader.digest(raw),
            packet_bytes=self.packet,
        )

    def inspect(self):
        return readback.inspect_attempt(**self.args())

    def test_complete_existing_reader_fractional_result_and_all_six_unrun(self):
        result = self.inspect()
        self.assertEqual(result["journal_result"]["status"], "completed")
        self.assertEqual(
            result["journal_result"]["modeled_delivered_u"], {"numerator": 25, "denominator": 48}
        )
        self.assertEqual(set(result["native_cases"]), set(launch.native_preflight.NATIVE_CASES))
        self.assertTrue(all(v["state"] == "not_run" for v in result["native_cases"].values()))
        self.assertTrue(all(result[k] is False for k in readback.AUTHORITY))
        self.assertFalse(result["external_observations_independently_proved"])

    def test_failure_keeps_primary_error_and_committed_prefix(self):
        self.session.update(
            rows=self.session["rows"][:3], status="failed", primary_error="invented primary"
        )
        self.receipt.update(status="failed", exit_code=23)
        result = self.inspect()["journal_result"]
        self.assertEqual(result["native_callbacks"], 3)
        self.assertEqual(result["primary_error"], "invented primary")
        self.assertEqual(result["status"], "failed")

    def test_deadline_cancel_and_signal_preserve_unfinished_tail(self):
        self.session["rows"] = self.session["rows"][:3]
        self.footer = False
        self.tail = b'{"torn":'
        for status, error, signals in (
            ("failed", "WorkerDeadline", []),
            ("interrupted", "Cancelled", []),
            ("interrupted", None, [15]),
        ):
            self.receipt.update(status=status, error=error, exit_code=-15, received_signals=signals)
            result = self.inspect()["journal_result"]
            self.assertEqual(result["status"], status)
            self.assertEqual(result["native_callbacks"], 3)
            self.assertEqual(result["uncommitted_tail_bytes"], len(self.tail))
            self.assertFalse(result["worker_finish_present"])

    def test_missing_finish_cannot_be_completed_by_outer_zero_exit(self):
        self.footer = False
        result = self.inspect()["journal_result"]
        self.assertEqual(result["status"], "failed")
        self.assertEqual(result["primary_error"], "Worker finish missing")

    def test_contradictory_completion_and_cleanup_flags_refuse(self):
        original = copy.deepcopy(self.receipt)
        for changes in (
            {"error": "WorkerDeadline"},
            {"received_signals": [15]},
            {"exit_code": 23},
            {"remaining_owned_processes": [{}]},
            {"cleanup_error": "unknown"},
            {"signal_error": "unknown"},
            {"native_host_qualified": True},
        ):
            self.receipt = {**copy.deepcopy(original), **changes}
            with self.assertRaises(ValueError):
                self.inspect()

    def test_changed_header_grants_owner_mode_output_and_attempt_refuse(self):
        for key, value in (
            ("engine_grant_sha256", "f" * 64),
            ("integration_sha256", "e" * 64),
            ("owner_pid", 99999),
            ("mode", "direct"),
            ("attempt", "other"),
            ("output_root", "/invented/other"),
            ("kind", "native-unadmitted"),
        ):
            self.header_changes = {key: value}
            with self.assertRaisesRegex(ValueError, "attempt binding"):
                self.inspect()

    def test_changed_packet_bytes_or_expected_identity_refuses(self):
        args = self.args()
        args["packet_bytes"] = dict(self.packet)
        args["packet_bytes"]["security_receipt.json"] = b"changed"
        with self.assertRaisesRegex(ValueError, "packet byte identity"):
            readback.inspect_attempt(**args)
        args = self.args()
        args["expected_plan_sha256"] = "f" * 64
        with self.assertRaisesRegex(ValueError, "capsule"):
            readback.inspect_attempt(**args)

    def test_rehashed_wrong_owner_root_profile_source_and_executable_refuse(self):
        tests = [
            (self.integration, "owner_pid", 99999),
            (self.host, "profile_sha256", "f" * 64),
            (self.host, "launcher_identity", {}),
            (self.engine["files"], "runtime/bin/node", "f" * 64),
            (self.host["roots"]["stage"], "path", "/invented/other"),
        ]
        for value, key, replacement in tests:
            old = value[key]
            value[key] = replacement
            with self.assertRaises(ValueError):
                self.inspect()
            value[key] = old

    def test_owner_start_and_owned_identity_cannot_be_omitted(self):
        for key, value in (("start", None), ("pid", True), ("ppid", None)):
            old = self.receipt["owned_processes"][0][key]
            self.receipt["owned_processes"][0][key] = value
            with self.assertRaises(ValueError):
                self.inspect()
            self.receipt["owned_processes"][0][key] = old
        self.receipt["owned_processes"] *= 2
        with self.assertRaisesRegex(ValueError, "duplicate"):
            self.inspect()

    def test_changed_files_are_detected_after_existing_reader(self):
        args = self.args()
        original = journal_reader.inspect

        def alter(*a, **k):
            result = original(*a, **k)
            self.plan.write_bytes(b"changed")
            return result

        with patch.object(journal_reader, "inspect", side_effect=alter):
            with self.assertRaisesRegex(ValueError, "byte identity"):
                readback.inspect_attempt(**args)

    def test_unsafe_permissions_alias_missing_journal_and_wrong_source_refuse(self):
        args = self.args()
        self.receipt_path.chmod(0o644)
        with self.assertRaisesRegex(ValueError, "private ordinary"):
            readback.inspect_attempt(**args)
        args = self.args()
        self.journal_path.unlink()
        with self.assertRaises(FileNotFoundError):
            readback.inspect_attempt(**args)
        args = self.args()
        capsule = json.loads(args["capsule_raw"])
        capsule["reader_identity"] = {}
        args.update(capsule_raw=wire(capsule), expected_capsule_sha256=reader.digest(wire(capsule)))
        with self.assertRaisesRegex(ValueError, "capsule source"):
            readback.inspect_attempt(**args)

    def test_reader_does_not_spawn_query_or_read_native_payload(self):
        args = self.args()
        with (
            patch("subprocess.run", side_effect=AssertionError("spawn")),
            patch.object(launch.host_context, "capture", side_effect=AssertionError("capture")),
            patch.object(launch, "launch_native", side_effect=AssertionError("native")),
        ):
            self.assertTrue(readback.inspect_attempt(**args)["structurally_correlated"])

    def test_empty_or_wrong_typed_optional_errors_are_not_absent(self):
        for key in ("cleanup_error", "signal_error"):
            for value in ("", False, 0):
                self.receipt[key] = value
                with self.assertRaisesRegex(ValueError, "cleanup/authority"):
                    self.inspect()
            self.receipt.pop(key)
        self.receipt.update(cleanup_error=None, signal_error=None)
        self.assertTrue(self.inspect()["structurally_correlated"])

    def test_inventory_alias_traversal_and_collisions_refuse(self):
        original = dict(self.engine["files"])
        for key in ("../outside", "/absolute", "source/src", "Source/LICENSE.md"):
            self.engine["files"] = {**original, key: "e" * 64}
            with self.assertRaises(ValueError):
                self.inspect()

    def test_pid_denominator_and_metadata_root_aliases_refuse(self):
        original = copy.deepcopy(self.receipt["owned_processes"])
        self.receipt["owned_processes"].append({**original[0], "start": "different-start"})
        with self.assertRaisesRegex(ValueError, "duplicate"):
            self.inspect()
        self.receipt["owned_processes"] = [
            {"pid": 20000 + i, "ppid": 12345, "start": f"invented-start-{i}"}
            for i in range(readback.MAX_OWNED + 1)
        ]
        with self.assertRaisesRegex(ValueError, "owned start"):
            self.inspect()
        self.receipt["owned_processes"] = original
        self.host["roots"]["output"]["identity"][:2] = self.host["roots"]["evidence"]["identity"][
            :2
        ]
        with self.assertRaisesRegex(ValueError, "aliased root"):
            self.inspect()
