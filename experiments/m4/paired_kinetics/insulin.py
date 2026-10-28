"""BC-005 nonzero-inventory wrapper derived from OpenT1D BC-002.

Keeps its integration order and calls the unchanged guarded native derivative.
The upstream package and the historical zero-initial wrapper remain unchanged.
"""

from types import SimpleNamespace

import numpy as np
from scipy.integrate import solve_ivp

from experiments.m4.kinetic_inlet.forcing import Forcing
from experiments.m4.kinetic_inlet.native import ROUTE_INDEX, Action, derivative


def simulate(times, params, forcing, initial, settings):
    """BC-002 integration path with explicit inventory initialization, liver input only."""
    route = "liver"
    if not isinstance(forcing, Forcing) or route not in ROUTE_INDEX:
        raise ValueError("valid Forcing and liver/peripheral route are required")
    times = np.asarray(times, dtype=float)
    if (
        times.ndim != 1
        or len(times) < 2
        or not np.all(np.isfinite(times))
        or times[0] != 0
        or times[-1] != forcing.horizon
        or np.any(np.diff(times) <= 0)
    ):
        raise ValueError("finite increasing output grid must span exactly the forcing horizon")
    solver = {key: value for key, value in settings.items() if key != "name"}
    if set(solver) != {"method", "rtol", "atol", "max_step"}:
        raise ValueError("solver settings must specify method, rtol, atol, and max_step")
    if solver["method"] not in ("RK45", "DOP853"):
        raise ValueError("unsupported integration method")
    for key in ("rtol", "atol", "max_step"):
        value = solver[key]
        if (
            isinstance(value, bool)
            or not np.isscalar(value)
            or not np.isfinite(value)
            or value <= 0
        ):
            raise ValueError(f"{key} must be finite and positive")
    if solver["rtol"] >= 1:
        raise ValueError("rtol must be less than one")
    carrier = np.asarray(params.iloc[2:15].values, dtype=float).copy()
    # The derivative owns every equation. A value-preserving attribute carrier
    # avoids repeated pandas label lookup at every solver evaluation.
    model_params = SimpleNamespace(**params.to_dict())
    carrier[10:12] = 0.0  # No pharmaceutical SC absorption in incremental kinetics.
    action = Action(CHO=0.0, insulin=0.0)
    raw = np.asarray(initial)
    if raw.dtype.kind not in "fiu" or raw.shape != (5,):
        raise ValueError("Initial state must contain five numeric inventories/ledgers")
    state = raw.astype(float).copy()
    if not np.isfinite(state).all() or np.any(state < 0) or np.any(state[2:] != 0):
        raise ValueError("Initial inventories must be nonnegative; ledgers must start at zero")
    output = np.empty((len(times), 5), dtype=float)
    output[0] = state
    filled = np.zeros(len(times), dtype=bool)
    filled[0] = True
    for segment in range(forcing.segments):
        start, stop = forcing.edges[segment : segment + 2]
        indices = np.flatnonzero((times > start) & (times <= stop))
        requested = times[indices]
        integration_times = np.unique(np.append(requested, stop))

        def rhs(time, current):
            carrier[5], carrier[9] = current[:2]
            q = forcing.segment_value(segment, time)
            native = derivative(time, carrier, action, model_params, q=q, route=route)
            return [
                native[5],
                native[9],
                model_params.m30 * current[1],
                model_params.m4 * current[0],
                q,
            ]

        # SciPy 1.13's automatic initial-step estimator may evaluate outside
        # t_span before enforcing max_step. Keep every probe in this segment;
        # accepted steps still adapt to the prespecified error tolerances.
        result = solve_ivp(
            rhs,
            (start, stop),
            state,
            t_eval=integration_times,
            first_step=min(stop - start, solver["max_step"]),
            **solver,
        )
        if (
            not result.success
            or result.y.shape != (5, len(integration_times))
            or not np.array_equal(result.t, integration_times)
            or not np.all(np.isfinite(result.y))
        ):
            raise RuntimeError(
                f"native subsystem solve failed or incomplete at segment {segment}: "
                f"{result.message}"
            )
        output[indices] = result.y[:, : len(indices)].T
        filled[indices] = True
        state = result.y[:, -1].copy()
    if not np.all(filled) or not np.all(np.isfinite(output)):
        raise RuntimeError("native subsystem output is incomplete or nonfinite")
    return output
