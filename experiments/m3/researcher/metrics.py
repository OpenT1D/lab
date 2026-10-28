"""Saved researcher-forecast arithmetic, without executing or importing models."""

import math
import random
import sys
from collections import Counter
from fractions import Fraction

from experiments.m3.azt1d.common import MINUTE, finite, require
from experiments.m3.azt1d.metrics import TARGETS, _time

METRIC = "researcher-cgm-forecast/1"
METHODS = ("candidate", "persistence")
STATES = ("completed", "failed", "interrupted", "not_attempted")
TRACE_FIELDS = {"origin_us", "features", "reason", "candidate", "persistence", "target"}
MIN_PAIRED_WINDOWS = 288
MIN_PAIRED_SPAN_US = 1440 * MINUTE


def _mean(values):
    """Average finite values without requiring their sum to be representable."""
    if not values:
        return None
    count = len(values)
    scaled = [value / count for value in values]
    # Division can erase or round subnormal contributions even when their mean
    # is representable.
    # Exact rational arithmetic is confined to that floating-point boundary and
    # to a rounded scaled sum overflowing at the largest representable value.
    if not any(
        value != 0 and abs(part) < sys.float_info.min for value, part in zip(values, scaled)
    ):
        try:
            return finite(math.fsum(scaled), "metric mean")
        except OverflowError:
            pass
    return finite(
        float(sum((Fraction(value) for value in values), Fraction()) / count), "metric mean"
    )


def _rmse(errors):
    if not errors:
        return None
    scale = max(abs(error) for error in errors)
    if scale == 0:
        return 0.0
    normalized = _mean([(error / scale) ** 2 for error in errors])
    # Normalized squared errors are bounded by one. Keep their rounded mean
    # within that bound so rescaling never introduces an overflow.
    return finite(scale * math.sqrt(min(1.0, normalized)), "root mean squared error")


def _bootstrap(differences):
    """Preserve the AZT1D participant resampling and empirical percentile rules."""
    if len(differences) < 2:
        return None
    rng = random.Random(301)
    means = sorted(_mean(rng.choices(differences, k=len(differences))) for _ in range(2000))
    # One-based empirical 50th and 1950th order statistics; no interpolation.
    return [means[49], means[1949]]


