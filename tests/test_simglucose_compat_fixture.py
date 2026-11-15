"""Fictional resource bytes and import-only compatibility, no native imports."""

import builtins
import copy
import unittest
from unittest.mock import patch

from experiments.simglucose_audit import compat_fixture as compat
from experiments.simglucose_audit.contract import digest, encode


class SimglucoseCompatFixtureTests(unittest.TestCase):
    def test_exact_invented_resources_and_cold_reader_remain_blocked(self):
        buffers = compat.fixed_resource_buffers()
        metadata = encode(compat.default_metadata())
        report = compat.run_compat_fixture(buffers, metadata)
        raw = encode(report)
        checked = compat.inspect_compat_report(
            raw, digest(raw), buffers, metadata, digest(metadata)
        )
        self.assertEqual(checked["status"], "blocked")
        self.assertEqual(len(report["resources"]), 3)
        self.assertFalse(report["actual_resources_opened"])
        self.assertFalse(report["real_import_effects_observed"])
        self.assertFalse(report["authority"]["asset_use_approved"])

    def test_extra_quest_absolute_parent_and_nonbyte_buffers_refused(self):
        buffers = compat.fixed_resource_buffers()
        for label in (
            "Quest.csv",
            "/params/pump_params.csv",
            "../params/pump_params.csv",
            "params/extra.csv",
        ):
            with self.subTest(label=label), self.assertRaises(ValueError):
                compat.run_compat_fixture(buffers | {label: b"invented"})
        for replacement in (
            "/never/open/asset.csv",
            b"changed-invented-bytes",
            memoryview(b"invented"),
        ):
            changed = buffers | {"params/pump_params.csv": replacement}
            with self.assertRaises(ValueError):
                compat.run_compat_fixture(changed)

    def test_symlink_claim_order_extra_and_duplicate_metadata_refused(self):
        buffers = compat.fixed_resource_buffers()
        original = compat.default_metadata()
        for field, value in (
            ("symlink", True),
            ("label", "../escape"),
            ("kind", "actual-asset"),
            ("sha256", "0" * 64),
            ("bytes", True),
            ("source_file", "/never/open"),
        ):
            metadata = copy.deepcopy(original)
            metadata["resources"][0][field] = value
            with self.subTest(field=field), self.assertRaises(ValueError):
                compat.run_compat_fixture(buffers, encode(metadata))
        reversed_metadata = copy.deepcopy(original)
        reversed_metadata["resources"].reverse()
        with self.assertRaises(ValueError):
            compat.run_compat_fixture(buffers, encode(reversed_metadata))
        for raw in (b'{"schema":1,"schema":2}', b'{"x":NaN}'):
            with self.assertRaises(ValueError):
                compat.run_compat_fixture(buffers, raw)

    def test_entrypoint_parse_and_load_refuse_before_argument_use(self):
        class Poison:
            def __str__(self):
                raise AssertionError("argument inspected")

            def __fspath__(self):
                raise AssertionError("path followed")

        for method in (
            compat.EntryPoint.parse,
            compat.EntryPoint.load,
            compat.EntryPoint().parse,
            compat.EntryPoint().load,
        ):
            with self.assertRaises(PermissionError):
                method(Poison(), path=Poison())

    def test_rehashed_authority_resource_and_source_forgery_refused(self):
        buffers, metadata = compat.fixed_resource_buffers(), encode(compat.default_metadata())
        report = compat.run_compat_fixture(buffers, metadata)
        for field, value in (
            ("status", "completed"),
            ("source_identity", {}),
            ("native_acceptance", True),
            ("resources", []),
            ("authority", report["authority"] | {"setup_authorized": True}),
        ):
            changed = report | {field: value}
            raw = encode(changed)
            with self.subTest(field=field), self.assertRaises(ValueError):
                compat.inspect_compat_report(raw, digest(raw), buffers, metadata, digest(metadata))
        with self.assertRaisesRegex(ValueError, "byte-pins"):
            compat.inspect_compat_report(
                encode(report), "0" * 64, buffers, metadata, digest(metadata)
            )

    def test_no_real_compatibility_or_engine_dependency_imports(self):
        real_import = builtins.__import__

        def guard(name, *args, **kwargs):
            if name.split(".")[0] in {
                "pkg_resources",
                "_distutils_hack",
                "simglucose",
                "gym",
                "numpy",
                "matplotlib",
            }:
                raise AssertionError("real dependency import")
            return real_import(name, *args, **kwargs)

        with patch("builtins.__import__", side_effect=guard):
            report = compat.run_compat_fixture(compat.fixed_resource_buffers())
            self.assertEqual(report["status"], "blocked")
            with self.assertRaises(PermissionError):
                compat.EntryPoint.parse("invented:target")


if __name__ == "__main__":
    unittest.main()
