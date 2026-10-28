"""BC-002 artifact validation and reconstruction; Python standard library only."""

import argparse
import csv
import hashlib
import json
import math
from pathlib import Path

SCHEMA = "bc002-run/1"
COLUMNS = (
    "time_min",
    "Ip_pmol_kg",
    "Il_pmol_kg",
    "hepatic_loss_pmol_kg",
    "peripheral_loss_pmol_kg",
    "input_pmol_kg",
    "plasma_pmol_l",
    "oracle_Ip_pmol_kg",
    "oracle_Il_pmol_kg",
    "oracle_plasma_pmol_l",
)
SOURCE_FILES = (
    "run.py",
    "report.py",
    "plot.py",
    "native.py",
    "forcing.py",
    "oracle.py",
    "verify.py",
    "test_native.py",
)
REQUIRED = {
    "protocol.json",
    "native-identity.json",
    "verification.json",
    "source-input.csv",
    "source-forcing.json",
    "source-liver.csv",
    "source-peripheral.csv",
    "matched-constant-liver.csv",
    "zero-liver.csv",
    "native-uv.lock",
    "native-pyproject.toml",
    *(f"source-{name}" for name in SOURCE_FILES),
}


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def dump(path, data):
    path.write_text(json.dumps(data, indent=2, allow_nan=False) + "\n")


def finite_tree(data):
    if isinstance(data, float) and not math.isfinite(data):
        raise ValueError("Nonfinite archived measurement")
    if isinstance(data, dict):
        for value in data.values():
            finite_tree(value)
    if isinstance(data, list):
        for value in data:
            finite_tree(value)


def table(path, columns):
    with path.open(newline="") as stream:
        reader = csv.DictReader(stream)
        if tuple(reader.fieldnames or ()) != columns:
            raise ValueError(f"Unexpected columns: {path.name}")
        rows = [{k: float(v) for k, v in row.items()} for row in reader]
    if not rows:
        raise ValueError("Empty trace")
    finite_tree(rows)
    return rows


REQUIRED_CHECKS = {
    "native_zero_extension",
    "primary_oracle_agreement",
    "primary_mass_balance",
    "primary_input_integrals",
    "positivity",
    "repeatability",
    "conversion_anchor",
    "source_oracle_agreement",
    "source_mass_balance",
    "communication_amount",
    "communication_refinement",
    "equal_area_baseline",
    "gain_linearity",
    "zero_gain",
    "route_contrast_resolution",
}


def validate_checks(verification, protocol):
    """Reevaluate archived measurements against protocol limits, not saved flags."""
    checks = verification.get("checks", {})
    if set(checks) != REQUIRED_CHECKS:
        raise ValueError("Missing or unexpected verification measurements")
    if (
        verification.get("schema") != "m4-kinetic-inlet-verification/1"
        or verification.get("protocol") != protocol["id"]
    ):
        raise ValueError("Verification belongs to an unsupported protocol")
    criteria = protocol["criteria"]
    outcomes = [verification.get("passed") is True]

    def measured(check, field):
        value = check.get(field)
        if (
            isinstance(value, bool)
            or not isinstance(value, (int, float))
            or not math.isfinite(value)
        ):
            raise ValueError(f"Missing/invalid measured {field}")
        return value

    def bounded(name, field, criterion):
        value = measured(checks[name], field)
        outcomes.append(0 <= value <= criteria[criterion])

    for name in REQUIRED_CHECKS:
        outcomes.append(checks[name].get("passed") is True)
    for name in ("primary_oracle_agreement", "source_oracle_agreement"):
        for field in ("max_insulin_state_error_pmol_kg", "max_plasma_error_pmol_l"):
            bounded(name, field, field)
    for name in ("primary_mass_balance", "primary_input_integrals", "source_mass_balance"):
        bounded(name, "max_error_pmol_kg", "max_mass_balance_error_pmol_kg")
    bounded("communication_amount", "max_error_pmol_kg", "max_communication_amount_error_pmol_kg")
    bounded("equal_area_baseline", "max_amount_error_pmol_kg", "max_mass_balance_error_pmol_kg")
    bounded("gain_linearity", "max_state_error_pmol_kg", "max_insulin_state_error_pmol_kg")
    bounded("repeatability", "max_absolute_state_error", "repeat_state_error")
    bounded("conversion_anchor", "relative_error", "conversion_relative_error")
    outcomes.append(measured(checks["zero_gain"], "max_absolute_state_pmol_kg") == 0)
    outcomes.append(
        measured(checks["positivity"], "minimum_state_pmol_kg")
        >= -criteria["negative_state_tolerance_pmol_kg"]
    )
    regression = checks["native_zero_extension"]
    bounded("native_zero_extension", "derivative_max_error", "native_zero_derivative_error")
    for field in ("trajectory_max_error", "fresh_max_error", "reset_max_error"):
        bounded("native_zero_extension", field, "native_zero_trajectory_error")
    if regression.get("states_per_sample") != 13 or regression.get("solver_successful") is not True:
        raise ValueError("Incomplete native zero-extension regression")
    routes = checks["communication_refinement"].get("routes", {})
    if set(routes) != {"liver", "peripheral"}:
        raise ValueError("Missing communication route")
    for item in routes.values():
        for field, criterion in (
            ("finest_error_pmol_l", "fine_communication_plasma_error_pmol_l"),
            ("fine_to_coarse_error_ratio", "fine_to_coarse_communication_error_ratio"),
        ):
            outcomes.append(0 <= measured(item, field) <= criteria[criterion])
    contrast = checks["route_contrast_resolution"]
    difference = measured(contrast, "max_route_contrast_pmol_l")
    error = measured(contrast, "max_numerical_error_pmol_l")
    outcomes.append(
        difference > 0
        and 0 <= error <= difference * criteria["numerical_error_fraction_of_route_contrast"]
    )
    return all(outcomes)


