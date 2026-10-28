"""One scientific branch per pinned runtime; save every completed case before proceeding."""

import argparse
import hashlib
import platform
from pathlib import Path

import numpy as np
import scipy

from experiments.m4.kinetic_inlet.forcing import Forcing, interval_average

from . import oracle
from .common import VERSION, cases, dump, grid, read, validate


def execute(directory, branch):
    directory = Path(directory)
    output = directory / branch
    output.mkdir(exist_ok=False)
    status = {
        "schema": "bc005-worker/1",
        "status": "started",
        "implementation": VERSION,
        "branch": branch,
        "runtime": {
            "python": platform.python_version(),
            "numpy": np.__version__,
            "scipy": scipy.__version__,
        },
    }
    dump(output / "worker.json", status)
    try:
        p = read(directory / "protocol.json")
        validate(p)
        boundary = read(directory / "boundary/protocol.json")
        if any(status["runtime"][k] != p["runtime"][branch][k] for k in ("numpy", "scipy")):
            raise ValueError("Wrong numerical runtime for paired branch")
        if branch == "insulin":
            from experiments.m4.kinetic_inlet import native

            from .insulin import simulate

            params, identity = native.load()
            expected = boundary["insulin"]
            for key in ("m1", "m2", "m30", "m4"):
                if not np.isclose(params[key], expected[key], rtol=1e-14, atol=0):
                    raise ValueError("Native coefficient differs from boundary")
            if params.BW != boundary["body_weight_kg"] or params.Vi != expected["volume_l_kg"]:
                raise ValueError("Native weight/volume differs from boundary")
            volume = float(params.Vi)
            status["native_identity"] = identity
            status["state_order"] = ["Ip", "Il", "hepatic_loss", "peripheral_loss", "input"]
        else:
            from experiments.m4.c_peptide.model import Parameters, simulate

            params = Parameters(
                **{k: v for k, v in boundary["cpeptide"].items() if k != "reference"}
            )
            volume = params.volume_l_kg
            status["state_order"] = ["central", "peripheral", "eliminated", "input"]
        status["volume_l_kg"] = volume
        dump(output / "worker.json", status)
        for case in cases(directory / "boundary", p):
            times = np.array(grid(case, p))
            forcing = Forcing(**case[branch]["forcing"])
            initial = np.array(case[branch]["initial"], dtype=float)
            states = {s["name"]: simulate(times, params, forcing, initial, s) for s in p["solvers"]}
            reference = getattr(oracle, branch)(times, params, forcing, initial)
            repeated = simulate(times, params, forcing, initial, p["solvers"][-1])
            legacy, analytical = None, None
            if branch == "insulin" and np.all(initial == 0):
                legacy = native.simulate(times, params, forcing, "liver", p["solvers"][-1]).tolist()
            if branch == "cpeptide" and forcing.left == forcing.right:
                from experiments.m4.c_peptide.reference import constant_schedule

                analytical = constant_schedule(times, params, forcing, initial).tolist()
            data = {
                "schema": "bc005-case/1",
                "id": case["id"],
                "branch": branch,
                "times_min": times.tolist(),
                "input": forcing.to_dict(),
                "initial": initial.tolist(),
                "volume_l_kg": volume,
                "states": {k: v.tolist() for k, v in states.items()},
                "oracle": reference.tolist(),
                "legacy": legacy,
                "analytical_pmol_l": analytical,
                "repeat_error": float(np.max(np.abs(repeated - states["reference"]))),
                "repeat_sha256": hashlib.sha256(repeated.astype("<f8").tobytes()).hexdigest(),
            }
            dump(output / f"{case['id']}.json", data)
            if case["id"] == p["communication_case"]:
                communicated = []
                for dt in p["communication_intervals_min"]:
                    average = interval_average(forcing, dt)
                    values = simulate(times, params, average, initial, p["solvers"][-1])
                    communicated.append(
                        {"dt_min": dt, "input": average.to_dict(), "states": values.tolist()}
                    )
                dump(output / "communication.json", {"case": case["id"], "runs": communicated})
        status["status"] = "completed"
        dump(output / "worker.json", status)
    except BaseException as exc:
        status.update(status="failed", error={"type": type(exc).__name__, "message": str(exc)})
        dump(output / "worker.json", status)
        raise


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("directory", type=Path)
    parser.add_argument("--branch", choices=("insulin", "cpeptide"), required=True)
    args = parser.parse_args()
    execute(args.directory, args.branch)


if __name__ == "__main__":
    main()
