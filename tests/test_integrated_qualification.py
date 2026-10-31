"""Reject false qualification claims before trusting an installed candidate."""

import copy
import unittest

from scripts.integrated_candidate_probe import connected_acceptance
from scripts.qualify_integrated_candidate import PREDECESSOR, TASKS, artifact_identity


class ArtifactQualification(unittest.TestCase):
    def records(self, label):
        actual = {
            "source": {
                "revision": PREDECESSOR if label == "predecessor" else "a" * 40,
                "dirty": False,
            },
            "schema": "opent1d.installed-sdk/3"
            if label == "predecessor"
            else "opent1d.installed-sdk/5",
            "tasks": list(TASKS),
            "native_execution": "explicit-reviewed-attachment/1",
            "descriptor_sha256": "b" * 64,
            "build_label": "qualification",
        }
        receipt = {
            **copy.deepcopy(actual),
            "descriptor_schema": actual["schema"],
            "native_runtimes_shipped": False,
            "runtime_dependencies": [],
        }
        receipt.pop("schema")
        return receipt, actual

    def test_actual_descriptor_owns_scope_even_when_receipt_is_relabelled(self):
        for label in ("candidate", "predecessor"):
            receipt, actual = self.records(label)
            artifact_identity(label, receipt, actual)
            for field, changed in (
                ("schema", "opent1d.installed-sdk/99"),
                ("tasks", ["mmtt-sensitivity", "mmtt-sampling"]),
                ("native_execution", "unavailable-public-policy"),
            ):
                with self.subTest(label=label, field=field):
                    forged_receipt, wrong_actual = copy.deepcopy(receipt), copy.deepcopy(actual)
                    wrong_actual[field] = changed
                    forged_receipt["descriptor_schema" if field == "schema" else field] = changed
                    with self.assertRaises(AssertionError):
                        artifact_identity(label, forged_receipt, wrong_actual)

    def test_clean_and_source_identity_cannot_be_coerced_or_promoted(self):
        for source in (
            {"revision": "a" * 40, "dirty": 0},
            {"revision": "not-a-git-revision", "dirty": False},
            {"revision": PREDECESSOR, "dirty": False},
        ):
            with self.subTest(source=source):
                receipt, actual = self.records("candidate")
                receipt["source"] = actual["source"] = source
                with self.assertRaises(AssertionError):
                    artifact_identity("candidate", receipt, actual)

    def test_missing_point_support_cannot_be_promoted_to_numerical_success(self):
        value = {
            "coverage": {
                "planned_rows": 72,
                "planned_native_variant_pairs": 24,
                "planned_comparison_members": 6,
                "available_point_rows": 48,
                "complete_rows": 36,
                "unavailable_point_rows": 24,
            },
            "rows": [None] * 72,
            "completeness": "incomplete",
            "point_recovery": {"planned": 6, "passed": 4, "all_passed": False},
            "mismatch_controls": {"planned": 18, "passed": 12, "all_passed": False},
            "numerical_acceptance": {"status": "unavailable", "all_passed": False},
        }
        connected_acceptance(value, True)
        for field in ("point_recovery", "mismatch_controls", "numerical_acceptance"):
            changed = copy.deepcopy(value)
            changed[field]["all_passed"] = True
            with self.subTest(field=field), self.assertRaises(AssertionError):
                connected_acceptance(changed, True)
        changed = copy.deepcopy(value)
        changed["numerical_acceptance"]["status"] = "passed"
        with self.assertRaises(AssertionError):
            connected_acceptance(changed, True)


if __name__ == "__main__":
    unittest.main()
