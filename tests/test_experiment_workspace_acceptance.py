"""Independent acceptance assertions for retained campaign evidence and repeats.

These assertions supplement fixed authoritative readers during actual acceptance.
They neither reconstruct archives nor replace their scientific validation.
"""

import copy
import math
import unittest

SCENES = {"fasting": "fasting", "load_15g": "gastric_load_15g"}
EXPECTED_SLOTS = [f"{cell}--r{repeat:03d}" for cell in SCENES for repeat in (1, 2)]


def require(condition, reason):
    if not condition:
        raise AssertionError(reason)


def assert_resume_evidence(initial, final, *, no_op=False):
    """Assert the independently selected four-slot, interrupted-second-slot exercise."""
    for value in (initial, final):
        require(value["schema"] == "opent1d.maintained-campaign-report/1", "Wrong schema")
        require(value["task"] == "m4-study-secure", "Wrong execution task")
        require(value["protocol"] == "MAINTAINED-CAMPAIGN/1", "Wrong protocol")
        require([row["id"] for row in value["slots"]] == EXPECTED_SLOTS, "Roster changed")
        require(value["planned_slots"] == 4, "Lost planned slots")
        require(value["planned_source_scenarios"] == 8, "Lost planned source/scenario cases")
    require(initial["passed"] is False and initial["status"] == "interrupted", "Lost interruption")
    require(initial["accepted_slots"] == 1, "First slot was not independently reusable")
    require(initial["accepted_source_scenarios"] == 2, "Initial complete-slot accounting differs")
    require([len(row["attempts"]) for row in initial["slots"]] == [1, 1, 0, 0], "Wrong stop point")
    require(
        initial["slots"][1]["attempts"][0]["outcome"]["status"] == "interrupted",
        "Second attempt was erased or relabeled",
    )
    require(final["passed"] is True and final["status"] == "completed", "Incomplete campaign")
    require(final["accepted_slots"] == 4, "Not all slots accepted")
    require(final["accepted_source_scenarios"] == 8, "Incomplete complete-slot accounting")
    require(
        [len(row["attempts"]) for row in final["slots"]] == [1, 2, 1, 1], "Wrong retry coverage"
    )
    require(
        final["slots"][0] == initial["slots"][0],
        "An accepted first slot was rerun or changed instead of reused",
    )
    old_attempt = initial["slots"][1]["attempts"][0]
    retry = final["slots"][1]["attempts"][1]
    require(final["slots"][1]["attempts"][0] == old_attempt, "Interrupted evidence changed")
    require(
        retry["previous_attempt_manifest_sha256"] == old_attempt["manifest_sha256"],
        "Retry lost its predecessor identity",
    )
    require(retry["session"] == 2 and retry["attempt"] == 2, "Retry was not a new attempt")
    require(
        [row["scheduled_slots"] for row in final["sessions"]] == ([4, 3, 0] if no_op else [4, 3]),
        "Resume or no-op dispatched the wrong slots",
    )
    for row in final["slots"]:
        require(row["accepted"] is True, "A slot is not accepted")
        accepted = [attempt for attempt in row["attempts"] if attempt["accepted"]]
        require(len(accepted) == 1, "Acceptance must identify one authoritative attempt")
        native = accepted[0]["native_report"]
        require(native["passed"] is True, "Campaign acceptance bypassed native acceptance")
        require(native["configuration"]["scenarios"] == [SCENES[row["cell"]]], "Condition changed")
        require(
            native["denominators"]["source_scenarios"] == 2
            and native["denominators"]["accepted_source_scenarios"] == 2,
            "Native complete-slot denominator differs",
        )
        require(len(native["sources"]) == 2, "A native source disappeared")
        require(
            all(source["accepted"] is True for source in native["sources"].values()),
            "Partial source",
        )


def assert_repeat_controls(left, right, scenario):
    """Assert exact saved control curves for two already reader-accepted native studies."""
    grid = [index / 4 for index in range(961)]
    for value in (left, right):
        require(value["passed"] is True, "Unaccepted native archive")
        require(value["protocol"] == "M4-STUDY-SECURE/1", "Wrong native protocol")
        require(value["common_controls"]["passed"] is True, "Shared controls failed")
    require(left["configuration"] == right["configuration"], "Repeat conditions differ")
    require(set(left["sources"]) == set(right["sources"]), "Repeat source roster differs")
    for identity in left["sources"]:
        for field in ("source_sha256", "declaration_sha256"):
            require(
                left["sources"][identity][field] == right["sources"][identity][field],
                "Source changed",
            )
    for mode in ("host_constant_basal", "bc008_reference"):
        key = scenario + "--" + mode
        a, b = (value["common_controls"]["trajectories"][key] for value in (left, right))
        for curve in (a, b):
            require(curve["times_min"] == grid, "Control time grid differs")
            for field in ("glucose_mg_dl", "insulin_pmol_l", "cpeptide_pmol_l"):
                values = curve[field]
                require(len(values) == 961, "Control curve length differs")
                require(
                    all(type(item) in (int, float) and math.isfinite(item) for item in values),
                    "Nonfinite curve",
                )
        require(a == b, "Independent repeat changed a shared control trajectory")


