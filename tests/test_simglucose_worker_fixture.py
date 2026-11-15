"""Invented worker transport, owned stop and cold readback; no native execution."""

import builtins
import copy
import io
import threading
import time
import unittest
from unittest.mock import Mock, patch

from experiments.simglucose_audit import bootstrap
from experiments.simglucose_audit import worker_fixture as worker
from experiments.simglucose_audit.contract import decode, digest, encode


class SimglucoseWorkerFixtureTests(unittest.TestCase):
    def request(self, mode="complete", **config):
        request = worker.default_request()
        request["mode"] = mode
        request["config"].update(config)
        return encode(request)

    def inspect(self, report, raw):
        report_raw = encode(report)
        return worker.inspect_worker_fixture(report_raw, digest(report_raw), raw, digest(raw))

    def run_request(self, raw):
        report = worker.run_worker_fixture(raw)
        self.inspect(report, raw)
        return report

    def test_fresh_real_fixed_children_repeat_and_close(self):
        raw = self.request()
        first, second = self.run_request(raw), self.run_request(raw)
        self.assertEqual(first, second)
        self.assertEqual(first["status"], "completed")
        self.assertEqual(first["frames_received"], ["ready", "result", "finished"])
        self.assertTrue(first["owned_stop_observed"])
        self.assertIsNone(first["cleanup_error"])
        fixture = first["fixture_report"]
        self.assertEqual(len(fixture["rows"]), 10)
        self.assertEqual(fixture["calls"]["reset"], 1)
        self.assertEqual(fixture["calls"]["close"], 1)
        self.assertEqual(fixture["delivered_u_exact"], {"numerator": "309", "denominator": "500"})
        self.assertFalse(first["host_or_process_qualified"])
        self.assertFalse(first["authority"]["native_execution_authorized"])

    def test_real_cancel_and_deadline_preserve_pending_prefix_and_owned_stop(self):
        for mode, error, status in (
            ("cancel", "fixture-cancelled", "interrupted"),
            ("deadline", "fixture-deadline", "incomplete"),
        ):
            with self.subTest(mode=mode):
                report = self.run_request(self.request(mode))
                self.assertEqual((report["primary_error"], report["status"]), (error, status))
                self.assertEqual(report["frames_received"], ["ready", "result"])
                self.assertTrue(report["owned_stop_observed"])
                fixture = report["fixture_report"]
                self.assertEqual(len(fixture["rows"]), 2)
                self.assertIsNotNone(fixture["pending_command"])
                self.assertEqual(fixture["calls"]["step"], 3)
                self.assertEqual(fixture["calls"]["close"], 1)
                self.assertEqual(
                    fixture["delivered_u_exact"],
                    {"numerator": "57", "denominator": "500"},
                )

    def test_invented_denial_events_never_claim_host_enforcement(self):
        for resource in ("network", "subprocess", "system-font"):
            report = self.run_request(self.request("deny-" + resource))
            self.assertEqual(report["primary_error"], "invented-permission-denied:" + resource)
            self.assertEqual(report["status"], "failed")
            self.assertIsNone(report["fixture_report"])
            self.assertFalse(report["host_or_process_qualified"])

    def test_nested_reset_failure_and_cleanup_error_are_preserved(self):
        report = self.run_request(self.request(fault="reset-error", close_error=True))
        fixture = report["fixture_report"]
        self.assertEqual(report["status"], "failed")
        self.assertEqual(fixture["primary_error"], "scripted-reset-error")
        self.assertEqual(fixture["diagnostic_error"], "scripted-close-error")
        self.assertEqual(fixture["rows"], [])
        self.assertIsNone(fixture["delivered_u_exact"])

    def test_transport_cleanup_failure_does_not_replace_primary_or_complete(self):
        stop = worker._stop

        def failed_cleanup(process):
            self.assertIsNone(stop(process))
            return "owned-stop-failed"

        raw = self.request("cancel")
        with patch.object(worker, "_stop", side_effect=failed_cleanup):
            report = worker.run_worker_fixture(raw)
        self.assertEqual(report["primary_error"], "fixture-cancelled")
        self.assertEqual(report["cleanup_error"], "owned-stop-failed")
        self.assertEqual(report["status"], "failed")
        self.assertFalse(report["owned_stop_observed"])
        self.inspect(report, raw)

    def test_strict_input_before_identity_or_spawn(self):
        invalid = [
            b"{}",
            b'{"schema":1,"schema":2}',
            b'{"x":NaN}',
            b"x" * (worker.MAX_BYTES + 1),
        ]
        for field, value in (
            ("module", "invented.module"),
            ("path", "/never/open"),
            ("factory", "blocked"),
        ):
            invalid.append(encode(worker.default_request() | {field: value}))
        for change in ({"kind": "native"}, {"mode": True}, {"mode": "native"}):
            invalid.append(encode(worker.default_request() | change))
        invalid.append(self.request(basal_u_h=True))
        invalid.append(self.request("cancel", fault="reset-error"))
        with (
            patch.object(worker, "_identity", side_effect=AssertionError("source read")),
            patch.object(worker.platform_process, "spawn", side_effect=AssertionError("spawn")),
        ):
            for raw in invalid:
                with self.subTest(raw=raw[:90]), self.assertRaises(ValueError):
                    worker.run_worker_fixture(raw)

    def test_launch_refusal_is_failed_and_has_no_cleanup_or_fixture(self):
        raw = self.request()
        with patch.object(
            worker.platform_process, "spawn", side_effect=PermissionError("invented")
        ):
            report = worker.run_worker_fixture(raw)
        self.assertEqual(report["primary_error"], "worker-launch-refused")
        self.assertFalse(report["owned_stop_observed"])
        self.assertEqual(report["frames_received"], [])
        self.inspect(report, raw)

    def fake_report(self, raw, lines):
        class Process:
            stdin = io.BytesIO()
            stdout = io.BytesIO(lines)
            returncode = 0

            def wait(self, timeout):
                return 0

        with (
            patch.object(worker.platform_process, "spawn", return_value=Process()),
            patch.object(worker, "_stop", return_value=None),
        ):
            report = worker.run_worker_fixture(raw)
        self.inspect(report, raw)
        return report

    def frames(self, raw):
        identity = worker._identity()
        request = decode(raw)
        return [
            {
                "phase": "ready",
                "request_sha256": digest(raw),
                "source_identity": identity,
            },
            worker._expected_result(request, identity),
            {"phase": "finished"},
        ]

    def test_truncated_duplicate_nonfinite_and_extra_frames_refuse_completion(self):
        raw = self.request()
        ready, result, finished = map(encode, self.frames(raw))
        for output, primary in (
            (ready + b"\n", "incomplete-worker-protocol"),
            (ready + b"\n" + result + b"\n", "incomplete-worker-protocol"),
            (ready + b"\n" + ready + b"\n", "worker-protocol-mismatch"),
            (b'{"phase":"ready","phase":"ready"}\n', "invalid-worker-frame"),
            (b'{"x":NaN}\n', "invalid-worker-frame"),
            (b"x" * (worker.MAX_BYTES + 1), "bounded-worker-frame"),
            (
                ready + b"\n" + result + b"\n" + finished + b"\n" + finished + b"\n",
                "worker-protocol-mismatch",
            ),
        ):
            with self.subTest(primary=primary):
                report = self.fake_report(raw, output)
                self.assertEqual(report["primary_error"], primary)
                self.assertEqual(report["status"], "failed")
        partial = self.fake_report(raw, ready + b"\n" + result + b"\n")
        self.assertEqual(len(partial["fixture_report"]["rows"]), 10)
        self.assertEqual(partial["status"], "failed")

    def test_rehashed_wrong_source_and_result_do_not_enter_prefix(self):
        raw = self.request()
        frames = self.frames(raw)
        frames[1]["fixture"]["rows"][0]["basal_u_min"] = 1.2
        report = self.fake_report(raw, b"\n".join(map(encode, frames)) + b"\n")
        self.assertEqual(report["frames_received"], ["ready"])
        self.assertIsNone(report["fixture_report"])
        self.assertEqual(report["primary_error"], "worker-protocol-mismatch")

    def test_cold_readback_rejects_rehashed_forgery_and_external_pin_drift(self):
        raw = self.request()
        original = self.run_request(raw)
        for field, value in (
            ("authority", original["authority"] | {"setup_authorized": True}),
            ("host_or_process_qualified", True),
            ("request_sha256", "0" * 64),
            ("source_identity", {}),
            ("process_owner_source_identity", {}),
            ("extra", False),
        ):
            report = copy.deepcopy(original)
            report[field] = value
            with self.subTest(field=field), self.assertRaises(ValueError):
                self.inspect(report, raw)
        altered = copy.deepcopy(original)
        altered["fixture_report"]["rows"][0]["bolus_u_min"] = 1
        with self.assertRaisesRegex(ValueError, "oracle"):
            self.inspect(altered, raw)
        with self.assertRaisesRegex(ValueError, "byte-pins"):
            worker.inspect_worker_fixture(encode(original), "0" * 64, raw, digest(raw))
        partial_raw = self.request("cancel")
        partial = self.run_request(partial_raw)
        partial["status"] = "completed"
        with self.assertRaises(ValueError):
            self.inspect(partial, partial_raw)

    def test_readback_no_consumer_child_or_native_import(self):
        raw = self.request()
        report = self.run_request(raw)
        real_import = builtins.__import__

        def guard(name, *args, **kwargs):
            if name.split(".")[0] in {
                "simglucose",
                "gym",
                "numpy",
                "matplotlib",
                "pkg_resources",
            }:
                raise AssertionError("selected dependency import")
            return real_import(name, *args, **kwargs)

        with (
            patch("builtins.__import__", side_effect=guard),
            patch.object(bootstrap, "run_fixture", side_effect=AssertionError("engine")),
            patch.object(worker.platform_process, "spawn", side_effect=AssertionError("child")),
        ):
            self.inspect(report, raw)
            host = worker.default_host_preconditions()
            host["requirements"] = dict.fromkeys(worker.HOST_REQUIREMENTS, "invented-pass")
            checked = worker.inspect_host_preconditions(encode(host))
        self.assertEqual(checked["status"], "blocked")
        self.assertFalse(checked["actual_host_probe_performed"])
        self.assertFalse(checked["host_or_process_qualified"])

    def test_host_preconditions_never_admit_real_or_incomplete_claims(self):
        host = worker.default_host_preconditions()
        self.assertEqual(worker.inspect_host_preconditions(encode(host))["status"], "blocked")
        for changed in (
            host | {"kind": "actual"},
            host | {"authority": {}},
            host | {"requirements": {}},
            host | {"requirements": dict.fromkeys(worker.HOST_REQUIREMENTS, True)},
            host | {"requirements": dict.fromkeys(worker.HOST_REQUIREMENTS, "qualified")},
        ):
            with self.assertRaises(ValueError):
                worker.inspect_host_preconditions(encode(changed))

    def test_source_drift_after_child_result_cannot_remain_completed(self):
        raw = self.request()
        identity = worker._identity()
        with patch.object(
            worker, "_identity", side_effect=[identity, identity | {"drift": "invented"}]
        ):
            report = worker.run_worker_fixture(raw)
        self.assertEqual(report["primary_error"], "worker-source-changed")
        self.assertEqual(report["status"], "failed")
        self.inspect(report, raw)
        owner = worker._owner_identity()
        with patch.object(
            worker, "_owner_identity", side_effect=[owner, owner | {"drift": "invented"}]
        ):
            report = worker.run_worker_fixture(raw)
        self.assertEqual(report["primary_error"], "worker-source-changed")
        self.assertEqual(report["status"], "failed")
        self.inspect(report, raw)

    def test_exact_request_bytes_bind_even_equivalent_json(self):
        raw = self.request()
        report = self.run_request(raw)
        same_data = b" " + raw
        self.assertEqual(decode(raw), decode(same_data))
        with self.assertRaisesRegex(ValueError, "binding"):
            self.inspect(report, same_data)

    def test_large_legal_input_backpressure_is_inside_whole_deadline(self):
        raw = self.request("stall-before-read")
        raw += b" " * (worker.MAX_BYTES - len(raw))
        self.assertEqual(len(raw), worker.MAX_BYTES)
        # The fixed child sleeps before reading. This valid request exceeds the
        # pipe capacity, so a synchronous parent write would miss this deadline.
        processes = []
        spawn = worker.platform_process.spawn

        def record_spawn(*args, **kwargs):
            process = spawn(*args, **kwargs)
            processes.append(process)
            return process

        start = time.monotonic()
        with (
            patch.object(worker, "BUDGET_SECONDS", 0.15),
            patch.object(worker.platform_process, "spawn", side_effect=record_spawn),
        ):
            report = worker.run_worker_fixture(raw)
        elapsed = time.monotonic() - start
        self.assertLess(elapsed, 2.5)
        self.assertEqual(report["primary_error"], "worker-deadline")
        self.assertEqual(report["status"], "incomplete")
        self.assertEqual(report["frames_received"], [])
        self.assertTrue(report["owned_stop_observed"])
        self.assertIsNotNone(processes[0].poll())
        self.assertTrue(processes[0].stdin.closed)
        self.assertTrue(processes[0].stdout.closed)
        self.assertFalse(
            any(
                thread.name in ("simglucose-fixture-input", "simglucose-fixture-output")
                for thread in threading.enumerate()
            )
        )
        self.inspect(report, raw)

    def test_exited_child_is_never_signalled_or_remaining_group_adopted(self):
        process = Mock()
        process.poll.return_value = 0
        with (
            patch.object(
                worker.platform_process,
                "force_tree",
                side_effect=AssertionError("old PID signalled"),
            ),
            patch.object(worker.platform_process, "tree_exists", return_value=False),
            patch.object(worker.platform_process, "close_tree") as close,
        ):
            self.assertIsNone(worker._stop(process))
            close.assert_called_once_with(process)
        process.wait.assert_not_called()
        with (
            patch.object(
                worker.platform_process,
                "force_tree",
                side_effect=AssertionError("old PID signalled"),
            ),
            patch.object(worker.platform_process, "tree_exists", return_value=True),
            patch.object(
                worker.platform_process,
                "close_tree",
                side_effect=AssertionError("unexpected group adopted"),
            ),
        ):
            self.assertEqual(worker._stop(process), "owned-tree-remains")

    def test_finished_frame_and_full_journal_do_not_replace_process_exit(self):
        raw = self.request("finish-block")
        report = self.run_request(raw)
        self.assertEqual(report["frames_received"], ["ready", "result", "finished"])
        self.assertEqual(len(report["fixture_report"]["rows"]), 10)
        self.assertEqual(report["fixture_report"]["status"], "completed")
        self.assertEqual(report["primary_error"], "fixture-finish-deadline")
        self.assertEqual(report["status"], "incomplete")
        self.assertTrue(report["owned_stop_observed"])
        promoted = copy.deepcopy(report)
        promoted.update(primary_error=None, status="completed")
        with self.assertRaisesRegex(ValueError, "terminal-status"):
            self.inspect(promoted, raw)
        promoted.update(frames_received=[], fixture_report=None)
        with self.assertRaisesRegex(ValueError, "terminal-status"):
            self.inspect(promoted, raw)

    def test_production_native_entry_remains_unconditional(self):
        class Poison:
            def __bytes__(self):
                raise AssertionError("input touched")

        with (
            patch.object(worker, "_identity", side_effect=AssertionError("source read")),
            patch.object(worker.platform_process, "spawn", side_effect=AssertionError("spawn")),
            self.assertRaises(PermissionError),
        ):
            bootstrap.run_native(Poison(), source=Poison(), factory=Poison())


if __name__ == "__main__":
    unittest.main()
