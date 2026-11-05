"""Invented retention records; no private files or deletion are accessed."""

import copy
import hashlib
import json
import unittest
from unittest.mock import patch

from experiments.lt1_diagnostic import retention


def encoded(value):
    raw = json.dumps(value, sort_keys=True).encode()
    return raw, hashlib.sha256(raw).hexdigest()


class LT1RetentionTests(unittest.TestCase):
    def setUp(self):
        self.context = "a" * 64
        self.policy = {
            "schema": "opent1d.lt1-retention-policy/1",
            "maximum_age_seconds": 604800,
            "extensions_allowed": False,
            "exports_allowed": False,
        }
        self.record = {
            "schema": "opent1d.lt1-retention-register/1",
            "policy_sha256": encoded(self.policy)[1],
            "previous_sha256": None,
            "subjects": {
                "invented-result": {
                    "retained_since": "2026-11-02T00:00:00Z",
                    "origin_evidence_sha256": "b" * 64,
                    "hold": False,
                    "copies": {
                        "original": {"state": "present", "evidence_sha256": "c" * 64},
                        "relocated-revision": {"state": "present", "evidence_sha256": "d" * 64},
                    },
                }
            },
            "coverage": {
                "all_copies_registered": True,
                "recovery_scope_reviewed": True,
                "recoverable_until": None,
                "processes_stopped": True,
                "context_sha256": self.context,
            },
        }

    def plan(self, *, at="2026-11-09T00:00:00Z", previous=None, context=None):
        raw, sha = encoded(self.record)
        policy, policy_sha = encoded(self.policy)
        kwargs = {}
        if previous is not None:
            kwargs["previous_raw"], kwargs["expected_previous_sha256"] = encoded(previous)
        return retention.plan(raw, sha, policy, policy_sha, at, context or self.context, **kwargs)

    def test_exact_boundary_copies_and_revisions_share_original_clock(self):
        before = self.plan(at="2026-11-08T23:59:59Z")
        self.assertEqual(before["actions"], [])
        due = self.plan()
        self.assertEqual(due["deadlines"], {"invented-result": "2026-11-09T00:00:00Z"})
        self.assertEqual(due["status"], "removal-review-needed")
        self.assertEqual({a["copy"] for a in due["actions"]}, {"original", "relocated-revision"})
        self.assertEqual(len(due["actions"]), 2)

    def test_independent_output_has_its_own_origin(self):
        other = copy.deepcopy(self.record["subjects"]["invented-result"])
        other.update(retained_since="2026-11-08T00:00:00Z")
        other["copies"] = {"new-output": {"state": "present", "evidence_sha256": "e" * 64}}
        self.record["subjects"]["new-independent-output"] = other
        result = self.plan()
        self.assertEqual(result["deadlines"]["new-independent-output"], "2026-11-15T00:00:00Z")
        self.assertEqual({a["subject"] for a in result["actions"]}, {"invented-result"})

    def test_known_predecessor_prevents_extension_and_dropped_evidence(self):
        previous = copy.deepcopy(self.record)
        self.record["previous_sha256"] = encoded(previous)[1]
        self.assertEqual(len(self.plan(previous=previous)["actions"]), 2)
        original = copy.deepcopy(self.record)
        self.record["subjects"]["invented-result"]["retained_since"] = "2026-11-03T00:00:00Z"
        with self.assertRaisesRegex(ValueError, "origin extension"):
            self.plan(previous=previous)
        self.record = copy.deepcopy(original)
        del self.record["subjects"]["invented-result"]["copies"]["original"]
        with self.assertRaisesRegex(ValueError, "dropped retained copy"):
            self.plan(previous=previous)
        self.record = copy.deepcopy(original)
        self.record["subjects"]["new-subject"] = self.record["subjects"].pop("invented-result")
        with self.assertRaisesRegex(ValueError, "dropped retention subject"):
            self.plan(previous=previous)

    def test_predecessor_is_externally_bound_and_cannot_be_omitted(self):
        previous = copy.deepcopy(self.record)
        self.record["previous_sha256"] = encoded(previous)[1]
        with self.assertRaisesRegex(ValueError, "predecessor identity"):
            self.plan()
        previous["coverage"]["processes_stopped"] = False
        with self.assertRaisesRegex(ValueError, "predecessor identity"):
            self.plan(previous=previous)
        self.record["previous_sha256"] = None
        with self.assertRaisesRegex(ValueError, "unexpected predecessor"):
            self.plan(previous=previous)

    def test_unknown_origin_remains_unknown(self):
        subject = self.record["subjects"]["invented-result"]
        subject.update(retained_since=None, origin_evidence_sha256=None)
        result = self.plan()
        self.assertEqual(result["status"], "blocked")
        self.assertEqual(result["deadlines"]["invented-result"], None)
        self.assertIn("invented-result:origin-unestablished", result["blockers"])
        self.assertEqual(result["actions"], [])

    def test_missing_coverage_does_not_disappear_before_or_after_expiry(self):
        for key in ("all_copies_registered", "recovery_scope_reviewed", "processes_stopped"):
            with self.subTest(key=key):
                self.record["coverage"][key] = False
                for at in ("2026-11-08T00:00:00Z", "2026-11-09T00:00:00Z"):
                    result = self.plan(at=at)
                    self.assertEqual(result["status"], "blocked")
                    self.assertIn(key, result["blockers"])
                self.record["coverage"][key] = True

    def test_backup_recovery_and_holds_cannot_extend_deadline(self):
        self.record["coverage"]["recoverable_until"] = "2026-11-10T00:00:00Z"
        self.record["subjects"]["invented-result"]["hold"] = True
        result = self.plan()
        self.assertEqual(result["status"], "blocked")
        self.assertEqual(result["deadlines"]["invented-result"], "2026-11-09T00:00:00Z")
        self.assertIn("invented-result:recovery-outlives-deadline", result["blockers"])
        self.assertIn("invented-result:hold-does-not-extend-retention", result["blockers"])
        self.assertEqual(len(result["actions"]), 2)

    def test_observed_absence_is_not_effective_erasure_or_permission(self):
        for item in self.record["subjects"]["invented-result"]["copies"].values():
            item["state"] = "absence-observed"
        with patch("builtins.open", side_effect=AssertionError("Planner must not access files")):
            result = self.plan()
        self.assertEqual(result["actions"], [])
        self.assertEqual(result["status"], "expired-absence-review-needed")
        self.assertEqual(result["expired_subjects"], ["invented-result"])
        for field in (
            "effective_erasure_verified",
            "deletion_authorized",
            "setup_admitted",
            "native_execution_authorized",
        ):
            self.assertIs(result[field], False)

    def test_policy_change_cannot_extend_known_predecessor_deadline(self):
        previous = copy.deepcopy(self.record)
        self.record["previous_sha256"] = encoded(previous)[1]
        self.policy["maximum_age_seconds"] += 2
        with self.assertRaisesRegex(ValueError, "policy identity"):
            self.plan(at="2026-11-09T00:00:01Z", previous=previous)
        self.record["policy_sha256"] = encoded(self.policy)[1]
        with self.assertRaisesRegex(ValueError, "policy lineage"):
            self.plan(at="2026-11-09T00:00:01Z", previous=previous)

    def test_external_bytes_and_stale_context_refuse(self):
        with self.assertRaisesRegex(ValueError, "stale host/storage/source context"):
            self.plan(context="f" * 64)
        raw, sha = encoded(self.record)
        policy, policy_sha = encoded(self.policy)
        for changed, expected, pbytes, psha in (
            (raw + b" ", sha, policy, policy_sha),
            (raw, sha, policy + b" ", policy_sha),
        ):
            with self.assertRaisesRegex(ValueError, "external byte identity"):
                retention.plan(
                    changed, expected, pbytes, psha, "2026-11-09T00:00:00Z", self.context
                )

    def test_schema_dates_truthy_flags_and_permissive_policy_refuse(self):
        original = copy.deepcopy(self.record)
        for field, value in (
            ("retained_since", "2026-11-10T00:00:00Z"),
            ("retained_since", "2026-11-02T00:00:00+00:00"),
            ("hold", "false"),
            ("origin_evidence_sha256", None),
        ):
            self.record = copy.deepcopy(original)
            self.record["subjects"]["invented-result"][field] = value
            with self.assertRaises(ValueError):
                self.plan()
        self.record = original
        self.record["coverage"]["recovery_scope_reviewed"] = 1
        with self.assertRaises(ValueError):
            self.plan()
        self.record["coverage"]["recovery_scope_reviewed"] = True
        for key, value in (
            ("maximum_age_seconds", True),
            ("maximum_age_seconds", 0),
            ("extensions_allowed", True),
            ("exports_allowed", True),
        ):
            original_policy = copy.deepcopy(self.policy)
            self.policy[key] = value
            with self.assertRaisesRegex(ValueError, "private policy"):
                self.plan()
            self.policy = original_policy

    def test_duplicate_copy_ids_and_resource_limits_refuse(self):
        with patch.object(retention, "MAX_COPIES", 1):
            with self.assertRaisesRegex(ValueError, "copy count"):
                self.plan()
        with patch.object(retention, "LIMIT", 10):
            with self.assertRaisesRegex(ValueError, "external byte identity"):
                self.plan()
        other = copy.deepcopy(self.record["subjects"]["invented-result"])
        self.record["subjects"]["second"] = other
        with self.assertRaisesRegex(ValueError, "duplicate copy identity"):
            self.plan()
