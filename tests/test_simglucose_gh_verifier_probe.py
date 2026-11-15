"""Controller fixtures only; real sandbox twins have separate explicit qualification."""

import base64
import copy
import os
import stat
import subprocess
import sys
import tempfile
import time
import unittest
from datetime import timedelta
from pathlib import Path
from unittest import mock

from experiments.simglucose_audit import fixture_time
from experiments.simglucose_audit import gh_verifier_probe as g


class FixtureImportIsolationTests(unittest.TestCase):
    def test_discovery_imports_do_not_install_process_global_network_denials(self):
        script = """import importlib,sys
for name in ('gh_error_review','gh_verifier_probe','retained_source_review'):
 importlib.import_module('tests.test_simglucose_'+name)
sys.audit('socket.getaddrinfo','localhost',9,0,0,0)
sys.audit('socket.connect',None,('127.0.0.1',9))
"""
        # The exact events trigger the old hooks, without requiring network privileges.
        script = "import sys;sys.path.insert(0," + repr(str(g.ROOT)) + ");" + script
        result = subprocess.run(
            [sys.executable, "-I", "-S", "-B", "-c", script],
            cwd=g.ROOT,
            capture_output=True,
            timeout=5,
        )
        self.assertEqual(result.returncode, 0, result.stderr)


