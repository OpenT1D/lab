"""Reconstruct BC-012 residuals, volume conditioning and local SVD evidence."""

import argparse
import math
from pathlib import Path

from experiments.m4.joint_identifiability import common as parent_common
from experiments.m4.joint_identifiability.report import (
    assess_forward as assess_parent_forward,
)
from experiments.m4.joint_identifiability.report import (
    close,
    matrix,
    norm_difference,
    number,
    svd_check,
)

from .common import (
    NAMES,
    VERSION,
    VOLUME,
    VOLUME_CHECKS,
    active_parameters,
    declared_parameters,
    digest,
    dump,
    fixed_parameters,
    numerical_files,
    read,
    required_files,
    specifications,
    unobservable,
    validate,
    verify_files,
)


def assess_observations(p, parent, evidence):
    """Keep the original three-parameter truth and shared unscaled observations."""
    if set(evidence) != {
        "truth",
        "times",
        "reference",
        "datasets",
        "noise",
        "initial",
        "baseline",
        "generator",
    }:
        raise ValueError("Changed BC-011 observation schema")
    if evidence["truth"] != parent["model"]["truth"] or evidence["times"] != list(range(241)):
        raise ValueError("Wrong parent observation truth/grid")
    reference = matrix(evidence["reference"], 241, 3)
    names = set(p["observation"]["data_cases"])
    if set(evidence["datasets"]) != names or set(evidence["noise"]) != names:
        raise ValueError("Missing or unplanned shared observation/noise case")
    matrix([evidence["initial"]], 1, 24)
    baseline = evidence["baseline"]
    if set(baseline) != {
        "state",
        "u_sc_pmol_kg_min",
        "action_insulin_u_min",
        "Sb_pmol_kg_min",
        "Z_pmol_kg_min",
        "P_pmol_kg",
        "h_mg_dl",
    }:
        raise ValueError("Changed parent baseline schema")
    matrix([baseline["state"]], 1, 13)
    for key, value in baseline.items():
        if key != "state":
            number(value)
    if evidence["generator"] != "reference solver; invented observations, known exact basal G/I":
        raise ValueError("Changed observation-generation claim")
    for name in names:
        data = matrix(evidence["datasets"][name], 241, 3)
        noise = matrix(evidence["noise"][name], 241, 3)
        for i in range(241):
            for j in range(3):
                close(data[i][j], reference[i][j] + noise[i][j])
                if name == "noiseless" or (i == 0 and j < 2):
                    close(noise[i][j], 0, 0)


def assess_forward(p, parent, evidence):
    parent_passed = assess_parent_forward(parent, evidence["parent"])
    if set(evidence["checks"]) != set(VOLUME_CHECKS):
        raise ValueError("Missing or unplanned volume numerical gate")
    states = [parent_passed]
    for name in VOLUME_CHECKS:
        check = evidence["checks"][name]
        limit = p["criteria"][name]
        close(check["limit"], limit, 0)
        value = number(check["value"])
        if value < 0:
            raise ValueError("Negative absolute numerical error")
        passed = value <= limit
        if check["passed"] is not passed:
            raise ValueError("False volume numerical gate status")
        states.append(passed)
    passed = all(states)
    if evidence["passed"] is not passed:
        raise ValueError("False joint forward verification status")
    return passed


