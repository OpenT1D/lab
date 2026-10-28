"""Bounded nuisance fits with an exact conditional C-peptide volume minimum.

Forward physiology and absolute log-coordinate finite differences are reused
unchanged from BC-012 and BC-011. The objective omits the two exact basal
conditioning observations and never estimates or rescales measurement error.
"""

from collections import OrderedDict

import numpy as np
from scipy.optimize import least_squares

from experiments.m4.joint_identifiability.inference import jacobian


def real_array(value, name):
    """Reject coercions that could conceal invalid numerical inputs."""
    try:
        raw = np.asarray(value, dtype=object)
        if any(
            isinstance(item, (bool, np.bool_, str, bytes, complex, np.complexfloating))
            for item in raw.flat
        ):
            raise ValueError(f"{name} must contain finite real numbers")
        result = np.asarray(value, dtype=float)
    except (TypeError, OverflowError) as exc:
        raise ValueError(f"{name} must contain finite real numbers") from exc
    if not np.isfinite(result).all():
        raise ValueError(f"{name} must contain finite real numbers")
    return result


def project_volume(q, observed, lower=0.5, upper=1.5):
    """Minimize sum((q/V-observed)**2) over a positive bounded volume.

    The common Cp standard deviation cancels from this conditional minimizer.
    Inputs are unweighted Cp concentrations at volume one, including time zero.
    """
    q = real_array(q, "Unit-volume prediction")
    observed = real_array(observed, "Observed C-peptide")
    bounds = real_array([lower, upper], "Volume bounds")
    if q.ndim != 1 or not len(q) or q.shape != observed.shape or not 0 < bounds[0] < bounds[1]:
        raise ValueError("Equal nonempty vectors and ordered positive volume bounds required")
    denominator = float(np.dot(q, q))
    numerator = float(np.dot(q, observed))
    if not np.isfinite([denominator, numerator]).all() or denominator <= 0:
        raise ValueError("A finite positive unit-volume sum of squares is required")
    inverse_volume = np.clip(numerator / denominator, 1 / bounds[1], 1 / bounds[0])
    return float(1 / inverse_volume)


class Problem:
    """One frozen design/dataset/solver with detached exact prediction caching."""

    CACHE_SIZE = 4096

    def __init__(self, model, observations, design, protocol, solver="fit", data="noiseless"):
        self.model, self.protocol, self.design = model, protocol, design
        if solver not in ("fit", "reference"):
            raise ValueError("A declared fit or reference solver is required")
        if data not in protocol["observation"]["data_cases"]:
            raise ValueError("Unknown frozen data case")
        self.solver, self.data = solver, data
        self.names = list(protocol["model"]["parameter_names"])
        self.lower = real_array(protocol["model"]["lower"], "Lower bounds")
        self.upper = real_array(protocol["model"]["upper"], "Upper bounds")
        self.estimated = list(design["estimated"])
        self.fixed = {self.names.index(name): value for name, value in design["fixed"].items()}
        self.columns = list(design["columns"])
        self.selected_times = list(range(0, 241, protocol["observation"]["step_min"]))
        self.selected_indices = [
            t * 3 + column
            for t in self.selected_times
            for column in self.columns
            if t != 0 or column == 2
        ]
        self.selected_columns = [index % 3 for index in self.selected_indices]
        values = real_array(observations["datasets"][data], "Observations")
        times = real_array(observations["times"], "Observation times")
        if values.shape != (241, 3) or not np.array_equal(times, np.arange(241)):
            raise ValueError("Complete minute-grid observations on [0,240] are required")
        self.observed = values.ravel()[self.selected_indices].copy()
        sd = real_array(protocol["observation"]["synthetic_sd"], "Observation SD")
        if sd.shape != (3,) or np.any(sd <= 0):
            raise ValueError("Three strictly positive observation SDs are required")
        self.scales = sd[self.selected_columns]
        self.cp_positions = np.flatnonzero(np.asarray(self.selected_columns) == 2)
        self._cache = OrderedDict()
        self.forward_evaluations = 0

    def theta(self, value):
        value = real_array(value, "Parameter vector")
        if value.shape != (4,) or np.any(value < self.lower) or np.any(value > self.upper):
            raise ValueError("Four parameters within the frozen bounds are required")
        return value

    def canonical(self, value, interest=None):
        """Apply the declared fixed/unobservable values and optional profile target."""
        value = self.theta(value)
        result = np.ones(4)
        result[self.estimated] = value[self.estimated]
        for index, fixed in self.fixed.items():
            result[index] = fixed
        if interest is not None:
            index, target = interest
            if (
                isinstance(index, (bool, np.bool_))
                or not isinstance(index, (int, np.integer))
                or index not in self.estimated
            ):
                raise ValueError("The profile parameter must be an estimated coordinate")
            target = real_array([target], "Profile target")[0]
            if not self.lower[index] <= target <= self.upper[index]:
                raise ValueError("Profile target lies outside the frozen bounds")
            result[index] = target
        return self.theta(result)

    def evaluate(self, theta):
        """Evaluate exactly the supplied four coordinates; never project volume."""
        theta = self.theta(theta)
        key = tuple(float(item) for item in theta)
        if key in self._cache:
            self._cache.move_to_end(key)
            prediction = self._cache[key]
        else:
            self.forward_evaluations += 1
            output = self.model.simulate(theta, solver=self.solver)
            values = real_array(output["observations"], "Model predictions")
            times = real_array(output["times"], "Model times")
            if values.shape != (241, 3) or not np.array_equal(times, np.arange(241)):
                raise RuntimeError("Incomplete forward calculation")
            if output.get("status", "completed") != "completed":
                raise RuntimeError("Forward calculation did not complete")
            prediction = values.ravel()[self.selected_indices].copy()
            self._cache[key] = prediction
            if len(self._cache) > self.CACHE_SIZE:
                self._cache.popitem(last=False)
        residuals = (prediction - self.observed) / self.scales
        objective = float(np.dot(residuals, residuals))
        if not np.isfinite(objective):
            raise RuntimeError("Nonfinite weighted objective")
        return {
            "evaluated_parameters": theta.tolist(),
            "prediction": prediction.tolist(),
            "residuals": residuals.tolist(),
            "objective": objective,
            "bound_hits": [
                j
                for j in self.estimated
                if min(np.log(theta[j] / self.lower[j]), np.log(self.upper[j] / theta[j])) <= 1e-4
            ],
        }


