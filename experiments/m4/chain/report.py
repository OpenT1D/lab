"""Reassess saved chain states without a solver or execution of archived code."""

import argparse
import math
from pathlib import Path

from experiments.m4.kinetic_inlet.forcing import Forcing
from experiments.m4.paired_kinetics.report import matrix, maxdiff, state_checks

from .common import (
    REUSED,
    SOURCES,
    VERSION,
    boundary,
    dump,
    finite,
    grid,
    load_source,
    prepare,
    read,
    validate,
    verify_files,
)


def integral(times, values):
    return math.fsum(
        (b - a) * (x + y) / 2 for a, b, x, y in zip(times, times[1:], values, values[1:])
    )


def samples(directory, p, source):
    data = read(Path(directory) / "source-samples.json")
    if (
        data.get("schema") != "bc007-source/1"
        or data.get("implementation") != VERSION
        or data.get("model") != p["source"]["model"]
    ):
        raise ValueError("Wrong source sampling identity")
    if any(data["runtime"][k] != p["runtime"]["cpeptide"][k] for k in ("numpy", "scipy")):
        raise ValueError("Wrong source sampling runtime")
    levels = data["levels"]
    if [v["step_min"] for v in levels] != p["source"]["refinement_steps_min"]:
        raise ValueError("Incomplete source refinement")
    if levels[0] != {"step_min": p["source"]["primary_sample_step_min"], **source}:
        raise ValueError("Primary samples differ from source archive")
    sp = read(Path(directory) / "secretion/protocol.json")
    error, amounts = 0.0, []
    for index, level in enumerate(levels):
        times = grid(p, level["step_min"])
        if level["times_min"] != times:
            raise ValueError("Incomplete source sample times")
        for key in ("glucose_mmol_l", "secretion_ug_min"):
            values = level[key]
            if len(values) != len(times):
                raise ValueError("Incomplete source samples")
            for v in values:
                finite(v)
        for t, g in zip(times, level["glucose_mmol_l"], strict=True):
            expected = sp["input"]["g_b"] + (sp["input"]["g_max"] - sp["input"]["g_b"]) * math.exp(
                -t / sp["input"]["tau_min"]
            )
            if abs(g - expected) > 1e-12:
                raise ValueError("Source glucose differs from prescribed input")
        if index > 0:
            rows = matrix(level.get("states"), len(times), 2)
            if any(
                abs(row[0] * sp["parameters"]["m"] - q) > 1e-12 or min(row) < 0
                for row, q in zip(rows, level["secretion_ug_min"], strict=True)
            ):
                raise ValueError("Fine source output differs from mX or has negative state")
        stride = round(p["sample_step_min"] / level["step_min"])
        error = max(
            error,
            max(
                abs(a - b)
                for a, b in zip(
                    source["secretion_ug_min"], level["secretion_ug_min"][::stride], strict=True
                )
            ),
        )
        amounts.append(integral(times, level["secretion_ug_min"]))
    return (
        levels,
        {
            "source_nested_sample_error_ug_min": error,
            "source_integral_refinement_relative_error": abs(amounts[-1] - amounts[-2])
            / max(abs(amounts[-1]), 1e-15),
        },
        amounts,
    )


def assess_case(item, request, p, branch, volume):
    times = grid(p)
    width = 5 if branch == "insulin" else 4
    initial = request["initial"][branch]
    if (
        item.get("schema") != "bc007-case/1"
        or item.get("branch") != branch
        or item.get("request") != request
        or item.get("times_min") != times
        or item.get("volume_l_kg") != volume
    ):
        raise ValueError("Wrong chain case, input, units, initial state or volume")
    if set(item["states"]) != {"tight", "reference"}:
        raise ValueError("Incomplete solver comparison")
    tight, ref = [matrix(item["states"][k], len(times), width) for k in ("tight", "reference")]
    exact = matrix(item["oracle"], len(times), width)
    repeat = matrix(item["repeated"], len(times), width)
    measured = {
        "oracle_state_error_pmol_kg": maxdiff(ref, exact),
        "solver_concentration_error_pmol_l": max(
            abs(a[0] - b[0]) / volume for a, b in zip(tight, ref, strict=True)
        ),
        "repeat_error": maxdiff(ref, repeat),
    }
    force = Forcing(**request["forcing"])
    for values in (tight, ref, exact, repeat):
        if values[0] != initial:
            raise ValueError("Kinetic initial inventory changed")
        for key, value in state_checks(values, times, force, initial).items():
            measured[key] = max(measured.get(key, 0), value)
    if request["id"] == "zero_increment" and any(
        v != 0 for values in (tight, ref, exact, repeat) for row in values for v in row
    ):
        raise ValueError("Zero source produced nonzero kinetic output")
    if request["id"] == "basal_only":
        measured["equilibrium_error_pmol_kg"] = max(
            abs(row[k] - initial[k]) for row in ref for k in (0, 1)
        )
    if branch == "insulin" and not any(initial):
        measured["legacy_zero_initial_error"] = maxdiff(
            matrix(item["legacy"], len(times), width), ref
        )
    elif item["legacy"] is not None:
        raise ValueError("Unexpected legacy comparison")
    return {
        "metrics": measured,
        "passed": all(v <= p["criteria"][k] for k, v in measured.items()),
        "initial_concentration_pmol_l": ref[0][0] / volume,
        "peak_sampled_concentration_pmol_l": max(row[0] / volume for row in ref),
        "final_concentration_pmol_l": ref[-1][0] / volume,
        "delivered_pmol_kg": ref[-1][-1],
    }


