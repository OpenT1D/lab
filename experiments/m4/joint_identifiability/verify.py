"""Numerical gates for BC-011, executed before synthetic inverse fitting."""

import numpy as np
from scipy.linalg import expm

from experiments.m4.feedback.coupled import integrate
from experiments.m4.feedback.secretion import parameters


def mass_errors(record):
    """Two separately owned conserved inventories, including initial amounts."""
    states, initial = record["states"], record["initial"]
    insulin = [5, 9, 10, 11, 14]
    insulin_error = (
        states[:, insulin].sum(axis=1)
        - initial[insulin].sum()
        + states[:, 18]
        + states[:, 19]
        - states[:, 15]
        - states[:, 16]
    )
    cp_error = states[:, 20:22].sum(axis=1) - initial[20:22].sum() + states[:, 22] - states[:, 23]
    return {
        "insulin_pmol_kg": float(np.max(np.abs(insulin_error))),
        "cpeptide_pmol_kg": float(np.max(np.abs(cp_error))),
        "paired_pancreatic_ledgers_pmol_kg": float(np.max(np.abs(states[:, 16] - states[:, 23]))),
    }


def cpeptide_oracle(times, pancreatic, initial, cp):
    """Independent affine-input matrix exponential, no model RHS imports.

    State [Q1,Q2,removed,delivered,q,dq/dt]; the last pair propagates the
    interpolated pancreatic source. Constant-step exponentials are reused.
    """
    matrix = np.zeros((6, 6))
    matrix[0, 0], matrix[0, 1] = -(cp["k1"] + cp["k3"]), cp["k2"]
    matrix[1, 0], matrix[1, 1] = cp["k1"], -cp["k2"]
    matrix[2, 0] = cp["k3"]
    matrix[0, 4] = matrix[3, 4] = matrix[4, 5] = 1
    state, result, operators = np.asarray(initial).copy(), [np.asarray(initial).copy()], {}
    for j, dt in enumerate(np.diff(times)):
        if dt not in operators:
            operators[dt] = expm(matrix * dt)
        slope = (pancreatic[j + 1] - pancreatic[j]) / dt
        state = (operators[dt] @ np.r_[state, pancreatic[j], slope])[:4]
        result.append(state.copy())
    return np.asarray(result)


