"""BC-012 forward gates, preserving every unchanged BC-011 numerical check."""

import numpy as np

from experiments.m4.joint_identifiability.verify import run as verify_parent


def run(model):
    parent = verify_parent(model.base)
    criteria = model.protocol["criteria"]
    names = (
        "correct_volume_parent_error",
        "volume_state_error",
        "volume_GI_error",
        "volume_scaling_relative_error",
        "analytic_log_volume_scaled_error",
        "basal_product_relative_error",
        "solver_scaled_output_error",
    )
    values = {name: 0.0 for name in names}
    trials = []

    def update(name, error):
        error = float(error)
        if not np.isfinite(error):
            raise RuntimeError("Nonfinite volume verification error: " + name)
        values[name] = max(values[name], error)

    for name, theta3 in (
        ("truth", model.parent["model"]["truth"]),
        ("lower_corner", model.parent["model"]["lower"]),
        ("upper_corner", model.parent["model"]["upper"]),
    ):
        baseline = {
            solver: model.base.simulate(theta3, solver=solver) for solver in model.parent["solvers"]
        }
        for volume in (0.5, 0.8, 1.0, 1.2, 1.5):
            theta = [*theta3, volume]
            reference = model.simulate(theta, solver="reference")
            for solver, original in baseline.items():
                record = model.simulate(theta, solver=solver)
                for field in ("states", "initial", "times"):
                    update("volume_state_error", np.max(np.abs(record[field] - original[field])))
                update(
                    "volume_GI_error",
                    np.max(np.abs(record["observations"][:, :2] - original["observations"][:, :2])),
                )
                if volume == 1:
                    update(
                        "correct_volume_parent_error",
                        np.max(np.abs(record["observations"] - original["observations"])),
                    )
                # Q1 is an amount in pmol/kg; 65.5 mL/kg is independently
                # converted here to L/kg before concentration is calculated.
                expected_cp = record["states"][:, 20] / (65.5e-3 * volume)
                update(
                    "volume_scaling_relative_error",
                    np.max(np.abs(record["observations"][:, 2] / expected_cp - 1)),
                )
                solver_error = np.max(
                    np.abs((record["observations"] - reference["observations"]) / model.sd)
                )
                update("solver_scaled_output_error", solver_error)
                trials.append(
                    {
                        "case": name,
                        "theta": theta,
                        "solver": solver,
                        "initial_Cp_pmol_l": float(record["observations"][0, 2]),
                        "solver_scaled_output_error": float(solver_error),
                    }
                )
            # Interior anchors allow a symmetric log-volume perturbation within
            # the frozen bounds; extrema are covered above for every solver.
            if volume in (0.8, 1.0, 1.2):
                h = 0.001
                high = model.simulate([*theta3, volume * np.exp(h)], solver="reference")
                low = model.simulate([*theta3, volume * np.exp(-h)], solver="reference")
                derivative = (high["observations"] - low["observations"]) / (2 * h)
                analytic = np.zeros_like(derivative)
                analytic[:, 2] = -reference["observations"][:, 2]
                update(
                    "analytic_log_volume_scaled_error",
                    np.max(np.abs((derivative - analytic) / model.sd)),
                )

    # One basal measurement depends on k3*V, but the loaded dynamic curves do
    # not share that symmetry: k3 changes amount decay and volume does not.
    nominal = model.simulate([1, 1, 1, 1], solver="reference")
    product = model.simulate([1, 1, 0.8, 1 / 0.8], solver="reference")
    cp = model.parent["model"]["cpeptide"]
    for record in (nominal, product):
        theta = record["theta"]
        expected = record["baseline"]["Sb_pmol_kg_min"] / (
            cp["k3"] * theta[2] * cp["volume_l_kg"] * theta[3]
        )
        update("basal_product_relative_error", abs(record["observations"][0, 2] / expected - 1))
    update(
        "basal_product_relative_error",
        abs(product["observations"][0, 2] / nominal["observations"][0, 2] - 1),
    )
    checks = {
        name: {"value": value, "limit": criteria[name], "passed": value <= criteria[name]}
        for name, value in values.items()
    }
    return {
        "passed": parent["passed"] and all(item["passed"] for item in checks.values()),
        "parent": parent,
        "checks": checks,
        "details": {
            "trials": trials,
            "volume_derivative": "dCp/dlog(V)=-Cp; dG/dlog(V)=dI/dlog(V)=0; h=0.001",
            "basal_product": {
                "nominal": nominal["theta"].tolist(),
                "matched_product": product["theta"].tolist(),
                "initial_Cp_pmol_l": [
                    float(nominal["observations"][0, 2]),
                    float(product["observations"][0, 2]),
                ],
                "dynamic_max_difference_pmol_l": float(
                    np.max(np.abs(product["observations"][:, 2] - nominal["observations"][:, 2]))
                ),
                "scope": "Basal identity only; no whole-trajectory symmetry claimed",
            },
        },
    }
