"""External-cohort saved-trace metrics; no fitting or estimator dependencies."""

from collections import Counter

from experiments.m3.azt1d.common import MINUTE, finite, require
from experiments.m3.azt1d.metrics import (
    METHODS,
    STATES,
    STRATA,
    _bootstrap,
    _mean,
    _summary,
    _time,
    _trace,
)

METRIC = "external-cgm-forecast/1"


def summarize_case(planned_origins, traces, *, execution_status, bounds_us):
    """Retain every registered origin; qualification uses external outcomes only.

    The external participant has no training qualification: a previously frozen
    model is evaluated without fitting to that participant. Trace arithmetic and
    exact-time checks are shared with the source study, but primary eligibility
    is a separately defined external-cohort decision.
    """
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
        "metric": METRIC,
        "execution_status": execution_status,
        "phase": phase,
        "bounds_us": [start, end],
        "eligible_for_primary": not reasons,
        "ineligibility_reasons": reasons,
        "coverage_basis": "registered origins; not fraction of elapsed time",
        **result,
        "origin_strata": strata,
    }


def summarize_study(cases):
    """Weight external participants equally, retaining every planned case.

    The caller supplies the complete frozen participant mapping, including
    failures and unattempted cases. Uncertainty resamples contributing people,
    never their correlated glucose observations.
    """
    require(isinstance(cases, dict) and cases, "Planned participant mapping required")
    require(
        all(isinstance(person, str) and person for person in cases), "Invalid participant alias"
    )
    people = {person: cases[person] for person in sorted(cases)}
    for case in people.values():
        require(
            isinstance(case, dict)
            and case.get("metric") == METRIC
            and "development_eligible" not in case
            and type(case.get("eligible_for_primary")) is bool,
            "External case summary required",
        )
        if case["eligible_for_primary"]:
            require(
                case["execution_status"] == "completed"
                and case["phase"] == "evaluation"
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
        "metric": METRIC,
        "planned_people": len(people),
        "contributing_people": len(included),
        "complete_cohort": not excluded,
        "interpretation": "incomplete planned external cohort"
        if excluded
        else "descriptive external-cohort CGM prediction without refitting",
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
