"""Verify source-audit deductions in the unchanged BC-001 numerical runtime."""

import argparse
import json
import platform
from pathlib import Path

import numpy as np
import scipy
from scipy.integrate import solve_ivp

from experiments.m4.beta_cell.runtime.model import GlucoseInput, Parameters, simulate

from .audit import burst, calculate


def integrate(times, initial, p, settings):
    def rhs(_t, state):
        h, f, _l, _u = state
        return [-(p["f"] + p["p_minus"]) * h, p["f"] * h - p["m"] * f, p["m"] * f, p["p_minus"] * h]

    result = solve_ivp(rhs, (times[0], times[-1]), initial, t_eval=times, **settings)
    if (
        not result.success
        or result.y.shape != (4, len(times))
        or not np.array_equal(result.t, times)
        or not np.isfinite(result.y).all()
    ):
        raise RuntimeError("Incomplete isolated-pool integration")
    return result.y.T


def execute(p):
    if np.__version__ != "2.2.6" or scipy.__version__ != "1.15.3":
        raise ValueError("Wrong scientific runtime")
    params = Parameters(**p["parameters"])
    settings = [{k: v for k, v in s.items() if k != "name"} for s in p["solvers"]]
    b = p["burst"]
    times = np.arange(round(b["horizon_min"] / b["step_min"]) + 1) * b["step_min"]
    states = [integrate(times, [b["h0_ug"], 0, 0, 0], p["parameters"], s) for s in settings]
    analytic = np.array([burst(t, b["h0_ug"], params.f, params.p_minus, params.m) for t in times])
    r, s = p["reduced_comparison"], p["source_values"]
    reduced_times = np.arange(round(r["horizon_min"] / r["step_min"]) + 1) * r["step_min"]
    glucose = GlucoseInput(s["g_max_mmol_l"], r["g_b_mmol_l"], s["tau_min"])
    calc = calculate(p)
    pool = calc["pools"]["caption_basal_equilibrium"]
    initials = {
        "printed": pool["printed_qss_ug"],
        "author_explicit": s["author_x0_ug"],
        "pre_bolus_hypothesis": pool["pre_bolus_recruited_ug"],
    }
    reduced = {
        name: [
            simulate(reduced_times, params, glucose, capacity=r["capacity"], x0_override=x, **st)
            for st in settings
        ]
        for name, x in initials.items()
    }
    repeated = simulate(
        reduced_times, params, glucose, x0_override=initials["pre_bolus_hypothesis"], **settings[-1]
    )
    return {
        "schema": "bc006-numerical/1",
        "runtime": {
            "python": platform.python_version(),
            "numpy": np.__version__,
            "scipy": scipy.__version__,
        },
        "burst_times_min": times.tolist(),
        "burst_states": [v.tolist() for v in states],
        "burst_analytic": analytic.tolist(),
        "reduced_times_min": reduced_times.tolist(),
        "reduced_initials_ug": initials,
        "reduced_states": {name: [v.tolist() for v in values] for name, values in reduced.items()},
        "repeated_reference": repeated.tolist(),
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("directory", type=Path)
    args = parser.parse_args()
    p = json.loads((args.directory / "protocol.json").read_text())
    result = execute(p)
    with (args.directory / "numerical.json").open("x") as handle:
        json.dump(result, handle, indent=2, allow_nan=False)
        handle.write("\n")


if __name__ == "__main__":
    main()
