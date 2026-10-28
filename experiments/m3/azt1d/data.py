"""Exact registered-time CGM windows for the separately versioned AZT1D study."""

from collections import Counter

from .common import MINUTE, SCHEMA, finite, require

STATUSES = (
    "measured",
    "missing",
    "invalid",
    "ambiguous",
    "censored_low",
    "censored_high",
    "unsupported",
)
PHASES = ("development", "validation", "evaluation")
ROW_FIELDS = {
    "time_us",
    "available_us",
    "segment",
    "raw_time",
    "status",
    "value",
    "bound",
    "source_rows",
}


def integer_time(value):
    """Retain exact local elapsed microseconds, including beyond float precision."""
    require(type(value) is int and value >= 0, "Invalid elapsed microseconds")
    return value


def validate_observations(document, person, start_us, end_us):
    require(isinstance(person, str) and person, "Missing observation participant")
    integer_time(start_us)
    integer_time(end_us)
    require(end_us > start_us, "Empty observation period")
    require(
        isinstance(document, dict)
        and set(document) == {"schema", "person", "clock", "unit", "bounds_us", "rows"},
        "Invalid observation document",
    )
    require(
        document["schema"] == SCHEMA
        and document["person"] == person
        and document["clock"] == "local_elapsed"
        and document["unit"] == "mg/dL",
        "Observation identity or semantics mismatch",
    )
    bounds = document["bounds_us"]
    require(
        isinstance(bounds, list)
        and len(bounds) == 2
        and all(type(value) is int for value in bounds)
        and bounds == [start_us, end_us],
        "Observation bounds differ",
    )
    require(isinstance(document["rows"], list), "Invalid observation rows")
    output, source_seen, segments = {}, set(), set()
    previous, segment = -1, None
    for row in document["rows"]:
        require(isinstance(row, dict) and set(row) == ROW_FIELDS, "Invalid observation fields")
        time = integer_time(row["time_us"])
        available = integer_time(row["available_us"])
        require(
            start_us <= time < end_us and time > previous and available >= time,
            "Invalid, duplicate or nonmonotone observation clock",
        )
        require(isinstance(row["raw_time"], str) and row["raw_time"], "Missing raw timestamp")
        require(isinstance(row["segment"], str) and row["segment"], "Missing clock segment")
        if row["segment"] != segment:
            require(row["segment"] not in segments, "Repeated clock segment")
            segments.add(row["segment"])
            segment = row["segment"]
        source = row["source_rows"]
        require(
            isinstance(source, list)
            and source
            and all(type(index) is int and index >= 1 for index in source),
            "Missing or invalid source row references",
        )
        require(
            source == sorted(set(source)) and not source_seen.intersection(source),
            "Repeated or unordered source row references",
        )
        source_seen.update(source)
        status, value, bound = row["status"], row["value"], row["bound"]
        require(status in STATUSES, "Unknown observation status")
        if status == "measured":
            finite(value, "measured CGM", 0)
            require(value > 0 and bound is None, "Invalid measured glucose")
        elif status.startswith("censored"):
            require(value is None, "Censoring is not a point measurement")
            if bound is not None:
                finite(bound, "censor bound", 0)
                require(bound > 0, "Invalid censor bound")
        else:
            require(value is None and bound is None, "Unavailable glucose has a numeric value")
        output[time] = dict(row, source_rows=list(source))
        previous = time
    return output


def origins(rows):
    """Every registered time remains planned, including unusable glucose."""
    return sorted(rows)


def history(rows, origin, start, phase):
    integer_time(origin)
    integer_time(start)
    require(phase in PHASES, "Unknown forecast phase")
    if phase == "evaluation" and origin < start + 60 * MINUTE:
        return None, "evaluation_warmup"
    if origin - 25 * MINUTE < start:
        return None, "history_outside_split"
    points = [rows.get(origin - offset * MINUTE) for offset in (25, 20, 15, 10, 5, 0)]
    if any(point is None for point in points):
        return None, "history_gap"
    if any(point["status"] != "measured" for point in points):
        return None, "history_unmeasured"
    if any(point["available_us"] > origin for point in points):
        return None, "history_unavailable"
    if len({point["segment"] for point in points}) != 1:
        return None, "clock_discontinuity"
    return [point["value"] for point in points], None


