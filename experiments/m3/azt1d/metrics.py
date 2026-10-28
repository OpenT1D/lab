"""Saved-trace AZT1D metrics; standard-library arithmetic, no estimator imports."""

import math
import random
from collections import Counter

from .common import MINUTE, finite, require

METHODS = ("ridge", "persistence")
STRATA = ("low", "in_range", "high", "unknown")
STATES = ("started", "completed", "failed", "interrupted", "not_attempted")
TARGETS = (
    "measured",
    "missing",
    "invalid",
    "ambiguous",
    "censored_low",
    "censored_high",
    "unsupported",
    "outside_split",
    "clock_discontinuity",
)
TRACE_FIELDS = {
    "person",
    "phase",
    "origin_us",
    "history_rows",
    "features",
    "forecasts",
    "target",
    "reason",
    "origin_stratum",
}


def _mean(values):
    if not values:
        return None
    return finite(math.fsum(values) / len(values), "metric mean")


def _time(value):
    require(type(value) is int and value >= 0, "Invalid elapsed microseconds")
    return value


def _trace(row, origin, start, end):
    require(isinstance(row, dict) and set(row) == TRACE_FIELDS, "Invalid forecast trace fields")
    require(
        isinstance(row["person"], str)
        and row["person"]
        and row["phase"] in ("development", "validation", "evaluation")
        and _time(row["origin_us"]) == origin,
        "Forecast identity or schedule differs",
    )
    require(
        isinstance(row["history_rows"], list) and len(row["history_rows"]) == 6,
        "Missing origin history",
    )
    point = row["history_rows"][-1]
    if point is None:
        stratum = "unknown"
    else:
        require(isinstance(point, dict), "Invalid origin observation")
        require(_time(point.get("time_us")) == origin, "Origin observation is shifted")
        available = _time(point.get("available_us"))
        require(available >= origin, "Invalid origin availability")
        if point.get("status") == "measured" and available <= origin:
            value = finite(point.get("value"), "origin glucose", 0)
            require(value > 0, "Invalid origin glucose")
            stratum = "low" if value < 70 else "high" if value > 180 else "in_range"
        else:
            stratum = "unknown"
    require(row["origin_stratum"] == stratum, "Origin stratum differs from observed history")
    forecasts, features, reason = row["forecasts"], row["features"], row["reason"]
    if forecasts is None:
        require(features is None and isinstance(reason, str) and reason, "Missing exclusion reason")
    else:
        require(
            isinstance(forecasts, dict)
            and set(forecasts) == set(METHODS)
            and reason is None
            and isinstance(features, list)
            and len(features) == 6,
            "Invalid forecast availability",
        )
        require(origin - 25 * MINUTE >= start, "Forecast history crosses phase boundary")
        require(
            row["phase"] != "evaluation" or origin >= start + 60 * MINUTE,
            "Forecast during evaluation warm-up",
        )
        for value in features:
            finite(value, "feature", 0)
            require(value > 0, "Invalid measured feature")
        for value in forecasts.values():
            finite(value, "forecast")
        require(
            stratum != "unknown"
            and features[-1] == point["value"]
            and forecasts["persistence"] == features[-1],
            "Persistence differs from available origin glucose",
        )
    outcome = row["target"]
    require(
        isinstance(outcome, dict)
        and set(outcome) == {"status", "value", "bound"}
        and outcome["status"] in TARGETS,
        "Invalid target outcome",
    )
    status, value, bound = outcome["status"], outcome["value"], outcome["bound"]
    require(
        (status == "outside_split") == (origin + 30 * MINUTE >= end),
        "Target phase exclusion differs",
    )
    if status == "measured":
        finite(value, "target glucose", 0)
        require(value > 0 and bound is None, "Invalid measured target")
    else:
        require(value is None, "Unmeasured target contains point value")
        if bound is not None:
            require(status in ("censored_low", "censored_high"), "Unknown target bound")
            finite(bound, "censor bound", 0)
            require(bound > 0, "Invalid censor bound")


def _method(rows, method, planned):
    errors, lower_bounds = [], []
    predicted, censored_targets = 0, 0
    for row in rows:
        if row["forecasts"] is None:
            continue
        predicted += 1
        forecast, outcome = row["forecasts"][method], row["target"]
        if outcome["status"] == "measured":
            error = finite(forecast - outcome["value"], "forecast error")
            finite(error * error, "squared forecast error")
            errors.append(error)
        elif outcome["status"] in ("censored_low", "censored_high"):
            censored_targets += 1
            if outcome["bound"] is not None:
                lower_bounds.append(
                    finite(
                        max(0, outcome["bound"] - forecast)
                        if outcome["status"] == "censored_high"
                        else max(0, forecast - outcome["bound"]),
                        "censored absolute-error lower bound",
                    )
                )
    return {
        "predicted": predicted,
        "scored": len(errors),
        "prediction_coverage": predicted / planned if planned else None,
        "score_coverage": len(errors) / planned if planned else None,
        "mae": _mean([abs(error) for error in errors]),
        "rmse": math.sqrt(_mean([error * error for error in errors])) if errors else None,
        "bias": _mean(errors),
        "censored_targets": censored_targets,
        "censored_count": len(lower_bounds),
        "mean_censored_absolute_error_lower_bound": _mean(lower_bounds),
    }


