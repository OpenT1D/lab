"""Reconstruct bounded profile objectives without a numerical runtime.

All contour geometry is reconstructed from recorded residuals. Regions describe
sampled evidence within engineering bounds, not finite-sample confidence sets.
"""

import argparse
import math
from pathlib import Path

from experiments.m4.joint_identifiability import common as joint_common
from experiments.m4.joint_identifiability.report import close, matrix, number
from experiments.m4.volume_sensitivity import common as volume_common
from experiments.m4.volume_sensitivity import report as volume_report

from .common import (
    NAMES,
    VERSION,
    digest,
    dump,
    numerical_files,
    read,
    required_files,
    specifications,
    validate,
    verify_files,
)


def selected_rows(p, spec):
    return [
        t * 3 + c
        for t in range(0, 241, p["observation"]["step_min"])
        for c in p["designs"][spec["design"]]["columns"]
        if t != 0 or c == 2
    ]


def profile_starts(p, spec, best, interest):
    """Independent reconstruction of the deterministic non-warm-start rule."""
    nuisance = [j for j in p["designs"][spec["design"]]["estimated"] if j != interest]
    inherited = p["inference"]["unrestricted_starts"][:2]
    farthest = max(
        range(2),
        key=lambda i: sum(math.log(inherited[i][j] / best[j]) ** 2 for j in nuisance),
    )
    return [best, inherited[farthest]]


def bounds_hit(p, theta, declared):
    return [
        j
        for j in declared
        if min(
            math.log(theta[j] / p["model"]["lower"][j]),
            math.log(p["model"]["upper"][j] / theta[j]),
        )
        <= 1e-4
    ]


def assess_evaluation(p, spec, record, observed, sd, *, interest=None):
    theta = matrix([record["evaluated_parameters"]], 1, 4)[0]
    declared = p["designs"][spec["design"]]["estimated"]
    fixed = p["designs"][spec["design"]]["fixed"]
    for j, value in enumerate(theta):
        if not p["model"]["lower"][j] <= value <= p["model"]["upper"][j]:
            raise ValueError("Evaluated parameter outside frozen bounds")
        if j not in declared:
            close(value, fixed.get(NAMES[j], 1.0), 0)
    if interest is not None:
        close(theta[interest["parameter"]], interest["value"], 0)
    prediction = matrix([record["prediction"]], 1, len(observed))[0]
    residuals = matrix([record["residuals"]], 1, len(observed))[0]
    for pred, obs, scale, residual in zip(prediction, observed, sd, residuals):
        close(residual, (pred - obs) / scale)
    objective = sum(r * r for r in residuals)
    close(record["objective"], objective)
    if record["objective"] < 0:
        raise ValueError("Weighted squared objective cannot be negative")
    hits = bounds_hit(p, theta, declared)
    if record["bound_hits"] != hits:
        raise ValueError("Wrong parameter-bound accounting")
    return {
        "evaluated_parameters": theta,
        # Reconstruct the arithmetic above, but retain the recorded reduction
        # order for deterministic near-tie start selection and contour sides.
        "objective": number(record["objective"]),
        "residual_objective": objective,
        "bound_hits": hits,
    }


