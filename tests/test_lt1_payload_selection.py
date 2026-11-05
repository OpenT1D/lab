"""Invented report selection; no archive code, filesystem staging or runtime."""

import copy
import hashlib
import json
import unittest
from pathlib import Path

from experiments.lt1_diagnostic.payload_selection import select_payload


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode()


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


class LT1PayloadSelectionTests(unittest.TestCase):
    def setUp(self):
        files = {
            "package/LICENSE": {"bytes": 7, "sha256": "1" * 64},
            "package/main.js": {"bytes": 11, "sha256": "2" * 64},
            "package/browser.js": {"bytes": 13, "sha256": "3" * 64},
        }
        package = {
            "name": "invented",
            "version": "1.0.0",
            "archive_sha256": "a" * 64,
            "root": "package",
            "lock_path": "node_modules/invented",
            "declared_license": "MIT",
            "notices": [{"path": "package/LICENSE", **files["package/LICENSE"]}],
        }
        self.inventory = {"lock_sha256": "b" * 64, "packages": [package]}
        self.reports = [
            {
                "schema": "opent1d.lt1-package-preflight/1",
                "archive_sha256": "a" * 64,
                "name": "invented",
                "version": "1.0.0",
                "declared_license": "MIT",
                "files": files,
                "recognized_notices": package["notices"],
                "setup_authorized": False,
                "execution_authorized": False,
            }
        ]
        prefix = "toolchain/node_modules/invented/"
        self.mapped = {
            prefix + path.removeprefix("package/"): value for path, value in files.items()
        }
        self.notices = {prefix + "LICENSE": files["package/LICENSE"]}
        self.selected = {k: v for k, v in self.mapped.items() if k != prefix + "browser.js"}
        self.profile = {
            "schema": "opent1d.lt1-headless-selection-proposal/1",
            "profile": "invented-proposal/1",
            "notice_inventory_sha256": sha(canonical(self.inventory)),
            "historical_lock_sha256": "b" * 64,
            "packages": [
                {k: package[k] for k in ("name", "version", "archive_sha256", "root", "lock_path")}
                | {"files": 3, "payload_bytes": 31, "filemap_sha256": sha(canonical(self.mapped))}
            ],
            "source_files": 3,
            "source_payload_bytes": 31,
            "source_filemap_sha256": sha(canonical(self.mapped)),
            "excluded": {"path": prefix + "browser.js", **files["package/browser.js"]},
            "selected_files": 2,
            "selected_payload_bytes": 18,
            "selected_filemap_sha256": sha(canonical(self.selected)),
            "recognized_notice_files": 1,
            "retained_notice_filemap_sha256": sha(canonical(self.notices)),
            "complete_remaining_embedded_license_closure": False,
            "functional_loader_qualification": "unrun",
            "setup_authorized": False,
            "execution_authorized": False,
        }

    def select(self, reports=None, profile=None):
        raw = canonical(self.profile if profile is None else profile)
        return select_payload(
            self.reports if reports is None else reports, canonical(self.inventory), raw, sha(raw)
        )

    def test_exact_selection_retains_notices_and_closed_authority_without_mutating_inputs(self):
        before = copy.deepcopy(self.reports)
        result = self.select()
        self.assertEqual(result["files"], self.selected)
        self.assertEqual(result["retained_notices"], self.notices)
        self.assertEqual(self.reports, before)
        for key in (
            "setup_authorized",
            "execution_authorized",
            "complete_remaining_embedded_license_closure",
        ):
            self.assertIs(result[key], False)
        result["files"]["toolchain/node_modules/invented/main.js"]["bytes"] = 99
        self.assertEqual(self.reports, before)

    def test_stale_profile_inventory_and_report_content_refuse(self):
        raw = canonical(self.profile)
        with self.assertRaisesRegex(ValueError, "profile bytes"):
            select_payload(self.reports, canonical(self.inventory), raw + b" ", sha(raw))
        with self.assertRaisesRegex(ValueError, "inventory bytes"):
            select_payload(self.reports, canonical(self.inventory) + b" ", raw, sha(raw))
        for mutate in (
            lambda r: r[0]["files"]["package/main.js"].update(sha256="4" * 64),
            lambda r: r[0]["files"].update({"package/extra.js": {"bytes": 1, "sha256": "4" * 64}}),
            lambda r: r[0]["files"].update(
                {"package/../outside": {"bytes": 1, "sha256": "4" * 64}}
            ),
            lambda r: r[0]["recognized_notices"].clear(),
            lambda r: r[0].update(version="2.0.0"),
        ):
            altered = copy.deepcopy(self.reports)
            mutate(altered)
            with self.subTest(mutate=mutate), self.assertRaises(ValueError):
                self.select(altered)

    def test_missing_duplicate_and_substituted_package_refuse(self):
        for reports in ([], self.reports * 2, [{**self.reports[0], "archive_sha256": "c" * 64}]):
            with self.subTest(reports=reports), self.assertRaises(ValueError):
                self.select(reports)

    def test_exclusion_notice_and_promotion_counterexamples_refuse(self):
        for mutate in (
            lambda p: p["excluded"].update(path="toolchain/node_modules/invented/LICENSE"),
            lambda p: p["excluded"].update(sha256="4" * 64),
            lambda p: p.update(selected_filemap_sha256="4" * 64),
            lambda p: p.update(retained_notice_filemap_sha256="4" * 64),
            lambda p: p.update(setup_authorized=True),
            lambda p: p.update(complete_remaining_embedded_license_closure=True),
            lambda p: p.update(functional_loader_qualification="passed"),
        ):
            altered = copy.deepcopy(self.profile)
            mutate(altered)
            with self.subTest(mutate=mutate), self.assertRaises(ValueError):
                self.select(profile=altered)

    def test_real_profile_binds_original_inventory_and_keeps_all_limits_explicit(self):
        root = Path(__file__).resolve().parents[1] / "experiments/lt1_diagnostic"
        profile = json.loads((root / "headless-selection.json").read_bytes())
        inventory = (root / "headless-notices.json").read_bytes()
        self.assertEqual(profile["notice_inventory_sha256"], sha(inventory))
        self.assertEqual(
            {p["archive_sha256"] for p in profile["packages"]},
            {p["archive_sha256"] for p in json.loads(inventory)["packages"]},
        )
        self.assertEqual(len(profile["packages"]), 20)
        self.assertEqual(profile["source_files"] - profile["selected_files"], 1)
        self.assertEqual(
            profile["source_payload_bytes"] - profile["selected_payload_bytes"],
            profile["excluded"]["bytes"],
        )
        self.assertEqual(profile["recognized_notice_files"], 22)
        self.assertIs(profile["setup_authorized"], False)
        self.assertIs(profile["execution_authorized"], False)
