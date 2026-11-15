"""Two-pass custody tests on newly created invented files; preserve all fixtures."""

import copy
import gzip
import os
import tarfile
import tempfile
import unittest
from datetime import UTC, datetime, timedelta
from pathlib import Path
from unittest.mock import patch

from experiments.simglucose_audit import pbs_archive
from experiments.simglucose_audit import pbs_inspection as inspection
from experiments.simglucose_audit.contract import digest, encode


def entry(name, body=b""):
    info = tarfile.TarInfo(name)
    info.size, info.mode = len(body), 0o644
    return info.tobuf(format=tarfile.USTAR_FORMAT) + body + b"\0" * ((-len(body)) % 512)


def invented(level=9):
    tar = entry(pbs_archive.MARKER_NAME, pbs_archive.MARKER)
    tar += entry("python/invented.bin", b"invented opaque bytes" * 500) + b"\0" * 1024
    return gzip.compress(tar, compresslevel=level, mtime=0)


class InspectionFixtureTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.proof_root = Path(tempfile.mkdtemp(prefix="ot062-inspection-tests-"))
        os.chmod(cls.proof_root, 0o700)
        cls.serial = 0

    def setUp(self):
        if not hasattr(os, "O_NOFOLLOW") or os.open not in os.supports_dir_fd:
            self.skipTest("owned nofollow dirfd fixture unsupported; no OS qualification")
        self.now = datetime(2026, 11, 10, 14, tzinfo=UTC)
        self.clock = patch.object(inspection, "_now", side_effect=lambda: self.now)
        self.clock.start()
        self.addCleanup(self.clock.stop)
        self.raw = invented()
        self.context = inspection.make_invented_context(self.raw)

    def destination(self):
        type(self).serial += 1
        return self.proof_root / f"case-{self.serial}"

    def run_fixture(self, raw=None, context=None, destination=None):
        raw = self.raw if raw is None else raw
        context = self.context if context is None else context
        return inspection.inspect_invented_file(
            raw, digest(raw), context, digest(context), destination or self.destination()
        )

    def cold(self, report, context=None):
        context = self.context if context is None else context
        raw_report = encode(report)
        return inspection.inspect_fixture_report(
            raw_report, digest(raw_report), self.raw, digest(self.raw), context, digest(context)
        )

    def test_completed_same_fd_order_and_exact_two_pass_accounting(self):
        original_read, original_seek, original_headers = os.read, os.lseek, inspection._headers
        reads, seeks = [], []

        def read(fd, count):
            raw = original_read(fd, count)
            reads.append((fd, count, len(raw)))
            return raw

        def seek(fd, offset, whence):
            seeks.append((fd, offset, whence))
            return original_seek(fd, offset, whence)

        def headers(raw, pin):
            self.assertEqual(sum(row[2] for row in reads), 2 * len(self.raw))
            self.assertEqual(sum(row[2] == 0 for row in reads), 2)
            return original_headers(raw, pin)

        with (
            patch.object(os, "read", side_effect=read),
            patch.object(os, "lseek", side_effect=seek),
            patch.object(inspection, "_headers", side_effect=headers),
        ):
            report = self.run_fixture()
        self.assertEqual(report["status"], "fixture-two-pass-completed")
        self.assertEqual(report["events"], list(inspection.STAGES))
        self.assertEqual(len({row[0] for row in reads + seeks}), 1)
        self.assertEqual(len(seeks), 2)
        self.assertTrue(report["owned_descriptor_closed"])
        self.assertEqual(len(report["tokens"]), 4)
        self.assertGreater(report["inventory"]["decompressed_member_bytes_drained"], 0)
        self.assertNotIn("payload_sha256", str(report["inventory"]))
        self.assertEqual(report["selected_notices"], [])
        self.assertFalse(report["actual_execution_ready"])
        self.assertEqual(self.cold(report)["status"], "fixture-metadata-consistent")

    def test_denied_and_pending_auth_never_rewind_or_parse(self):
        for status in ("denied", "pending"):
            context = inspection.decode(self.context)
            context["fixture_auth_status"] = status
            context = encode(context)
            with (
                patch.object(inspection, "_headers", side_effect=AssertionError("parser reached")),
                patch.object(os, "lseek", wraps=os.lseek) as seek,
            ):
                report = self.run_fixture(context=context)
            self.assertEqual(seek.call_count, 1)
            self.assertEqual(report["events"], ["created", "pass1"])
            self.assertIsNone(report["pass2"])
            self.assertIn("fixture-auth-not-admitted", report["error"])
            self.assertTrue(report["owned_descriptor_closed"])
            self.cold(report, context)

    def test_bad_input_context_or_actual_claim_rejected_before_path(self):
        for field, value in (
            ("artifact_sha256", "0" * 64),
            ("actual_crypto_verified", True),
            ("actual_authentication_admitted", True),
            ("extra", "path"),
            ("source_identity", {}),
            ("artifact_bytes", True),
        ):
            mutant = inspection.decode(self.context)
            mutant[field] = value
            context = encode(mutant)
            destination = self.destination()
            with (
                self.subTest(field=field),
                self.assertRaises(ValueError),
                patch.object(os, "open", side_effect=AssertionError("path opened")),
            ):
                self.run_fixture(context=context, destination=destination)
            self.assertFalse(destination.exists())

    def test_expired_or_future_context_before_path(self):
        for now in (self.now + timedelta(hours=2), self.now - timedelta(hours=2)):
            self.now = now
            with (
                self.assertRaises(ValueError),
                patch.object(os, "open", side_effect=AssertionError("opened")),
            ):
                self.run_fixture()

    def test_expiry_between_passes_no_parser(self):
        original = inspection._read_pass

        def read(*args):
            result = original(*args)
            self.now += timedelta(hours=2)
            return result

        with (
            patch.object(inspection, "_read_pass", side_effect=read),
            patch.object(inspection, "_headers", side_effect=AssertionError("parser")),
        ):
            report = self.run_fixture()
        self.assertEqual(report["events"], ["created", "pass1"])
        self.assertIn("current-fixture-window", report["error"])
        self.assertTrue(report["owned_descriptor_closed"])

    def test_growth_and_same_size_mutation_between_passes(self):
        original = inspection._observe
        for grow in (False, True):
            calls = 0

            def observe(fd, *args):
                nonlocal calls
                calls += 1
                if calls == 2:
                    os.pwrite(fd, b"X", len(self.raw) if grow else 20)
                return original(fd, *args)

            with (
                patch.object(inspection, "_observe", side_effect=observe),
                patch.object(inspection, "_headers", side_effect=AssertionError("parser")),
            ):
                report = self.run_fixture()
            self.assertIn("file-changed-after-pass1", report["error"])
            self.cold(report)
            self.assertIsNone(report["pass2"])
            self.assertTrue(report["owned_descriptor_closed"])

    def test_replaced_name_refuses_old_descriptor_adoption(self):
        original, calls = inspection._observe, 0

        def observe(fd, directory_fd, *args):
            nonlocal calls
            calls += 1
            if calls == 2:
                os.rename(
                    "input.fixture",
                    "retained-original.fixture",
                    src_dir_fd=directory_fd,
                    dst_dir_fd=directory_fd,
                )
                replacement = os.open(
                    "input.fixture",
                    os.O_WRONLY | os.O_CREAT | os.O_EXCL,
                    0o600,
                    dir_fd=directory_fd,
                )
                try:
                    os.write(replacement, self.raw)
                finally:
                    os.close(replacement)
            return original(fd, directory_fd, *args)

        with patch.object(inspection, "_observe", side_effect=observe):
            report = self.run_fixture()
        self.assertIn("same-fd-name-binding", report["error"])
        self.assertTrue(report["owned_descriptor_closed"])

    def test_hardlink_and_mode_drift(self):
        original = inspection._observe
        for hardlink in (False, True):
            calls = 0

            def observe(fd, directory_fd, *args):
                nonlocal calls
                calls += 1
                if calls == 2:
                    if hardlink:
                        os.link(
                            "input.fixture",
                            "retained-alias.fixture",
                            src_dir_fd=directory_fd,
                            dst_dir_fd=directory_fd,
                            follow_symlinks=False,
                        )
                    else:
                        os.fchmod(fd, 0o644)
                return original(fd, directory_fd, *args)

            with patch.object(inspection, "_observe", side_effect=observe):
                report = self.run_fixture()
            self.assertIn("private-owned-regular-fixture", report["error"])
            self.assertIsNone(report["pass2"])

    def test_directory_name_replaced(self):
        original, calls = inspection._observe, 0

        def observe(fd, directory_fd, parent_fd, name):
            nonlocal calls
            calls += 1
            if calls == 2:
                os.rename(name, name + "-retained", src_dir_fd=parent_fd, dst_dir_fd=parent_fd)
                os.mkdir(name, 0o700, dir_fd=parent_fd)
            return original(fd, directory_fd, parent_fd, name)

        with patch.object(inspection, "_observe", side_effect=observe):
            report = self.run_fixture()
        self.assertIn("same-private-directory-name-binding", report["error"])

    def test_no_overwrite_or_symlink_destination(self):
        destination = self.destination()
        os.mkdir(destination, 0o700)
        report = self.run_fixture(destination=destination)
        self.assertEqual(report["status"], "incomplete")
        self.assertFalse((destination / "input.fixture").exists())
        destination = self.destination()
        os.symlink("absent-invented-target", destination)
        report = self.run_fixture(destination=destination)
        self.assertEqual(report["status"], "incomplete")
        self.assertFalse((self.proof_root / "absent-invented-target").exists())

    def test_logical_deadline_before_create(self):
        destination = self.destination()
        with patch.object(inspection, "FIXTURE_SECONDS", 0):
            report = self.run_fixture(destination=destination)
        self.assertIn("fixture-logical-deadline", report["error"])
        self.assertFalse(destination.exists())
        self.cold(report)

    def test_partial_pass_read_error_counts_prefix_and_closes(self):
        self.raw = invented(level=0)
        self.context = inspection.make_invented_context(self.raw)
        original, calls = os.read, 0

        def read(fd, count):
            nonlocal calls
            calls += 1
            if calls == 2:
                raise OSError(5, "invented failure")
            return original(fd, count)

        with patch.object(os, "read", side_effect=read):
            report = self.run_fixture()
        self.assertEqual(report["pass1"]["bytes"], 4096)
        self.assertEqual(report["pass1"]["EOF_probes"], 0)
        self.assertTrue(report["owned_descriptor_closed"])
        self.cold(report)

    def test_source_change_between_passes(self):
        original, identity = inspection._read_pass, inspection._identity()

        def read(*args):
            result = original(*args)
            identity["invented-drift"] = "0" * 64
            return result

        with (
            patch.object(inspection, "_identity", side_effect=lambda: dict(identity)),
            patch.object(inspection, "_read_pass", side_effect=read),
        ):
            report = self.run_fixture()
        self.assertIn("source-changed", report["error"])
        self.assertIsNone(report["pass2"])

    def test_parser_refusal_preserves_two_pass_prefix(self):
        self.raw = gzip.compress(b"invented no mandatory marker or tar", mtime=0)
        self.context = inspection.make_invented_context(self.raw)
        report = self.run_fixture()
        self.assertEqual(report["events"], list(inspection.STAGES[:-1]))
        self.assertEqual(report["status"], "incomplete")
        self.assertTrue(report["owned_descriptor_closed"])
        self.cold(report)

    def test_cold_reader_never_opens_file_or_calls_producer(self):
        report = self.run_fixture()
        with (
            patch.object(
                inspection, "inspect_invented_file", side_effect=AssertionError("producer")
            ),
            patch.object(os, "open", side_effect=AssertionError("file opened")),
        ):
            self.cold(report)

    def test_rehashed_cold_promotions_and_binding_forgeries(self):
        report = self.run_fixture()
        for field, value in (
            ("actual_crypto_verified", True),
            ("actual_authentication_admitted", True),
            ("actual_execution_ready", True),
            ("selected_notices", ["LICENSE"]),
            ("source_identity", {}),
            ("context_sha256", "0" * 64),
            ("physical_history_authenticated", True),
            ("owned_descriptor_closed", False),
            ("error", "invented failure"),
            ("events", list(reversed(inspection.STAGES))),
        ):
            mutant = copy.deepcopy(report)
            mutant[field] = value
            with self.subTest(field=field), self.assertRaises(ValueError):
                self.cold(mutant)
        mutant = copy.deepcopy(report)
        mutant["pass2"]["EOF_probes"] = 0
        with self.assertRaises(ValueError):
            self.cold(mutant)
        mutant = copy.deepcopy(report)
        mutant["inventory"]["rows"][0]["bytes"] += 1
        with self.assertRaises(ValueError):
            self.cold(mutant)

    def test_denied_auth_rehashed_premature_pass_and_token_observations(self):
        context = inspection.decode(self.context)
        context["fixture_auth_status"] = "denied"
        context = encode(context)
        report = self.run_fixture(context=context)
        for changes in (
            {"pass2": {"bytes": 1, "sha256": digest(self.raw[:1]), "EOF_probes": 0}},
            {"fixture_auth_observation": "fixture-controls-passed"},
            {"tokens": report["tokens"] + [report["tokens"][0]]},
            {"events": [], "pass1": report["pass1"], "tokens": []},
        ):
            mutant = copy.deepcopy(report)
            mutant.update(changes)
            with self.assertRaises(ValueError):
                self.cold(mutant, context)

    def test_failure_status_cannot_be_promoted_by_one_boolean(self):
        context = inspection.decode(self.context)
        context["fixture_auth_status"] = "denied"
        context = encode(context)
        report = self.run_fixture(context=context)
        report["status"] = "fixture-two-pass-completed"
        report["error"] = None
        with self.assertRaises(ValueError):
            self.cold(report, context)

    def test_close_error_is_sticky_and_never_completes(self):
        original, calls = os.close, 0

        def close(fd):
            nonlocal calls
            calls += 1
            original(fd)
            if calls == 1:
                raise OSError(5, "invented reported close error after actual close")

        with patch.object(os, "close", side_effect=close):
            report = self.run_fixture()
        self.assertEqual(calls, 3)
        self.assertEqual(report["status"], "incomplete")
        self.assertIn("close-errno", report["cleanup_error"])
        self.assertFalse(report["owned_descriptor_closed"])
        self.cold(report)

    def test_strict_cold_json_types(self):
        report = self.run_fixture()
        for mutate in (
            lambda value: value.update(actual_crypto_verified=0),
            lambda value: value["pass1"].update(EOF_probes=True),
        ):
            mutant = copy.deepcopy(report)
            mutate(mutant)
            with self.assertRaises(ValueError):
                self.cold(mutant)

    def test_actual_facade_refuses_poison_before_source_path_or_body(self):
        class Poison:
            def __fspath__(self):
                raise AssertionError("path touched")

            def __bytes__(self):
                raise AssertionError("body touched")

        with (
            patch.object(inspection, "_identity", side_effect=AssertionError("source")),
            patch.object(os, "open", side_effect=AssertionError("open")),
        ):
            with self.assertRaises(PermissionError):
                inspection.inspect_archive(Poison(), authenticated=True, context=Poison())


if __name__ == "__main__":
    unittest.main()
