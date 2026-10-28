"""Reconstruct BC-001 metrics using only archived artifacts and the standard library."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
from pathlib import Path

DATA_FILES = (
    "protocol.json",
    "input.csv",
    "trace.csv",
    "reference-functions.csv",
    "verification.json",
)
SOURCE_FILES = (
    "model.py",
    "verify.py",
    "test_model.py",
    "run.py",
    "report.py",
    "plot.py",
    "pyproject.toml",
    "uv.lock",
)
TRACE_COLUMNS = (
    "time_min",
    "glucose_mmol_per_L",
    "x_ug",
    "y_ug_per_min",
    "secretion_ug_per_min",
    "coarse_ug_per_min",
    "tight_ug_per_min",
    "capacity_0_ug_per_min",
    "capacity_0.25_ug_per_min",
    "capacity_0.5_ug_per_min",
    "capacity_1_ug_per_min",
    "alternative_initialization_ug_per_min",
)


def dump(path: Path, value: object) -> None:
    path.write_text(json.dumps(value, indent=2, allow_nan=False) + "\n")


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read_table(path: Path, columns: tuple[str, ...]) -> list[dict[str, float]]:
    with path.open(newline="") as stream:
        reader = csv.DictReader(stream)
        if tuple(reader.fieldnames or ()) != columns:
            raise ValueError(f"Unexpected columns: {path.name}")
        rows = [{k: float(v) for k, v in row.items()} for row in reader]
    if not rows or any(not math.isfinite(v) for row in rows for v in row.values()):
        raise ValueError(f"Missing/nonfinite values: {path.name}")
    return rows


REQUIRED_CHECKS = (
    "solver_sensitivity",
    "deterministic_repeat",
    "capacity_linearity",
    "zero_capacity",
    "basal_threshold",
    "positivity",
    "constant_forcing_closed_form",
    "glucose_conversion",
    "published_algebraic_relationships",
    "initialization",
    "capacity_amplitude_confounding",
    "invalid_input_rejection",
    "local_sensitivity_finite",
)


def validate_verification(value: dict, protocol: dict) -> bool:
    """Recheck recorded measurements against the protocol, not just a saved pass flag."""
    checks = value.get("checks", {})
    if set(checks) != set(REQUIRED_CHECKS):
        raise ValueError("Missing or unexpected verification checks")

    def finite_tree(item, key=None):
        if isinstance(item, bool) and key != "passed":
            raise ValueError("Boolean used as verification measurement")
        if isinstance(item, float) and not math.isfinite(item):
            raise ValueError("Nonfinite verification measurement")
        if isinstance(item, dict):
            for name, child in item.items():
                finite_tree(child, name)
        if isinstance(item, list):
            for child in item:
                finite_tree(child)

    finite_tree(value)
    c = protocol["criteria"]
    try:
        tests = [value["passed"] is True, *(v["passed"] is True for v in checks.values())]
        for name, field, limit in (
            (
                "solver_sensitivity",
                "tight_reference_max_sr_error_ug_per_min",
                c["max_solver_secretion_error_ug_per_min"],
            ),
            ("deterministic_repeat", "maximum_absolute_state_error", c["repeat_absolute_error"]),
            ("capacity_linearity", "maximum_absolute_state_error", c["capacity_linearity_error"]),
            ("zero_capacity", "maximum_absolute_state", 0),
            ("basal_threshold", "maximum_absolute_state", 0),
            ("glucose_conversion", "maximum_absolute_state_error", 1e-12),
            ("initialization", "independent_expression_absolute_error", 1e-12),
            (
                "capacity_amplitude_confounding",
                "maximum_absolute_state_difference",
                c["capacity_linearity_error"],
            ),
        ):
            tests.append(0 <= checks[name][field] <= limit)
        errors = checks["constant_forcing_closed_form"]["maximum_absolute_state_errors"]
        if set(errors) != {"distinct_rates", "equal_rates", "nearly_equal_rates"}:
            raise ValueError("Missing constant-forcing cases")
        tests.extend(0 <= v <= c["constant_input_closed_form_error"] for v in errors.values())
        tests.append(checks["positivity"]["minimum_state"] >= -c["negative_state_tolerance"])
        rates = checks["published_algebraic_relationships"]
        tests.extend(
            0 <= rates[k] <= c["reference_grid_absolute_error"]
            for k in ("maximum_independent_expression_error", "asymptote_absolute_error")
        )
        low, high = c["published_delay_min_bounds"]
        tests.append(
            low <= rates["minimum_grid_delay_min"] <= rates["maximum_grid_delay_min"] <= high
        )
        tests.append(checks["glucose_conversion"]["anchor_90_mg_dl_in_mmol_l"] == 5)
        rejection = checks["invalid_input_rejection"]
        tests.append(
            rejection["attempted"] >= 10 and rejection["rejected"] == rejection["attempted"]
        )
        if set(value["sensitivity"]) != set(protocol["sensitivity"]["parameters"]):
            raise ValueError("Missing sensitivity cases")
        for case in value["sensitivity"].values():
            if set(case) != {"minus_auc_ug", "plus_auc_ug", "normalized_central_sensitivity"}:
                raise ValueError("Missing sensitivity measurements")
            tests.append(
                all(isinstance(v, (float, int)) and not isinstance(v, bool) for v in case.values())
            )
    except (KeyError, TypeError) as exc:
        raise ValueError("Incomplete verification measurements") from exc
    return all(tests)


def reconstruct(directory: Path, *, allow_pending: bool = False) -> dict:
    manifest = json.loads((directory / "manifest.json").read_text())
    accepted_status = {"completed", "calculated"} if allow_pending else {"completed"}
    if (
        manifest.get("schema") != "m4-beta-cell-run/1"
        or manifest.get("status") not in accepted_status
    ):
        raise ValueError("A complete BC-001 manifest is required; inspect errors for failed runs")
    required = {*DATA_FILES, *(f"source-{name}" for name in SOURCE_FILES)}
    if not allow_pending:
        required.update(("report.json", "figure.svg"))
    files = manifest.get("files", {})
    if not required.issubset(files):
        raise ValueError("Manifest omits required artifacts")
    for name, expected in files.items():
        path = directory / name
        if Path(name).name != name or path.is_symlink() or not path.is_file():
            raise ValueError(f"Invalid/missing local artifact: {name}")
        if sha256(path) != expected:
            raise ValueError(f"Changed artifact: {name}")
    p = json.loads((directory / "protocol.json").read_text())
    rows = read_table(directory / "trace.csv", TRACE_COLUMNS)
    inputs = read_table(directory / "input.csv", ("time_min", "glucose_mmol_per_L"))
    step, horizon = p["sample_step_min"], p["horizon_min"]
    expected_count = round(horizon / step) + 1
    if len(rows) != expected_count or len(inputs) != expected_count:
        raise ValueError("Incomplete output grid")
    for i, (row, inp) in enumerate(zip(rows, inputs)):
        if abs(row["time_min"] - i * step) > 1e-10 or row["time_min"] != inp["time_min"]:
            raise ValueError("Invalid output time grid")
        if row["glucose_mmol_per_L"] != inp["glucose_mmol_per_L"]:
            raise ValueError("Input/output glucose differs")
    if abs(rows[-1]["time_min"] - horizon) > 1e-10:
        raise ValueError("Incomplete time horizon")
    functions = read_table(
        directory / "reference-functions.csv",
        ("glucose_mmol_per_L", "rho_per_min", "y_infinity_ug_per_min", "delay_min"),
    )
    grid = p["reference_glucose_grid"]
    if len(functions) != round((grid["stop"] - grid["start"]) / grid["step"]) + 1:
        raise ValueError("Incomplete published-function grid")
    for i, row in enumerate(functions):
        if abs(row["glucose_mmol_per_L"] - (grid["start"] + i * grid["step"])) > 1e-10:
            raise ValueError("Invalid published-function grid")
        if row["rho_per_min"] <= 0 or abs(row["rho_per_min"] * row["delay_min"] - 1) > 1e-12:
            raise ValueError("Invalid delay")
        low, high = p["criteria"]["published_delay_min_bounds"]
        if not low <= row["delay_min"] <= high or row["y_infinity_ug_per_min"] < 0:
            raise ValueError("Invalid published-function range")
    verification = json.loads((directory / "verification.json").read_text())
    errors = {
        name: max(abs(row[f"{name}_ug_per_min"] - row["secretion_ug_per_min"]) for row in rows)
        for name in ("coarse", "tight")
    }
    auc = math.fsum(
        (a["secretion_ug_per_min"] + b["secretion_ug_per_min"])
        * (b["time_min"] - a["time_min"])
        / 2
        for a, b in zip(rows, rows[1:])
    )
    peak = max(rows, key=lambda row: row["secretion_ug_per_min"])
    capacity_error = max(
        abs(row[f"capacity_{capacity:g}_ug_per_min"] - capacity * row["secretion_ug_per_min"])
        for row in rows
        for capacity in p["capacity_values"]
    )
    output_error = max(
        abs(row["secretion_ug_per_min"] - p["parameters"]["m"] * row["x_ug"]) for row in rows
    )
    min_state = min(
        row[key] for row in rows for key in ("x_ug", "y_ug_per_min", "secretion_ug_per_min")
    )
    passed = (
        validate_verification(verification, p)
        and errors["tight"] <= p["criteria"]["max_solver_secretion_error_ug_per_min"]
        and capacity_error <= p["criteria"]["capacity_linearity_error"]
        and min_state >= -p["criteria"]["negative_state_tolerance"]
        and output_error <= 1e-12
    )
    return {
        "schema": "m4-beta-cell-report/1",
        "protocol": p["id"],
        "claim": p["claim"],
        "passed": passed,
        "time_points": len(rows),
        "horizon_min": horizon,
        "initial_x_ug": rows[0]["x_ug"],
        "initial_y_ug_per_min": rows[0]["y_ug_per_min"],
        "sampled_peak_evoked_secretion_ug_per_min": peak["secretion_ug_per_min"],
        "sampled_peak_time_min": peak["time_min"],
        "trapezoid_evoked_secretion_auc_ug": auc,
        "solver_max_absolute_secretion_error_ug_per_min": errors,
        "capacity_max_absolute_error_ug_per_min": capacity_error,
        "minimum_state": min_state,
        "reference_delay_range_min": [
            min(r["delay_min"] for r in functions),
            max(r["delay_min"] for r in functions),
        ],
        "verification": verification,
        "empirical_evaluation": p["empirical_evaluation"],
        "published_dynamic_figure_reproduction": p["published_dynamic_figure_reproduction"],
        "theoretical_reference": (
            "Figure 2c/d functions and approximately 12-minute delay; no digitized cohort result"
        ),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("directory", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = reconstruct(args.directory)
    with args.output.open("x") as stream:
        stream.write(json.dumps(result, indent=2, allow_nan=False) + "\n")
    if not result["passed"]:
        raise SystemExit("Reconstructed numerical criteria failed")


if __name__ == "__main__":
    main()
