"""Immutable finite piecewise-linear input in pmol/(kg min), including jumps.

Each segment owns both endpoint values. Distinct values at a shared boundary
represent a discontinuity, not an extra triangular ramp or an impulse.
"""

import math
from bisect import bisect_right
from dataclasses import dataclass
from numbers import Real

UNITS = "pmol/(kg min)"


def _finite(value, name, *, positive=False):
    if isinstance(value, bool) or not isinstance(value, Real):
        raise ValueError(f"{name} must be a finite real number")
    try:
        numeric = float(value)
    except (TypeError, ValueError, OverflowError) as error:
        raise ValueError(f"{name} must be a finite real number") from error
    if not math.isfinite(numeric) or (numeric <= 0 if positive else numeric < 0):
        raise ValueError(f"{name} must be finite and {'positive' if positive else 'nonnegative'}")
    return numeric


@dataclass(frozen=True)
class Forcing:
    edges: tuple
    left: tuple
    right: tuple
    units: str = UNITS

    def __post_init__(self):
        if self.units != UNITS:
            raise ValueError(f"forcing units must be exactly {UNITS}")
        for name in ("edges", "left", "right"):
            try:
                values = tuple(_finite(value, name) for value in getattr(self, name))
            except TypeError as error:
                raise ValueError(f"{name} must be a sequence") from error
            object.__setattr__(self, name, values)
        if len(self.edges) < 2 or self.edges[0] != 0:
            raise ValueError("forcing edges must start at zero and include an end")
        if any(b <= a for a, b in zip(self.edges, self.edges[1:])):
            raise ValueError("forcing edges must be strictly increasing")
        if len(self.left) != self.segments or len(self.right) != self.segments:
            raise ValueError("left and right must contain one rate for every segment")

    @property
    def horizon(self):
        return self.edges[-1]

    @property
    def segments(self):
        return len(self.edges) - 1

    def segment_value(self, index, time):
        if isinstance(index, bool) or not isinstance(index, int) or not 0 <= index < self.segments:
            raise ValueError("invalid segment index")
        time = _finite(time, "time")
        start, stop = self.edges[index : index + 2]
        if not start <= time <= stop:
            raise ValueError("time lies outside this input segment")
        fraction = (time - start) / (stop - start)
        return self.left[index] * (1 - fraction) + self.right[index] * fraction

    def evaluate(self, time, side="right"):
        time = _finite(time, "time")
        if time > self.horizon:
            raise ValueError("forcing cannot extrapolate beyond its horizon")
        if side not in ("left", "right"):
            raise ValueError("side must be left or right")
        index = min(bisect_right(self.edges, time) - 1, self.segments - 1)
        if side == "left" and index > 0 and self.edges[index] == time:
            index -= 1
        return self.segment_value(index, time)

    def integral(self, start=0.0, stop=None):
        start = _finite(start, "integral start")
        stop = self.horizon if stop is None else _finite(stop, "integral stop")
        if not start <= stop <= self.horizon:
            raise ValueError("integral limits must lie in the supplied horizon")
        contributions = []
        first = min(bisect_right(self.edges, start) - 1, self.segments - 1)
        for index in range(first, self.segments):
            a, b = max(start, self.edges[index]), min(stop, self.edges[index + 1])
            if b > a:
                contributions.append(
                    (b - a) * (self.segment_value(index, a) + self.segment_value(index, b)) / 2
                )
            if self.edges[index + 1] >= stop:
                break
        total = math.fsum(contributions)
        if not math.isfinite(total):
            raise ValueError("integrated amount is nonfinite")
        return total

    def to_dict(self):
        return {
            "edges": list(self.edges),
            "left": list(self.left),
            "right": list(self.right),
            "units": self.units,
        }


def from_source_samples(times, values, units=UNITS):
    """Define a continuous linear interpolant; never infer unobserved curvature."""
    times, values = tuple(times), tuple(values)
    if len(times) != len(values):
        raise ValueError("source sample times and values must have equal lengths")
    return Forcing(times, values[:-1], values[1:], units=units)


def interval_average(forcing, dt):
    """Piecewise-constant communication, preserving each interval's exact amount."""
    if not isinstance(forcing, Forcing):
        raise ValueError("forcing must be a Forcing instance")
    dt = _finite(dt, "communication interval", positive=True)
    ratio = forcing.horizon / dt
    if not math.isfinite(ratio):
        raise ValueError("communication interval creates a nonfinite number of intervals")
    count = math.ceil(ratio)
    edges = [0.0] + [min(i * dt, forcing.horizon) for i in range(1, count + 1)]
    rates = [forcing.integral(a, b) / (b - a) for a, b in zip(edges, edges[1:])]
    return Forcing(edges, rates, rates, units=forcing.units)
