"""Generated invented files only; full declared limits, no cleanup or real input."""

import copy
import gzip
import os
import subprocess
import sys
import tempfile
import time
import unittest
from datetime import UTC, datetime, timedelta
from pathlib import Path
from unittest.mock import patch

from experiments.simglucose_audit import fixture_time
from experiments.simglucose_audit import pbs_production_inspection as reader
from experiments.simglucose_audit.contract import digest, encode


def member(path, body=b"", flag=b"0", link=""):
    return reader._header_bytes(path, len(body), flag, link) + body + b"\0" * ((-len(body)) % 512)


def archive(*parts, tail=b"\0" * 1024):
    return gzip.compress(b"".join(parts) + tail, mtime=0)


def change(raw, start, value):
    header = bytearray(raw)
    header[start : start + len(value)] = value
    header[148:156] = b" " * 8
    header[148:156] = (f"{sum(header):06o}\0 ").encode()
    return bytes(header)


class ProductionReaderTests(unittest.TestCase):
    def setUp(self):
        self.enterContext(fixture_time.use(True))

    @classmethod
    def setUpClass(cls):
        if not hasattr(os, "O_NOFOLLOW") or os.open not in os.supports_dir_fd:
            raise unittest.SkipTest("owned dirfd fixtures unsupported; no platform qualification")
        cls.root = Path(tempfile.mkdtemp(prefix="ot062-production-reader-tests-"))
        os.chmod(cls.root, 0o700)
        cls.serial, cls.reports = 0, {}

    def path(self):
        type(self).serial += 1
        return self.root / f"fixture-{self.serial}"

    def scenario(self, name):
        if name not in self.reports:
            self.reports[name] = reader.qualify_invented_scenario(name, self.path())
        return self.reports[name]

    def cold(self, report, pin="issued"):
        raw = encode(report)
        return reader.inspect_fixture_metadata(
            raw, digest(raw), report["issued_completion_pin"] if pin == "issued" else pin
        )

    def parse(self, raw, fragment=None):
        path = self.path()
        fd = os.open(path, os.O_RDWR | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
        try:
            offset = 0
            while offset < len(raw):
                offset += os.write(fd, raw[offset:])
            os.lseek(fd, 0, os.SEEK_SET)
            observation = {}
            original = os.read

            def read(owned, count):
                return original(owned, min(count, fragment) if fragment and owned == fd else count)

            with patch.object(os, "read", side_effect=read):
                result = reader._inventory(fd, lambda: None, observation)
            return result, observation
        finally:
            os.close(fd)

    def test_small_marker_free_core_and_owned_route(self):
        report = self.scenario("small")
        self.assertEqual(report["status"], "invented-owned-route-completed")
        worker = report["worker"]
        self.assertEqual(worker["pass1"]["bytes"], worker["pass2"]["compressed_bytes"])
        self.assertEqual(worker["pass1"]["EOF_probes"], 1)
        self.assertEqual(worker["pass2"]["EOF_probes"], 1)
        self.assertTrue(worker["descriptor_closed"])
        self.assertTrue(report["reader_joined"] and report["reader_eof"])
        self.assertIsNone(report["cleanup_error"])
        self.assertFalse(worker["actual_crypto_verified"])
        self.assertEqual(self.cold(report)["payload_reopened_or_rehashed"], False)
        result, _ = self.parse(archive(member("unmarked-invented", b"opaque")))
        self.assertEqual(result["headers"][0]["path"], "unmarked-invented")
        self.assertNotIn("sha256", str(result))

    def test_full_256MiB_member_and_rejection(self):
        report = self.scenario("member-exact")
        self.assertEqual(report["status"], "invented-owned-route-completed")
        self.assertEqual(report["worker"]["inventory"]["member_bytes_opaquely_drained"], 268435456)
        over = self.scenario("member-over")
        self.assertIn("member-size-or-mode", over["worker"]["error"])
        self.assertIsNone(over["issued_completion_pin"])
        self.cold(over)

    def test_full_512MiB_expanded_and_one_byte_sentinel(self):
        exact = self.scenario("expanded-exact")
        self.assertEqual(exact["status"], "invented-owned-route-completed")
        self.assertEqual(exact["worker"]["pass2"]["decompressed_bytes"], 536870912)
        self.assertLessEqual(exact["worker"]["pass2"]["max_decompressed_chunk"], 65536)
        over = self.scenario("expanded-over")
        self.assertIn("decompressed-sentinel-cap", over["worker"]["error"])
        self.assertEqual(over["worker"]["pass2"]["decompressed_bytes"], 536870913)
        self.cold(exact)
        self.cold(over)

    def test_full_20000_member_roster_and_over(self):
        exact = self.scenario("roster-exact")
        self.assertEqual(exact["status"], "invented-owned-route-completed")
        self.assertEqual(len(exact["worker"]["inventory"]["headers"]), 20000)
        self.assertGreater(exact["stdout_bytes"], 1024 * 1024)
        over = self.scenario("roster-over")
        self.assertIn("member-count-cap", over["worker"]["error"])
        self.assertEqual(len(over["worker"]["pass2"]["headers_prefix"]), 20000)
        self.cold(exact)
        self.cold(over)

    def test_full_8MiB_inventory_and_over(self):
        exact = self.scenario("inventory-exact")
        self.assertEqual(exact["status"], "invented-owned-route-completed")
        self.assertEqual(exact["worker"]["inventory"]["inventory_bytes"], 8388608)
        self.assertGreater(exact["stdout_bytes"], 8388608)
        over = self.scenario("inventory-over")
        self.assertIn("inventory-output-cap", over["worker"]["error"])
        self.assertLessEqual(over["worker"]["pass2"]["inventory_bytes"], 8388608)
        self.cold(exact)
        self.cold(over)

    def test_full_valid_gzip_compressed_ceiling_two_passes(self):
        exact = self.scenario("compressed-gzip-exact")
        self.assertEqual(exact["status"], "invented-owned-route-completed")
        self.assertEqual(exact["worker"]["input"]["bytes"], 25172086)
        self.assertEqual(exact["worker"]["pass1"]["bytes"], 25172086)
        self.assertEqual(exact["worker"]["pass2"]["compressed_bytes"], 25172086)
        self.cold(exact)
        over = self.scenario("compressed-gzip-over")
        self.assertEqual(over["worker"]["pass1"]["bytes"], 25172087)
        self.assertEqual(over["worker"]["pass1"]["sha256"], over["worker"]["input"]["sha256"])
        self.assertEqual(over["worker"]["pass2"], {})
        self.cold(over)

    def test_pass2_independent_compressed_sentinel_uses_full_limit(self):
        path = self.path()
        fd = os.open(path, os.O_RDWR | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
        try:
            reader._generate(fd, "compressed-gzip-over", lambda: None)
            os.lseek(fd, 0, os.SEEK_SET)
            observed = {}
            with self.assertRaisesRegex(ValueError, "compressed-sentinel-cap"):
                reader._inventory(fd, lambda: None, observed)
            self.assertEqual(observed["compressed_bytes"], 25172087)
        finally:
            os.close(fd)

    def test_one_and_two_byte_short_reads(self):
        raw = archive(member("invented/a", b"opaque"))
        for fragment in (1, 2):
            result, observed = self.parse(raw, fragment)
            self.assertEqual(result["headers"][0]["bytes"], 6)
            self.assertEqual(observed["compressed_bytes"], len(raw))
            self.assertEqual(observed["EOF_probes"], 1)

    def test_fixed_path_depth_size_helpers_do_not_expand_ustar_grammar(self):
        self.assertEqual(reader._path("a" * 4096), "a" * 4096)
        with self.assertRaises(ValueError):
            reader._path("a" * 4097)
        self.assertEqual(len(reader._path("/".join(["a"] * 32)).split("/")), 32)
        with self.assertRaises(ValueError):
            reader._path("/".join(["a"] * 33))
        # USTAR physical name/prefix fields are narrower; no PAX is inferred.
        with self.assertRaises(ValueError):
            reader._header_bytes("a" * 4096)

    def test_strict_paths_aliases_prefixes_and_links(self):
        cases = [
            (member(path),)
            for path in (
                "/absolute",
                "../parent",
                "a/../x",
                "a//x",
                "a\\b",
                "C:drive",
                "cafe\u0301",
                "a\u0085",
                "a\u202e",
            )
        ]
        cases += [
            (member("a"), member("a")),
            (member("A"), member("a")),
            (member("a"), member("a/x")),
            (member("a/x"), member("a")),
            (member("a", flag=b"2", link="future"), member("future")),
            (member("base"), member("a", flag=b"2", link="base"), member("a/x")),
            (member("base"), member("a/x"), member("a", flag=b"2", link="base")),
            (member("base"), member("a", flag=b"2", link="base"), member("b", flag=b"2", link="a")),
            (member("a", flag=b"1", link="../escape"),),
        ]
        for parts in cases:
            with self.subTest(case=len(parts)), self.assertRaises(ValueError):
                self.parse(archive(*parts))
        linked = self.scenario("links")
        self.assertEqual(linked["status"], "invented-owned-route-completed")
        self.cold(linked)

    def test_types_octal_checksum_and_nonfile_payloads(self):
        good = reader._header_bytes("invented")
        bads = [
            reader._header_bytes("invented", flag=flag)
            for flag in (b"x", b"g", b"L", b"K", b"S", b"3", b"4", b"6", b"7")
        ]
        bads += [
            b"X" + good[1:],
            change(good, 124, b"\x80" + b"\0" * 11),
            change(good, 124, b"00000000008\0"),
            change(good, 100, b"0007777\0"),
            reader._header_bytes("invented", 1, b"5"),
            reader._header_bytes("invented", 1, b"2", "other"),
            reader._header_bytes("invented", link="hidden"),
            change(good, 329, b"0000001\0"),
            change(good, 265, b"bad\x7f"),
        ]
        for bad in bads:
            with self.assertRaises(ValueError):
                self.parse(archive(bad))

    def test_gzip_framing_crc_tar_padding_and_trailer(self):
        raw = archive(member("invented", b"x"))
        bad_crc = bytearray(raw)
        bad_crc[-8] ^= 1
        bad_flag = bytearray(raw)
        bad_flag[3] = 8
        for bad in (
            raw[:-1],
            raw + b"\0",
            raw + gzip.compress(b""),
            bytes(bad_crc),
            bytes(bad_flag),
        ):
            with self.assertRaises(ValueError):
                self.parse(bad)
        for tail in (b"", b"\0" * 512, b"\0" * 1024 + b"x", b"\0" * 1025):
            with self.assertRaises(ValueError):
                self.parse(archive(tail=tail))
        bad_padding = reader._header_bytes("invented", 1) + b"x" + b"Y" + b"\0" * 510
        with self.assertRaises(ValueError):
            self.parse(archive(bad_padding))

    def test_auth_denial_never_second_pass(self):
        report = self.scenario("deny-auth")
        worker = report["worker"]
        self.assertEqual(worker["events"], ["generated", "pass1"])
        self.assertEqual(worker["pass2"], {})
        self.assertIsNone(report["issued_completion_pin"])
        self.cold(report)

    def test_owned_watchdog_covers_generation_storage_report_and_finish_block(self):
        for scenario in ("stall-generate", "stall-storage", "stall-report", "finish-block"):
            start = time.monotonic()
            report = reader._supervise(scenario, self.path(), 3.3)
            self.assertLess(time.monotonic() - start, 5)
            self.assertEqual(report["status"], "incomplete")
            self.assertIsNone(report["issued_completion_pin"])
            self.assertTrue(report["reader_joined"])
            self.assertIsNone(report["cleanup_error"])
            self.assertIsNotNone(report["returncode"])
            self.cold(report)

    def test_unrelated_owned_fixture_process_preserved(self):
        other = subprocess.Popen(
            [sys.executable, "-I", "-S", "-B", "-c", "import time;time.sleep(10)"],
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        try:
            report = reader._supervise("stall-generate", self.path(), 3.3)
            self.assertEqual(report["status"], "incomplete")
            self.assertIsNone(other.poll())
        finally:
            other.terminate()
            other.wait(timeout=2)

    def test_reader_start_failure_stops_actual_owned_child(self):
        original, held = reader.platform_process.spawn, []

        def spawn(*args, **kwargs):
            process = original(*args, **kwargs)
            held.append(process)
            return process

        with (
            patch.object(reader.platform_process, "spawn", side_effect=spawn),
            patch.object(reader.threading.Thread, "start", side_effect=RuntimeError("invented")),
        ):
            report = reader._supervise("stall-generate", self.path(), 3.3)
        self.assertEqual(report["status"], "incomplete")
        self.assertIsNotNone(held[0].poll())
        self.assertIsNone(report["issued_completion_pin"])

    def test_stop_attempts_all_cleanup_stages_and_preserves_errors(self):
        process = unittest.mock.Mock()
        process.poll.return_value = None
        process.wait.side_effect = subprocess.TimeoutExpired("fixed-root-Python", 0.1)
        with (
            patch.object(reader.platform_process, "force_tree", side_effect=OSError(5, "invented")),
            patch.object(
                reader.platform_process, "close_tree", side_effect=RuntimeError("invented")
            ) as close,
            patch.object(reader.platform_process, "tree_exists", return_value=True),
        ):
            result = reader._stop(process, time.monotonic() + 2)
        self.assertIn("owned-force-error", result)
        self.assertIn("owned-wait-error", result)
        self.assertIn("owned-tree-close-error", result)
        self.assertIn("owned-tree-remains", result)
        close.assert_called_once_with(process)

    def test_started_then_raising_reader_still_joins(self):
        original = reader.threading.Thread.start

        def start(thread):
            original(thread)
            raise RuntimeError("invented post-start failure")

        with patch.object(reader.threading.Thread, "start", side_effect=start, autospec=True):
            report = reader._supervise("stall-generate", self.path(), 3.3)
        self.assertEqual(report["status"], "incomplete")
        self.assertTrue(report["reader_joined"])
        self.assertIsNone(report["issued_completion_pin"])

    def test_expiry_and_source_mismatch_before_allocation(self):
        path = self.path()
        with (
            self.assertRaisesRegex(ValueError, "retention-headroom"),
            patch.object(reader, "_now", return_value=datetime(2026, 11, 29, tzinfo=UTC)),
            patch.object(reader.platform_process, "spawn", side_effect=AssertionError("spawn")),
        ):
            reader.qualify_invented_scenario("small", path)
        self.assertFalse(path.exists())
        with self.assertRaises(ValueError):
            reader._worker(
                "small",
                path,
                {},
                fixture_time.FIXTURE_UTC + timedelta(seconds=30),
                time.monotonic() + 30,
            )
        self.assertFalse(path.exists())

    def test_no_overwrite_and_private_namespace(self):
        path = self.path()
        report = reader.qualify_invented_scenario("small", path)
        self.assertEqual(report["status"], "invented-owned-route-completed")
        self.assertEqual(path.stat().st_mode & 0o777, 0o700)
        for name in ("input.gz", "inventory.json"):
            self.assertEqual((path / name).stat().st_mode & 0o777, 0o600)
        second = reader.qualify_invented_scenario("small", path)
        self.assertEqual(second["status"], "incomplete")
        self.assertIsNone(second["issued_completion_pin"])

    def test_cold_reader_never_reopens_body_or_calls_producer(self):
        report = self.scenario("small")
        original_open = os.open
        source_root = Path(reader.__file__).parents[2]
        allowed = {Path(reader.__file__).parent / name for name in reader.SOURCE_FILES}
        allowed.add(Path(reader.__file__))
        allowed.update(source_root / name for name in reader.platform_process.SOURCE_FILES)

        def source_only(path, *args, **kwargs):
            self.assertIn(Path(path), allowed)
            return original_open(path, *args, **kwargs)

        with (
            patch.object(os, "open", side_effect=source_only),
            patch.object(
                reader, "qualify_invented_scenario", side_effect=AssertionError("producer")
            ),
        ):
            self.cold(report)
        with self.assertRaises(ValueError):
            self.cold(report, None)

    def test_independent_rehashed_cold_impossible_completions(self):
        original = self.scenario("small")
        mutations = [
            lambda r: r["worker"].update(events=[], tokens=[]),
            lambda r: r["worker"].update(kind="actual"),
            lambda r: r.update(stdout_bytes=0),
            lambda r: r.update(returncode=False),
            lambda r: r["worker"].update(retention_not_after_utc="2027-01-01T00:00:00Z"),
            lambda r: r["worker"].update(scenario="deny-auth"),
            lambda r: r["worker"]["inventory"]["headers"][0].update(mode=0o4755),
            lambda r: r["worker"]["inventory"]["headers"][0].update(kind="directory"),
            lambda r: r["worker"].update(actual_crypto_verified=True),
            lambda r: r["worker"].update(selected_notices=["LICENSE"]),
            lambda r: r["worker"]["tokens"][1].update(ino=1),
            lambda r: r["worker"]["inventory"]["headers"][0].update(path="a\u202e"),
            lambda r: r["worker"]["pass1"].update(EOF_probes=True),
            lambda r: r["worker"].update(extra="command"),
            lambda r: r.update(physical_history_authenticated=True),
        ]
        for mutate in mutations:
            report = copy.deepcopy(original)
            mutate(report)
            report["stdout_bytes"] = len(encode(report["worker"])) if report["stdout_bytes"] else 0
            report["issued_completion_pin"] = digest(encode(report["worker"]))
            with self.assertRaises(ValueError):
                self.cold(report)

    def test_denied_partial_second_pass_forgery(self):
        report = copy.deepcopy(self.scenario("deny-auth"))
        report["worker"]["pass2"] = copy.deepcopy(self.scenario("small")["worker"]["pass2"])
        report["stdout_bytes"] = len(encode(report["worker"]))
        with self.assertRaises(ValueError):
            self.cold(report)

    def test_large_strict_json_decoder(self):
        raw = encode({"invented": "x" * (2 * 1024 * 1024)})
        self.assertEqual(len(reader._decode(raw)["invented"]), 2 * 1024 * 1024)
        for malformed in (
            b'{"x":1,"x":2}',
            b'{"x":NaN}',
            b'{"x":1e400}',
            b"[" * 65 + b"0" + b"]" * 65,
        ):
            with self.assertRaises(ValueError):
                reader._decode(malformed)

    def direct_worker(self, scenario="small"):
        return reader._worker(
            scenario,
            self.path(),
            reader._identity(),
            fixture_time.FIXTURE_UTC + timedelta(seconds=30),
            time.monotonic() + 30,
        )

    def test_source_fifo_symlink_oversize_and_deadline_fail_bounded(self):
        fifo = self.path()
        os.mkfifo(fifo, 0o600)
        start = time.monotonic()
        with self.assertRaisesRegex(ValueError, "bounded-regular-source"):
            reader._source_bytes(fifo, time.monotonic() + 1)
        self.assertLess(time.monotonic() - start, 1)
        symlink = self.path()
        os.symlink(fifo, symlink)
        with self.assertRaises(OSError):
            reader._source_bytes(symlink, time.monotonic() + 1)
        source = self.path()
        fd = os.open(source, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        try:
            for _ in range(17):
                os.write(fd, b"x" * 65536)
        finally:
            os.close(fd)
        with self.assertRaises(ValueError):
            reader._source_bytes(source, time.monotonic() + 1)
        with self.assertRaisesRegex(ValueError, "source-read-deadline"):
            reader._source_bytes(source, time.monotonic() - 1)

    def test_held_input_growth_replacement_and_mode_drift_refused(self):
        original = reader._observe
        for variant in ("grow", "replace", "mode", "hardlink"):
            calls = 0

            def observe(fd, directory_fd, *args):
                nonlocal calls
                calls += 1
                if calls == 2:
                    if variant == "grow":
                        os.pwrite(fd, b"x", os.fstat(fd).st_size)
                    elif variant == "mode":
                        os.fchmod(fd, 0o644)
                    elif variant == "hardlink":
                        os.link(
                            "input.gz",
                            "retained-alias.gz",
                            src_dir_fd=directory_fd,
                            dst_dir_fd=directory_fd,
                            follow_symlinks=False,
                        )
                    else:
                        os.rename(
                            "input.gz",
                            "retained-original.gz",
                            src_dir_fd=directory_fd,
                            dst_dir_fd=directory_fd,
                        )
                        replacement = os.open(
                            "input.gz",
                            os.O_WRONLY | os.O_CREAT | os.O_EXCL,
                            0o600,
                            dir_fd=directory_fd,
                        )
                        os.close(replacement)
                return original(fd, directory_fd, *args)

            with patch.object(reader, "_observe", side_effect=observe):
                report = self.direct_worker()
            self.assertEqual(report["status"], "incomplete")
            self.assertTrue(report["descriptor_closed"])
            self.assertNotIn("invented-auth-control", report["events"])

    def test_output_directory_replacement_never_redirects_write(self):
        original, calls, selected = reader._observe, 0, self.path()

        def observe(fd, directory_fd, parent_fd, name):
            nonlocal calls
            result = original(fd, directory_fd, parent_fd, name)
            calls += 1
            if calls == 3:
                os.rename(name, name + "-retained", src_dir_fd=parent_fd, dst_dir_fd=parent_fd)
                os.mkdir(name, 0o700, dir_fd=parent_fd)
            return result

        with patch.object(reader, "_observe", side_effect=observe):
            result = reader._worker(
                "small",
                selected,
                reader._identity(),
                fixture_time.FIXTURE_UTC + timedelta(seconds=30),
                time.monotonic() + 30,
            )
        self.assertEqual(result["status"], "incomplete")
        self.assertIn("output-held-directory-binding", result["output_error"])
        self.assertFalse((selected / "inventory.json").exists())
        self.assertFalse(
            (selected.with_name(selected.name + "-retained") / "inventory.json").exists()
        )

    def test_output_fd_name_replacement_refused(self):
        opened, original_open, original_write, replaced = {}, os.open, os.write, False

        def opening(path, *args, **kwargs):
            fd = original_open(path, *args, **kwargs)
            if path == "inventory.json":
                opened.update(fd=fd, directory=kwargs["dir_fd"])
            return fd

        def writing(fd, raw):
            nonlocal replaced
            if fd == opened.get("fd") and not replaced:
                replaced = True
                directory = opened["directory"]
                os.rename(
                    "inventory.json",
                    "retained-report.json",
                    src_dir_fd=directory,
                    dst_dir_fd=directory,
                )
                replacement = original_open(
                    "inventory.json", os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600, dir_fd=directory
                )
                os.close(replacement)
            return original_write(fd, raw)

        with (
            patch.object(os, "open", side_effect=opening),
            patch.object(os, "write", side_effect=writing),
        ):
            result = self.direct_worker()
        self.assertEqual(result["status"], "incomplete")
        self.assertIn("output-fd-name-binding", result["output_error"])

    def test_actual_frontdoor_and_fixed_worker_guard(self):
        class Poison:
            def __fspath__(self):
                raise AssertionError("path")

            def __bytes__(self):
                raise AssertionError("body")

        with (
            patch.object(reader, "_identity", side_effect=AssertionError("source")),
            patch.object(os, "open", side_effect=AssertionError("open")),
        ):
            with self.assertRaises(PermissionError):
                reader.inspect_archive(Poison(), authenticated=True)
        for event in ("socket.connect", "socket.getaddrinfo", "subprocess.Popen", "os.system"):
            with self.assertRaises(PermissionError):
                reader._fixture_audit(event, ())
        with self.assertRaises(ValueError):
            reader.qualify_invented_scenario("actual", self.path())


if __name__ == "__main__":
    unittest.main()
