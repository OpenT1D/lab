"""Execute the frozen standalone BC-001 reference; never changes a metabolic engine."""

from __future__ import annotations

import argparse
import csv
import json
import platform
import shutil
import subprocess
from datetime import UTC, datetime
from pathlib import Path

import matplotlib
import numpy as np
import scipy
from model import MODEL_VERSION, GlucoseInput, Parameters, algebraic, simulate
from report import SOURCE_FILES, TRACE_COLUMNS, dump, reconstruct, sha256
from verify import verify

HERE = Path(__file__).resolve().parent


def table(path: Path, columns: tuple[str, ...], values) -> None:
    with path.open("x", newline="") as stream:
        writer = csv.writer(stream)
        writer.writerow(columns)
        writer.writerows(values)


def checked_protocol(p: dict) -> None:
    if p["schema"] != "m4-beta-cell-protocol/1" or p["capacity_values"] != [0, 0.25, 0.5, 1]:
        raise ValueError("Unsupported protocol schema or capacity cases")
    if (
        p["initialization"]
        != "paper_equation_4_13_with_D0_equal_M_infinity_at_input_basal_divided_by_r_and_Y0_zero"
    ):
        raise ValueError("Unsupported initialization")
    for field in ("sample_step_min", "horizon_min"):
        if isinstance(p[field], bool) or not np.isfinite(p[field]) or p[field] <= 0:
            raise ValueError(f"Invalid {field}")
    count = p["horizon_min"] / p["sample_step_min"]
    if count > 100000 or abs(count - round(count)) > 1e-9:
        raise ValueError("Horizon must be an integer number of steps (at most 100000)")
    if [s["name"] for s in p["solvers"]] != ["coarse", "tight", "reference"]:
        raise ValueError("Expected coarse/tight/reference solvers")
    grid = p["reference_glucose_grid"]
    if grid != {"start": 0.0, "stop": 20.0, "step": 0.1}:
        raise ValueError("Published-function reference grid is frozen")


def execute(protocol_path: Path, output: Path) -> dict:
    output.mkdir(parents=True, exist_ok=False)
    manifest = {
        "schema": "m4-beta-cell-run/1",
        "model_version": MODEL_VERSION,
        "status": "started",
        "started_utc": datetime.now(UTC).isoformat(),
        "runtime": {
            "python": platform.python_version(),
            "numpy": np.__version__,
            "scipy": scipy.__version__,
            "matplotlib": matplotlib.__version__,
        },
        "files": {},
    }
    dump(output / "manifest.json", manifest)
    try:
        manifest["git_head"] = subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=HERE, text=True
        ).strip()
        manifest["git_branch"] = subprocess.check_output(
            ["git", "branch", "--show-current"], cwd=HERE, text=True
        ).strip()
        manifest["source_identity"] = (
            "Archived source hashes are authoritative for uncommitted implementation"
        )
        for name in SOURCE_FILES:
            shutil.copyfile(HERE / name, output / f"source-{name}")
        shutil.copyfile(protocol_path, output / "protocol.json")
        p = json.loads((output / "protocol.json").read_text())
        checked_protocol(p)
        params, glucose = Parameters(**p["parameters"]), GlucoseInput(**p["input"])
        times = np.linspace(0, p["horizon_min"], round(p["horizon_min"] / p["sample_step_min"]) + 1)
        table(
            output / "input.csv",
            ("time_min", "glucose_mmol_per_L"),
            zip(times, glucose(times), strict=True),
        )
        solved = {}
        for settings in p["solvers"]:
            solved[settings["name"]] = simulate(
                times, params, glucose, **{k: v for k, v in settings.items() if k != "name"}
            )
        settings = {k: v for k, v in p["solvers"][-1].items() if k != "name"}
        capacities = [
            simulate(times, params, glucose, capacity=c, **settings)[:, 0] * params.m
            for c in p["capacity_values"]
        ]
        alternative = (
            simulate(
                times,
                params,
                glucose,
                x0_override=p["initialization_alternative"]["x0_ug"],
                **settings,
            )[:, 0]
            * params.m
        )
        states = solved["reference"]
        values = np.column_stack(
            (
                times,
                glucose(times),
                states,
                states[:, 0] * params.m,
                solved["coarse"][:, 0] * params.m,
                solved["tight"][:, 0] * params.m,
                *capacities,
                alternative,
            )
        )
        table(output / "trace.csv", TRACE_COLUMNS, values)
        grid = np.linspace(0, 20, 201)
        rho, yinf = algebraic(grid, params)
        table(
            output / "reference-functions.csv",
            ("glucose_mmol_per_L", "rho_per_min", "y_infinity_ug_per_min", "delay_min"),
            zip(grid, rho, yinf, 1 / rho, strict=True),
        )
        verification = verify(p)
        dump(output / "verification.json", verification)
        manifest["files"] = {
            file.name: sha256(file)
            for file in sorted(output.iterdir())
            if file.name != "manifest.json"
        }
        if not verification["passed"]:
            raise RuntimeError("Prespecified verification failed; inspect verification.json")
        manifest.update(status="calculated")
        dump(output / "manifest.json", manifest)
        result = reconstruct(output, allow_pending=True)
        if not result["passed"]:
            raise RuntimeError("Artifact reconstruction criteria failed")
        dump(output / "report.json", result)
        from plot import render

        render(output, output / "figure.svg", allow_pending=True)
        manifest["files"].update(
            {name: sha256(output / name) for name in ("figure.svg", "report.json")}
        )
        manifest.update(status="completed", finished_utc=datetime.now(UTC).isoformat())
        dump(output / "manifest.json", manifest)
        return result
    except BaseException as exc:
        manifest.update(
            status="failed",
            finished_utc=datetime.now(UTC).isoformat(),
            error={"type": type(exc).__name__, "message": str(exc)},
        )
        manifest["files"] = {
            file.name: sha256(file)
            for file in sorted(output.iterdir())
            if file.is_file() and file.name != "manifest.json"
        }
        dump(output / "manifest.json", manifest)
        raise


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--protocol", type=Path, default=HERE.parent / "protocol.json")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = execute(args.protocol, args.output)
    print(
        json.dumps(
            {
                k: result[k]
                for k in (
                    "passed",
                    "initial_x_ug",
                    "sampled_peak_evoked_secretion_ug_per_min",
                    "trapezoid_evoked_secretion_auc_ug",
                    "solver_max_absolute_secretion_error_ug_per_min",
                )
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
