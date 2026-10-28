"""Dalla Man 2007 equations 23-26, shifted Z=Y+Sb; original implementation.

Minutes, glucose mg/dL, Z pmol/(kg min), P pmol/kg. Ledger order is
pancreatic appearance, liver arrival, both pmol/kg. No insulin clearance.
"""

from dataclasses import dataclass

import numpy as np
from scipy.integrate import solve_ivp

from .contract import number

VERSION = "dallaman2007-static-dynamic-portal/1"


@dataclass(frozen=True)
class GlucoseSignal:
    """Continuous affine glucose in mg/dL, with explicit time knots in minutes."""

    edges: tuple
    values: tuple

    def __post_init__(self):
        if len(self.edges) != len(self.values) or len(self.edges) < 2:
            raise ValueError("Glucose knots and concentrations must match")
        for value in (*self.edges, *self.values):
            number(value)
        if self.edges[0] != 0 or any(b <= a for a, b in zip(self.edges, self.edges[1:])):
            raise ValueError("Glucose times must increase from zero")

    @property
    def left(self):
        return self.values[:-1]

    @property
    def right(self):
        return self.values[1:]

    @property
    def horizon(self):
        return self.edges[-1]

    @property
    def segments(self):
        return len(self.edges) - 1

    def segment_value(self, j, time):
        start, end = self.edges[j : j + 2]
        return self.left[j] + (self.right[j] - self.left[j]) * (time - start) / (end - start)


@dataclass(frozen=True)
class Parameters:
    alpha: float
    beta: float
    K: float
    gamma: float
    basal: float
    threshold: float
    gain: float = 1

    def __post_init__(self):
        for key in ("alpha", "gamma", "threshold"):
            number(getattr(self, key), positive=True)
        for key in ("beta", "K", "basal", "gain"):
            number(getattr(self, key))


def parameters(protocol, baseline, gain):
    p = protocol["source"]["parameters"]
    return Parameters(
        p["alpha_per_min"],
        p["beta_pmol_kg_min_per_mg_dl"],
        p["K_pmol_kg_per_mg_dl"],
        p["gamma_per_min"],
        baseline["Sb_pmol_kg_min"],
        baseline["h_mg_dl"],
        gain,
    )


def rates(glucose, glucose_rate, z, portal, p):
    """Internal RHS: no clipping of integrated states, including trial stages."""
    target = max(p.basal + p.gain * p.beta * (glucose - p.threshold), 0)
    pancreatic = z + p.gain * p.K * max(glucose_rate, 0)
    liver = p.gamma * portal
    return p.alpha * (target - z), pancreatic - liver, pancreatic, liver


def settings(spec):
    result = {k: v for k, v in spec.items() if k != "name"}
    if set(result) != {"method", "rtol", "atol", "max_step"} or result["method"] not in (
        "RK45",
        "DOP853",
    ):
        raise ValueError("Incomplete solver settings")
    for key in ("rtol", "atol", "max_step"):
        number(result[key], positive=True)
    if result["rtol"] >= 1:
        raise ValueError("Invalid relative tolerance")
    return result


def simulate(times, glucose, initial, p, solver):
    """Integrate an explicit continuous piecewise-affine glucose clamp/ramp."""
    if not isinstance(glucose, GlucoseSignal):
        raise ValueError("Glucose samples must be a checked affine signal")
    if any(a != b for a, b in zip(glucose.right[:-1], glucose.left[1:])):
        raise ValueError("Glucose jumps need an impulse convention; use continuous ramps")
    times = np.asarray(times, dtype=float)
    if (
        times.ndim != 1
        or len(times) < 2
        or not np.isfinite(times).all()
        or times[0] != 0
        or times[-1] != glucose.horizon
        or np.any(np.diff(times) <= 0)
    ):
        raise ValueError("Incomplete or invalid source grid")
    if len(initial) != 2:
        raise ValueError("Source rate Z and portal amount P required")
    state = np.array([number(v) for v in initial] + [0, 0], dtype=float)
    output = np.empty((len(times), 4))
    output[0] = state
    opts = settings(solver)
    for j, (start, end) in enumerate(zip(glucose.edges, glucose.edges[1:])):
        slope = (glucose.right[j] - glucose.left[j]) / (end - start)
        indices = np.flatnonzero((times > start) & (times <= end))
        requested = np.unique(np.append(times[indices], end))

        def rhs(t, x):
            g = glucose.segment_value(j, t)
            return rates(g, slope, x[0], x[1], p)

        result = solve_ivp(
            rhs,
            (start, end),
            state,
            t_eval=requested,
            first_step=min(end - start, opts["max_step"]),
            **opts,
        )
        if (
            not result.success
            or result.y.shape != (4, len(requested))
            or not np.array_equal(result.t, requested)
            or not np.isfinite(result.y).all()
        ):
            raise RuntimeError("Source solve failed or returned incomplete/nonfinite output")
        output[indices] = result.y[:, : len(indices)].T
        state = result.y[:, -1]
    return output