def assess_fit(p, spec, record, observed, sd, start, *, interest=None):
    declared = p["designs"][spec["design"]]["estimated"]
    nuisance = [j for j in declared if interest is None or j != interest["parameter"]]
    projected = 3 in nuisance
    optimized = [j for j in nuisance if not (j == 3 and projected)]
    if (
        record["start"] != start
        or record["interest"] != interest
        or record["estimated_parameters"] != nuisance
        or record["optimized_parameters"] != optimized
        or record["projected_volume"] is not projected
    ):
        raise ValueError("Changed start, target, nuisance or projected dimensions")
    status = record["status"]
    if status == "model_failed":
        error = record.get("error")
        if (
            not isinstance(error, dict)
            or not isinstance(error.get("type"), str)
            or not isinstance(error.get("message"), str)
        ):
            raise ValueError("Model failure must retain its error")
        if any(k in record for k in ("estimates", "objective", "prediction", "residuals")):
            raise ValueError("Failed model cannot fabricate numerical evidence")
        return {"status": status, "error": error}
    if status not in ("completed", "optimizer_failed"):
        raise ValueError("Unknown optimizer status")
    code = record["optimizer_status"]
    if (
        type(code) is not int
        or code not in (0, 1, 2, 3, 4)
        or (code > 0) != (status == "completed")
    ):
        raise ValueError("Optimizer status contradicts termination code")
    if not isinstance(record["message"], str):
        raise ValueError("Missing optimizer termination message")
    checked = assess_evaluation(p, spec, record, observed, sd, interest=interest)
    estimates = record["estimates"]
    if len(estimates) != 4:
        raise ValueError("Incomplete estimates")
    for j, value in enumerate(estimates):
        if j in nuisance:
            close(value, checked["evaluated_parameters"][j], 0)
        elif value is not None:
            raise ValueError("Fixed, absent and interest coordinates are not nuisance estimates")
    if projected:
        # Reconstruct q at V=1 from recorded predictions. This independently
        # checks the conditional minimum, including clipping at both bounds.
        rows = selected_rows(p, spec)
        volume = checked["evaluated_parameters"][3]
        cp = [i for i, row in enumerate(rows) if row % 3 == 2]
        q = [record["prediction"][i] * volume / sd[i] for i in cp]
        y = [observed[i] / sd[i] for i in cp]
        denominator = sum(v * v for v in q)
        if denominator <= 0:
            raise ValueError("Undefined volume projection")
        inverse = min(
            1 / p["model"]["lower"][3],
            max(1 / p["model"]["upper"][3], sum(a * b for a, b in zip(q, y)) / denominator),
        )
        close(volume, 1 / inverse, 1e-8)
    for key in ("nfev", "forward_evaluations"):
        if type(record[key]) is not int or record[key] < (1 if key == "nfev" else 0):
            raise ValueError("Incomplete optimizer evaluation accounting")
    if number(record["optimality"]) < 0:
        raise ValueError("Negative optimizer optimality")
    return {
        **checked,
        "status": status,
        "estimates": estimates,
        "projected_volume": projected,
        "estimated_parameters": nuisance,
        "optimized_parameters": optimized,
        "nfev": record["nfev"],
        "forward_evaluations": record["forward_evaluations"],
    }


def assess_fits(p, spec, fits, observed, sd, starts, *, interest=None):
    if len(fits) != len(starts):
        raise ValueError("Lost or added optimizer start")
    checked = [
        assess_fit(p, spec, record, observed, sd, start, interest=interest)
        for start, record in zip(starts, fits)
    ]
    completed = [r for r in checked if r["status"] == "completed"]
    best = min(completed, key=lambda r: r["objective"]) if completed else None
    return checked, best


def contour_side(delta, cutoff):
    return number(delta) <= cutoff


def components(values, deltas, cutoff):
    """Number of sampled inside runs; unsampled components remain possible."""
    inside = [contour_side(deltas[v], cutoff) for v in values]
    return sum(value and (i == 0 or not inside[i - 1]) for i, value in enumerate(inside))


