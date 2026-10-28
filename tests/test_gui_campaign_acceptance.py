"""Independent Goal 2 evidence assertions, supplementary to fixed native readers."""

import copy
import json
import unittest

from tests.test_experiment_workspace_acceptance import assert_repeat_controls, require

SCENES = {"fasting": "fasting", "load_15g": "gastric_load_15g"}
SLOTS = [cell + "--r001" for cell in SCENES]


def assert_gui_campaign_resume(initial, final):
    """Require the selected two-cell GUI cancellation/resume exercise, without reruns."""
    for value in (initial, final):
        require(value["schema"] == "opent1d.maintained-campaign-report/1", "Wrong schema")
        require(value["task"] == "m4-study-secure", "Wrong maintained task")
        require(value["protocol"] == "MAINTAINED-CAMPAIGN/1", "Wrong campaign protocol")
        require([row["id"] for row in value["slots"]] == SLOTS, "Selected roster changed")
        require(value["planned_slots"] == 2, "Lost planned slots")
        require(value["planned_source_scenarios"] == 4, "Lost source/scenario denominator")
    require(initial["status"] == "interrupted" and initial["passed"] is False, "Lost cancellation")
    require(initial["accepted_slots"] == 1, "First accepted slot was not reusable")
    require(initial["accepted_source_scenarios"] == 2, "Wrong interrupted acceptance count")
    require(
        [len(row["attempts"]) for row in initial["slots"]] == [1, 1], "Wrong cancellation point"
    )
    interrupted = initial["slots"][1]["attempts"][0]
    require(interrupted["outcome"]["status"] == "interrupted", "Interrupted attempt relabeled")
    require(interrupted["accepted"] is False, "Interrupted attempt falsely accepted")
    require(final["status"] == "completed" and final["passed"] is True, "Incomplete resume")
    require(final["accepted_slots"] == 2, "Resume did not accept both slots")
    require(final["accepted_source_scenarios"] == 4, "Incomplete resumed denominator")
    require([len(row["attempts"]) for row in final["slots"]] == [1, 2], "Wrong retained attempts")
    require(
        initial["slots"][0] == final["slots"][0], "Accepted first slot changed instead of reuse"
    )
    require(interrupted == final["slots"][1]["attempts"][0], "Interrupted evidence changed")
    retry = final["slots"][1]["attempts"][1]
    require(retry["session"] == 2 and retry["attempt"] == 2, "Retry identity changed")
    require(
        retry["previous_attempt_manifest_sha256"] == interrupted["manifest_sha256"],
        "Retry predecessor missing",
    )
    require(
        [row["scheduled_slots"] for row in final["sessions"]] == [2, 1], "Reused slot dispatched"
    )
    for row in final["slots"]:
        require(row["accepted"] is True, "Unaccepted slot")
        accepted = [attempt for attempt in row["attempts"] if attempt["accepted"]]
        require(len(accepted) == 1, "Missing unique authoritative attempt")
        native = accepted[0]["native_report"]
        require(native["passed"] is True and native["status"] == "completed", "Native not accepted")
        require(native["protocol"] == "M4-STUDY-SECURE/1", "Wrong native protocol")
        require(native["configuration"]["scenarios"] == [SCENES[row["cell"]]], "Scenario changed")
        require(
            native["denominators"]
            == {
                "sources": 2,
                "accepted_sources": 2,
                "source_scenarios": 2,
                "accepted_source_scenarios": 2,
                "pairs": 1,
                "accepted_pairs": 1,
            },
            "Native complete-slot denominator differs",
        )
        require(len(native["sources"]) == 2, "Source disappeared")
        require(
            all(source["accepted"] is True for source in native["sources"].values()),
            "Partial source",
        )


def assert_clean_ownership(observed, live_after, *, forced=False):
    """Require fresh OS-start observations and an actually checked terminal process table."""
    require(bool(observed), "No live ownership was observed")
    require(forced is False and live_after == [], "Owned process survived or forced cleanup")
    require(len({row["pid"] for row in observed}) == len(observed), "Duplicated process identity")
    for row in observed:
        require(type(row["pid"]) is int and row["pid"] > 0, "Invalid owned PID")
        require(
            isinstance(row["start"], str) and row["start"].startswith(("darwin:", "linux:")),
            "Ownership lacks OS start identity",
        )