def _trace(row, origin, start, end):
    require(isinstance(row, dict) and set(row) == TRACE_FIELDS, "Invalid forecast trace fields")
    require(_time(row["origin_us"]) == origin, "Forecast schedule differs")
    features, reason = row["features"], row["reason"]
    if features is None:
        require(isinstance(reason, str) and bool(reason.strip()), "Missing exclusion reason")
        require(
            row["candidate"] is None and row["persistence"] is None,
            "Excluded history contains forecasts",
        )
    else:
        require(
            isinstance(features, list) and len(features) == 6 and reason is None,
            "Invalid forecast availability",
        )
        require(origin - 25 * MINUTE >= start, "Forecast history crosses evaluation boundary")
        require(origin >= start + 60 * MINUTE, "Forecast during evaluation warm-up")
        for value in features:
            finite(value, "feature", 0)
            require(value > 0, "Invalid measured feature")
        for method in METHODS:
            finite(row[method], f"{method} forecast")
        require(row["persistence"] == features[-1], "Persistence differs from origin glucose")

    target = row["target"]
    require(
        isinstance(target, dict)
        and set(target) == {"status", "value", "bound"}
        and target["status"] in TARGETS,
        "Invalid target outcome",
    )
    status, value, bound = target["status"], target["value"], target["bound"]
    require(
        (status == "outside_split") == (origin + 30 * MINUTE >= end),
        "Target evaluation exclusion differs",
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
    errors = []
    predicted = 0
    for row in rows:
        if row["features"] is None:
            continue
        predicted += 1
        if row["target"]["status"] == "measured":
            error = finite(row[method] - row["target"]["value"], "forecast error")
            errors.append(error)
    return {
        "predicted": predicted,
        "scored": len(errors),
        "prediction_coverage": predicted / planned if planned else None,
        "score_coverage": len(errors) / planned if planned else None,
        "mae": _mean([abs(error) for error in errors]),
        "rmse": _rmse(errors),
        "bias": _mean(errors),
    }


def _eligibility(execution_status, scored, span):
    reasons = []
    if execution_status != "completed":
        reasons.append("execution_incomplete")
    if scored < MIN_PAIRED_WINDOWS:
        reasons.append("insufficient_evaluation_windows")
    if span is None or span < MIN_PAIRED_SPAN_US:
        reasons.append("insufficient_evaluation_span")
    return reasons


def _summary(rows, planned):
    paired = [
        row for row in rows if row["features"] is not None and row["target"]["status"] == "measured"
    ]
    differences = [
        finite(
            abs(row["candidate"] - row["target"]["value"])
            - abs(row["persistence"] - row["target"]["value"]),
            "paired absolute-error difference",
        )
        for row in paired
    ]
    span = paired[-1]["origin_us"] - paired[0]["origin_us"] if paired else None
    forecastable = sum(row["features"] is not None for row in rows)
    history_exclusions = Counter(row["reason"] for row in rows if row["reason"] is not None)
    scoring_exclusions = history_exclusions.copy()
    for row in rows:
        if row["features"] is not None and row["target"]["status"] != "measured":
            scoring_exclusions["target_" + row["target"]["status"]] += 1
    return {
        "planned": planned,
        "attempted": len(rows),
        "not_attempted": planned - len(rows),
        "forecastable": forecastable,
        "scored": len(paired),
        "prediction_coverage": forecastable / planned if planned else None,
        "score_coverage": len(paired) / planned if planned else None,
        "history_exclusions": dict(sorted(history_exclusions.items())),
        "scoring_exclusions": dict(sorted(scoring_exclusions.items())),
        "target_status_counts": dict(
            sorted(Counter(row["target"]["status"] for row in rows).items())
        ),
        "paired": {
            "scored": len(paired),
            "origins_span_us": span,
            "mae_difference": _mean(differences),
        },
        **{method: _method(rows, method, planned) for method in METHODS},
    }


def summarize_case(planned_origins, traces, *, execution_status, bounds_us):
    """Compare paired forecasts against every registered synthetic origin.

    A failed or interrupted participant retains its valid trace prefix. Every
    prediction uses six exact five-minute measurements and the evaluation's
    sixty-minute warm-up; target values remain thirty minutes ahead. Checking
    those features against saved observations belongs to reconstruction.
    """
    require(execution_status in STATES, "Unknown execution status")
    require(isinstance(bounds_us, (list, tuple)) and len(bounds_us) == 2, "Missing phase bounds")
    start, end = map(_time, bounds_us)
    require(end > start, "Empty phase")
    planned, rows = list(planned_origins), list(traces)
    for origin in planned:
        _time(origin)
        require(start <= origin < end, "Origin outside evaluation")
    require(planned == sorted(set(planned)), "Repeated or unordered planned origins")
    require(len(rows) <= len(planned), "Unexpected forecast origins")
    require(execution_status != "completed" or len(rows) == len(planned), "False case completion")
    require(execution_status != "not_attempted" or not rows, "Unattempted case contains forecasts")
    for row, origin in zip(rows, planned):
        _trace(row, origin, start, end)
    result = _summary(rows, len(planned))
    reasons = _eligibility(execution_status, result["scored"], result["paired"]["origins_span_us"])
    return {
        "metric": METRIC,
        "execution_status": execution_status,
        "bounds_us": [start, end],
        "eligible_for_primary": not reasons,
        "ineligibility_reasons": reasons,
        "coverage_basis": "registered origins; not fraction of elapsed time",
        **result,
    }


def _case_summary(case):
    require(
        isinstance(case, dict)
        and case.get("metric") == METRIC
        and case.get("execution_status") in STATES
        and type(case.get("eligible_for_primary")) is bool,
        "Researcher case summary required",
    )
    counts = [
        case.get(key) for key in ("planned", "attempted", "not_attempted", "forecastable", "scored")
    ]
    require(all(type(value) is int and value >= 0 for value in counts), "Invalid case counts")
    planned, attempted, not_attempted, forecastable, scored = counts
    require(
        planned == attempted + not_attempted and attempted >= forecastable >= scored,
        "Inconsistent case counts",
    )
    status = case["execution_status"]
    require(status != "completed" or attempted == planned, "False case completion")
    require(status != "not_attempted" or attempted == 0, "Unattempted case contains forecasts")
    paired = case.get("paired")
    require(
        isinstance(paired, dict)
        and type(paired.get("scored")) is int
        and paired["scored"] == scored,
        "Invalid paired summary",
    )
    span = paired.get("origins_span_us")
    require((span is None) == (scored == 0), "Invalid paired span")
    if span is not None:
        _time(span)
        require((span == 0) == (scored == 1), "Invalid paired span")
    reasons = _eligibility(status, scored, span)
    require(
        case["eligible_for_primary"] == (not reasons)
        and case.get("ineligibility_reasons") == reasons,
        "False primary eligibility",
    )
    if scored:
        finite(paired.get("mae_difference"), "person MAE difference")
    else:
        require(paired.get("mae_difference") is None, "Unscored case has MAE difference")
    for method in METHODS:
        metrics = case.get(method)
        require(
            isinstance(metrics, dict)
            and type(metrics.get("scored")) is int
            and metrics["scored"] == scored,
            "Invalid method summary",
        )
        for metric in ("mae", "rmse", "bias"):
            if scored:
                finite(metrics.get(metric), "person " + metric, 0 if metric != "bias" else None)
            else:
                require(metrics.get(metric) is None, "Unscored case has error metric")


def summarize_study(cases):
    """Weight contributing participants equally and retain the complete roster.

    The caller supplies every planned participant, including failed and
    unattempted cases. The fixed, source-study participant bootstrap resamples
    people, never the correlated forecast windows within each person.
    """
    require(isinstance(cases, dict) and cases, "Planned participant mapping required")
    require(
        all(isinstance(person, str) and bool(person.strip()) for person in cases),
        "Invalid participant alias",
    )
    people = {person: cases[person] for person in sorted(cases)}
    for case in people.values():
        _case_summary(case)
    included = {person: case for person, case in people.items() if case["eligible_for_primary"]}
    excluded = [person for person in people if person not in included]
    differences = {person: case["paired"]["mae_difference"] for person, case in included.items()}
    return {
        "metric": METRIC,
        "planned_people": len(people),
        "contributing_people": len(included),
        "complete_cohort": not excluded,
        "interpretation": "incomplete planned synthetic cohort"
        if excluded
        else "descriptive synthetic CGM prediction without refitting",
        "execution_status_counts": dict(
            sorted(Counter(case["execution_status"] for case in people.values()).items())
        ),
        "people": people,
        "primary": {
            "paired_people": len(included),
            "excluded_people": excluded,
            "mean_person_mae_difference": _mean(list(differences.values())),
            "participant_bootstrap_95": _bootstrap(list(differences.values())),
            "person_differences": differences,
        },
        "equal_person_metrics": {
            method: {
                metric: _mean([case[method][metric] for case in included.values()])
                for metric in ("mae", "rmse", "bias")
            }
            for method in METHODS
        },
    }
