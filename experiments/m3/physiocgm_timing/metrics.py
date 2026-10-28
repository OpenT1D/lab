"""Saved timing-trace validation and fixed equal-person comparison arithmetic.

No estimator is imported here. Validity of nearest selection against the full
source is established by trace reconstruction; these checks additionally reject
inconsistent timing metadata, causal history and cross-radius comparisons.
"""

from collections import Counter

from experiments.m3.azt1d.common import finite, require
from experiments.m3.azt1d.data import ROW_FIELDS, STATUSES
from experiments.m3.azt1d.metrics import (
    METHODS,
    STATES,
    STRATA,
    TARGETS,
    TRACE_FIELDS,
    _bootstrap,
    _mean,
    _summary,
    _time,
)

from .common import METRIC, MINUTE, RADII_US

MATCH_FIELDS = {"nominal_us", "selected_us", "offset_us", "nearest_us", "distance_us"}


def _match(match, nominal, radius, start, end, *, not_after=None, outside=False):
    require(isinstance(match, dict) and set(match) == MATCH_FIELDS, "Invalid timing match")
    require(
        type(match["nominal_us"]) is int and match["nominal_us"] == nominal,
        "Nominal matching time changed",
    )
    nearest = match["nearest_us"]
    require(isinstance(nearest, list) and len(nearest) <= 2, "Invalid nearest candidates")
    require(
        all(type(time) is int and start <= time < end for time in nearest),
        "Nearest candidate outside interval",
    )
    require(nearest == sorted(set(nearest)), "Repeated or unordered nearest candidates")
    require(
        not_after is None or all(time <= not_after for time in nearest),
        "Future historical candidate",
    )
    distance = match["distance_us"]
    if nearest:
        require(
            type(distance) is int
            and distance >= 0
            and all(abs(time - nominal) == distance for time in nearest),
            "Nearest distance differs",
        )
    else:
        require(distance is None, "Distance without nearest candidate")
    require(not outside or not nearest, "Outside target was searched")
    selected = nearest[0] if len(nearest) == 1 and distance <= radius else None
    require(
        match["selected_us"] == selected
        and (selected is None or type(match["selected_us"]) is int),
        "Selected time differs from unambiguous nearest candidate",
    )
    offset = None if selected is None else selected - nominal
    require(
        match["offset_us"] == offset and (offset is None or type(match["offset_us"]) is int),
        "Selected offset differs",
    )


def _point(point, selected):
    if selected is None:
        require(point is None, "History point without selection")
        return
    require(isinstance(point, dict) and set(point) == ROW_FIELDS, "Invalid selected history row")
    require(
        _time(point["time_us"]) == selected and _time(point["available_us"]) >= selected,
        "Invalid history availability",
    )
    require(
        isinstance(point["segment"], str)
        and point["segment"]
        and isinstance(point["raw_time"], str)
        and point["raw_time"],
        "Missing selected clock provenance",
    )
    source = point["source_rows"]
    require(
        isinstance(source, list)
        and source
        and all(type(index) is int and index > 0 for index in source)
        and source == sorted(set(source)),
        "Invalid selected source references",
    )
    require(point["status"] in STATUSES, "Invalid selected observation status")
    _outcome({key: point[key] for key in ("status", "value", "bound")})


def _outcome(outcome):
    require(
        isinstance(outcome, dict)
        and set(outcome) == {"status", "value", "bound"}
        and outcome["status"] in (*TARGETS, "matching_ambiguity"),
        "Invalid target outcome",
    )
    status, value, bound = outcome["status"], outcome["value"], outcome["bound"]
    if status == "measured":
        finite(value, "measured glucose", 0)
        require(value > 0 and bound is None, "Invalid measured outcome")
    else:
        require(value is None, "Unmeasured outcome contains a point value")
        if bound is not None:
            require(status in ("censored_low", "censored_high"), "Unexpected outcome bound")
            finite(bound, "outcome bound", 0)
            require(bound > 0, "Invalid outcome bound")


