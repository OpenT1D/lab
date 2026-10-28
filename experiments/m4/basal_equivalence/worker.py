"""Run a frozen SC-rate search inside the locked BC-008 numerical runtime."""

import argparse
import platform
from pathlib import Path

import numpy as np
import scipy

from experiments.m4.causal_secretion import coupled
from experiments.m4.causal_secretion.common import load_model, preflight
from experiments.m4.feedback.report import outcomes
from experiments.m4.kinetic_inlet.native import load
from experiments.m4.paired_kinetics.common import dump

from .common import (
    SLOTS,
    VERSION,
    context,
    declared_sources,
    next_step,
    no_solution_confirmation_factors,
    sc_context,
)


def run(directory, label):
    directory = Path(directory)
    folder = directory / label
    folder.mkdir(exist_ok=False)
    status = {
        "schema": "m4-basal-equivalence-worker/1",
        "implementation": VERSION,
        "label": label,
        "status": "started",
        "runtime": {
            "python": platform.python_version(),
            "numpy": np.__version__,
            "scipy": scipy.__version__,
        },
        "attempts": [],
    }
    dump(folder / "worker.json", status)
    try:
        bc, archived_native, basal, gamma, task, target = context(
            directory / "reference", directory / "protocol.json"
        )
        if any(status["runtime"][key] != bc["runtime"][key] for key in ("numpy", "scipy")):
            raise ValueError("Wrong locked BC-008 numerical runtime")
        if not status["runtime"]["python"].startswith(bc["runtime"]["python"] + "."):
            raise ValueError("Wrong locked BC-008 Python runtime")
        native, identity = load()
        params = {
            key: (str(v) if key == "Name" else float(v)) for key, v in native.to_dict().items()
        }
        if identity != archived_native["identity"] or params != archived_native["parameters"]:
            raise ValueError("Native source or parameters differ from BC-008")
        status["native_identity"] = identity
        declared = declared_sources(directory)
        meal = next(item for item in bc["scenarios"] if item["id"] == "gastric_load_30g")
        fasting = next(item for item in bc["scenarios"] if item["id"] == "fasting")
        solvers = {item["name"]: item for item in bc["solvers"]}

        def attempt(path, slot, factor, phase, mode, scenario, solver, model, model_params):
            entry = {
                "slot": slot,
                "factor": factor,
                "phase": phase,
                "mode": mode,
                "scenario": scenario["id"],
                "solver": solver["name"],
                "file": str(path.relative_to(folder)),
                "status": "started",
            }
            status["attempts"].append(entry)
            dump(folder / "worker.json", status)
            try:
                record, _ = coupled.integrate(
                    task,
                    bc,
                    params,
                    sc_context(basal, params, factor),
                    gamma,
                    scenario["stomach_solid_mg"],
                    solver,
                    model,
                    model_params,
                    mode,
                )
                record["model_source_sha256"] = declared[slot]["source_sha256"]
                record["gamma_per_min"] = gamma
                record["sc_factor"] = factor
                dump(path, record)
                entry["status"] = record["status"]
                if entry["status"] != "completed":
                    raise RuntimeError("Numerical trajectory stopped before horizon")
                return record
            except Exception as exc:
                if not path.exists():
                    dump(
                        path,
                        {
                            "schema": "m4-causal-trajectory/1",
                            "status": "failed",
                            "error": {"type": type(exc).__name__, "message": str(exc)[:500]},
                        },
                    )
                entry["status"] = "failed"
                raise
            finally:
                dump(folder / "worker.json", status)

        failed = False
        for slot in SLOTS:
            scene = folder / slot
            scene.mkdir()
            source = declared[slot]
            search = {"schema": "m4-basal-search/1", "status": "started", "history": []}
            dump(scene / "search.json", search)
            try:
                model = load_model(directory / f"{slot}.py")
                checked = preflight(
                    model, basal["Sb_pmol_kg_min"], basal["h_mg_dl"], source["parameters"], task
                )
                dump(scene / "preflight.json", checked)
                while True:
                    decision, factor = next_step(search["history"], target, task)
                    if decision not in ("grid", "bisect"):
                        search.update(status=decision, root_factor=factor)
                        break
                    name = f"{len(search['history']):02d}-{decision}-tight.json"
                    record = attempt(
                        scene / name,
                        slot,
                        factor,
                        decision,
                        "candidate",
                        meal,
                        solvers["tight"],
                        model,
                        source["parameters"],
                    )
                    auc = outcomes(record["times"], record["states"], params["Vg"])[
                        "auc_above_initial_mg_min_dl"
                    ]
                    search["history"].append(
                        {"factor": factor, "phase": decision, "file": name, "auc": auc}
                    )
                    dump(scene / "search.json", search)
                if search["status"] == "matched":
                    factor = search["root_factor"]
                    attempt(
                        scene / "root-reference.json",
                        slot,
                        factor,
                        "confirmation",
                        "candidate",
                        meal,
                        solvers["reference"],
                        model,
                        source["parameters"],
                    )
                    attempt(
                        scene / "fasting-reference.json",
                        slot,
                        factor,
                        "diagnostic",
                        "candidate",
                        fasting,
                        solvers["reference"],
                        model,
                        source["parameters"],
                    )
                else:
                    for index, factor in enumerate(
                        no_solution_confirmation_factors(search["history"], target, task)
                    ):
                        attempt(
                            scene / f"confirm-{index:02d}-reference.json",
                            slot,
                            factor,
                            "no_solution_confirmation",
                            "candidate",
                            meal,
                            solvers["reference"],
                            model,
                            source["parameters"],
                        )
                dump(scene / "search.json", search)
            except Exception as exc:
                failed = True
                search.update(
                    status="failed", error={"type": type(exc).__name__, "message": str(exc)[:500]}
                )
                dump(scene / "search.json", search)
        control = folder / "control"
        control.mkdir()
        try:
            for solver in (solvers["tight"], solvers["reference"]):
                attempt(
                    control / f"anchor-{solver['name']}.json",
                    SLOTS[0],
                    0.75,
                    "anchor_control",
                    "host_constant_basal",
                    meal,
                    solver,
                    None,
                    {},
                )
        except Exception:
            failed = True
        status["status"] = "failed" if failed else "completed"
        dump(folder / "worker.json", status)
        if failed:
            raise RuntimeError("One or more basal-equivalence cases failed")
    except BaseException as exc:
        status.update(
            status="failed", error={"type": type(exc).__name__, "message": str(exc)[:500]}
        )
        dump(folder / "worker.json", status)
        raise


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("directory", type=Path)
    parser.add_argument("--label", choices=("primary", "repeat"), required=True)
    args = parser.parse_args()
    run(args.directory, args.label)


if __name__ == "__main__":
    main()
