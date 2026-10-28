"""Reviewed runtime context must retain every historical output requirement."""

import copy
import json
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from experiments.m0.simglucose import runtime_context as context
from experiments.m1.historical import check_record


class RuntimeBaselineExtensionTests(unittest.TestCase):
    def setUp(self):
        self.review, self.canonical, _ = context.reviewed_extension()
        self.baseline = self.canonical["m1"]
        self.old = self.review["historical_lock_sha256"]
        self.current = self.review["current_lock_sha256"]

    def observed(self, *, extended=True, collection=0):
        source = self.baseline["collections"][collection]["outputs_sha256"]
        result = {
            name: copy.deepcopy(self.baseline["shared"] | case | source[name])
            for name, case in self.baseline["cases"].items()
        }
        if extended:
            for case in result.values():
                case["lock_sha256"] = self.current
                case["packages"] = copy.deepcopy(self.review["packages"])
        return result

    def project(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        root = Path(temporary.name)
        paths = list(context.BASELINES.values()) + [
            "experiments/m0/simglucose/uv.lock",
            "experiments/m0/simglucose/runtime-context/legacy-uv.lock",
            "experiments/m0/simglucose/runtime-context/review.json",
        ]
        for name in paths:
            target = root / name
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(context.ROOT / name, target)
        return root

    def test_original_and_extended_collections_are_distinguished_without_mutation(self):
        original = copy.deepcopy(self.baseline)
        legacy = check_record(self.observed(extended=False), self.baseline)
        reviewed = check_record(self.observed(), self.baseline)
        self.assertNotIn("runtime_extension", legacy)
        self.assertTrue(reviewed["matched"])
        self.assertFalse(reviewed["tolerance_applied"])
        self.assertEqual(reviewed["runtime_extension"]["actual_lock_sha256"], self.current)
        self.assertEqual(reviewed["runtime_extension"]["historical_lock_sha256"], self.old)
        self.assertEqual(self.baseline, original)

    def test_m0_extension_retains_all_original_fields_and_declares_full_inventory(self):
        baseline = self.canonical["m0"]
        for platform, original in baseline["environments"].items():
            with self.subTest(platform=platform):
                expected, evidence = context.expected_context(
                    "m0",
                    baseline,
                    self.current,
                    platform_key=platform,
                    actual_packages=self.review["m0_packages"],
                )
                self.assertEqual(
                    expected | {"lock_sha256": self.old},
                    original | {"packages": self.review["m0_packages"]},
                )
                self.assertEqual(evidence["added_packages"], {"glucosim": "0.1.2"})

    def test_unknown_and_mixed_locks_are_rejected(self):
        observed = self.observed()
        for case in observed.values():
            case["lock_sha256"] = "0" * 64
        with self.assertRaisesRegex(ValueError, "lock_sha256"):
            check_record(observed, self.baseline)
        observed = self.observed()
        next(iter(observed.values()))["lock_sha256"] = self.old
        with self.assertRaisesRegex(ValueError, "locks differ"):
            check_record(observed, self.baseline)

    def test_extra_changed_or_missing_package_versions_are_rejected(self):
        for name, version in (
            ("unreviewed", "1.0"),
            ("glucosim", "9.0"),
            ("numpy", "9.0"),
            ("setuptools", "83.0.0"),
            ("glucosim", None),
        ):
            with self.subTest(name=name, version=version):
                observed = self.observed()
                packages = next(iter(observed.values()))["packages"]
                if version is None:
                    packages.pop(name)
                else:
                    packages[name] = version
                with self.assertRaisesRegex(ValueError, "packages"):
                    check_record(observed, self.baseline)

    def test_wrong_output_or_changed_scenario_remains_rejected_in_new_context(self):
        for field, value in (
            ("trace_sha256", "0" * 64),
            ("initial_sha256", "0" * 64),
            ("config", {}),
            ("effective_settings", {}),
        ):
            with self.subTest(field=field):
                observed = self.observed()
                next(iter(observed.values()))[field] = value
                with self.assertRaises(ValueError):
                    check_record(observed, self.baseline)

    def test_historical_collections_cannot_be_mixed_under_new_runtime(self):
        first, second = self.observed(collection=0), self.observed(collection=1)
        differences = [key for key in first if first[key] != second[key]]
        self.assertGreater(len(differences), 1)
        first[differences[0]] = second[differences[0]]
        with self.assertRaisesRegex(ValueError, "trajectories differ"):
            check_record(first, self.baseline)

    def test_modified_lock_or_baseline_bytes_fail_closed(self):
        for name in (
            "experiments/m0/simglucose/uv.lock",
            "experiments/m0/simglucose/runtime-context/legacy-uv.lock",
            "experiments/m1/baseline.json",
            "experiments/m0/simglucose/baseline.json",
        ):
            with self.subTest(path=name):
                root = self.project()
                target = root / name
                target.write_bytes(target.read_bytes() + b"\n")
                with patch.object(context, "ROOT", root), self.assertRaises(ValueError):
                    context.reviewed_extension()

    def test_rehashing_an_existing_dependency_change_does_not_approve_it(self):
        root = self.project()
        lock = root / "experiments/m0/simglucose/uv.lock"
        content = lock.read_text()
        self.assertIn('version = "1.26.4"', content)
        lock.write_text(content.replace('version = "1.26.4"', 'version = "1.26.5"'))
        review_path = root / "experiments/m0/simglucose/runtime-context/review.json"
        review = json.loads(review_path.read_text())
        review["current_lock_sha256"] = context.digest(lock.read_bytes())
        review["m0_packages"]["numpy"] = "1.26.5"
        review_path.write_text(json.dumps(review))
        with (
            patch.object(context, "ROOT", root),
            self.assertRaisesRegex(ValueError, "existing locked dependencies"),
        ):
            context.reviewed_extension()

    def test_changed_supplied_baseline_cannot_borrow_the_extension(self):
        baseline = copy.deepcopy(self.baseline)
        baseline["shared"]["protocol_sha256"] = "0" * 64
        with self.assertRaisesRegex(ValueError, "no reviewed extension"):
            context.expected_context("m1", baseline, self.current)

    def test_m0_inventory_cannot_claim_changed_core_versions(self):
        root = self.project()
        path = root / "experiments/m0/simglucose/runtime-context/review.json"
        review = json.loads(path.read_text())
        review["m0_packages"]["numpy"] = "9.0"
        path.write_text(json.dumps(review))
        with (
            patch.object(context, "ROOT", root),
            self.assertRaisesRegex(ValueError, "M0 package inventory"),
        ):
            context.reviewed_extension()

    def test_m0_raw_and_legacy_vendored_inventories_are_whole_and_exact(self):
        baseline = self.canonical["m0"]
        platform = next(iter(baseline["environments"]))
        for packages in (self.review["m0_packages"], self.review["packages"]):
            expected, _ = context.expected_context(
                "m0", baseline, self.current, platform_key=platform, actual_packages=packages
            )
            self.assertEqual(expected["packages"], packages)
        wrong = self.review["m0_packages"] | {"unreviewed": "1.0"}
        with self.assertRaisesRegex(ValueError, "packages"):
            context.expected_context(
                "m0", baseline, self.current, platform_key=platform, actual_packages=wrong
            )
        wrong = copy.deepcopy(self.review["m0_packages"])
        wrong.pop("glucosim")
        with self.assertRaisesRegex(ValueError, "packages"):
            context.expected_context(
                "m0", baseline, self.current, platform_key=platform, actual_packages=wrong
            )

    def test_m0_review_cannot_omit_or_duplicate_locked_distributions(self):
        for change in ("omit", "duplicate"):
            with self.subTest(change=change):
                root = self.project()
                path = root / "experiments/m0/simglucose/runtime-context/review.json"
                review = json.loads(path.read_text())
                if change == "omit":
                    review["m0_packages"].pop("numpy")
                else:
                    review["m0_packages"]["NumPy"] = review["m0_packages"]["numpy"]
                path.write_text(json.dumps(review))
                with (
                    patch.object(context, "ROOT", root),
                    self.assertRaisesRegex(ValueError, "complete lock"),
                ):
                    context.reviewed_extension()
