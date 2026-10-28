"""Reconstruct residuals, recovery and SVD evidence without numerical libraries."""

import argparse
import math
from pathlib import Path

from .common import (
    VERSION,
    active_parameters,
    digest,
    dump,
    forward_check_specifications,
    numerical_files,
    read,
    required_files,
    specifications,
    validate,
    verify_files,
)


def number(x):
    if isinstance(x, bool) or not isinstance(x, (int, float)) or not math.isfinite(x):
        raise ValueError("Expected finite numeric evidence")
    return x


def matrix(x, rows, cols):
    if (
        not isinstance(x, list)
        or len(x) != rows
        or any(not isinstance(r, list) or len(r) != cols for r in x)
    ):
        raise ValueError("Incomplete observation or matrix shape")
    for row in x:
        for v in row:
            number(v)
    return x


def close(a, b, tolerance=1e-9):
    if abs(number(a) - number(b)) > tolerance * max(1, abs(a), abs(b)):
        raise ValueError("Inconsistent reconstructed arithmetic")


def svd_check(record, p):
    j = record["jacobian"]
    n, d = len(j), len(record["declared_parameters"])
    matrix(j, n, d)
    u, vt = matrix(record["left_vectors"], n, d), matrix(record["right_vectors"], d, d)
    singular = record["singular_values"]
    if (
        len(singular) != d
        or any(number(s) < 0 for s in singular)
        or any(b > a for a, b in zip(singular, singular[1:]))
    ):
        raise ValueError("Invalid singular values")
    for i in range(d):
        for k in range(d):
            close(sum(vt[i][index] * vt[k][index] for index in range(d)), float(i == k), 1e-8)
            close(sum(u[index][i] * u[index][k] for index in range(n)), float(i == k), 1e-8)
    for i in range(n):
        for k in range(d):
            close(
                sum(u[i][index] * singular[index] * vt[index][k] for index in range(d)),
                j[i][k],
                1e-8,
            )
    rank = sum(s > p["inference"]["svd_relative_cutoff"] * singular[0] for s in singular)
    if rank != record["rank"]:
        raise ValueError("Incorrect sensitivity rank")
    if rank == d:
        close(record["condition_number"], singular[0] / singular[-1])
    elif record["condition_number"] is not None:
        raise ValueError("Rank-deficient condition number must be null")
    return {k: v for k, v in record.items() if k not in ("jacobian", "left_vectors")}


def norm_difference(a, b):
    return math.sqrt(sum((x - y) ** 2 for ar, br in zip(a, b) for x, y in zip(ar, br)))


def assess_sensitivities(p, evidence):
    full = evidence["full_weighted_log_jacobians"]
    keys = {f"{s}-{h}" for s in ("fit", "reference") for h in (0.002, 0.001)}
    if set(full) != keys:
        raise ValueError("Incomplete derivative refinement evidence")
    for array in full.values():
        matrix(array, 723, 3)
    ref = full["reference-0.001"]
    denominator = max(math.sqrt(sum(v * v for row in ref for v in row)), 1e-12)
    checks = {
        "jacobian_relative_refinement_error": norm_difference(ref, full["reference-0.002"])
        / denominator,
        "jacobian_solver_relative_error": norm_difference(ref, full["fit-0.001"]) / denominator,
    }
    if set(evidence["checks"]) != set(checks):
        raise ValueError("Missing derivative convergence gate")
    for name, value in checks.items():
        close(value, evidence["checks"][name])
    result, seen = [], set()
    expected = {(s["regime"], s["modality"], s["step"]) for s in specifications(p)}
    for record in evidence["records"]:
        identity = (record["regime"], record["modality"], record["step"])
        if identity not in expected or identity in seen:
            raise ValueError("Wrong or duplicate sensitivity design")
        seen.add(identity)
        regime, modality, step = identity
        declared = [0] if regime == "known_kinetics" else [0, 1, 2]
        if record["declared_parameters"] != declared or record[
            "active_parameters"
        ] != active_parameters(record):
            raise ValueError("Wrong sensitivity parameter dimensions")
        unobservable = ["k3_scale"] if regime == "unknown_clearance" and modality != "GIC" else []
        if record["unobservable"] != unobservable:
            raise ValueError("Wrong sensitivity unobservable label")
        rows = [
            t * 3 + c for t in range(0, 241, step) for c in p["observation"]["modalities"][modality]
        ]

        def selected(array):
            return [
                [0.0 if unobservable and c == 2 else array[r][c] for c in declared] for r in rows
            ]

        predicted = selected(ref)
        matrix(record["jacobian"], len(rows), len(declared))
        for actual, wanted in zip(record["jacobian"], predicted):
            for a, b in zip(actual, wanted):
                close(a, b)
        leakage = max(abs(ref[r][2]) for r in rows) if unobservable else 0.0
        close(leakage, record["k3_numerical_leakage_max"])
        numeric_uncertainty = max(
            norm_difference(predicted, selected(full[k])) for k in ("reference-0.002", "fit-0.001")
        )
        checked = svd_check(record, p)
        # A discrepancy is a diagnostic estimate, not a rigorous total-error bound.
        checked["jacobian_refinement_discrepancy_norm"] = numeric_uncertainty
        checked["directions_above_numerical_discrepancy"] = sum(
            s
            > max(
                numeric_uncertainty,
                p["inference"]["svd_relative_cutoff"] * record["singular_values"][0],
            )
            for s in record["singular_values"]
        )
        checked["rank_resolved_under_checked_refinements"] = (
            checked["directions_above_numerical_discrepancy"] == checked["rank"]
        )
        result.append(checked)
    if seen != expected:
        raise ValueError("Incomplete sensitivity matrix")
    passed = all(v <= p["criteria"][k] for k, v in checks.items())
    if evidence["passed"] is not passed:
        raise ValueError("False sensitivity gate status")
    return result, checks, passed


