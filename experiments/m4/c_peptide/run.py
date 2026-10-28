"""Durable, reproducible BC-003 execution in the existing locked numerical runtime."""

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

from experiments.m4.kinetic_inlet.forcing import Forcing

from .identify import analyze
from .model import VERSION, Parameters, initial_state, simulate
from .reference import constant_schedule, one_compartment
from .report import COLUMNS, SCHEMA, SOURCES, digest, dump, reconstruct, validate_protocol
from .verify import verify

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]


def hashes(output):
    return {
        p.name: digest(p)
        for p in sorted(output.iterdir())
        if p.is_file() and p.name != "manifest.json"
    }


def execute(protocol_path, output):
    output.mkdir(parents=True, exist_ok=False)
    manifest = {
        "schema": SCHEMA,
        "status": "started",
        "model": VERSION,
        "started_utc": datetime.now(UTC).isoformat(),
        "files": {},
        "runtime": {
            "matplotlib": matplotlib.__version__,
            "python": platform.python_version(),
            "numpy": np.__version__,
            "scipy": scipy.__version__,
        },
    }
    dump(output / "manifest.json", manifest)
    try:
        manifest["git_head"] = subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=HERE, text=True
        ).strip()
        manifest["git_dirty"] = bool(
            subprocess.check_output(["git", "status", "--porcelain"], cwd=HERE)
        )
        for name in SOURCES:
            shutil.copyfile(HERE / name, output / f"source-{name}")
        shutil.copyfile(
            ROOT / "experiments/m4/kinetic_inlet/forcing.py", output / "source-forcing.py"
        )
        for name in ("uv.lock", "pyproject.toml"):
            shutil.copyfile(
                ROOT / "experiments/m4/beta_cell/runtime" / name, output / f"runtime-{name}"
            )
        shutil.copyfile(protocol_path, output / "protocol.json")
        protocol = json.loads((output / "protocol.json").read_text())
        validate_protocol(protocol)
        parameters = {name: Parameters(**values) for name, values in protocol["profiles"].items()}
        runs, inputs = {}, {}
        for profile, params in parameters.items():
            for case in protocol["cases"]:
                name = f"{profile}--{case['name']}"
                forcing = Forcing(**case["input"])
                count = round(forcing.horizon / protocol["sample_step_min"])
                times = np.linspace(0, forcing.horizon, count + 1)
                initial = initial_state(case["initial"], params)
                states = {
                    s["name"]: simulate(times, params, forcing, initial, s)
                    for s in protocol["solvers"]
                }
                analytical = constant_schedule(times, params, forcing, initial)
                simple = one_compartment(times, params, forcing, initial[0])
                values = np.column_stack(
                    (
                        times,
                        [forcing.evaluate(t) for t in times],
                        states["reference"],
                        states["reference"][:, 0] / params.volume_l_kg,
                        analytical,
                        states["coarse"][:, 0] / params.volume_l_kg,
                        states["tight"][:, 0] / params.volume_l_kg,
                        simple,
                    )
                )
                with (output / f"{name}.csv").open("x", newline="") as stream:
                    writer = csv.writer(stream)
                    writer.writerow(COLUMNS)
                    writer.writerows(values)
                inputs[name] = {
                    "forcing": forcing.to_dict(),
                    "initial": initial.tolist(),
                    "evidence": case["evidence"],
                }
                runs[name] = {
                    "name": case["name"],
                    "times": times,
                    "forcing": forcing,
                    "initial": initial,
                    "states": states,
                    "analytical": analytical,
                    "params": params,
                }
        dump(output / "inputs.json", inputs)
        identification = analyze(protocol)
        dump(output / "identifiability.json", identification)
        checks = verify(protocol, runs, identification, parameters)
        dump(output / "verification.json", checks)
        if not checks["passed"]:
            raise RuntimeError("BC-003 criteria failed; inspect verification.json")
        manifest.update(status="calculated", files=hashes(output))
        dump(output / "manifest.json", manifest)
        result = reconstruct(output, allow_pending=True)
        if not result["passed"]:
            raise RuntimeError("Artifact reconstruction failed numerical criteria")
        dump(output / "report.json", result)
        from .plot import render

        render(output, output / "figure.svg", allow_pending=True)
        manifest.update(
            status="completed", finished_utc=datetime.now(UTC).isoformat(), files=hashes(output)
        )
        dump(output / "manifest.json", manifest)
        return result
    except BaseException as exc:
        manifest.update(
            status="failed",
            finished_utc=datetime.now(UTC).isoformat(),
            error={"type": type(exc).__name__, "message": str(exc)},
            files=hashes(output),
        )
        dump(output / "manifest.json", manifest)
        raise


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--protocol", type=Path, default=HERE / "protocol.json")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = execute(args.protocol, args.output)
    print(
        json.dumps(
            {"passed": result["passed"], "checks": result["verification"]["checks"]}, indent=2
        )
    )


if __name__ == "__main__":
    main()
