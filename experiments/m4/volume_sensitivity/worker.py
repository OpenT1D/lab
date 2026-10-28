"""Locked numerical process: gates, common observations and all 60 fits."""

import platform
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path

import numpy as np
import scipy

from . import inference, verify
from .common import dump, read, specifications, validate
from .model import Model


def plain(value):
    if isinstance(value, np.ndarray):
        return value.tolist()
    if isinstance(value, np.generic):
        return value.item()
    if isinstance(value, dict):
        return {k: plain(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [plain(v) for v in value]
    return value


def fit(arguments):
    directory, p, spec = arguments
    path = Path(directory) / "cases" / (spec["id"] + ".json")
    dump(path, {**spec, "status": "started", "fits": []})
    try:
        model = Model(p)
        result = inference.fit_case(
            model,
            spec,
            read(Path(directory) / "observations.json"),
            checkpoint=lambda fits: dump(path, plain({**spec, "status": "partial", "fits": fits})),
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
    model = Model(p)
    dump(
        directory / "worker.json",
        plain({"runtime": runtime, "native": model.identity, "parameters": model.params}),
    )
    result = verify.run(model)
    dump(directory / "verification.json", plain(result))
    if not result["passed"]:
        raise RuntimeError("Forward numerical gate failed; no inference executed")
    dump(directory / "observations.json", plain(inference.generate(model)))
    sensitivity = inference.sensitivities(model)
    dump(directory / "sensitivity.json", plain(sensitivity))
    if not sensitivity["passed"]:
        raise RuntimeError("Sensitivity numerical gate failed; no fits executed")
    print("Numerical gates passed; starting 60 analyses, two starts each", flush=True)
    # Each worker owns one artifact; order of execution cannot select observations.
    with ProcessPoolExecutor(max_workers=2) as pool:
        futures = [pool.submit(fit, (str(directory), p, s)) for s in specifications(p)]
        for future in as_completed(futures):
            print(future.result(), flush=True)


if __name__ == "__main__":
    import sys

    run(Path(sys.argv[1]), Path(sys.argv[2]))
