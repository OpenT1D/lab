"""BC-003 artifact-only reconstruction. Python standard library; no saved code execution."""

import argparse
import csv
import hashlib
import json
import math
from bisect import bisect_right
from pathlib import Path

SCHEMA = "bc003-run/1"
SOURCES = (
    "model.py",
    "reference.py",
    "identify.py",
    "verify.py",
    "run.py",
    "report.py",
    "plot.py",
    "test_model.py",
)
COLUMNS = (
    "time_min",
    "input_pmol_kg_min",
    "central_pmol_kg",
    "peripheral_pmol_kg",
    "eliminated_pmol_kg",
    "delivered_pmol_kg",
    "cpeptide_pmol_l",
    "analytical_pmol_l",
    "coarse_pmol_l",
    "tight_pmol_l",
    "one_compartment_pmol_l",
)
CHECKS = {
    "analytical_agreement": "max_concentration_error_pmol_l",
    "solver_sensitivity": "max_concentration_error_pmol_l",
    "mass_balance": "max_mass_balance_error_pmol_kg",
    "input_accounting": "max_input_amount_error_pmol_kg",
    "positivity": "negative_state_tolerance_pmol_kg",
    "zero_input": None,
    "repeatability": "repeat_state_error",
    "equilibrium": "max_equilibrium_state_error_pmol_kg",
    "one_compartment_limit": "max_one_compartment_error_pmol_l",
    "unit_conversion": "max_unit_conversion_relative_error",
    "synthetic_recovery": "max_synthetic_recovery_relative_error",
    "synthetic_fit": "max_synthetic_fit_error_pmol_l",
    "sensitivity_refinement": "max_sensitivity_refinement_relative_error",
    "scale_confounding": "max_scale_confounding_error_pmol_l",
    "identifiability_ranks": None,
}


def dump(path, value):
    Path(path).write_text(json.dumps(value, indent=2, allow_nan=False) + "\n")


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def finite(value, name="value", *, positive=False):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        raise ValueError(f"Missing/nonfinite numeric {name}")
    if (value <= 0) if positive else (value < 0):
        raise ValueError(f"Invalid sign for {name}")
    return value


def read_json(path):
    return json.loads(
        Path(path).read_text(),
        parse_constant=lambda value: (_ for _ in ()).throw(ValueError(f"Nonfinite JSON {value}")),
    )


def grid(case, step):
    horizon = case["input"]["edges"][-1]
    count = round(horizon / step)
    return [i * step for i in range(count + 1)]


def initial(spec, params):
    if spec == {"kind": "zero"}:
        return [0.0] * 4
    if spec.get("kind") == "bolus" and set(spec) == {"kind", "dose_pmol_kg"}:
        return [finite(spec["dose_pmol_kg"]), 0, 0, 0]
    if spec.get("kind") == "equilibrium" and set(spec) == {"kind", "basal_q_pmol_kg_min"}:
        central = finite(spec["basal_q_pmol_kg_min"]) / params["k3"]
        return [central, params["k1"] / params["k2"] * central, 0, 0]
    raise ValueError("Invalid initial-state specification")


