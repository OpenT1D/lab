"""Fresh invented metadata only; no register activation or native qualification."""

import copy
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import lt1_bundle_removal_fixture as fixture

from experiments.lt1_diagnostic import bundle_reconciliation as reconciliation

wire, removal = reconciliation.wire, reconciliation.removal


@unittest.skipUnless(os.name == "posix", "POSIX private bundle fixture required")
class BundleReconciliationTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.folder = Path(temporary.name).resolve()
        self.folder.chmod(0o700)
        self.request, self.registry, self.context = fixture.prepare(self.folder)
        self.manifest = (self.folder / "bundle/manifest.json").read_bytes()
        self.intent = (self.folder / "bundle/intent.json").read_bytes()
        self.allocation = json.loads((self.folder / "allocation.json").read_bytes())
        self.provenance = {
            copy_id: (self.folder / (copy_id + ".json")).read_bytes()
            for copy_id in self.allocation["copies"].values()
        }
        self.outer = {
            "status": "completed",
            "error": None,
            "cleanup_error": None,
            "exit_code": 0,
            "remaining_owned_processes": [],
            "received_signals": [],
            "fixture": "invented external owner receipt, not host qualification",
        }
        self.stop = False
        self.removed = False

    def finish(self, phase="complete"):
        def checkpoint(event, _name):
            if event == phase:
                self.stop = True

        result = removal._remove_reviewed(
            self.request,
            self.registry,
            self.context,
            stop=lambda: self.stop,
            checkpoint=checkpoint,
        )
        self.assertEqual(
            result["status"], "namespace-absence-observed" if phase == "complete" else "interrupted"
        )
        self.removed = True

    def args(self):
        if not self.removed:
            self.finish()
        values = {
            "base_raw": (self.folder / "base-register.json").read_bytes(),
            "registration_raw": (self.folder / "proposed-register.json").read_bytes(),
            "policy_raw": (self.folder / "policy.json").read_bytes(),
            "allocation_raw": (self.folder / "allocation.json").read_bytes(),
            "manifest_raw": self.manifest,
            "intent_raw": self.intent,
            "request_raw": self.request,
            "context_raw": self.context,
            "journal_raw": (
                self.folder / "reports/remove-derived-bundle/events.jsonl"
            ).read_bytes(),
            "outer_raw": wire.encoded(self.outer),
        }
        args = {
            **values,
            **{
                "expected_" + name[:-4] + "_sha256": wire.digest(raw)
                for name, raw in values.items()
            },
        }
        return {
            **args,
            "provenance_raw": dict(self.provenance),
            "expected_provenance_sha256": {
                key: wire.digest(raw) for key, raw in self.provenance.items()
            },
            "as_of": "2026-11-05T12:00:00Z",
            "expected_reader_identity": reconciliation.source_identity(),
        }

    def changed(self, args, name, mutate):
        value = json.loads(args[name + "_raw"])
        mutate(value)
        raw = wire.encoded(value)
        return {**args, name + "_raw": raw, "expected_" + name + "_sha256": wire.digest(raw)}

    def refuse_before_intake(self, args, reason=None):
        with patch.object(
            removal, "inspect", side_effect=AssertionError("private namespace intake")
        ) as read:
            with self.assertRaisesRegex(ValueError, reason or ".*"):
                reconciliation.propose_reconciliation(**args)
            read.assert_not_called()

    def assert_closed(self, result):
        for key in reconciliation.AUTHORITY:
            self.assertIs(result[key], False, key)
        self.assertFalse(result["saved_or_approved"])
        self.assertFalse(result["global_copy_coverage_verified"])
        self.assertTrue(result["new_bundle_copy_registration_required"])
        self.assertTrue(result["provenance_retention_required"])

    def test_complete_updates_only_explicit_new_copies_and_preserves_old_objects(self):
        args = self.args()
        before = copy.deepcopy(args)
        result = reconciliation.propose_reconciliation(**args)
        self.assertEqual(result, reconciliation.propose_reconciliation(**args))
        self.assertEqual(args, before)
        self.assertEqual(result["status"], "proposed")
        self.assertTrue(result["new_revision_proposed"])
        old, new = json.loads(args["registration_raw"]), json.loads(result["register_raw"])
        self.assertEqual(new["previous_sha256"], args["expected_registration_sha256"])
        self.assertEqual(new["coverage"], old["coverage"])
        self.assertEqual(new["policy_sha256"], old["policy_sha256"])
        for name, subject in old["subjects"].items():
            expected = copy.deepcopy(subject)
            copy_id = self.allocation["copies"][name]
            raw = result["provenance_raw"][copy_id]
            expected["copies"][copy_id] = {
                "state": "absence-observed",
                "evidence_sha256": wire.digest(raw),
            }
            self.assertEqual(new["subjects"][name], expected)
            provenance = json.loads(raw)
            self.assertEqual(provenance["bindings"], result["bindings"])
            self.assertFalse(provenance["absence_time_established"])
            self.assertNotIn("absence_since", provenance)
            self.assertFalse(provenance["retention_deadline_compliance_verified"])
        self.assertIsNone(new["subjects"]["unknown-object"]["retained_since"])
        self.assertTrue(new["subjects"]["unknown-object"]["hold"])
        self.assertEqual(new["coverage"]["recoverable_until"], "2026-12-01T00:00:00Z")
        self.assertEqual(
            result["assessment"]["deadlines"],
            {"object-one": "2026-11-08T00:00:00Z", "unknown-object": None},
        )
        self.assertEqual(result["assessment"]["status"], "blocked")
        self.assertEqual((self.folder / "original-object.txt").read_bytes(), fixture.ORIGINAL)
        self.assertEqual(
            (self.folder / "proposed-register.json").read_bytes(), args["registration_raw"]
        )
        self.assert_closed(result)

    def test_partial_unlink_and_quarantine_keep_exact_registration_bytes(self):
        self.finish("quarantined")
        args = self.args()
        # Whitespace is retained for incomplete results; no register is rewritten.
        raw = json.dumps(json.loads(args["registration_raw"]), indent=2).encode()
        args.update(registration_raw=raw, expected_registration_sha256=wire.digest(raw))
        result = reconciliation.propose_reconciliation(**args)
        self.assertEqual(result["status"], "incomplete")
        self.assertFalse(result["new_revision_proposed"])
        self.assertEqual(result["register_raw"], raw)
        self.assertEqual(result["register_sha256"], wire.digest(raw))
        self.assertEqual(result["provenance_raw"], {})
        self.assert_closed(result)

    def test_stopped_after_unlink_does_not_promote_one_copy(self):
        self.finish("removed")
        args = self.args()
        result = reconciliation.propose_reconciliation(**args)
        self.assertEqual(result["removal_readback"]["status"], "incomplete")
        self.assertEqual(result["register_raw"], args["registration_raw"])
        self.assertEqual(result["provenance_raw"], {})

    def test_owner_cancel_error_cleanup_or_live_process_never_promote_absence(self):
        args = self.args()
        for changes in (
            {"status": "interrupted", "error": "Cancelled"},
            {"status": "failed", "error": "WorkerDeadline"},
            {"cleanup_error": "invented failure"},
            {"remaining_owned_processes": [{"pid": 12345}]},
            {"exit_code": False},
            {"received_signals": ["SIGTERM"]},
        ):
            raw = wire.encoded({**self.outer, **changes})
            result = reconciliation.propose_reconciliation(
                **{**args, "outer_raw": raw, "expected_outer_sha256": wire.digest(raw)}
            )
            self.assertEqual(result["register_raw"], args["registration_raw"])
            self.assertFalse(result["new_revision_proposed"])

    def test_every_external_byte_hash_and_provenance_hash_precedes_intake(self):
        args = self.args()
        for name in (
            "base",
            "registration",
            "policy",
            "allocation",
            "manifest",
            "intent",
            "request",
            "context",
            "journal",
            "outer",
        ):
            with self.subTest(name=name):
                self.refuse_before_intake({**args, "expected_" + name + "_sha256": "a" * 64})
        wrong = dict(args["expected_provenance_sha256"])
        wrong[next(iter(wrong))] = "a" * 64
        self.refuse_before_intake({**args, "expected_provenance_sha256": wrong})

    def test_allocation_cannot_select_old_duplicate_or_missing_copy_ids(self):
        args = self.args()

        def old(v):
            v["copies"]["object-one"] = "copy-live"

        def duplicate(v):
            v["copies"]["unknown-object"] = v["copies"]["object-one"]

        def missing(v):
            del v["copies"]["unknown-object"]

        for mutate in (old, duplicate, missing):
            self.refuse_before_intake(self.changed(args, "allocation", mutate))

    def test_rehashed_registration_cannot_change_old_states_origins_holds_or_coverage(self):
        args = self.args()
        mutations = [
            lambda v: v["subjects"]["object-one"]["copies"]["copy-live"].update(
                state="absence-observed"
            ),
            lambda v: v["subjects"]["unknown-object"].update(hold=False),
            lambda v: v["subjects"]["object-one"].update(retained_since="2026-10-08T00:00:00Z"),
            lambda v: v["coverage"].update(recoverable_until=None),
            lambda v: v["coverage"].update(all_copies_registered=True),
            lambda v: v["subjects"]["unknown-object"]["copies"].pop("unknown-original"),
            lambda v: v.update(previous_sha256="a" * 64),
        ]
        for mutate in mutations:
            self.refuse_before_intake(self.changed(args, "registration", mutate))

    def test_rehashed_provenance_cannot_change_subject_root_leaf_source_or_hold(self):
        args = self.args()
        key = self.allocation["copies"]["unknown-object"]
        for field, value in (
            ("subject", "object-one"),
            ("bundle_leaf", "different"),
            ("bundle_path", "/invented/other"),
            ("bundle_root", {"device": 0, "inode": 0, "uid": 0}),
            ("registration_source_identity_sha256", "a" * 64),
            ("bundle_source_identity_sha256", "a" * 64),
            ("inherited", {"retained_since": None, "origin_evidence_sha256": None, "hold": 1}),
        ):
            raw = wire.encoded({**json.loads(self.provenance[key]), field: value})
            changed = {
                **args,
                "provenance_raw": {**self.provenance, key: raw},
                "expected_provenance_sha256": {
                    **args["expected_provenance_sha256"],
                    key: wire.digest(raw),
                },
            }
            # Rebind the proposed copy evidence too, so the provenance guard is challenged.
            changed = self.changed(
                changed,
                "registration",
                lambda v: v["subjects"]["unknown-object"]["copies"][key].update(
                    evidence_sha256=wire.digest(raw)
                ),
            )
            self.refuse_before_intake(changed, "aggregate-copy provenance")

    def test_rehashed_request_must_match_whole_manifest_and_root(self):
        args = self.args()
        for mutate in (
            lambda v: v["files"].pop("assessment.json"),
            lambda v: v["root"].update(inode=v["root"]["inode"] + 1),
            lambda v: v["root"].update(path=v["root"]["path"] + "/../bundle"),
            lambda v: v.update(kind="private-data"),
        ):
            self.refuse_before_intake(self.changed(args, "request", mutate))

    def test_manifest_intent_and_registration_sources_cannot_be_rehashed_stale(self):
        args = self.args()
        self.refuse_before_intake(
            self.changed(args, "manifest", lambda v: v["files"].pop("scope.json"))
        )
        self.refuse_before_intake(
            self.changed(args, "intent", lambda v: v.update(source_identity={}))
        )
        self.refuse_before_intake(
            self.changed(args, "allocation", lambda v: v.update(source_identity={}))
        )
        self.refuse_before_intake({**args, "expected_reader_identity": {}})

    def test_missing_extra_and_oversized_provenance_or_other_input_refuse_early(self):
        args = self.args()
        for mapping in (
            {},
            {**self.provenance, "extra": b"{}"},
            {key: b"x" * (reconciliation.PROVENANCE_LIMIT + 1) for key in self.provenance},
        ):
            self.refuse_before_intake({**args, "provenance_raw": mapping})
        for name, limit in (
            ("journal", removal.JOURNAL_LIMIT),
            ("outer", removal.REQUEST_LIMIT),
            ("manifest", removal.REQUEST_LIMIT),
            ("allocation", reconciliation.retention.LIMIT),
        ):
            raw = b"x" * (limit + 1)
            self.refuse_before_intake(
                {**args, name + "_raw": raw, "expected_" + name + "_sha256": wire.digest(raw)}
            )

    def test_assessment_clock_cannot_precede_registration(self):
        args = self.args()
        self.refuse_before_intake({**args, "as_of": "2026-11-05T11:59:59Z"})

    def test_changed_journal_namespace_or_source_during_derivation_refuses(self):
        args = self.args()
        real = removal.inspect
        calls = 0

        def moved(*values):
            nonlocal calls
            calls += 1
            result = real(*values)
            if calls == 1:
                (self.folder / "bundle/new-entry").write_bytes(b"invented late metadata")
            return result

        with patch.object(removal, "inspect", side_effect=moved):
            with self.assertRaisesRegex(ValueError, "unexpected retained"):
                reconciliation.propose_reconciliation(**args)
        (self.folder / "bundle/new-entry").unlink()
        changed = copy.deepcopy(args["expected_reader_identity"])
        changed["python"] = "changed"
        with patch.object(
            reconciliation,
            "source_identity",
            side_effect=[
                args["expected_reader_identity"],
                args["expected_reader_identity"],
                changed,
            ],
        ):
            with self.assertRaisesRegex(ValueError, "source changed"):
                reconciliation.propose_reconciliation(**args)

    def test_torn_journal_retains_input_and_wrong_live_journal_hash_refuses(self):
        args = self.args()
        path = self.folder / "reports/remove-derived-bundle/events.jsonl"
        torn = args["journal_raw"][:-2]
        path.write_bytes(torn)
        result = reconciliation.propose_reconciliation(
            **{**args, "journal_raw": torn, "expected_journal_sha256": wire.digest(torn)}
        )
        self.assertEqual(result["register_raw"], args["registration_raw"])
        self.assertTrue(result["removal_readback"]["truncated_journal"])
        with self.assertRaisesRegex(ValueError, "journal identity"):
            reconciliation.propose_reconciliation(**args)

    def test_final_source_check_cannot_leave_recreated_namespace_unread(self):
        args = self.args()
        calls = 0

        def source():
            nonlocal calls
            calls += 1
            if calls == 3:
                (self.folder / "bundle/recreated").write_bytes(b"invented namespace race")
            return args["expected_reader_identity"]

        with patch.object(reconciliation, "source_identity", side_effect=source):
            with self.assertRaisesRegex(ValueError, "unexpected retained"):
                reconciliation.propose_reconciliation(**args)
        self.assertEqual(calls, 3)

    def test_fully_rehashed_intent_cannot_replace_boolean_hold_with_integer(self):
        args = self.args()
        intent = json.loads(args["intent_raw"])
        intent["subjects"]["unknown-object"]["hold"] = 1
        intent_raw = wire.encoded(intent)
        manifest = json.loads(args["manifest_raw"])
        manifest["files"]["intent.json"] = {
            "bytes": len(intent_raw),
            "sha256": wire.digest(intent_raw),
        }
        manifest_raw = wire.encoded(manifest)
        allocation = json.loads(args["allocation_raw"])
        allocation["manifest_sha256"] = wire.digest(manifest_raw)
        allocation_raw = wire.encoded(allocation)
        current = json.loads(args["registration_raw"])
        provenance = {}
        for subject, copy_id in allocation["copies"].items():
            value = json.loads(args["provenance_raw"][copy_id])
            value.update(
                manifest_sha256=wire.digest(manifest_raw),
                allocation_sha256=wire.digest(allocation_raw),
            )
            provenance[copy_id] = wire.encoded(value)
            current["subjects"][subject]["copies"][copy_id]["evidence_sha256"] = wire.digest(
                provenance[copy_id]
            )
        request = json.loads(args["request_raw"])
        for name, raw in (("intent.json", intent_raw), ("manifest.json", manifest_raw)):
            request["files"][name].update(bytes=len(raw), sha256=wire.digest(raw))
        values = {
            "intent": intent_raw,
            "manifest": manifest_raw,
            "allocation": allocation_raw,
            "registration": wire.encoded(current),
            "request": wire.encoded(request),
        }
        for name, raw in values.items():
            args.update({name + "_raw": raw, "expected_" + name + "_sha256": wire.digest(raw)})
        args.update(
            provenance_raw=provenance,
            expected_provenance_sha256={key: wire.digest(raw) for key, raw in provenance.items()},
        )
        self.refuse_before_intake(args, "intent preserves original subjects")
