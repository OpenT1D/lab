"""Only literal invented in-memory gzip/ustar fixtures; no archive extraction."""

import copy
import gzip
import tarfile
import unittest
from unittest.mock import patch

from experiments.simglucose_audit import pbs_archive as archive
from experiments.simglucose_audit.contract import digest, encode


def header(name, size=0, kind=tarfile.REGTYPE, link="", prefix=None):
    info = tarfile.TarInfo(name)
    info.size, info.type, info.linkname = size, kind, link
    info.mode = 0o755 if kind == tarfile.DIRTYPE else 0o644
    raw = info.tobuf(format=tarfile.USTAR_FORMAT, encoding="utf-8")
    if prefix is not None:
        raw = change(raw, 345, prefix.encode().ljust(155, b"\0"))
    return raw


def change(raw, start, value):
    out = bytearray(raw)
    out[start : start + len(value)] = value
    out[148:156] = b" " * 8
    out[148:156] = (f"{sum(out):06o}\0 ").encode()
    return bytes(out)


def entry(name, body=b"", kind=tarfile.REGTYPE, link=""):
    return header(name, len(body), kind, link) + body + b"\0" * ((-len(body)) % 512)


def marked(*entries, tail=b"\0" * 1024):
    return entry(archive.MARKER_NAME, archive.MARKER) + b"".join(entries) + tail


def packed(*entries, tail=b"\0" * 1024):
    return gzip.compress(marked(*entries, tail=tail), mtime=0)