def assess_forward(p, evidence):
    expected = forward_check_specifications(p)
    if set(evidence["checks"]) != set(expected):
        raise ValueError("Missing or unplanned forward numerical gate")
    states = []
    for name, limit in expected.items():
        check = evidence["checks"][name]
        close(check["limit"], limit, 0)
        value = number(check["value"])
        if value < 0:
            raise ValueError("Negative absolute numerical error")
        passed = value <= limit
        if check["passed"] is not passed:
            raise ValueError("False numerical gate status")
        states.append(passed)
    passed = all(states)
    if evidence["passed"] is not passed:
        raise ValueError("False forward verification status")
    return passed


def assess_case(p, spec, case, observations):
    if any(case.get(k) != v for k, v in spec.items()):
        raise ValueError("Case identity mismatch")
    active = active_parameters(spec)
    columns = p["observation"]["modalities"][spec["modality"]]
    times = list(range(0, 241, spec["step"]))
    expected = [[observations["datasets"][spec["data"]][t][c] for c in columns] for t in times]
    if (
        case.get("times") != times
        or case.get("columns") != columns
        or case.get("observed") != expected
    ):
        raise ValueError("Case did not use the common nested observations")
    if case["active_parameters"] != active or len(case["fits"]) != 2:
        raise ValueError("Missing parameter/start accounting")
    should_be_unobservable = (
        ["k3_scale"] if spec["regime"] == "unknown_clearance" and spec["modality"] != "GIC" else []
    )
    if case["unobservable"] != should_be_unobservable:
        raise ValueError("Incorrect unobservable-parameter label")
    fixed = {"m4_scale": 1, "k3_scale": 1} if spec["regime"] == "known_kinetics" else {}
    if case["fixed_parameters"] != fixed:
        raise ValueError("Wrong kinetic conditioning")
    results = []
    truth = p["model"]["truth"]
    for start, fit in zip(p["inference"]["starts"], case["fits"]):
        if fit["start"] != start or fit["active_parameters"] != active:
            raise ValueError("Changed start or fitted dimensions")
        if fit["status"] not in ("completed", "optimizer_failed"):
            results.append({"status": fit["status"], "error": fit.get("error")})
            continue
        code = fit["optimizer_status"]
        if (
            type(code) is not int
            or code not in (0, 1, 2, 3, 4)
            or (code > 0) != (fit["status"] == "completed")
        ):
            raise ValueError("Optimizer completion disagrees with termination code")
        predictions = matrix(fit["prediction"], len(times), len(columns))
        residuals = [
            (predictions[i][k] - expected[i][k]) / p["observation"]["synthetic_sd"][c]
            for i in range(len(times))
            for k, c in enumerate(columns)
        ]
        if len(fit["residuals"]) != len(residuals):
            raise ValueError("Incomplete residuals")
        for a, b in zip(residuals, fit["residuals"]):
            close(a, b)
        objective = sum(r * r for r in residuals)
        close(objective, fit["objective"])
        estimates = fit["estimates"]
        if len(estimates) != 3 or any(
            estimates[j] is not None for j in range(3) if j not in active
        ):
            raise ValueError("Unestimated parameter must not have a numerical estimate")
        errors = [None] * 3
        for j in active:
            value = number(estimates[j])
            if not p["model"]["lower"][j] <= value <= p["model"]["upper"][j]:
                raise ValueError("Estimate outside frozen bounds")
            errors[j] = abs(value - truth[j]) / truth[j]
        bound_hits = [
            j
            for j in active
            if min(
                math.log(estimates[j] / p["model"]["lower"][j]),
                math.log(p["model"]["upper"][j] / estimates[j]),
            )
            <= 1e-4
        ]
        if fit["bound_hits"] != bound_hits:
            raise ValueError("Wrong bound-hit accounting")
        results.append(
            {
                "status": fit["status"],
                "estimates": estimates,
                "relative_errors": errors,
                "max_active_relative_error": max(errors[j] for j in active),
                "objective": objective,
                "bound_hits": fit["bound_hits"],
                "optimizer_status": fit["optimizer_status"],
                "nfev": fit["nfev"],
            }
        )
    completed = [r for r in results if r["status"] == "completed"]
    best = min(completed, key=lambda r: r["objective"]) if completed else None
    disagreement = (
        max(abs(results[0]["estimates"][j] - results[1]["estimates"][j]) for j in active)
        if len(completed) == 2
        else None
    )
    return {
        **spec,
        "active_parameters": active,
        "unobservable": should_be_unobservable,
        "fits": results,
        "best": best,
        "start_max_absolute_disagreement": disagreement,
        "noiseless_recovered": all(
            r["status"] == "completed"
            and r["max_active_relative_error"]
            <= p["criteria"]["noiseless_active_parameter_relative_error"]
            for r in results
        )
        if spec["data"] == "noiseless"
        else None,
    }


