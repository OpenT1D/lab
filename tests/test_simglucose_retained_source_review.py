"""Invented fixtures only: no retained source/notice/runtime material access."""

import copy
import os
import stat
import tempfile
import time
import unittest
from datetime import timedelta
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

from experiments.simglucose_audit import fixture_time
from experiments.simglucose_audit import retained_source_review as r


class RetainedSourceReviewTests(unittest.TestCase):
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

    def test_stat_tokens_preserve_flags_only_where_the_platform_exposes_them(self):
        info = dict(
            st_dev=1,
            st_ino=2,
            st_uid=3,
            st_mode=stat.S_IFREG | 0o600,
            st_nlink=1,
            st_size=4,
            st_mtime_ns=5,
            st_ctime_ns=6,
        )
        self.assertEqual(r._token(SimpleNamespace(**info)), [1, 2, 3, 0o600, 1, 4, 5, 6, 0])
        self.assertEqual(r._token(SimpleNamespace(**info, st_flags=8))[-1], 8)

    def fixture(self, **kwargs):
        parent = Path(
            tempfile.mkdtemp(prefix="retained-invented-", dir=os.environ.get("OT062_FIXTURE_ROOT"))
        ).resolve()
        return parent, r.fixture_inputs(parent, **kwargs)

    def completed(self):
        parent, inputs = self.fixture()
        a = r.run_fixture_review(inputs)
        self.assertEqual(a["status"], "completed")
        return parent, inputs, a

    def b(self, inputs, a, **kwargs):
        return r.run_fixture_review(
            inputs,
            substep="B",
            held_producer_receipt_sha256=r.digest(r.encode(a)),
            held_report_sha256=a["report_sha256"],
            **kwargs,
        )

    def test_ordinary_closed_before_arguments(self):
        class Trap:
            def __getattribute__(self, name):
                raise AssertionError("argument touched")

        with self.assertRaises(PermissionError):
            r.run_review(Trap())

    def test_two_substeps_all_labels_notice_exact_and_metadata_only(self):
        parent, inputs, a = self.completed()
        self.assertNotIn(r.FIXTURE_NOTICE, r.encode(a).decode())
        self.assertEqual(
            r.digest((parent / "invented-retained-review" / "receipt.private.json").read_bytes()),
            r.digest(r.encode(a)),
        )
        b = self.b(inputs, a)
        review = b["review"]
        self.assertEqual(review["notice"]["full_literal_text"], r.FIXTURE_NOTICE)
        self.assertEqual(len(review["go_mod_context"]["require_labels"]), 201)
        self.assertFalse(review["go_mod_context"]["labels_truncated"])
        self.assertFalse(review["claims"]["actual_crypto_or_native_admission"])
        self.assertEqual(
            set(p.name for p in (parent / "invented-retained-review").iterdir()),
            {"report.private.json", "receipt.private.json"},
        )
        self.assertTrue(
            all(
                stat.S_IMODE(p.stat().st_mode) == 0o600
                for p in (parent / "invented-retained-review").iterdir()
            )
        )
        self.assertEqual(b["review_receipt"]["report_material_passes"], 1)

    def test_replay_markers_after_output_rename(self):
        parent, inputs, a = self.completed()
        output = parent / "invented-retained-review"
        output.rename(parent / "retained-old-output")
        self.assertEqual(r.run_fixture_review(inputs)["status"], "incomplete")
        self.assertFalse(output.exists())
        (parent / "retained-old-output").rename(output)
        self.assertIn("review", self.b(inputs, a))
        output.rename(parent / "retained-final-output")
        self.assertEqual(self.b(inputs, a)["status"], "incomplete")

    def test_wrong_source_hash_no_notice_copy(self):
        parent, inputs = self.fixture()
        path = parent / "invented-input" / "objects" / "LICENSE"
        path.write_bytes(b"X" * path.stat().st_size)
        a = r.run_fixture_review(inputs)
        self.assertEqual(a["status"], "incomplete")
        self.assertFalse((parent / "invented-retained-review").exists())
        self.assertNotIn("full_literal_text", r.encode(a).decode())

    def test_source_symlink_fifo_hardlink_refused_without_open(self):
        for kind in ("symlink", "fifo", "hardlink"):
            with self.subTest(kind=kind):
                parent, inputs = self.fixture()
                path = parent / "invented-input" / "objects" / "LICENSE"
                saved = parent / "invented-notice-saved"
                path.rename(saved)
                if kind == "symlink":
                    path.symlink_to(saved)
                elif kind == "fifo":
                    os.mkfifo(path, 0o600)
                else:
                    os.link(saved, path)
                self.assertEqual(r.run_fixture_review(inputs)["status"], "incomplete")
                self.assertFalse((parent / "invented-retained-review").exists())

    def test_go_context_uncertainty_without_raw_lines(self):
        context = r._parse_mod(
            "module invented.invalid/x\nreplace secret.invalid/X => ../PRI"
            "VATE\nrequire (\na.invalid/b v1.0.0\n)\nunknownxyz hidden-secret"
            "\n"
        )
        self.assertFalse(context["complete_supported_lexical_context"])
        self.assertNotIn("hidden-secret", r.encode(context).decode())
        self.assertNotIn("PRIVATE", r.encode(context).decode())
        r._validate_context(context, 300)
        for text in (
            "module x\nrequire (\nbad\n",
            "module x\nmodule y\n",
            "module x\u2028go 1.23",
            "module x\n" + "x" * 4097,
        ):
            self.assertFalse(r._parse_mod(text)["complete_supported_lexical_context"])

    def test_report_output_overflow_rejects_without_silent_drop(self):
        parent, inputs = self.fixture(go_text="module x\n" + "?\n" * 7000)
        self.assertEqual(r.run_fixture_review(inputs)["status"], "incomplete")
        self.assertFalse((parent / "invented-retained-review").exists())

    def test_notice_roundtrip_controls_quotes_and_nonascii(self):
        notice = '"invented"\\\r\n\t© café\x01\n'
        parent, inputs = self.fixture(notice_text=notice)
        a = r.run_fixture_review(inputs)
        self.assertEqual(self.b(inputs, a)["review"]["notice"]["full_literal_text"], notice)

    def test_source_split_utf8_and_invalid_utf8_NUL(self):
        parent, inputs = self.fixture(notice_text="a" * 4094 + "é")
        # Generic LICENSE cap is deliberately finite; use direct role source to exercise decoder.
        plan = r.decode(inputs[0])
        plan["targets"][1]["expected_bytes"] = 4096
        expiry = r.core._now() + timedelta(seconds=30)
        text, _ = r._read_source(plan, plan["targets"][1], expiry, time.monotonic() + 10)
        self.assertEqual(text, "a" * 4094 + "é")
        for raw in (b"\xff", b"\0", b"\xc3"):
            parent, inputs = self.fixture(notice_text="a")
            path = parent / "invented-input" / "objects" / "LICENSE"
            path.write_bytes(raw)
            self.assertEqual(r.run_fixture_review(inputs)["status"], "incomplete")

    def test_cold_metadata_no_report_or_original_open(self):
        parent, inputs, a = self.completed()
        original = os.open
        denied = {str(parent / "invented-input" / "objects" / name) for name in r.ROLES}

        def guarded(path, *args, **kwargs):
            if os.fsdecode(path) == "report.private.json" or os.fsdecode(path) in denied:
                raise AssertionError("material reopen")
            return original(path, *args, **kwargs)

        with mock.patch.object(r.os, "open", guarded):
            self.assertEqual(
                r.inspect_receipt_metadata(
                    *inputs, held_receipt_sha256=r.digest(r.encode(a)), fixture=True
                ),
                a,
            )

    def test_B_requires_held_A_pin_and_consumes_before_report_open(self):
        parent, inputs, a = self.completed()
        result = r.run_fixture_review(
            inputs,
            substep="B",
            held_producer_receipt_sha256="0" * 64,
            held_report_sha256=a["report_sha256"],
        )
        self.assertEqual(result["status"], "incomplete")
        self.assertEqual(self.b(inputs, a)["status"], "incomplete")

    def test_B_no_original_body_reopen(self):
        _, inputs, a = self.completed()
        plan = r.decode(inputs[0])
        deadline = time.monotonic() + 30
        expiry = r.core._now() + timedelta(seconds=30)
        original = os.open

        def guarded(path, *args, **kwargs):
            if os.fsdecode(path) in r.ROLES:
                raise AssertionError("original body reopened")
            return original(path, *args, **kwargs)

        with mock.patch.object(r.os, "open", guarded):
            r._check_inputs(plan, expiry, deadline)
        self.assertIn("review", self.b(inputs, a))

    def test_strict_parent_B_rehashed_promotion_and_raw_lines(self):
        _, inputs, a = self.completed()
        b = self.b(inputs, a)
        plan = r.decode(inputs[0])
        approval = r.decode(inputs[1])
        expiry = r.core._utc(approval["expires_utc"])
        mutations = [
            lambda x: x["review_receipt"].update(extra="unknown"),
            lambda x: x["review_receipt"].update(report_material_passes=True),
            lambda x: x["review_receipt"].update(ended_utc="2099-01-01T00:00:00Z"),
            lambda x: x["review"]["claims"].update(actual_crypto_or_native_admission=True),
            lambda x: x["review"]["go_mod_context"].update(raw_go_mod="secret"),
            lambda x: x["review"]["notice"].update(full_literal_text="forged"),
        ]
        for mutate in mutations:
            changed = copy.deepcopy(b)
            mutate(changed)
            with self.assertRaises((ValueError, RuntimeError)):
                r._validate_B(
                    changed,
                    plan,
                    inputs[3],
                    r.digest(r.encode(a)),
                    r.digest(r.encode(changed["review"])),
                    r.core._utc(approval["issued_utc"]),
                    expiry,
                )

    def test_parent_B_wrong_held_digest_refuses(self):
        _, inputs, a = self.completed()
        b = self.b(inputs, a)
        approval = r.decode(inputs[1])
        with self.assertRaises(ValueError):
            r._validate_B(
                b,
                r.decode(inputs[0]),
                inputs[3],
                r.digest(r.encode(a)),
                "0" * 64,
                r.core._utc(approval["issued_utc"]),
                r.core._utc(approval["expires_utc"]),
            )

    def test_namespace_extra_file_stops_B(self):
        parent, inputs, a = self.completed()
        (parent / "invented-retained-review" / "unexpected").write_bytes(b"invented")
        self.assertEqual(self.b(inputs, a)["status"], "incomplete")

    def test_owned_whole_deadline_stalls(self):
        for case in ("source-stall", "read-stall", "write-stall", "fsync-stall", "finalize-stall"):
            with self.subTest(case=case):
                _, inputs = self.fixture()
                start = time.monotonic()
                a = r.run_fixture_review(inputs, case=case, whole_seconds=0.6)
                self.assertEqual(a["status"], "incomplete")
                self.assertLess(time.monotonic() - start, 2)
        for case in ("B-read-stall", "B-emit-stall"):
            with self.subTest(case=case):
                _, inputs, a = self.completed()
                start = time.monotonic()
                b = self.b(inputs, a, case=case, whole_seconds=0.6)
                self.assertEqual(b["status"], "incomplete")
                self.assertLess(time.monotonic() - start, 2)

    def test_source_named_directory_swap_refused(self):
        parent = Path(
            tempfile.mkdtemp(prefix="source-binding-", dir=os.environ.get("OT062_FIXTURE_ROOT"))
        ).resolve()
        directory = parent / "source"
        directory.mkdir()
        source = directory / "module.py"
        source.write_bytes(b"invented old source")
        alternate = parent / "alternate"
        alternate.mkdir()
        (alternate / "module.py").write_bytes(b"invented new source")
        original = os.read
        swapped = False

        def read(fd, n):
            nonlocal swapped
            data = original(fd, n)
            if not swapped:
                swapped = True
                directory.rename(parent / "held-old")
                alternate.rename(directory)
            return data

        with mock.patch.object(r.os, "read", read), self.assertRaises(ValueError):
            r._source_hash(source)

    def test_checked_write_short_zero_and_expiry(self):
        parent = Path(
            tempfile.mkdtemp(prefix="writes-", dir=os.environ.get("OT062_FIXTURE_ROOT"))
        ).resolve()
        fd = r.core._directory(str(parent))
        original = os.write
        expiry = r.core._now() + timedelta(seconds=10)
        try:
            with mock.patch.object(r.os, "write", lambda fd, raw: original(fd, raw[:1])):
                r._write_checked(fd, "short", b"invented", expiry, time.monotonic() + 10)
            self.assertEqual((parent / "short").read_bytes(), b"invented")
            with mock.patch.object(r.os, "write", return_value=0), self.assertRaises(ValueError):
                r._write_checked(fd, "zero", b"invented", expiry, time.monotonic() + 10)
            with self.assertRaises(ValueError):
                r._write_checked(
                    fd,
                    "expired",
                    b"invented",
                    r.core._now() - timedelta(seconds=1),
                    time.monotonic() + 10,
                )
            self.assertFalse((parent / "expired").exists())
        finally:
            os.close(fd)

    def test_fixture_rehashed_plan_cannot_select_foreign_material(self):
        _, inputs = self.fixture()
        plan, approval, origin, held = inputs
        changed = r.decode(plan)
        changed["qualification_sha256"] = "0" * 64
        changed_raw = r.encode(changed)
        grant = r.decode(approval)
        grant["plan_sha256"] = r.digest(changed_raw)
        grant_raw = r.encode(grant)
        forged = (
            changed_raw,
            grant_raw,
            origin,
            held | {"plan_sha256": r.digest(changed_raw), "approval_sha256": r.digest(grant_raw)},
        )
        with (
            mock.patch.object(r.os, "open", side_effect=AssertionError("unowned fixture opened")),
            self.assertRaises(ValueError),
        ):
            r.run_fixture_review(forged)

    def test_cold_historical_grant_expired_live_retention(self):
        _, inputs, a = self.completed()
        future = r.core._now() + timedelta(hours=2)
        with mock.patch.object(r.core, "_now", return_value=future):
            self.assertEqual(
                r.inspect_receipt_metadata(
                    *inputs, held_receipt_sha256=r.digest(r.encode(a)), fixture=True
                ),
                a,
            )
            with self.assertRaises(ValueError):
                r.run_fixture_review(
                    inputs,
                    substep="B",
                    held_producer_receipt_sha256=r.digest(r.encode(a)),
                    held_report_sha256=a["report_sha256"],
                )
        with (
            mock.patch.object(r.core, "_now", return_value=future + timedelta(days=2)),
            mock.patch.object(r.os, "open", side_effect=AssertionError("retention expired path")),
            self.assertRaises(ValueError),
        ):
            r.inspect_receipt_metadata(
                *inputs, held_receipt_sha256=r.digest(r.encode(a)), fixture=True
            )

    def test_report_short_write_hash_and_zero_write_refusal(self):
        parent = Path(
            tempfile.mkdtemp(prefix="report-write-", dir=os.environ.get("OT062_FIXTURE_ROOT"))
        ).resolve()
        directory = r.core._directory(str(parent))
        expiry = r.core._now() + timedelta(seconds=20)
        original = os.write
        raw = r.encode({"invented_notice": "quoted é\r\n"})
        try:
            with mock.patch.object(r.os, "write", lambda fd, data: original(fd, data[:1])):
                count, sha, token = r._write_report(
                    directory, raw, expiry, time.monotonic() + 10, None
                )
            self.assertEqual((count, sha, token[5]), (len(raw), r.digest(raw), len(raw)))
        finally:
            os.close(directory)
        parent = Path(
            tempfile.mkdtemp(prefix="report-zero-", dir=os.environ.get("OT062_FIXTURE_ROOT"))
        ).resolve()
        directory = r.core._directory(str(parent))
        try:
            with mock.patch.object(r.os, "write", return_value=0), self.assertRaises(ValueError):
                r._write_report(directory, raw, expiry, time.monotonic() + 10, None)
        finally:
            os.close(directory)

    def test_ownership_close_attempted_when_tree_query_fails(self):
        process = mock.Mock()
        process.poll.return_value = 0
        with (
            mock.patch.object(r.platform_process, "tree_exists", side_effect=OSError("invented")),
            mock.patch.object(r.platform_process, "close_tree") as close,
            self.assertRaises(ValueError),
        ):
            r._stop(process, None, None, True, time.monotonic() + 1)
        close.assert_called_once_with(process)

    def test_actual_profile_cannot_use_invented_self_approval(self):
        _, inputs = self.fixture()
        with (
            mock.patch.object(
                r.os, "open", side_effect=AssertionError("actual path before refusal")
            ),
            self.assertRaises(ValueError),
        ):
            r.read_approved(*inputs)

    def test_fixture_parent_must_be_empty_before_writes(self):
        parent = Path(
            tempfile.mkdtemp(prefix="nonempty-fixture-", dir=os.environ.get("OT062_FIXTURE_ROOT"))
        ).resolve()
        (parent / "preserved-invented").write_bytes(b"invented")
        with self.assertRaises(ValueError):
            r.fixture_inputs(parent)
        self.assertFalse((parent / "invented-input").exists())

    def test_full_generic_source_caps_and_split_utf8(self):
        prefix = "module invented.invalid/x\n//"
        go = prefix + "a" * (4095 - len(prefix)) + "é" + " " * (r.ROLE_CAPS[0] - 4097)
        notice = "z" * r.ROLE_CAPS[1]
        _, inputs = self.fixture(go_text=go, notice_text=notice)
        a = r.run_fixture_review(inputs)
        self.assertEqual(a["status"], "completed")
        self.assertEqual(a["source_rows"][0]["bytes"], r.ROLE_CAPS[0])
        self.assertEqual(self.b(inputs, a)["review"]["notice"]["full_literal_text"], notice)

    def test_gate_before_path_on_expiry_or_pin_mismatch(self):
        _, inputs = self.fixture()
        plan, approval, origin, held = inputs
        with (
            mock.patch.object(r.os, "open", side_effect=AssertionError("path before pin")),
            self.assertRaises(ValueError),
        ):
            r._gate(plan + b" ", approval, origin, held, True)
        expired = r.decode(approval)
        expired["expires_utc"] = expired["issued_utc"]
        raw = r.encode(expired)
        held = held | {"approval_sha256": r.digest(raw)}
        with (
            mock.patch.object(r.os, "open", side_effect=AssertionError("path before expiry")),
            self.assertRaises(ValueError),
        ):
            r._gate(plan, raw, origin, held, True)


if __name__ == "__main__":
    unittest.main()
