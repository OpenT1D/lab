"""Execute a trusted local one-file secretion model in its selected Python runtime."""

import argparse
import contextlib
import importlib.util
import json
import sys
from pathlib import Path


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("source", type=Path)
    parser.add_argument("input", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    request = json.loads(args.input.read_text())
    if set(request) != {"times_min", "glucose_mmol_l"}:
        raise ValueError("Incomplete model request")
    spec = importlib.util.spec_from_file_location("researcher_secretion_model", args.source)
    if spec is None or spec.loader is None:
        raise ValueError("Cannot load researcher source")
    module = importlib.util.module_from_spec(spec)
    with contextlib.redirect_stdout(sys.stderr):
        spec.loader.exec_module(module)
        rates = module.secretion(request["times_min"], request["glucose_mmol_l"])
    result = {
        "schema": "m4-model-samples/1",
        "times_min": request["times_min"],
        "glucose_mmol_l": request["glucose_mmol_l"],
        "secretion_pmol_kg_min": rates,
        "unit": "pmol/(kg min)",
    }
    args.output.write_text(json.dumps(result, allow_nan=False, indent=2) + "\n")


if __name__ == "__main__":
    main()
