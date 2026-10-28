"""Faggionato 2021 equations with declared synthetic, zero-history bolus input.

No physiological engine integration, fitted person or reconstructed cohort.
Equation (3)'s printed ka1(t) is interpreted as the per-person constant ka1,
consistent with its other rows, Figure 3, Equation (12) and Table 2.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from scipy.integrate import solve_ivp


@dataclass(frozen=True)
class Parameters:
    tau: float
    volume: float
    alpha: float
    ka1: float
    ka2: float
    ke: float

    def __post_init__(self) -> None:
        if not all(
            not isinstance(x, bool) and np.isfinite(x) and x > 0 for x in vars(self).values()
        ):
            raise ValueError("Parameters must be finite and positive")

    @classmethod
    def from_record(cls, record: dict) -> Parameters:
        p = record["deterministic_parameters"]
        return cls(*(p[k]["value"] for k in ("tau", "V_I", "alpha", "k_a1", "k_a2", "k_e")))

    @property
    def kd(self) -> float:
        return self.ka2 + self.alpha


def validate(times: np.ndarray, dose: float) -> None:
    if isinstance(dose, bool) or not np.isfinite(dose) or dose < 0:
        raise ValueError("Dose must be finite and nonnegative")
    if times.ndim != 1 or not len(times) or not np.all(np.isfinite(times)):
        raise ValueError("A finite one-dimensional time grid is required")
    if times[0] < 0 or np.any(np.diff(times) <= 0):
        raise ValueError("Times must be nonnegative and strictly increasing")


def analytic(times: np.ndarray, dose: float, p: Parameters) -> np.ndarray:
    """Closed-form chain response; states SC1, SC2, plasma, eliminated (mU/kg)."""
    validate(times, dose)
    a, b, c = p.ka1 + p.kd, p.ka2, p.ke
    if min(abs(a - b), abs(c - a), abs(c - b)) < 1e-10:
        raise ValueError("Closed form requires distinct rates; no limiting formula assumed")
    s = np.maximum(times - p.tau, 0)
    ea, eb, ec = np.exp(-a * s), np.exp(-b * s), np.exp(-c * s)
    sc1 = dose * ea
    sc2 = dose * p.kd * (eb - ea) / (a - b)
    plasma = dose * p.ka1 * (ea - ec) / (c - a)
    plasma += dose * p.kd * b / (a - b) * ((eb - ec) / (c - b) - (ea - ec) / (c - a))
    eliminated = dose - sc1 - sc2 - plasma
    result = np.column_stack((sc1, sc2, plasma, eliminated))
    result[times < p.tau] = 0
    return result


def numerical(
    times: np.ndarray,
    dose: float,
    p: Parameters,
    *,
    method: str,
    rtol: float,
    atol: float,
) -> np.ndarray:
    """Integrate from the exact delayed impulse, without rounding its event time."""
    validate(times, dose)
    output = np.zeros((len(times), 4))
    active = times >= p.tau
    if not np.any(active):
        return output
    if times[-1] == p.tau:
        output[active] = (dose, 0, 0, 0)
        return output

    def rhs(_time: float, state: np.ndarray) -> tuple[float, ...]:
        first, second, plasma, _eliminated = state
        return (
            -(p.ka1 + p.kd) * first,
            p.kd * first - p.ka2 * second,
            p.ka1 * first + p.ka2 * second - p.ke * plasma,
            p.ke * plasma,
        )

    solved = solve_ivp(
        rhs,
        (p.tau, times[-1]),
        (dose, 0, 0, 0),
        t_eval=times[active],
        method=method,
        rtol=rtol,
        atol=atol,
    )
    if not solved.success or solved.y.shape != (4, active.sum()):
        raise RuntimeError(f"Incomplete integration: {solved.message}")
    output[active] = solved.y.T
    if not np.all(np.isfinite(output)):
        raise ValueError("Nonfinite numerical result")
    return output
