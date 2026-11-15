"""Invented source/lock syntax only; no simulator or third-party import."""

import copy
import unittest
from unittest.mock import patch

from experiments.simglucose_audit import runtime_sources as scope
from experiments.simglucose_audit.contract import digest, source_contract, source_identity

LOCK = b"""version = 1
requires-python = ">=3.12,<3.13"
[[package]]
name = "fixture-project"
version = "0"
source = {virtual = "."}
dependencies = [{name = "numpy"}, {name = "pathos", marker = "sys_platform == 'win32'"}]
[[package]]
name = "numpy"
version = "1.0"
source = {registry = "https://invalid.example/simple"}
wheels = [{url = "https://invalid.example/never-read.whl", hash = "sha256:invented", size = 7}]
[[package]]
name = "pathos"
version = "0.1"
source = {registry = "https://invalid.example/simple"}
"""


class SimglucoseRuntimeSourcesTests(unittest.TestCase):
    def test_empty_package_initializers_are_real_source_members(self):
        value = scope.analyze_python("invented", True, b"")
        self.assertEqual((value["bytes"], value["sha256"]), (0, digest(b"")))
        self.assertTrue(value["package_initializer"])
        self.assertEqual(value["imports"], [])

    def test_source_is_parsed_and_never_executed(self):
        raw = (
            b"raise AssertionError('executed')\n"
            b"__import__('forbidden_native')\nexec('raise Exception()')"
        )
        value = scope.analyze_python("invented", False, raw)
        self.assertEqual(
            [c["target_syntax"] for c in value["sensitive_call_syntax"]], ["__import__", "exec"]
        )
        self.assertFalse(value["source_executed"])
        self.assertFalse(value["dynamic_or_alias_effects_resolved"])

    def test_demo_conditional_and_optional_imports_are_never_pruned(self):
        raw = b"""import matplotlib.pyplot
if __name__ == "__main__":
    import matplotlib.dates
try:
    from rllab.envs.base import Step
except ImportError:
    from collections import namedtuple
if False:
    import pathos
"""
        value = scope.analyze_python("invented", False, raw)
        imports = value["imports"]
        self.assertEqual(
            [i["module"] for i in imports],
            ["matplotlib.pyplot", "matplotlib.dates", "rllab.envs.base", "collections", "pathos"],
        )
        self.assertEqual(imports[0]["context"], [])
        self.assertEqual(imports[1]["context"][0]["field"], "body")
        self.assertEqual(imports[2]["context"][0]["node"], "Try")
        self.assertEqual(imports[3]["context"][-1]["exception_syntax"], "ImportError")
        self.assertEqual(imports[-1]["context"][0]["test_syntax"], "False")

    def test_class_body_decorator_defaults_and_function_body_remain_lexical(self):
        raw = b"""class C:
    import numpy
@__import__("decorator")
def f(value=__import__("default")):
    import scipy
"""
        value = scope.analyze_python("invented", False, raw)
        self.assertEqual(
            value["imports"][0]["context"][0], {"node": "ClassDef", "field": "body", "line": 1}
        )
        self.assertEqual(value["imports"][1]["context"][0]["field"], "body")
        self.assertEqual(
            {c["context"][0]["field"] for c in value["sensitive_call_syntax"]},
            {"decorator_list", "args"},
        )
        self.assertFalse(value["execution_order_inferred"])

    def test_relative_imports_preserve_package_and_parent_meaning(self):
        self.assertEqual(
            scope.analyze_python("p.child.mod", False, b"from .base import B")["imports"][0][
                "module"
            ],
            "p.child.base",
        )
        self.assertEqual(
            scope.analyze_python("p.child", True, b"from . import base")["imports"][0]["module"],
            "p.child",
        )
        self.assertEqual(
            scope.analyze_python("p.child.mod", False, b"from .. import base")["imports"][0][
                "module"
            ],
            "p",
        )
        with self.assertRaisesRegex(ValueError, "relative-import-outside-package"):
            scope.analyze_python("p.mod", False, b"from ..outside import B")

    def test_resource_and_entrypoint_calls_are_syntax_never_path_or_import_intake(self):
        raw = b"""p = pkg_resources.resource_filename("simglucose", "params/Quest.csv")
q = pkg_resources.resource_filename(package, path)
EntryPoint.parse("evil = forbidden.module:run").load()
"""
        with patch("builtins.open", side_effect=AssertionError("path followed")):
            value = scope.analyze_python("invented", False, raw)
        calls = value["sensitive_call_syntax"]
        self.assertEqual(calls[0]["positional_literals"], ["simglucose", "params/Quest.csv"])
        self.assertEqual(calls[1]["positional_literals"], [None, None])
        self.assertFalse(calls[1]["all_positional_arguments_string_literals"])
        self.assertIn("EntryPoint.parse", [c["target_syntax"] for c in calls])

    def test_invalid_source_and_byte_bounds_refuse(self):
        for bad in ("import os", bytearray(b"pass"), b" " * (1024 * 1024 + 1)):
            with self.assertRaisesRegex(ValueError, "bounded-source-bytes"):
                scope.analyze_python("invented", False, bad)
        with self.assertRaises(SyntaxError):
            scope.analyze_python("invented", False, b"not valid python !!!")

    def test_lock_inventory_retains_marked_edges_and_unread_artifacts(self):
        with patch("builtins.open", side_effect=AssertionError("artifact followed")):
            value = scope.analyze_lock(LOCK)
        self.assertEqual((value["nonvirtual_packages"], value["virtual_projects"]), (2, 1))
        root = value["packages"][0]
        self.assertEqual(root["dependencies"][1]["marker"], "sys_platform == 'win32'")
        self.assertEqual(value["packages"][1]["declared_wheels"], 1)
        for key in (
            "markers_or_extras_evaluated",
            "packages_pruned",
            "lock_resolved",
            "artifact_selected_or_read",
        ):
            self.assertFalse(value[key])

    def test_lock_ambiguity_dangling_and_wrong_version_refuse(self):
        variants = [
            (
                LOCK + b'\n[[package]]\nname="NumPy"\nversion="9"\nsource={registry="x"}',
                "unique-lock-packages",
            ),
            (LOCK.replace(b'{name = "numpy"}', b'{name = "missing"}'), "lock-edge-target"),
            (
                LOCK.replace(b'{name = "numpy"}', b'{name = "numpy", version = "9"}'),
                "lock-edge-identity",
            ),
            (
                LOCK.replace(
                    b'name = "numpy"\nversion',
                    b'optional-dependencies = {test = []}\nname = "numpy"\nversion',
                ),
                "unsupported-lock-package-fields",
            ),
        ]
        for raw, reason in variants:
            with self.subTest(reason=reason), self.assertRaisesRegex(ValueError, reason):
                scope.analyze_lock(raw)

    def test_fixed_source_membership_and_pins_before_ast_or_lock_parser(self):
        contract = source_contract()
        buffers = {r["upstream_path"]: b"invented wrong source" for r in contract["code"]}
        with (
            patch("ast.parse", side_effect=AssertionError("parser reached")),
            patch("tomllib.loads", side_effect=AssertionError("TOML reached")),
        ):
            with self.assertRaisesRegex(ValueError, "exact-selected-source-buffers"):
                scope.inspect_runtime_sources({}, LOCK, LOCK)
            with self.assertRaisesRegex(ValueError, "source-byte-pin"):
                scope.inspect_runtime_sources(buffers, LOCK, LOCK)

    def test_lock_pin_before_any_parser_with_empty_invented_bound_sources(self):
        contract = copy.deepcopy(source_contract())
        for r in contract["code"]:
            r["bytes"], r["sha256"] = 0, digest(b"")
        buffers = {r["upstream_path"]: b"" for r in contract["code"]}
        # Only the test replaces trusted policy. Production never accepts supplied policy.
        with (
            patch.object(scope, "source_contract", return_value=contract),
            patch("ast.parse", side_effect=AssertionError("parser reached")),
        ):
            with self.assertRaisesRegex(ValueError, "predecessor-lock-pin"):
                scope.inspect_runtime_sources(buffers, LOCK, LOCK)

    def test_reader_refuses_external_pin_before_input_or_reconstruction(self):
        with patch.object(
            scope, "inspect_runtime_sources", side_effect=AssertionError("reconstruct reached")
        ):
            with self.assertRaisesRegex(ValueError, "external-runtime-report-pin"):
                scope.inspect_runtime_report(b"{}", "0" * 64, {}, b"", b"")

    def test_source_identity_now_binds_passive_inspector(self):
        self.assertIn("runtime_sources.py", source_identity())
        self.assertEqual(scope.AUTHORITY["native_execution_deferred"], True)
        self.assertTrue(
            all(v is False for k, v in scope.AUTHORITY.items() if k != "native_execution_deferred")
        )


if __name__ == "__main__":
    unittest.main()
