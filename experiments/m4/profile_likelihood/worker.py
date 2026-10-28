"""Locked BC-013 process with independent oracles and complete case checkpoints."""

import platform
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path

import numpy as np
import scipy

from experiments.m4.volume_sensitivity import verify as parent_verify
from experiments.m4.volume_sensitivity.inference import generate
from experiments.m4.volume_sensitivity.model import Model
from experiments.m4.volume_sensitivity.worker import plain

from . import profiles, verify
from .common import dump, read, specifications, validate


def fit(arguments):
    source, directory, p, spec = arguments
    path = Path(directory) / "cases" / (spec["id"] + ".json")
    dump(path, {**spec, "status": "started"})
    try:
        model = Model(read(Path(source) / "parent-volume.json"))
        result = profiles.run_case(
            model,
            p,
            spec,
            read(Path(directory) / "observations.json"),
            checkpoint=lambda result: dump(path, plain({**result, "status": "partial"})),
        )
        dump(path, plain(result))
        return spec["id"]
    except BaseException as exc:
        dump(
            path,
            {
                **read(path),
                "status": "failed",
                "error": {"type": type(exc).__name__, "message": str(exc)},
            },
        )
        raise


def run(source, directory):
    directory = Path(directory)
    if directory != Path(source):
        directory.mkdir(exist_ok=False)
    (directory / "cases").mkdir(exist_ok=False)
    p = read(Path(source) / "protocol.json")
    validate(p)
    runtime = {
        "python": platform.python_version(),
        "numpy": np.__version__,
        "scipy": scipy.__version__,
    }
    if not runtime["python"].startswith("3.12.") or any(
        runtime[k] != p["runtime"][k] for k in ("numpy", "scipy")
    ):
        raise ValueError("Wrong locked numerical runtime")
    model = Model(read(Path(source) / "parent-volume.json"))
    dump(
        directory / "worker.json",
        plain({"runtime": runtime, "native": model.identity, "parameters": model.params}),
    )
    result = {"parent": parent_verify.run(model), "profile_oracles": verify.run(p)}
    dump(directory / "verification.json", plain(result))
    if not all(r["passed"] for r in result.values()):
        raise RuntimeError("Forward/profile oracle gate failed; no biological fits executed")
    dump(directory / "observations.json", plain(generate(model)))
    print("Numerical gates passed; starting nine cases with 27 nuisance profiles", flush=True)
    with ProcessPoolExecutor(max_workers=3) as pool:
        futures = [pool.submit(fit, (str(source), str(directory), p, s)) for s in specifications(p)]
        for future in as_completed(futures):
            print(future.result(), flush=True)


if __name__ == "__main__":
    import sys

    run(Path(sys.argv[1]), Path(sys.argv[2]))
