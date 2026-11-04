"""Tooling-host validators and unconfined controls; no automatic OS sandbox."""

import copy
import json
import os
import shutil
import socket
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from experiments.lt1_diagnostic import host_entry_probe as probe


def group(confined=True):
    return {
        **{
            name: {"denied": True, "code": "EPERM"} if confined else {"denied": False}
            for name in probe.DENIALS
        },
        "allowed_input": True,
        "allowed_scratch": True,
        "clean_declared_environment": True,
        "pid": 12345,
        "ppid": 54321,
    }


class ToolingHostEntryTests(unittest.TestCase):
    def test_supported_group_and_successful_controls_do_not_grant_authority(self):
        probe.validate_group(group(), confined=True)
        probe.validate_group(group(False), confined=False)
        self.assertTrue(all(v is False for v in probe.AUTHORITY.values()))

    def test_missing_target_refused_connection_or_generic_error_never_passes(self):
        for code in ("ENOENT", "ECONNREFUSED", "ETIMEDOUT", None):
            for name in probe.DENIALS:
                value = group()
                value[name]["code"] = code
                with self.subTest(code=code, name=name), self.assertRaises(ValueError):
                    probe.validate_group(value, confined=True)

    def test_unconfined_operation_error_cannot_masquerade_as_success(self):
        for name in probe.DENIALS:
            value = group(False)
            value[name]["code"] = "ENOENT"
            with (
                self.subTest(name=name),
                self.assertRaisesRegex(ValueError, "successful unconfined"),
            ):
                probe.validate_group(value, confined=False)

    def test_missing_allowed_controls_and_boolean_pid_refuse(self):
        for key in ("allowed_input", "allowed_scratch", "clean_declared_environment", "pid"):
            value = group()
            value[key] = False
            with self.subTest(key=key), self.assertRaises(ValueError):
                probe.validate_group(value, confined=True)

    def test_profile_is_fixed_literal_node_with_no_network_or_outside_access(self):
        policy = probe.profile(
            Path("/invented/node"), Path("/invented/input"), Path("/invented/output")
        )
        self.assertIn("(deny default)", policy)
        self.assertIn('(allow process-exec (literal "/invented/node"))', policy)
        self.assertNotIn("(allow network", policy)
        self.assertNotIn("outside", policy)
        self.assertNotIn('(subpath "/System")', policy)
        self.assertNotIn("(allow process-exec*)", policy)
        for name in probe.JS:
            self.assertIn(str(probe.HERE / name), policy)

    def test_unsupported_host_refuses_before_paths_or_runtime_lookup(self):
        with patch.object(probe.sys, "platform", "unsupported"):
            with patch.object(probe.shutil, "which", side_effect=AssertionError("runtime")):
                with self.assertRaises(probe.Unsupported):
                    probe.qualify(object())

    def test_source_identity_explicitly_binds_fixed_javascript_and_transport(self):
        value = probe.source_identity()["implementation"]
        self.assertIn("experiments/lt1_diagnostic/entry_transport.py", value)
        self.assertIn("experiments/lt1_diagnostic/entry_exec.py", value)
        for name in probe.JS:
            self.assertEqual(
                value["experiments/lt1_diagnostic/" + name], probe.digest(probe.HERE / name)
            )

    def test_selected_candidate_hash_refuses_before_any_runtime_start_or_output(self):
        with tempfile.TemporaryDirectory() as temp:
            parent = Path(temp).resolve()
            parent.chmod(0o700)
            candidate = parent / "invented-node"
            candidate.write_bytes(b"invented candidate executable")
            target = parent / "new-probe"
            with (
                patch.object(probe.sys, "platform", "darwin"),
                patch.object(probe.platform, "machine", return_value="arm64"),
            ):
                with (
                    patch.object(probe, "SANDBOX", candidate),
                    patch.object(probe.shutil, "which", return_value=str(candidate)),
                ):
                    with patch.dict(
                        probe.native_preflight.RUNTIME,
                        {"executable_sha256": probe.digest(candidate)},
                    ):
                        with patch.object(
                            probe.subprocess, "run", side_effect=AssertionError("runtime start")
                        ):
                            with self.assertRaisesRegex(ValueError, "selected candidate excluded"):
                                probe.qualify(target)
            self.assertFalse(target.exists())

    @unittest.skipUnless(os.name == "posix" and shutil.which("node"), "POSIX tooling Node required")
    def test_fixed_node_controls_actually_succeed_without_os_sandbox(self):
        with tempfile.TemporaryDirectory() as temp:
            parent = Path(temp).resolve()
            inputs, output, outside = [parent / name for name in ("input", "output", "outside")]
            for path in (inputs, output, outside):
                path.mkdir(mode=0o700)
            (inputs / "invented.txt").write_bytes(b"invented input\n")
            (outside / "secret.txt").write_bytes(b"invented sentinel\n")
            with socket.socket() as server:
                server.bind(("127.0.0.1", 0))
                server.listen(4)
                result = subprocess.run(
                    [
                        shutil.which("node"),
                        str(probe.ENTRY),
                        "controls",
                        str(inputs),
                        str(output),
                        str(outside),
                        str(server.getsockname()[1]),
                        "a" * 64,
                        "b" * 64,
                    ],
                    stdin=subprocess.DEVNULL,
                    capture_output=True,
                    env=dict(probe.transport.owner.ENVIRONMENT),
                    timeout=10,
                )
            self.assertEqual(result.returncode, 0, result.stderr)
            data = json.loads((output / "control-boundary.json").read_bytes())
            probe.validate_group(data, confined=False)
            self.assertEqual((outside / "secret.txt").read_bytes(), b"invented sentinel\n")
            self.assertEqual((outside / "output-new.txt").read_bytes(), b"invented outside write\n")

    def test_terminal_or_protocol_contradiction_refuses_before_boundary_file_intake(self):
        result = {
            "outer": {
                "status": "completed",
                "exit_code": 0,
                "error": None,
                "remaining_owned_processes": [],
                "received_signals": [],
            },
            "exchange": {
                "thread_finished": True,
                "status": "ack-sent",
                "frame_eof": True,
                "ack_sent": True,
                "ack_eof_sent": True,
                "ack_raw": b"ack",
                "ack_sent_raw": b"ack",
            },
            "source_stable": True,
            "resource_close_errors": [],
            **probe.transport.AUTHORITY,
        }
        for changes in (
            {"source_stable": False},
            {"source_stable": "false"},
            {"native_host_qualified": True},
            *(
                {"exchange": {**result["exchange"], key: value}}
                for key, value in (
                    ("thread_finished", "false"),
                    ("frame_eof", 1),
                    ("ack_sent", 1),
                    ("ack_eof_sent", 1),
                )
            ),
            {"exchange": {**result["exchange"], "ack_sent_raw": b"a"}},
            {"outer": {**result["outer"], "received_signals": [15]}},
            {"outer": {**result["outer"], "exit_code": False}},
        ):
            value = copy.deepcopy(result)
            value.update(changes)
            with self.subTest(changes=changes), self.assertRaises(ValueError):
                probe.validate_case("complete", value, object(), group(False), True)
        with self.assertRaisesRegex(ValueError, "unrelated process"):
            probe.validate_case("complete", result, object(), group(False), "false")

    def test_unconfined_receipt_requires_clean_typed_completion(self):
        control = {
            "status": "completed",
            "exit_code": 0,
            "error": None,
            "received_signals": [],
            "remaining_owned_processes": [],
        }
        probe.validate_controls(control)
        for changes in (
            {"exit_code": False},
            {"received_signals": [15]},
            {"cleanup_error": "invented"},
            {"signal_error": "invented"},
            {"remaining_owned_processes": [{"pid": 12345}]},
        ):
            with self.subTest(changes=changes), self.assertRaises(ValueError):
                probe.validate_controls({**control, **changes})

    def test_owned_lineage_requires_distinct_typed_matching_observations(self):
        result = {
            "outer": {
                "status": "completed",
                "exit_code": 0,
                "error": None,
                "remaining_owned_processes": [],
                "received_signals": [],
                "owned_processes": [
                    {"pid": 12345, "ppid": os.getpid(), "start": "invented:parent"},
                    {"pid": 12346, "ppid": 12345, "start": "invented:child"},
                ],
            },
            "exchange": {
                "thread_finished": True,
                "status": "ack-sent",
                "frame_eof": True,
                "ack_sent": True,
                "ack_eof_sent": True,
                "ack_raw": b"ack",
                "ack_sent_raw": b"ack",
            },
            "source_stable": True,
            "resource_close_errors": [],
            **probe.transport.AUTHORITY,
        }
        parent = {**group(), "ppid": os.getpid()}
        child = {**group(), "pid": 12346, "ppid": 12345}
        cases = [
            (result, parent, child),
            (
                {
                    **result,
                    "outer": {
                        **result["outer"],
                        "owned_processes": [
                            result["outer"]["owned_processes"][0],
                            {**result["outer"]["owned_processes"][1], "ppid": 99999},
                        ],
                    },
                },
                parent,
                child,
            ),
            (
                {
                    **result,
                    "outer": {
                        **result["outer"],
                        "owned_processes": result["outer"]["owned_processes"] * 2,
                    },
                },
                parent,
                child,
            ),
            (result, parent, {**child, "pid": parent["pid"]}),
            (result, parent, {**child, "pid": -1}),
            (
                {
                    **result,
                    "outer": {
                        **result["outer"],
                        "owned_processes": [
                            {**result["outer"]["owned_processes"][0], "start": ""},
                            result["outer"]["owned_processes"][1],
                        ],
                    },
                },
                parent,
                child,
            ),
        ]
        with tempfile.TemporaryDirectory() as temp:
            output = Path(temp)
            (output / "heartbeat.txt").write_bytes(b"invented heartbeat")
            (output / "handshake.json").write_text(
                json.dumps(
                    {
                        "status": "acknowledged",
                        "kind": "invented",
                    }
                )
            )
            with patch.object(probe, "ProcessTable") as table, patch.object(probe.time, "sleep"):
                table.return_value.one.return_value = None
                for index, (value, parent_group, child_group) in enumerate(cases):
                    for role, data in (("parent", parent_group), ("child", child_group)):
                        (output / (role + "-boundary.json")).write_text(json.dumps(data))
                    with self.subTest(index=index):
                        if index == 0:
                            self.assertEqual(
                                probe.validate_case(
                                    "complete",
                                    value,
                                    output,
                                    group(False),
                                    True,
                                )["status"],
                                "passed",
                            )
                        else:
                            with self.assertRaises(ValueError):
                                probe.validate_case("complete", value, output, group(False), True)
