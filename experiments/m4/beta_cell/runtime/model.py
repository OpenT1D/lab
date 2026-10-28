"""Bounded Pedersen–Cobelli (2013) reduced IVGTT equation reference.

Original OpenT1D implementation of final equations 3.1, 3.5, 4.9 and
4.11–4.13 (doi:10.1098/rsfs.2012.0085), not a copy of the author code.
Native units: minute, mmol/L, microgram; states X [ug], Y [ug/min].
This reduced approximation omits the derivative of the glucose-dependent
factor when introducing Y. It is not justified for arbitrary glucose inputs.
Only a single nonincreasing exponential post-bolus scenario is exposed.
"""

from dataclasses import dataclass
from math import isfinite

import numpy as np
from scipy.integrate import solve_ivp

MODEL_VERSION = "pedersen-cobelli-2013-reduced/1"


def _number(name, value, *, positive=False):
    if isinstance(value, (bool, np.bool_)) or not np.isscalar(value):
        raise ValueError(f"{name} must be a finite real number")
    try:
        valid = isfinite(value) and (value > 0 if positive else value >= 0)
    except (TypeError, ValueError, OverflowError):
        valid = False
    if not valid:
        qualifier = "positive" if positive else "nonnegative"
        raise ValueError(f"{name} must be finite and {qualifier}")


@dataclass(frozen=True)
class Parameters:
    r: float
    p_plus: float
    p_minus: float
    f: float
    m: float
    k_m: float
    n: float
    c: float
    m0: float
    k_phi: float
    g_b: float

    def __post_init__(self):
        for name in ("r", "f", "m", "k_m", "n"):
            _number(name, getattr(self, name), positive=True)
        for name in ("p_plus", "p_minus", "c", "m0", "g_b", "k_phi"):
            _number(name, getattr(self, name))
        if self.k_phi <= self.g_b:
            raise ValueError("k_phi must exceed g_b")


@dataclass(frozen=True)
class GlucoseInput:
    g_max: float
    g_b: float
    tau_min: float
    kind: str = "exponential_post_bolus"

    def __post_init__(self):
        for name in ("g_max", "g_b", "tau_min"):
            _number(name, getattr(self, name), positive=True)
        if self.g_max < self.g_b:
            raise ValueError("g_max must be at least g_b; rising inputs are unsupported")
        if self.kind != "exponential_post_bolus":
            raise ValueError("only exponential_post_bolus input is supported")

    def __call__(self, time_min):
        time_min = np.asarray(time_min, dtype=float)
        if not np.all(np.isfinite(time_min)) or np.any(time_min < 0):
            raise ValueError("time must be finite and nonnegative")
        return self.g_b + (self.g_max - self.g_b) * np.exp(-time_min / self.tau_min)


def mg_dl_to_mmol_l(glucose):
    """The author's stated glucose conversion, 18 mg/dL per mmol/L."""
    glucose = _glucose(glucose)
    return glucose / 18.0


def _glucose(value):
    value = np.asarray(value, dtype=float)
    if not np.all(np.isfinite(value)) or np.any(value < 0):
        raise ValueError("glucose must be finite and nonnegative, in mmol/L")
    return value


def _hill(value, scale, exponent):
    # Ratios never exceed one, avoiding G**n overflow for otherwise valid inputs.
    small = value <= scale
    ratio = np.empty_like(value, dtype=float)
    np.divide(value, scale, out=ratio, where=small)
    np.divide(scale, value, out=ratio, where=~small)
    powered = ratio**exponent
    return np.where(small, powered / (1.0 + powered), 1.0 / (1.0 + powered))


def activation(glucose, p):
    return _hill(np.maximum(_glucose(glucose) - p.g_b, 0.0), p.k_phi - p.g_b, 3.0)


def mobilization(glucose, p):
    """M_infinity [ug/min]; m0 is mobilization, not basal insulin secretion."""
    return p.m0 + p.c * _hill(_glucose(glucose), p.k_m, p.n)


def algebraic(glucose, p):
    """Return rho [1/min] and Y_infinity [ug/min], before capacity scaling."""
    q = p.f * p.p_plus * activation(glucose, p) / (p.p_minus + p.f)
    rho = p.r + q
    y_infinity = q * mobilization(glucose, p) / rho
    if not np.all(np.isfinite(rho)) or not np.all(np.isfinite(y_infinity)):
        raise ValueError("parameters produce nonfinite algebraic quantities")
    return rho, y_infinity


def initial_state(p, glucose_input, capacity=1.0):
    """Literal printed 4.13; D0=M(input basal)/r, Y0=0.

    This intentionally differs from the author's hard-coded X0=92.7 ug.
    Capacity scales nominal provision and the nominal initial insulin pool.
    """
    _number("capacity", capacity)
    if glucose_input.g_b > p.g_b:
        raise ValueError(
            "input basal must not exceed the activation threshold for basal initialization"
        )
    docked_basal = mobilization(glucose_input.g_b, p) / p.r
    x0 = p.p_plus * activation(glucose_input.g_max, p) * docked_basal / (p.p_minus + p.f)
    state = np.asarray([capacity * x0, 0.0], dtype=float)
    if not np.all(np.isfinite(state)):
        raise ValueError("parameters produce nonfinite initial state")
    return state


def simulate(
    times,
    p,
    glucose_input,
    capacity=1.0,
    x0_override=None,
    method="RK45",
    rtol=1e-9,
    atol=1e-11,
    max_step=0.25,
):
    """Return rows [X,Y] at a finite strictly increasing grid starting at zero.

    x0_override, if present, replaces nominal X0 [ug] before capacity scaling;
    Y0 remains zero. This numerical override bypasses the basal-equilibrium
    initializer, permitting constant suprathreshold forcing for verification.
    It does not assert that its starting state is a physiological equilibrium.
    Solver failure, incomplete output and nonfinite states raise RuntimeError.
    """
    if not isinstance(p, Parameters) or not isinstance(glucose_input, GlucoseInput):
        raise ValueError("Parameters and GlucoseInput instances are required")
    times = np.asarray(times, dtype=float)
    if (
        times.ndim != 1
        or len(times) < 2
        or not np.all(np.isfinite(times))
        or times[0] != 0.0
        or np.any(np.diff(times) <= 0.0)
    ):
        raise ValueError("times must be finite, strictly increasing, and start at zero")
    for name, value in (("rtol", rtol), ("atol", atol), ("max_step", max_step)):
        _number(name, value, positive=True)
    if rtol >= 1.0:
        raise ValueError("rtol must be smaller than one")
    if method not in ("RK45", "DOP853"):
        raise ValueError("method must be RK45 or DOP853")
    _number("capacity", capacity)
    if x0_override is not None:
        _number("x0_override", x0_override)
        start = np.asarray([capacity * x0_override, 0.0], dtype=float)
        if not np.isfinite(start[0]):
            raise ValueError("capacity-scaled x0_override must be finite")
    else:
        start = initial_state(p, glucose_input, capacity)

    def derivative(time_min, state):
        rho, y_infinity = algebraic(glucose_input(time_min), p)
        x, y = state
        return [y - p.m * x, rho * (capacity * y_infinity - y)]

    result = solve_ivp(
        derivative,
        (times[0], times[-1]),
        start,
        t_eval=times,
        method=method,
        rtol=rtol,
        atol=atol,
        max_step=max_step,
    )
    if (
        not result.success
        or result.y.shape != (2, len(times))
        or not np.array_equal(result.t, times)
        or not np.all(np.isfinite(result.y))
    ):
        raise RuntimeError(f"incomplete or nonfinite integration: {result.message}")
    return result.y.T.copy()
