"""BC-009 numerical worker; all failed cases remain explicit in the matrix."""

import platform
from dataclasses import asdict
from pathlib import Path

import numpy as np
import scipy

from experiments.m4.feedback import coupled, secretion
from experiments.m4.feedback.contract import baseline
from experiments.m4.feedback.verify_source import verify
from experiments.m4.kinetic_inlet.native import load

from .common import case_specs, dump, key, read, validate
from .model import literal_mismatch, terms
from .numerical import integrate, rhs_factory


def preflight(p, parent, params, initial):
    gamma = parent["source"]["parameters"]["gamma_per_min"]
    hepatic = p["source"] | {"gamma": gamma}
    probes, baselines = [], []
    for case in parent["cases"]:
        if case["id"] not in p["cases"]:
            continue
        b = baseline(params, initial, case["fraction"], gamma)
        source = secretion.parameters(parent, b, case["gain"])
        x0 = np.r_[b["state"], b["Z_pmol_kg_min"], b["P_pmol_kg"], np.zeros(5)]
        original = coupled.rhs_factory(params, b, source, 0)
        baselines.append(
            {
                "case": case["id"],
                "baseline": b,
                "literal_mismatch": literal_mismatch(params, b, hepatic),
                "original_derivative": original(0, x0).tolist(),
                "variants": {
                    v["id"]: rhs_factory(params, b, source, hepatic, 0, v)(0, x0).tolist()
                    for v in p["variants"]
                },
            }
        )
        for offset in (False, True):
            x = x0.copy()
            if offset:
                x[2] += 1000
                x[3] += 20
                x[5] += 2
                x[9] += 1
                x[13] += 5
                x[14] += 3
            for v in p["variants"]:
                dx = rhs_factory(params, b, source, hepatic, 0, v)(0, x)
                probes.append(
                    {
                        "case": case["id"],
                        "variant": v,
                        "state": x.tolist(),
                        "baseline": b,
                        "source_parameters": asdict(source),
                        "original": original(0, x).tolist(),
                        "adjusted": dx.tolist(),
                        "hepatic": terms(x, params, b, hepatic, v),
                    }
                )
    return {"baselines": baselines, "probes": probes}


def run(directory):
    directory = Path(directory)
    p, parent = read(directory / "protocol.json"), read(directory / "parent.json")
    validate(p, parent)
    runtime = {
        "python": platform.python_version(),
        "numpy": np.__version__,
        "scipy": scipy.__version__,
    }
    if any(runtime[k] != parent["runtime"][k] for k in ("numpy", "scipy")) or not runtime[
        "python"
    ].startswith(parent["runtime"]["python"] + "."):
        raise ValueError("Wrong BC-009 numerical runtime")
    verify(directory / "source-check")
    native, identity = load()
    params = {k: (str(v) if k == "Name" else float(v)) for k, v in native.to_dict().items()}
    initial = [float(v) for v in native.iloc[2:15]]
    dump(
        directory / "native.json",
        {"runtime": runtime, "identity": identity, "parameters": params, "initial": initial},
    )
    probe = preflight(p, parent, params, initial)
    dump(directory / "preflight.json", probe)
    from .report import assess_preflight

    checks = assess_preflight(p, parent, params, initial, probe)
    if any(value > p["verification"][name] for name, value in checks.items()):
        raise RuntimeError("BC-009 preflight failed; no trajectories executed")
    (directory / "cases").mkdir()
    (directory / "parent").mkdir()
    for scenario, case, variant in case_specs(p, parent):
        b = baseline(
            params, initial, case["fraction"], parent["source"]["parameters"]["gamma_per_min"]
        )
        source = secretion.parameters(parent, b, case["gain"])
        for solver in parent["solvers"]:
            try:
                data = integrate(
                    parent, p, params, b, source, scenario["stomach_solid_mg"], variant, solver
                )
                data["source_parameters"] = asdict(source)
            except Exception as exc:
                data = {
                    "schema": "bc009-trajectory/1",
                    "status": "failed",
                    "failure": {
                        "kind": "calculation_error",
                        "type": type(exc).__name__,
                        "message": str(exc),
                    },
                    "variant": variant,
                    "solver": solver,
                    "baseline": b,
                    "load_mg": scenario["stomach_solid_mg"],
                }
            dump(
                directory / "cases" / f"{key(scenario, case, variant)}--{solver['name']}.json", data
            )
            print(key(scenario, case, variant), solver["name"], data["status"], flush=True)
        if variant["id"] == "fixed":
            old, _ = coupled.integrate(
                parent, params, b, source, scenario["stomach_solid_mg"], parent["solvers"][-1]
            )
            dump(directory / "parent" / f"{scenario['id']}--{case['id']}.json", old)


if __name__ == "__main__":
    import sys

    run(Path(sys.argv[1]))