def reconstruct(directory, *, allow_pending=False):
    directory = Path(directory)
    p, manifest = read(directory / "protocol.json"), read(directory / "manifest.json")
    validate(p)
    states = {"completed", "calculated"} if allow_pending else {"completed"}
    if manifest.get("schema") != VERSION or manifest.get("status") not in states:
        raise ValueError(
            "Incomplete/failed experiment; inspect retained manifest and case evidence"
        )
    verify_files(directory, manifest, required_files(p))
    repeat_differences = sum(
        digest(directory / name) != digest(directory / "repeat" / name)
        for name in numerical_files(p)
    )
    verification = read(directory / "verification.json")
    sensitivity = read(directory / "sensitivity.json")
    observations = read(directory / "observations.json")
    if observations["truth"] != p["model"]["truth"] or observations["times"] != list(range(241)):
        raise ValueError("Wrong observation truth/grid")
    reference = matrix(observations["reference"], 241, 3)
    if set(observations["datasets"]) != set(p["observation"]["data_cases"]):
        raise ValueError("Missing planned observation case")
    for name, data in observations["datasets"].items():
        matrix(data, 241, 3)
        noise = matrix(observations["noise"][name], 241, 3)
        for i in range(241):
            for j in range(3):
                close(data[i][j], reference[i][j] + noise[i][j])
                if name == "noiseless" or (i == 0 and j < 2):
                    close(noise[i][j], 0, 0)
    cases = [
        assess_case(p, s, read(directory / "cases" / (s["id"] + ".json")), observations)
        for s in specifications(p)
    ]
    svds, sensitivity_checks, sensitivity_passed = assess_sensitivities(p, sensitivity)
    gates = {
        "forward_verification": assess_forward(p, verification),
        "sensitivity_refinement": sensitivity_passed,
        "fresh_process_repeat": repeat_differences == 0,
        "all_fits_completed": all(f["status"] == "completed" for c in cases for f in c["fits"]),
        "noiseless_active_recovery": all(
            c["noiseless_recovered"] for c in cases if c["data"] == "noiseless"
        ),
    }
    return {
        "schema": VERSION,
        "protocol": p["id"],
        "claim": p["claim"],
        "passed": all(gates.values()),
        "gates": gates,
        "analyses": len(cases),
        "fit_starts": sum(len(c["fits"]) for c in cases),
        "repeat_artifact_differences": repeat_differences,
        "verification": verification,
        "sensitivity_checks": sensitivity_checks,
        "local_sensitivity": svds,
        "cases": cases,
        "limits": p["inference"]["scope"],
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("directory", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = reconstruct(args.directory)
    if args.output.resolve() == (args.directory / "report.json").resolve() or args.output.exists():
        raise ValueError("Choose a new reconstruction path")
    dump(args.output, result)
