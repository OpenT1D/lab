"""Reconstruct BC-014 arithmetic, coverage and failures without numerical packages."""

import argparse
import math
from pathlib import Path

from experiments.m4.joint_identifiability import common as joint_common
from experiments.m4.joint_identifiability.report import close, matrix
from experiments.m4.profile_likelihood import common as profile_common
from experiments.m4.profile_likelihood import report as profile_report
from experiments.m4.volume_sensitivity import common as volume_common

from .common import (
    GROUPS,
    VERSION,
    adapted_profile,
    digest,
    dump,
    file_hashes,
    numerical_files,
    observation_specs,
    read,
    required_files,
    specifications,
    validate,
    verify_files,
)


def wilson(included, planned):
    """Two-sided 95% Wilson interval, with explicit finite integer inputs."""
    if (
        type(included) is not int
        or type(planned) is not int
        or planned <= 0
        or not 0 <= included <= planned
    ):
        raise ValueError("Valid integer inclusion count and positive denominator required")
    z = 1.959963984540054
    p = included / planned
    divisor = 1 + z * z / planned
    center = (p + z * z / (2 * planned)) / divisor
    half = z * math.sqrt(p * (1 - p) / planned + z * z / (4 * planned * planned)) / divisor
    return [max(0.0, center - half), min(1.0, center + half)]


def assess_observation(protocol, spec, record):
    if (
        record.get("id") != spec["id"]
        or record.get("group") != spec["group"]
        or record.get("seed") != spec["seed"]
        or record.get("status") != "completed"
        or record.get("truth") != protocol["design"][spec["group"]]["truth"]
        or record.get("times") != list(range(241))
        or record.get("generator")
        != "unchanged BC-012 reference solver; independent seeded Gaussian errors"
    ):
        raise ValueError("Changed or incomplete generating observation identity")
    sd = matrix([record["sd"]], 1, 3)[0]
    if sd != [5, 10, 30]:
        raise ValueError("Changed declared Gaussian SDs")
    reference = matrix(record["reference"], 241, 3)
    error = matrix(record["error"], 241, 3)
    observed = matrix(record["observed"], 241, 3)
    if error[0][:2] != [0, 0]:
        raise ValueError("Basal glucose/insulin errors must be exactly zero")
    for row in range(241):
        for channel in range(3):
            close(observed[row][channel], reference[row][channel] + error[row][channel])
    return {"times": record["times"], "observed": observed, "sd": sd}