def run(model):
    p, criteria = model.protocol, model.protocol["criteria"]
    checks, details = {}, {}

    def gate(name, value, criterion):
        limit = criteria[criterion]
        checks[name] = {
            "passed": bool(np.isfinite(value) and value <= limit),
            "value": float(value),
            "limit": limit,
            "criterion": criterion,
        }

    truth = p["model"]["truth"]
    reference = None
    for name, theta in (
        ("truth", truth),
        ("lower_corner", p["model"]["lower"]),
        ("upper_corner", p["model"]["upper"]),
    ):
        _, basal, _, initial, rhs = model.prepare(theta)
        derivative_error = np.max(np.abs(rhs(0, initial)[list(range(15)) + [20, 21]]))
        gate(name + "/fasting_derivative", derivative_error, "baseline_derivative_error")
        records = {solver: model.simulate(theta, solver=solver) for solver in p["solvers"]}
        if name == "truth":
            reference = records["reference"]
        for solver, record in records.items():
            error = np.max(
                np.abs((record["observations"] - records["reference"]["observations"]) / model.sd)
            )
            gate(name + "/" + solver + "/output", error, "solver_scaled_output_error")
            for key, value in mass_errors(record).items():
                gate(name + "/" + solver + "/" + key, value, "mass_balance_error_pmol_kg")
        details[name] = {
            "theta": theta,
            "derived_Sb_pmol_kg_min": basal["Sb_pmol_kg_min"],
            "fasting_derivative_native_units_per_min": float(derivative_error),
            "initial_observations": records["reference"]["observations"][0].tolist(),
            "nfev": {solver: record["nfev"] for solver, record in records.items()},
        }

    parent_protocol = {**model.parent_protocol, "sample_step_min": 1}
    parent, _ = integrate(
        parent_protocol,
        model.params,
        model.nominal,
        parameters(model.parent_protocol, model.nominal, 1),
        p["model"]["load_mg"],
        p["solvers"]["reference"],
    )
    if parent["status"] != "completed":
        raise RuntimeError("Original BC-008 reference failed")
    original = np.asarray(parent["states"])[:, [3, 5]] / np.array(
        [model.params["Vg"], model.params["Vi"]]
    )
    gate(
        "original_BC008_GI",
        np.max(np.abs((original - reference["observations"][:, :2]) / model.sd[:2])),
        "parent_GI_scaled_error",
    )

    symmetry = {}
    for scale in (0.5, 2.0):
        alternative = model.simulate(truth, solver="reference", source_scale=scale)
        error = np.max(np.abs((alternative["observations"] - reference["observations"]) / model.sd))
        gate("gain_beta_K_symmetry/" + str(scale), error, "exact_symmetry_scaled_error")
        symmetry[str(scale)] = float(error)
    details["exact_symmetry"] = {
        "operation": "gain times scale; beta and K divided by scale; all else identical",
        "scaled_output_errors": symmetry,
        "interpretation": "Exact redundancy removed from inference by fixing beta and K",
    }

    passive = []
    for k3_scale in (0.5, 1.5):
        value = model.simulate([1, 1, k3_scale], solver="reference")
        error = np.max(
            np.abs((value["observations"][:, :2] - reference["observations"][:, :2]) / model.sd[:2])
        )
        gate("passive_k3/" + str(k3_scale), error, "passive_GI_scaled_error")
        passive.append({"k3_scale": k3_scale, "GI_scaled_error": float(error)})
    # Equation locality is exact even when numerical steps differ because of Cp.
    _, _, _, state_a, rhs_a = model.prepare([1, 1, 0.5])
    _, _, _, state_b, rhs_b = model.prepare([1, 1, 1.5])
    equation_error = float(np.max(np.abs(rhs_a(0, state_a)[:20] - rhs_b(0, state_b)[:20])))
    checks["passive_k3/equation_locality"] = {
        "passed": equation_error == 0,
        "value": equation_error,
        "limit": 0.0,
    }
    details["passive_k3"] = passive

    cp = p["model"]["cpeptide"]
    dense_times = np.arange(0, p["model"]["horizon_min"] + 0.03125, 0.0625)
    fine = model.simulate(truth, times=dense_times, solver="reference")
    params, basal, source, _, _ = model.prepare(truth)
    loaded_rhs = model._rhs(params, basal, source, p["model"]["load_mg"], 1)
    pancreatic = np.array(
        [loaded_rhs(t, state)[16] for t, state in zip(dense_times, fine["states"])]
    )
    oracle_refinement = []
    for stride in (4, 2, 1):
        oracle = cpeptide_oracle(
            dense_times[::stride], pancreatic[::stride], fine["initial"][20:24], cp
        )
        error = np.max(np.abs(oracle[:, 0] - fine["states"][::stride, 20])) / cp["volume_l_kg"]
        oracle_refinement.append({"source_step_min": 0.0625 * stride, "error_pmol_l": float(error)})
    gate("independent_cpeptide", oracle_refinement[-1]["error_pmol_l"], "cp_oracle_error_pmol_l")
    details["cpeptide_oracle"] = {
        "method": "Independent six-state affine forcing matrix exponential",
        "comparison": "monolithic reference Q1 versus sampled-source propagation",
        "refinement": oracle_refinement,
        "error_includes": "piecewise-linear source interpolation and ODE error",
    }
    return {
        "passed": all(item["passed"] for item in checks.values()),
        "checks": checks,
        "details": details,
        "scope": "Forward gates; derivative refinement and recovery checked separately",
    }
