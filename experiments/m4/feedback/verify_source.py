"""Prespecified synthetic source checks, before any metabolic feedback execution."""

from dataclasses import asdict
from pathlib import Path

import numpy as np

from experiments.m4.paired_kinetics.common import dump, read

from . import secretion, source_oracle
from .common import validate_source_cases
from .contract import validate


def verify(directory):
    directory = Path(directory)
    p = read(directory / "protocol.json")
    validate(p)
    spec = read(directory / "source-cases.json")
    validate_source_cases(spec)
    entries = []
    for case in spec["cases"]:
        params = secretion.parameters(
            p,
            {
                "Sb_pmol_kg_min": case.get("basal", spec["default_basal"]),
                "h_mg_dl": spec["default_threshold"],
            },
            case.get("gain", spec["default_gain"]),
        )
        if "gamma" in case:
            params = secretion.Parameters(**(asdict(params) | {"gamma": case["gamma"]}))
        g = secretion.GlucoseSignal(tuple(case["times"]), tuple(case["glucose"]))
        t = np.arange(0, g.horizon + spec["sample_step_min"] / 2, spec["sample_step_min"])
        exact = np.asarray(source_oracle.simulate(t, g, case["initial"], params))
        results = {}
        for solver in p["solvers"]:
            y = secretion.simulate(t, g, case["initial"], params, solver)
            results[solver["name"]] = y.tolist()
        entries.append(
            {
                "id": case["id"],
                "parameters": asdict(params),
                "times": t.tolist(),
                "analytic": exact.tolist(),
                "solutions": results,
            }
        )
    data = {"schema": "bc008-source-reference/1", "cases": entries}
    dump(directory / "source-reference.json", data)
    # Coarse output is diagnostic. Frozen acceptance compares tight/reference.
    rate_error = max(
        abs(np.asarray(c["solutions"][s])[:, 0] - np.asarray(c["analytic"])[:, 0]).max()
        for c in entries
        for s in ("tight", "reference")
    )
    mass_error = max(
        abs(np.asarray(c["solutions"][s])[:, 1] - np.asarray(c["analytic"])[:, 1]).max()
        for c in entries
        for s in ("tight", "reference")
    )
    result = {
        "rate_error_pmol_kg_min": float(rate_error),
        "mass_error_pmol_kg": float(mass_error),
        "passed": bool(
            rate_error <= p["criteria"]["secretion_rate_closed_form_error_pmol_kg_min"]
            and mass_error <= p["criteria"]["secretion_closed_form_error_pmol_kg"]
        ),
    }
    dump(directory / "source-assessment.json", result)
    if not result["passed"]:
        raise RuntimeError("Source analytic checks failed; feedback must not run")
    return result


if __name__ == "__main__":
    import sys

    print(verify(Path(sys.argv[1])))
