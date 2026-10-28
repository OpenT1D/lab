"""Locked numerical process; writes every completed/failed attempt immediately."""

import platform
from dataclasses import asdict
from pathlib import Path

import numpy as np
import scipy

from experiments.m4.kinetic_inlet.forcing import Forcing
from experiments.m4.kinetic_inlet.native import load
from experiments.m4.paired_kinetics.common import dump, read

from . import coupled, preflight, secretion
from .contract import baseline, validate
from .verify_source import verify


def run(directory):
    directory = Path(directory)
    p = read(directory / "protocol.json")
    validate(p)
    runtime = {
        "python": platform.python_version(),
        "numpy": np.__version__,
        "scipy": scipy.__version__,
    }
    if any(runtime[k] != p["runtime"][k] for k in ("numpy", "scipy")) or not runtime[
        "python"
    ].startswith("3.12."):
        raise ValueError("Wrong numerical runtime")
    verify(directory)  # Hard ordering: no metabolic solve before source checks.
    preflight.probe(directory)
    before = preflight.assess(p, read(directory / "probe.json"))
    dump(directory / "preflight.json", before)
    if not before["passed"]:
        raise RuntimeError("Preflight failed")
    native, identity = load()
    params = {k: (str(v) if k == "Name" else float(v)) for k, v in native.to_dict().items()}
    dump(
        directory / "native.json", {"runtime": runtime, "identity": identity, "parameters": params}
    )
    initial = [float(v) for v in native.iloc[2:15]]
    for scenario in p["scenarios"]:
        folder = directory / scenario["id"]
        folder.mkdir()
        for case in p["cases"]:
            b = baseline(
                params, initial, case["fraction"], p["source"]["parameters"]["gamma_per_min"]
            )
            source = secretion.parameters(p, b, case["gain"])
            for solver in p["solvers"]:
                record, dense = coupled.integrate(
                    p, params, b, source, scenario["stomach_solid_mg"], solver
                )
                record["source_parameters"] = asdict(source)
                dump(folder / f"{case['id']}-{solver['name']}.json", record)
                print(scenario["id"], case["id"], solver["name"], record["status"], flush=True)
            if case["id"] == "native_zero":
                padded, _ = coupled.integrate(
                    p,
                    params,
                    b,
                    source,
                    scenario["stomach_solid_mg"],
                    p["solvers"][-1],
                    native_only=True,
                )
                dump(folder / "native-padded.json", padded)
                dump(
                    folder / "native-class.json",
                    coupled.native_class(native, b, scenario["stomach_solid_mg"], p["horizon_min"]),
                )
            if case["id"] == "feedback_full":
                if record["status"] != "completed":
                    dump(
                        folder / "derived-controls-failed.json",
                        {"reason": "Parent reference incomplete"},
                    )
                    continue
                for step in p["refinement"]["replay_sample_steps_min"]:
                    times = np.arange(0, p["horizon_min"] + step / 2, step)
                    rates = np.array([source.gamma * dense(t)[14] for t in times])
                    force = Forcing(times.tolist(), rates[:-1].tolist(), rates[1:].tolist())
                    replay, _ = coupled.integrate(
                        p,
                        params,
                        b,
                        source,
                        scenario["stomach_solid_mg"],
                        p["solvers"][-1],
                        forcing=force.evaluate,
                        edges=force.edges,
                    )
                    replay["forcing"] = force.to_dict()
                    replay["transferred_amount_pmol_kg"] = force.integral()
                    replay["sample_step_min"] = step
                    dump(folder / f"replay-{step}.json", replay)
                    print(scenario["id"], "replay", step, replay["status"], flush=True)
                amount = force.integral()
                const = Forcing(
                    [0, p["horizon_min"]], [amount / p["horizon_min"]], [amount / p["horizon_min"]]
                )
                for solver in p["solvers"]:
                    equal, _ = coupled.integrate(
                        p,
                        params,
                        b,
                        source,
                        scenario["stomach_solid_mg"],
                        solver,
                        forcing=const.evaluate,
                    )
                    equal["forcing"] = const.to_dict()
                    equal["transferred_amount_pmol_kg"] = const.integral()
                    dump(folder / f"equal-arrival-{solver['name']}.json", equal)
                    print(
                        scenario["id"], "equal-arrival", solver["name"], equal["status"], flush=True
                    )


if __name__ == "__main__":
    import sys

    run(Path(sys.argv[1]))
