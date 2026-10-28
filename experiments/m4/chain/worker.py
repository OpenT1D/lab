"""Execute the existing kinetic functions in their own locked environments."""

import argparse
import platform
from pathlib import Path

import numpy as np
import scipy

from experiments.m4.kinetic_inlet.forcing import Forcing
from experiments.m4.paired_kinetics import oracle

from .common import VERSION, boundary, dump, grid, load_source, prepare, read


def execute(directory, branch):
    directory = Path(directory)
    folder = directory / branch
    folder.mkdir(exist_ok=False)
    status = {
        "schema": "bc007-worker/1",
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
        p = read(directory / "protocol.json")
        source = load_source(directory / "secretion", p)
        b = boundary(directory, p)
        if any(status["runtime"][k] != p["runtime"][branch][k] for k in ("numpy", "scipy")):
            raise ValueError("Wrong kinetic runtime")
        if branch == "insulin":
            from experiments.m4.kinetic_inlet import native
            from experiments.m4.paired_kinetics.insulin import simulate

            params, identity = native.load()
            for key in ("m1", "m2", "m30", "m4"):
                if not np.isclose(params[key], b["insulin"][key], rtol=1e-14, atol=0):
                    raise ValueError("Native coefficients differ from boundary")
            if (
                params.BW != p["boundary"]["body_weight_kg"]
                or params.Vi != b["insulin"]["volume_l_kg"]
            ):
                raise ValueError("Native body mass/volume mismatch")
            status["native_identity"] = identity
            volume = float(params.Vi)
            order = ["Ip", "Il", "hepatic_loss", "peripheral_loss", "input"]
        else:
            from experiments.m4.c_peptide.model import Parameters, simulate

            params = Parameters(**{k: v for k, v in b["cpeptide"].items() if k != "reference"})
            volume = params.volume_l_kg
            order = ["central", "peripheral", "eliminated", "input"]
        status.update(volume_l_kg=volume, state_order=order)
        dump(folder / "worker.json", status)
        times = np.array(grid(p))
        for case in p["cases"]:
            request = prepare(p, b, case, source)
            force = Forcing(**request["forcing"])
            initial = request["initial"][branch]
            solved = {
                s["name"]: simulate(times, params, force, initial, s).tolist() for s in p["solvers"]
            }
            independent = getattr(oracle, branch)(times, params, force, np.array(initial)).tolist()
            repeat = simulate(times, params, force, initial, p["solvers"][-1]).tolist()
            legacy = (
                native.simulate(times, params, force, "liver", p["solvers"][-1]).tolist()
                if branch == "insulin" and not any(initial)
                else None
            )
            dump(
                folder / f"{case['id']}.json",
                {
                    "schema": "bc007-case/1",
                    "branch": branch,
                    "request": request,
                    "times_min": times.tolist(),
                    "volume_l_kg": volume,
                    "states": solved,
                    "oracle": independent,
                    "repeated": repeat,
                    "legacy": legacy,
                },
            )
        levels = read(directory / "source-samples.json")["levels"]
        reference_case = next(c for c in p["cases"] if c["id"] == "full_increment")
        runs = []
        for level in levels:
            request = prepare(p, b, reference_case, level)
            values = simulate(
                times,
                params,
                Forcing(**request["forcing"]),
                request["initial"][branch],
                p["solvers"][-1],
            )
            runs.append(
                {"step_min": level["step_min"], "request": request, "states": values.tolist()}
            )
        dump(folder / "refinement.json", {"runs": runs})
        status["status"] = "completed"
        dump(folder / "worker.json", status)
    except BaseException as exc:
        status.update(status="failed", error={"type": type(exc).__name__, "message": str(exc)})
        dump(folder / "worker.json", status)
        raise


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("directory", type=Path)
    parser.add_argument("--branch", choices=("insulin", "cpeptide"), required=True)
    args = parser.parse_args()
    execute(args.directory, args.branch)


if __name__ == "__main__":
    main()
