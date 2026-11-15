"""Controlled invented collector qualification; no network or asset intake."""

import base64
import copy
import io
import os
import socket
import ssl
import subprocess
import sys
import tempfile
import time
import unittest
from datetime import timedelta
from pathlib import Path
from unittest.mock import Mock, patch

from experiments.simglucose_audit import fixture_time
from experiments.simglucose_audit import intake_collector as collector
from experiments.simglucose_audit.contract import decode, digest, encode


@unittest.skipUnless(
    hasattr(os, "O_NOFOLLOW") and os.open in os.supports_dir_fd,
    "nofollow dir-fd host unavailable; not qualified",
)
class SimglucoseIntakeCollectorTests(unittest.TestCase):
    def setUp(self):
        self.enterContext(fixture_time.use(True))
        base = os.environ.get("OT062_COLLECTOR_FIXTURE_PROOF_ROOT", tempfile.gettempdir())
        self.root = Path(tempfile.mkdtemp(prefix="collector-test-", dir=base)).resolve()

    def request(self, case="ok"):
        return encode({"schema": collector.SCHEMA, "kind": "invented", "case": case})

    def run_case(self, case="ok"):
        destination = self.root / case
        inputs = collector.fixture_inputs(destination)
        with patch.object(collector, "fixture_inputs", return_value=inputs):
            result = collector.run_fixture_collector(self.request(case), destination)
        files = collector.read_intake_fixture(destination)
        return inputs, result, files

    def inspect(self, inputs, result, files):
        plan, approval, _notice, origin = inputs
        return collector.inspect_intake_fixture(
            files,
            result["receipt_sha256"],
            plan,
            digest(plan),
            approval,
            digest(approval),
            origin,
            digest(origin),
        )

    def test_three_fixed_gets_notice_first_opaque_sizes_hashes_and_cold_read(self):
        inputs, result, files = self.run_case()
        self.assertEqual(self.inspect(inputs, result, files)["status"], "completed")
        receipt = result["receipt"]
        self.assertEqual([row["status"] for row in receipt["targets"]], ["accepted"] * 3)
        self.assertEqual(
            [len(files["objects/" + name]) for name in collector.NAMES], list(collector.SIZES)
        )
        self.assertEqual(len(files["notices/simglucose-LICENSE.txt"]), 1052)
        self.assertLessEqual(sum(map(len, files.values())), 84752)
        self.assertEqual(result["returncode"], 0)
        self.assertFalse(receipt["actual_HTTPS_qualified"])
        self.assertFalse(receipt["authority"]["native_execution_authorized"])
        self.assertNotIn("passive_intake", receipt["authority"])
        for row in receipt["targets"]:
            self.assertEqual(row["process"]["source_before"], row["process"]["source_after"])
            self.assertLessEqual(row["process"]["elapsed_ns"], 30_000_000_000)

    def test_missing_length_still_requires_unframed_eof(self):
        inputs, result, files = self.run_case("no-content-length")
        self.assertEqual(result["status"], "completed")
        self.assertIsNone(result["receipt"]["targets"][0]["headers"]["content_length"])
        self.inspect(inputs, result, files)

    def test_sentinel_short_blob_status_and_header_failures_stop_after_first(self):
        for case in (
            "extra-first",
            "short-first",
            "blob-first",
            "status-first",
            "redirect-first",
            "duplicate-cl",
            "duplicate-ce",
            "bad-cl",
            "transfer-encoding",
            "encoding",
            "bad-header",
            "header-overflow",
        ):
            with self.subTest(case=case):
                inputs, result, files = self.run_case(case)
                self.assertEqual(result["status"], "incomplete")
                self.assertEqual(
                    [row["status"] for row in result["receipt"]["targets"]][1:],
                    ["not-run", "not-run"],
                )
                self.assertNotIn("objects/sensor_params.csv", files)
                self.assertNotIn("objects/pump_params.csv", files)
                self.assertIsNone(result["receipt"]["targets"][0]["accepted_sha256"])
                self.inspect(inputs, result, files)
                if case == "extra-first":
                    self.assertEqual(len(files["objects/vpatient_params.csv"]), 17783)

    def test_slow_header_body_and_connect_deadlines_preserve_bounded_prefix(self):
        for case in ("slow-headers", "slow-body", "stall-connect"):
            start = time.monotonic()
            inputs, result, files = self.run_case(case)
            self.assertLess(time.monotonic() - start, 3)
            self.assertEqual(result["status"], "incomplete")
            self.assertEqual(result["receipt"]["targets"][0]["error"], "request-deadline")
            self.assertLessEqual(
                sum(len(raw) for name, raw in files.items() if name.startswith("objects/")), 17783
            )
            self.inspect(inputs, result, files)
            if case == "slow-body":
                # The whole request clock includes cold child startup. A deadline
                # can precede its first byte; preserve exactly the prefix returned.
                prefix = files.get("objects/vpatient_params.csv", b"")
                self.assertEqual(len(prefix), result["receipt"]["targets"][0]["actual_bytes"])
                self.assertLess(len(prefix), collector.SIZES[0])

    def test_outer_storage_deadline_recovers_published_body_once_without_late_success(self):
        start = time.monotonic()
        inputs, result, files = self.run_case("stall-storage")
        self.assertLess(time.monotonic() - start, 4)
        self.assertEqual(result["status"], "incomplete")
        self.assertEqual(result["acquisition_error"], "whole-deadline")
        self.assertEqual(files["objects/vpatient_params.csv"], collector.BODIES[0])
        self.assertNotIn("intake-receipt.private.json", files)
        self.assertEqual(self.inspect(inputs, result, files)["status"], "incomplete")
        self.assertEqual(
            [name for name in files if name.endswith("vpatient_params.csv")],
            ["objects/vpatient_params.csv"],
        )

    def test_outer_deadline_stops_inherited_request_leaf(self):
        inputs, result, files = self.run_case("outer-deadline")
        self.assertEqual(result["status"], "incomplete")
        self.assertEqual(result.get("acquisition_error"), "whole-deadline")
        self.inspect(inputs, result, files)
        launches = [
            item for item in result["acquisition_progress"] if item["phase"] == "request-launched"
        ]
        self.assertEqual(len(launches), 1)
        if os.name != "nt":
            self.assertEqual(launches[0]["owner_group"], launches[0]["leaf_group"])
            self.assertEqual(
                launches[0]["owner_group"], result["acquisition_process"]["controller_pid"]
            )
            for _ in range(50):
                try:
                    os.kill(launches[0]["pid"], 0)
                except ProcessLookupError:
                    break
                time.sleep(0.01)
            else:
                self.fail("owned fixed request leaf remained after outer timeout")

    def test_closed_facade_and_invented_grant_refuse_before_path_source_or_spawn(self):
        class Poison:
            def __fspath__(self):
                raise AssertionError("path touched")

        with (
            patch.object(collector, "_identity", side_effect=AssertionError("source read")),
            self.assertRaises(PermissionError),
        ):
            collector.run_intake(Poison(), grant=Poison())
        plan, approval, notice, origin = collector.fixture_inputs(self.root / "never")
        with (
            patch.object(collector, "_supervise", side_effect=AssertionError("spawn")),
            self.assertRaises(ValueError),
        ):
            collector.collect_approved(
                plan, digest(plan), approval, digest(approval), notice, origin, digest(origin)
            )
        self.assertFalse((self.root / "never").exists())

    def test_strict_fixture_and_plan_scope_authority_source_retention_before_spawn(self):
        for changed in (
            {"url": "https://never.invalid"},
            {"command": "false"},
            {"path": "/never"},
            {"case": "actual"},
        ):
            value = decode(self.request()) | changed
            with (
                patch.object(
                    collector, "fixture_inputs", side_effect=AssertionError("destination touched")
                ),
                self.assertRaises(ValueError),
            ):
                collector.run_fixture_collector(encode(value), self.root / "never")
        inputs = collector.fixture_inputs(self.root / "never")
        plan, approval, notice, origin = map(decode, (inputs[0], inputs[1], encode({}), inputs[3]))
        cases = []
        bad = copy.deepcopy(plan)
        bad["targets"][0]["url"] += "?x=1"
        cases.append((bad, approval, origin))
        bad = copy.deepcopy(plan)
        bad["limits"]["body_bytes"] = 18165
        cases.append((bad, approval, origin))
        bad = copy.deepcopy(plan)
        bad["source_identity"] = {}
        cases.append((bad, approval, origin))
        bad = copy.deepcopy(approval)
        bad["authority"]["setup_authorized"] = True
        cases.append((plan, bad, origin))
        bad = copy.deepcopy(origin)
        bad["unknown_required_origins"] = ["notice-copy"]
        cases.append((plan, approval, bad))
        for p, a, o in cases:
            p, a, o = copy.deepcopy(p), copy.deepcopy(a), copy.deepcopy(o)
            o_raw = encode(o)
            p["origin_context_sha256"] = digest(o_raw)
            p_raw = encode(p)
            a.update(plan_sha256=digest(p_raw), origin_context_sha256=digest(o_raw))
            a_raw = encode(a)
            with self.assertRaises(ValueError):
                collector._gate(
                    p_raw,
                    digest(p_raw),
                    a_raw,
                    digest(a_raw),
                    inputs[2],
                    o_raw,
                    digest(o_raw),
                    True,
                )

    def test_fresh_root_replay_symlink_escape_and_exclusive_modes(self):
        inputs, _result, files = self.run_case()
        before = dict(files)
        result = collector._collect(
            inputs[0],
            digest(inputs[0]),
            inputs[1],
            digest(inputs[1]),
            inputs[2],
            inputs[3],
            digest(inputs[3]),
            "ok",
        )
        self.assertIsNone(result["receipt_sha256"])
        self.assertEqual(collector.read_intake_fixture(self.root / "ok"), before)
        self.assertEqual((self.root / "ok").stat().st_mode & 0o777, 0o700)
        self.assertTrue(
            all(
                path.stat().st_mode & 0o777 == 0o600
                for path in (self.root / "ok").rglob("*")
                if path.is_file()
            )
        )
        (self.root / "alias").symlink_to(self.root / "ok", target_is_directory=True)
        with self.assertRaises(OSError):
            collector.read_intake_fixture(self.root / "alias")
        with self.assertRaises(ValueError):
            collector._directory(self.root / ".." / "escape")

    def test_mode_alias_fifo_and_unknown_loader_names_rejected(self):
        root = self.root / "bad"
        root.mkdir(mode=0o700)
        (root / "objects").mkdir(mode=0o700)
        (root / "notices").mkdir(mode=0o700)
        fd = os.open(
            root / "objects" / collector.NAMES[0], os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o644
        )
        os.write(fd, b"invented")
        os.close(fd)
        with self.assertRaisesRegex(ValueError, "mode-owner-links"):
            collector.read_intake_fixture(root)
        if hasattr(os, "mkfifo"):
            fifo = self.root / "fifo"
            fifo.mkdir(mode=0o700)
            (fifo / "objects").mkdir(mode=0o700)
            (fifo / "notices").mkdir(mode=0o700)
            os.mkfifo(fifo / "objects" / collector.NAMES[0], 0o600)
            start = time.monotonic()
            with self.assertRaises(ValueError):
                collector.read_intake_fixture(fifo)
            self.assertLess(time.monotonic() - start, 0.5)

    def test_rehashed_headers_process_error_and_completion_forgeries_rejected(self):
        inputs, result, files = self.run_case()
        original = decode(files["intake-receipt.private.json"])
        for section, key, value in (
            ("headers", "content_length", 0),
            ("headers", "content_encoding", "gzip"),
            ("process", "elapsed_ns", 10**12),
            ("process", "pid", -1),
        ):
            changed = copy.deepcopy(original)
            changed["targets"][0][section][key] = value
            raw = encode(changed)
            candidate = files | {"intake-receipt.private.json": raw}
            with self.subTest(key=key), self.assertRaises(ValueError):
                self.inspect(inputs, result | {"receipt_sha256": digest(raw)}, candidate)
        for key, value in (
            ("error", "whole-deadline"),
            ("controller_elapsed_ns", 91_000_000_000),
            ("nonce_sha256", "0" * 64),
            ("source_identity_after", {}),
        ):
            changed = original | {key: value}
            raw = encode(changed)
            with self.subTest(key=key), self.assertRaises(ValueError):
                self.inspect(
                    inputs,
                    result | {"receipt_sha256": digest(raw)},
                    files | {"intake-receipt.private.json": raw},
                )

    def test_header_parser_rejects_raw_syntax_and_unframed_sentinel(self):
        for header in (
            b"HTTP/1.1 200 OK\r\nContent-Length: 17782\r\nContent-Length: 17782\r\n\r\n",
            b"HTTP/1.1 200 OK\r\nContent-Length : 17782\r\n\r\n",
            b"HTTP/1.1 200 OK\r\n Folded: value\r\n\r\n",
            b"HTTP/1.1 200 OK\r\nTransfer-Encoding: identity\r\n\r\n",
            b"HTTP/1.1 200 OK\r\nX: a\tb\r\n\r\n",
        ):
            with self.assertRaises(ValueError):
                collector._headers(header, 17782)
        raw = b"HTTP/1.1 200 OK\r\nContent-Length: 17782\r\n\r\n" + collector.BODIES[0] + b"!"
        sock = Mock()
        stream = io.BytesIO(raw)
        sock.recv.side_effect = stream.read
        frames = []
        with (
            patch.object(collector, "_open_https", return_value=sock),
            patch.object(collector, "_emit", side_effect=frames.append),
        ):
            collector._fetch(0, None)
        body = b"".join(
            base64.b64decode(frame["bytes_b64"]) for frame in frames if frame["phase"] == "body"
        )
        self.assertEqual(len(body), 17783)
        sock.close.assert_called_once()

    def test_actual_tls_adapter_uses_verified_fixed_host_and_no_ambient_environment(self):
        context, plain, tls = Mock(), Mock(), Mock()
        context.verify_mode, context.check_hostname = ssl.CERT_REQUIRED, True
        context.wrap_socket.return_value = tls
        with (
            patch.object(collector.ssl, "create_default_context", return_value=context),
            patch.object(collector.socket, "create_connection", return_value=plain) as connect,
        ):
            self.assertIs(collector._open_https(), tls)
        connect.assert_called_once_with((collector.HOST, 443), timeout=30)
        context.wrap_socket.assert_called_once_with(plain, server_hostname=collector.HOST)
        self.assertIsNone(context.keylog_filename)
        self.assertEqual(set(collector._environment()), {"PATH", "LANG", "LC_ALL"})

    def test_fixture_child_audit_guard_denies_accidental_real_socket_branch(self):
        script = collector._script(
            "_fixture_fetch; import experiments.simglucose_audit.intake_collector "
            "as c; c._FixtureSocket=lambda *a:c.socket.create_connection((c.HOST,443),"
            "timeout=30); _fixture_fetch(0, "
            "'ok')"
        )
        result = subprocess.run(
            [sys.executable, "-I", "-S", "-B", "-c", script],
            capture_output=True,
            cwd=collector.ROOT,
            env=collector._environment(),
            timeout=3,
            check=False,
        )
        self.assertEqual(result.returncode, 0)
        self.assertEqual(decode(result.stdout)["phase"], "error")
        self.assertNotIn(b"bytes_b64", result.stdout)

    def test_cleanup_failure_refuses_recovery_and_keeps_primary(self):
        inputs = collector.fixture_inputs(self.root / "never")
        failed = {
            "kind": "invented",
            "status": "incomplete",
            "receipt_sha256": None,
            "owned_cleanup_error": "owned-tree-remains",
            "error": "whole-deadline",
            "_acquired": {0: b"A"},
        }
        with patch.object(collector, "_supervise", return_value=failed) as supervise:
            result = collector._collect(
                inputs[0],
                digest(inputs[0]),
                inputs[1],
                digest(inputs[1]),
                inputs[2],
                inputs[3],
                digest(inputs[3]),
                "ok",
            )
        supervise.assert_called_once()
        self.assertEqual(result["owned_cleanup_error"], "owned-tree-remains")
        self.assertEqual(result["error"], "whole-deadline")
        self.assertNotIn("_acquired", result)
        self.assertFalse((self.root / "never").exists())

    def test_postspawn_notification_error_stops_and_reaps_exact_leaf(self):
        processes = []
        popen = collector.subprocess.Popen

        def capture(*args, **kwargs):
            process = popen(*args, **kwargs)
            processes.append(process)
            return process

        with (
            patch.object(collector.subprocess, "Popen", side_effect=capture),
            patch.object(collector, "_emit", side_effect=OSError("invented broken notification")),
        ):
            _body, _headers, error, observed = collector._one_request(
                0, "stall-connect", time.monotonic() + 1, 1
            )
        self.assertEqual(error, "invalid-response-protocol")
        self.assertIsNotNone(processes[0].poll())
        self.assertEqual(observed["pid"], processes[0].pid)
        self.assertIsNone(observed["cleanup_error"])

    def test_historical_grant_cold_read_and_current_retention_are_distinct(self):
        destination = self.root / "historical"
        p_raw, a_raw, notice, o_raw = collector.fixture_inputs(destination)
        plan, approval, origin = decode(p_raw), decode(a_raw), decode(o_raw)
        later = fixture_time.FIXTURE_UTC + timedelta(hours=2)
        for row in origin["records"]:
            row["deadline_utc"] = collector._stamp(later)
        o_raw = encode(origin)
        plan["origin_context_sha256"] = digest(o_raw)
        p_raw = encode(plan)
        approval.update(plan_sha256=digest(p_raw), origin_context_sha256=digest(o_raw))
        a_raw = encode(approval)
        inputs = p_raw, a_raw, notice, o_raw
        result = collector._collect(
            p_raw, digest(p_raw), a_raw, digest(a_raw), notice, o_raw, digest(o_raw), "ok"
        )
        files = collector.read_intake_fixture(destination)
        with patch.object(
            collector,
            "_now",
            return_value=collector._utc(approval["expires_utc"]) + timedelta(seconds=1),
        ):
            self.assertEqual(self.inspect(inputs, result, files)["status"], "completed")
        with (
            patch.object(collector, "_now", return_value=later + timedelta(seconds=1)),
            self.assertRaisesRegex(ValueError, "retention"),
        ):
            self.inspect(inputs, result, files)

    def test_short_approval_refused_before_any_path_or_process(self):
        p_raw, a_raw, notice, o_raw = collector.fixture_inputs(self.root / "never")
        approval = decode(a_raw)
        approval["expires_utc"] = collector._stamp(fixture_time.FIXTURE_UTC + timedelta(seconds=20))
        a_raw = encode(approval)
        with (
            patch.object(collector, "_supervise", side_effect=AssertionError("spawn")),
            self.assertRaisesRegex(ValueError, "headroom"),
        ):
            collector._collect(
                p_raw, digest(p_raw), a_raw, digest(a_raw), notice, o_raw, digest(o_raw), "ok"
            )
        self.assertFalse((self.root / "never").exists())

    def test_cold_reader_does_not_connect_or_signal_saved_pids(self):
        inputs, result, files = self.run_case()
        with (
            patch.object(socket, "create_connection", side_effect=AssertionError("network")),
            patch.object(
                collector.platform_process, "force_tree", side_effect=AssertionError("saved PID")
            ),
        ):
            self.assertEqual(self.inspect(inputs, result, files)["status"], "completed")


if __name__ == "__main__":
    unittest.main()