def reconstruct(directory, *, allow_pending=False):
    directory = Path(directory)
    manifest = json.loads((directory / "manifest.json").read_text())
    statuses = {"completed", "calculated"} if allow_pending else {"completed"}
    if manifest.get("schema") != SCHEMA or manifest.get("status") not in statuses:
        raise ValueError("BC-002 attempt is not complete")
    required = REQUIRED | (set() if allow_pending else {"report.json", "figure.svg"})
    files = manifest.get("files", {})
    if not required.issubset(files) or "bc001/manifest.json" not in files:
        raise ValueError("Missing required artifact declaration")
    for name, expected in files.items():
        p = Path(name)
        if (
            p.is_absolute()
            or ".." in p.parts
            or len(p.parts) > 2
            or (len(p.parts) == 2 and p.parts[0] != "bc001")
        ):
            raise ValueError("Invalid artifact path")
        path = directory / p
        if any((directory / Path(*p.parts[:i])).is_symlink() for i in range(1, len(p.parts) + 1)):
            raise ValueError("Symlink artifact is unsupported")
        if not path.is_file() or digest(path) != expected:
            raise ValueError(f"Missing/changed artifact: {name}")
    # Validate the nested archive using the original simulator-free BC-001 reader.
    from experiments.m4.beta_cell.runtime.report import reconstruct as source_report

    if not source_report(directory / "bc001")["passed"]:
        raise ValueError("BC-001 source fails its own criteria")
    protocol = json.loads((directory / "protocol.json").read_text())
    identity = json.loads((directory / "native-identity.json").read_text())
    verification = json.loads((directory / "verification.json").read_text())
    finite_tree(verification)
    passed_checks = validate_checks(verification, protocol)
    for field, key in (
        ("upstream_revision", "revision"),
        ("profile", "profile"),
        ("patient_file_sha256", "patient_file_sha256"),
        ("parameter_file_sha256", "parameter_file_sha256"),
    ):
        if identity.get(field) != protocol["upstream"][key]:
            raise ValueError("Native identity differs from the declared source")
    if protocol["initial_state"] != [0] * 5 or protocol["added_basal_pmol_kg_min"] != 0:
        raise ValueError("Unsupported nonzero incremental initial or basal state")
    horizon, step = protocol["horizon_min"], protocol["sample_step_min"]
    times = sorted(
        {i * step for i in range(round(horizon / step) + 1)}
        | set(protocol["additional_sample_times_min"])
    )
    native = identity["kinetic_parameters"]
    if not all(
        math.isfinite(native[k]) and native[k] > 0 for k in ("BW", "Vi", "m1", "m2", "m4", "m30")
    ):
        raise ValueError("Invalid native parameters")
    criteria = protocol["criteria"]
    cases = {}
    traces = {}
    for name in ("source-liver", "source-peripheral", "matched-constant-liver", "zero-liver"):
        rows = table(directory / f"{name}.csv", COLUMNS)
        if [r["time_min"] for r in rows] != times:
            raise ValueError("Incomplete or altered trace grid")
        if any(rows[0][k] != 0 for k in COLUMNS[1:]):
            raise ValueError("Incremental initial state must be zero")
        if name == "zero-liver" and any(r[k] != 0 for r in rows for k in COLUMNS[1:]):
            raise ValueError("Zero forcing must have zero incremental states")
        state_error = max(
            abs(r[k] - r[f"oracle_{k}"]) for r in rows for k in ("Ip_pmol_kg", "Il_pmol_kg")
        )
        mass_error = max(
            abs(
                r["Ip_pmol_kg"]
                + r["Il_pmol_kg"]
                + r["hepatic_loss_pmol_kg"]
                + r["peripheral_loss_pmol_kg"]
                - r["input_pmol_kg"]
            )
            for r in rows
        )
        minimum = min(r[k] for r in rows for k in COLUMNS[1:7])
        oracle_error = max(abs(r["plasma_pmol_l"] - r["oracle_plasma_pmol_l"]) for r in rows)
        if max(abs(r["Ip_pmol_kg"] / native["Vi"] - r["plasma_pmol_l"]) for r in rows) > 1e-10:
            raise ValueError("Plasma concentration is inconsistent with Vi")
        auc = math.fsum(
            (a["plasma_pmol_l"] + b["plasma_pmol_l"]) * (b["time_min"] - a["time_min"]) / 2
            for a, b in zip(rows, rows[1:])
        )
        cases[name] = {
            "peak_incremental_plasma_pmol_l": max(r["plasma_pmol_l"] for r in rows),
            "trapezoid_plasma_auc_pmol_min_l": auc,
            "final_input_pmol_kg": rows[-1]["input_pmol_kg"],
            "max_mass_balance_error_pmol_kg": mass_error,
            "max_oracle_plasma_error_pmol_l": oracle_error,
            "max_oracle_state_error_pmol_kg": state_error,
            "minimum_amount_pmol_kg": minimum,
            "passed": state_error <= criteria["max_insulin_state_error_pmol_kg"]
            and mass_error <= criteria["max_mass_balance_error_pmol_kg"]
            and oracle_error <= criteria["max_plasma_error_pmol_l"]
            and minimum >= -criteria["negative_state_tolerance_pmol_kg"],
        }
        traces[name] = rows
    source_rows = table(
        directory / "source-input.csv", ("time_min", "secretion_ug_per_min", "q_pmol_kg_min")
    )
    if (
        source_rows[0]["time_min"] != 0
        or source_rows[-1]["time_min"] != horizon
        or any(b["time_min"] <= a["time_min"] for a, b in zip(source_rows, source_rows[1:]))
    ):
        raise ValueError("Incomplete source forcing")
    with (directory / "bc001" / "trace.csv").open(newline="") as stream:
        original_source = list(csv.DictReader(stream))
    if [(r["time_min"], r["secretion_ug_per_min"]) for r in source_rows] != [
        (float(r["time_min"]), float(r["secretion_ug_per_min"])) for r in original_source
    ]:
        raise ValueError("Source forcing is not the complete archived BC-001 trace")
    expected_forcing = {
        "edges": [r["time_min"] for r in source_rows],
        "left": [r["q_pmol_kg_min"] for r in source_rows[:-1]],
        "right": [r["q_pmol_kg_min"] for r in source_rows[1:]],
        "units": "pmol/(kg min)",
    }
    if json.loads((directory / "source-forcing.json").read_text()) != expected_forcing:
        raise ValueError("Forcing declaration differs from converted source samples")
    factor = 1e6 / (protocol["trace_bridge"]["molar_mass_g_mol"] * native["BW"])
    if any(
        r["q_pmol_kg_min"] < 0
        or abs(r["q_pmol_kg_min"] - r["secretion_ug_per_min"] * factor) > 1e-12
        for r in source_rows
    ):
        raise ValueError("Invalid mass-to-mole conversion")
    source_amount = math.fsum(
        (a["q_pmol_kg_min"] + b["q_pmol_kg_min"]) * (b["time_min"] - a["time_min"]) / 2
        for a, b in zip(source_rows, source_rows[1:])
    )
    amount_error = max(
        abs(cases[k]["final_input_pmol_kg"] - source_amount)
        for k in ("source-liver", "source-peripheral", "matched-constant-liver")
    )
    contrast = max(
        abs(a["plasma_pmol_l"] - b["plasma_pmol_l"])
        for a, b in zip(traces["source-liver"], traces["source-peripheral"])
    )
    error = max(
        *(
            cases[k]["max_oracle_plasma_error_pmol_l"]
            for k in ("source-liver", "source-peripheral")
        ),
        *(
            item["finest_error_pmol_l"]
            for item in verification["checks"]["communication_refinement"]["routes"].values()
        ),
    )
    passed = (
        passed_checks
        and all(v["passed"] for v in cases.values())
        and amount_error <= criteria["max_communication_amount_error_pmol_kg"]
        and contrast > 0
        and error <= contrast * criteria["numerical_error_fraction_of_route_contrast"]
    )
    return {
        "schema": "bc002-report/1",
        "protocol": protocol["id"],
        "claim": protocol["claim"],
        "passed": passed,
        "cases": cases,
        "source_input_amount_pmol_kg": source_amount,
        "input_amount_comparison_error_pmol_kg": amount_error,
        "maximum_route_contrast_pmol_l": contrast,
        "numerical_error_fraction_of_route_contrast": error / contrast if contrast else None,
        "verification": verification,
        "limitations": protocol["excluded_claims"],
    }


def main():
    p = argparse.ArgumentParser()
    p.add_argument("directory", type=Path)
    p.add_argument("--output", type=Path, required=True)
    args = p.parse_args()
    result = reconstruct(args.directory)
    with args.output.open("x") as stream:
        stream.write(json.dumps(result, indent=2, allow_nan=False) + "\n")
    if not result["passed"]:
        raise SystemExit("BC-002 numerical criteria failed")


if __name__ == "__main__":
    main()