def _history_reason(matches, points, origin, start, radius):
    if origin < start + 60 * MINUTE:
        return "evaluation_warmup"
    if origin - 25 * MINUTE < start:
        return "history_outside_split"
    if any(match["distance_us"] is None or match["distance_us"] > radius for match in matches):
        return "history_gap"
    if any(len(match["nearest_us"]) != 1 for match in matches):
        return "history_matching_ambiguity"
    if any(
        left["selected_us"] >= right["selected_us"] for left, right in zip(matches, matches[1:])
    ):
        return "history_assignment_conflict"
    if any(point["status"] != "measured" for point in points):
        return "history_unmeasured"
    if any(point["available_us"] > origin for point in points):
        return "history_unavailable"
    if len({point["segment"] for point in points}) != 1:
        return "clock_discontinuity"
    return None


def validate_trace(row, origin, start, end, radius_us):
    """Validate actual selected times; never pretend tolerant times were exact."""
    require(type(radius_us) is int and radius_us in RADII_US, "Unregistered timing radius")
    require(
        isinstance(row, dict) and set(row) == TRACE_FIELDS | {"timing"},
        "Invalid timing trace fields",
    )
    require(
        isinstance(row["person"], str)
        and row["person"]
        and row["phase"] == "evaluation"
        and _time(row["origin_us"]) == origin,
        "Forecast identity or schedule differs",
    )
    timing = row["timing"]
    require(
        isinstance(timing, dict)
        and set(timing) == {"radius_us", "history", "target"}
        and type(timing["radius_us"]) is int
        and timing["radius_us"] == radius_us,
        "Timing variant differs",
    )
    matches, points = timing["history"], row["history_rows"]
    require(
        isinstance(matches, list)
        and len(matches) == 6
        and isinstance(points, list)
        and len(points) == 6,
        "Missing selected history",
    )
    for offset, match, point in zip((25, 20, 15, 10, 5, 0), matches, points, strict=True):
        _match(
            match,
            origin - offset * MINUTE,
            radius_us if offset else 0,
            start,
            end,
            not_after=origin,
        )
        _point(point, match["selected_us"])
    point = points[-1]
    require(point is not None and point["time_us"] == origin, "Origin observation is shifted")
    if point["status"] == "measured" and point["available_us"] <= origin:
        value = point["value"]
        stratum = "low" if value < 70 else "high" if value > 180 else "in_range"
    else:
        stratum = "unknown"
    require(row["origin_stratum"] == stratum, "Origin stratum differs")
    reason = _history_reason(matches, points, origin, start, radius_us)
    require(row["reason"] == reason, "History exclusion differs from selected observations")
    if reason is not None:
        require(
            row["features"] is None and row["forecasts"] is None, "Excluded history has forecasts"
        )
    else:
        require(
            isinstance(row["features"], list) and len(row["features"]) == 6,
            "Missing six selected features",
        )
        for value in row["features"]:
            finite(value, "feature", 0)
        require(
            row["features"] == [point["value"] for point in points],
            "Features differ from selected observations",
        )
        forecasts = row["forecasts"]
        require(
            isinstance(forecasts, dict) and set(forecasts) == set(METHODS),
            "Missing paired forecasts",
        )
        for value in forecasts.values():
            finite(value, "forecast")
        require(forecasts["persistence"] == point["value"], "Persistence changed")
    outcome, match = row["target"], timing["target"]
    _outcome(outcome)
    outside = origin + 30 * MINUTE >= end
    _match(match, origin + 30 * MINUTE, radius_us, start, end, outside=outside)
    if outside:
        expected = "outside_split"
    elif match["distance_us"] is None or match["distance_us"] > radius_us:
        expected = "missing"
    elif len(match["nearest_us"]) != 1:
        expected = "matching_ambiguity"
    else:
        expected = None
    require(
        outcome["status"] == expected
        if expected is not None
        else outcome["status"] in (*STATUSES, "clock_discontinuity"),
        "Target exclusion differs from timing match",
    )


