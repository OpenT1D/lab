"""Bounded native M5 presentation and declarations; no scientific recomputation."""

import math
import re

from .service import digest, encode

MAX_NATIVE_FILE = 500_000
SCHEMA = "m5-researcher-workflow/1"
DECLARATION_KEYS = {
    "schema",
    "model_id",
    "rights_basis",
    "input_schema",
    "output_unit",
    "source_sha256",
    "state_sha256",
    "runtime",
    "training",
}
ATTEMPT_FAILURES = {"timeout", "worker_failed", "invalid_output", "interrupted"}
CANDIDATE_STATUSES = {
    "completed",
    "failed",
    "interrupted",
    "incomplete",
    "not_reproducible",
    "not_attempted",
}


def require(condition, message):
    if not condition:
        raise ValueError(message)


def sha(value):
    return isinstance(value, str) and re.fullmatch(r"[0-9a-f]{64}", value) is not None


def finite(value):
    return type(value) in (int, float) and math.isfinite(value)


def runtime(value):
    require(
        isinstance(value, dict)
        and set(value) == {"implementation", "python_version", "python_major_minor"}
        and value["implementation"] == "CPython"
        and all(isinstance(item, str) and 0 < len(item) <= 128 for item in value.values()),
        "Malformed native M5 runtime",
    )


def validate_report(report):
    require(
        isinstance(report, dict) and report.get("schema") == SCHEMA, "Unsupported native M5 report"
    )
    require(
        report.get("claim") == "invented_pipeline_check_only"
        and report.get("human_execution_authorized") is False
        and report.get("treatment_effect_or_cure_estimated") is False
        and report.get("training_provenance") == "researcher_declared_not_independently_verified"
        and report.get("metric") == "mean absolute error in reported insulin U/day",
        "Malformed synthetic M5 scope",
    )
    require(
        isinstance(report.get("model_id"), str)
        and re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]{0,127}", report["model_id"])
        and sha(report.get("source_sha256"))
        and sha(report.get("state_sha256")),
        "Malformed native M5 model identity",
    )
    for key, expected in {
        "roster_count": 32,
        "development_roster_count": 24,
        "evaluation_roster_count": 8,
        "development_eligible_count": 20,
        "evaluation_eligible_count": 7,
        "excluded_count": 5,
    }.items():
        require(
            type(report.get(key)) is int and report[key] == expected,
            "Malformed fixed M5 roster counts",
        )
    people = report.get("people")
    require(isinstance(people, list) and len(people) == 32, "Malformed native M5 roster")
    expected_aliases = [f"SYN{i:03d}" for i in range(1, 33)]
    for person, alias in zip(people, expected_aliases, strict=True):
        require(
            isinstance(person, dict)
            and person.get("alias") == alias
            and person.get("split") == ("evaluation" if int(alias[-3:]) % 4 == 0 else "development")
            and type(person.get("eligible")) is bool
            and isinstance(person.get("issues"), list)
            and all(isinstance(issue, str) and len(issue) <= 500 for issue in person["issues"])
            and person["eligible"] == (not person["issues"])
            and isinstance(person.get("intervening_infusion_days"), list)
            and all(finite(day) and 0 <= day <= 365 for day in person["intervening_infusion_days"])
            and type(person.get("y1_present")) is bool
            and type(person.get("visit15_present")) is bool,
            "Malformed native M5 roster row",
        )
    for split, expected in (("development", 20), ("evaluation", 7)):
        require(
            sum(person["eligible"] for person in people if person["split"] == split) == expected,
            "M5 roster eligibility counts differ",
        )
    eligible = [
        person["alias"]
        for person in people
        if person["split"] == "evaluation" and person["eligible"]
    ]
    predictions = report.get("evaluation_predictions")
    require(
        isinstance(predictions, list) and len(predictions) == 7,
        "Malformed native M5 evaluation predictions",
    )
    pairs, execution_complete = 0, True
    for item, alias in zip(predictions, eligible, strict=True):
        require(
            isinstance(item, dict)
            and item.get("alias") == alias
            and item.get("candidate_status") in CANDIDATE_STATUSES
            and all(
                finite(item.get(key)) and 0 <= item[key] <= 1000
                for key in ("observed_reported_insulin_mean_u_day", "baseline_prediction_u_day")
            ),
            "Malformed native M5 prediction row",
        )
        attempts = item.get("attempts")
        require(
            isinstance(attempts, list) and len(attempts) <= 2, "Malformed native M5 attempt roster"
        )
        for index, attempt in enumerate(attempts, 1):
            require(
                isinstance(attempt, dict)
                and set(attempt) == {"attempt", "status", "prediction_u_day", "runtime"}
                and type(attempt["attempt"]) is int
                and attempt["attempt"] == index,
                "Malformed native M5 attempt identity",
            )
            if attempt["status"] == "completed":
                require(
                    finite(attempt["prediction_u_day"])
                    and 0 <= attempt["prediction_u_day"] <= 1000,
                    "Malformed native M5 attempt prediction",
                )
                runtime(attempt["runtime"])
            else:
                require(
                    attempt["status"] in ATTEMPT_FAILURES
                    and attempt["prediction_u_day"] is None
                    and attempt["runtime"] is None,
                    "Malformed native M5 failure attempt",
                )
        if not attempts:
            status = "not_attempted"
        elif any(attempt["status"] == "interrupted" for attempt in attempts):
            status = "interrupted"
        elif len(attempts) < 2:
            status = "incomplete"
        elif any(attempt["status"] != "completed" for attempt in attempts):
            status = "failed"
        elif (
            attempts[0]["prediction_u_day"] != attempts[1]["prediction_u_day"]
            or attempts[0]["runtime"] != attempts[1]["runtime"]
        ):
            status = "not_reproducible"
        else:
            status = "completed"
        require(item["candidate_status"] == status, "M5 prediction and attempts disagree")
        require(
            item.get("candidate_prediction_u_day") is None
            or (
                finite(item["candidate_prediction_u_day"])
                and 0 <= item["candidate_prediction_u_day"] <= 1000
            ),
            "Malformed native M5 paired prediction",
        )
        require(
            item.get("candidate_prediction_u_day")
            == (attempts[0]["prediction_u_day"] if status == "completed" else None),
            "M5 paired prediction and attempts disagree",
        )
        pairs += status == "completed"
        execution_complete = (
            execution_complete
            and len(attempts) == 2
            and all(attempt["status"] != "interrupted" for attempt in attempts)
        )
    require(
        type(report.get("paired_count")) is int
        and report["paired_count"] == pairs
        and finite(report.get("candidate_coverage"))
        and report["candidate_coverage"] == pairs / 7
        and report.get("comparison_status") == ("complete" if pairs == 7 else "incomplete")
        and type(report.get("candidate_execution_complete")) is bool
        and report["candidate_execution_complete"] == execution_complete,
        "Malformed native M5 paired/execution accounting",
    )
    require(
        finite(report.get("baseline_mae_all_eligible_u_day"))
        and report["baseline_mae_all_eligible_u_day"] >= 0,
        "Malformed native M5 full baseline metric",
    )
    for key in (
        "baseline_mae_paired_u_day",
        "candidate_mae_paired_u_day",
        "mae_change_candidate_minus_baseline_u_day",
    ):
        require(
            (
                (
                    finite(report.get(key))
                    and abs(report[key]) <= 1000
                    and (key == "mae_change_candidate_minus_baseline_u_day" or report[key] >= 0)
                )
                if pairs
                else report.get(key) is None
            ),
            "Malformed native M5 paired metrics",
        )
    return report


