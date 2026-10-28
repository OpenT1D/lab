"""Check proposed baseline states against pinned native insulin derivatives, without integration."""

import argparse
import json
from pathlib import Path

from .run import ROOT, digest, read, reconstruct


def probe(directory):
    # This optional check runs in the existing M0 runtime, never the tooling environment.
    import numpy as np

    from experiments.m4.kinetic_inlet.native import Action, derivative, load

    report = reconstruct(directory)
    p = read(Path(directory) / "protocol.json")
    params, identity = load()
    for key in ("m1", "m2", "m30", "m4"):
        if not np.isclose(p["insulin"][key], params[key], rtol=1e-14, atol=0):
            raise ValueError("Protocol coefficient differs from verified native profile")
    if p["body_weight_kg"] != params.BW or p["insulin"]["volume_l_kg"] != params.Vi:
        raise ValueError("Protocol body mass or distribution volume differs from native profile")
    residuals = {}
    for case in report["bundles"]:
        carrier = np.asarray(params.iloc[2:15].values, dtype=float).copy()
        carrier[5], carrier[9] = case["insulin"]["initial"][:2]
        carrier[10:12] = 0
        values = derivative(
            0, carrier, Action(CHO=0, insulin=0), params, q=case["basal_pmol_kg_min"], route="liver"
        )
        residuals[case["id"]] = float(max(abs(values[5]), abs(values[9])))
    return {
        "scope": (
            "Pinned insulin derivative at proposed baseline states; "
            "no trajectory or glucose interpretation"
        ),
        "passed": max(residuals.values()) <= p["acceptance"]["equilibrium_derivative_pmol_kg_min"],
        "max_derivative_residuals_pmol_kg_min": residuals,
        "native_identity": identity,
        "input_manifest_sha256": digest(Path(directory) / "manifest.json"),
        "probe_sha256": digest(__file__),
        "native_lock_sha256": digest(ROOT / "experiments/m0/simglucose/uv.lock"),
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("directory", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    with args.output.open("x") as stream:
        try:
            result = probe(args.directory)
            stream.write(json.dumps(result, indent=2, allow_nan=False) + "\n")
        except BaseException as exc:
            stream.write(json.dumps({"passed": False, "error": type(exc).__name__}) + "\n")
            raise
    if not result["passed"]:
        raise SystemExit("Native baseline derivative check failed")
    print("Pinned native baseline derivatives passed")


if __name__ == "__main__":
    main()
