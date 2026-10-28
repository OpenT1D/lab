"""Trusted local frozen model execution; isolated process, not a security sandbox."""

import importlib.util
import json
import math
import platform
import random
from pathlib import Path


def main():
    random.seed(0)
    directory = Path.cwd()
    record = json.loads((directory / "input.json").read_text())
    state = json.loads((directory / "state.json").read_text())
    spec = importlib.util.spec_from_file_location(
        "researcher_prognostic_model", directory / "model.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    prediction = module.predict(record, state)
    if (
        type(prediction) not in (int, float)
        or not math.isfinite(prediction)
        or not 0 <= prediction <= 1000
    ):
        raise ValueError("Invalid prediction")
    result = {
        "schema": "m5-prognostic-worker/1",
        "prediction_u_day": prediction,
        "runtime": {
            "implementation": platform.python_implementation(),
            "python_version": platform.python_version(),
            "python_major_minor": ".".join(platform.python_version_tuple()[:2]),
        },
    }
    (directory / "output.json").write_text(json.dumps(result, allow_nan=False) + "\n")


if __name__ == "__main__":
    main()
