"""Pure POSIX fixture controls; no automatic sandbox, executable or socket launch."""

import copy
import errno
import json
import os
import stat
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from experiments.lt1_diagnostic import host_boundary_fixture as fixture
from experiments.lt1_diagnostic import host_boundary_probe as probe


@unittest.skipUnless(os.name == "posix", "POSIX boundary fixture helpers required")
class HostBoundaryTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        self.controls = dict.fromkeys(probe.DENIALS, True)
        self.group = {name: {"denied": True, "errno": errno.EPERM} for name in probe.DENIALS}
        self.group.update(
            allowed_input=True, allowed_scratch=True, isolated_start=True, clean_environment=True
        )
        for name in ("boundary.json", "child-boundary.json"):
            self.write(name, self.group)
        self.write("child-ready.json", {"pid": 123})
        self.write("completed.json", {"kind": "invented", "status": "completed"})
        self.write_bytes("heartbeat.txt", b"stopped")
        self.write_bytes(
            "prefix.jsonl",
            b"".join(
                (json.dumps({"kind": "invented", "ordinal": i, "time_ms": t}) + "\n").encode()
                for i, t in enumerate((0, 60000, 150000))
            ),
        )
        self.receipt = {
            "status": "completed",
            "exit_code": 0,
            "error": None,
            "remaining_owned_processes": [],
            "received_signals": [],
            "owned_processes": [{"pid": 123, "start": "invented:start"}],
        }
        table = patch.object(probe.legacy, "ProcessTable")
        self.table = table.start()
        self.addCleanup(table.stop)
        self.table.return_value.one.return_value = None
        sleep = patch.object(probe.time, "sleep")
        self.sleep = sleep.start()
        self.addCleanup(sleep.stop)

    def write(self, name, value):
        (self.root / name).write_text(json.dumps(value))

    def write_bytes(self, name, value):
        (self.root / name).write_bytes(value)

    def validate(self, mode="complete", receipt=None, controls=None):
        return probe.validate_case(
            mode,
            receipt or self.receipt,
            self.root,
            True,
            self.controls if controls is None else controls,
        )

    def test_complete_requires_both_boundary_groups_and_observed_child(self):
        result = self.validate()
        self.assertEqual(result["boundary_groups"], 2)
        self.assertEqual(result["denials_per_group"], 9)
        for rows in ([], [{"pid": 123}], [{"pid": 123, "start": ""}]):
            with self.assertRaisesRegex(ValueError, "start identity"):
                self.validate(receipt={**self.receipt, "owned_processes": rows})

    def test_complete_rejects_missing_child_or_live_child(self):
        self.table.return_value.one.return_value = {"alive": True}
        with self.assertRaisesRegex(ValueError, "remains alive"):
            self.validate()
        self.table.return_value.one.return_value = None
        (self.root / "child-ready.json").unlink()
        with self.assertRaises(FileNotFoundError):
            self.validate()

    def test_complete_marker_and_unrelated_control_are_still_required(self):
        with self.assertRaisesRegex(ValueError, "unrelated"):
            probe.validate_case("complete", self.receipt, self.root, False, self.controls)
        (self.root / "completed.json").unlink()
        with self.assertRaises(FileNotFoundError):
            self.validate()

    def test_completion_rejects_bool_exit_and_contradictory_errors(self):
        for change in (
            {"exit_code": False},
            {"exit_code": 0.0},
            {"error": "invented primary failure"},
            {"cleanup_error": "invented cleanup failure"},
        ):
            with self.subTest(change=change), self.assertRaises(ValueError):
                self.validate(receipt={**self.receipt, **change})

    def test_executable_denial_reaches_exec_without_opening_devnull(self):
        with (
            patch.object(
                subprocess.Popen,
                "_get_devnull",
                side_effect=PermissionError(errno.EACCES, "invented stdio failure"),
            ) as devnull,
            patch.object(
                subprocess.Popen,
                "_execute_child",
                side_effect=PermissionError(errno.EPERM, "invented exec denial"),
            ) as execute,
        ):
            self.assertEqual(
                fixture.observe(fixture.fixed_shell), {"denied": True, "errno": errno.EPERM}
            )
        devnull.assert_not_called()
        execute.assert_called_once()

    def test_cancel_reuses_legacy_cause_prefix_cleanup_and_no_completion(self):
        (self.root / "completed.json").unlink()
        receipt = {**self.receipt, "status": "interrupted", "error": "Cancelled", "exit_code": -15}
        self.assertEqual(self.validate("cancel", receipt)["boundary_groups"], 2)
        with self.assertRaisesRegex(ValueError, "cause differs"):
            self.validate("cancel", {**receipt, "error": "WorkerDeadline"})
        with self.assertRaisesRegex(ValueError, "cleanup"):
            self.validate("cancel", {**receipt, "remaining_owned_processes": None})

    def test_all_denials_need_exact_errno_in_parent_and_child(self):
        for filename in ("boundary.json", "child-boundary.json"):
            for denial in probe.DENIALS:
                for bad in (
                    {"denied": True, "errno": errno.ENOENT},
                    {"denied": True, "errno": errno.ECONNREFUSED},
                    {"denied": True, "errno": True},
                    {"denied": False, "errno": errno.EPERM},
                ):
                    changed = copy.deepcopy(self.group)
                    changed[denial] = bad
                    self.write(filename, changed)
                    with self.subTest(filename=filename, denial=denial, bad=bad):
                        with self.assertRaises(ValueError):
                            self.validate()
                self.write(filename, self.group)

    def test_allowed_scratch_and_all_existing_allowed_flags_are_required(self):
        for name in ("allowed_input", "allowed_scratch", "isolated_start", "clean_environment"):
            changed = {**self.group, name: "true"}
            self.write("child-boundary.json", changed)
            with self.assertRaisesRegex(ValueError, "boundary observation"):
                self.validate()

    def test_missing_or_false_unconfined_control_refuses_before_legacy_validation(self):
        for controls in (
            {},
            {**self.controls, "network": False},
            {**self.controls, "data_alias_read": "true"},
            {**self.controls, "extra": True},
        ):
            with patch.object(probe.legacy, "validate_case") as old:
                with self.assertRaisesRegex(ValueError, "unconfined control"):
                    self.validate(controls=controls)
                old.assert_not_called()

    def test_changing_or_empty_heartbeat_cannot_complete(self):
        self.write_bytes("heartbeat.txt", b"")
        with self.assertRaisesRegex(ValueError, "heartbeat"):
            self.validate()
        self.write_bytes("heartbeat.txt", b"before")
        self.sleep.side_effect = lambda _delay: self.write_bytes("heartbeat.txt", b"after")
        with self.assertRaisesRegex(ValueError, "heartbeat"):
            self.validate()

    def test_external_signal_and_unknown_case_never_pass(self):
        with self.assertRaisesRegex(ValueError, "external interruption"):
            self.validate(receipt={**self.receipt, "received_signals": [15]})
        with self.assertRaisesRegex(ValueError, "Unknown"):
            self.validate("failure")

    def test_profile_narrows_system_but_documents_broad_mach_limit(self):
        hostile = Path('/invented/"\n(allow default)')
        policy = probe.profile(
            hostile, Path("/runtime"), Path("/fixture"), Path("/input"), Path("/out")
        )
        self.assertNotIn('(subpath "/System")', policy)
        self.assertEqual(policy.count('(subpath "/System/Library")'), 2)
        self.assertIn("(allow mach-lookup)", policy)
        self.assertIn(probe.legacy.quoted(hostile), policy)
        self.assertNotIn("\n(allow default)", policy)
        self.assertNotIn("(allow network", policy)
        self.assertNotIn('(literal "/bin/sh")', policy)
        with patch.object(probe.legacy, "profile", return_value="(deny default)\n"):
            with self.assertRaisesRegex(ValueError, "Legacy system profile changed"):
                probe.profile(None, None, None, None, None)

    def test_alias_needs_existing_same_canonical_target_and_real_read_control(self):
        secret = self.root / "secret.txt"
        probe.private_bytes(secret, probe.SENTINEL)
        mirror = self.root / "mirror"
        alias = mirror / secret.relative_to("/")
        alias.parent.mkdir(parents=True)
        with patch.object(probe, "DATA_ROOT", mirror):
            with self.assertRaises(probe.Unsupported):
                probe.data_alias(secret)
            alias.symlink_to(secret)
            self.assertEqual(probe.data_alias(secret), alias)
            alias.unlink()
            other = self.root / "other.txt"
            probe.private_bytes(other, probe.SENTINEL)
            alias.symlink_to(other)
            with self.assertRaisesRegex(probe.Unsupported, "canonical target"):
                probe.data_alias(secret)

    def test_private_writes_are_exclusive_and_owner_only(self):
        path = self.root / "new.txt"
        probe.private_bytes(path, b"invented")
        self.assertEqual(stat.S_IMODE(path.stat().st_mode), 0o600)
        with self.assertRaises(FileExistsError):
            probe.private_bytes(path, b"replacement")
        self.assertEqual(path.read_bytes(), b"invented")

    def test_alias_object_identity_does_not_require_equal_path_strings(self):
        secret, alias = self.root / "original.txt", self.root / "distinct-alias.txt"
        probe.private_bytes(secret, probe.SENTINEL)
        os.link(secret, alias)  # Invented stand-in for distinct names of one object.
        self.assertNotEqual(secret.resolve(), alias.resolve())
        self.assertTrue(probe.alias_control(alias, secret))

    def test_sources_close_initializers_and_changed_final_sources_fail(self):
        probe_source = "from experiments.extra import value\n"
        files = {
            "experiments/lt1_diagnostic/host_boundary_probe.py": probe_source,
            "experiments/lt1_diagnostic/host_boundary_fixture.py": "# invented\n",
            "experiments/lt1_diagnostic/__init__.py": "from experiments.nested import value\n",
            "experiments/extra.py": "value = 1\n",
            "experiments/nested.py": "value = 2\n",
        }
        for name, raw in files.items():
            path = self.root / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(raw)
        with (
            patch.object(probe, "ROOT", self.root),
            patch.object(probe, "HERE", self.root / "experiments/lt1_diagnostic"),
            patch("experiments.m4.initial_load.common.ROOT", self.root),
        ):
            before = probe.sources()
            self.assertEqual(set(before), set(files))
            report = {"status": "passed", "implementation": before}
            probe.check_final_sources(report)
            self.assertEqual(report["status"], "passed")
            (self.root / "experiments/nested.py").write_text("value = 3\n")
            probe.check_final_sources(report)
            self.assertEqual(report["status"], "failed")
            self.assertTrue(report["source_change"])

    def test_unsupported_host_and_unintegrated_drafts_cannot_launch(self):
        target = self.root / "not-created"
        with (
            patch.object(probe.sys, "platform", "linux"),
            patch.object(probe.legacy, "supervise") as supervise,
        ):
            with self.assertRaises(probe.Unsupported):
                probe.qualify(target)
            supervise.assert_not_called()
        self.assertFalse(target.exists())
        sandbox = self.root / "sandbox-stub"
        probe.private_bytes(sandbox, b"inert invented stub, never executed")
        with (
            patch.object(probe, "HERE", self.root / "not-canonical"),
            patch.object(probe.sys, "platform", "darwin"),
            patch.object(probe.platform, "machine", return_value="arm64"),
            patch.object(probe.legacy, "SANDBOX", sandbox),
            patch.object(probe.legacy, "supervise") as supervise,
        ):
            with self.assertRaisesRegex(ValueError, "canonical boundary sources"):
                probe.qualify(target)
            supervise.assert_not_called()
        self.assertFalse(target.exists())

    def test_fixture_observation_and_probe_agree_and_missing_is_not_denial(self):
        self.assertEqual(fixture.DENIALS, probe.DENIALS)
        self.assertEqual(fixture.observe(lambda: None), {"denied": False})
        for code in (errno.EPERM, errno.EACCES, errno.ENOENT, errno.ECONNREFUSED):

            def fail():
                raise OSError(code, "invented")

            observed = fixture.observe(fail)
            self.assertEqual(observed["denied"], code in {errno.EPERM, errno.EACCES})


if __name__ == "__main__":
    unittest.main()
