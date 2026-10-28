"""Causal one-state model on the unchanged BC-008 native metabolic boundary.

Indices 0:13 native; 13 Z (rate), 14 P (amount); 15:20 SC, pancreatic,
liver-arrival, hepatic-loss, peripheral-loss integrated amounts [pmol/kg].
"""

from bisect import bisect_right
from types import SimpleNamespace

import numpy as np
from scipy.integrate import quad_vec, solve_ivp

from experiments.m4.feedback.secretion import settings
from experiments.m4.kinetic_inlet.native import Action, T1DPatient

from .common import evaluate

PHYSICAL = tuple(i for i in range(15) if i != 6)
SWITCHES = ("glucose_rate_zero", "egp_floor", "renal_threshold")


def glucose_fluxes(x, p):
    """Independent native flux formulas, never inferred from a balance residual."""
    return np.array(
        [
            max(p.kp1 - p.kp2 * x[3] - p.kp3 * x[8], 0),
            p.f * p.kabs * x[2] / p.BW,
            p.Fsnc,
            (p.Vm0 + p.Vmx * x[6]) * x[4] / (p.Km0 + x[4]),
            p.ke1 * max(x[3] - p.ke2, 0),
        ]
    )


def rhs_factory(params, basal, gamma, load, model, model_params, task, mode):
    if mode not in ("candidate", "host_constant_basal"):
        raise ValueError("Unsupported causal source mode")
    p = SimpleNamespace(**params)
    action = Action(CHO=0, insulin=basal["action_insulin_u_min"])

    def rhs(t, x):
        dx = T1DPatient.model(t, x[:13], action, p, load, 0)
        if mode == "host_constant_basal":
            dz, pancreatic = 0.0, basal["Sb_pmol_kg_min"]
        else:
            dz, pancreatic = evaluate(
                model,
                t,
                x[3] / p.Vg,
                dx[3] / p.Vg,
                x[13],
                basal["Sb_pmol_kg_min"],
                basal["h_mg_dl"],
                model_params,
                task,
            )
        liver = gamma * x[14]
        dp = pancreatic - liver
        # Keep the native state guard, including trial stages. No state clipping.
        dx[9] += liver * (x[9] >= 0)
        return np.r_[
            dx, dz, dp, basal["u_sc_pmol_kg_min"], pancreatic, liver, p.m30 * x[9], p.m4 * x[5]
        ]

    return rhs


def integrate(task, protocol, params, basal, gamma, load, solver, model, model_params, mode):
    horizon, step = protocol["horizon_min"], protocol["sample_step_min"]
    times = np.arange(0, horizon + step / 2, step)
    opts = settings(solver)
    x0 = np.r_[basal["state"], basal["Z_pmol_kg_min"], basal["P_pmol_kg"], np.zeros(5)]
    x0[0] = load
    rhs = rhs_factory(params, basal, gamma, load, model, model_params, task, mode)
    p = SimpleNamespace(**params)
    lower, upper = protocol["glucose_envelope_mg_dl"]
    tolerance = protocol["criteria"]["negative_amount_tolerance"]

    def low(t, x):
        return x[3] / p.Vg - lower

    def high(t, x):
        return upper - x[3] / p.Vg

    def negative(t, x):
        return np.min(x[list(PHYSICAL)]) + tolerance

    for event in (low, high, negative):
        event.terminal = True
        event.direction = -1

    def gd(t, x):
        return rhs(t, x)[3] / p.Vg

    def egp(t, x):
        return p.kp1 - p.kp2 * x[3] - p.kp3 * x[8]

    def renal(t, x):
        return x[3] - p.ke2

    events = (low, high, negative, gd, egp, renal)
    names = ("glucose_below_envelope", "glucose_above_envelope", "negative_amount", *SWITCHES)
    state, pieces, stops = x0.copy(), [], []
    transitions = {name: [] for name in names}
    failure = None
    nfev = 0
    if low(0, x0) <= 0 or high(0, x0) <= 0 or negative(0, x0) <= 0:
        raise ValueError("Initial state outside the declared domain")
    edges = [0, horizon]
    for start, stop in zip(edges, edges[1:]):
        result = solve_ivp(
            rhs,
            (start, stop),
            state,
            dense_output=True,
            events=events,
            first_step=min(stop - start, opts["max_step"]),
            **opts,
        )
        nfev += result.nfev
        pieces.append(result.sol)
        stops.append(float(result.t[-1]))
        for name, roots in zip(names, result.t_events):
            transitions[name].extend(roots.tolist())
        state = result.y[:, -1]
        if result.status != 0 or result.t[-1] != stop or not np.isfinite(result.y).all():
            failure = {
                "message": result.message,
                "time": float(result.t[-1]),
                "last_state": state.tolist(),
                "terminal_events": [name for name in names[:3] if transitions[name]],
            }
            break

    def dense(t):
        j = min(bisect_right(stops, float(t)), len(pieces) - 1)
        return pieces[j](t)

    sampled_times = times[times <= stops[-1]]
    values = np.array([dense(t) for t in sampled_times])
    if not np.isfinite(values).all():
        raise RuntimeError("Nonfinite feedback output")
    if failure is None and len(sampled_times) != len(times):
        raise RuntimeError("Incomplete feedback output without failure record")
    # Independent dense-trajectory quadrature split at the output grid and
    # recorded native regime transitions; no implied model discontinuities.
    cuts = sorted({*edges, *(t for roots in transitions.values() for t in roots)})
    fluxes, errors = [np.zeros(5)], [0.0]
    for a, b in zip(sampled_times, sampled_times[1:]):
        points = [c for c in cuts if a < c < b]
        value, error = quad_vec(
            lambda t: glucose_fluxes(dense(t), p),
            a,
            b,
            epsabs=1e-9,
            epsrel=1e-9,
            points=points,
            norm="max",
        )
        fluxes.append(fluxes[-1] + value)
        errors.append(errors[-1] + float(error))
    if errors[-1] > 1e-6:
        raise RuntimeError("Glucose quadrature error requires tighter verification")
    src = []
    for t, x in zip(sampled_times, values):
        dx = rhs(t, x)
        src.append([float(dx[16]), float(dx[17])])
    record = {
        "schema": "m4-causal-trajectory/1",
        "status": "failed" if failure else "completed",
        "failure": failure,
        "solver": solver,
        "nfev": nfev,
        "initial": x0.tolist(),
        "baseline": basal,
        "load_mg": load,
        "mode": mode,
        "times": sampled_times.tolist(),
        "states": values.tolist(),
        "source_rates": src,
        "transitions": transitions,
        "glucose_flux_integrals": np.asarray(fluxes).tolist(),
        "glucose_quadrature_error_bounds": errors,
        "quadrature": {
            "method": "quad_vec",
            "epsabs": 1e-9,
            "epsrel": 1e-9,
            "norm": "max",
            "flux_order": ["EGP", "Ra", "Uii", "Uid", "renal"],
        },
    }
    return record, dense