class ArchiveFixtureTests(unittest.TestCase):
    def inspect(self, raw):
        return archive.inspect_invented_archive(raw, digest(raw))

    def reject(self, raw, reason=None):
        with self.assertRaisesRegex(ValueError, reason or ".*"):
            self.inspect(raw)

    def test_valid_inventory_links_and_opaque_members(self):
        raw = packed(
            entry("python/", kind=tarfile.DIRTYPE),
            entry("python/data.csv", b"invented opaque no CSV parse"),
            entry("python/font.ttf", b"invented opaque no font parse"),
            entry("python/alias", kind=tarfile.SYMTYPE, link="data.csv"),
            entry("hard", kind=tarfile.LNKTYPE, link="python/data.csv"),
            entry("python/LICENSE.fixture.txt", b"invented notice only"),
            entry("python/NOTICE.unknown", b"invented unknown notice"),
        )
        report = self.inspect(raw)
        self.assertEqual(report["members"][4]["link_target"], "python/data.csv")
        self.assertEqual(report["unreviewed_notice_names"], ["python/NOTICE.unknown"])
        self.assertEqual(len(report["invented_notice_allowlist_metadata"]), 1)
        self.assertFalse(report["actual_archive_authenticated"])
        self.assertFalse(report["actual_PBS_grammar_qualified"])
        self.assertNotIn("invented notice only", str(report))
        self.assertEqual(
            report["expanded_sha256"],
            digest(
                marked(
                    entry("python/", kind=tarfile.DIRTYPE),
                    entry("python/data.csv", b"invented opaque no CSV parse"),
                    entry("python/font.ttf", b"invented opaque no font parse"),
                    entry("python/alias", kind=tarfile.SYMTYPE, link="data.csv"),
                    entry("hard", kind=tarfile.LNKTYPE, link="python/data.csv"),
                    entry("python/LICENSE.fixture.txt", b"invented notice only"),
                    entry("python/NOTICE.unknown", b"invented unknown notice"),
                )
            ),
        )

    def test_implicit_directory_may_become_explicit(self):
        self.inspect(packed(entry("python/a", b"invented"), entry("python/", kind=tarfile.DIRTYPE)))

    def test_ustar_prefix_join(self):
        name = "p" * 110 + "/invented"
        self.assertEqual(self.inspect(packed(entry(name)))["members"][1]["path"], name)

    def test_missing_wrong_and_displaced_marker(self):
        for raw in (
            gzip.compress(entry("a") + b"\0" * 1024),
            gzip.compress(entry(archive.MARKER_NAME, b"x" * len(archive.MARKER)) + b"\0" * 1024),
            packed(entry(archive.MARKER_NAME, archive.MARKER)),
        ):
            with self.subTest(raw_length=len(raw)):
                self.reject(raw)

    def test_required_held_pin_and_literal_bytes(self):
        raw = packed()
        for value, pin in ((raw, "0" * 64), (bytearray(raw), digest(raw)), (raw, None)):
            with self.subTest(value_type=type(value)):
                with self.assertRaises(ValueError):
                    archive.inspect_invented_archive(value, pin)

    def test_path_rejections(self):
        for name in (
            "/absolute",
            "../escape",
            "x/../escape",
            "./x",
            "x//y",
            "x\\y",
            "C:drive",
            "x\ny",
            "x/",
            "cafe\u0301",
            "/".join(["a"] * 33),
        ):
            with self.subTest(name=name):
                self.reject(packed(entry(name)))

    def test_unicode_control_and_format_metadata_refused(self):
        for char in ("\u0085", "\u202e", "\u2028", "\u2029", "\u200b"):
            with self.subTest(category_char=repr(char)):
                self.reject(packed(entry("a" + char + "b")))
                self.reject(
                    packed(change(header("invented"), 265, ("owner" + char).encode("utf-8")))
                )

    def test_case_duplicate_and_normalized_prefix_collisions(self):
        for first, second in (("a", "a"), ("A", "a"), ("X/a", "x/b"), ("Straße/a", "STRASSE/b")):
            with self.subTest(paths=(first, second)):
                self.reject(packed(entry(first), entry(second)))

    def test_file_prefix_both_orderings(self):
        for entries in ((entry("a"), entry("a/b")), (entry("a/b"), entry("a"))):
            self.reject(packed(*entries))

    def test_links_escape_forward_self_and_chains(self):
        cases = (
            (entry("a", kind=tarfile.SYMTYPE, link="../escape"),),
            (entry("a", kind=tarfile.LNKTYPE, link="/escape"),),
            (entry("a", kind=tarfile.SYMTYPE, link="future"), entry("future")),
            (entry("a", kind=tarfile.SYMTYPE, link="a"),),
            (
                entry("base"),
                entry("a", kind=tarfile.SYMTYPE, link="base"),
                entry("b", kind=tarfile.SYMTYPE, link="a"),
            ),
            (
                entry("base"),
                entry("a", kind=tarfile.LNKTYPE, link="base"),
                entry("b", kind=tarfile.LNKTYPE, link="a"),
            ),
            (entry("dir/", kind=tarfile.DIRTYPE), entry("a", kind=tarfile.LNKTYPE, link="dir")),
        )
        for items in cases:
            with self.subTest(case=len(items)):
                self.reject(packed(*items))

    def test_linked_prefix_both_orderings(self):
        for kind in (tarfile.SYMTYPE, tarfile.LNKTYPE):
            for items in (
                (entry("base"), entry("a", kind=kind, link="base"), entry("a/x")),
                (entry("base"), entry("a/x"), entry("a", kind=kind, link="base")),
            ):
                self.reject(packed(*items))

    def test_unsupported_types(self):
        for kind in (b"x", b"g", b"L", b"K", b"S", b"3", b"4", b"6", b"7", b"D"):
            with self.subTest(kind=kind):
                self.reject(packed(header("invented", kind=kind)))

    def test_checksum_magic_and_reserved_bytes(self):
        good = header("invented")
        for bad in (b"X" + good[1:], change(good, 257, b"ustar "), change(good, 500, b"x")):
            self.reject(packed(bad))

    def test_octal_base256_malformed_and_overflow(self):
        good = header("invented")
        for start, value in (
            (124, b"\x80" + b"\0" * 11),
            (124, b"00000000008\0"),
            (124, b"77777777777\0"),
            (100, b"0007777\0"),
            (108, b"0000\0001\0"),
            (329, b"0000001\0"),
        ):
            with self.subTest(start=start, value=value):
                self.reject(packed(change(good, start, value)))

    def test_nonzero_text_padding_and_invalid_utf8(self):
        good = header("invented")
        for value in (b"a\0b", b"\xff", b"a\x7f"):
            self.reject(packed(change(good, 0, value)))

    def test_nonfile_payload_and_regular_link_refused(self):
        for kind in (tarfile.DIRTYPE, tarfile.SYMTYPE, tarfile.LNKTYPE):
            self.reject(packed(header("a", 1, kind, "base" if kind != tarfile.DIRTYPE else "")))
        self.reject(packed(header("a", link="hidden")))

    def test_tar_end_padding_and_truncation(self):
        for tail in (b"", b"\0" * 512, b"\0" * 512 + b"X" * 512, b"\0" * 1024 + b"X", b"\0" * 1025):
            self.reject(packed(tail=tail))
        bad = header("a", 1) + b"x" + b"Y" + b"\0" * 510
        self.reject(packed(bad))
        self.reject(gzip.compress(marked(header("a", 512) + b"x"), mtime=0))

    def test_gzip_tail_concat_extensions_crc_and_truncation(self):
        raw = packed()
        bad_crc = bytearray(raw)
        bad_crc[-8] ^= 1
        bad_flag = bytearray(raw)
        bad_flag[3] = 8
        for bad in (
            raw + b"\0",
            raw + gzip.compress(b""),
            bytes(bad_crc),
            bytes(bad_flag),
            raw[:-1],
            raw[:20],
        ):
            self.reject(bad)

    def test_compressed_cap_before_inflation(self):
        raw = b"x" * (archive.LIMITS["compressed_bytes"] + 1)
        with patch.object(
            archive.zlib, "decompressobj", side_effect=AssertionError("must not inflate")
        ):
            self.reject(raw, "bounded-invented")

    def test_expansion_bomb_cap(self):
        raw = gzip.compress(marked() + b"\0" * archive.LIMITS["decompressed_bytes"], mtime=0)
        self.reject(raw, "decompressed-byte-cap")

    def test_member_size_and_count_caps(self):
        self.reject(
            packed(header("oversize", archive.LIMITS["member_bytes"] + 1)), "member-mode-or-size"
        )
        self.reject(packed(*(entry(f"a{n}") for n in range(256))), "member-count-cap")

    def test_notice_per_member_and_aggregate_caps(self):
        self.reject(packed(entry("LICENSE.invented", b"x" * (64 * 1024 + 1))), "notice-byte-cap")
        self.reject(
            packed(*(entry(f"NOTICE.invented{n}", b"x" * 50000) for n in range(3))),
            "notice-aggregate-cap",
        )

    def test_inventory_byte_cap(self):
        # Long UTF8 prefix/name paths plus resolved symlink targets enlarge JSON,
        # while all archive bytes remain literal invented buffers under the cap.
        prefix = "é" * 70
        base = "é" * 40
        items = [entry(prefix + "/" + base)]
        for n in range(220):
            items.append(entry(prefix + "/" + "é" * 35 + str(n), kind=tarfile.SYMTYPE, link=base))
        self.reject(packed(*items), "inventory-byte-cap")

    def test_cold_report_without_public_producer(self):
        raw = packed(entry("invented", b"opaque"))
        report_raw = encode(self.inspect(raw))
        with patch.object(
            archive, "inspect_invented_archive", side_effect=AssertionError("producer called")
        ):
            result = archive.inspect_fixture_report(
                report_raw, digest(report_raw), raw, digest(raw)
            )
        self.assertEqual(result["status"], "fixture-metadata-reconstructed")
        self.assertFalse(result["actual_archive_authenticated"])

    def test_rehashed_report_promotions_and_binding_forgeries(self):
        raw = packed(entry("invented", b"opaque"))
        report = self.inspect(raw)
        changes = (
            ("actual_archive_authenticated", True),
            ("actual_archive_inspection_authorized", True),
            ("runtime_use_authorized", True),
            ("extraction_performed", True),
            ("payload_provenance_proved_by_marker", True),
            ("archive_sha256", "0" * 64),
            ("source_identity", {}),
            ("notice_coverage", "complete"),
            ("authority", {"native_execution": True}),
            ("extra", True),
        )
        for key, value in changes:
            mutant = copy.deepcopy(report)
            mutant[key] = value
            encoded = encode(mutant)
            with self.subTest(field=key), self.assertRaisesRegex(ValueError, "cold-fixture"):
                archive.inspect_fixture_report(encoded, digest(encoded), raw, digest(raw))
        mutant = copy.deepcopy(report)
        mutant["members"][1]["payload_sha256"] = "0" * 64
        encoded = encode(mutant)
        with self.assertRaises(ValueError):
            archive.inspect_fixture_report(encoded, digest(encoded), raw, digest(raw))

    def test_cold_external_pin_strict_json_and_source_change(self):
        raw = packed()
        report = encode(self.inspect(raw))
        with self.assertRaises(ValueError):
            archive.inspect_fixture_report(report, "0" * 64, raw, digest(raw))
        malformed = b'{"x":1,"x":2}'
        with self.assertRaises(ValueError):
            archive.inspect_fixture_report(malformed, digest(malformed), raw, digest(raw))
        with patch.object(archive, "_identity", side_effect=({}, {"changed": True})):
            with self.assertRaisesRegex(ValueError, "fixture-source-changed"):
                self.inspect(raw)

    def test_actual_facade_refuses_before_any_argument_or_source_use(self):
        class Poison:
            def __bytes__(self):
                raise AssertionError("argument bytes accessed")

            def __fspath__(self):
                raise AssertionError("path accessed")

        with patch.object(archive, "_identity", side_effect=AssertionError("source read")):
            with self.assertRaises(PermissionError):
                archive.inspect_archive(Poison(), authenticated=True, path=Poison())

    def test_no_extraction_network_or_process(self):
        with (
            patch.object(tarfile.TarFile, "extractall", side_effect=AssertionError("extract")),
            patch("socket.socket", side_effect=AssertionError("network")),
            patch("subprocess.Popen", side_effect=AssertionError("process")),
        ):
            self.inspect(packed(entry("python3", b"invented non executable opaque bytes")))


if __name__ == "__main__":
    unittest.main()
