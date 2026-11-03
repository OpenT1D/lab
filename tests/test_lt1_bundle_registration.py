"""Fresh invented bundle accounting; no active register, pilot or native runtime."""

import copy
import json
import os
import shutil
import unittest
from unittest.mock import patch

import test_lt1_review_bundle as fixtures

from experiments.lt1_diagnostic import bundle_registration as registration

bundle = registration.review_bundle
wire = registration.wire


@unittest.skipUnless(os.name == "posix", "POSIX private bundle fixture required")
class BundleRegistrationTests(unittest.TestCase):
    def setUp(self):
        self.storage = fixtures.ReviewBundleTests()
        self.storage.setUp()
        self.addCleanup(self.storage.doCleanups)
        self.previous = None

    def publish(self, *, stop=lambda: False, checkpoint=lambda *_: None):
        self.storage.inputs = self.storage.fixture.args()
        if self.previous is not None:
            self.storage.inputs.update(
                previous_raw=self.previous,
                expected_previous_sha256=wire.digest(self.previous),
            )
        self.saved = self.storage.save(stop=stop, checkpoint=checkpoint)
        self.target = self.storage.output
        base = registration.retention.register(
            self.storage.inputs["register_raw"], self.storage.inputs["expected_register_sha256"]
        )
        self.allocation = {
            "schema": "opent1d.lt1-bundle-copy-allocation/1",
            "kind": "invented",
            "manifest_sha256": self.saved["manifest_sha256"],
            "register_sha256": self.storage.inputs["expected_register_sha256"],
            "policy_sha256": self.storage.inputs["expected_policy_sha256"],
            "context_sha256": self.storage.inputs["expected_context_sha256"],
            "source_identity": registration.source_identity(),
            "copies": {
                name: f"bundle-copy-{index}" for index, name in enumerate(sorted(base["subjects"]))
            },
        }

    def args(self):
        inputs = self.storage.inputs
        raw = wire.encoded(self.allocation)
        args = {
            "bundle_path": self.target,
            "expected_manifest_sha256": self.saved["manifest_sha256"],
            "register_raw": inputs["register_raw"],
            "expected_register_sha256": inputs["expected_register_sha256"],
            "policy_raw": inputs["policy_raw"],
            "expected_policy_sha256": inputs["expected_policy_sha256"],
            "allocation_raw": raw,
            "expected_allocation_sha256": wire.digest(raw),
            "as_of": inputs["as_of"],
            "expected_context_sha256": inputs["expected_context_sha256"],
        }
        if self.previous is not None:
            args.update(
                previous_raw=self.previous, expected_previous_sha256=wire.digest(self.previous)
            )
        return args

    def propose(self, **changes):
        args = self.args()
        args.update(changes)
        return registration.propose_registration(**args)

    def test_exact_base_preserved_and_one_new_aggregate_copy_per_subject(self):
        self.publish()
        before = copy.deepcopy(self.storage.inputs)
        result = self.propose()
        base = json.loads(before["register_raw"])
        proposed = json.loads(result["register_raw"])
        self.assertEqual(proposed["previous_sha256"], before["expected_register_sha256"])
        self.assertEqual(proposed["policy_sha256"], base["policy_sha256"])
        self.assertEqual(proposed["subjects"].keys(), base["subjects"].keys())
        for name, old in base["subjects"].items():
            subject = proposed["subjects"][name]
            for key in ("retained_since", "origin_evidence_sha256", "hold"):
                self.assertEqual(subject[key], old[key])
            for copy_id, record in old["copies"].items():
                self.assertEqual(subject["copies"][copy_id], record)
            new_id = self.allocation["copies"][name]
            raw = result["provenance_raw"][new_id]
            self.assertEqual(
                subject["copies"][new_id], {"state": "present", "evidence_sha256": wire.digest(raw)}
            )
            provenance = json.loads(raw)
            self.assertEqual(provenance["manifest_sha256"], self.saved["manifest_sha256"])
            self.assertEqual(provenance["subject"], name)
            self.assertEqual(
                provenance["registration_source_identity_sha256"],
                wire.digest(wire.encoded(result["source_identity"])),
            )
            self.assertEqual(result["source_identity"], self.allocation["source_identity"])
            self.assertEqual(provenance["bundle_path"], str(self.target))
            self.assertEqual(provenance["base_register_sha256"], before["expected_register_sha256"])
        self.assertFalse(result["saved_or_approved"])
        self.assertTrue(all(result[k] is False for k in registration.AUTHORITY))
        self.assertFalse(result["global_copy_coverage_verified"])
        self.assertEqual(self.storage.inputs, before)
        self.assertEqual(self.storage.active.read_bytes(), before["register_raw"])

    def test_unapproved_recovery_proposal_states_are_never_adopted(self):
        f = self.storage.fixture
        row = f.report["local_readbacks"][0]
        f.report["local_readbacks"][0] = {
            key: row[key]
            for key in ("path", "observed_from", "observed_to", "data_device_matches", "device")
        }
        f.report["local_readbacks"][0]["state"] = "absence-observed"
        self.publish()
        unapproved = json.loads((self.target / "proposed-register.json").read_bytes())
        self.assertEqual(
            unapproved["subjects"]["object-one"]["copies"]["copy-live"]["state"], "absence-observed"
        )
        result = self.propose()
        proposed = json.loads(result["register_raw"])
        self.assertEqual(
            proposed["subjects"]["object-one"]["copies"]["copy-live"]["state"], "present"
        )

    def test_unknown_origin_hold_and_known_recovery_horizon_are_inherited(self):
        f = self.storage.fixture
        f.current["subjects"]["object-one"].update(
            retained_since=None, origin_evidence_sha256=None, hold=True
        )
        horizon = "2026-12-01T00:00:00Z"
        f.current["coverage"]["recoverable_until"] = horizon
        self.publish()
        result = self.propose()
        proposed = json.loads(result["register_raw"])
        subject = proposed["subjects"]["object-one"]
        self.assertIsNone(subject["retained_since"])
        self.assertIsNone(subject["origin_evidence_sha256"])
        self.assertTrue(subject["hold"])
        self.assertIsNone(result["assessment"]["deadlines"]["object-one"])
        self.assertEqual(proposed["coverage"]["recoverable_until"], horizon)
        for key in ("all_copies_registered", "recovery_scope_reviewed", "processes_stopped"):
            self.assertIs(proposed["coverage"][key], False)
        self.assertEqual(
            proposed["coverage"]["context_sha256"], self.storage.inputs["expected_context_sha256"]
        )
        new_id = self.allocation["copies"]["object-one"]
        self.assertEqual(
            json.loads(result["provenance_raw"][new_id])["inherited"],
            {k: subject[k] for k in ("retained_since", "origin_evidence_sha256", "hold")},
        )

    def test_unknown_recovery_horizon_is_not_filled(self):
        self.publish()
        result = self.propose()
        self.assertIsNone(json.loads(result["register_raw"])["coverage"]["recoverable_until"])

    def test_known_deadlines_never_move_later(self):
        self.publish()
        old = registration.retention.plan(
            self.storage.inputs["register_raw"],
            self.storage.inputs["expected_register_sha256"],
            self.storage.inputs["policy_raw"],
            self.storage.inputs["expected_policy_sha256"],
            self.storage.inputs["as_of"],
            self.storage.inputs["expected_context_sha256"],
        )
        self.assertEqual(self.propose()["assessment"]["deadlines"], old["deadlines"])

    def test_existing_predecessor_is_required_then_current_becomes_predecessor(self):
        self.previous = wire.encoded(self.storage.fixture.current)
        self.storage.fixture.current["previous_sha256"] = wire.digest(self.previous)
        self.publish()
        args = self.args()
        args.pop("previous_raw")
        args.pop("expected_previous_sha256")
        with patch.object(bundle, "_inspect", side_effect=AssertionError("private FS")):
            with self.assertRaises(ValueError):
                registration.propose_registration(**args)
        result = self.propose()
        self.assertEqual(
            json.loads(result["register_raw"])["previous_sha256"],
            self.storage.inputs["expected_register_sha256"],
        )

    def test_missing_extra_reused_or_bad_copy_id_refuses_before_private_fs(self):
        self.publish()
        original = copy.deepcopy(self.allocation)
        for copies in (
            {},
            {"object-one": "new-id", "foreign": "another"},
            {"object-one": "copy-live"},
            {"object-one": True},
            {"object-one": "Bad ID"},
        ):
            self.allocation = copy.deepcopy(original)
            self.allocation["copies"] = copies
            with (
                self.subTest(copies=copies),
                patch.object(bundle, "_inspect", side_effect=AssertionError("private FS")),
            ):
                with self.assertRaises(ValueError):
                    self.propose()

    def test_every_subject_gets_a_distinct_globally_new_copy(self):
        f = self.storage.fixture
        f.current["subjects"]["object-two"] = {
            "retained_since": None,
            "origin_evidence_sha256": None,
            "hold": True,
            "copies": {"copy-other": {"state": "present", "evidence_sha256": "f" * 64}},
        }
        f.fixture.scope["copy_channels"]["copy-other"] = "live"
        self.publish()
        self.allocation["copies"] = {"object-one": "new-same", "object-two": "new-same"}
        with patch.object(bundle, "_inspect", side_effect=AssertionError("private FS")):
            with self.assertRaisesRegex(ValueError, "globally unused"):
                self.propose()
        self.allocation["copies"]["object-two"] = "new-other"
        result = self.propose()
        self.assertEqual(set(result["provenance_raw"]), {"new-same", "new-other"})
        proposed = json.loads(result["register_raw"])
        self.assertTrue(proposed["subjects"]["object-two"]["hold"])
        self.assertIsNone(proposed["subjects"]["object-two"]["retained_since"])

    def test_changed_policy_context_or_allocation_hash_refuses_before_private_fs(self):
        self.publish()
        for values in (
            {"expected_context_sha256": "f" * 64},
            {"expected_policy_sha256": "f" * 64},
            {"expected_allocation_sha256": "f" * 64},
            {"expected_manifest_sha256": "f" * 64},
        ):
            with (
                self.subTest(values=values),
                patch.object(bundle, "_inspect", side_effect=AssertionError("private FS")),
            ):
                with self.assertRaises(ValueError):
                    self.propose(**values)

    def test_malformed_allocation_and_source_refuse_before_private_fs(self):
        self.publish()
        with patch.object(bundle, "_inspect", side_effect=AssertionError("private FS")):
            with self.assertRaises(ValueError):
                self.propose(
                    allocation_raw=b"not json", expected_allocation_sha256=wire.digest(b"not json")
                )
            self.allocation["source_identity"] = {"changed": True}
            with self.assertRaisesRegex(ValueError, "source identity"):
                self.propose()

    def test_future_origin_and_copy_bound_refuse_before_private_fs(self):
        self.publish()
        base = json.loads(self.storage.inputs["register_raw"])
        base["subjects"]["object-one"]["retained_since"] = "2026-12-01T00:00:00Z"
        raw = wire.encoded(base)
        with patch.object(bundle, "_inspect", side_effect=AssertionError("private FS")):
            with self.assertRaisesRegex(ValueError, "future origin"):
                self.propose(register_raw=raw, expected_register_sha256=wire.digest(raw))
            with patch.object(registration.retention, "MAX_COPIES", 4):
                with self.assertRaisesRegex(ValueError, "aggregate copy bound"):
                    self.propose()

    def test_valid_different_base_does_not_rebase_the_frozen_bundle(self):
        self.publish()
        base = json.loads(self.storage.inputs["register_raw"])
        base["subjects"]["object-one"]["copies"]["other-present"] = {
            "state": "present",
            "evidence_sha256": "e" * 64,
        }
        raw = wire.encoded(base)
        self.allocation["register_sha256"] = wire.digest(raw)
        with self.assertRaisesRegex(ValueError, "current register"):
            self.propose(register_raw=raw, expected_register_sha256=wire.digest(raw))

    def test_reversed_assessment_clock_or_mixed_evidence_kind_refuses(self):
        self.publish()
        with self.assertRaisesRegex(ValueError, "clock reversed"):
            self.propose(as_of="2026-11-05T11:59:59Z")
        self.allocation["kind"] = "observed"
        with self.assertRaisesRegex(ValueError, "evidence kind"):
            self.propose()

    def test_same_complete_inputs_are_deterministic_and_bundle_stays_unchanged(self):
        self.publish()
        before = {p.name: p.read_bytes() for p in self.target.iterdir()}
        first, second = self.propose(), self.propose()
        self.assertEqual(first, second)
        self.assertEqual({p.name: p.read_bytes() for p in self.target.iterdir()}, before)

    def test_late_same_byte_member_inode_change_refuses(self):
        self.publish()
        actual, calls = registration.source_identity, 0

        def change():
            nonlocal calls
            value = actual()
            calls += 1
            if calls == 2:
                path = self.target / "register.json"
                raw = path.read_bytes()
                path.rename(self.storage.parent / "retained-original.json")
                path.write_bytes(raw)
                path.chmod(0o600)
            return value

        with patch.object(registration, "source_identity", side_effect=change):
            with self.assertRaisesRegex(ValueError, "bundle changed during"):
                self.propose()

    def test_late_same_byte_root_inode_change_refuses(self):
        self.publish()
        actual, calls = registration.source_identity, 0

        def change():
            nonlocal calls
            value = actual()
            calls += 1
            if calls == 2:
                original = self.storage.parent / "retained-original-bundle"
                self.target.rename(original)
                shutil.copytree(original, self.target)
                self.target.chmod(0o700)
            return value

        with patch.object(registration, "source_identity", side_effect=change):
            with self.assertRaisesRegex(ValueError, "bundle changed during"):
                self.propose()

    def test_late_source_change_refuses(self):
        self.publish()
        original = registration.source_identity()
        with patch.object(
            registration, "source_identity", side_effect=[original, {"changed": True}]
        ):
            with self.assertRaisesRegex(ValueError, "registration source changed"):
                self.propose()

    def test_complete_pending_is_not_a_verified_published_bundle(self):
        stopped = False

        def halt(event, _name):
            nonlocal stopped
            if event == "prepared":
                stopped = True

        self.publish(stop=lambda: stopped, checkpoint=halt)
        self.target = self.storage.parent / "review.pending"
        with self.assertRaisesRegex(ValueError, "intended published leaf"):
            self.propose()

    def test_no_save_activate_query_capture_or_removal(self):
        self.publish()
        active = self.storage.active.read_bytes()
        with (
            patch.object(bundle, "save_review_bundle", side_effect=AssertionError("save")),
            patch.object(bundle.removal, "remove", side_effect=AssertionError("remove")),
            patch("os.write", side_effect=AssertionError("write")),
            patch("subprocess.run", side_effect=AssertionError("process")),
        ):
            result = self.propose()
        self.assertFalse(result["saved_or_approved"])
        self.assertEqual(self.storage.active.read_bytes(), active)

    def test_aggregate_provenance_bound_refuses_without_mutating_bundle(self):
        self.publish()
        before = {p.name: p.read_bytes() for p in self.target.iterdir()}
        with patch.object(registration, "PROVENANCE_LIMIT", 1):
            with self.assertRaisesRegex(ValueError, "aggregate provenance byte bound"):
                self.propose()
        self.assertEqual({p.name: p.read_bytes() for p in self.target.iterdir()}, before)