class GHProbeTests(unittest.TestCase):
    def setUp(self):
        self.enterContext(fixture_time.use(True))
        # Scope network denials to this case; discovery must not change other tests.
        for target in (
            "socket.create_connection",
            "socket.getaddrinfo",
            "socket.socket.connect",
            "socket.socket.connect_ex",
        ):
            guard = mock.patch(target, side_effect=PermissionError("fixture-network-denied"))
            guard.start()
            self.addCleanup(guard.stop)

    def fixture(self):
        parent = Path(
            tempfile.mkdtemp(prefix="gh-probe-invented-", dir=os.environ.get("OT062_FIXTURE_ROOT"))
        ).resolve()
        return parent, g.fixture_inputs(parent)

    def completed(self):
        parent, inputs = self.fixture()
        result = g.run_fixture_probe(inputs)
        self.assertEqual(result["status"], "completed")
        return parent, inputs, result

    def test_closed_facade_before_argument(self):
        class Trap:
            def __getattribute__(self, name):
                raise AssertionError("argument touched")

        with self.assertRaises(PermissionError):
            g.run_probe(Trap())

    def test_invented_policy_factory_and_gate_never_capture_host_policy(self):
        with mock.patch.object(g, "_policy_identity", side_effect=AssertionError("host policy")):
            _, inputs = self.fixture()
            plan, _ = g._gate(*inputs, fixture=True, headroom=True)
        self.assertEqual(plan["OS_policy"]["kind"], "invented-controller-policy")
        self.assertFalse(plan["OS_policy"]["host_policy_observed"])
        with self.assertRaises(ValueError):
            g.probe_approved(*inputs)

    def test_case_scoped_network_guard_is_active(self):
        import socket

        with self.assertRaisesRegex(PermissionError, "fixture-network-denied"):
            socket.getaddrinfo("unused.invalid", 443)

    def test_two_ordered_probes_metadata_only_and_environment_empty(self):
        parent, inputs, result = self.completed()
        self.assertEqual([r["role"] for r in result["probes"]], ["version", "help"])
        self.assertNotIn("raw_base64", g.encode(result).decode())
        self.assertFalse(result["raw_outputs_in_receipt"])
        root = parent / "invented-gh-probe"
        self.assertEqual(
            set(p.name for p in root.iterdir()),
            {".environment", "receipt.private.json", "report.private.json"},
        )
        for path in (root / ".environment").iterdir():
            self.assertTrue(path.is_dir())
            self.assertEqual(list(path.iterdir()), [])
            self.assertEqual(stat.S_IMODE(path.stat().st_mode), 0o700)
        self.assertEqual(
            g.digest((root / "receipt.private.json").read_bytes()), g.digest(g.encode(result))
        )
        self.assertTrue(
            all(
                stat.S_IMODE((root / name).stat().st_mode) == 0o600
                for name in ("report.private.json", "receipt.private.json")
            )
        )
        self.assertEqual(result["binary_hash_observation"]["body_passes"], 1)
        self.assertFalse(result["binary_hash_observation"]["OS_exec_mapping_library_IO_included"])

    def test_replay_after_rename_and_dangling_preflight(self):
        parent, inputs, _ = self.completed()
        root = parent / "invented-gh-probe"
        root.rename(parent / "retained-prefix")
        self.assertEqual(g.run_fixture_probe(inputs)["status"], "incomplete")
        parent, inputs = self.fixture()
        root = parent / "invented-gh-probe"
        root.symlink_to(parent / "absent-target")
        with (
            mock.patch.object(g, "_supervise", side_effect=AssertionError("spawn before absence")),
            self.assertRaises(ValueError),
        ):
            g.run_fixture_probe(inputs)

    def test_minted_fixture_and_actual_kind_boundary(self):
        _, inputs = self.fixture()
        plan, approval, origin, held = inputs
        changed = g.decode(plan)
        changed["qualification_sha256"] = "0" * 64
        raw = g.encode(changed)
        grant = g.decode(approval)
        grant["plan_sha256"] = g.digest(raw)
        grant_raw = g.encode(grant)
        forged = (
            raw,
            grant_raw,
            origin,
            held | {"plan_sha256": g.digest(raw), "approval_sha256": g.digest(grant_raw)},
        )
        with (
            mock.patch.object(g.os, "open", side_effect=AssertionError("foreign fixture path")),
            self.assertRaises(ValueError),
        ):
            g.run_fixture_probe(forged)
        with (
            mock.patch.object(
                g.os, "open", side_effect=AssertionError("actual path before consent")
            ),
            self.assertRaises(ValueError),
        ):
            g.probe_approved(*inputs)

    def test_nonzero_version_help_and_UTF8_stop_prefix(self):
        for case in (
            "nonzero",
            "version-mismatch",
            "help-mismatch",
            "invalidUTF8",
            "help-prefix-only",
        ):
            with self.subTest(case=case):
                _, inputs = self.fixture()
                result = g.run_fixture_probe(inputs, case)
                self.assertEqual(result["status"], "rejected")
                self.assertEqual(result["probes"][-1]["status"], "rejected")
                self.assertEqual(
                    len(result["probes"]), 2 if case in ("help-mismatch", "help-prefix-only") else 1
                )

    def test_each_stream_cap_and_unstored_sentinel(self):
        for case, stream in (
            ("stdout-overflow", "stdout"),
            ("stderr-overflow", "stderr"),
            ("fullpipe", "stdout"),
        ):
            with self.subTest(case=case):
                _, inputs = self.fixture()
                result = g.run_fixture_probe(inputs, case)
                self.assertEqual(result["status"], "rejected")
                row = result["probes"][0]
                self.assertEqual(row["consumed_application_bytes"][stream], 8193)
                self.assertEqual(row["stored_bytes"][stream], 8192)
                self.assertEqual(row["stored_sha256"][stream], g.digest(b"x" * 8192))
                self.assertNotIn("raw_base64", row)

    def test_drip_timeout_is_whole_elapsed_not_socket_idle(self):
        _, inputs = self.fixture()
        start = time.monotonic()
        result = g.run_fixture_probe(inputs, "drip", probe_seconds=0.2)
        self.assertEqual(result["status"], "rejected")
        self.assertEqual(len(result["probes"]), 1)
        self.assertLess(time.monotonic() - start, 2)

    def test_owned_blocking_stage_deadlines(self):
        for case in (
            "hash-stall",
            "probe-stall",
            "write-stall",
            "fsync-stall",
            "finalize-stall",
            "exit-survivor",
            "spawn-stall",
        ):
            with self.subTest(case=case):
                _, inputs = self.fixture()
                start = time.monotonic()
                try:
                    result = g.run_fixture_probe(inputs, case, whole_seconds=0.7, probe_seconds=0.2)
                except ValueError as error:
                    self.assertEqual(case, "exit-survivor")
                    self.assertEqual(str(error), "owned-cleanup-failed")
                    result = {"status": "incomplete"}
                self.assertIn(result["status"], ("rejected", "incomplete"))
                self.assertLess(time.monotonic() - start, 2)

    def test_protocol_receipt_then_error_or_nonzero_never_success(self):
        for case in ("receipt-then-error", "receipt-then-nonzero"):
            _, inputs = self.fixture()
            self.assertEqual(g.run_fixture_probe(inputs, case)["status"], "incomplete")

    def test_wrong_binary_context_no_invocation(self):
        parent, inputs = self.fixture()
        path = parent / "invented-binary.bin"
        path.write_bytes(b"X" * path.stat().st_size)
        with mock.patch.object(g, "_run_probe", side_effect=AssertionError("parent cannot invoke")):
            result = g.run_fixture_probe(inputs)
        self.assertEqual(result["status"], "incomplete")
        self.assertFalse((parent / "invented-gh-probe").exists())

    def test_binary_FD_name_parent_binding_no_private_mode_requirement(self):
        parent, inputs = self.fixture()
        plan = g.decode(inputs[0])
        directory = parent / "installation"
        directory.mkdir(mode=0o755)
        path = directory / "candidate"
        path.write_bytes(b"invented")
        fd = os.open(directory, os.O_RDONLY | os.O_DIRECTORY)
        try:
            identity = g._parent_identity(fd)
        finally:
            os.close(fd)
        plan["binary"] = {
            "path": str(path),
            "bytes": 8,
            "sha256": g.digest(b"invented"),
            "token": g._token(path.lstat()),
            "parent_path": str(directory),
            "parent_identity": identity,
        }
        expiry = g.core._now() + timedelta(seconds=10)
        fd, row = g._hash_binary(plan, expiry, time.monotonic() + 5)
        try:
            self.assertEqual(row["bytes"], 8)
            path.rename(directory / "old")
            path.write_bytes(b"invented")
            with self.assertRaises(ValueError):
                g._binary_context(plan, expiry, time.monotonic() + 5, fd)
        finally:
            os.close(fd)

    def test_binary_symlink_FIFO_and_hardlink_refuse(self):
        for kind in ("symlink", "fifo", "hardlink"):
            parent, inputs = self.fixture()
            path = parent / "invented-binary.bin"
            old = parent / "preserved-invented"
            path.rename(old)
            if kind == "symlink":
                path.symlink_to(old)
            elif kind == "fifo":
                os.mkfifo(path, 0o600)
            else:
                os.link(old, path)
            self.assertEqual(g.run_fixture_probe(inputs)["status"], "incomplete")

    def test_base64_worst_raw_report_fits_without_text_duplicate(self):
        report = {
            "probes": [
                {
                    "raw_base64": {
                        s: base64.b64encode(bytes(range(256)) * 32).decode()
                        for s in ("stdout", "stderr")
                    }
                }
                for _ in range(2)
            ]
        }
        self.assertLess(len(g.encode(report)), 65536)
        self.assertNotIn("raw_text", g.encode(report).decode())

    def test_metadata_historical_grant_current_retention_no_report_or_binary_open(self):
        parent, inputs, result = self.completed()
        original = os.open

        def guarded(path, *args, **kwargs):
            if os.fsdecode(path) in (str(parent / "invented-binary.bin"), "report.private.json"):
                raise AssertionError("cold material access")
            return original(path, *args, **kwargs)

        future = g.core._now() + timedelta(hours=2)
        with (
            mock.patch.object(g.core, "_now", return_value=future),
            mock.patch.object(g.os, "open", guarded),
        ):
            self.assertEqual(
                g.inspect_receipt_metadata(
                    *inputs, held_receipt_sha256=g.digest(g.encode(result)), fixture=True
                ),
                result,
            )
        with (
            mock.patch.object(g.core, "_now", return_value=future + timedelta(days=2)),
            mock.patch.object(g.os, "open", side_effect=AssertionError("expired retention path")),
            self.assertRaises(ValueError),
        ):
            g.inspect_receipt_metadata(
                *inputs, held_receipt_sha256=g.digest(g.encode(result)), fixture=True
            )

    def test_strict_rehashed_receipt_mutations(self):
        _, inputs, result = self.completed()
        plan = g.decode(inputs[0])
        grant = g.decode(inputs[1])
        issued = g.core._utc(grant["issued_utc"])
        expiry = g.core._utc(grant["expires_utc"])
        changes = [
            lambda x: x.update(raw_outputs_in_receipt=True),
            lambda x: x.update(report_readback_passes=True),
            lambda x: x.update(ended_utc="2099-01-01T00:00:00Z"),
            lambda x: x["probes"].reverse(),
            lambda x: x["probes"][0].update(real_crypto_or_artifact_verification=True),
            lambda x: x["probes"][0]["consumed_application_bytes"].update(stdout=8194),
            lambda x: x["probes"][0]["parsed"].update(extra="raw"),
            lambda x: x["binary_hash_observation"].update(OS_exec_mapping_library_IO_included=True),
        ]
        for mutate in changes:
            changed = copy.deepcopy(result)
            mutate(changed)
            with self.assertRaises(ValueError):
                g._validate_receipt(changed, plan, inputs[3], True, issued, expiry)

    def test_empty_outputs_cannot_claim_successful_parsed_markers(self):
        _, inputs, result = self.completed()
        changed = copy.deepcopy(result)
        plan = g.decode(inputs[0])
        grant = g.decode(inputs[1])
        for row in changed["probes"]:
            row["consumed_application_bytes"] = {"stdout": 0, "stderr": 0}
            row["stored_bytes"] = {"stdout": 0, "stderr": 0}
            row["stored_sha256"] = {"stdout": g.digest(b""), "stderr": g.digest(b"")}
        with self.assertRaises(ValueError):
            g._validate_receipt(
                changed,
                plan,
                inputs[3],
                True,
                g.core._utc(grant["issued_utc"]),
                g.core._utc(grant["expires_utc"]),
            )

    def test_exact_environment_no_auth_proxy_config_inheritance(self):
        _, inputs = self.fixture()
        env = g._environment(g.decode(inputs[0]))
        self.assertNotIn("GH_TOKEN", env)
        self.assertNotIn("HTTP_PROXY", env)
        self.assertNotIn("DYLD_INSERT_LIBRARIES", env)
        self.assertEqual(env["GIT_CONFIG_GLOBAL"], "/dev/null")
        self.assertEqual(env["GH_CONFIG_DIR"], env["XDG_CONFIG_HOME"])

    def test_profile_fixed_rules_and_fixture_delta(self):
        _, inputs = self.fixture()
        plan = g.decode(inputs[0])
        actual = g._profile(plan)
        fixture = g._profile(plan, True)
        for profile in (actual, fixture):
            self.assertIn("(deny default)", profile)
            self.assertIn(str(g.DYLD), profile)
            self.assertEqual(profile.count("(allow sysctl-read"), 1)
            self.assertIn('(allow sysctl-read (sysctl-name "hw.pagesize"))', profile)
            for forbidden in (
                "(allow mach-lookup",
                "(allow process-fork",
                "(allow network",
                "(allow file-read-metadata)",
            ):
                self.assertNotIn(forbidden, profile)
        self.assertNotIn(str(Path(sys.executable).resolve().parent.parent), actual)
        self.assertIn(str(Path(sys.executable).resolve().parent.parent), fixture)

    def test_singleton_sysctl_policy_cannot_be_extended_by_plan(self):
        _, inputs = self.fixture()
        plan_raw, approval_raw, origin_raw, held = inputs
        plan = g.decode(plan_raw)
        self.assertEqual(plan["OS_policy"]["sysctl_read_names"], ["hw.pagesize"])
        self.assertFalse(plan["OS_policy"]["global_sysctl_read"])
        for names in ([], ["hw.ncpu"], ["hw.pagesize", "hw.ncpu"], ["hw."], ["hw.pagesize.*"]):
            changed = g.decode(plan_raw)
            changed["OS_policy"]["sysctl_read_names"] = names
            raw = g.encode(changed)
            grant = g.decode(approval_raw)
            grant["plan_sha256"] = g.digest(raw)
            approval = g.encode(grant)
            external = held | {"plan_sha256": g.digest(raw), "approval_sha256": g.digest(approval)}
            with self.assertRaises(ValueError):
                g._gate(raw, approval, origin_raw, external, True)
        baseline = g._profile({}, True, control=("sysctl-baseline", None))
        candidate = g._profile({}, True)
        self.assertEqual(
            candidate.replace('(allow sysctl-read (sysctl-name "hw.pagesize"))\n', ""), baseline
        )
        neighbor = g._profile({}, True, control=("sysctl-neighbor", None))
        self.assertEqual(neighbor, candidate + '(allow sysctl-read (sysctl-name "hw.ncpu"))\n')
        with self.assertRaises(ValueError):
            g._profile(plan, control=("sysctl-neighbor", None))
        with self.assertRaises(ValueError):
            g._profile(plan, True, control=("sysctl-neighbor", "arbitrary"))

    def test_queue_failure_precedes_worker_spawn(self):
        with (
            mock.patch.object(
                g.queue, "Queue", side_effect=MemoryError("invented queue allocation")
            ),
            mock.patch.object(
                g.platform_process, "spawn", side_effect=AssertionError("spawn before Queue")
            ) as spawn,
            self.assertRaises(MemoryError),
        ):
            g._supervise({"fixture": False}, time.monotonic() + 1)
        spawn.assert_not_called()

    def test_leaf_buffer_failure_precedes_Popen(self):
        _, inputs = self.fixture()
        plan = g.decode(inputs[0])
        with (
            mock.patch.object(
                g, "bytearray", create=True, side_effect=MemoryError("invented stream buffer")
            ),
            mock.patch.object(
                g.subprocess, "Popen", side_effect=AssertionError("Popen before buffer")
            ) as spawn,
            mock.patch.object(g, "_emit"),
            self.assertRaises(MemoryError),
        ):
            g._run_probe(
                plan,
                "version",
                g.core._now() + timedelta(seconds=20),
                time.monotonic() + 10,
                True,
                "ok",
            )
        spawn.assert_not_called()

    def test_namespace_extra_environment_file_refuses_cold(self):
        parent, inputs, result = self.completed()
        (parent / "invented-gh-probe/.environment/home/forbidden").write_bytes(b"invented")
        with self.assertRaises(ValueError):
            g.inspect_receipt_metadata(
                *inputs, held_receipt_sha256=g.digest(g.encode(result)), fixture=True
            )

    def test_checked_report_short_and_zero_writes(self):
        parent = Path(
            tempfile.mkdtemp(prefix="gh-output-", dir=os.environ.get("OT062_FIXTURE_ROOT"))
        ).resolve()
        directory = g.core._directory(str(parent))
        original = os.write
        expiry = g.core._now() + timedelta(seconds=10)
        raw = g.encode({"invented": "x"})
        try:
            with mock.patch.object(g.os, "write", lambda fd, data: original(fd, data[:1])):
                g._write_output(directory, raw, expiry, time.monotonic() + 5)
            self.assertEqual((parent / "report.private.json").read_bytes(), raw)
        finally:
            os.close(directory)
        parent = Path(
            tempfile.mkdtemp(prefix="gh-zero-", dir=os.environ.get("OT062_FIXTURE_ROOT"))
        ).resolve()
        directory = g.core._directory(str(parent))
        try:
            with mock.patch.object(g.os, "write", return_value=0), self.assertRaises(ValueError):
                g._write_output(directory, raw, expiry, time.monotonic() + 5)
        finally:
            os.close(directory)

    def test_source_named_binding_and_cleanup_aggregation(self):
        parent = Path(
            tempfile.mkdtemp(prefix="gh-source-", dir=os.environ.get("OT062_FIXTURE_ROOT"))
        ).resolve()
        source = parent / "source"
        source.mkdir()
        path = source / "module.py"
        path.write_bytes(b"invented old")
        alternate = parent / "alternate"
        alternate.mkdir()
        (alternate / "module.py").write_bytes(b"invented new")
        original = os.read
        swapped = False

        def read(fd, n):
            nonlocal swapped
            data = original(fd, n)
            if not swapped:
                swapped = True
                source.rename(parent / "preserved")
                alternate.rename(source)
            return data

        with mock.patch.object(g.os, "read", read), self.assertRaises(ValueError):
            g._source_hash(path)
        process = mock.Mock()
        process.poll.return_value = 0
        with (
            mock.patch.object(g.platform_process, "tree_exists", side_effect=OSError("invented")),
            mock.patch.object(g.platform_process, "close_tree") as close,
            self.assertRaises(ValueError),
        ):
            g._stop(process, None, None, True, time.monotonic() + 1)
        close.assert_called_once_with(process)


if __name__ == "__main__":
    unittest.main()
