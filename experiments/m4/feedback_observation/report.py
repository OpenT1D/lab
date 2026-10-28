"""Reconstruct BC-010 boundary checks and results using only saved artifacts."""

import argparse
import math
from pathlib import Path

from experiments.m4.feedback.contract import number
from experiments.m4.hepatic.report import reconstruct as parent_report
from experiments.m4.kinetic_inlet.forcing import Forcing
from experiments.m4.paired_kinetics.report import matrix

from .adapter import diagnostic_inputs, prepare
from .common import (
    VERSION,
    digest,
    dump,
    labels,
    numerical_files,
    read,
    required_files,
    source,
    validate,
    verify_files,
)


def concentrations(states, volume):
    return [row[0] / volume for row in states]


def discrepancy(a, b, volume):
    return max(abs(x[0] - y[0]) / volume for x, y in zip(a, b, strict=True))


def outcomes(times, values):
    peak = max(values)
    return {
        "baseline_pmol_l": values[0],
        "peak_pmol_l": peak,
        "sampled_peak_time_min": times[values.index(peak)],
        "final_pmol_l": values[-1],
        "auc_above_initial_pmol_min_l": math.fsum(
            (tb - ta) * (a + b - 2 * values[0]) / 2
            for ta, tb, a, b in zip(times, times[1:], values, values[1:])
        ),
    }


def inspect(states, boundary):
    t, initial = boundary["times"], boundary["initial"]
    y = matrix(states, len(t), 4)
    if y[0] != initial:
        raise ValueError("Incorrect C-peptide initial inventory")
    forcing = Forcing(**boundary["forcing"])
    amount, input_error = 0.0, 0.0
    for a, b, row in zip(t, t[1:], y[1:]):
        amount += forcing.integral(a, b)
        input_error = max(input_error, abs(row[3] - amount))
    return {
        "mass_error_pmol_kg": max(
            abs(math.fsum(row[:3]) - row[3] - math.fsum(initial[:2])) for row in y
        ),
        "input_error_pmol_kg": input_error,
        "negative_tolerance_pmol_kg": max(0, -min(v for row in y for v in row)),
    }


def assess_case(p, item, reference, tight):
    expected = prepare(p, reference)
    if (
        item["status"] != "completed"
        or item["boundary"] != expected
        or set(item["states"]) != {"tight", "reference"}
    ):
        raise ValueError("Wrong observation boundary or incomplete kinetic solve")
    times, volume = expected["times"], expected["parameters"]["volume_l_kg"]
    states = {k: matrix(v, len(times), 4) for k, v in item["states"].items()}
    exact = matrix(item["oracle"], len(times), 4)
    checks = {k: 0.0 for k in p["criteria"] if k != "sampling_ratio_floor_pmol_l"}
    for y in [*states.values(), exact]:
        for k, v in inspect(y, expected).items():
            checks[k] = max(checks[k], v)
        checks["oracle_concentration_error_pmol_l"] = max(
            checks["oracle_concentration_error_pmol_l"], discrepancy(y, exact, volume)
        )
    ref = states["reference"]
    checks["solver_concentration_error_pmol_l"] = discrepancy(ref, states["tight"], volume)
    concentration = concentrations(ref, volume)
    inp = Forcing(**expected["forcing"])
    parent_amount = number(reference["states"][-1][16])
    checks["parent_dose_relative_error"] = abs(inp.integral() - parent_amount) / max(
        1, parent_amount
    )
    if all(q == 0 for q in inp.left + inp.right):
        checks["zero_state_error"] = max(abs(v) for row in ref for v in row)
    if "--constant_basal--" in item["id"] or item["id"].startswith("fasting--"):
        checks["equilibrium_drift_pmol_l"] = max(abs(v - concentration[0]) for v in concentration)
    bundles = diagnostic_inputs(p, reference, tight)
    if item["diagnostics"].keys() != bundles.keys():
        raise ValueError("Missing observation diagnostic")
    diagnostics = {}
    for name, bundle in bundles.items():
        data = item["diagnostics"][name]
        if data["boundary"] != bundle:
            raise ValueError("Changed diagnostic input, volume or initial inventory")
        y = matrix(data["states"], len(times), 4)
        for k, v in inspect(y, bundle).items():
            checks[k] = max(checks[k], v)
        vals = concentrations(y, bundle["parameters"]["volume_l_kg"])
        delta = [v - b for v, b in zip(vals, concentration, strict=True)]
        diagnostics[name] = {
            "max_abs_difference_pmol_l": max(abs(v) for v in delta),
            "min_signed_difference_pmol_l": min(delta),
            "max_signed_difference_pmol_l": max(delta),
            "outcomes": outcomes(times, vals),
        }

    def error(name):
        return diagnostics[name]["max_abs_difference_pmol_l"]

    checks["parent_source_solver_error_pmol_l"] = error("parent_tight")
    checks["finest_coarsening_error_pmol_l"] = error("sampling_0.5")
    coarse = error("sampling_1")
    checks["coarsening_error_ratio"] = (
        error("sampling_0.5") / coarse
        if coarse > p["criteria"]["sampling_ratio_floor_pmol_l"]
        else 0.0
    )
    checks["scale_ambiguity_error_pmol_l"] = max(error("scale_0.5"), error("scale_2"))
    return {
        "checks": checks,
        "outcomes": outcomes(times, concentration),
        "diagnostics": diagnostics,
        "pancreatic_amount_pmol_kg": parent_amount,
        "interpolated_amount_pmol_kg": inp.integral(),
    }


