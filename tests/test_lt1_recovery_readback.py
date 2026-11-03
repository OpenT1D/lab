"""Invented retained observations; the bridge cannot access files or processes."""

import base64
import copy
import json
import plistlib
import unittest
from unittest.mock import patch

import test_lt1_recovery_evidence as fixtures

from experiments.lt1_diagnostic import recovery_evidence as evidence
from experiments.lt1_diagnostic import recovery_probe as probe
from experiments.lt1_diagnostic import recovery_readback as bridge


def wire(value):
    return bridge.encoded(value)


class RecoveryReadbackTests(unittest.TestCase):
    def setUp(self):
        self.fixture = fixtures.RecoveryEvidenceTests()
        self.fixture.setUp()
        f = self.fixture
        self.current = copy.deepcopy(f.register)
        self.current["policy_sha256"] = bridge.digest(wire(f.policy))
        f.scope["policy_sha256"] = self.current["policy_sha256"]
        self.current["subjects"]["object-one"]["copies"]["copy-live"]["state"] = "present"
        source = {
            "implementation": {"experiments/lt1_diagnostic/recovery_probe.py": "a" * 64},
            "python": "3.12.0",
            "executable_sha256": "b" * 64,
        }
        tools = {"diskutil": "c" * 64, "tmutil": "d" * 64}
        rows = [
            self.row("/invented/private/live", "present"),
            self.row("/invented/private/quarantine", "absence-observed"),
        ]
        self.report = {
            "schema": "opent1d.lt1-readonly-recovery-probe/1",
            "kind": "point-observation",
            "observed_from": "2026-11-05T11:59:58.100000+00:00",
            "observed_to": "2026-11-05T11:59:59.900000+00:00",
            "status": "observed",
            "collector_identity": source,
            "tool_sha256": tools,
            "data_device": 123,
            "queries": {name: self.query(name) for name in probe.COMMANDS},
            "local_readbacks": rows,
            "coverage": dict(probe.COVERAGE),
            "authorizations": dict(probe.AUTHORITY),
        }
        self.mapping = {
            "schema": "opent1d.lt1-recovery-readback-map/1",
            "kind": "invented",
            "context_sha256": f.context,
            "probe_sha256": None,
            "collector_identity": copy.deepcopy(source),
            "tool_sha256": dict(tools),
            "data_device": 123,
            "owner_uid": 456,
            "copies": {
                "copy-live": {"subject": "object-one", "channel": "live", "path": rows[0]["path"]},
                "copy-quarantine": {
                    "subject": "object-one",
                    "channel": "quarantine",
                    "path": rows[1]["path"],
                },
            },
        }

    def query(self, name):
        raw = (
            b"Snapshots for invented volume:\n"
            if name == "time_machine_snapshots"
            else plistlib.dumps({"Invented": []})
        )
        return {
            "status": "response-observed",
            "returncode": 0,
            "truncated": False,
            "plist_valid": None if name == "time_machine_snapshots" else True,
            "stdout_base64": base64.b64encode(raw).decode("ascii"),
            "stderr_base64": "",
            "stdout_sha256": bridge.digest(raw),
            "stderr_sha256": bridge.digest(b""),
        }

    def row(self, path, state):
        value = {
            "path": path,
            "observed_from": "2026-11-05T11:59:58.900000Z",
            "observed_to": "2026-11-05T11:59:59.200000Z",
            "state": state,
            "data_device_matches": True,
            "device": 123,
        }
        if state == "present":
            value.update(
                bytes=8, sha256="e" * 64, inode=789, uid=456, mode=0o600, mtime_ns=0, ctime_ns=0
            )
        return value

    def args(self):
        f = self.fixture
        report = wire(self.report)
        mapping = copy.deepcopy(self.mapping)
        mapping["probe_sha256"] = bridge.digest(report)
        raw = {
            "register": wire(self.current),
            "policy": wire(f.policy),
            "scope": wire(f.scope),
            "mapping": wire(mapping),
            "probe": report,
        }
        result = {
            key: value
            for name, data in raw.items()
            for key, value in (
                (name + "_raw", data),
                ("expected_" + name + "_sha256", bridge.digest(data)),
            )
        }
        result.update(as_of=f.as_of, expected_context_sha256=f.context)
        return result

    def run_bridge(self):
        return bridge.propose(**self.args())

    def test_positive_preserves_lineage_copies_policy_origins_and_false_gates(self):
        before = copy.deepcopy(self.current)
        result = self.run_bridge()
        proposed = json.loads(result["register_raw"])
        self.assertEqual(proposed["previous_sha256"], bridge.digest(wire(before)))
        for subject in proposed["subjects"]:
            for name in ("retained_since", "origin_evidence_sha256", "hold"):
                self.assertEqual(
                    proposed["subjects"][subject][name], before["subjects"][subject][name]
                )
            self.assertEqual(
                proposed["subjects"][subject]["copies"].keys(),
                before["subjects"][subject]["copies"].keys(),
            )
        self.assertEqual(proposed["coverage"], before["coverage"])
        self.assertEqual(proposed["policy_sha256"], before["policy_sha256"])
        self.assertEqual(self.current, before)
        self.assertFalse(result["saved_or_approved"])
        self.assertTrue(all(result[k] is False for k in bridge.AUTHORITY))

    def test_retained_provenance_binds_exact_intervals_and_evidence_hashes(self):
        result = self.run_bridge()
        obs = json.loads(result["observations_raw"])
        proposed = json.loads(result["register_raw"])
        for key, raw in result["provenance_raw"].items():
            value = json.loads(raw)
            row = next(
                r
                for r in self.report["local_readbacks"]
                if r["path"] == self.mapping["copies"][key]["path"]
            )
            self.assertEqual(value["readback"], row)
            self.assertEqual(obs["copies"][key]["evidence_sha256"], bridge.digest(raw))
            self.assertEqual(
                proposed["subjects"]["object-one"]["copies"][key]["evidence_sha256"],
                bridge.digest(raw),
            )
            self.assertEqual(obs["copies"][key]["observed_at"], "2026-11-05T11:59:58Z")
            self.assertIsNone(obs["copies"][key]["absent_since"])

    def test_successful_queries_never_complete_live_snapshot_or_backup_coverage(self):
        result = self.run_bridge()
        assessment = result["assessment"]
        self.assertFalse(assessment["scoped_removal_evidence_complete"])
        for channel in evidence.CHANNELS:
            self.assertIn("coverage-incomplete-or-stale:" + channel, assessment["blockers"])
        self.assertIn("copy-unobserved:copy-snapshot", assessment["blockers"])
        self.assertIn("copy-unobserved:copy-backup", assessment["blockers"])

    def test_unknown_keeps_old_registered_state_and_is_unknown_observation(self):
        row = self.report["local_readbacks"][0]
        self.report["local_readbacks"][0] = {
            k: row[k] for k in ("path", "observed_from", "observed_to")
        }
        self.report["local_readbacks"][0].update(
            state="unknown",
            data_device_matches=None,
            error="invented unavailable",
            inspected_bytes=3,
        )
        self.report["status"] = "partial"
        result = self.run_bridge()
        proposed = json.loads(result["register_raw"])
        self.assertEqual(
            proposed["subjects"]["object-one"]["copies"]["copy-live"],
            self.current["subjects"]["object-one"]["copies"]["copy-live"],
        )
        self.assertEqual(
            json.loads(result["observations_raw"])["copies"]["copy-live"]["state"], "unknown"
        )
        self.assertEqual(result["assessment"]["retention_timing"], "unknown")

    def test_unknown_origin_and_hold_are_not_repaired_or_extended(self):
        subject = self.current["subjects"]["object-one"]
        subject.update(retained_since=None, origin_evidence_sha256=None, hold=True)
        result = self.run_bridge()
        updated = json.loads(result["register_raw"])["subjects"]["object-one"]
        self.assertIsNone(updated["retained_since"])
        self.assertIsNone(updated["origin_evidence_sha256"])
        self.assertTrue(updated["hold"])
        self.assertEqual(result["assessment"]["retention_timing"], "unknown")
        self.assertTrue(result["assessment"]["policy_conflicts"])

    def test_reversed_future_and_outside_capture_intervals_refuse(self):
        for lower, upper in (
            ("2026-11-05T11:59:59Z", "2026-11-05T11:59:58Z"),
            ("2026-11-05T12:00:00Z", "2026-11-05T12:00:00.100Z"),
            ("2026-11-05T11:59:57Z", "2026-11-05T11:59:59Z"),
            ("2026-11-05T11:59:58", "2026-11-05T11:59:59"),
        ):
            with self.subTest(lower=lower), self.assertRaises(ValueError):
                self.report["local_readbacks"][0].update(observed_from=lower, observed_to=upper)
                self.run_bridge()

    def test_stale_lower_bound_cannot_be_rounded_forward(self):
        self.report.update(
            observed_from="2026-11-05T11:54:59.999Z", observed_to="2026-11-05T11:59:59.999Z"
        )
        for row in self.report["local_readbacks"]:
            row.update(
                observed_from="2026-11-05T11:54:59.999Z", observed_to="2026-11-05T11:59:59.999Z"
            )
        result = self.run_bridge()
        self.assertIn(
            "copy-evidence-stale-or-inconsistent:copy-live", result["assessment"]["blockers"]
        )
        self.assertEqual(
            json.loads(result["observations_raw"])["copies"]["copy-live"]["observed_at"],
            "2026-11-05T11:54:59Z",
        )

    def test_changed_collector_tool_device_and_authority_refuse(self):
        original = copy.deepcopy(self.report)
        mutations = [
            lambda r: r["collector_identity"].update(python="changed"),
            lambda r: r["tool_sha256"].update(tmutil="f" * 64),
            lambda r: r.update(data_device=True),
            lambda r: r["coverage"].update(all_copies_registered=True),
            lambda r: r["authorizations"].update(deletion_authorized=True),
        ]
        for mutate in mutations:
            self.report = copy.deepcopy(original)
            mutate(self.report)
            with self.assertRaises(ValueError):
                self.run_bridge()

    def test_wrong_subject_unregistered_duplicate_or_recovery_channel_mapping_refuse(self):
        original = copy.deepcopy(self.mapping)
        changes = [
            lambda m: m["copies"]["copy-live"].update(subject="another"),
            lambda m: m["copies"].update(unregistered=m["copies"]["copy-live"]),
            lambda m: m["copies"]["copy-live"].update(path=m["copies"]["copy-quarantine"]["path"]),
            lambda m: m["copies"]["copy-live"].update(channel="backup"),
        ]
        for mutate in changes:
            self.mapping = copy.deepcopy(original)
            mutate(self.mapping)
            with self.assertRaises(ValueError):
                self.run_bridge()

    def test_unmapped_or_duplicate_acquired_target_refuses(self):
        self.mapping["copies"].pop("copy-live")
        with self.assertRaisesRegex(ValueError, "unmapped"):
            self.run_bridge()
        self.report["local_readbacks"].append(copy.deepcopy(self.report["local_readbacks"][0]))
        with self.assertRaisesRegex(ValueError, "unique"):
            self.run_bridge()

    def test_absence_cannot_claim_payload_and_changed_kind_or_hash_refuse(self):
        self.report["local_readbacks"][1]["sha256"] = "e" * 64
        with self.assertRaisesRegex(ValueError, "nonpresent"):
            self.run_bridge()
        self.report["local_readbacks"][1].pop("sha256")
        self.mapping["kind"] = "observed"
        with self.assertRaisesRegex(ValueError, "kind"):
            self.run_bridge()
        self.mapping["kind"] = "invented"
        args = self.args()
        args["expected_probe_sha256"] = "f" * 64
        with self.assertRaisesRegex(ValueError, "bytes"):
            bridge.propose(**args)

    def test_bad_budget_missing_queries_and_optimistic_status_refuse(self):
        for mutate in (
            lambda r: r["local_readbacks"][0].update(bytes=probe.FILE_LIMIT + 1),
            lambda r: r["queries"].pop("apfs_snapshots"),
            lambda r: r["queries"]["apfs_snapshots"].update(status="unavailable"),
        ):
            report = copy.deepcopy(self.report)
            mutate(report)
            with patch.object(self, "report", report), self.assertRaises(ValueError):
                self.run_bridge()

    def test_existing_predecessor_is_checked_and_preserved(self):
        prior = wire(self.current)
        self.current["previous_sha256"] = bridge.digest(prior)
        args = self.args()
        with self.assertRaises(ValueError):
            bridge.propose(**args)
        args.update(previous_raw=prior, expected_previous_sha256=bridge.digest(prior))
        result = bridge.propose(**args)
        self.assertEqual(
            json.loads(result["register_raw"])["previous_sha256"],
            bridge.digest(args["register_raw"]),
        )

    def test_no_file_process_query_or_removal_operation(self):
        with (
            patch("builtins.open", side_effect=AssertionError("I/O")),
            patch("os.open", side_effect=AssertionError("I/O")),
            patch("os.remove", side_effect=AssertionError("deletion")),
            patch("subprocess.run", side_effect=AssertionError("spawn")),
        ):
            self.assertFalse(self.run_bridge()["saved_or_approved"])

    def test_query_exit_truncation_base64_and_hash_contradictions_refuse(self):
        original = copy.deepcopy(self.report)
        for changes in (
            {"returncode": 1},
            {"returncode": True},
            {"truncated": True},
            {"stdout_base64": "invalid***"},
            {"stdout_sha256": "e" * 64},
            {"plist_valid": False},
        ):
            self.report = copy.deepcopy(original)
            self.report["queries"]["apfs_snapshots"].update(changes)
            with self.assertRaises(ValueError):
                self.run_bridge()

    def test_unavailable_tool_and_query_remain_incomplete(self):
        self.report["tool_sha256"]["diskutil"] = None
        self.mapping["tool_sha256"]["diskutil"] = None
        self.report["queries"]["apfs_snapshots"] = {
            "status": "unavailable",
            "returncode": None,
            "error": "tool-unavailable",
        }
        self.report["status"] = "partial"
        self.assertFalse(self.run_bridge()["assessment"]["scoped_removal_evidence_complete"])

    def test_proposed_scope_and_deadline_straddle_do_not_become_timely_erasure(self):
        self.fixture.scope["decision"] = "proposed"
        result = self.run_bridge()
        self.assertIn("recovery-scope-not-approved", result["assessment"]["blockers"])
        self.fixture.policy["maximum_age_seconds"] = 4 * 86400 + 12 * 3600 - 1
        policy_sha = bridge.digest(wire(self.fixture.policy))
        self.current["policy_sha256"] = policy_sha
        self.fixture.scope["policy_sha256"] = policy_sha
        self.assertEqual(self.run_bridge()["assessment"]["retention_timing"], "unknown")

    def test_known_absence_or_presence_cannot_carry_failed_read_metadata(self):
        original = copy.deepcopy(self.report)
        for index in (0, 1):
            for changes in (
                {"error": "controlled partial read failure"},
                {"error": None},
                {"inspected_bytes": 1},
                {"inspected_bytes": 0},
            ):
                self.report = copy.deepcopy(original)
                self.report["local_readbacks"][index].update(changes)
                with (
                    self.subTest(index=index, changes=changes),
                    self.assertRaisesRegex(ValueError, "failure or partial-read"),
                ):
                    self.run_bridge()

    def test_rehashed_noncanonical_known_path_cannot_update_copy_state(self):
        for path in (
            "/invented/private/../private/live",
            "/invented/private/./live",
            "//invented/private/live",
            "/invented//private/live",
            "/invented/private/live/",
        ):
            self.report["local_readbacks"][0]["path"] = path
            self.mapping["copies"]["copy-live"]["path"] = path
            with self.subTest(path=path), self.assertRaisesRegex(ValueError, "canonical lexical"):
                self.run_bridge()

    def test_unknown_noncanonical_path_preserves_previous_state_and_uncertainty(self):
        path = "/invented/private/../private/live"
        old = copy.deepcopy(self.current["subjects"]["object-one"]["copies"]["copy-live"])
        self.report["local_readbacks"][0] = {
            "path": path,
            "observed_from": "2026-11-05T11:59:58.900Z",
            "observed_to": "2026-11-05T11:59:59.200Z",
            "state": "unknown",
            "data_device_matches": None,
            "error": "noncanonical parent",
            "inspected_bytes": 0,
        }
        self.mapping["copies"]["copy-live"]["path"] = path
        self.report["status"] = "partial"
        result = self.run_bridge()
        self.assertEqual(
            json.loads(result["register_raw"])["subjects"]["object-one"]["copies"]["copy-live"], old
        )
        observation = json.loads(result["observations_raw"])["copies"]["copy-live"]
        self.assertEqual(observation["state"], "unknown")
        self.assertIsNone(observation["absent_since"])
