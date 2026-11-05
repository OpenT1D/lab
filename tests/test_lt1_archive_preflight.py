"""Invented archives challenge passive intake without setup or native execution."""

import gzip
import io
import json
import tarfile
import unittest
from unittest.mock import patch

from experiments.lt1_diagnostic import archive_preflight as preflight


class LT1ArchivePreflightTests(unittest.TestCase):
    def archive(self, entries, *, package_raw=None):
        meta = package_raw or b'{"name":"invented","version":"1.0.0","license":"MIT"}'
        entries = [("package/package.json", meta, tarfile.REGTYPE), *entries]
        stream = io.BytesIO()
        with tarfile.open(fileobj=stream, mode="w") as output:
            for name, payload, kind in entries:
                member = tarfile.TarInfo(name)
                member.type = kind
                member.size = len(payload) if kind == tarfile.REGTYPE else 0
                if kind in {tarfile.SYMTYPE, tarfile.LNKTYPE}:
                    member.linkname = "/outside"
                output.addfile(member, io.BytesIO(payload) if kind == tarfile.REGTYPE else None)
        raw = gzip.compress(stream.getvalue())
        notice = b"invented notice"
        expected = {
            "archive_sha256": preflight.digest(raw),
            "root": "package",
            "name": "invented",
            "version": "1.0.0",
            "declared_license": "MIT",
            "package_json_sha256": preflight.digest(meta),
            "notices": [
                {
                    "path": "package/LICENSE",
                    "bytes": len(notice),
                    "sha256": preflight.digest(notice),
                }
            ],
        }
        return raw, expected

    def inspect(self, entries, **kwargs):
        return preflight.inspect_archive(*self.archive(entries, **kwargs))

    def test_regular_notice_metadata_inventory_and_closed_authority(self):
        result = self.inspect(
            [
                ("package/LICENSE", b"invented notice", tarfile.REGTYPE),
                ("package/lib/", b"", tarfile.DIRTYPE),
                ("package/lib/index.js", b"throw Error('never execute');", tarfile.REGTYPE),
            ]
        )
        self.assertEqual(len(result["files"]), 3)
        self.assertEqual(result["files"]["package/lib/index.js"]["bytes"], 29)
        for key in ("complete_license_closure", "setup_authorized", "execution_authorized"):
            self.assertIs(result[key], False)

    def test_unsafe_paths_links_specials_duplicates_and_collisions_refuse(self):
        good = ("package/LICENSE", b"invented notice", tarfile.REGTYPE)
        for path in (
            "/outside",
            "package/../outside",
            "package/./x",
            "package//x",
            "package\\x",
            "other/x",
        ):
            with self.subTest(path=path), self.assertRaisesRegex(ValueError, "path"):
                self.inspect([good, (path, b"bad", tarfile.REGTYPE)])
        for kind in (tarfile.SYMTYPE, tarfile.LNKTYPE, tarfile.FIFOTYPE, tarfile.CHRTYPE):
            with self.subTest(kind=kind), self.assertRaisesRegex(ValueError, "type"):
                self.inspect([good, ("package/x", b"", kind)])
        for bad in (
            [good, good],
            [
                good,
                ("package/lib", b"x", tarfile.REGTYPE),
                ("package/lib/x", b"y", tarfile.REGTYPE),
            ],
            [
                good,
                ("package/lib/x", b"y", tarfile.REGTYPE),
                ("package/lib", b"x", tarfile.REGTYPE),
            ],
        ):
            with self.subTest(bad=bad), self.assertRaisesRegex(ValueError, "duplicate|collision"):
                self.inspect(bad)

    def test_hash_notice_package_identity_and_duplicate_json_keys_refuse(self):
        raw, expected = self.archive([("package/LICENSE", b"invented notice", tarfile.REGTYPE)])
        for key in ("archive_sha256", "package_json_sha256", "name", "version", "declared_license"):
            with self.subTest(key=key), self.assertRaises(ValueError):
                preflight.inspect_archive(raw, {**expected, key: "wrong"})
        with self.assertRaisesRegex(ValueError, "notice"):
            self.inspect([("package/LICENSE", b"altered notice", tarfile.REGTYPE)])
        with self.assertRaisesRegex(ValueError, "notice"):
            self.inspect([])
        with self.assertRaisesRegex(ValueError, "duplicate metadata"):
            self.inspect([], package_raw=b'{"name":"invented","name":"shadow"}')

    def test_compressed_expanded_file_and_member_bounds_and_truncation(self):
        raw, expected = self.archive([("package/LICENSE", b"invented notice", tarfile.REGTYPE)])
        for name in ("COMPRESSED_LIMIT", "EXPANDED_LIMIT", "MEMBER_LIMIT", "FILE_LIMIT"):
            with (
                self.subTest(name=name),
                patch.object(preflight, name, 1),
                self.assertRaisesRegex(ValueError, "bound|size"),
            ):
                preflight.inspect_archive(raw, expected)
        truncated = raw[:-8]
        with self.assertRaises((EOFError, OSError)):
            preflight.inspect_archive(
                truncated, {**expected, "archive_sha256": preflight.digest(truncated)}
            )

    def test_hidden_gnu_pax_metadata_and_invalid_tar_end_refuse(self):
        raw, expected = self.archive([("package/LICENSE", b"invented notice", tarfile.REGTYPE)])
        base = gzip.decompress(raw)
        for kind in (
            tarfile.GNUTYPE_LONGNAME,
            tarfile.GNUTYPE_LONGLINK,
            tarfile.XHDTYPE,
            tarfile.XGLTYPE,
        ):
            header = tarfile.TarInfo("././@LongLink")
            header.type = kind
            payload = b"package/package.json\0"
            header.size = len(payload)
            extension = (
                header.tobuf(format=tarfile.GNU_FORMAT) + payload + bytes(512 - len(payload))
            )
            altered = gzip.compress(extension * 20 + base)
            with (
                self.subTest(kind=kind),
                patch.object(preflight, "MEMBER_LIMIT", 5),
                self.assertRaisesRegex(ValueError, "type or metadata"),
            ):
                preflight.inspect_archive(
                    altered, {**expected, "archive_sha256": preflight.digest(altered)}
                )
        # A bound/hash alone cannot turn a missing terminator or hidden tail into
        # an inspected archive. Include a valid positive control first.
        self.assertEqual(preflight.inspect_archive(raw, expected)["name"], "invented")
        for expanded in (base.rstrip(b"\0"), base + b"hidden"):
            altered = gzip.compress(expanded)
            with (
                self.subTest(length=len(expanded)),
                self.assertRaises((ValueError, tarfile.TarError)),
            ):
                preflight.inspect_archive(
                    altered, {**expected, "archive_sha256": preflight.digest(altered)}
                )

    def test_recognized_inventory_matches_frozen_lock_and_stays_unadmitted(self):
        from pathlib import Path

        root = Path(__file__).resolve().parents[1]
        inventory = json.loads(
            (root / "experiments/lt1_diagnostic/headless-notices.json").read_bytes()
        )
        lock = (root / "experiments/m0/lt1/package-lock.json").read_bytes()
        self.assertEqual(preflight.digest(lock), inventory["lock_sha256"])
        expected = {p: v for p, v in json.loads(lock)["packages"].items() if p}
        self.assertEqual({p["lock_path"] for p in inventory["packages"]}, set(expected))
        self.assertEqual(sum(len(p["notices"]) for p in inventory["packages"]), 22)
        for item in inventory["packages"]:
            package = expected[item["lock_path"]]
            self.assertEqual(item["version"], package["version"])
            self.assertEqual(item["integrity"], package["integrity"])
            self.assertEqual(item["resolved"], package["resolved"])
            self.assertEqual(item["declared_license"], package["license"])
        self.assertIs(inventory["complete_license_closure"], False)
        self.assertIs(inventory["setup_authorized"], False)
        self.assertIs(inventory["execution_authorized"], False)
