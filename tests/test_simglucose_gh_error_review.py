"""Invented material only; no retained report/diagnostic or verifier execution."""

import copy
import os
import stat
import tempfile
import threading
import time
import unittest
from datetime import timedelta
from pathlib import Path
from unittest import mock

from experiments.simglucose_audit import fixture_time
from experiments.simglucose_audit import gh_error_review as g


class ErrorReviewTests(unittest.TestCase):
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

    def fixture(self, **kwargs):
        p = Path(
            tempfile.mkdtemp(prefix="error-invented-", dir=os.environ.get("OT062_FIXTURE_ROOT"))
        ).resolve()
        return p, g.fixture_inputs(p, **kwargs)

    def prepared(self, **kwargs):
        p, inputs = self.fixture(**kwargs)
        result = g.run_fixture_review(inputs)
        self.assertEqual(result["review_receipt"]["status"], "prepared")
        return p, inputs, result

    def test_closed_before_arguments(self):
        class Trap:
            def __getattribute__(self, name):
                raise AssertionError("argument touched")

        with self.assertRaises(PermissionError):
            g.run_review(Trap())

    def test_single_container_and_view_only_receipt_file(self):
        raw = b"INVENTED diagnostic \\x41\r\n\x1b\xff"
        p, inputs, result = self.prepared(stderr=raw)
        self.assertEqual(g.reverse_ascii(result["review"]["escaped_ascii"]), raw)
        self.assertFalse(result["review_receipt"]["downstream_display_confirmed"])
        self.assertTrue(result["review"]["untrusted_data"])
        self.assertEqual(result["review_receipt"]["input_passes"], 1)
        root = p / "invented-error-review"
        self.assertEqual(set(q.name for q in root.iterdir()), {"receipt.private.json"})
        receipt = (root / "receipt.private.json").read_bytes()
        self.assertEqual(g.digest(receipt), g.digest(g.encode(result["review_receipt"])))
        self.assertNotIn(b"escaped_ascii", receipt)
        self.assertNotIn(b"raw_base64", receipt)
        self.assertNotIn(raw, receipt)
        self.assertEqual(stat.S_IMODE(root.stat().st_mode), 0o700)
        self.assertEqual(stat.S_IMODE((root / "receipt.private.json").stat().st_mode), 0o600)
        self.assertLessEqual(len(g.encode(result)) + 1, g.ENVELOPE_CAP)

    def test_all_bytes_roundtrip_and_max_generic_view(self):
        raw = bytes(range(256)) * 8
        self.assertEqual(g.reverse_ascii(g.escape_ascii(raw)), raw)
        _, _, result = self.prepared(stderr=raw)
        self.assertEqual(g.reverse_ascii(result["review"]["escaped_ascii"]), raw)
        self.assertLessEqual(len(g.encode(result)) + 1, g.ENVELOPE_CAP)
        _, _, result = self.prepared(stderr=b"\x00" * g.STDERR_CAP)
        self.assertLessEqual(len(g.encode(result)) + 1, g.ENVELOPE_CAP)

    def test_noncanonical_escape_forms_refused(self):
        for text in ("\\x41", "\\x5c", "\\xFF", "\\x0A", "\\x0", "\\", "é", "\n", "\\q"):
            with self.subTest(text=repr(text)), self.assertRaises(ValueError):
                g.reverse_ascii(text)
        self.assertEqual(g.reverse_ascii("\\\\x41"), b"\\x41")

    def test_rehashed_private_view_promotions_refused_without_file_IO(self):
        _, inputs, result = self.prepared()
        plan = g.decode(inputs[0])
        grant = g.decode(inputs[1])
        issued = g.core._utc(grant["issued_utc"])
        expiry = g.core._utc(grant["expires_utc"])
        mutations = [
            lambda x: x["review"].update(escaped_ascii="forged"),
            lambda x: x["review"].update(untrusted_data=False),
            lambda x: x["review"].update(decoded_bytes=True),
            lambda x: x["review_receipt"].update(downstream_display_confirmed=True),
            lambda x: x["review_receipt"].update(input_passes=True),
            lambda x: x["review_receipt"].update(metadata_receipt_readback_passes=1),
            lambda x: x["review_receipt"].update(ended_utc="2099-01-01T00:00:00Z"),
            lambda x: x["review_receipt"].update(escaped_ascii="material"),
        ]
        for mutate in mutations:
            changed = copy.deepcopy(result)
            mutate(changed)
            with (
                mock.patch.object(g.os, "open", side_effect=AssertionError("pure validation IO")),
                self.assertRaises(ValueError),
            ):
                g.validate_review_result(changed, plan, inputs[3], issued, expiry, True)

    def test_all_wrong_container_forms_fail_before_view(self):
        for kind in (
            "extra-field",
            "extra-row",
            "stdout",
            "wrong-b64",
            "wrong-kind",
            "duplicate",
            "trailing",
            "wrong-row",
            "fixture-kind",
            "noncanonical-b64",
            "numeric-type",
            "utf16",
        ):
            with self.subTest(kind=kind):
                p, inputs = self.fixture(mutate_report=kind)
                with self.assertRaises(ValueError):
                    g.run_fixture_review(inputs)
                self.assertFalse((p / "invented-error-review").exists())

    def test_minted_fixture_registry_no_rehashed_selector(self):
        _, inputs = self.fixture()
        plan, approval, origin, held = inputs
        changed = g.decode(plan)
        changed["qualification_sha256"] = "0" * 64
        raw = g.encode(changed)
        grant = g.decode(approval)
        grant["plan_sha256"] = g.digest(raw)
        gr = g.encode(grant)
        forged = (
            raw,
            gr,
            origin,
            held | {"plan_sha256": g.digest(raw), "approval_sha256": g.digest(gr)},
        )
        with (
            mock.patch.object(g.os, "open", side_effect=AssertionError("unowned fixture open")),
            self.assertRaises(ValueError),
        ):
            g.run_fixture_review(forged)
        held["rights_basis_sha256"] = "0" * 64
        with self.assertRaises(ValueError):
            g.run_fixture_review(inputs)

    def test_fresh_empty_private_fixture_parent(self):
        p = Path(
            tempfile.mkdtemp(prefix="nonempty-", dir=os.environ.get("OT062_FIXTURE_ROOT"))
        ).resolve()
        (p / "preserved").write_bytes(b"invented")
        with self.assertRaises(ValueError):
            g.fixture_inputs(p)
        self.assertFalse((p / "invented-container.json").exists())

    def test_actual_entry_rejects_self_minted_fixture_approval(self):
        _, inputs = self.fixture()
        with (
            mock.patch.object(g.os, "open", side_effect=AssertionError("actual path")),
            self.assertRaises(ValueError),
        ):
            g.review_approved(*inputs)

    def test_consumed_marker_before_source_and_replay_after_rootrename(self):
        p, inputs, result = self.prepared()
        root = p / "invented-error-review"
        root.rename(p / "retained-old")
        with self.assertRaises(ValueError):
            g.run_fixture_review(inputs)
        self.assertFalse(root.exists())
        p, inputs = self.fixture()
        source = p / "invented-container.json"
        source.write_bytes(b"X" * source.stat().st_size)
        with self.assertRaises(ValueError):
            g.run_fixture_review(inputs)
        self.assertTrue(any(q.name.startswith(".gh-error-consumed-") for q in p.iterdir()))

    def test_dangling_output_refuses_before_worker(self):
        p, inputs = self.fixture()
        (p / "invented-error-review").symlink_to(p / "absent")
        with (
            mock.patch.object(g, "_supervise", side_effect=AssertionError("worker before ABSENT")),
            self.assertRaises(ValueError),
        ):
            g.run_fixture_review(inputs)

    def test_symlink_FIFO_hardlink_and_wrongmode_refused(self):
        for kind in ("symlink", "fifo", "hardlink", "mode"):
            p, inputs = self.fixture()
            source = p / "invented-container.json"
            if kind == "mode":
                source.chmod(0o644)
            else:
                old = p / "retained-invented"
                source.rename(old)
                if kind == "symlink":
                    source.symlink_to(old)
                elif kind == "fifo":
                    os.mkfifo(source, 0o600)
                else:
                    os.link(old, source)
            start = time.monotonic()
            with self.assertRaises(ValueError):
                g.run_fixture_review(inputs)
            self.assertLess(time.monotonic() - start, 1)

    def test_exact_size_overflow_and_hash_failure(self):
        for extra in (b"x", b"", b"xx"):
            p, inputs = self.fixture()
            source = p / "invented-container.json"
            old = source.read_bytes()
            source.write_bytes(old[:-1] + extra)
            with self.assertRaises(ValueError):
                g.run_fixture_review(inputs)

    def test_owned_stage_stalls_IPC_backpressure_and_protocol_failure(self):
        for case in (
            "read-stall",
            "parse-stall",
            "write-stall",
            "fsync-stall",
            "emit-stall",
            "overflow-frame",
            "drip-frame",
            "late-error",
            "nonzero",
            "descendant",
        ):
            with self.subTest(case=case):
                _, inputs = self.fixture()
                start = time.monotonic()
                with self.assertRaises(ValueError):
                    g.run_fixture_review(inputs, case, whole_seconds=0.6)
                self.assertLess(time.monotonic() - start, 2)

    def test_cold_receipt_after_grant_no_container_or_material_reopen(self):
        p, inputs, result = self.prepared()
        original = os.open

        def guarded(path, *args, **kwargs):
            if os.fsdecode(path) == str(p / "invented-container.json"):
                raise AssertionError("cold material open")
            return original(path, *args, **kwargs)

        future = g.core._now() + timedelta(hours=2)
        with (
            mock.patch.object(g.core, "_now", return_value=future),
            mock.patch.object(g.os, "open", guarded),
        ):
            self.assertEqual(
                g.inspect_receipt_metadata(
                    *inputs,
                    held_receipt_sha256=g.digest(g.encode(result["review_receipt"])),
                    fixture=True,
                ),
                result["review_receipt"],
            )
        with (
            mock.patch.object(g.core, "_now", return_value=future + timedelta(days=2)),
            mock.patch.object(g.os, "open", side_effect=AssertionError("expired retention open")),
            self.assertRaises(ValueError),
        ):
            g.inspect_receipt_metadata(
                *inputs,
                held_receipt_sha256=g.digest(g.encode(result["review_receipt"])),
                fixture=True,
            )

    def test_receipt_short_zero_write_and_earliest_expiry(self):
        p = Path(
            tempfile.mkdtemp(prefix="metadata-write-", dir=os.environ.get("OT062_FIXTURE_ROOT"))
        ).resolve()
        directory = g.core._directory(str(p))
        original = os.write
        expiry = g.core._now() + timedelta(seconds=5)
        try:
            with mock.patch.object(g.os, "write", lambda fd, raw: original(fd, raw[:1])):
                g._write_receipt(directory, b'{"invented":true}', expiry, time.monotonic() + 2)
            self.assertEqual((p / "receipt.private.json").read_bytes(), b'{"invented":true}')
        finally:
            os.close(directory)
        p = Path(
            tempfile.mkdtemp(prefix="metadata-zero-", dir=os.environ.get("OT062_FIXTURE_ROOT"))
        ).resolve()
        directory = g.core._directory(str(p))
        try:
            with mock.patch.object(g.os, "write", return_value=0), self.assertRaises(ValueError):
                g._write_receipt(directory, b"{}", expiry, time.monotonic() + 2)
        finally:
            os.close(directory)

    def test_source_snapshot_namespace_and_input_FD_name_binding(self):
        p, inputs = self.fixture()
        plan = g.decode(inputs[0])
        expiry = g.core._now() + timedelta(seconds=5)
        source = p / "invented-container.json"
        fd = os.open(source, os.O_RDONLY)
        try:
            source.rename(p / "preserved")
            source.write_bytes(b"invented")
            with self.assertRaises(ValueError):
                g._input_context(plan, expiry, time.monotonic() + 2, fd)
        finally:
            os.close(fd)
        with (
            mock.patch.object(g.previous, "_identity", return_value={"changed": "invented"}),
            self.assertRaises(ValueError),
        ):
            g._gate(*inputs, True)

    def test_named_parent_replacement_and_expiry_refuse_before_read(self):
        p, inputs = self.fixture()
        plan = g.decode(inputs[0])
        source = p / "invented-container.json"
        fd = os.open(source, os.O_RDONLY)
        expiry = g.core._now() + timedelta(seconds=10)
        try:
            renamed = p.with_name(p.name + "-preserved")
            p.rename(renamed)
            p.mkdir(mode=0o700)
            (p / "invented-container.json").write_bytes(b"invented replacement")
            with (
                mock.patch.object(
                    g.os, "read", side_effect=AssertionError("read after parent drift")
                ),
                self.assertRaises(ValueError),
            ):
                g._input_context(plan, expiry, time.monotonic() + 5, fd)
        finally:
            os.close(fd)
        p, inputs = self.fixture()
        plan = g.decode(inputs[0])
        with (
            mock.patch.object(g.os, "open", side_effect=AssertionError("expired read")),
            self.assertRaises(ValueError),
        ):
            g._read_container(plan, g.core._now() - timedelta(seconds=1), time.monotonic() + 5)

    def test_producer_numeric_types_are_not_python_equal_promotions(self):
        _, inputs = self.fixture()
        plan = g.decode(inputs[0])
        producer = copy.deepcopy(plan["producer_receipt"])
        producer["probes"][0]["consumed_application_bytes"]["stdout"] = False
        with self.assertRaises(ValueError):
            g._producer_metadata(producer, plan["expected_stderr"])
        producer = copy.deepcopy(plan["producer_receipt"])
        producer["probes"][0]["parsed"]["version_matches"] = 0
        with self.assertRaises(ValueError):
            g._producer_metadata(producer, plan["expected_stderr"])

    def test_queue_acquisition_failure_precedes_any_spawn(self):
        with (
            mock.patch.object(g.queue, "Queue", side_effect=MemoryError("invented queue failure")),
            mock.patch.object(
                g.platform_process, "spawn", side_effect=AssertionError("spawn before queue")
            ) as spawn,
            self.assertRaises(MemoryError),
        ):
            g._supervise({"fixture": False}, time.monotonic() + 1)
        spawn.assert_not_called()

    def test_cancellation_closes_owned_worker_and_no_second_result(self):
        _, inputs = self.fixture()
        original = threading.Thread.start

        def start(thread):
            if thread._target == g.previous._send:
                raise KeyboardInterrupt()
            return original(thread)

        with (
            mock.patch.object(g.threading.Thread, "start", start),
            self.assertRaises(KeyboardInterrupt),
        ):
            g.run_fixture_review(inputs)


if __name__ == "__main__":
    unittest.main()