def assess_case(protocol, parent, spec, record, observation):
    if any(record.get(key) != spec[key] for key in ("id", "group", "seed", "design")):
        raise ValueError("Wrong case identity")
    if record.get("truth") != protocol["design"][spec["group"]]["truth"]:
        raise ValueError("Wrong generating parameter vector")
    if record.get("status") != "completed":
        if record.get("status") not in ("failed", "started", "partial"):
            raise ValueError("Unknown incomplete case status")
        if record.get("covered") is not False:
            raise ValueError("Incomplete case cannot claim inclusion")
        if len(record.get("baseline", [])) > 3 or len(record.get("constrained", [])) > 2:
            raise ValueError("Incomplete case has extra optimizer starts")
        return {**spec, "status": record["status"], "covered": False, "error": record.get("error")}

    adapted = adapted_profile(parent)
    rows = profile_common.selection(adapted, spec)
    observed = [observation["observed"][i // 3][i % 3] for i in rows]
    sd = [observation["sd"][i % 3] for i in rows]
    starts = adapted["inference"]["unrestricted_starts"]
    _, baseline = profile_report.assess_fits(
        adapted, spec, record["baseline"], observed, sd, starts
    )
    if baseline is None:
        raise ValueError("Completed case has no unrestricted minimum")
    target = {"parameter": protocol["design"]["interest_parameter"], "value": record["truth"][0]}
    nuisance_starts = profile_report.profile_starts(
        adapted, spec, baseline["evaluated_parameters"], target["parameter"]
    )
    _, constrained = profile_report.assess_fits(
        adapted,
        spec,
        record["constrained"],
        observed,
        sd,
        nuisance_starts,
        interest=target,
    )
    if constrained is None:
        raise ValueError("Completed case has no true-gain conditional minimum")
    ref = record["reference"]
    base_eval = profile_report.assess_evaluation(
        adapted, spec, ref["baseline_at_fit"], observed, sd
    )
    fixed_eval = profile_report.assess_evaluation(
        adapted, spec, ref["constrained_at_fit"], observed, sd, interest=target
    )
    if (
        base_eval["evaluated_parameters"] != baseline["evaluated_parameters"]
        or fixed_eval["evaluated_parameters"] != constrained["evaluated_parameters"]
    ):
        raise ValueError("Reference solver did not evaluate the selected fit optima")
    cutoff = protocol["analysis"]["cutoff"]
    tolerance = protocol["analysis"]["reference_objective_tolerance"]
    delta = constrained["objective"] - baseline["objective"]
    reference_delta = fixed_eval["objective"] - base_eval["objective"]
    covered = delta <= cutoff
    need_refit = abs(delta - cutoff) <= protocol["analysis"][
        "reference_refit_margin"
    ] or covered != (reference_delta <= cutoff)
    if (ref["refit"] is not None) is not need_refit:
        raise ValueError("Missing or unplanned reference-solver reoptimization")
    refit_agrees = True
    if need_refit:
        _, ref_base = profile_report.assess_fits(
            adapted, spec, ref["refit"]["baseline"], observed, sd, starts
        )
        if ref_base is None:
            raise ValueError("Reference unrestricted fit is incomplete")
        ref_starts = profile_report.profile_starts(
            adapted, spec, ref_base["evaluated_parameters"], target["parameter"]
        )
        _, ref_fixed = profile_report.assess_fits(
            adapted,
            spec,
            ref["refit"]["constrained"],
            observed,
            sd,
            ref_starts,
            interest=target,
        )
        if ref_fixed is None:
            raise ValueError("Reference conditional fit is incomplete")
        refit_delta = ref_fixed["objective"] - ref_base["objective"]
        refit_agrees = (
            all(
                fit["status"] == "completed"
                for fit in (*ref["refit"]["baseline"], *ref["refit"]["constrained"])
            )
            and abs(ref_base["objective"] - baseline["objective"]) <= tolerance
            and abs(ref_fixed["objective"] - constrained["objective"]) <= tolerance
            and abs(refit_delta - delta) <= tolerance
            and (refit_delta <= cutoff) == covered
        )
    gates = {
        "all_starts_completed": all(
            fit["status"] == "completed" for fit in (*record["baseline"], *record["constrained"])
        ),
        "constrained_not_below_baseline": delta >= -protocol["analysis"]["lower_delta_tolerance"],
        "reference_objectives": abs(base_eval["objective"] - baseline["objective"]) <= tolerance
        and abs(fixed_eval["objective"] - constrained["objective"]) <= tolerance
        and abs(reference_delta - delta) <= tolerance,
        "reference_inclusion": (reference_delta <= cutoff) == covered,
        "reference_refit": refit_agrees,
    }
    if record["gates"] != gates or not all(gates.values()):
        raise ValueError("False completed numerical gate")
    close(record["delta_q"], delta)
    if record["covered"] is not covered:
        raise ValueError("False pointwise inclusion")
    return {
        **spec,
        "status": "completed",
        "covered": covered,
        "delta_q": delta,
        "unrestricted_objective": baseline["objective"],
        "constrained_objective": constrained["objective"],
        "unrestricted_bound_hits": baseline["bound_hits"],
        "nuisance_bound_hits": [j for j in constrained["bound_hits"] if j != target["parameter"]],
        "reference_refit": need_refit,
    }


def summarize(protocol, cases):
    result = {}
    for group in GROUPS:
        for design in protocol["design"][group]["observation_designs"]:
            expected = protocol["design"][group]["seeds"]["count"]
            selected = [c for c in cases if c["group"] == group and c["design"] == design]
            if len(selected) != expected:
                raise ValueError("Missing planned coverage analysis")
            completed = sum(c["status"] == "completed" for c in selected)
            included = sum(c["status"] == "completed" and c["covered"] for c in selected)
            result[f"{group}/{design}"] = {
                "planned": expected,
                "completed": completed,
                "failed": expected - completed,
                "included": included,
                "conservative_rate": included / expected,
                "wilson_95": wilson(included, expected),
                "completed_rate": included / completed if completed else None,
                "unrestricted_bound_hits": sum(
                    bool(c["unrestricted_bound_hits"])
                    for c in selected
                    if c["status"] == "completed"
                ),
                "constrained_nuisance_bound_hits": sum(
                    bool(c["nuisance_bound_hits"]) for c in selected if c["status"] == "completed"
                ),
                "reference_refits": sum(
                    c["reference_refit"] for c in selected if c["status"] == "completed"
                ),
                "nominal_reference": protocol["design"][group]["nominal_reference"],
            }
    return result


def reconstruct(directory, *, allow_pending=False, allow_failed=False):
    directory = Path(directory)
    protocol = read(directory / "protocol.json")
    parent, volume, joint = (
        read(directory / "parent-profile.json"),
        read(directory / "parent-volume.json"),
        read(directory / "parent-joint.json"),
    )
    validate(protocol)
    profile_common.validate(parent)
    volume_common.validate(volume)
    joint_common.validate(joint)
    if (
        protocol["parent_protocol"] != parent["id"]
        or parent["parent_protocol"] != volume["id"]
        or volume["parent_protocol"] != joint["id"]
    ):
        raise ValueError("Changed model and inference ancestry")
    manifest = read(directory / "manifest.json")
    permitted = {"completed"}
    if allow_pending:
        permitted.add("calculated")
    if allow_failed:
        permitted.add("failed")
    if manifest.get("schema") != VERSION or manifest.get("status") not in permitted:
        raise ValueError("Incomplete or failed campaign; inspect retained checkpoints")
    verify_files(directory, manifest, required_files(protocol))
    if set(manifest["files"]) != set(file_hashes(directory)):
        raise ValueError("Unaccounted archived file")
    differences = sum(
        digest(directory / name) != digest(directory / "repeat" / name)
        for name in numerical_files(protocol)
    )
    worker = read(directory / "worker.json")
    runtime = worker["runtime"]
    upstream = read(directory / "source-experiments__m4__feedback__protocol.json")["upstream"]
    native = worker["native"]
    if (
        not runtime["python"].startswith(protocol["runtime"]["python"] + ".")
        or runtime["numpy"] != protocol["runtime"]["numpy"]
        or runtime["scipy"] != protocol["runtime"]["scipy"]
        or native["profile"] != upstream["profile"]
        or native["upstream_revision"] != upstream["revision"]
        or native["patient_file_sha256"] != upstream["patient_file_sha256"]
        or native["parameter_file_sha256"] != upstream["parameter_file_sha256"]
    ):
        raise ValueError("Wrong native profile or numerical runtime")
    observations = {
        spec["id"]: assess_observation(
            protocol,
            spec,
            read(directory / "observations" / (spec["id"] + ".json")),
        )
        for spec in observation_specs(protocol)
    }
    cases = [
        assess_case(
            protocol,
            parent,
            spec,
            read(directory / "cases" / (spec["id"] + ".json")),
            observations[f"{spec['group']}-{spec['seed']}"],
        )
        for spec in specifications(protocol)
    ]
    verification = read(directory / "verification.json")
    gates = {
        "inherited_numerical_oracles": profile_report.assess_forward(
            parent, volume, joint, verification
        ),
        "all_cases_completed": all(c["status"] == "completed" for c in cases),
        "fresh_process_repeat": differences == 0,
    }
    report = {
        "schema": VERSION,
        "protocol": protocol["id"],
        "claim": protocol["claim"],
        "passed": all(gates.values()),
        "gates": gates,
        "analyses": len(cases),
        "new_draws": len(observations),
        "repeat_artifact_differences": differences,
        "summary": summarize(protocol, cases),
        "cases": cases,
        "limits": protocol["limitations"],
    }
    if manifest["status"] == "completed":
        if read(directory / "report.json") != report:
            raise ValueError("Saved report differs from independent reconstruction")
        from .plot import render

        if (directory / "figure.svg").read_text() != render(report):
            raise ValueError("Saved figure differs from reconstructed coverage")
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("directory", type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--allow-failed", action="store_true")
    args = parser.parse_args()
    if args.output.exists() or args.output.resolve() == (args.directory / "report.json").resolve():
        raise ValueError("Choose a new reconstruction path")
    dump(args.output, reconstruct(args.directory, allow_failed=args.allow_failed))