def reconstruct(directory, *, allow_pending=False, allow_failed=False):
    directory = Path(directory)
    p, manifest = read(directory / "protocol.json"), read(directory / "manifest.json")
    validate(p)
    allowed = (
        {"completed"}
        | ({"calculated"} if allow_pending else set())
        | ({"failed"} if allow_failed else set())
    )
    if manifest["schema"] != VERSION or manifest["status"] not in allowed:
        raise ValueError("Incomplete observation archive")
    verify_files(directory, manifest, {"protocol.json"})
    if not all(
        (directory / "hepatic" / name).is_file()
        for name in ("manifest.json", "protocol.json", "parent.json")
    ):
        if allow_failed and manifest["status"] == "failed":
            return {
                "passed": False,
                "expected_cases": 24,
                "cases": {},
                "error": manifest.get("error"),
                "missing_evidence": ["completed parent"],
            }
        raise ValueError("Missing parent")
    names = labels(directory)
    required = required_files(names)
    missing = sorted(required - manifest["files"].keys())
    failures = {
        name: read(directory / f"cases/{name}.json")
        for name in names
        if (directory / f"cases/{name}.json").is_file()
        and read(directory / f"cases/{name}.json").get("status") != "completed"
    }
    if missing or failures:
        if not allow_failed and manifest["status"] != "calculated":
            raise ValueError("Missing or failed observation cases")
        return {
            "passed": False,
            "expected_cases": 24,
            "cases": {},
            "failures": failures,
            "missing_evidence": missing,
            "error": manifest.get("error"),
        }
    if digest(directory / "hepatic/manifest.json") != manifest["parent_manifest_sha256"]:
        raise ValueError("Changed parent provenance")
    if not parent_report(directory / "hepatic")["passed"]:
        raise ValueError("Parent numerical criteria failed")
    for prefix in ("", "repeat/"):
        worker = read(directory / prefix / "worker.json")
        if worker["status"] != "completed" or worker["failures"]:
            raise ValueError("Failed observation worker")
        rt = worker["runtime"]
        if any(rt[k] != p["runtime"][k] for k in ("numpy", "scipy")) or not rt["python"].startswith(
            p["runtime"]["python"] + "."
        ):
            raise ValueError("Wrong observation runtime")
    changed = [
        f
        for f in sorted(numerical_files(names))
        if digest(directory / f) != digest(directory / "repeat" / f)
    ]
    summaries = {}
    metrics = {k: 0.0 for k in p["criteria"] if k != "sampling_ratio_floor_pmol_l"}
    for name in names:
        item = read(directory / f"cases/{name}.json")
        if item["id"] != name:
            raise ValueError("Mislabeled observation case")
        result = assess_case(p, item, source(directory, name), source(directory, name, "tight"))
        summaries[name] = result
        for k, v in result["checks"].items():
            metrics[k] = max(metrics[k], v)
    metrics["repeat_artifact_differences"] = len(changed)
    checks = {
        k: {"value": v, "limit": p["criteria"][k], "passed": v <= p["criteria"][k]}
        for k, v in metrics.items()
    }
    return {
        "schema": VERSION,
        "protocol": p["id"],
        "claim": p["claim"],
        "passed": manifest["status"] != "failed" and all(c["passed"] for c in checks.values()),
        "expected_cases": 24,
        "completed_cases": len(summaries),
        "checks": checks,
        "cases": summaries,
        "repeat_changed_files": changed,
        "limitations": p["excluded"],
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("directory", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--allow-failed", action="store_true")
    args = parser.parse_args()
    if args.output.exists():
        raise FileExistsError(args.output)
    dump(args.output, reconstruct(args.directory, allow_failed=args.allow_failed))