def assess_sensitivities(p, parent, evidence):
    full = evidence["full_weighted_log_jacobians"]
    anchors = {"0.8", "1.0", "1.2"}
    keys = {f"{solver}-{h}" for solver in ("fit", "reference") for h in (0.002, 0.001)}
    if set(full) != anchors or set(evidence["checks"]) != anchors:
        raise ValueError("Missing volume sensitivity anchor")
    checks = {}
    for anchor in sorted(anchors):
        calculations = full[anchor]
        if set(calculations) != keys:
            raise ValueError("Incomplete derivative refinement evidence")
        for array in calculations.values():
            matrix(array, 723, 4)
        ref = calculations["reference-0.001"]
        denominator = max(math.sqrt(sum(v * v for row in ref for v in row)), 1e-12)
        checks[anchor] = {
            "jacobian_relative_refinement_error": norm_difference(
                ref, calculations["reference-0.002"]
            )
            / denominator,
            "jacobian_solver_relative_error": norm_difference(ref, calculations["fit-0.001"])
            / denominator,
        }
        if set(evidence["checks"][anchor]) != set(checks[anchor]):
            raise ValueError("Missing derivative convergence gate")
        for name, value in checks[anchor].items():
            close(value, evidence["checks"][anchor][name])
    result, seen = [], set()
    expected = {(s["regime"], s["arm"], s["step"]) for s in specifications(p)}
    for record in evidence["records"]:
        identity = (record["regime"], record["arm"], record["step"])
        if identity not in expected or identity in seen:
            raise ValueError("Wrong or duplicate sensitivity design")
        seen.add(identity)
        _, arm, step = identity
        modality = "GI" if arm == "control" else "GIC"
        anchor = str(VOLUME.get(arm, 1.0))
        declared, active = declared_parameters(record), active_parameters(record)
        absent = unobservable(record)
        if (
            record["modality"] != modality
            or record["anchor"] != anchor
            or record["declared_parameters"] != declared
            or record["active_parameters"] != active
            or record["unobservable"] != [NAMES[j] for j in absent]
        ):
            raise ValueError("Wrong sensitivity anchor, modality or parameter dimensions")
        rows = [
            t * 3 + c for t in range(0, 241, step) for c in p["observation"]["modalities"][modality]
        ]
        calculations = full[anchor]
        ref = calculations["reference-0.001"]

        def selected(array):
            return [[0.0 if c in absent else array[r][c] for c in declared] for r in rows]

        predicted = selected(ref)
        matrix(record["jacobian"], len(rows), len(declared))
        for actual, wanted in zip(record["jacobian"], predicted):
            for a, b in zip(actual, wanted):
                close(a, b)
        leakage = {NAMES[j]: max(abs(ref[r][j]) for r in rows) for j in absent}
        if set(record["numerical_leakage"]) != set(leakage):
            raise ValueError("Wrong unobservable-column leakage accounting")
        for key, value in leakage.items():
            close(value, record["numerical_leakage"][key])
        numeric_uncertainty = max(
            norm_difference(predicted, selected(calculations[k]))
            for k in ("reference-0.002", "fit-0.001")
        )
        checked = svd_check(record, parent)
        checked["jacobian_refinement_discrepancy_norm"] = numeric_uncertainty
        checked["directions_above_numerical_discrepancy"] = sum(
            s
            > max(
                numeric_uncertainty,
                parent["inference"]["svd_relative_cutoff"] * record["singular_values"][0],
            )
            for s in record["singular_values"]
        )
        checked["rank_resolved_under_checked_refinements"] = (
            checked["directions_above_numerical_discrepancy"] == checked["rank"]
        )
        result.append(checked)
    if seen != expected:
        raise ValueError("Incomplete sensitivity matrix")
    passed = all(v <= p["criteria"][k] for item in checks.values() for k, v in item.items())
    if evidence["passed"] is not passed:
        raise ValueError("False sensitivity gate status")
    return result, checks, passed