def complete(report):
    return report["comparison_status"] == "complete" and report["candidate_execution_complete"]


def validate_declaration(declaration, report):
    require(
        isinstance(declaration, dict) and set(declaration) == DECLARATION_KEYS,
        "Malformed verified M5 model declaration",
    )
    require(
        declaration["schema"] == "m5-prognostic-model/1"
        and declaration["input_schema"] == "m5-landmark-input/1"
        and declaration["output_unit"] == "U/day"
        and isinstance(declaration["rights_basis"], str)
        and bool(declaration["rights_basis"].strip())
        and len(declaration["rights_basis"]) <= 500,
        "Malformed verified M5 declaration contract",
    )
    require(
        all(
            declaration[key] == report[key] for key in ("model_id", "source_sha256", "state_sha256")
        ),
        "M5 declaration and report identity differ",
    )
    declared_runtime = declaration["runtime"]
    require(
        isinstance(declared_runtime, dict)
        and set(declared_runtime) == {"python_major_minor", "dependencies"}
        and isinstance(declared_runtime["python_major_minor"], str)
        and 0 < len(declared_runtime["python_major_minor"]) <= 128
        and declared_runtime["dependencies"] == [],
        "Malformed verified M5 declaration runtime",
    )
    training = declaration["training"]
    require(
        isinstance(training, dict)
        and set(training) == {"phase", "fixture_sha256", "participant_aliases"}
        and training["phase"] == "development_only"
        and sha(training["fixture_sha256"])
        and training["participant_aliases"]
        == [
            person["alias"]
            for person in report["people"]
            if person["split"] == "development" and person["eligible"]
        ],
        "Malformed verified M5 training declaration",
    )
    return declaration


def declaration_digest(declaration):
    return digest(encode(declaration))