def assess_crossings(p, initial_values, points, crossings):
    """Audit every bracket and midpoint from the predeclared sampling grid."""
    cutoff = p["profiles"]["cutoff"]
    deltas = {v: point["delta_q"] for v, point in points.items()}
    expected = [
        [a, b]
        for a, b in zip(initial_values, initial_values[1:])
        if contour_side(deltas[a], cutoff) != contour_side(deltas[b], cutoff)
    ]
    if [r["initial_bracket"] for r in crossings] != expected:
        raise ValueError("Missing, duplicate or unplanned contour crossing")
    used, output = set(initial_values), []
    for crossing, initial in zip(crossings, expected):
        bracket = initial[:]
        history = crossing["history"]
        if len(history) > 12:
            raise ValueError("Too many contour bisections")
        for event in history:
            if bracket[1] - bracket[0] <= p["criteria"]["crossing_max_width"]:
                raise ValueError("Unplanned bisection after convergence")
            midpoint = sum(bracket) / 2
            if event["bracket"] != bracket or event["midpoint"] != midpoint:
                raise ValueError("Changed contour bisection history")
            if midpoint not in points:
                raise ValueError("Missing contour midpoint evidence")
            if points[midpoint]["stage"] != "crossing_refinement":
                raise ValueError("Wrong midpoint provenance")
            used.add(midpoint)
            if contour_side(deltas[bracket[0]], cutoff) == contour_side(deltas[midpoint], cutoff):
                bracket[0] = midpoint
            else:
                bracket[1] = midpoint
        if crossing["bracket"] != bracket:
            raise ValueError("Final contour bracket does not follow history")
        if bracket[1] - bracket[0] > p["criteria"]["crossing_max_width"]:
            raise ValueError("Unresolved contour crossing")
        output.append({"initial_bracket": initial, "bracket": bracket, "history": history})
    if used != set(points):
        raise ValueError("Missing or unplanned profile point")
    return output


def sampled_regions(points, crossings, cutoff):
    """Return bracketing endpoint evidence rather than interpolated intervals."""
    values = sorted(points)
    side = contour_side(points[values[0]]["delta_q"], cutoff)
    lower = {"value": values[0], "kind": "bound_limited"} if side else None
    result = []
    for crossing in crossings:
        endpoint = {"bracket": crossing["bracket"], "kind": "contour_bracket"}
        if side:
            result.append(
                {
                    "lower": lower,
                    "upper": endpoint,
                    "closed_within_bounds": lower["kind"] != "bound_limited",
                }
            )
        else:
            lower = endpoint
        side = not side
    if side:
        result.append(
            {
                "lower": lower,
                "upper": {"value": values[-1], "kind": "bound_limited"},
                "closed_within_bounds": False,
            }
        )
    return result