def assess_branch(directory, p, b, source, levels, branch):
    folder = Path(directory) / branch
    meta = read(folder / "worker.json")
    order = (
        ["Ip", "Il", "hepatic_loss", "peripheral_loss", "input"]
        if branch == "insulin"
        else ["central", "peripheral", "eliminated", "input"]
    )
    volume = b[branch]["volume_l_kg"]
    if (
        meta.get("schema") != "bc007-worker/1"
        or meta.get("status") != "completed"
        or meta.get("branch") != branch
        or meta.get("implementation") != VERSION
        or meta.get("state_order") != order
        or meta.get("volume_l_kg") != volume
    ):
        raise ValueError("Incomplete or mismatched chain worker")
    if any(meta["runtime"][k] != p["runtime"][branch][k] for k in ("numpy", "scipy")):
        raise ValueError("Wrong worker runtime")
    if branch == "insulin":
        identity = meta["native_identity"]
        upstream = read(Path(directory) / "source-experiments__m4__kinetic_inlet__protocol.json")[
            "upstream"
        ]
        for key, expected in (
            ("upstream_revision", upstream["revision"]),
            ("profile", upstream["profile"]),
            ("patient_file_sha256", upstream["patient_file_sha256"]),
            ("parameter_file_sha256", upstream["parameter_file_sha256"]),
            ("body_weight_kg", p["boundary"]["body_weight_kg"]),
        ):
            if identity[key] != expected:
                raise ValueError("Wrong native identity")
        expected = {
            "BW": p["boundary"]["body_weight_kg"],
            "Vi": volume,
            **{k: b["insulin"][k] for k in ("m1", "m2", "m30", "m4")},
        }
        if any(
            not math.isclose(identity["kinetic_parameters"][k], v, rel_tol=1e-14, abs_tol=0)
            for k, v in expected.items()
        ):
            raise ValueError("Wrong native parameters")
    data, summaries = {}, {}
    for case in p["cases"]:
        item = read(folder / f"{case['id']}.json")
        data[case["id"]] = item
        summaries[case["id"]] = assess_case(item, prepare(p, b, case, source), p, branch, volume)
    states = {k: v["states"]["reference"] for k, v in data.items()}
    full, half, total, basal = [
        states[k]
        for k in ("full_increment", "half_increment", "full_synthetic_total", "basal_only")
    ]
    superposition = max(
        abs(t - a - z)
        for rt, rf, rb in zip(total, full, basal, strict=True)
        for t, a, z in zip(rt, rf, rb, strict=True)
    )
    linearity = max(
        abs(h - 0.5 * f)
        for rh, rf in zip(half, full, strict=True)
        for h, f in zip(rh, rf, strict=True)
    )
    matched = states["matched_constant_increment"]
    contrast = max(abs(a[0] - v[0]) / volume for a, v in zip(full, matched, strict=True))
    runs = read(folder / "refinement.json")["runs"]
    if [v["step_min"] for v in runs] != p["source"]["refinement_steps_min"]:
        raise ValueError("Missing chain source refinement")
    case = next(c for c in p["cases"] if c["id"] == "full_increment")
    refinement = []
    for run, level in zip(runs, levels, strict=True):
        request = prepare(p, b, case, level)
        if run["request"] != request:
            raise ValueError("Refinement input differs from source samples")
        values = matrix(run["states"], len(grid(p)), len(order))
        if values[0] != request["initial"][branch]:
            raise ValueError("Wrong refined initial state")
        checks = state_checks(
            values, grid(p), Forcing(**request["forcing"]), request["initial"][branch]
        )
        if any(v > p["criteria"][k] for k, v in checks.items()):
            raise ValueError("Refined trajectory violates accounting or positivity")
        refinement.append(values)
    if refinement[0] != full:
        raise ValueError("Repeated primary transfer differs")
    errors = [
        max(abs(a[0] - z[0]) / volume for a, z in zip(values, refinement[-1], strict=True))
        for values in refinement[:-1]
    ]
    metrics = {
        "superposition_error_pmol_kg": superposition,
        "gain_linearity_error_pmol_kg": linearity,
        "fine_sampling_error_pmol_l": errors[-1],
        "sampling_error_ratio": errors[-1] / errors[0]
        if errors[0]
        else (0 if errors[-1] == 0 else math.inf),
    }
    return {
        "metadata": meta,
        "cases": summaries,
        "metrics": metrics,
        "sampling_errors_to_finest_pmol_l": errors,
        "matched_constant_max_concentration_contrast_pmol_l": contrast,
        "passed": all(s["passed"] for s in summaries.values())
        and all(v <= p["criteria"][k] for k, v in metrics.items()),
    }


