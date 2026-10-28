"""Execute causal source and fixed basal control in the BC-008 locked runtime."""

import argparse
import platform
from pathlib import Path

import numpy as np
import scipy

from experiments.m4.kinetic_inlet.native import load
from experiments.m4.paired_kinetics.common import dump, read

from . import coupled
from .common import (
    CASES,
    SCENARIOS,
    SOLVERS,
    VERSION,
    baseline_context,
    declaration,
    load_model,
    preflight,
    protocol,
    reference,
    sha256,
)


def run(directory, label):
    directory = Path(directory)
    folder = directory / label
    folder.mkdir(exist_ok=False)
    status = {
        "schema": "m4-causal-worker/1",
        "implementation": VERSION,
        "label": label,
        "status": "started",
        "runtime": {
            "python": platform.python_version(),
            "numpy": np.__version__,
            "scipy": scipy.__version__,
        },
        "attempts": [],
    }
    dump(folder / "worker.json", status)
    try:
        bc, archived_native, probe, _ = reference(directory / "reference")
        task = protocol(read(directory / "protocol.json"), bc)
        if any(
            status["runtime"][key] != bc["runtime"][key] for key in ("numpy", "scipy")
        ) or not status["runtime"]["python"].startswith(bc["runtime"]["python"] + "."):
            raise ValueError("Wrong locked BC-008 runtime")
        native, identity = load()
        params = {
            key: (str(v) if key == "Name" else float(v)) for key, v in native.to_dict().items()
        }
        if identity != archived_native["identity"] or params != archived_native["parameters"]:
            raise ValueError("Native parameters or source identity differ from BC-008 reference")
        status["native_identity"] = identity
        basal, gamma = baseline_context(bc, archived_native, probe)
        declared = declaration(read(directory / "model.json"))
        if sha256(directory / "model.py") != declared["source_sha256"]:
            raise ValueError("Researcher source hash differs from declaration")
        model = load_model(directory / "model.py")
        checked = preflight(
            model, basal["Sb_pmol_kg_min"], basal["h_mg_dl"], declared["parameters"], task
        )
        dump(folder / "preflight.json", checked)
        dump(folder / "worker.json", status)
        failed = False
        for scenario in bc["scenarios"]:
            if scenario["id"] not in SCENARIOS:
                raise ValueError("Unexpected BC-008 scenario")
            scene = folder / scenario["id"]
            scene.mkdir()
            for mode in CASES:
                for solver in bc["solvers"]:
                    if solver["name"] not in SOLVERS:
                        continue
                    name = f"{mode}-{solver['name']}.json"
                    path = scene / name
                    status["attempts"].append(
                        {
                            "scenario": scenario["id"],
                            "mode": mode,
                            "solver": solver["name"],
                            "status": "started",
                        }
                    )
                    dump(folder / "worker.json", status)
                    try:
                        record, _ = coupled.integrate(
                            task,
                            bc,
                            params,
                            basal,
                            gamma,
                            scenario["stomach_solid_mg"],
                            solver,
                            model,
                            declared["parameters"],
                            mode,
                        )
                        record["model_source_sha256"] = declared["source_sha256"]
                        record["gamma_per_min"] = gamma
                        dump(path, record)
                        status["attempts"][-1]["status"] = record["status"]
                        failed |= record["status"] != "completed"
                    except Exception as exc:
                        failed = True
                        record = {
                            "schema": "m4-causal-trajectory/1",
                            "status": "failed",
                            "scenario": scenario["id"],
                            "mode": mode,
                            "solver": solver,
                            "error": {"type": type(exc).__name__, "message": str(exc)[:500]},
                        }
                        dump(path, record)
                        status["attempts"][-1]["status"] = "failed"
                    dump(folder / "worker.json", status)
                    print(
                        label,
                        scenario["id"],
                        mode,
                        solver["name"],
                        status["attempts"][-1]["status"],
                        flush=True,
                    )
        status["status"] = "failed" if failed else "completed"
        dump(folder / "worker.json", status)
        if failed:
            raise RuntimeError("One or more causal cases failed; inspect preserved cases")
    except BaseException as exc:
        status.update(
            status="failed", error={"type": type(exc).__name__, "message": str(exc)[:500]}
        )
        dump(folder / "worker.json", status)
        raise


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("directory", type=Path)
    parser.add_argument("--label", choices=("primary", "repeat"), required=True)
    args = parser.parse_args()
    run(args.directory, args.label)


if __name__ == "__main__":
    main()