def _canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False)


def scientific_report(value, plan):
    """Normalize only enumerated administrative fields; preserve all scientific values."""
    result = copy.deepcopy(value)
    provenance = result["provenance"]
    require(
        set(provenance)
        == {"checkout_path", "git_dirty", "git_head", "platform", "python", "sources"},
        "Unexpected provenance shape",
    )
    require(isinstance(provenance["checkout_path"], str), "Missing checkout provenance")
    provenance["checkout_path"] = "<checkout>"
    del provenance["git_head"], provenance["git_dirty"]

    def argument(value):
        require(isinstance(value, str), "Non-string command argument")
        if value == plan["coordinator_executable"]:
            return "<coordinator-python>"
        for origin, token in (
            (plan["archive_original_path"], "<archive>"),
            (plan["provenance"]["checkout_path"], "<checkout>"),
        ):
            if value == origin or value.startswith(origin + "/"):
                return token + value[len(origin) :]
        return value

    for owner in [result["reference"], *result["sources"].values()]:
        execution = owner["execution"]
        execution.pop("duration_seconds", None)
        for attempt in execution.get("attempts", []):
            attempt["argv"] = [argument(value) for value in attempt["argv"]]
    return result


def assert_native_report_parity(left, right, left_plan, right_plan):
    """Require complete report parity after both independent native readers have passed."""
    require(left["configuration"]["scenarios"] == ["fasting"], "Wrong selected parity condition")
    assert_repeat_controls(left, right, "fasting")
    require(
        _canonical(scientific_report(left, left_plan))
        == _canonical(scientific_report(right, right_plan)),
        "GUI/CLI scientific report differs",
    )


def _ledger_fixture():
    slots = []
    for index, (cell, scenario) in enumerate(SCENES.items()):
        native = {
            "passed": True,
            "status": "completed",
            "protocol": "M4-STUDY-SECURE/1",
            "configuration": {"scenarios": [scenario]},
            "denominators": {
                "sources": 2,
                "accepted_sources": 2,
                "source_scenarios": 2,
                "accepted_source_scenarios": 2,
                "pairs": 1,
                "accepted_pairs": 1,
            },
            "sources": {source: {"accepted": True} for source in ("dalla_man", "ultradian")},
        }
        attempt = {
            "session": 1,
            "attempt": 1,
            "manifest_sha256": str(index) * 64,
            "previous_attempt_manifest_sha256": None,
            "outcome": {"status": "completed"},
            "accepted": True,
            "native_report": native,
        }
        slots.append({"id": cell + "--r001", "cell": cell, "accepted": True, "attempts": [attempt]})
    retry = slots[1]["attempts"][0]
    interrupted = copy.deepcopy(retry)
    interrupted.update(accepted=False, native_report=None, outcome={"status": "interrupted"})
    retry.update(
        session=2, attempt=2, previous_attempt_manifest_sha256=interrupted["manifest_sha256"]
    )
    slots[1]["attempts"].insert(0, interrupted)
    final = {
        "schema": "opent1d.maintained-campaign-report/1",
        "task": "m4-study-secure",
        "protocol": "MAINTAINED-CAMPAIGN/1",
        "status": "completed",
        "passed": True,
        "planned_slots": 2,
        "accepted_slots": 2,
        "planned_source_scenarios": 4,
        "accepted_source_scenarios": 4,
        "slots": slots,
        "sessions": [{"scheduled_slots": 2}, {"scheduled_slots": 1}],
    }
    initial = copy.deepcopy(final)
    initial.update(
        status="interrupted", passed=False, accepted_slots=1, accepted_source_scenarios=2
    )
    initial["sessions"] = initial["sessions"][:1]
    initial["slots"][1].update(accepted=False, attempts=[interrupted])
    return initial, final


