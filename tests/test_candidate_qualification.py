"""Counterexamples to claiming qualification for dirty artifacts or broken tasks."""

import copy
import unittest

from scripts import qualify_reader_candidate as candidate


class CandidateQualification(unittest.TestCase):
    def identities(self):
        actual = {
            "source": {"dirty": False, "revision": "b" * 40},
            "build_label": "candidate",
            "schema": "opent1d.installed-sdk/4",
            "tasks": candidate.TASKS,
            "native_execution": "unavailable-public-policy",
            "descriptor_sha256": "c" * 64,
        }
        receipt = {**copy.deepcopy(actual), "descriptor_schema": actual["schema"]}
        return receipt, actual

    def test_receipt_cannot_relabel_a_dirty_or_broader_installed_artifact(self):
        receipt, actual = self.identities()
        candidate.artifact_identity("b", receipt, actual)
        for field, value in (
            ("source", {"dirty": True, "revision": "b" * 40}),
            ("schema", "opent1d.installed-sdk/3"),
            ("tasks", candidate.TASKS + ["m4-study-installed"]),
            ("native_execution", "explicit-reviewed-attachment/1"),
            ("descriptor_sha256", "d" * 64),
        ):
            changed = {**actual, field: value}
            with self.subTest(field=field), self.assertRaises(AssertionError):
                candidate.artifact_identity("b", receipt, changed)
        for dirty in (0, None, ""):
            receipt, actual = self.identities()
            receipt["source"]["dirty"] = actual["source"]["dirty"] = dirty
            with self.subTest(dirty=dirty), self.assertRaises(AssertionError):
                candidate.artifact_identity("b", receipt, actual)

    def test_required_success_cannot_be_replaced_by_matching_failed_replays(self):
        for name, planned, complete in (
            ("paired", 3, 3),
            ("sampling", 60, 60),
            ("missing", 60, 36),
        ):
            result = {
                "execution_status": "completed",
                "payload": "native",
                "completeness": "incomplete" if name == "missing" else "complete",
                "slot_statuses": {
                    str(i): "complete" if i < complete else "failed" for i in range(planned)
                },
            }
            attempt = {"receipt": {"remaining_owned_processes": []}, "result": result}
            candidate.expected_outcome(name, attempt)
            for field, value in (
                ("payload", "forensic"),
                ("execution_status", "failed"),
                ("slot_statuses", {}),
            ):
                changed = copy.deepcopy(attempt)
                changed["result"][field] = value
                with self.subTest(name=name, field=field), self.assertRaises(AssertionError):
                    candidate.expected_outcome(name, changed)
            changed = copy.deepcopy(attempt)
            changed["receipt"]["remaining_owned_processes"] = None
            with self.assertRaises(AssertionError):
                candidate.expected_outcome(name, changed)


if __name__ == "__main__":
    unittest.main()
