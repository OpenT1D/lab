"""OT-053 analytical feasibility controls, not an upstream R execution or estimator.

Only synthetic observations and declared reference constants are used.
The two-compartment equilibrium follows
Polonsky 1986 (see the existing BC-003 model card). The exponential quadrature
control examines the mathematical consequence of the interpolation described
by pinned insulin.secretion source; no upstream code is vendored or imported.
"""

import argparse
import hashlib
import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def inspect_sources(directory):
    manifest = json.loads((ROOT / "source-manifest.json").read_text())
    for name, spec in manifest["files"].items():
        if hashlib.sha256((directory / name).read_bytes()).hexdigest() != spec["sha256"]:
            raise ValueError(f"Source hash mismatch: {name}")
    return manifest["commit"]


def equilibrium_quadrature_error(times, k1, k2, k3):
    """Relative basal-rate error from trapezoids of exp(k2*t) at midpoints.

    For constant central amount M, the exact rate is k3*M. Approximating
    integral(exp(k2*s), 0, t) changes it by
    -k1*k2*M*exp(-k2*t)*(approximate_integral - exact_integral).
    This dimensionless control is independent of concentration and volume.
    """
    nodes = [0.0] + [(a + b) / 2 for a, b in zip(times, times[1:])]
    integral = 0.0
    errors = []
    for left, right in zip(nodes, nodes[1:]):
        integral += (right - left) * (math.exp(k2 * left) + math.exp(k2 * right)) / 2
        exact = math.expm1(k2 * right) / k2
        errors.append(-k1 * k2 * math.exp(-k2 * right) * (integral - exact) / k3)
    return errors


def controls():
    # BC-003's nominal t1d_mean is a synthetic control, not human calibration.
    k1, k2, k3 = 0.037, 0.031, 0.052
    volume_l = 0.0655 * 70
    concentration_pmol_l = 200.0
    central = volume_l * concentration_pmol_l
    peripheral = k1 / k2 * central
    rate = k3 * central
    assert abs(rate - (k1 + k3) * central + k2 * peripheral) < 1e-12
    assert abs(k1 * central - k2 * peripheral) < 1e-12
    assert math.isclose(volume_l * concentration_pmol_l, volume_l * 1000 * 0.2)
    # AUC has concentration*time units and is deliberately not total secretion.
    schedules = ([0, 15, 30, 60, 90, 120], [0, 30, 60, 90, 120], [0, 60, 120])
    quadrature = []
    for times in schedules:
        error = equilibrium_quadrature_error(times, k1, k2, k3)
        assert all(value < 0 for value in error)
        quadrature.append(
            {
                "times_min": times,
                "max_absolute_relative_rate_error": max(abs(value) for value in error),
                "last_midpoint_relative_rate_error": error[-1],
            }
        )
    fine = equilibrium_quadrature_error(list(range(121)), k1, k2, k3)
    assert max(abs(value) for value in fine) < 0.0001
    return {
        "schema": "ot053-analytical-feasibility/1",
        "scope": "invented analytical controls; no upstream R execution or human analysis",
        "upstream_runtime_executed": False,
        "equilibrium": {
            "k1_min_inverse": k1,
            "k2_min_inverse": k2,
            "k3_min_inverse": k3,
            "volume_l": volume_l,
            "concentration_pmol_l": concentration_pmol_l,
            "secretion_pmol_min": rate,
            "total_secretion_0_120_pmol": rate * 120,
            "cpeptide_auc_0_120_pmol_min_l": concentration_pmol_l * 120,
        },
        "exponential_quadrature_controls": quadrature,
        "one_minute_grid_max_absolute_relative_rate_error": max(abs(value) for value in fine),
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-dir", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    commit = inspect_sources(args.source_dir)
    result = controls()
    result["inspected_upstream_commit"] = commit
    result["probe_sha256"] = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    # Refuse replacement of any existing result.
    with args.output.open("x") as stream:
        stream.write(json.dumps(result, indent=2, allow_nan=False) + "\n")
    print(f"Analytical controls passed; saved {args.output}")


if __name__ == "__main__":
    main()
