"""Forward C-peptide kinetics from the process scheme in Polonsky et al. 1986.

Amounts: pmol/kg; input: pmol/(kg min); volume: L/kg; concentration: pmol/L.
No glucose, insulin clearance, subcutaneous absorption or inverse estimator.
"""

from dataclasses import dataclass

import numpy as np
from scipy.integrate import solve_ivp

from experiments.m4.kinetic_inlet.forcing import Forcing

VERSION = "polonsky1986-forward-cpeptide/1"


def finite(value, name, *, positive=False):
    if isinstance(value, (bool, np.bool_, str, bytes)) or not np.isscalar(value):
        raise ValueError(f"{name} must be a finite numeric scalar")
    try:
        number = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{name} must be numeric") from exc
    if not np.isfinite(number) or (number <= 0 if positive else number < 0):
        raise ValueError(f"{name} must be finite and {'positive' if positive else 'nonnegative'}")
    return number


@dataclass(frozen=True)
class Parameters:
    k1: float
    k2: float
    k3: float
    volume_l_kg: float

    def __post_init__(self):
        for name in ("k1", "k2", "k3", "volume_l_kg"):
            object.__setattr__(self, name, finite(getattr(self, name), name, positive=name != "k1"))


def initial_state(spec, params):
    kind = spec.get("kind")
    if kind == "zero" and set(spec) == {"kind"}:
        return np.zeros(4)
    if kind == "bolus" and set(spec) == {"kind", "dose_pmol_kg"}:
        return np.array([finite(spec["dose_pmol_kg"], "bolus dose"), 0, 0, 0])
    if kind == "equilibrium" and set(spec) == {"kind", "basal_q_pmol_kg_min"}:
        central = finite(spec["basal_q_pmol_kg_min"], "basal rate") / params.k3
        return np.array([central, params.k1 / params.k2 * central, 0, 0])
    raise ValueError("Unsupported or incomplete initial-state definition")


def insulin_mass_to_molar_input(rate_ug_min, body_weight_kg):
    """Explicit equimolar appearance assumption; rounded source MW 5808 g/mol.

    This is a unit bridge, not a calibration of BC-001 or proof of graft processing.
    """
    return (
        finite(rate_ug_min, "insulin mass rate")
        * 1e6
        / (5808 * finite(body_weight_kg, "body weight", positive=True))
    )


def concentration_to_pmol_l(value, unit):
    value = finite(value, "C-peptide concentration")
    if unit == "pmol/L":
        return value
    if unit == "pmol/mL":
        return value * 1000
    if unit == "ng/mL":
        return value * 1e6 / 3021  # Polonsky p99 footnote; rounded MW in g/mol.
    raise ValueError("Unsupported C-peptide concentration unit")


def simulate(times, params, forcing, initial, settings):
    if not isinstance(params, Parameters) or not isinstance(forcing, Forcing):
        raise ValueError("Explicit Parameters and finite molar Forcing are required")
    grid = np.asarray(times, dtype=float)
    state = np.asarray(initial, dtype=float).copy()
    if (
        grid.ndim != 1
        or len(grid) < 2
        or not np.isfinite(grid).all()
        or grid[0] != 0
        or grid[-1] != forcing.horizon
        or np.any(np.diff(grid) <= 0)
    ):
        raise ValueError("Output grid must increase from zero to the exact input horizon")
    if (
        state.shape != (4,)
        or not np.isfinite(state).all()
        or np.any(state < 0)
        or np.any(state[2:] != 0)
    ):
        raise ValueError(
            "Initial inventories must be nonnegative and both ledgers must start at zero"
        )
    solver = {k: v for k, v in settings.items() if k != "name"}
    if set(solver) != {"method", "rtol", "atol", "max_step"} or solver["method"] not in {
        "RK45",
        "DOP853",
    }:
        raise ValueError("Incomplete or unsupported numerical settings")
    for key in ("rtol", "atol", "max_step"):
        solver[key] = finite(solver[key], key, positive=True)
    if solver["rtol"] >= 1:
        raise ValueError("rtol must be less than one")
    output = np.empty((len(grid), 4))
    output[0] = state
    filled = np.zeros(len(grid), dtype=bool)
    filled[0] = True
    for i in range(forcing.segments):
        start, stop = forcing.edges[i : i + 2]
        indices = np.flatnonzero((grid > start) & (grid <= stop))
        requested = np.unique(np.append(grid[indices], stop))

        def rhs(t, amounts):
            central, peripheral = amounts[:2]
            rate = forcing.segment_value(i, t)
            exchange = params.k1 * central - params.k2 * peripheral
            removed = params.k3 * central
            return [rate - exchange - removed, exchange, removed, rate]

        solution = solve_ivp(
            rhs,
            (start, stop),
            state,
            t_eval=requested,
            first_step=min(stop - start, solver["max_step"]),
            **solver,
        )
        if (
            not solution.success
            or solution.y.shape != (4, len(requested))
            or not np.array_equal(solution.t, requested)
            or not np.isfinite(solution.y).all()
        ):
            raise RuntimeError(
                f"Incomplete/nonfinite C-peptide solve at segment {i}: {solution.message}"
            )
        output[indices] = solution.y[:, : len(indices)].T
        filled[indices] = True
        state = solution.y[:, -1].copy()
    if not filled.all():
        raise RuntimeError("Incomplete C-peptide output grid")
    return output