def required(p):
    return {
        "protocol.json",
        "boundary.json",
        "source-samples.json",
        "secretion/manifest.json",
        *(f"source-{s}" for s in SOURCES),
        *("source-" + s.replace("/", "__") for s in REUSED),
        *(f"{branch}-{name}" for branch in p["runtime"] for name in ("uv.lock", "pyproject.toml")),
        *(
            f"{branch}/{name}.json"
            for branch in p["runtime"]
            for name in ([c["id"] for c in p["cases"]] + ["worker", "refinement"])
        ),
    }


def reconstruct(directory, *, allow_pending=False):
    directory = Path(directory)
    manifest = read(directory / "manifest.json")
    if (
        manifest.get("implementation") != VERSION
        or manifest.get("schema") != "bc007-run/1"
        or manifest.get("status")
        not in ({"calculated", "completed"} if allow_pending else {"completed"})
    ):
        raise ValueError("Chain run is not complete")
    p = read(directory / "protocol.json")
    validate(p)
    verify_files(
        directory,
        manifest,
        required(p) | (set() if allow_pending else {"report.json", "figure.svg"}),
    )
    source = load_source(directory / "secretion", p)
    b = boundary(directory, p)
    levels, source_metrics, amounts = samples(directory, p, source)
    requests = {c["id"]: prepare(p, b, c, source) for c in p["cases"]}
    factor = 1e6 / (p["boundary"]["insulin_molar_mass_g_mol"] * p["boundary"]["body_weight_kg"])
    conversion = 0.0
    for case in p["cases"]:
        force = Forcing(**requests[case["id"]]["forcing"])
        expected = amounts[0] * case["evoked_gain"] * factor
        if case["basal"]:
            expected += (
                p["boundary"]["basal_pmol_min"] * p["horizon_min"] / p["boundary"]["body_weight_kg"]
            )
        conversion = max(conversion, abs(force.integral() - expected) / max(abs(expected), 1))
    equal = abs(
        Forcing(**requests["full_increment"]["forcing"]).integral()
        - Forcing(**requests["matched_constant_increment"]["forcing"]).integral()
    )
    branches = {key: assess_branch(directory, p, b, source, levels, key) for key in p["runtime"]}
    pair = 0.0
    for case in p["cases"]:
        left = read(directory / "insulin" / f"{case['id']}.json")["request"]["forcing"]
        right = read(directory / "cpeptide" / f"{case['id']}.json")["request"]["forcing"]
        if left != right:
            raise ValueError("Branches received different molar forcing")
    metrics = {
        **source_metrics,
        "conversion_relative_error": conversion,
        "equal_amount_error_pmol_kg": equal,
        "paired_input_error": pair,
    }
    return {
        "schema": "bc007-report/1",
        "implementation": VERSION,
        "protocol": p["id"],
        "source_manifest_sha256": source["source_manifest_sha256"],
        "source_interpolant_amounts_ug": amounts,
        "transfer_metrics": metrics,
        "branches": branches,
        "passed": all(v <= p["criteria"][k] for k, v in metrics.items())
        and all(v["passed"] for v in branches.values()),
        "claim": p["claim"],
        "limitations": p["excluded"],
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("directory", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise FileExistsError(args.output)
    result = reconstruct(args.directory)
    dump(args.output, result)
    if not result["passed"]:
        raise SystemExit("Chain criteria failed")


if __name__ == "__main__":
    main()