def validate_protocol(p):
    if (
        p.get("schema") != "bc003-protocol/1"
        or p.get("id") != "BC-003/1"
        or p.get("model") != "polonsky1986-forward-cpeptide/1"
    ):
        raise ValueError("Unsupported BC-003 protocol or model")
    if p["units"] != {
        "time": "min",
        "amounts": "pmol/kg",
        "appearance": "pmol/(kg min)",
        "volume": "L/kg",
        "concentration": "pmol/L",
        "rates": "1/min",
    }:
        raise ValueError("Unsupported units")
    if p["state_order"] != ["central", "peripheral", "eliminated", "delivered_since_start"]:
        raise ValueError("Unsupported state order")
    if set(p["profiles"]) != {"normal_mean", "t1d_mean"}:
        raise ValueError("Both declared nominal profiles are required")
    for values in p["profiles"].values():
        if set(values) != {"k1", "k2", "k3", "volume_l_kg"}:
            raise ValueError("Incomplete kinetic parameters")
        for key, value in values.items():
            finite(value, key, positive=key != "k1")
    step = finite(p["sample_step_min"], positive=True)
    if len(p["cases"]) != 4 or {c["name"] for c in p["cases"]} != {
        "bolus",
        "step",
        "basal_pulse",
        "zero",
    }:
        raise ValueError("Incomplete or duplicate case matrix")
    for case in p["cases"]:
        spec = case["input"]
        if set(spec) != {"edges", "left", "right"} or len(spec["edges"]) < 2:
            raise ValueError("Incomplete forcing")
        edges, rates = spec["edges"], spec["left"]
        for value in [*edges, *rates, *spec["right"]]:
            finite(value)
        if edges[0] != 0 or any(b <= a for a, b in zip(edges, edges[1:])):
            raise ValueError("Invalid forcing edges")
        if len(rates) != len(edges) - 1 or rates != spec["right"]:
            raise ValueError("BC-003 reference requires constant input segments")
        count = edges[-1] / step
        if count < 1 or count > 100000 or count != round(count):
            raise ValueError("Incomplete reporting grid")
        for params in p["profiles"].values():
            initial(case["initial"], params)
        if case["name"] == "zero" and (any(rates) or case["initial"] != {"kind": "zero"}):
            raise ValueError("Zero case must have zero input and inventories")
    if [s["name"] for s in p["solvers"]] != ["coarse", "tight", "reference"]:
        raise ValueError("Missing solver comparison")
    for settings in p["solvers"]:
        if set(settings) != {"name", "method", "rtol", "atol", "max_step"} or settings[
            "method"
        ] not in {"RK45", "DOP853"}:
            raise ValueError("Unsupported solver settings")
        for key in ("rtol", "atol", "max_step"):
            finite(settings[key], positive=True)
        if settings["rtol"] >= 1:
            raise ValueError("Invalid relative tolerance")
    if set(p["criteria"]) != {v for v in CHECKS.values() if v is not None}:
        raise ValueError("Missing or unexpected acceptance criteria")
    for value in p["criteria"].values():
        finite(value)
    spec = p["identifiability"]
    if (
        spec["parameter_order"] != ["k1", "k2", "k3", "volume_l_kg"]
        or spec["profile"] not in p["profiles"]
    ):
        raise ValueError("Invalid identification parameter definition")
    finite(spec["dose_pmol_kg"], positive=True)
    finite(spec["rank_relative_threshold"], positive=True)
    if spec["rank_relative_threshold"] >= 1:
        raise ValueError("Invalid rank threshold")
    for name in ("times_min", "early_times_min", "sparse_times_min"):
        times = spec[name]
        if len(times) < 3 or any(b <= a for a, b in zip(times, times[1:])):
            raise ValueError("Invalid synthetic observation times")
        for time in times:
            finite(time)
    if (
        len(spec["recovery_start_factors"]) != 2
        or len(spec["finite_difference_steps"]) != 2
        or len(spec["confounding_factors"]) != 2
    ):
        raise ValueError("Incomplete synthetic design")
    for factors in spec["recovery_start_factors"]:
        if len(factors) != 4:
            raise ValueError("Invalid recovery start")
        for factor in factors:
            finite(factor, positive=True)
    for value in [
        *spec["bound_factors"],
        *spec["finite_difference_steps"],
        *spec["confounding_factors"],
    ]:
        finite(value, positive=True)
    if (
        len(spec["bound_factors"]) != 2
        or not spec["bound_factors"][0] < 1 < spec["bound_factors"][1]
    ):
        raise ValueError("Invalid recovery bounds")


def table(path):
    with Path(path).open(newline="") as stream:
        reader = csv.DictReader(stream)
        if tuple(reader.fieldnames or ()) != COLUMNS:
            raise ValueError("Invalid C-peptide trace columns")
        rows = [{key: float(value) for key, value in row.items()} for row in reader]
    if not rows or any(not math.isfinite(value) for row in rows for value in row.values()):
        raise ValueError("Empty/nonfinite trace")
    return rows


