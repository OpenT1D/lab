"""Isolated BC-009 wrapper and solver; no edits or monkeypatches to BC-008."""

from types import SimpleNamespace

import numpy as np
from scipy.integrate import quad_vec, solve_ivp

from experiments.m4.feedback import coupled, secretion

from .model import terms


def rhs_factory(params, basal, source, hepatic, load, variant):
    original = coupled.rhs_factory(params, basal, source, load)
    if not variant["extraction"] and not variant["portal"]:
        return original

    def rhs(t, x):
        dx = original(t, x)
        h = terms(x, params, basal, hepatic, variant, check_domain=False)
        if h["delta_hepatic_loss"] != 0:
            dx[9] -= h["delta_hepatic_loss"] * (x[9] >= 0)
            dx[18] = h["m3"] * x[9]
        if h["delta_EGP"] != 0:
            dx[3] += h["delta_EGP"] * (x[3] >= 0)
            dz, dp, spo, arrival = secretion.rates(
                x[3] / params["Vg"], dx[3] / params["Vg"], x[13], x[14], source
            )
            dx[13], dx[14], dx[16], dx[17] = dz, dp, spo, arrival
        return dx

    return rhs


def integrate(parent, p, params, basal, source, load, variant, solver):
    horizon, step = parent["horizon_min"], parent["sample_step_min"]
    times = np.arange(0, horizon + step / 2, step)
    x0 = np.r_[basal["state"], basal["Z_pmol_kg_min"], basal["P_pmol_kg"], np.zeros(5)]
    x0[0] = load
    hepatic = p["source"] | {"gamma": source.gamma}
    rhs = rhs_factory(params, basal, source, hepatic, load, variant)
    lo, hi = parent["glucose_envelope_mg_dl"]
    helo, hehi = p["HE_computational_envelope"]

    def low(t, x):
        return x[3] / params["Vg"] - lo

    def high(t, x):
        return hi - x[3] / params["Vg"]

    def negative(t, x):
        return min(x[list(coupled.PHYSICAL)]) + p["verification"]["negative_amount_tolerance"]

    def helow(t, x):
        return terms(x, params, basal, hepatic, variant, check_domain=False)["HE"] - helo

    def hehigh(t, x):
        return hehi - terms(x, params, basal, hepatic, variant, check_domain=False)["HE"]

    events = [low, high, negative, helow, hehigh]
    names = ["glucose_low", "glucose_high", "negative_amount", "HE_low", "HE_high"]
    for event in events:
        event.terminal, event.direction = True, -1

    def gd(t, x):
        return rhs(t, x)[3] / params["Vg"]

    def floor(t, x):
        return source.basal + source.gain * source.beta * (x[3] / params["Vg"] - source.threshold)

    def egp(t, x):
        return terms(x, params, basal, hepatic, variant, check_domain=False)["raw_EGP"]

    def renal(t, x):
        return x[3] - params["ke2"]

    events += [gd, floor, egp, renal]
    names += ["glucose_rate_zero", "static_floor", "EGP_floor", "renal_threshold"]
    if any(event(0, x0) <= 0 for event in events[:5]):
        raise ValueError("Initial state outside protocol domain")
    opts = secretion.settings(solver)
    result = solve_ivp(
        rhs, (0, horizon), x0, dense_output=True, events=events, first_step=opts["max_step"], **opts
    )
    stop = float(result.t[-1])
    failure = None
    if result.status != 0 or stop != horizon or not np.isfinite(result.y).all():
        failure = {
            "time": stop,
            "message": result.message,
            "last_state": result.y[:, -1].tolist(),
            "terminal_events": [
                name for name, roots in zip(names[:5], result.t_events[:5]) if len(roots)
            ],
        }
    times = times[times <= stop]
    y = np.array([result.sol(t) for t in times])
    if not np.isfinite(y).all() or (failure is None and len(times) != round(horizon / step) + 1):
        raise RuntimeError("Incomplete or nonfinite solver output")
    transitions = {name: roots.tolist() for name, roots in zip(names, result.t_events)}
    cuts = sorted({t for roots in transitions.values() for t in roots})
    carrier = SimpleNamespace(**params)

    def flux(t):
        x = result.sol(t)
        values = coupled.glucose_fluxes(x, carrier)
        values[0] = terms(x, params, basal, hepatic, variant, check_domain=False)["EGP"]
        return values

    integrals, errors = [np.zeros(5)], [0.0]
    quad = p["quadrature"]
    for a, b in zip(times, times[1:]):
        values, error = quad_vec(
            flux,
            a,
            b,
            epsabs=quad["epsabs"],
            epsrel=quad["epsrel"],
            norm="max",
            points=[c for c in cuts if a < c < b],
        )
        integrals.append(integrals[-1] + values)
        errors.append(errors[-1] + float(error))
    if errors[-1] > quad["max_estimated_cumulative_error"]:
        raise RuntimeError("Independent glucose quadrature not precise enough")
    source_rates = [[float(rhs(t, x)[16]), float(rhs(t, x)[17])] for t, x in zip(times, y)]
    hepatic_terms = [terms(x, params, basal, hepatic, variant, check_domain=False) for x in y]
    return {
        "schema": "bc009-trajectory/1",
        "status": "failed" if failure else "completed",
        "failure": failure,
        "variant": variant,
        "solver": solver,
        "nfev": result.nfev,
        "baseline": basal,
        "load_mg": load,
        "initial": x0.tolist(),
        "times": times.tolist(),
        "states": y.tolist(),
        "source_rates": source_rates,
        "hepatic": hepatic_terms,
        "glucose_flux_integrals": np.asarray(integrals).tolist(),
        "quadrature_error_bounds": errors,
        "quadrature": quad,
        "transitions": transitions,
    }
