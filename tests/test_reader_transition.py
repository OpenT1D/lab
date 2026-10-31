"""Pinned prior comparison metadata, exact successor identity and unchanged evidence."""

import copy
import os
import unittest
from unittest.mock import patch

from experiments.shared_services import comparisons, execution, reader_compatibility, store
from tests import test_plan_comparisons as fixtures


@unittest.skipUnless(os.name == "posix", "Project leases require POSIX")
class ReaderTransition(unittest.TestCase):
    setUp = fixtures.PlanComparisons.setUp
    freeze_plan = fixtures.PlanComparisons.freeze_plan
    definition = fixtures.PlanComparisons.definition

    def predecessor(self):
        return store.read(reader_compatibility.REGISTRY)["predecessor"]

    def freeze_previous(self):
        with store.opened(self.project, write_access=True) as project:
            plan = self.freeze_plan(project)
            with patch.object(comparisons, "reader", return_value=self.predecessor()):
                frozen = comparisons.freeze(project, self.definition([plan, plan]))
        return plan, frozen["comparison"]

    def test_actual_inverse_old_definition_prefix_and_inventory_are_preserved(self):
        plan, identity = self.freeze_previous()
        with store.opened(self.project, write_access=True) as project:
            execution.execute(project, plan)
        before = store.inventory(self.project, store.Budget())
        with store.opened(self.project) as project:
            result = comparisons.reconstruct(project, identity, self.root / "report")
            original = comparisons.view(project, identity)
            self.assertEqual(original["reader"], self.predecessor())
            self.assertNotEqual(result["reader"], original["reader"])
            self.assertEqual(result["reader_transition"]["policy"], reader_compatibility.SCHEMA)
            report = store.read(self.root / "report/report.json")
            self.assertEqual(report["definition"]["reader"], original["reader"])
            for row in report["members"][1]["rows"]:
                concentration = (
                    100
                    if row["endpoint"] == "paired_change"
                    else 200
                    if "before" in row["endpoint"]
                    else 300
                )
                expected = concentration * 4.585 * 0.052 * 120
                self.assertAlmostEqual(row["reference_value"], expected, delta=1e-8)
                self.assertAlmostEqual(row["difference"], expected * 0.2, delta=1e-8)
        self.assertEqual(store.inventory(self.project, store.Budget()), before)

    def test_full_prior_and_successor_metadata_required(self):
        previous, current = self.predecessor(), comparisons.reader()
        self.assertTrue(reader_compatibility.accepts(previous, current, "mmtt-sensitivity"))
        self.assertTrue(reader_compatibility.accepts(previous, current, "mmtt-sampling"))
        self.assertFalse(reader_compatibility.accepts(previous, current, "m4-study-installed"))
        for key in previous:
            altered = copy.deepcopy(previous)
            altered[key] = None
            self.assertFalse(reader_compatibility.accepts(altered, current, "mmtt-sampling"), key)
        for key in current:
            altered = copy.deepcopy(current)
            altered[key] = None
            self.assertFalse(reader_compatibility.accepts(previous, altered, "mmtt-sampling"), key)
        for name in current["reader_static_dependencies_sha256"]:
            altered = copy.deepcopy(current)
            altered["reader_static_dependencies_sha256"][name] = "0" * 64
            self.assertFalse(reader_compatibility.accepts(previous, altered, "mmtt-sampling"), name)

    def test_other_definition_fields_are_still_canonical(self):
        _, identity = self.freeze_previous()
        with store.opened(self.project) as project:
            original = project.comparisons[identity]
            for field in ("support", "changes", "attempt_policy", "task", "schema"):
                altered = copy.deepcopy(original)
                altered[field] = None
                with (
                    self.subTest(field=field),
                    self.assertRaisesRegex(
                        ValueError,
                        "Explicit comparison definition required"
                        if field == "schema"
                        else "identity differs",
                    ),
                ):
                    comparisons.validate(project, altered)

    def test_boolean_integer_aliases_are_not_exact_reader_identities(self):
        previous, current = self.predecessor(), comparisons.reader()
        for original in (previous, current):
            altered = copy.deepcopy(original)
            altered["archived_code_execution"] = 0
            self.assertNotEqual(store.encoded(altered), store.encoded(original))
            self.assertFalse(reader_compatibility.accepts(altered, current, "mmtt-sensitivity"))
        altered = copy.deepcopy(current)
        altered["archived_code_execution"] = 0
        self.assertFalse(reader_compatibility.accepts(previous, altered, "mmtt-sampling"))

    def test_unqualified_current_renderer_is_not_a_compatibility_exception(self):
        self.freeze_previous()
        before = store.inventory(self.project, store.Budget())
        changed = comparisons.reader()
        changed["reader_static_dependencies_sha256"][
            "experiments/shared_services/comparison_reports.py"
        ] = "0" * 64
        with patch.object(comparisons, "reader", return_value=changed):
            with self.assertRaisesRegex(ValueError, "Frozen comparison/source identity differs"):
                with store.opened(self.project):
                    pass
        self.assertEqual(store.inventory(self.project, store.Budget()), before)

    def test_former_strict_reader_rejects_the_same_preserved_project(self):
        self.freeze_previous()
        before = store.inventory(self.project, store.Budget())
        with patch.object(reader_compatibility, "accepts", side_effect=lambda a, b, _: a == b):
            with self.assertRaisesRegex(ValueError, "Frozen comparison/source identity differs"):
                with store.opened(self.project):
                    pass
        self.assertEqual(store.inventory(self.project, store.Budget()), before)


if __name__ == "__main__":
    unittest.main()
