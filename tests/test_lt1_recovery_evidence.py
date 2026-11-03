"""Invented logical recovery evidence; no files, host or native engine accessed."""

import copy
import hashlib
import json
import unittest

from experiments.lt1_diagnostic import recovery_evidence as evidence


def encoded(value):
    raw = json.dumps(value, sort_keys=True).encode()
    return raw, hashlib.sha256(raw).hexdigest()


class RecoveryEvidenceTests(unittest.TestCase):
    def setUp(self):
        self.context = "a" * 64
        self.as_of = "2026-11-05T12:00:00Z"
        self.policy = {
            "schema": "opent1d.lt1-retention-policy/1",
            "maximum_age_seconds": 604800,
            "extensions_allowed": False,
            "exports_allowed": False,
        }
        self.copy_channels = {"copy-" + channel: channel for channel in evidence.CHANNELS}
        self.receipts = {
            channel: hashlib.sha256((channel + "-coverage").encode()).hexdigest()
            for channel in evidence.CHANNELS
        }
        self.copy_receipts = {
            name: hashlib.sha256((name + "-absence").encode()).hexdigest()
            for name in self.copy_channels
        }
        self.register = {
            "schema": "opent1d.lt1-retention-register/1",
            "policy_sha256": encoded(self.policy)[1],
            "previous_sha256": None,
            "subjects": {
                "object-one": {
                    "retained_since": "2026-11-01T00:00:00Z",
                    "origin_evidence_sha256": "b" * 64,
                    "hold": False,
                    "copies": {
                        name: {"state": "absence-observed", "evidence_sha256": sha}
                        for name, sha in self.copy_receipts.items()
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
        self.scope = {
            "schema": "opent1d.lt1-logical-recovery-scope/1",
            "kind": "invented",
            "decision": "approved",
            "context_sha256": self.context,
            "policy_sha256": encoded(self.policy)[1],
            "channels": list(evidence.CHANNELS),
            "excluded": list(evidence.EXCLUDED),
            "copy_channels": self.copy_channels,
            "coverage_receipts": self.receipts,
            "max_evidence_age_seconds": 300,
        }
        self.observations = {
            "schema": "opent1d.lt1-recovery-observations/1",
            "kind": "invented",
            "register_sha256": None,
            "scope_sha256": None,
            "context_sha256": self.context,
            "copies": {
                name: {
                    "subject": "object-one",
                    "channel": channel,
                    "state": "absent",
                    "method": evidence.METHODS[channel],
                    "observed_at": self.as_of,
                    "absent_since": "2026-11-04T12:00:00Z",
                    "evidence_sha256": self.copy_receipts[name],
                }
                for name, channel in self.copy_channels.items()
            },
            "coverage": {
                channel: {
                    "complete": True,
                    "observed_at": self.as_of,
                    "evidence_sha256": self.receipts[channel],
                }
                for channel in evidence.CHANNELS
            },
        }

    def kwargs(self):
        raw, rsha = encoded(self.register)
        scope, ssha = encoded(self.scope)
        observations = copy.deepcopy(self.observations)
        observations.update(register_sha256=rsha, scope_sha256=ssha)
        obs, osha = encoded(observations)
        policy, psha = encoded(self.policy)
        return dict(
            register_raw=raw,
            expected_register_sha256=rsha,
            policy_raw=policy,
            expected_policy_sha256=psha,
            scope_raw=scope,
            expected_scope_sha256=ssha,
            observations_raw=obs,
            expected_observations_sha256=osha,
            as_of=self.as_of,
            expected_context_sha256=self.context,
        )

    def assess(self):
        return evidence.assess(**self.kwargs())

    def move_clock(self, value):
        self.as_of = value
        for entry in (
            *self.observations["copies"].values(),
            *self.observations["coverage"].values(),
        ):
            entry["observed_at"] = value

    def test_positive_scoped_evidence_is_distinct_from_permission_and_forensics(self):
        result = self.assess()
        self.assertTrue(result["scoped_removal_evidence_complete"])
        self.assertEqual(result["within_reviewed_scope"], "evidence-complete")
        self.assertEqual(result["retention_timing"], "met")
        self.assertEqual(result["copies"], dict.fromkeys(self.copy_channels, "absent"))
        for key in evidence.AUTHORITY:
            self.assertIs(result[key], False)
        self.assertIs(result["truth_of_external_observations_independently_proved"], False)

    def test_unknown_original_clock_does_not_invalidate_scoped_absence(self):
        self.register["subjects"]["object-one"].update(
            retained_since=None, origin_evidence_sha256=None
        )
        result = self.assess()
        self.assertTrue(result["scoped_removal_evidence_complete"])
        self.assertEqual(result["retention_timing"], "unknown")
        self.assertFalse(result["retention_deadline_met"])

    def test_late_removal_is_scoped_absence_but_missed_retention(self):
        self.move_clock("2026-11-10T12:00:00Z")
        self.observations["copies"]["copy-backup"]["absent_since"] = "2026-11-09T00:00:00Z"
        result = self.assess()
        self.assertTrue(result["scoped_removal_evidence_complete"])
        self.assertEqual(result["retention_timing"], "missed")
        self.assertFalse(result["retention_deadline_met"])

    def test_retained_quarantine_is_not_removed(self):
        self.register["subjects"]["object-one"]["copies"]["copy-quarantine"]["state"] = "present"
        self.observations["copies"]["copy-quarantine"].update(state="present", absent_since=None)
        result = self.assess()
        self.assertFalse(result["scoped_removal_evidence_complete"])
        self.assertEqual(result["copies"]["copy-quarantine"], "present")
        self.assertEqual(result["retention_timing"], "pending")
        self.move_clock("2026-11-10T12:00:00Z")
        self.assertEqual(self.assess()["retention_timing"], "missed")

    def test_missing_coverage_cannot_prove_scope_or_global_deadline(self):
        for channel in evidence.CHANNELS:
            self.observations["coverage"][channel]["complete"] = False
            result = self.assess()
            self.assertFalse(result["scoped_removal_evidence_complete"])
            self.assertEqual(result["registered_copy_timing"], "met")
            self.assertFalse(result["retention_deadline_met"])
            self.observations["coverage"][channel]["complete"] = True

    def test_coverage_receipt_and_still_recoverable_data_are_not_ignored(self):
        self.scope["coverage_receipts"]["backup"] = None
        self.assertFalse(self.assess()["scoped_removal_evidence_complete"])
        self.scope["coverage_receipts"]["backup"] = self.receipts["backup"]
        self.register["coverage"]["recoverable_until"] = "2026-11-05T13:00:00Z"
        self.assertIn("recorded-recovery-still-available", self.assess()["blockers"])

    def test_unknown_copy_preserves_planned_denominator(self):
        del self.observations["copies"]["copy-backup"]
        result = self.assess()
        self.assertEqual(len(result["copies"]), 4)
        self.assertEqual(result["copies"]["copy-backup"], "unobserved")
        self.assertFalse(result["scoped_removal_evidence_complete"])

    def test_past_recovery_beyond_deadline_cannot_become_timely(self):
        self.move_clock("2026-11-10T12:00:00Z")
        self.register["coverage"]["recoverable_until"] = "2026-11-09T00:00:00Z"
        result = self.assess()
        self.assertTrue(result["scoped_removal_evidence_complete"])
        self.assertEqual(result["retention_timing"], "unknown")
        self.assertEqual(result["registered_copy_timing"], "met")
        self.assertIn("object-one:recovery-outlives-deadline", result["policy_conflicts"])
        self.assertFalse(result["retention_deadline_met"])

    def test_present_observation_must_itself_reach_deadline_to_prove_missed(self):
        self.move_clock("2026-11-08T00:00:01Z")
        self.register["subjects"]["object-one"]["copies"]["copy-live"]["state"] = "present"
        item = self.observations["copies"]["copy-live"]
        item.update(state="present", absent_since=None)
        for observed_at, timing in (
            ("2026-11-07T23:59:59Z", "unknown"),
            ("2026-11-08T00:00:00Z", "missed"),
            ("2026-11-08T00:00:01Z", "missed"),
        ):
            with self.subTest(observed_at=observed_at):
                item["observed_at"] = observed_at
                self.assertEqual(self.assess()["retention_timing"], timing)

    def test_no_silent_scope_exclusion_or_fixture_promotion(self):
        self.scope["channels"].remove("backup")
        with self.assertRaisesRegex(ValueError, "explicit recovery scope"):
            self.assess()
        self.scope["channels"].append("backup")
        self.scope["kind"] = "observed"
        with self.assertRaisesRegex(ValueError, "observation kind"):
            self.assess()
        self.scope["kind"] = "invented"
        self.scope["decision"] = "proposed"
        self.assertIn("recovery-scope-not-approved", self.assess()["blockers"])

    def test_stale_evidence_and_equality_boundary(self):
        self.observations["copies"]["copy-live"]["observed_at"] = "2026-11-05T11:54:59Z"
        self.assertFalse(self.assess()["scoped_removal_evidence_complete"])
        self.observations["copies"]["copy-live"]["observed_at"] = "2026-11-05T11:55:00Z"
        self.assertTrue(self.assess()["scoped_removal_evidence_complete"])
        self.observations["coverage"]["snapshot"]["observed_at"] = "2026-11-05T11:54:59Z"
        self.assertFalse(self.assess()["scoped_removal_evidence_complete"])

    def test_future_and_contradictory_timestamps_refuse(self):
        item = self.observations["copies"]["copy-live"]
        item["observed_at"] = "2026-11-06T00:00:00Z"
        with self.assertRaisesRegex(ValueError, "future observation"):
            self.assess()
        item["observed_at"] = self.as_of
        item["absent_since"] = "2026-11-06T00:00:00Z"
        with self.assertRaisesRegex(ValueError, "absence timing"):
            self.assess()

    def test_hold_conflict_is_not_hidden_by_a_truthful_absence_result(self):
        self.register["subjects"]["object-one"]["hold"] = True
        result = self.assess()
        self.assertTrue(result["scoped_removal_evidence_complete"])
        self.assertEqual(result["policy_conflicts"], ["object-one:hold-conflict-no-extension"])
        self.assertFalse(result["deletion_authorized"])

    def test_inconsistent_late_observation_cannot_prove_a_timing_violation(self):
        self.move_clock("2026-11-10T12:00:00Z")
        self.observations["copies"]["copy-live"].update(
            absent_since="2026-11-09T00:00:00Z", evidence_sha256="f" * 64
        )
        result = self.assess()
        self.assertFalse(result["scoped_removal_evidence_complete"])
        self.assertEqual(result["retention_timing"], "unknown")

    def test_context_and_byte_bindings_refuse(self):
        args = self.kwargs()
        args["expected_context_sha256"] = "f" * 64
        with self.assertRaisesRegex(ValueError, "context"):
            evidence.assess(**args)
        args = self.kwargs()
        args["observations_raw"] += b" "
        with self.assertRaisesRegex(ValueError, "external byte identity"):
            evidence.assess(**args)

    def test_history_cannot_drop_a_copy_to_improve_the_assessment(self):
        previous = copy.deepcopy(self.register)
        prev_raw, prev_sha = encoded(previous)
        self.register["previous_sha256"] = prev_sha
        del self.register["subjects"]["object-one"]["copies"]["copy-backup"]
        del self.scope["copy_channels"]["copy-backup"]
        del self.observations["copies"]["copy-backup"]
        with self.assertRaisesRegex(ValueError, "dropped retained copy"):
            evidence.assess(
                **self.kwargs(), previous_raw=prev_raw, expected_previous_sha256=prev_sha
            )

    def test_truthy_coverage_and_bounded_packet_refuse(self):
        self.observations["coverage"]["backup"]["complete"] = "true"
        with self.assertRaisesRegex(ValueError, "coverage schema"):
            self.assess()
        self.observations["coverage"]["backup"]["complete"] = True
        args = self.kwargs()
        args["observations_raw"] += b" " * (1024 * 1024)
        args["expected_observations_sha256"] = hashlib.sha256(args["observations_raw"]).hexdigest()
        with self.assertRaisesRegex(ValueError, "external byte identity"):
            evidence.assess(**args)
