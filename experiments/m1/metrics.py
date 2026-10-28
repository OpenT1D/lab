"""Duration-weighted interval exposure; never substitutes held CGM into metrics."""

import math

from .contracts import HORIZON, STEP, WARMUP, number, validate_rows

VERSION = "ot001-exposure/1"


def exposure(samples, scheduled_minutes):
    number(scheduled_minutes, "scheduled_minutes", 0)
    valid = []
    observed = 0
    represented = 0
    for value, duration in samples:
        number(duration, "duration", 0)
        if duration == 0:
            raise ValueError("Zero duration")
        represented += duration
        if value is not None:
            number(value, "glucose", 0)
            valid.append((value, duration))
            observed += duration
    if represented > scheduled_minutes:
        raise ValueError("Observed duration exceeds schedule")
    result = {
        "observed_minutes": observed,
        "scheduled_minutes": scheduled_minutes,
        "missing_minutes": scheduled_minutes - observed,
        "coverage_percent": 100 * observed / scheduled_minutes if scheduled_minutes else None,
    }
    mean = sum(v * d for v, d in valid) / observed if observed else None
    sd = math.sqrt(sum(d * (v - mean) ** 2 for v, d in valid) / observed) if observed else None
    result.update(mean_mg_dl=mean, sd_mg_dl=sd, cv_percent=100 * sd / mean if mean else None)
    for key, predicate in (
        ("in_70_180_percent", lambda v: 70 <= v <= 180),
        ("below_70_percent", lambda v: v < 70),
        ("below_54_percent", lambda v: v < 54),
        ("above_180_percent", lambda v: v > 180),
        ("above_250_percent", lambda v: v > 250),
    ):
        result[key] = (
            100 * sum(d for v, d in valid if predicate(v)) / observed if observed else None
        )
    return result


def summarize(rows):
    completed = validate_rows(rows)
    scored = [r for r in rows if WARMUP < r.end_min <= HORIZON]
    return {
        "metric_version": VERSION,
        "completed_minutes": completed,
        "glucose_semantics": "exposure of three-minute mean subcutaneous glucose",
        "glucose": exposure([(r.glucose_mg_dl, STEP) for r in scored], HORIZON - WARMUP),
        "sensor": exposure(
            [(r.raw_cgm_mg_dl if r.sensor_available else None, STEP) for r in scored],
            HORIZON - WARMUP,
        ),
        "delivered_insulin_u": sum(r.delivered_u_min * STEP for r in scored),
        "delivered_interval_minutes": len(scored) * STEP,
    }
