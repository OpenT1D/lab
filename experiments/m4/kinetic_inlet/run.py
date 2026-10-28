"""Run BC-002 against pinned native kinetics; preserve every attempted experiment."""

import argparse
import csv
import json
import platform
import shutil
import subprocess
from datetime import UTC, datetime
from pathlib import Path

import numpy as np
import scipy

from experiments.m4.beta_cell.runtime.report import reconstruct as source_report
from experiments.m4.kinetic_inlet.forcing import Forcing, from_source_samples
from experiments.m4.kinetic_inlet.native import load, simulate
from experiments.m4.kinetic_inlet.oracle import simulate as oracle
from experiments.m4.kinetic_inlet.report import (
    COLUMNS,
    SCHEMA,
    SOURCE_FILES,
    digest,
    dump,
    reconstruct,
)
from experiments.m4.kinetic_inlet.verify import verify

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]


def hashes(output):
    return {
        str(p.relative_to(output)): digest(p)
        for p in sorted(output.rglob("*"))
        if p.is_file() and p != output / "manifest.json"
    }


def write_table(path, columns, values):
    with path.open("x", newline="") as stream:
        writer = csv.writer(stream)
        writer.writerow(columns)
        writer.writerows(values)


def checked_protocol(p):
    if p["schema"] != "m4-kinetic-inlet-protocol/1" or p["id"] not in ("BC-002/1", "BC-002/2"):
        raise ValueError("Unsupported protocol")
    if p["initial_state"] != [0, 0, 0, 0, 0] or p["added_basal_pmol_kg_min"] != 0:
        raise ValueError("Only zero incremental inventories and baseline are supported")
    if p["routes"] != ["liver", "peripheral"]:
        raise ValueError("Expected explicit liver and peripheral routes")
    for name in ("horizon_min", "sample_step_min"):
        if isinstance(p[name], bool) or not np.isfinite(p[name]) or p[name] <= 0:
            raise ValueError(f"Invalid {name}")
    n = p["horizon_min"] / p["sample_step_min"]
    if n > 100000 or abs(n - round(n)) > 1e-12:
        raise ValueError("Invalid output grid")
    bridge = p["trace_bridge"]
    if bridge["molar_mass_g_mol"] != 5808 or bridge["field"] != "secretion_ug_per_min":
        raise ValueError("Unreviewed mass conversion")
    if [s["name"] for s in p["solvers"]] != ["coarse", "tight", "reference"]:
        raise ValueError("Incomplete solver comparison")


def source_input(source, output, protocol, identity):
    result = source_report(source)
    manifest = json.loads((source / "manifest.json").read_text())
    if not result["passed"] or result["protocol"] != protocol["trace_bridge"]["source_protocol"]:
        raise ValueError("Unsupported or failed source protocol")
    if manifest.get("model_version") != protocol["trace_bridge"]["source_model"]:
        raise ValueError("Unsupported secretion model")
    if result["horizon_min"] != protocol["horizon_min"]:
        raise ValueError("Source horizon differs; no extrapolation allowed")
    target = output / "bc001"
    target.mkdir()
    for name in (*manifest["files"], "manifest.json"):
        # BC-001 reader already requires safe, regular local filenames.
        shutil.copyfile(source / name, target / name)
    with (target / "trace.csv").open(newline="") as stream:
        rows = list(csv.DictReader(stream))
    times = np.array([float(r["time_min"]) for r in rows])
    mass_rate = np.array([float(r["secretion_ug_per_min"]) for r in rows])
    p = identity["kinetic_parameters"]
    q = mass_rate * 1e6 / (protocol["trace_bridge"]["molar_mass_g_mol"] * p["BW"])
    forcing = from_source_samples(times, q)
    write_table(
        output / "source-input.csv",
        ("time_min", "secretion_ug_per_min", "q_pmol_kg_min"),
        zip(times, mass_rate, q, strict=True),
    )
    dump(output / "source-forcing.json", forcing.to_dict())
    return forcing


def execute(protocol_path, source, output):
    output.mkdir(parents=True, exist_ok=False)
    manifest = {
        "schema": SCHEMA,
        "status": "started",
        "started_utc": datetime.now(UTC).isoformat(),
        "files": {},
        "runtime": {
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
        manifest["git_branch"] = subprocess.check_output(
            ["git", "branch", "--show-current"], cwd=HERE, text=True
        ).strip()
        for name in SOURCE_FILES:
            shutil.copyfile(HERE / name, output / f"source-{name}")
        for name in ("uv.lock", "pyproject.toml"):
            shutil.copyfile(ROOT / "experiments/m0/simglucose" / name, output / f"native-{name}")
        shutil.copyfile(protocol_path, output / "protocol.json")
        p = json.loads((output / "protocol.json").read_text())
        checked_protocol(p)
        params, identity = load(p["upstream"]["profile"])
        for field, key in (
            ("upstream_revision", "revision"),
            ("profile", "profile"),
            ("patient_file_sha256", "patient_file_sha256"),
            ("parameter_file_sha256", "parameter_file_sha256"),
        ):
            if identity[field] != p["upstream"][key]:
                raise ValueError(
                    "Declared upstream identity differs from the installed native source"
                )
        dump(output / "native-identity.json", identity)
        forcing = source_input(source, output, p, identity)
        times = np.unique(
            np.append(
                np.linspace(
                    0, p["horizon_min"], round(p["horizon_min"] / p["sample_step_min"]) + 1
                ),
                p["additional_sample_times_min"],
            )
        )
        settings = {k: v for k, v in p["solvers"][-1].items() if k != "name"}
        average = forcing.integral() / p["horizon_min"]
        constant = Forcing([0, p["horizon_min"]], [average], [average])
        zero = Forcing([0, p["horizon_min"]], [0], [0])
        for name, signal, route in (
            ("source-liver", forcing, "liver"),
            ("source-peripheral", forcing, "peripheral"),
            ("matched-constant-liver", constant, "liver"),
            ("zero-liver", zero, "liver"),
        ):
            states = simulate(times, params, signal, route, settings)
            exact = oracle(times, params, signal, route)
            plasma = states[:, 0] / params.Vi
            values = np.column_stack((times, states, plasma, exact[:, :2], exact[:, 0] / params.Vi))
            write_table(output / f"{name}.csv", COLUMNS, values)
        manifest["phase"] = "verification"
        manifest["files"] = hashes(output)
        dump(output / "manifest.json", manifest)
        verification = verify(p, params, forcing)
        dump(output / "verification.json", verification)
        if not verification["passed"]:
            raise RuntimeError("Prespecified BC-002 criteria failed; inspect verification.json")
        manifest.update(status="calculated", files=hashes(output))
        dump(output / "manifest.json", manifest)
        result = reconstruct(output, allow_pending=True)
        if not result["passed"]:
            raise RuntimeError("Reconstructed criteria failed")
        dump(output / "report.json", result)
        from experiments.m4.kinetic_inlet.plot import render

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
    parser.add_argument("--protocol", type=Path, default=HERE / "refined-protocol.json")
    parser.add_argument("--secretion-run", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = execute(args.protocol, args.secretion_run, args.output)
    print(
        json.dumps(
            {
                "passed": result["passed"],
                "maximum_route_contrast_pmol_l": result["maximum_route_contrast_pmol_l"],
                "cases": result["cases"],
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
