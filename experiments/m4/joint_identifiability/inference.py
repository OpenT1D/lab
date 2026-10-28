"""Conditional weighted local sensitivity and bounded synthetic recovery."""

import numpy as np
from scipy.optimize import least_squares

from .common import active_parameters


def jacobian(function, x, step, lower, upper):
    """Absolute coordinate steps; three-point differences remain inside bounds."""
    x = np.asarray(x, dtype=float)
    if step <= 0 or not np.isfinite(x).all():
        raise ValueError("Finite coordinates and positive derivative step required")
    columns = []
    for j in range(len(x)):
        delta = np.zeros_like(x)
        if x[j] - step >= lower[j] and x[j] + step <= upper[j]:
            delta[j] = step
            col = (function(x + delta) - function(x - delta)) / (2 * step)
        else:
            direction = 1 if upper[j] - x[j] >= x[j] - lower[j] else -1
            available = upper[j] - x[j] if direction == 1 else x[j] - lower[j]
            h = min(step, available / 2)
            if h <= 0:
                raise ValueError("Empty derivative interval")
            delta[j] = direction * h
            col = (-3 * function(x) + 4 * function(x + delta) - function(x + 2 * delta)) / (
                2 * direction * h
            )
        columns.append(col)
    result = np.column_stack(columns)
    if not np.isfinite(result).all():
        raise ValueError("Nonfinite sensitivity")
    return result


def observations(model, p):
    reference = model.simulate(p["model"]["truth"], solver="reference")
    values = np.asarray(reference["observations"])
    datasets = {"noiseless": values.tolist()}
    noise = {"noiseless": np.zeros_like(values).tolist()}
    for seed in p["observation"]["noise_seeds"]:
        draw = np.random.default_rng(seed).normal(size=values.shape)
        draw[0, :2] = 0  # Exact basal conditioning, shared by every modality.
        name = f"noise_{seed}"
        error = draw * p["observation"]["synthetic_sd"]
        datasets[name] = (values + error).tolist()
        noise[name] = error.tolist()
    return {
        "truth": p["model"]["truth"],
        "times": list(reference["times"]),
        "reference": values.tolist(),
        "datasets": datasets,
        "noise": noise,
        "initial": list(reference["initial"]),
        "baseline": reference["baseline"],
        "generator": "reference solver; invented observations, known exact basal G/I",
    }


def subset(p, spec, data):
    rows = list(range(0, p["model"]["horizon_min"] + 1, spec["step"]))
    columns = p["observation"]["modalities"][spec["modality"]]
    selected = np.asarray(data)[np.ix_(rows, columns)]
    return rows, columns, selected


def sensitivities(model, p):
    truth = np.log(p["model"]["truth"])
    lower, upper = np.log(p["model"]["lower"]), np.log(p["model"]["upper"])
    sd = np.asarray(p["observation"]["synthetic_sd"])
    calculations = {}
    for solver in ("fit", "reference"):

        def function(x):
            return (
                np.asarray(model.simulate(np.exp(x), solver=solver)["observations"]) / sd
            ).ravel()

        for h in p["inference"]["sensitivity_log_steps"]:
            calculations[f"{solver}-{h}"] = jacobian(function, truth, h, lower, upper)
    ref = calculations["reference-0.001"]
    denominator = max(float(np.linalg.norm(ref)), 1e-12)
    checks = {
        "jacobian_relative_refinement_error": float(
            np.linalg.norm(ref - calculations["reference-0.002"]) / denominator
        ),
        "jacobian_solver_relative_error": float(
            np.linalg.norm(ref - calculations["fit-0.001"]) / denominator
        ),
    }
    records = []
    for regime in p["inference"]["regimes"]:
        for modality, columns in p["observation"]["modalities"].items():
            for step in p["observation"]["sample_steps_min"]:
                spec = {"regime": regime, "modality": modality, "step": step}
                selected = [t * 3 + c for t in range(0, 241, step) for c in columns]
                declared = [0] if regime == "known_kinetics" else [0, 1, 2]
                matrix = ref[np.ix_(selected, declared)].copy()
                # Proven equation-level zero; numerical adaptive-solver leakage
                # is retained below and never interpreted as k3 information.
                leakage = 0.0
                if regime == "unknown_clearance" and modality != "GIC":
                    leakage = float(np.max(np.abs(matrix[:, 2])))
                    matrix[:, 2] = 0
                u, singular, vt = np.linalg.svd(matrix, full_matrices=False)
                cutoff = p["inference"]["svd_relative_cutoff"] * singular[0]
                rank = int(np.count_nonzero(singular > cutoff))
                records.append(
                    {
                        **spec,
                        "declared_parameters": declared,
                        "active_parameters": active_parameters(spec),
                        "jacobian": matrix.tolist(),
                        "singular_values": singular.tolist(),
                        "right_vectors": vt.tolist(),
                        "left_vectors": u.tolist(),
                        "rank": rank,
                        "condition_number": float(singular[0] / singular[-1])
                        if rank == len(declared)
                        else None,
                        "unobservable": ["k3_scale"]
                        if regime == "unknown_clearance" and modality != "GIC"
                        else [],
                        "k3_numerical_leakage_max": leakage,
                    }
                )
    return {
        "checks": checks,
        "passed": all(v <= p["criteria"][k] for k, v in checks.items()),
        "full_weighted_log_jacobians": {k: v.tolist() for k, v in calculations.items()},
        "records": records,
    }


def fit_case(model, p, spec, data, checkpoint=None):
    rows, columns, observed = subset(p, spec, data["datasets"][spec["data"]])
    active = active_parameters(spec)
    lower, upper = np.log(p["model"]["lower"])[active], np.log(p["model"]["upper"])[active]
    scales = np.asarray(p["observation"]["synthetic_sd"])[columns]
    options = p["inference"]["optimizer"]
    records = []
    for start in p["inference"]["starts"]:
        cache = {}

        def prediction(x):
            key = tuple(float(v) for v in x)
            if key not in cache:
                theta = np.ones(3)
                theta[active] = np.exp(x)
                output = model.simulate(theta)
                cache[key] = np.asarray(output["observations"])[np.ix_(rows, columns)]
            return cache[key]

        def residual(x):
            return ((prediction(x) - observed) / scales).ravel()

        record = {"start": start, "active_parameters": active}
        try:
            solution = least_squares(
                residual,
                np.log(start)[active],
                bounds=(lower, upper),
                jac=lambda x: jacobian(residual, x, options["log_step"], lower, upper),
                **{k: options[k] for k in ("method", "max_nfev", "ftol", "xtol", "gtol")},
            )
            estimates = [None, None, None]
            for j, value in zip(active, np.exp(solution.x)):
                estimates[j] = float(value)
            record.update(
                status="completed" if solution.success else "optimizer_failed",
                optimizer_status=int(solution.status),
                message=solution.message,
                estimates=estimates,
                prediction=prediction(solution.x).tolist(),
                residuals=residual(solution.x).tolist(),
                objective=float(2 * solution.cost),
                nfev=int(solution.nfev),
                model_calls=len(cache),
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
                model_calls=len(cache),
            )
        records.append(record)
        if checkpoint is not None:
            checkpoint(records)
    return {
        **spec,
        "times": rows,
        "columns": columns,
        "observed": observed.tolist(),
        "active_parameters": active,
        "unobservable": ["k3_scale"]
        if spec["regime"] == "unknown_clearance" and spec["modality"] != "GIC"
        else [],
        "fixed_parameters": {"m4_scale": 1, "k3_scale": 1}
        if spec["regime"] == "known_kinetics"
        else {},
        "fits": records,
    }