def solve(problem, start, interest=None):
    """Fit the nuisance coordinates, retaining every failure and true final output."""
    # Invalid caller inputs are errors, not fabricated model/optimizer failures.
    start = problem.theta(start)
    base = problem.canonical(start, interest)
    interest_index = None if interest is None else int(interest[0])
    estimated = [j for j in problem.estimated if j != interest_index]
    projected = 3 in estimated and bool(len(problem.cp_positions))
    optimized = [j for j in estimated if not (j == 3 and projected)]
    lower, upper = np.log(problem.lower[optimized]), np.log(problem.upper[optimized])
    options = problem.protocol["inference"]["optimizer"]
    before = problem.forward_evaluations
    record = {
        "start": start.tolist(),
        "interest": None
        if interest is None
        else {"parameter": interest_index, "value": float(interest[1])},
        "estimated_parameters": estimated,
        "optimized_parameters": optimized,
        "projected_volume": projected,
    }
    cache = {}

    def evaluate(x):
        key = tuple(float(value) for value in x)
        if key not in cache:
            theta = base.copy()
            theta[optimized] = np.exp(x)
            if projected:
                theta[3] = 1
                unit = problem.evaluate(theta)
                q = np.asarray(unit["prediction"])[problem.cp_positions]
                theta[3] = project_volume(
                    q,
                    problem.observed[problem.cp_positions],
                    problem.lower[3],
                    problem.upper[3],
                )
            cache[key] = problem.evaluate(theta)
        return cache[key]

    def residual(x):
        return np.asarray(evaluate(x)["residuals"])

    try:
        if not optimized:
            # Supports analytic-only conditional checks without inventing an
            # optimizer invocation or asking SciPy to fit an empty vector.
            final = evaluate(np.empty(0))
            status, optimizer_status, message = "completed", None, "No numerical coordinates"
            nfev, optimality = 0, 0.0
        else:
            solution = least_squares(
                residual,
                np.log(base[optimized]),
                bounds=(lower, upper),
                jac=lambda x: jacobian(residual, x, options["log_step"], lower, upper),
                **{key: options[key] for key in ("method", "max_nfev", "ftol", "xtol", "gtol")},
            )
            final = evaluate(solution.x)
            status = "completed" if solution.success else "optimizer_failed"
            optimizer_status, message = int(solution.status), str(solution.message)
            nfev, optimality = int(solution.nfev), float(solution.optimality)
        estimates = [None] * 4
        for j in estimated:
            estimates[j] = final["evaluated_parameters"][j]
        record.update(
            final,
            status=status,
            optimizer_status=optimizer_status,
            message=message,
            estimates=estimates,
            nfev=nfev,
            optimality=optimality,
        )
    except Exception as exc:
        record.update(
            status="model_failed",
            optimizer_status=None,
            message=str(exc),
            error={"type": type(exc).__name__, "message": str(exc)},
        )
    record["forward_evaluations"] = problem.forward_evaluations - before
    return record