def _summary(rows, planned):
    paired = [
        row
        for row in rows
        if row["forecasts"] is not None and row["target"]["status"] == "measured"
    ]
    differences = [
        finite(
            abs(row["forecasts"]["ridge"] - row["target"]["value"])
            - abs(row["forecasts"]["persistence"] - row["target"]["value"]),
            "paired absolute-error difference",
        )
        for row in paired
    ]
    predicted = sum(row["forecasts"] is not None for row in rows)
    exclusions = Counter()
    for row in rows:
        if row["forecasts"] is None:
            exclusions[row["reason"]] += 1
        elif row["target"]["status"] != "measured":
            exclusions["target_" + row["target"]["status"]] += 1
    return {
        "planned": planned,
        "attempted": len(rows),
        "not_attempted": planned - len(rows),
        "predicted": predicted,
        "scored": len(paired),
        "prediction_coverage": predicted / planned if planned else None,
        "score_coverage": len(paired) / planned if planned else None,
        "history_exclusions": dict(
            sorted(Counter(row["reason"] for row in rows if row["reason"]).items())
        ),
        "scoring_exclusions": dict(sorted(exclusions.items())),
        "target_statuses": dict(sorted(Counter(row["target"]["status"] for row in rows).items())),
        "paired": {
            "scored": len(paired),
            "origins_span_us": paired[-1]["origin_us"] - paired[0]["origin_us"] if paired else None,
            "mae_difference": _mean(differences),
        },
        **{method: _method(rows, method, planned) for method in METHODS},
    }


def summarize_case(planned_origins, traces, *, development_eligible, execution_status, bounds_us):
    """Summarize a complete trace or retained prefix against its frozen denominator."""
    require(type(development_eligible) is bool, "Development eligibility must be explicit")
    require(execution_status in STATES, "Unknown execution status")
    require(isinstance(bounds_us, (list, tuple)) and len(bounds_us) == 2, "Missing phase bounds")
    start, end = map(_time, bounds_us)
    require(end > start, "Empty phase")
    planned, rows = list(planned_origins), list(traces)
    for origin in planned:
        _time(origin)
        require(start <= origin < end, "Origin outside phase")
    require(planned == sorted(set(planned)), "Repeated or unordered planned origins")
    require(len(rows) <= len(planned), "Unexpected forecast origins")
    require(execution_status != "completed" or len(rows) == len(planned), "False case completion")
    require(execution_status != "not_attempted" or not rows, "Unattempted case contains forecasts")
    for row, origin in zip(rows, planned):
        _trace(row, origin, start, end)
    require(
        len({row["person"] for row in rows}) <= 1 and len({row["phase"] for row in rows}) <= 1,
        "Mixed participant or phase traces",
    )
    phase = rows[0]["phase"] if rows else None
    result = _summary(rows, len(planned))
    reasons = []
    if not development_eligible:
        reasons.append("development_ineligible")
    if execution_status != "completed":
        reasons.append("execution_incomplete")
    if phase != "evaluation":
        reasons.append("not_evaluation")
    if result["paired"]["scored"] < 288:
        reasons.append("insufficient_evaluation_windows")
    span = result["paired"]["origins_span_us"]
    if span is None or span < 1440 * MINUTE:
        reasons.append("insufficient_evaluation_span")
    strata = {}
    for stratum in STRATA:
        selected = [row for row in rows if row["origin_stratum"] == stratum]
        unknown = result["not_attempted"] if stratum == "unknown" else 0
        strata[stratum] = _summary(selected, len(selected) + unknown)
    return {
        "execution_status": execution_status,
        "phase": phase,
        "bounds_us": [start, end],
        "development_eligible": development_eligible,
        "eligible_for_primary": not reasons,
        "ineligibility_reasons": reasons,
        "coverage_basis": "registered origins; not fraction of elapsed time",
        **result,
        "origin_strata": strata,
    }


def _bootstrap(differences):
    if len(differences) < 2:
        return None
    rng = random.Random(301)
    means = sorted(_mean(rng.choices(differences, k=len(differences))) for _ in range(2000))
    # One-based empirical 50th and 1950th order statistics; no interpolation.
    return [means[49], means[1949]]


def summarize_study(cases):
    """Equal-person aggregation; the caller supplies every planned participant."""
    require(isinstance(cases, dict) and cases, "Planned participant mapping required")
    require(
        all(isinstance(person, str) and person for person in cases), "Invalid participant alias"
    )
    people = {person: cases[person] for person in sorted(cases)}
    for case in people.values():
        require(
            isinstance(case, dict) and type(case.get("eligible_for_primary")) is bool,
            "Case summary required",
        )
        if case["eligible_for_primary"]:
            require(
                case["execution_status"] == "completed"
                and case["phase"] == "evaluation"
                and case["development_eligible"] is True
                and case["attempted"] == case["planned"]
                and case["paired"]["scored"] >= 288
                and case["paired"]["origins_span_us"] >= 1440 * MINUTE,
                "False primary eligibility",
            )
    included = {person: case for person, case in people.items() if case["eligible_for_primary"]}
    excluded = [person for person in people if person not in included]
    differences = {
        person: finite(case["paired"]["mae_difference"], "person MAE difference")
        for person, case in included.items()
    }
    aggregates = {
        method: {
            metric: _mean(
                [finite(case[method][metric], "person metric") for case in included.values()]
            )
            for metric in ("mae", "rmse", "bias")
        }
        for method in METHODS
    }
    values = list(differences.values())
    return {
        "planned_people": len(people),
        "contributing_people": len(included),
        "complete_cohort": not excluded,
        "interpretation": "incomplete planned cohort"
        if excluded
        else "descriptive later-period CGM prediction for known participants",
        "execution_status_counts": dict(
            sorted(Counter(case["execution_status"] for case in people.values()).items())
        ),
        "people": people,
        "primary": {
            "paired_people": len(included),
            "excluded_people": excluded,
            "mean_person_mae_difference": _mean(values),
            "participant_bootstrap_95": _bootstrap(values),
            "person_differences": differences,
        },
        "equal_person_metrics": aggregates,
    }