def identification_summary(data, protocol):
    spec, criteria = protocol["identifiability"], protocol["criteria"]
    if (
        data.get("schema") != "bc003-synthetic-identifiability/1"
        or data["times_min"] != spec["times_min"]
        or data["parameter_order"] != spec["parameter_order"]
        or data["dose_pmol_kg"] != spec["dose_pmol_kg"]
    ):
        raise ValueError("Mismatched synthetic identification design")
    nominal = [protocol["profiles"][spec["profile"]][k] for k in spec["parameter_order"]]
    if data["nominal_parameters"] != nominal or len(data["observations_pmol_l"]) != len(
        spec["times_min"]
    ):
        raise ValueError("Incomplete synthetic observations")
    for value in data["observations_pmol_l"]:
        finite(value)
    for name, columns in (("sensitivity_matrix_pmol_l", 4), ("joint_sensitivity_matrix_pmol_l", 5)):
        matrix = data[name]
        if len(matrix) != len(spec["times_min"]) or any(len(row) != columns for row in matrix):
            raise ValueError("Incomplete sensitivity matrix")
        if any(
            isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v)
            for row in matrix
            for v in row
        ):
            raise ValueError("Nonfinite sensitivity")
    if len(data["fits"]) != len(spec["recovery_start_factors"]):
        raise ValueError("Missing synthetic recovery start")
    errors, residuals = [], []
    for fit, start in zip(data["fits"], spec["recovery_start_factors"]):
        if (
            fit["start_factors"] != start
            or len(fit["estimated_parameters"]) != 4
            or len(fit["predictions_pmol_l"]) != len(spec["times_min"])
        ):
            raise ValueError("Incomplete synthetic fit")
        errors.append(
            max(
                abs(finite(a, positive=True) / b - 1)
                for a, b in zip(fit["estimated_parameters"], nominal)
            )
        )
        residuals.append(
            max(
                abs(finite(a) - b)
                for a, b in zip(fit["predictions_pmol_l"], data["observations_pmol_l"])
            )
        )
    design_shapes = {
        "full_known_input": (len(spec["times_min"]), 4),
        "full_unknown_amplitude": (len(spec["times_min"]), 5),
        "early_known_input": (len(spec["early_times_min"]), 4),
        "sparse_known_input": (len(spec["sparse_times_min"]), 4),
    }
    if set(data["designs"]) != set(design_shapes):
        raise ValueError("Missing observation design")
    ranks = {}
    for name, (rows, cols) in design_shapes.items():
        item = data["designs"][name]
        values = item["singular_values_pmol_l"]
        if item["rows"] != rows or item["columns"] != cols or len(values) != min(rows, cols):
            raise ValueError("Incomplete singular spectrum")
        for value in values:
            finite(value)
        if values[0] <= 0 or values != sorted(values, reverse=True):
            raise ValueError("Invalid singular spectrum")
        ranks[name] = sum(value > values[0] * spec["rank_relative_threshold"] for value in values)
        if ranks[name] != item["rank"]:
            raise ValueError("Stored sensitivity rank is inconsistent")
    refinement = finite(data["sensitivity_refinement_relative_error"])
    confounding = data["amplitude_volume_confounding"]
    if [c["factor"] for c in confounding] != spec["confounding_factors"]:
        raise ValueError("Incomplete amplitude/volume experiment")
    scale_error = max(finite(c["max_concentration_difference_pmol_l"]) for c in confounding)
    return {
        "max_parameter_error": max(errors),
        "max_fit_residual_pmol_l": max(residuals),
        "sensitivity_refinement_relative_error": refinement,
        "max_scale_confounding_error_pmol_l": scale_error,
        "ranks": ranks,
        "passed": max(errors) <= criteria["max_synthetic_recovery_relative_error"]
        and max(residuals) <= criteria["max_synthetic_fit_error_pmol_l"]
        and ranks["full_known_input"] == 4
        and ranks["full_unknown_amplitude"] == 4
        and ranks["sparse_known_input"] <= 3
        and refinement <= criteria["max_sensitivity_refinement_relative_error"]
        and scale_error <= criteria["max_scale_confounding_error_pmol_l"],
    }


