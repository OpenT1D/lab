"""Bounded nearest-time matching without interpolation or observation IO."""

from bisect import bisect_left, bisect_right

from experiments.m3.azt1d.common import SCHEMA as OBSERVATION_SCHEMA
from experiments.m3.azt1d.data import integer_time, validate_observations
from experiments.m3.common import require

from .common import MINUTE, RADII_US


def _radius(value):
    require(type(value) is int and value in RADII_US, "Unsupported timing radius")
    return value


def _empty_match(nominal):
    return {
        "nominal_us": nominal,
        "selected_us": None,
        "offset_us": None,
        "nearest_us": [],
        "distance_us": None,
    }


class TimeIndex:
    """Index one normalized evaluation interval, preserving integer clocks.

    Nearest candidates are selected from registered times before checking their
    status, arrival time or clock segment. A rejected candidate has no fallback.
    The current observation stays exact; tolerant targets are observed outcomes
    near the nominal horizon, not interpolated values at that horizon.
    """

    def __init__(self, rows, start, end):
        integer_time(start)
        integer_time(end)
        require(end > start and isinstance(rows, dict), "Invalid timing interval")
        require(
            all(type(time) is int and time >= 0 for time in rows),
            "Invalid registered clock",
        )
        require(
            all(
                isinstance(row, dict) and type(row.get("time_us")) is int and row["time_us"] == time
                for time, row in rows.items()
            ),
            "Observation key differs from registered clock",
        )
        document = {
            "schema": OBSERVATION_SCHEMA,
            "person": "in-memory-timing-input",
            "clock": "local_elapsed",
            "unit": "mg/dL",
            "bounds_us": [start, end],
            "rows": [rows[time] for time in sorted(rows)],
        }
        self.rows = validate_observations(document, document["person"], start, end)
        self.times = sorted(self.rows)
        self.start, self.end = start, end

    def _origin(self, origin):
        integer_time(origin)
        require(origin in self.rows, "Forecast origin is not registered")

    def _match(self, nominal, radius, not_after=None):
        """Keep nearest metadata even when radius or a tie prevents selection."""
        result = _empty_match(nominal)
        upper = len(self.times) if not_after is None else bisect_right(self.times, not_after)
        position = bisect_left(self.times, nominal, 0, upper)
        candidates = []
        if position:
            candidates.append(self.times[position - 1])
        if position < upper:
            candidates.append(self.times[position])
        if not candidates:
            return result
        distance = min(abs(time - nominal) for time in candidates)
        nearest = [time for time in candidates if abs(time - nominal) == distance]
        result.update(nearest_us=nearest, distance_us=distance)
        if distance <= radius and len(nearest) == 1:
            result.update(selected_us=nearest[0], offset_us=nearest[0] - nominal)
        return result

    def history(self, origin, radius_us):
        """Select six causal inputs with the frozen exclusion precedence."""
        radius = _radius(radius_us)
        self._origin(origin)
        matches = [
            self._match(origin - offset * MINUTE, radius if offset else 0, origin)
            for offset in (25, 20, 15, 10, 5, 0)
        ]
        points = [self.rows.get(match["selected_us"]) for match in matches]
        reason = None
        if origin < self.start + 60 * MINUTE:
            reason = "evaluation_warmup"
        elif origin - 25 * MINUTE < self.start:
            reason = "history_outside_split"
        elif any(
            match["distance_us"] is None or match["distance_us"] > radius for match in matches
        ):
            reason = "history_gap"
        elif any(len(match["nearest_us"]) != 1 for match in matches):
            reason = "history_matching_ambiguity"
        elif any(
            left["selected_us"] >= right["selected_us"] for left, right in zip(matches, matches[1:])
        ):
            reason = "history_assignment_conflict"
        elif any(point["status"] != "measured" for point in points):
            reason = "history_unmeasured"
        elif any(point["available_us"] > origin for point in points):
            reason = "history_unavailable"
        elif len({point["segment"] for point in points}) != 1:
            reason = "clock_discontinuity"
        return {
            "features": None if reason is not None else [point["value"] for point in points],
            "reason": reason,
            "history_rows": points,
            "matches": matches,
        }

    def target(self, origin, radius_us):
        """Select a descriptive outcome; outcome availability cannot gate inputs."""
        radius = _radius(radius_us)
        self._origin(origin)
        nominal = origin + 30 * MINUTE
        if nominal >= self.end:
            match, status = _empty_match(nominal), "outside_split"
        else:
            match = self._match(nominal, radius)
            if match["distance_us"] is None or match["distance_us"] > radius:
                status = "missing"
            elif len(match["nearest_us"]) != 1:
                status = "matching_ambiguity"
            else:
                point = self.rows[match["selected_us"]]
                if point["segment"] != self.rows[origin]["segment"]:
                    status = "clock_discontinuity"
                else:
                    return {
                        "target": {key: point[key] for key in ("status", "value", "bound")},
                        "match": match,
                    }
        return {"target": {"status": status, "value": None, "bound": None}, "match": match}
