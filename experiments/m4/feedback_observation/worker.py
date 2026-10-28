"""Unchanged C-peptide solver, isolated from the native feedback runtime."""

import platform
import sys
from pathlib import Path

import numpy as np
import scipy

from experiments.m4.c_peptide.model import Parameters, simulate
from experiments.m4.hepatic.report import reconstruct as parent_report
from experiments.m4.kinetic_inlet.forcing import Forcing
from experiments.m4.paired_kinetics.oracle import cpeptide

from .adapter import diagnostic_inputs, prepare
from .common import VERSION, dump, labels, read, source, validate


def solve(bundle, solver):
    return simulate(
        bundle["times"],
        Parameters(**bundle["parameters"]),
        Forcing(**bundle["forcing"]),
        bundle["initial"],
        solver,
    ).tolist()


def execute(directory, output):
    directory, output = Path(directory), Path(output)
    p = read(directory / "protocol.json")
    validate(p)
    runtime = {
        "python": platform.python_version(),
        "numpy": np.__version__,
        "scipy": scipy.__version__,
    }
    if any(runtime[k] != p["runtime"][k] for k in ("numpy", "scipy")) or not runtime[
        "python"
    ].startswith(p["runtime"]["python"] + "."):
        raise ValueError("Wrong C-peptide runtime")
    if not parent_report(directory / "hepatic")["passed"]:
        raise ValueError("Failing parent cannot support observations")
    (output / "cases").mkdir(parents=True)
    status = {"schema": VERSION, "status": "started", "runtime": runtime, "failures": []}
    dump(output / "worker.json", status)
    for label in labels(directory):
        try:
            reference, tight = source(directory, label), source(directory, label, "tight")
            bundle = prepare(p, reference)
            record = {
                "id": label,
                "status": "completed",
                "boundary": bundle,
                "states": {s["name"]: solve(bundle, s) for s in p["solvers"]},
                "oracle": cpeptide(
                    bundle["times"],
                    Parameters(**bundle["parameters"]),
                    Forcing(**bundle["forcing"]),
                    bundle["initial"],
                ).tolist(),
                "diagnostics": {
                    name: {"boundary": item, "states": solve(item, p["solvers"][-1])}
                    for name, item in diagnostic_inputs(p, reference, tight).items()
                },
            }
        except Exception as exc:
            record = {
                "id": label,
                "status": "failed",
                "error": {"type": type(exc).__name__, "message": str(exc)},
            }
            status["failures"].append(label)
        dump(output / "cases" / (label + ".json"), record)
        print(label, record["status"], flush=True)
    status["status"] = "failed" if status["failures"] else "completed"
    dump(output / "worker.json", status)


if __name__ == "__main__":
    execute(*sys.argv[1:])