def assess_profile(p, spec, record, observed, sd, baseline):
    j = record["parameter"]
    if type(j) is not int or j not in p["designs"][spec["design"]]["profiled"]:
        raise ValueError("Unplanned profile target")
    best = baseline["fit_best"]
    reference = baseline["reference_best"]
    if best is None or reference is None:
        raise ValueError("Profiles require completed unrestricted minima")
    theta = best["evaluated_parameters"]
    coarse = sorted(set(p["profiles"]["coarse_grid"] + [theta[j]]))
    initial = sorted(set(coarse + p["profiles"]["refinement_grid"]))
    if record["coarse_values"] != coarse or record["initial_values"] != initial:
        raise ValueError("Changed planned profile grids or missing unrestricted estimate")
    points = {}
    starts = profile_starts(p, spec, theta, j)
    for point in record["points"]:
        value = number(point["value"])
        if value in points or not p["model"]["lower"][j] <= value <= p["model"]["upper"][j]:
            raise ValueError("Duplicate or out-of-bounds profile target")
        expected_stage = (
            "coarse"
            if value in p["profiles"]["coarse_grid"]
            else "grid_refinement"
            if value in p["profiles"]["refinement_grid"]
            else "estimate"
            if value == theta[j]
            else "crossing_refinement"
        )
        if point["stage"] != expected_stage:
            raise ValueError("Wrong profile point provenance")
        interest = {"parameter": j, "value": value}
        fits, selected = assess_fits(
            p, spec, point["fits"], observed, sd, starts, interest=interest
        )
        if selected is None:
            raise ValueError("Profile point has no completed start")
        sliced = assess_evaluation(p, spec, point["slice"], observed, sd, interest=interest)
        for k in range(4):
            close(sliced["evaluated_parameters"][k], value if j == k else theta[k], 0)
        points[value] = {
            "value": value,
            "stage": point["stage"],
            "fits": fits,
            "best": selected,
            "objective": selected["objective"],
            "delta_q": selected["objective"] - best["objective"],
            "slice_objective": sliced["objective"],
            "slice_delta_q": sliced["objective"] - best["objective"],
            "nuisance_bound_hits": [k for k in selected["bound_hits"] if k != j],
        }
    if list(points) != sorted(points) or not set(initial) <= set(points):
        raise ValueError("Missing or unsorted planned profile points")
    crossings = assess_crossings(p, initial, points, record["crossings"])
    wanted = {p["model"]["lower"][j], p["model"]["upper"][j]}
    wanted.update(v for crossing in crossings for v in crossing["bracket"])
    if [r["value"] for r in record["reference_checks"]] != sorted(wanted):
        raise ValueError("Reference checks omit bounds or final crossing endpoints")
    checks = []
    for check in record["reference_checks"]:
        value = check["value"]
        interest = {"parameter": j, "value": value}
        fits, selected = assess_fits(
            p, spec, check["fits"], observed, sd, starts, interest=interest
        )
        if selected is None:
            raise ValueError("Reference profile has no completed start")
        direct = assess_evaluation(p, spec, check["at_fit_best"], observed, sd, interest=interest)
        if direct["evaluated_parameters"] != points[value]["best"]["evaluated_parameters"]:
            raise ValueError("Reference direct evaluation changed the fit-solver vector")
        delta = selected["objective"] - reference["objective"]
        checked = {
            "value": value,
            "fits": fits,
            "best": selected,
            "delta_q": delta,
            "objective_error": abs(selected["objective"] - points[value]["objective"]),
            "at_fit_best_error": abs(direct["objective"] - points[value]["objective"]),
            "at_fit_best_objective": direct["objective"],
            "delta_q_error": abs(delta - points[value]["delta_q"]),
            "contour_side_matches": contour_side(delta, p["profiles"]["cutoff"])
            == contour_side(points[value]["delta_q"], p["profiles"]["cutoff"]),
        }
        checks.append(checked)
    deltas = {v: point["delta_q"] for v, point in points.items()}
    gates = {
        "all_fits_completed": all(
            f["status"] == "completed" for r in [*points.values(), *checks] for f in r["fits"]
        ),
        "not_below_unrestricted_minimum": min([*deltas.values(), *(r["delta_q"] for r in checks)])
        >= -p["criteria"]["profile_below_baseline_tolerance"],
        "not_above_feasible_slice": all(
            r["objective"] - r["slice_objective"] <= p["criteria"]["profile_above_slice_tolerance"]
            for r in points.values()
        ),
        "reference_objective_agreement": all(
            r[name] <= p["criteria"]["objective_absolute_tolerance"]
            for r in checks
            for name in ("objective_error", "at_fit_best_error", "delta_q_error")
        ),
        "reference_contour_side_agreement": all(r["contour_side_matches"] for r in checks),
        "reference_not_above_feasible_candidate": all(
            r["best"]["objective"] - r["at_fit_best_objective"]
            <= p["criteria"]["profile_above_slice_tolerance"]
            for r in checks
        ),
    }
    return {
        "parameter": j,
        "name": NAMES[j],
        "points": list(points.values()),
        "crossings": crossings,
        "sampled_regions": sampled_regions(points, crossings, p["profiles"]["cutoff"]),
        "sampled_topology": {
            "coarse_components": components(coarse, deltas, p["profiles"]["cutoff"]),
            "fine_components": components(initial, deltas, p["profiles"]["cutoff"]),
            "final_components": components(sorted(points), deltas, p["profiles"]["cutoff"]),
            "untested_components_not_excluded": True,
        },
        "reference_checks": checks,
        "gates": gates,
        "passed": all(gates.values()),
    }


