"""Fixture-only host qualification controls; no automatic sandbox/native launch."""

import copy
import errno
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from experiments.lt1_diagnostic import host_probe as probe


class LT1HostProbeTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.checks = {
            name: {"denied": True, "errno": errno.EPERM}
            for name in ("outside_read", "outside_write", "network")
        }
        self.checks.update(allowed_input=True, isolated_start=True, clean_environment=True)
        self.write("boundary.json", self.checks)
        self.rows = [
            {"kind": "invented", "ordinal": i, "time_ms": t}
            for i, t in enumerate((0, 60000, 150000))
        ]
        self.prefix()
        self.write("completed.json", {"kind": "invented", "status": "completed"})
        self.receipt = {
            "status": "completed",
            "exit_code": 0,
            "error": None,
            "remaining_owned_processes": [],
            "owned_processes": [],
            "received_signals": [],
        }

    def write(self, name, value):
        (self.root / name).write_text(json.dumps(value))

    def prefix(self):
        (self.root / "prefix.jsonl").write_text(
            "".join(json.dumps(row) + "\n" for row in self.rows)
        )

    def test_completion_requires_exact_explicit_marker_and_all_observations(self):
        self.assertEqual(
            probe.validate_case("complete", self.receipt, self.root, True)["durable_rows"], 3
        )
        (self.root / "completed.json").unlink()
        with self.assertRaises(FileNotFoundError):
            probe.validate_case("complete", self.receipt, self.root, True)
        self.write("completed.json", {"kind": "invented", "status": "failed"})
        with self.assertRaisesRegex(ValueError, "completion marker"):
            probe.validate_case("complete", self.receipt, self.root, True)

    def test_external_signals_cannot_satisfy_intentional_cancel_or_final_case(self):
        for mode in probe.MODES:
            receipt = {**self.receipt, "received_signals": [15]}
            with self.assertRaisesRegex(ValueError, "external interruption"):
                probe.validate_case(mode, receipt, self.root, True)
        unknown = {key: value for key, value in self.receipt.items() if key != "received_signals"}
        with self.assertRaisesRegex(ValueError, "external interruption"):
            probe.validate_case("complete", unknown, self.root, True)
        with self.assertRaisesRegex(ValueError, "Unknown case"):
            probe.validate_case("other", self.receipt, self.root, True)

    def test_connection_refusal_truthy_flag_and_boolean_time_are_not_denial_evidence(self):
        for mutate in (
            lambda checks: checks["network"].update(errno=errno.ECONNREFUSED),
            lambda checks: checks["outside_read"].update(denied=False),
            lambda checks: checks.update(clean_environment="true"),
        ):
            changed = copy.deepcopy(self.checks)
            mutate(changed)
            self.write("boundary.json", changed)
            with self.assertRaisesRegex(ValueError, "observation"):
                probe.validate_case("complete", self.receipt, self.root, True)
        self.write("boundary.json", self.checks)
        self.rows[0]["time_ms"] = False
        self.prefix()
        with self.assertRaisesRegex(ValueError, "prefix"):
            probe.validate_case("complete", self.receipt, self.root, True)

    def test_failures_keep_prefix_child_ownership_and_distinct_causes(self):
        (self.root / "completed.json").unlink()
        self.write("child-ready.json", {"pid": 123})
        self.write("child-boundary.json", self.checks)
        (self.root / "heartbeat.txt").write_text("stopped")
        with patch.object(probe, "ProcessTable") as table, patch.object(probe.time, "sleep"):
            table.return_value.one.return_value = None
            for mode, status, error, code in (
                ("failure", "failed", None, 23),
                ("deadline", "failed", "WorkerDeadline", -15),
                ("cancel", "interrupted", "Cancelled", -15),
            ):
                receipt = {
                    **self.receipt,
                    "status": status,
                    "error": error,
                    "exit_code": code,
                    "owned_processes": [{"pid": 123}],
                }
                self.assertEqual(
                    probe.validate_case(mode, receipt, self.root, True)["boundary_groups"], 2
                )
                with self.assertRaisesRegex(ValueError, "cleanup"):
                    probe.validate_case(
                        mode, {**receipt, "remaining_owned_processes": None}, self.root, True
                    )
                with self.assertRaisesRegex(ValueError, "unrelated"):
                    probe.validate_case(mode, receipt, self.root, False)
                with self.assertRaisesRegex(ValueError, "ownership"):
                    probe.validate_case(mode, {**receipt, "owned_processes": []}, self.root, True)
            self.write("completed.json", {"kind": "invented", "status": "completed"})
            with self.assertRaisesRegex(ValueError, "promoted"):
                probe.validate_case("cancel", receipt, self.root, True)

    def test_profile_quotes_paths_and_never_grants_network(self):
        path = Path('/invented/"\n(allow default)')
        policy = probe.profile(path, Path("/runtime"), Path("/fixture"), Path("/in"), Path("/out"))
        self.assertIn("(deny default)", policy)
        self.assertIn(probe.quoted(path), policy)
        self.assertNotIn("\n(allow default)", policy)
        self.assertNotIn("(allow network", policy)
        self.assertNotIn('(subpath "/")', policy)

    def test_source_identity_covers_reused_process_implementation(self):
        files = probe.sources()
        for name in (
            "experiments/lt1_diagnostic/host_probe.py",
            "experiments/lt1_diagnostic/host_fixture.py",
            "experiments/shared_services/execution.py",
            "experiments/gui/ownership.py",
            "experiments/platform_process.py",
        ):
            self.assertIn(name, files)
            self.assertEqual(files[name], probe.digest(probe.ROOT / name))

    def test_unsupported_host_refuses_before_output_creation(self):
        target = self.root / "not-created"
        with patch.object(probe.sys, "platform", "linux"):
            with self.assertRaisesRegex(ValueError, "Darwin arm64"):
                probe.qualify(target)
        self.assertFalse(target.exists())

    def test_missing_or_invalid_final_sources_retain_failed_qualification(self):
        for error in (OSError("removed helper"), SyntaxError("changed helper")):
            report = {"status": "passed", "implementation": {"helper": "old"}}
            with patch.object(probe, "sources", side_effect=error):
                probe.check_final_sources(report)
            self.assertEqual(report["status"], "failed")
            self.assertTrue(report["source_change"])
            self.assertIn("helper", report["source_error"])