def reconstruct(directory, *, allow_pending=False):
    directory = Path(directory)
    manifest = read_json(directory / "manifest.json")
    statuses = {"completed", "calculated"} if allow_pending else {"completed"}
    if manifest.get("schema") != SCHEMA or manifest.get("status") not in statuses:
        raise ValueError("BC-003 attempt is not complete")
    required = {
        "protocol.json",
        "inputs.json",
        "identifiability.json",
        "verification.json",
        "source-forcing.py",
        "runtime-uv.lock",
        "runtime-pyproject.toml",
        *(f"source-{name}" for name in SOURCES),
    }
    if not allow_pending:
        required |= {"report.json", "figure.svg"}
    files = manifest.get("files", {})
    if not required.issubset(files):
        raise ValueError("Missing required artifacts")
    for name, expected in files.items():
        path = Path(name)
        if path.is_absolute() or path.name != name or name in {".", ".."}:
            raise ValueError("Unsafe artifact path")
        path = directory / name
        if path.is_symlink() or not path.is_file() or digest(path) != expected:
            raise ValueError(f"Changed/missing artifact: {name}")
    p = read_json(directory / "protocol.json")
    validate_protocol(p)
    if manifest.get("model") != p["model"]:
        raise ValueError("Manifest model disagrees with protocol")
    criteria = p["criteria"]
    v = read_json(directory / "verification.json")
    if (
        v.get("schema") != "bc003-verification/1"
        or v.get("protocol") != p["id"]
        or set(v.get("checks", {})) != set(CHECKS)
    ):
        raise ValueError("Missing verification groups or wrong protocol")
    passed = v.get("passed") is True
    for name, criterion in CHECKS.items():
        item = v["checks"][name]
        limit = criteria[criterion] if criterion else 0
        passed &= item.get("passed") is True and finite(item.get("value"), name) <= limit
    inputs = read_json(directory / "inputs.json")
    expected_names = {
        f"{profile}--{case['name']}" for profile in p["profiles"] for case in p["cases"]
    }
    if set(inputs) != expected_names or not {f"{name}.csv" for name in expected_names}.issubset(
        files
    ):
        raise ValueError("Incomplete profile/case matrix")
    summaries = {}
    for profile, params in p["profiles"].items():
        for case in p["cases"]:
            name = f"{profile}--{case['name']}"
            spec, initial_values = case["input"], initial(case["initial"], params)
            if inputs[name] != {
                "forcing": {**spec, "units": "pmol/(kg min)"},
                "initial": initial_values,
                "evidence": case["evidence"],
            }:
                raise ValueError("Archived forcing/initial state differs from protocol")
            rows = table(directory / f"{name}.csv")
            if [r["time_min"] for r in rows] != grid(case, p["sample_step_min"]):
                raise ValueError("Incomplete trace grid")
            if [rows[0][key] for key in COLUMNS[2:6]] != initial_values:
                raise ValueError("Incorrect initial state")
            balances, amounts, negatives, analytic, convergence, comparator = [], [], [], [], [], []
            for r in rows:
                t = r["time_min"]
                i = min(bisect_right(spec["edges"], t) - 1, len(spec["left"]) - 1)
                # The shared linear interpolator can round a constant segment by an ulp.
                if not math.isclose(
                    r["input_pmol_kg_min"], spec["left"][i], rel_tol=1e-14, abs_tol=1e-14
                ):
                    raise ValueError("Recorded input disagrees with forcing")
                delivered = math.fsum(
                    q * max(0, min(t, b) - a)
                    for a, b, q in zip(spec["edges"], spec["edges"][1:], spec["left"])
                )
                amounts.append(abs(delivered - r["delivered_pmol_kg"]))
                balances.append(
                    abs(
                        math.fsum(r[key] for key in COLUMNS[2:5])
                        - r["delivered_pmol_kg"]
                        - sum(initial_values[:2])
                    )
                )
                if abs(r["central_pmol_kg"] / params["volume_l_kg"] - r["cpeptide_pmol_l"]) > 1e-9:
                    raise ValueError("Concentration/volume conversion mismatch")
                negatives.append(max(0, -min(r[key] for key in COLUMNS[2:6])))
                analytic.append(
                    max(
                        abs(r[key] - r["analytical_pmol_l"])
                        for key in ("cpeptide_pmol_l", "tight_pmol_l")
                    )
                )
                convergence.append(abs(r["cpeptide_pmol_l"] - r["tight_pmol_l"]))
                comparator.append(abs(r["cpeptide_pmol_l"] - r["one_compartment_pmol_l"]))
            if case["name"] == "zero" and any(r[key] != 0 for r in rows for key in COLUMNS[1:]):
                raise ValueError("Zero input has nonzero outcomes")
            ok = (
                max(balances) <= criteria["max_mass_balance_error_pmol_kg"]
                and max(amounts) <= criteria["max_input_amount_error_pmol_kg"]
                and max(negatives) <= criteria["negative_state_tolerance_pmol_kg"]
                and max(analytic) <= criteria["max_concentration_error_pmol_l"]
                and max(convergence) <= criteria["max_concentration_error_pmol_l"]
            )
            passed &= ok
            summaries[name] = {
                "passed": ok,
                "evidence": case["evidence"],
                "sample_count": len(rows),
                "peak_sampled_cpeptide_pmol_l": max(r["cpeptide_pmol_l"] for r in rows),
                "initial_cpeptide_pmol_l": rows[0]["cpeptide_pmol_l"],
                "final_input_pmol_kg": rows[-1]["delivered_pmol_kg"],
                "max_mass_error_pmol_kg": max(balances),
                "max_input_error_pmol_kg": max(amounts),
                "max_analytical_error_pmol_l": max(analytic),
                "max_solver_difference_pmol_l": max(convergence),
                "max_one_compartment_difference_pmol_l": max(comparator),
            }
    identification = read_json(directory / "identifiability.json")
    identification_checks = identification_summary(identification, p)
    return {
        "schema": "bc003-report/1",
        "protocol": p["id"],
        "model": p["model"],
        "passed": bool(passed and identification_checks["passed"]),
        "cases": summaries,
        "verification": v,
        "identifiability": identification,
        "identifiability_reconstruction": identification_checks,
        "evidence": (
            "published equations/stimulus with nominal coefficients; "
            "synthetic observations; no cohort reproduction"
        ),
        "limitations": p["excluded_claims"],
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("directory", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = reconstruct(args.directory)
    with args.output.open("x") as stream:
        stream.write(json.dumps(result, indent=2, allow_nan=False) + "\n")
    if not result["passed"]:
        raise SystemExit("BC-003 criteria failed")


if __name__ == "__main__":
    main()
