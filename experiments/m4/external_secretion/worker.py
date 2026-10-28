"""Run candidate rates through the two unchanged kinetic implementations."""

import argparse
import platform
from pathlib import Path

import numpy as np
import scipy

from experiments.m4.kinetic_inlet.forcing import Forcing
from experiments.m4.paired_kinetics import oracle
from experiments.m4.paired_kinetics.common import dump

from .common import CASES, VERSION, candidate_request, read, reference


def execute(directory, branch):
    directory = Path(directory)
    folder = directory / branch
    folder.mkdir(exist_ok=False)
    status = {
        "schema": "m4-external-worker/1",
        "implementation": VERSION,
        "branch": branch,
        "status": "started",
        "runtime": {
            "python": platform.python_version(),
            "numpy": np.__version__,
            "scipy": scipy.__version__,
        },
    }
    dump(folder / "worker.json", status)
    try:
        protocol, source, base, _ = reference(directory / "reference")
        expected = protocol["runtime"][branch]
        if any(status["runtime"][k] != expected[k] for k in ("numpy", "scipy")):
            raise ValueError("Wrong locked kinetic runtime")
        if branch == "insulin":
            from experiments.m4.kinetic_inlet.native import load
            from experiments.m4.paired_kinetics.insulin import simulate

            params, identity = load()
            if params.BW != protocol["boundary"]["body_weight_kg"] or any(
                not np.isclose(params[k], base["insulin"][k], rtol=1e-14, atol=0)
                for k in ("m1", "m2", "m30", "m4")
            ):
                raise ValueError("Native insulin parameters differ from frozen boundary")
            volume = float(params.Vi)
            status["native_identity"] = identity
            order = ["Ip", "Il", "hepatic_loss", "peripheral_loss", "input"]
        else:
            from experiments.m4.c_peptide.model import Parameters, simulate

            params = Parameters(**{k: v for k, v in base["cpeptide"].items() if k != "reference"})
            volume = params.volume_l_kg
            order = ["central", "peripheral", "eliminated", "input"]
        if volume != base[branch]["volume_l_kg"]:
            raise ValueError("Kinetic volume differs from frozen boundary")
        status.update(volume_l_kg=volume, state_order=order)
        dump(folder / "worker.json", status)
        times = np.array(read(directory / "model-samples.json")["times_min"])
        for case_id in CASES:
            request = candidate_request(directory, case_id, context=(protocol, source, base))
            force = Forcing(**request["forcing"])
            initial = request["initial"][branch]
            solved = {
                settings["name"]: simulate(times, params, force, initial, settings).tolist()
                for settings in protocol["solvers"]
            }
            independent = getattr(oracle, branch)(times, params, force, np.array(initial)).tolist()
            dump(
                folder / f"{case_id}.json",
                {
                    "schema": "m4-external-case/1",
                    "branch": branch,
                    "case_id": case_id,
                    "request": request,
                    "times_min": times.tolist(),
                    "volume_l_kg": volume,
                    "states": solved,
                    "oracle": independent,
                },
            )
        status["status"] = "completed"
        dump(folder / "worker.json", status)
    except BaseException as exc:
        status.update(status="failed", error={"type": type(exc).__name__, "message": str(exc)})
        dump(folder / "worker.json", status)
        raise


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("directory", type=Path)
    parser.add_argument("--branch", required=True, choices=("insulin", "cpeptide"))
    args = parser.parse_args()
    execute(args.directory, args.branch)


if __name__ == "__main__":
    main()
