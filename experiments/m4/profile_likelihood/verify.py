"""Independent analytic nuisance-profile and conditional-volume oracles."""

import json
from pathlib import Path

import numpy as np
from scipy.optimize import minimize_scalar

from .optimizer import Problem, project_volume, solve


class QuadraticModel:
    """Independent test model with Q=(x+y-A)^2+(y-B)^2.

    Only the minute-30 G/I samples carry these two residuals; physical SD
    factors cancel their declared weighting. No physiological ODE is involved.
    """

    def simulate(self, theta, solver="fit"):
        values = np.zeros((241, 3))
        values[0, :2] = [500, 1000]  # Excluded exact-conditioning samples.
        values[30, :2] = [5 * (theta[0] + theta[1]), 10 * theta[1]]
        values[:, 2] = np.linspace(1, 2, 241) * 30 / theta[3]
        return {"observations": values, "times": np.arange(241), "status": "completed"}


def quadratic_observations(a=2.1, b=0.8):
    values = np.zeros((241, 3))
    values[30, :2] = [5 * a, 10 * b]
    values[:, 2] = np.linspace(1, 2, 241) * 30
    return {
        "times": list(range(241)),
        "datasets": {name: values.tolist() for name in ("noiseless", "noise_117", "noise_221")},
    }


def run(protocol=None):
    """Check the conditional minimum against separate scalar and closed forms."""
    if protocol is None:
        protocol = json.loads(Path(__file__).with_name("protocol.json").read_text())
    values = {
        "analytic_volume_objective_error": 0.0,
        "quadratic_profile_objective_error": 0.0,
        "quadratic_profile_parameter_error": 0.0,
    }
    volume_cases = []
    # Interior, lower and upper active-bound solutions. The scalar solver uses
    # V directly and never evaluates the reciprocal-coordinate closed form.
    q = np.asarray([2.0, 3.0, 7.0, 11.0])
    for ratio in (0.2, 0.9, 1.25, 3.0):
        observed = ratio * q + np.asarray([0.1, -0.1, 0.05, -0.02])
        volume = project_volume(q, observed)

        def objective(v):
            return float(sum((float(qi) / v - float(yi)) ** 2 for qi, yi in zip(q, observed)))

        numerical = minimize_scalar(
            objective, method="bounded", bounds=(0.5, 1.5), options={"xatol": 1e-14}
        )
        if not numerical.success:
            raise RuntimeError("Independent scalar volume minimizer failed")
        scalar_candidates = [0.5, float(numerical.x), 1.5]
        independent_volume = min(scalar_candidates, key=objective)
        error = abs(objective(volume) - objective(independent_volume))
        values["analytic_volume_objective_error"] = max(
            values["analytic_volume_objective_error"], error
        )
        # Bound cases have exact independently known solutions, not a claim
        # about SciPy's finite-distance approximation to an endpoint.
        expected_bound = 1.5 if ratio == 0.2 else (0.5 if ratio == 3 else None)
        if expected_bound is not None and volume != expected_bound:
            raise RuntimeError("Incorrect active volume bound")
        volume_cases.append(
            {
                "ratio": ratio,
                "projected_volume": volume,
                "independent_volume": independent_volume,
                "objective_error": error,
                "expected_bound": expected_bound,
            }
        )

    problem = Problem(
        QuadraticModel(), quadratic_observations(), protocol["designs"]["GI"], protocol
    )
    unrestricted = solve(problem, [0.7, 1.25, 0.8, 0.8])
    if unrestricted["status"] != "completed":
        raise RuntimeError("Independent quadratic unrestricted fit did not complete")
    values["quadratic_profile_objective_error"] = unrestricted["objective"]
    values["quadratic_profile_parameter_error"] = max(
        abs(unrestricted["evaluated_parameters"][0] - 1.3),
        abs(unrestricted["evaluated_parameters"][1] - 0.8),
    )
    profile_cases = []
    for target in protocol["profiles"]["coarse_grid"]:
        fit = solve(problem, [1.3, 0.8, 1, 1], interest=(0, target))
        if fit["status"] != "completed":
            raise RuntimeError("Independent quadratic profile did not complete")
        expected_y = (2.9 - target) / 2
        expected_objective = (target - 1.3) ** 2 / 2
        objective_error = abs(fit["objective"] - expected_objective)
        parameter_error = abs(fit["evaluated_parameters"][1] - expected_y)
        values["quadratic_profile_objective_error"] = max(
            values["quadratic_profile_objective_error"], objective_error
        )
        values["quadratic_profile_parameter_error"] = max(
            values["quadratic_profile_parameter_error"], parameter_error
        )
        slice_objective = problem.evaluate([target, 0.8, 1, 1])["objective"]
        # These grid points exclude the unique optimum x=1.3: the slice must be
        # strictly higher because its nuisance coordinate is held at y=0.8.
        if not fit["objective"] < slice_objective:
            raise RuntimeError("A nuisance profile was replaced by a fixed-nuisance slice")
        profile_cases.append(
            {
                "target": target,
                "expected_nuisance": expected_y,
                "expected_objective": expected_objective,
                "fit": fit,
                "slice_objective": slice_objective,
            }
        )
    checks = {
        name: {
            "value": float(value),
            "limit": protocol["criteria"][name],
            "passed": bool(value <= protocol["criteria"][name]),
        }
        for name, value in values.items()
    }
    return {
        "passed": all(record["passed"] for record in checks.values()),
        "checks": checks,
        "details": {
            "volume_cases": volume_cases,
            "quadratic_unrestricted": unrestricted,
            "quadratic_profiles": profile_cases,
            "quadratic_equation": "Q=(x+y-2.1)^2+(y-0.8)^2; y*(x)=(2.9-x)/2",
        },
    }