def assess_case(p, spec, case, observations):
    if any(case.get(k) != v for k, v in spec.items()):
        raise ValueError("Case identity mismatch")
    active, fixed = active_parameters(spec), fixed_parameters(spec)
    absent = [NAMES[j] for j in unobservable(spec)]
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
    if case["unobservable"] != absent or case["fixed_parameters"] != fixed:
        raise ValueError("Wrong fixed or unobservable parameter conditioning")
    results, truth = [], p["model"]["truth"]
    for start, fit in zip(p["inference"]["starts"], case["fits"]):
        if fit["start"] != start or fit["active_parameters"] != active:
            raise ValueError("Changed start or fitted dimensions")
        if fit["status"] == "model_failed":
            error = fit.get("error")
            if (
                not isinstance(error, dict)
                or not isinstance(error.get("type"), str)
                or not isinstance(error.get("message"), str)
            ):
                raise ValueError("Failed model must retain its error")
            if any(k in fit for k in ("estimates", "objective", "prediction", "residuals")):
                raise ValueError("Failed model cannot contain fabricated fit evidence")
            results.append({"status": fit["status"], "error": error})
            continue
        if fit["status"] not in ("completed", "optimizer_failed"):
            raise ValueError("Unknown fit status")
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
        for actual, expected_value in zip(fit["residuals"], residuals):
            close(actual, expected_value)
        channel_objectives = [
            sum(r * r for r in residuals[k :: len(columns)]) for k in range(len(columns))
        ]
        if len(fit["channel_objectives"]) != len(columns):
            raise ValueError("Incomplete channel objectives")
        for actual, expected_value in zip(fit["channel_objectives"], channel_objectives):
            close(actual, expected_value)
        objective = sum(channel_objectives)
        close(fit["objective"], objective)
        estimates = fit["estimates"]
        if len(estimates) != 4 or any(
            estimates[j] is not None for j in range(4) if j not in active
        ):
            raise ValueError("Unestimated parameter must not have a numerical estimate")
        errors, bias = [None] * 4, [None] * 4
        for j in active:
            value = number(estimates[j])
            if not p["model"]["lower"][j] <= value <= p["model"]["upper"][j]:
                raise ValueError("Estimate outside frozen bounds")
            bias[j] = (value - truth[j]) / truth[j]
            errors[j] = abs(bias[j])
        evaluated = matrix([fit["evaluated_parameters"]], 1, 4)[0]
        for j, value in enumerate(evaluated):
            target = estimates[j] if j in active else fixed.get(NAMES[j], 1.0)
            close(value, target, 0)
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
        for key in ("nfev", "forward_evaluations"):
            if type(fit[key]) is not int or fit[key] < 1:
                raise ValueError("Incomplete optimizer evaluation accounting")
        if number(fit["optimality"]) < 0:
            raise ValueError("Negative optimizer optimality")
        results.append(
            {
                "status": fit["status"],
                "estimates": estimates,
                "evaluated_parameters": evaluated,
                "relative_errors": errors,
                "relative_bias": bias,
                "max_active_relative_error": max(errors[j] for j in active),
                "objective": objective,
                "channel_objectives": channel_objectives,
                "bound_hits": bound_hits,
                "optimizer_status": code,
                "nfev": fit["nfev"],
                "forward_evaluations": fit["forward_evaluations"],
            }
        )
    completed = [r for r in results if r["status"] == "completed"]
    best = min(completed, key=lambda r: r["objective"]) if completed else None
    disagreement = (
        max(abs(results[0]["estimates"][j] - results[1]["estimates"][j]) for j in active)
        if len(completed) == 2
        else None
    )
    eligible = spec["data"] == "noiseless" and spec["arm"] in ("correct", "estimated", "control")
    return {
        **spec,
        "active_parameters": active,
        "unobservable": absent,
        "fixed_parameters": fixed,
        "fits": results,
        "best": best,
        "start_max_absolute_disagreement": disagreement,
        "noiseless_recovery_eligible": eligible,
        "noiseless_recovered": all(
            r["status"] == "completed"
            and r["max_active_relative_error"]
            <= p["criteria"]["noiseless_active_parameter_relative_error"]
            for r in results
        )
        if eligible
        else None,
    }


def reconstruct(directory, *, allow_pending=False):
    directory = Path(directory)
    p, parent = read(directory / "protocol.json"), read(directory / "parent.json")
    manifest = read(directory / "manifest.json")
    validate(p)
    parent_common.validate(parent)
    if p["parent_protocol"] != parent["id"]:
        raise ValueError("Wrong parent protocol")
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
    observations = read(directory / "observations.json")
    assess_observations(p, parent, observations)
    cases = [
        assess_case(p, s, read(directory / "cases" / (s["id"] + ".json")), observations)
        for s in specifications(p)
    ]
    svds, sensitivity_checks, sensitivity_passed = assess_sensitivities(
        p, parent, read(directory / "sensitivity.json")
    )
    gates = {
        "forward_verification": assess_forward(p, parent, verification),
        "sensitivity_refinement": sensitivity_passed,
        "fresh_process_repeat": repeat_differences == 0,
        "all_fits_completed": all(f["status"] == "completed" for c in cases for f in c["fits"]),
        "noiseless_eligible_recovery": all(
            c["noiseless_recovered"] for c in cases if c["noiseless_recovery_eligible"]
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
        "limits": p["inference"]["interpretation"],
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
