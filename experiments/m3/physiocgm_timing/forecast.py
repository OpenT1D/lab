"""Fixed-model forecasts with separately preserved timing selections."""

from experiments.m3.azt1d.common import require

from .common import RADII_US
from .data import TimeIndex


def legacy_projection(trace):
    """Remove only the new timing evidence for the strict zero-radius control."""
    return {key: value for key, value in trace.items() if key != "timing"}


def forecast_rows(rows, person, bounds, model, radius_us):
    """Keep every origin; compute forecasts before looking up its future outcome.

    The scaler and Ridge parameters are passed unchanged to the existing
    standard-library predictor. This module neither fits nor changes a model.
    """
    from experiments.m3.estimator import predict

    require(isinstance(person, str) and person, "Missing forecast participant")
    require(type(radius_us) is int and radius_us in RADII_US, "Unregistered timing radius")
    require(isinstance(bounds, (list, tuple)) and len(bounds) == 2, "Invalid forecast bounds")
    index = TimeIndex(rows, *bounds)
    for origin in index.times:
        history = index.history(origin, radius_us)
        features = history["features"]
        forecasts = (
            None
            if features is None
            else {"ridge": predict(model, features), "persistence": features[-1]}
        )
        point = index.rows[origin]
        if point["status"] != "measured" or point["available_us"] > origin:
            stratum = "unknown"
        else:
            stratum = (
                "low" if point["value"] < 70 else "high" if point["value"] > 180 else "in_range"
            )
        # Outcome matching must not decide whether a forecast can be made.
        outcome = index.target(origin, radius_us)
        yield {
            "person": person,
            "phase": "evaluation",
            "origin_us": origin,
            "history_rows": history["history_rows"],
            "features": features,
            "forecasts": forecasts,
            "target": outcome["target"],
            "reason": history["reason"],
            "origin_stratum": stratum,
            "timing": {
                "radius_us": radius_us,
                "history": history["matches"],
                "target": outcome["match"],
            },
        }
