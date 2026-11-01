"""Shard scheduling preserves discovery, fixtures, failures and new modules."""

import collections
import io
import json
import tempfile
import types
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts import check, root_tests


class RootPartitionTests(unittest.TestCase):
    def suite(self):
        modules = []
        for number in range(7):
            kind = type("Cases", (unittest.TestCase,), {"__module__": f"test_module_{number}"})
            modules.append(unittest.TestSuite([kind("runTest") for _ in range(number + 1)]))
        return unittest.TestSuite(modules)

    def test_every_discovered_occurrence_is_selected_exactly_once_in_original_order(self):
        original = self.suite()
        expected = root_tests.identities(original)
        selected = []
        for index in range(1, 5):
            suite = root_tests.partition(original, index, 4, {"test_module_0": 1000})
            names = root_tests.identities(suite)
            selected += names
            self.assertEqual(names, [name for name in expected if name in names])
        self.assertEqual(collections.Counter(selected), collections.Counter(expected))
        self.assertEqual(root_tests.identities(original), expected)
        self.assertEqual(len(selected), 28)  # Repeated IDs must not be deduplicated.

    def test_new_modules_are_not_excluded_by_old_timing_weights(self):
        original = self.suite()
        for weights in ({}, {"removed_module": 9999}, {"test_module_1": 0.001}):
            selected = [
                name
                for i in range(1, 4)
                for name in root_tests.identities(root_tests.partition(original, i, 3, weights))
            ]
            self.assertCountEqual(selected, root_tests.identities(original))

    def test_invalid_and_empty_shards_are_rejected(self):
        for index, total in ((0, 4), (5, 4), (1, 0), (1, 17), (2, 1)):
            with self.subTest(index=index, total=total), self.assertRaises(ValueError):
                root_tests.partition(self.suite(), index, total, {})
        with self.assertRaisesRegex(ValueError, "Empty"):
            root_tests.partition(unittest.TestSuite(), 1, 1, {})

    def test_discovery_import_errors_fail_before_any_partition(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "tests").mkdir()
            (root / "tests/test_broken_ci_fixture.py").write_text("raise ImportError('CONTROL')\n")
            with self.assertRaisesRegex(ValueError, "CONTROL"):
                root_tests.discover(root)

    def test_whole_module_selection_keeps_class_and_module_fixture_lifecycle(self):
        calls = []
        module = types.ModuleType("test_shard_fixture")
        module.setUpModule = lambda: calls.append("module setup")
        module.tearDownModule = lambda: calls.append("module cleanup")

        class Cases(unittest.TestCase):
            @classmethod
            def setUpClass(cls):
                calls.append("class setup")
                cls.addClassCleanup(lambda: calls.append("class cleanup"))

            def test_a(self):
                calls.append("a")

            def test_b(self):
                calls.append("b")

        Cases.__module__ = module.__name__
        with patch.dict(root_tests.sys.modules, {module.__name__: module}):
            suite = unittest.defaultTestLoader.loadTestsFromTestCase(Cases)
            selected = root_tests.partition(suite, 1, 1, {})
            result = unittest.TextTestRunner(stream=io.StringIO()).run(selected)
        self.assertTrue(result.wasSuccessful())
        self.assertEqual(
            calls, ["module setup", "class setup", "a", "b", "class cleanup", "module cleanup"]
        )

    def test_actual_repository_discovery_multiset_is_complete_across_four_shards(self):
        suite = root_tests.discover()
        weights = json.loads((root_tests.ROOT / "tests/root-test-timings.json").read_text())[
            "module_seconds"
        ]
        all_ids = root_tests.identities(suite)
        selected = []
        modules = []
        for index in range(1, 5):
            shard = root_tests.partition(suite, index, 4, weights)
            selected.extend(root_tests.identities(shard))
            modules.append({case.__class__.__module__ for case in root_tests.cases(shard)})
        self.assertCountEqual(selected, all_ids)
        for i in range(4):
            for j in range(i):
                self.assertFalse(modules[i] & modules[j])

    def test_shard_argument_cannot_silently_limit_the_default_full_check(self):
        with patch.object(check, "check_tests") as execute, self.assertRaises(SystemExit):
            check.main(["--test-shard", "1/4"])
        execute.assert_not_called()

    def test_assertion_failure_produces_a_failed_receipt_and_nonzero_outcome(self):
        class Fails(unittest.TestCase):
            def test_failure(self):
                self.fail("CONTROL ASSERTION")

        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary) / "receipt.json"
            with patch.object(
                root_tests, "discover", return_value=unittest.TestSuite([Fails("test_failure")])
            ):
                self.assertEqual(root_tests.main(["--output", str(output)]), 1)
            receipt = json.loads(output.read_text())
        self.assertTrue(receipt["completed"])
        self.assertFalse(receipt["passed"])
        self.assertEqual(receipt["tests_run"], 1)
        self.assertEqual(len(receipt["failures"]), 1)

    def test_discovery_error_replaces_previous_successful_receipt(self):
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary) / "receipt.json"
            output.write_text('{"passed":true,"completed":true}')
            with patch.object(
                root_tests, "discover", side_effect=ValueError("CONTROL IMPORT FAILURE")
            ):
                self.assertEqual(root_tests.main(["--output", str(output)]), 2)
            receipt = json.loads(output.read_text())
        self.assertFalse(receipt["passed"])
        self.assertFalse(receipt["completed"])
        self.assertIn("CONTROL IMPORT FAILURE", receipt["error"])
        self.assertEqual(receipt["phase"], "discovery")

    def test_early_result_stop_cannot_pass_with_unrun_selected_cases(self):
        class Stops(unittest.TestCase):
            def runTest(self):
                pass

            def run(self, result):
                super().run(result)
                result.stop()

        suite = unittest.TestSuite([Stops(), Stops()])
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary) / "receipt.json"
            with patch.object(root_tests, "discover", return_value=suite):
                self.assertEqual(root_tests.main(["--output", str(output)]), 1)
            receipt = json.loads(output.read_text())
        self.assertEqual(len(receipt["selected"]), 2)
        self.assertEqual(receipt["tests_run"], 1)
        self.assertFalse(receipt["completed"])
        self.assertFalse(receipt["passed"])

    def test_optional_class_and_module_fixture_skips_are_explicit_complete_accounting(self):
        for fixture in ("class", "module"):
            module = types.ModuleType("test_root_optional_fixture")

            class Optional(unittest.TestCase):
                def test_a(self):
                    self.fail("Skipped optional fixture must not execute")

                def test_b(self):
                    self.fail("Skipped optional fixture must not execute")

            def unavailable():
                raise unittest.SkipTest("CONTROL OPTIONAL TOOLING")

            Optional.__module__ = module.__name__
            if fixture == "class":
                Optional.setUpClass = staticmethod(unavailable)
            else:
                module.setUpModule = unavailable
            suite = unittest.defaultTestLoader.loadTestsFromTestCase(Optional)
            with tempfile.TemporaryDirectory() as temporary:
                output = Path(temporary) / "receipt.json"
                with (
                    self.subTest(fixture=fixture),
                    patch.dict(root_tests.sys.modules, {module.__name__: module}),
                    patch.object(root_tests, "discover", return_value=suite),
                ):
                    self.assertEqual(root_tests.main(["--output", str(output)]), 0)
                receipt = json.loads(output.read_text())
            self.assertTrue(receipt["passed"])
            self.assertTrue(receipt["completed"])
            self.assertEqual(receipt["tests_run"], 0)
            self.assertEqual(len(receipt["fixture_skipped"]), 2)
            self.assertEqual(len(receipt["skipped"]), 1)
            self.assertEqual(
                {row["reason"] for row in receipt["fixture_skipped"]},
                {"CONTROL OPTIONAL TOOLING"},
            )


if __name__ == "__main__":
    unittest.main()