def _offsets(rows):
    """Descriptive actual timing displacements; not corrected glucose values."""
    output = {}
    for kind in ("history", "target"):
        offsets = []
        for row in rows:
            if kind == "history" and row["forecasts"] is not None:
                offsets.extend(match["offset_us"] for match in row["timing"]["history"])
            elif (
                kind == "target"
                and row["forecasts"] is not None
                and row["target"]["status"] == "measured"
            ):
                offsets.append(row["timing"]["target"]["offset_us"])
        output[kind] = {
            "count": len(offsets),
            "maximum_absolute_us": max(map(abs, offsets)) if offsets else None,
            "signed_offset_counts": [
                {"offset_us": offset, "count": count}
                for offset, count in sorted(Counter(offsets).items())
            ],
        }
    return output


def summarize_case(planned_origins, traces, *, execution_status, bounds_us, radius_us):
    """Retain the complete denominator, including empty and failed cases."""
    require(execution_status in STATES, "Unknown execution status")
    require(type(radius_us) is int and radius_us in RADII_US, "Unregistered timing radius")
    require(isinstance(bounds_us, (list, tuple)) and len(bounds_us) == 2, "Missing phase bounds")
    start, end = map(_time, bounds_us)
    require(end > start, "Empty evaluation phase")
    planned, rows = list(planned_origins), list(traces)
    for origin in planned:
        require(start <= _time(origin) < end, "Origin outside phase")
    require(planned == sorted(set(planned)), "Repeated or unordered planned origins")
    require(len(rows) <= len(planned), "Unexpected forecast origins")
    require(execution_status != "completed" or len(rows) == len(planned), "False case completion")
    require(execution_status != "not_attempted" or not rows, "Unattempted case has forecasts")
    for row, origin in zip(rows, planned):
        validate_trace(row, origin, start, end, radius_us)
    require(len({row["person"] for row in rows}) <= 1, "Mixed participant traces")
    result = _summary(rows, len(planned))
    phase = "evaluation" if rows else None
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
        "radius_us": radius_us,
        "execution_status": execution_status,
        "phase": phase,
        "bounds_us": [start, end],
        "eligible_for_primary": not reasons,
        "ineligibility_reasons": reasons,
        "coverage_basis": "registered origins; not fraction of elapsed time",
        **result,
        "origin_strata": strata,
        "timing_offsets": _offsets(rows),
    }


def _equal_person(included):
    return {
        method: {
            metric: _mean(
                [finite(case[method][metric], "person metric") for case in included.values()]
            )
            for metric in ("mae", "rmse", "bias")
        }
        for method in METHODS
    }


