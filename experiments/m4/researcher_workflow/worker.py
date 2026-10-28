"""Observe a verified causal archive in the unchanged locked C-peptide runtime."""

import argparse
import platform
from pathlib import Path

import numpy as np
import scipy

from experiments.m4.c_peptide.model import Parameters
from experiments.m4.causal_secretion.report import reconstruct as reconstruct_parent
from experiments.m4.feedback_observation.adapter import diagnostic_inputs, prepare
from experiments.m4.feedback_observation.common import dump, read, validate
from experiments.m4.feedback_observation.worker import solve
from experiments.m4.kinetic_inlet.forcing import Forcing
from experiments.m4.paired_kinetics.oracle import cpeptide

from .observation import (
    CASE_SCHEMA,
    WORKER_SCHEMA,
    case_ids,
    parent_records,
    validate_worker,
)


def case_record(p, case_id, reference, tight):
    bundle = prepare(p, reference)
    return {
        "schema": CASE_SCHEMA,
        "id": case_id,
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


def run(directory, label):
    if label not in ("primary", "repeat"):
        raise ValueError("Observer label must be primary or repeat")
    directory = Path(directory)
    output = directory / "observations" / label
    output.mkdir(parents=True, exist_ok=False)
    (output / "cases").mkdir()
    status = {
        "schema": WORKER_SCHEMA,
        "label": label,
        "status": "started",
        "runtime": {
            "python": platform.python_version(),
            "numpy": np.__version__,
            "scipy": scipy.__version__,
        },
        "failures": [],
    }
    dump(output / "worker.json", status)
    preflight_error = None
    try:
        p = read(directory / "observation-protocol.json")
        validate(p)
        validate_worker(p, dict(status, status="completed"), label)
        if not reconstruct_parent(directory / "causal")["passed"]:
            raise ValueError("Failing causal parent cannot support observations")
    except Exception as exc:
        preflight_error = exc
    # Even a failed global preflight preserves the complete six-case roster.
    # No source code is imported or called from a researcher model here.
    for case_id in case_ids():
        try:
            if preflight_error is not None:
                raise preflight_error
            record = case_record(p, case_id, *parent_records(directory, case_id))
        except Exception as exc:
            record = {
                "schema": CASE_SCHEMA,
                "id": case_id,
                "status": "failed",
                "error": {"type": type(exc).__name__, "message": str(exc)[:500]},
            }
            status["failures"].append(case_id)
        dump(output / "cases" / f"{case_id}.json", record)
        dump(output / "worker.json", status)
        print(label, case_id, record["status"], flush=True)
    status["status"] = "failed" if status["failures"] else "completed"
    dump(output / "worker.json", status)
    if status["failures"]:
        raise RuntimeError("Observation cases failed; inspect all preserved case records")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("directory", type=Path)
    parser.add_argument("--label", choices=("primary", "repeat"), required=True)
    args = parser.parse_args()
    run(args.directory, args.label)


if __name__ == "__main__":
    main()