def assess_case(p, volume, spec, case, observations):
    if any(case.get(k) != v for k, v in spec.items()):
        raise ValueError("Case identity mismatch")
    if case.get("status", "completed") != "completed":
        raise ValueError("Incomplete/failed case; inspect retained checkpoint evidence")
    rows = selected_rows(p, spec)
    observed = [observations["datasets"][spec["data"]][r // 3][r % 3] for r in rows]
    sd = [p["observation"]["synthetic_sd"][r % 3] for r in rows]
    if case["selection"] != rows or case["observed"] != observed or case["sd"] != sd:
        raise ValueError("Changed shared observations, exclusions or fixed error scales")
    baseline = {}
    for solver in ("fit", "reference"):
        baseline[solver], baseline[solver + "_best"] = assess_fits(
            p, spec, case["baseline"][solver], observed, sd, p["inference"]["unrestricted_starts"]
        )
    comparator = case["baseline"]["parent_unprojected"]
    baseline["parent_unprojected"] = None
    comparator_difference = None
    if spec["design"] == "free_volume":
        parent_spec = {
            "id": f"estimated_rates-estimated-30-{spec['data']}",
            "regime": "estimated_rates",
            "arm": "estimated",
            "step": 30,
            "data": spec["data"],
            "modality": "GIC",
        }
        if comparator is None:
            raise ValueError("Missing independent unprojected comparator")
        checked = volume_report.assess_case(volume, parent_spec, comparator, observations)
        baseline["parent_unprojected"] = checked
        if checked["best"] is not None and baseline["fit_best"] is not None:
            comparator_difference = abs(
                checked["best"]["objective"] - baseline["fit_best"]["objective"]
            )
    elif comparator is not None:
        raise ValueError("Unplanned parent comparator")
    baseline["comparator_objective_difference"] = comparator_difference
    targets = p["designs"][spec["design"]]["profiled"]
    if [r["parameter"] for r in case["profiles"]] != targets:
        raise ValueError("Missing or unplanned profile target")
    profiles = [assess_profile(p, spec, r, observed, sd, baseline) for r in case["profiles"]]
    baseline_complete = all(
        f["status"] == "completed" for key in ("fit", "reference") for f in baseline[key]
    )
    comparator_complete = comparator is None or all(
        f["status"] == "completed" for f in baseline["parent_unprojected"]["fits"]
    )
    eligible = spec["data"] == "noiseless"
    recovered = (
        all(
            f["status"] == "completed"
            and all(
                abs(f["evaluated_parameters"][j] / p["model"]["truth"][j] - 1)
                <= p["criteria"]["noiseless_parameter_relative_error"]
                for j in p["designs"][spec["design"]]["estimated"]
            )
            for key in ("fit", "reference")
            for f in baseline[key]
        )
        if eligible
        else None
    )
    baseline_error = (
        abs(baseline["fit_best"]["objective"] - baseline["reference_best"]["objective"])
        if baseline["fit_best"] is not None and baseline["reference_best"] is not None
        else None
    )
    gates = {
        "all_fits_completed": baseline_complete
        and comparator_complete
        and all(r["gates"]["all_fits_completed"] for r in profiles),
        "noiseless_baseline_recovery": recovered if eligible else True,
        "baseline_reference_agreement": baseline_error is not None
        and baseline_error <= p["criteria"]["objective_absolute_tolerance"],
        "parent_comparator_agreement": comparator is None
        or (
            comparator_difference is not None
            and comparator_difference <= p["criteria"]["objective_absolute_tolerance"]
        ),
        "profiles": all(r["passed"] for r in profiles),
    }
    return {
        **spec,
        "baseline": baseline,
        "baseline_reference_objective_error": baseline_error,
        "noiseless_recovery_eligible": eligible,
        "noiseless_recovered": recovered,
        "profiles": profiles,
        "gates": gates,
        "passed": all(gates.values()),
    }


def assess_forward(p, volume, joint, evidence):
    parent_passed = volume_report.assess_forward(volume, joint, evidence["parent"])
    oracles = evidence["profile_oracles"]
    names = {
        "analytic_volume_objective_error",
        "quadratic_profile_objective_error",
        "quadratic_profile_parameter_error",
    }
    if set(oracles["checks"]) != names:
        raise ValueError("Missing independent profile oracle")
    states = []
    for name in names:
        check = oracles["checks"][name]
        close(check["limit"], p["criteria"][name], 0)
        value = number(check["value"])
        if value < 0:
            raise ValueError("Negative absolute oracle error")
        passed = value <= check["limit"]
        if check["passed"] is not passed:
            raise ValueError("False profile oracle status")
        states.append(passed)
    if oracles["passed"] is not all(states):
        raise ValueError("False aggregate oracle status")
    return parent_passed and all(states)


def reconstruct(directory, *, allow_pending=False):
    directory = Path(directory)
    p = read(directory / "protocol.json")
    volume, joint = read(directory / "parent-volume.json"), read(directory / "parent-joint.json")
    validate(p)
    volume_common.validate(volume)
    joint_common.validate(joint)
    if p["parent_protocol"] != volume["id"] or volume["parent_protocol"] != joint["id"]:
        raise ValueError("Wrong model ancestry")
    manifest = read(directory / "manifest.json")
    states = {"completed", "calculated"} if allow_pending else {"completed"}
    if manifest.get("schema") != VERSION or manifest.get("status") not in states:
        raise ValueError("Incomplete/failed experiment; inspect retained evidence")
    verify_files(directory, manifest, required_files(p))
    differences = sum(
        digest(directory / name) != digest(directory / "repeat" / name)
        for name in numerical_files(p)
    )
    observations, verification = (
        read(directory / "observations.json"),
        read(directory / "verification.json"),
    )
    volume_report.assess_observations(volume, joint, observations)
    cases = [
        assess_case(
            p, volume, spec, read(directory / "cases" / (spec["id"] + ".json")), observations
        )
        for spec in specifications(p)
    ]
    gates = {
        "forward_and_oracle_verification": assess_forward(p, volume, joint, verification),
        "fresh_process_repeat": differences == p["criteria"]["repeat_artifact_differences"],
        "all_fits_completed": all(c["gates"]["all_fits_completed"] for c in cases),
        "noiseless_baseline_recovery": all(
            c["gates"]["noiseless_baseline_recovery"] for c in cases
        ),
        "baseline_reference_agreement": all(
            c["gates"]["baseline_reference_agreement"] for c in cases
        ),
        "parent_comparator_agreement": all(
            c["gates"]["parent_comparator_agreement"] for c in cases
        ),
        "profile_checks": all(c["gates"]["profiles"] for c in cases),
    }
    starts = sum(
        sum(len(c["baseline"][key]) for key in ("fit", "reference"))
        + (
            len(c["baseline"]["parent_unprojected"]["fits"])
            if c["baseline"]["parent_unprojected"]
            else 0
        )
        + sum(
            len(record["fits"])
            for r in c["profiles"]
            for record in [*r["points"], *r["reference_checks"]]
        )
        for c in cases
    )
    return {
        "schema": VERSION,
        "protocol": p["id"],
        "claim": p["claim"],
        "passed": all(gates.values()),
        "gates": gates,
        "analyses": len(cases),
        "profiles": sum(len(c["profiles"]) for c in cases),
        "fit_starts": starts,
        "repeat_artifact_differences": differences,
        "verification": verification,
        "cases": cases,
        "limits": [p["profiles"]["cutoff_meaning"], p["profiles"]["bounds"], *p["excluded"]],
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("directory", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = reconstruct(args.directory)
    if args.output.exists() or args.output.resolve() == (args.directory / "report.json").resolve():
        raise ValueError("Choose a new reconstruction path")
    dump(args.output, result)