def target(rows, origin, end):
    integer_time(origin)
    integer_time(end)
    if origin + 30 * MINUTE >= end:
        return {"status": "outside_split", "value": None, "bound": None}
    point = rows.get(origin + 30 * MINUTE)
    if point is None:
        return {"status": "missing", "value": None, "bound": None}
    if rows.get(origin) is not None and rows[origin]["segment"] != point["segment"]:
        return {"status": "clock_discontinuity", "value": None, "bound": None}
    return {key: point[key] for key in ("status", "value", "bound")}


def training_windows(rows, start, end):
    """Development labels must also have arrived before the block ends."""
    integer_time(start)
    integer_time(end)
    require(end > start, "Empty development period")
    windows = []
    for origin in origins(rows):
        if not start <= origin < end:
            continue
        features, _ = history(rows, origin, start, "development")
        outcome = target(rows, origin, end)
        if (
            features is not None
            and outcome["status"] == "measured"
            and rows[origin + 30 * MINUTE]["available_us"] < end
        ):
            windows.append((origin, features, outcome["value"]))
    return windows


def forecast_rows(rows, person_id, phase, bounds, model):
    """Yield forecasts before reading targets; each registered origin is retained."""
    from experiments.m3.estimator import predict

    require(isinstance(bounds, (list, tuple)) and len(bounds) == 2, "Invalid forecast bounds")
    start, end = bounds
    integer_time(start)
    integer_time(end)
    require(end > start and phase in PHASES, "Invalid forecast period")
    require(all(start <= time < end for time in rows), "Observation outside forecast period")
    for origin in origins(rows):
        features, reason = history(rows, origin, start, phase)
        forecasts = (
            None
            if features is None
            else {"ridge": predict(model, features), "persistence": features[-1]}
        )
        point = rows[origin]
        if point["status"] != "measured" or point["available_us"] > origin:
            stratum = "unknown"
        else:
            stratum = (
                "low" if point["value"] < 70 else "high" if point["value"] > 180 else "in_range"
            )
        # Future outcomes cannot decide whether a forecast was causally possible.
        outcome = target(rows, origin, end)
        yield {
            "person": person_id,
            "phase": phase,
            "origin_us": origin,
            "history_rows": [
                rows.get(origin - offset * MINUTE) for offset in (25, 20, 15, 10, 5, 0)
            ],
            "features": features,
            "forecasts": forecasts,
            "target": outcome,
            "reason": reason,
            "origin_stratum": stratum,
        }


def timing_summary(rows, start, end):
    """Registered timestamps and adjacent gaps; no inferred clinical time coverage."""
    integer_time(start)
    integer_time(end)
    require(end > start, "Empty timing period")
    times = origins(rows)
    require(all(start <= time < end for time in times), "Observation outside timing period")
    intervals = [right - left for left, right in zip(times, times[1:])]
    counts = Counter(intervals)
    return {
        "registered_origins": len(times),
        "elapsed_us": end - start,
        "registered_origins_per_day": len(times) * (1440 * MINUTE) / (end - start),
        "first_registered_us": times[0] if times else None,
        "last_registered_us": times[-1] if times else None,
        "start_to_first_registered_us": times[0] - start if times else None,
        "last_registered_to_end_us": end - times[-1] if times else None,
        "adjacent_intervals": len(intervals),
        "minimum_interval_us": min(intervals) if intervals else None,
        "maximum_interval_us": max(intervals) if intervals else None,
        "interval_distribution": [
            {"interval_us": interval, "count": count} for interval, count in sorted(counts.items())
        ],
        "gaps_over_minutes": {
            str(minutes): sum(interval > minutes * MINUTE for interval in intervals)
            for minutes in (5, 15, 60, 1440)
        },
        "coverage_basis": "registered timestamps; not fraction of elapsed time",
    }


def eligibility(window_origins, minimum=288, span=1440 * MINUTE):
    require(type(minimum) is int and minimum > 0, "Invalid minimum window count")
    integer_time(span)
    times = list(window_origins)
    for time in times:
        integer_time(time)
    require(times == sorted(set(times)), "Window origins must be unique and ordered")
    return len(times) >= minimum and times[-1] - times[0] >= span
