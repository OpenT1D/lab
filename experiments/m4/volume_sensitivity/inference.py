"""Volume misspecification and recovery, with unchanged BC-011 observations."""

import numpy as np
from scipy.optimize import least_squares

from experiments.m4.joint_identifiability.inference import jacobian, observations

from .common import (
    NAMES,
    VOLUME,
    active_parameters,
    declared_parameters,
    fixed_parameters,
    unobservable,
)


def generate(model):
    # Returned artifact is exactly the original generator's schema and data.
    return observations(model.base, model.parent)


def sensitivities(model):
    p, parent = model.protocol, model.parent
    lower, upper = np.log(p["model"]["lower"]), np.log(p["model"]["upper"])
    sd = np.asarray(p["observation"]["synthetic_sd"])
    full, checks = {}, {}
    for anchor in (0.8, 1.0, 1.2):
        point = np.log([1, 1, 1, anchor])
        calculations = {}
        for solver in ("fit", "reference"):

            def function(x):
                return (model.simulate(np.exp(x), solver=solver)["observations"] / sd).ravel()

            for h in parent["inference"]["sensitivity_log_steps"]:
                calculations[f"{solver}-{h}"] = jacobian(function, point, h, lower, upper)
        ref = calculations["reference-0.001"]
        denominator = max(float(np.linalg.norm(ref)), 1e-12)
        checks[str(anchor)] = {
            "jacobian_relative_refinement_error": float(
                np.linalg.norm(ref - calculations["reference-0.002"]) / denominator
            ),
            "jacobian_solver_relative_error": float(
                np.linalg.norm(ref - calculations["fit-0.001"]) / denominator
            ),
        }
        full[str(anchor)] = {k: v.tolist() for k, v in calculations.items()}
    records = []
    for regime in p["inference"]["regimes"]:
        for arm in (*p["inference"]["volume_arms"], "control"):
            for step in p["observation"]["sample_steps_min"]:
                modality = "GI" if arm == "control" else "GIC"
                spec = {"regime": regime, "arm": arm, "step": step, "modality": modality}
                anchor = str(VOLUME.get(arm, 1.0))
                rows = [
                    t * 3 + c
                    for t in range(0, 241, step)
                    for c in p["observation"]["modalities"][modality]
                ]
                declared = declared_parameters(spec)
                matrix = np.asarray(full[anchor]["reference-0.001"])[np.ix_(rows, declared)].copy()
                leakage = {}
                for j in unobservable(spec):
                    column = declared.index(j)
                    leakage[NAMES[j]] = float(np.max(np.abs(matrix[:, column])))
                    matrix[:, column] = 0
                u, singular, vt = np.linalg.svd(matrix, full_matrices=False)
                rank = int(
                    np.count_nonzero(
                        singular > parent["inference"]["svd_relative_cutoff"] * singular[0]
                    )
                )
                records.append(
                    {
                        **spec,
                        "anchor": anchor,
                        "declared_parameters": declared,
                        "active_parameters": active_parameters(spec),
                        "unobservable": [NAMES[j] for j in unobservable(spec)],
                        "jacobian": matrix.tolist(),
                        "left_vectors": u.tolist(),
                        "right_vectors": vt.tolist(),
                        "singular_values": singular.tolist(),
                        "rank": rank,
                        "condition_number": float(singular[0] / singular[-1])
                        if rank == len(declared)
                        else None,
                        "numerical_leakage": leakage,
                    }
                )
    return {
        "full_weighted_log_jacobians": full,
        "checks": checks,
        "records": records,
        "passed": all(v <= p["criteria"][k] for item in checks.values() for k, v in item.items()),
    }


def fit_case(model, spec, data, checkpoint=None):
    p, parent = model.protocol, model.parent
    rows = list(range(0, 241, spec["step"]))
    columns = p["observation"]["modalities"][spec["modality"]]
    observed = np.asarray(data["datasets"][spec["data"]])[np.ix_(rows, columns)]
    active, fixed = active_parameters(spec), fixed_parameters(spec)
    lower, upper = np.log(p["model"]["lower"])[active], np.log(p["model"]["upper"])[active]
    sd = np.asarray(p["observation"]["synthetic_sd"])[columns]
    options, records = parent["inference"]["optimizer"], []
    for start in p["inference"]["starts"]:
        cache = {}

        def effective(x):
            theta = np.ones(4)
            theta[active] = np.exp(x)
            for name, value in fixed.items():
                theta[NAMES.index(name)] = value
            return theta

        def prediction(x):
            key = tuple(float(v) for v in x)
            if key not in cache:
                output = model.simulate(effective(x))
                cache[key] = output["observations"][np.ix_(rows, columns)]
            return cache[key]

        def residual(x):
            return ((prediction(x) - observed) / sd).ravel()

        record = {"start": start, "active_parameters": active}
        try:
            solution = least_squares(
                residual,
                np.log(start)[active],
                bounds=(lower, upper),
                jac=lambda x: jacobian(residual, x, options["log_step"], lower, upper),
                **{k: options[k] for k in ("method", "max_nfev", "ftol", "xtol", "gtol")},
            )
            estimates = [None] * 4
            for j, value in zip(active, np.exp(solution.x)):
                estimates[j] = float(value)
            final_residuals = residual(solution.x).reshape(len(rows), len(columns))
            record.update(
                status="completed" if solution.success else "optimizer_failed",
                optimizer_status=int(solution.status),
                message=solution.message,
                estimates=estimates,
                evaluated_parameters=effective(solution.x).tolist(),
                prediction=prediction(solution.x).tolist(),
                residuals=final_residuals.ravel().tolist(),
                objective=float(2 * solution.cost),
                channel_objectives=np.sum(final_residuals**2, axis=0).tolist(),
                nfev=int(solution.nfev),
                forward_evaluations=len(cache),
                optimality=float(solution.optimality),
                bound_hits=[
                    int(j)
                    for j, x, lo, hi in zip(active, solution.x, lower, upper)
                    if min(x - lo, hi - x) <= 1e-4
                ],
            )
        except Exception as exc:
            record.update(
                status="model_failed",
                error={"type": type(exc).__name__, "message": str(exc)},
                forward_evaluations=len(cache),
            )
        records.append(record)
        if checkpoint:
            checkpoint(records)
    return {
        **spec,
        "times": rows,
        "columns": columns,
        "observed": observed.tolist(),
        "active_parameters": active,
        "unobservable": [NAMES[j] for j in unobservable(spec)],
        "fixed_parameters": fixed,
        "fits": records,
    }
