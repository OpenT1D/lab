"""Maintenance evidence permits one bound startup downgrade, never data loss."""

import copy
import json
import tempfile
import unittest
from pathlib import Path

from scripts.windows_preservation import (
    compare_preservation,
    identity,
    restart_expectation,
)

JOB_ID = "job-" + "1" * 32
ENTRY_ID = "obs-study-" + "2" * 32
JOB = f"workspace/results/gui/{JOB_ID}/job.json"
ENTRY = f"workspace/results/gui/observations/archives/{ENTRY_ID}/record.json"
REPORT = f"workspace/results/gui/observations/archives/{ENTRY_ID}/archive/report.json"


def encode(value):
    return json.dumps(value, sort_keys=True, indent=2, allow_nan=False).encode() + b"\n"


def record():
    return {
        "id": ENTRY_ID,
        "schema": "opent1d.gui-observation-entry/1",
        "state": "completed",
        "verification": "native_reader_verified",
        "artifacts_sha256": {"report.json": "a" * 64, "report.md": "b" * 64},
        "coverage": {"complete_cohort": True},
        "display_name": "Invented example",
    }


class WindowsPreservationTests(unittest.TestCase):
    def test_exact_bytes_remain_the_default_and_new_files_are_separate(self):
        before = {REPORT: identity(b"original report"), ENTRY: identity(encode(record()))}
        self.assertTrue(compare_preservation(before, before)["all_original_bytes_identical"])
        after = {**before, "workspace/extra.json": identity(b"new")}
        result = compare_preservation(before, after)
        self.assertEqual((result["original_files_unchanged"], result["additional_files"]), (2, 1))
        value = record()
        value["verification"] = "recorded_verification"
        with self.assertRaisesRegex(ValueError, "Saved data changed"):
            compare_preservation(before, {**before, ENTRY: identity(encode(value))})

    def test_expected_downgrade_is_counted_without_claiming_byte_equality(self):
        raw = encode(record())
        expectation = restart_expectation(ENTRY, raw)
        value = record()
        value["verification"] = "recorded_verification"
        before = {ENTRY: identity(raw), REPORT: identity(b"report")}
        after = {**before, ENTRY: identity(encode(value))}
        result = compare_preservation(before, after, expected_bookkeeping={ENTRY: expectation})
        self.assertEqual(result["original_files_unchanged"], 1)
        self.assertEqual(result["expected_bookkeeping_changes"], [{"path": ENTRY, **expectation}])
        self.assertFalse(result["all_original_bytes_identical"])
        self.assertFalse(result["fresh_verification_claim"])

    def test_report_data_missing_or_other_json_change_cannot_hide_in_downgrade(self):
        raw = encode(record())
        expected = {ENTRY: restart_expectation(ENTRY, raw)}
        before = {ENTRY: identity(raw), REPORT: identity(b"report")}
        changed = record()
        changed["verification"] = "recorded_verification"
        for label, after in (
            ("report", {ENTRY: identity(encode(changed)), REPORT: identity(b"corrupt")}),
            ("missing", {ENTRY: identity(encode(changed))}),
            (
                "other field",
                {
                    ENTRY: identity(encode({**changed, "display_name": "changed"})),
                    REPORT: before[REPORT],
                },
            ),
            ("format", {ENTRY: identity(encode(changed) + b"\n"), REPORT: before[REPORT]}),
        ):
            with (
                self.subTest(label=label),
                self.assertRaisesRegex(ValueError, "Saved data changed"),
            ):
                compare_preservation(before, after, expected_bookkeeping=expected)

    def test_nested_marker_is_not_replaced_or_used_as_permission(self):
        value = record()
        value["nested"] = {"verification": "native_reader_verified"}
        expectation = restart_expectation(ENTRY, encode(value))
        value["verification"] = "recorded_verification"
        self.assertEqual(expectation["after"], identity(encode(value)))
        value["nested"]["verification"] = "recorded_verification"
        with self.assertRaisesRegex(ValueError, "Saved data changed"):
            compare_preservation(
                {ENTRY: expectation["before"]},
                {ENTRY: identity(encode(value))},
                expected_bookkeeping={ENTRY: expectation},
            )
        value.pop("verification")
        self.assertIsNone(restart_expectation(ENTRY, encode(value)))

    def test_wrong_path_schema_identity_or_active_state_gets_no_exception(self):
        base = record()
        for name, value in (
            (REPORT, base),
            (ENTRY.replace("workspace/", "durable/"), base),
            (ENTRY, {**base, "schema": "other"}),
            (ENTRY, {**base, "id": "obs-study-" + "3" * 32}),
            (ENTRY, {**base, "state": "running"}),
            (ENTRY, {**base, "verification": "verifying"}),
            (ENTRY, {**base, "verification": "recorded_verification"}),
        ):
            with self.subTest(name=name, value=value):
                self.assertIsNone(restart_expectation(name, encode(value)))
        self.assertIsNone(restart_expectation(ENTRY, encode(base).replace(b'"state":', b'"id":')))
        self.assertIsNone(restart_expectation(ENTRY, b"\xef\xbb\xbf" + encode(base)))

    def test_allowance_cannot_move_to_another_original_or_accept_bad_identity(self):
        raw = encode(record())
        expectation = restart_expectation(ENTRY, raw)
        before = {ENTRY: identity(raw)}
        for expected in (
            {REPORT: expectation},
            {ENTRY: {**expectation, "before": identity(b"other")}},
            {ENTRY: {**expectation, "record_id": "obs-study-" + "3" * 32}},
            {ENTRY: {**expectation, "after": {"bytes": True, "sha256": "a" * 64}}},
        ):
            with self.subTest(expected=expected), self.assertRaises(ValueError):
                compare_preservation(before, before, expected_bookkeeping=expected)
        for name in (
            "../report.json",
            "workspace/../report.json",
            "workspace//report.json",
            "workspace\\report.json",
            "workspace/C:report.json",
        ):
            with self.subTest(name=name), self.assertRaises(ValueError):
                compare_preservation({name: identity(raw)}, before)

    def test_closed_job_and_sampling_are_bound_to_their_own_schema_and_path(self):
        job = {
            "schema": "opent1d.gui-job/1",
            "id": JOB_ID,
            "state": "completed",
            "exit_code": 0,
            "pid": None,
            "cleanup_forced": False,
            "remaining_owned_processes": [],
            "verification": "native_reader_verified",
        }
        self.assertIsNotNone(restart_expectation(JOB, encode(job)))
        for field, value in (
            ("state", "running"),
            ("pid", 123),
            ("exit_code", None),
            ("exit_code", False),
            ("remaining_owned_processes", [123]),
            ("cleanup_forced", True),
        ):
            with self.subTest(field=field, value=value):
                self.assertIsNone(restart_expectation(JOB, encode({**job, field: value})))
        sample = {
            **record(),
            "id": "sam-study-" + "4" * 32,
            "schema": "opent1d.gui-sampling-entry/1",
        }
        path = f"workspace/results/gui/sampling/archives/{sample['id']}/record.json"
        self.assertIsNotNone(restart_expectation(path, encode(sample)))

    def test_real_gui_restart_matches_only_the_precomputed_bookkeeping_bytes(self):
        from experiments.gui.service import Service
        from experiments.gui.service import encode as producer_encode

        entry = record()
        job = {
            "schema": "opent1d.gui-job/1",
            "id": JOB_ID,
            "task": "m4-study-secure",
            "operation": "reconstruct",
            "state": "completed",
            "exit_code": 0,
            "pid": None,
            "cleanup_forced": False,
            "remaining_owned_processes": [],
            "verification": "native_reader_verified",
            "commands": [],
            "result": {"report_sha256": "a" * 64},
        }
        originals = {
            JOB: producer_encode(job),
            ENTRY: producer_encode(entry),
            REPORT: b'{"synthetic": true}\n',
        }
        expected = {
            name: item
            for name, raw in originals.items()
            if (item := restart_expectation(name, raw)) is not None
        }
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            for name, raw in originals.items():
                path = root / name.removeprefix("workspace/")
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(raw)
            service = Service(root)
            try:
                self.assertEqual(service.jobs[JOB_ID]["verification"], "recorded_verification")
                self.assertEqual(
                    service.observations.entries[ENTRY_ID]["verification"], "recorded_verification"
                )
            finally:
                service.close()
            current = {
                name: identity((root / name.removeprefix("workspace/")).read_bytes())
                for name in originals
            }
            result = compare_preservation(
                {name: identity(raw) for name, raw in originals.items()},
                current,
                expected_bookkeeping=expected,
            )
            self.assertEqual(result["original_files_unchanged"], 1)
            self.assertEqual(len(result["expected_bookkeeping_changes"]), 2)
            damaged = copy.deepcopy(current)
            damaged[REPORT] = identity(b"corrupted report")
            with self.assertRaisesRegex(ValueError, "Saved data changed"):
                compare_preservation(
                    {name: identity(raw) for name, raw in originals.items()},
                    damaged,
                    expected_bookkeeping=expected,
                )