def summarize_study(cases):
    """Frozen equal-person weighting and person bootstrap; no row resampling."""
    require(isinstance(cases, dict) and cases, "Planned participant mapping required")
    require(all(isinstance(person, str) and person for person in cases), "Invalid person alias")
    people = {person: cases[person] for person in sorted(cases)}
    for case in people.values():
        require(
            isinstance(case, dict)
            and case.get("metric") == METRIC
            and type(case.get("eligible_for_primary")) is bool,
            "Timing case summary required",
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
    radii = {case["radius_us"] for case in people.values()}
    require(len(radii) == 1 and next(iter(radii)) in RADII_US, "Mixed timing variants")
    included = {person: case for person, case in people.items() if case["eligible_for_primary"]}
    excluded = [person for person in people if person not in included]
    differences = {
        person: finite(case["paired"]["mae_difference"], "person MAE difference")
        for person, case in included.items()
    }
    return {
        "metric": METRIC,
        "radius_us": next(iter(radii)),
        "planned_people": len(people),
        "contributing_people": len(included),
        "complete_cohort": not excluded,
        "interpretation": "descriptive timing follow-up on inspected evaluation material"
        if not excluded
        else "incomplete planned timing follow-up cohort",
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
        "equal_person_metrics": _equal_person(included),
    }


def compare_variants(
    traces_by_radius_by_person,
    *,
    planned_origins_by_person,
    bounds_by_person,
    execution_statuses_by_radius_by_person,
):
    """Require nested coverage and unchanged decisions on shared origins.

    Added groups are descriptive, equal-person summaries with at least one
    paired outcome per contributor. They have no bootstrap or primary test.
    """
    require(
        isinstance(planned_origins_by_person, dict) and planned_origins_by_person,
        "Complete planned participant mapping required",
    )
    people = sorted(planned_origins_by_person)
    require(set(bounds_by_person) == set(people), "Participant bounds differ")
    require(
        set(traces_by_radius_by_person) == set(RADII_US)
        and set(execution_statuses_by_radius_by_person) == set(RADII_US),
        "Complete registered radius mapping required",
    )
    traces, variants, indices, predicted, scored = {}, {}, {}, {}, {}
    for radius in RADII_US:
        require(
            set(traces_by_radius_by_person[radius]) == set(people)
            and set(execution_statuses_by_radius_by_person[radius]) == set(people),
            "Timing variant omits a planned participant",
        )
        traces[radius], cases, indices[radius], predicted[radius], scored[radius] = (
            {},
            {},
            {},
            {},
            {},
        )
        for person in people:
            rows = list(traces_by_radius_by_person[radius][person])
            require(all(row.get("person") == person for row in rows), "Wrong participant trace")
            cases[person] = summarize_case(
                planned_origins_by_person[person],
                rows,
                execution_status=execution_statuses_by_radius_by_person[radius][person],
                bounds_us=bounds_by_person[person],
                radius_us=radius,
            )
            traces[radius][person] = rows
            indices[radius][person] = {row["origin_us"]: row for row in rows}
            predicted[radius][person] = {
                row["origin_us"] for row in rows if row["forecasts"] is not None
            }
            scored[radius][person] = {
                row["origin_us"]
                for row in rows
                if row["forecasts"] is not None and row["target"]["status"] == "measured"
            }
        variants[str(radius)] = summarize_study(cases)
    intersections, groups = {}, {}
    for low, high, label in (
        (0, 1_000_000, "S1-S0"),
        (0, 5_000_000, "S5-S0"),
        (1_000_000, 5_000_000, "S5-S1"),
    ):
        counts, additions = {}, {}
        for person in people:
            require(predicted[low][person] <= predicted[high][person], "Prediction sets not nested")
            require(scored[low][person] <= scored[high][person], "Scored sets not nested")
            for origin in predicted[low][person]:
                left, right = indices[low][person][origin], indices[high][person][origin]
                require(
                    all(
                        left[key] == right[key]
                        for key in ("history_rows", "features", "forecasts", "origin_stratum")
                    )
                    and left["timing"]["history"] == right["timing"]["history"],
                    "Shared prediction changed across timing variants",
                )
            for origin in scored[low][person]:
                left, right = indices[low][person][origin], indices[high][person][origin]
                require(
                    left["target"] == right["target"]
                    and left["timing"]["target"] == right["timing"]["target"],
                    "Shared scored target changed across timing variants",
                )
            counts[person] = {
                "predicted": len(predicted[low][person]),
                "scored": len(scored[low][person]),
            }
            added = scored[high][person] - scored[low][person]
            rows = [indices[high][person][origin] for origin in sorted(added)]
            additions[person] = {**_summary(rows, len(rows)), "contributes": bool(rows)}
        intersections[f"{low}:{high}"] = {
            "predicted": sum(value["predicted"] for value in counts.values()),
            "scored": sum(value["scored"] for value in counts.values()),
            "people": counts,
        }
        included = {person: case for person, case in additions.items() if case["contributes"]}
        groups[label] = {
            "planned_people": len(people),
            "contributing_people": len(included),
            "scored": sum(case["scored"] for case in additions.values()),
            "minimum_paired_windows_per_contributor": 1,
            "interpretation": "descriptive added scored origins; no primary test or bootstrap",
            "people": additions,
            "mean_person_mae_difference": _mean(
                [case["paired"]["mae_difference"] for case in included.values()]
            ),
            "equal_person_metrics": _equal_person(included),
        }
    return {
        "metric": METRIC,
        "radii_us": list(RADII_US),
        "complete_execution_cohort": all(
            status == "completed"
            for states in execution_statuses_by_radius_by_person.values()
            for status in states.values()
        ),
        "variants": variants,
        "intersections": intersections,
        "added_groups": groups,
    }
