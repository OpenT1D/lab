"""Sample the unchanged secretion equations more finely; retain original primary trace."""

import argparse
import platform
from pathlib import Path

import numpy as np
import scipy

from experiments.m4.beta_cell.runtime.model import MODEL_VERSION, GlucoseInput, Parameters, simulate

from .common import VERSION, dump, grid, load_source, read


def execute(directory):
    directory = Path(directory)
    p = read(directory / "protocol.json")
    original = load_source(directory / "secretion", p)
    spec = read(directory / "secretion/protocol.json")
    if (
        np.__version__ != p["runtime"]["cpeptide"]["numpy"]
        or scipy.__version__ != p["runtime"]["cpeptide"]["scipy"]
    ):
        raise ValueError("Wrong secretion runtime")
    levels = [{"step_min": p["source"]["primary_sample_step_min"], **original}]
    params, glucose = Parameters(**spec["parameters"]), GlucoseInput(**spec["input"])
    solver = {k: v for k, v in spec["solvers"][-1].items() if k != "name"}
    for step in p["source"]["refinement_steps_min"][1:]:
        times = np.array(grid(p, step))
        states = simulate(times, params, glucose, **solver)
        levels.append(
            {
                "step_min": step,
                "times_min": times.tolist(),
                "glucose_mmol_l": glucose(times).tolist(),
                "secretion_ug_min": (params.m * states[:, 0]).tolist(),
                "states": states.tolist(),
            }
        )
    dump(
        directory / "source-samples.json",
        {
            "schema": "bc007-source/1",
            "implementation": VERSION,
            "model": MODEL_VERSION,
            "runtime": {
                "python": platform.python_version(),
                "numpy": np.__version__,
                "scipy": scipy.__version__,
            },
            "levels": levels,
        },
    )


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("directory", type=Path)
    args = parser.parse_args()
    execute(args.directory)


if __name__ == "__main__":
    main()