def _native_fixture(path):
    from tests.test_experiment_workspace_acceptance import curve_fixture

    report = curve_fixture()
    report["provenance"] = {
        "checkout_path": path,
        "git_head": "1" * 40,
        "git_dirty": False,
        "platform": "darwin",
        "python": "3.12.13",
        "sources": {"source.py": "a" * 64},
    }
    plan = {
        "coordinator_executable": path + "/.venv/bin/python",
        "archive_original_path": path + "/archive",
        "provenance": {"checkout_path": path},
    }
    execution = {
        "duration_seconds": 10,
        "attempts": [{"argv": [plan["coordinator_executable"], plan["archive_original_path"]]}],
    }
    report["reference"] = {"execution": copy.deepcopy(execution), "accepted": True}
    report["sources"]["a"].update(
        execution=execution,
        numerical={"passed": True, "solver_tolerance": 0.0001},
        observer={"passed": True},
    )
    report["pairs"] = [{"accepted": True, "signed_auc_difference": 1.5}]
    return report, plan


class GuiCampaignAcceptanceAssertionTests(unittest.TestCase):
    def test_resume_preserves_first_acceptance_and_interrupted_second_attempt(self):
        initial, final = _ledger_fixture()
        assert_gui_campaign_resume(initial, final)
        final["slots"][0]["attempts"][0]["manifest_sha256"] = "changed"
        with self.assertRaisesRegex(AssertionError, "first slot changed"):
            assert_gui_campaign_resume(initial, final)

    def test_lost_attempt_link_dispatch_or_native_case_is_not_complete(self):
        for fault in ("link", "dispatch", "pair", "source"):
            with self.subTest(fault=fault):
                initial, final = _ledger_fixture()
                if fault == "link":
                    final["slots"][1]["attempts"][1]["previous_attempt_manifest_sha256"] = None
                elif fault == "dispatch":
                    final["sessions"][1]["scheduled_slots"] = 2
                else:
                    native = final["slots"][1]["attempts"][1]["native_report"]
                    if fault == "pair":
                        native["denominators"]["accepted_pairs"] = 0
                    else:
                        native["sources"]["ultradian"]["accepted"] = False
                with self.assertRaises(AssertionError):
                    assert_gui_campaign_resume(initial, final)

    def test_saved_pid_or_unchecked_survivor_cannot_establish_clean_ownership(self):
        observed = [{"pid": 123, "start": "darwin:1234:5"}]
        assert_clean_ownership(observed, [])
        for rows, remaining, forced in (
            ([], [], False),
            ([{"pid": 123, "start": "saved-pid"}], [], False),
            (observed, observed, False),
            (observed, [], True),
        ):
            with self.subTest(rows=rows, remaining=remaining, forced=forced):
                with self.assertRaises(AssertionError):
                    assert_clean_ownership(rows, remaining, forced=forced)

    def test_parity_allows_enumerated_administration_only(self):
        left, left_plan = _native_fixture("/gui-checkout")
        right, right_plan = _native_fixture("/cli-checkout")
        right["provenance"].update(git_head="2" * 40, git_dirty=True)
        right["reference"]["execution"]["duration_seconds"] = 25
        assert_native_report_parity(left, right, left_plan, right_plan)

    def test_same_controls_cannot_hide_scientific_or_runtime_mismatch(self):
        for fault in ("pair", "tolerance", "python", "platform", "source", "scientific_duration"):
            with self.subTest(fault=fault):
                left, left_plan = _native_fixture("/gui-checkout")
                right, right_plan = _native_fixture("/cli-checkout")
                if fault == "pair":
                    right["pairs"][0]["signed_auc_difference"] += 0.01
                elif fault == "tolerance":
                    right["sources"]["a"]["numerical"]["solver_tolerance"] *= 2
                elif fault in {"python", "platform"}:
                    right["provenance"][fault] = "changed"
                elif fault == "source":
                    right["sources"]["a"]["source_sha256"] = "b" * 64
                else:
                    left["sources"]["a"]["numerical"]["duration_seconds"] = 1
                    right["sources"]["a"]["numerical"]["duration_seconds"] = 2
                with self.assertRaises(AssertionError):
                    assert_native_report_parity(left, right, left_plan, right_plan)


if __name__ == "__main__":
    unittest.main()
