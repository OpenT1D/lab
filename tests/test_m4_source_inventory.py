"""Source admission stays fresh without eager inventory work in every worker."""

import importlib.util
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from experiments.m4.initial_load import common as inherited
from experiments.m4.secure_study import common
from experiments.m4.secure_study.adapter import activate


class SourceInventoryTests(unittest.TestCase):
    def test_worker_common_import_does_not_enumerate_sources(self):
        spec = importlib.util.spec_from_file_location(
            "experiments.m4.secure_study._inventory_import_test", common.__file__
        )
        module = importlib.util.module_from_spec(spec)
        with patch.object(
            inherited, "source_roots", side_effect=AssertionError("enumerated")
        ) as discover:
            spec.loader.exec_module(module)
            discover.assert_not_called()
            self.assertIs(module.INHERITED_SOURCE_ROOTS, discover)
            with self.assertRaisesRegex(AssertionError, "enumerated"):
                module.source_paths()

    def test_adapter_uses_original_discovery_without_recursion_or_scope_loss(self):
        expected = common.source_paths()
        self.assertIn("experiments/platform_files.py", expected)
        self.assertIn("experiments/m4/secure_study/compat.py", expected)
        with activate():
            self.assertIs(inherited.source_paths, common.source_paths)
            self.assertEqual(common.source_paths(), expected)
        self.assertEqual(common.source_paths(), expected)

    def test_import_aliases_cycles_and_missing_candidates_are_examined_once(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            package = root / "experiments/example"
            package.mkdir(parents=True)
            (package / "__init__.py").write_text("")
            (package / "a.py").write_text(
                "import experiments.example.helper\n"
                "import experiments.example.helper as alias\n"
                "from . import helper, absent\n"
                "from .helper import nonexistent_attribute\n"
            )
            (package / "helper.py").write_text("from . import a\n")
            inspected = []
            original = Path.is_file

            def inspect(path):
                inspected.append(path)
                return original(path)

            with patch.object(inherited, "ROOT", root), patch.object(Path, "is_file", inspect):
                actual = inherited.source_closure({"experiments/example/a.py"})
            self.assertEqual(
                actual,
                (
                    "experiments/example/__init__.py",
                    "experiments/example/a.py",
                    "experiments/example/helper.py",
                ),
            )
            self.assertEqual(len(inspected), len(set(inspected)))

    def test_later_checks_see_added_removed_and_changed_imports(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            package = root / "experiments/example"
            package.mkdir(parents=True)
            main = package / "a.py"
            main.write_text("import experiments.example.later\n")
            with patch.object(inherited, "ROOT", root):
                names = {"experiments/example/a.py"}
                self.assertEqual(inherited.source_closure(names), tuple(names))
                later = package / "later.py"
                later.write_text("")
                self.assertIn("experiments/example/later.py", inherited.source_closure(names))
                main.write_text("import experiments.example.changed\n")
                (package / "changed.py").write_text("")
                current = inherited.source_closure(names)
                self.assertIn("experiments/example/changed.py", current)
                self.assertNotIn("experiments/example/later.py", current)
                main.unlink()
                with self.assertRaises(FileNotFoundError):
                    inherited.source_closure(names)


if __name__ == "__main__":
    unittest.main()
