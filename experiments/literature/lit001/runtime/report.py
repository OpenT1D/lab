"""Reconstruct the LIT-001 numeric report with only the Python standard library."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
from pathlib import Path


def reconstruct(directory: Path) -> dict:
    manifest = json.loads((directory / "manifest.json").read_text())
    if manifest["status"] != "completed":
        raise ValueError("Cannot reconstruct a completed report from a failed run")
    for filename, expected in manifest["files"].items():
        if Path(filename).name != filename:
            raise ValueError("Artifact name must be local")
        if hashlib.sha256((directory / filename).read_bytes()).hexdigest() != expected:
            raise ValueError(f"Changed artifact: {filename}")
    protocol = json.loads((directory / "protocol.json").read_text())
    with (directory / "trace.csv").open(newline="") as stream:
        rows = [{key: float(value) for key, value in row.items()} for row in csv.DictReader(stream)]
    if not rows or any(not math.isfinite(x) for row in rows for x in row.values()):
        raise ValueError("Missing/nonfinite trace")
    intervals = [right["time_min"] - left["time_min"] for left, right in zip(rows, rows[1:])]
    if any(dt <= 0 for dt in intervals):
        raise ValueError("Non-increasing time")
    if rows[0]["time_min"] != 0 or rows[-1]["time_min"] != protocol["horizon_min"]:
        raise ValueError("Incomplete time horizon")
    peak = max(rows, key=lambda row: row["analytic_mU_per_L"])
    dose = protocol["dose_U_per_kg"] * 1000
    errors = {
        name: max(abs(row[name] - row["analytic_mU_per_L"]) for row in rows)
        for name in ("rk45_coarse_mU_per_L", "rk45_tight_mU_per_L", "dop853_mU_per_L")
    }
    mass_error = max(
        abs(sum(row[k] for k in ("sc1", "sc2", "plasma", "eliminated", "pending")) - dose)
        for row in rows
    )
    minimum = min(row[k] for row in rows for k in ("sc1", "sc2", "plasma", "eliminated"))
    auc = sum(
        (left["analytic_mU_per_L"] + right["analytic_mU_per_L"]) * dt / 2
        for left, right, dt in zip(rows, rows[1:], intervals)
    )
    limits = protocol["criteria"]
    passed = (
        errors["rk45_tight_mU_per_L"] <= limits["max_concentration_error_mU_per_L"]
        and errors["dop853_mU_per_L"] <= limits["max_concentration_error_mU_per_L"]
        and mass_error <= limits["max_mass_error_mU_per_kg"]
        and minimum >= -limits["negative_state_tolerance_mU_per_kg"]
    )
    return {
        "schema": "lit001-numerical-report/1",
        "claim": protocol["claim"],
        "passed_numerical_criteria": passed,
        "time_points": len(rows),
        "horizon_min": protocol["horizon_min"],
        "sampled_peak_mU_per_L": peak["analytic_mU_per_L"],
        "sampled_peak_time_min": peak["time_min"],
        "trapezoid_auc_mU_min_per_L": auc,
        "max_absolute_error_mU_per_L": errors,
        "mass_error_mU_per_kg": mass_error,
        "minimum_numerical_state_mU_per_kg": minimum,
        "empirical_validation": "not_performed",
        "published_cohort_figure_reproduction": "not_performed_missing_inputs",
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("directory", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    with args.output.open("x") as stream:
        stream.write(json.dumps(reconstruct(args.directory), indent=2) + "\n")