def ledger_fixture():
    slots = []
    for index, identity in enumerate(EXPECTED_SLOTS):
        cell, _ = identity.split("--")
        native = {
            "passed": True,
            "configuration": {"scenarios": [SCENES[cell]]},
            "denominators": {"source_scenarios": 2, "accepted_source_scenarios": 2},
            "sources": {name: {"accepted": True} for name in ("a", "b")},
        }
        attempt = {
            "session": 1 if index < 2 else 2,
            "attempt": 1,
            "manifest_sha256": str(index) * 64,
            "previous_attempt_manifest_sha256": None,
            "outcome": {"status": "completed"},
            "accepted": True,
            "native_report": native,
        }
        slots.append({"id": identity, "cell": cell, "accepted": True, "attempts": [attempt]})
    interrupted = copy.deepcopy(slots[1]["attempts"][0])
    interrupted.update(accepted=False, native_report=None, outcome={"status": "interrupted"})
    slots[1]["attempts"][0].update(
        session=2, attempt=2, previous_attempt_manifest_sha256=interrupted["manifest_sha256"]
    )
    slots[1]["attempts"].insert(0, interrupted)
    final = {
        "schema": "opent1d.maintained-campaign-report/1",
        "task": "m4-study-secure",
        "protocol": "MAINTAINED-CAMPAIGN/1",
        "passed": True,
        "status": "completed",
        "planned_slots": 4,
        "accepted_slots": 4,
        "planned_source_scenarios": 8,
        "accepted_source_scenarios": 8,
        "slots": slots,
        "sessions": [{"scheduled_slots": 4}, {"scheduled_slots": 3}],
    }
    initial = copy.deepcopy(final)
    initial.update(
        passed=False, status="interrupted", accepted_slots=1, accepted_source_scenarios=2
    )
    initial["sessions"] = initial["sessions"][:1]
    initial["slots"][1].update(accepted=False, attempts=[interrupted])
    for row in initial["slots"][2:]:
        row.update(accepted=False, attempts=[])
    return initial, final


def curve_fixture():
    curve = {
        "times_min": [index / 4 for index in range(961)],
        "glucose_mg_dl": [100.0] * 961,
        "insulin_pmol_l": [10.0] * 961,
        "cpeptide_pmol_l": [100.0] * 961,
    }
    return {
        "passed": True,
        "protocol": "M4-STUDY-SECURE/1",
        "configuration": {"scenarios": ["fasting"]},
        "sources": {"a": {"source_sha256": "a" * 64, "declaration_sha256": "b" * 64}},
        "common_controls": {
            "passed": True,
            "trajectories": {
                "fasting--" + mode: copy.deepcopy(curve)
                for mode in ("host_constant_basal", "bc008_reference")
            },
        },
    }


class WorkspaceAcceptanceAssertionTests(unittest.TestCase):
    def test_retained_retry_and_no_op_are_distinct_from_rerunning_acceptance(self):
        initial, final = ledger_fixture()
        assert_resume_evidence(initial, final)
        final["sessions"].append({"scheduled_slots": 0})
        assert_resume_evidence(initial, final, no_op=True)
        final["slots"][0]["attempts"].append(copy.deepcopy(final["slots"][0]["attempts"][0]))
        with self.assertRaisesRegex(AssertionError, "retry coverage"):
            assert_resume_evidence(initial, final, no_op=True)

    def test_lost_interruption_or_wrong_predecessor_is_not_accepted(self):
        initial, final = ledger_fixture()
        final["slots"][1]["attempts"].pop(0)
        with self.assertRaisesRegex(AssertionError, "retry coverage"):
            assert_resume_evidence(initial, final)
        initial, final = ledger_fixture()
        final["slots"][1]["attempts"][1]["previous_attempt_manifest_sha256"] = "changed"
        with self.assertRaisesRegex(AssertionError, "predecessor"):
            assert_resume_evidence(initial, final)

    def test_complete_campaign_cannot_hide_partial_native_acceptance(self):
        initial, final = ledger_fixture()
        final["slots"][2]["attempts"][0]["native_report"]["sources"]["a"]["accepted"] = False
        with self.assertRaisesRegex(AssertionError, "Partial source"):
            assert_resume_evidence(initial, final)

    def test_same_repeat_controls_require_every_saved_variable_and_time_point(self):
        left = curve_fixture()
        right = copy.deepcopy(left)
        assert_repeat_controls(left, right, "fasting")
        right["common_controls"]["trajectories"]["fasting--bc008_reference"]["cpeptide_pmol_l"][
            400
        ] += 1
        with self.assertRaisesRegex(AssertionError, "trajectory"):
            assert_repeat_controls(left, right, "fasting")

    def test_identical_arrays_cannot_hide_nonfinite_grid_or_source_changes(self):
        for edit in ("time", "nonfinite", "source"):
            with self.subTest(edit=edit):
                left = curve_fixture()
                right = copy.deepcopy(left)
                if edit == "source":
                    right["sources"]["a"]["source_sha256"] = "c" * 64
                else:
                    curve = right["common_controls"]["trajectories"]["fasting--host_constant_basal"]
                    curve["times_min" if edit == "time" else "insulin_pmol_l"][40] = (
                        11 if edit == "time" else float("nan")
                    )
                with self.assertRaises(AssertionError):
                    assert_repeat_controls(left, right, "fasting")


if __name__ == "__main__":
    unittest.main()
