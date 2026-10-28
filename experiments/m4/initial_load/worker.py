"""Isolated numerical stages; callbacks run only in the pinned native runtime."""

import argparse
import platform
import signal
from dataclasses import asdict
from pathlib import Path

from .common import (
    MODES,
    REFERENCE_MODES,
    SCENARIOS,
    dump,
    read,
    require,
    sha256,
    validate_native_record,
    verify_reference_snapshot,
)


def runtime(project):
    import numpy
    import scipy

    value = {
        "python": platform.python_version(),
        "numpy": numpy.__version__,
        "scipy": scipy.__version__,
    }
    require(value["python"].startswith(project["python"] + "."), "Wrong locked Python runtime")
    require(
        all(value[key] == project[key] for key in ("numpy", "scipy")),
        "Wrong locked numerical runtime",
    )
    return value


def parent_records(directory, name, scenario, mode):
    if mode == "bc008_reference":
        folder = directory / "reference" / "primary"
    else:
        folder = directory / "children" / name / "primary"
    return tuple(
        read(folder / scenario / f"{mode}-{solver}.json") for solver in ("reference", "tight")
    )


def replay(p, params, basal, source, load, parent, dense, folder):
    import numpy as np

    from experiments.m4.feedback import coupled
    from experiments.m4.kinetic_inlet.forcing import Forcing

    if parent["status"] != "completed":
        return
    for step in p["refinement"]["replay_sample_steps_min"]:
        times = np.arange(0, p["horizon_min"] + step / 2, step)
        values = [source.gamma * dense(time)[14] for time in times]
        forcing = Forcing(times.tolist(), values[:-1], values[1:])
        item, _ = coupled.integrate(
            p,
            params,
            basal,
            source,
            load,
            p["solvers"][-1],
            forcing=forcing.evaluate,
            edges=forcing.edges,
        )
        item.update(
            forcing=forcing.to_dict(),
            transferred_amount_pmol_kg=forcing.integral(),
            sample_step_min=step,
        )
        dump(folder / f"replay-{step}.json", item)


def numerical(directory, label, name=None):
    from experiments.m4.causal_secretion import common as causal
    from experiments.m4.causal_secretion.coupled import integrate as supplied_integrate
    from experiments.m4.feedback import coupled, secretion
    from experiments.m4.feedback.contract import baseline
    from experiments.m4.kinetic_inlet.native import load

    plan = read(directory / "plan.json")
    p = read(directory / "historical" / "protocol.json")
    folder = directory / ("reference" if name is None else f"children/{name}") / label
    folder.mkdir(parents=True, exist_ok=False)
    status = {
        "schema": "m4-initial-load-worker/1",
        "kind": "reference" if name is None else "source",
        "label": label,
        "source": name,
        "status": "started",
        "runtime": runtime(p["runtime"]),
        "attempts": [],
    }
    dump(folder / "worker.json", status)
    try:
        causal.reference(directory / "historical")
        native, identity = load()
        params = {
            key: (str(value) if key == "Name" else float(value))
            for key, value in native.to_dict().items()
        }
        old = read(directory / "historical" / "native.json")
        current = {"identity": identity, "parameters": params, "runtime": status["runtime"]}
        validate_native_record(current, old)
        status["native_identity"] = identity
        dump(folder / "native.json", current)
        initial = read(directory / "historical" / "probe.json")["initial"]
        gamma = p["source"]["parameters"]["gamma_per_min"]
        basal = baseline(params, initial, 0.25, gamma)
        task = read(directory / "sources/experiments/m4/causal_secretion/protocol.json")
        if name is not None:
            verify_reference_snapshot(directory)
            declared = causal.declaration(read(directory / "frozen" / name / "model.json"))
            require(
                sha256(directory / "frozen" / name / "model.py") == declared["source_sha256"],
                "Frozen callback changed",
            )
            model = causal.load_model(directory / "frozen" / name / "model.py")
            dump(
                folder / "preflight.json",
                causal.preflight(
                    model, basal["Sb_pmol_kg_min"], basal["h_mg_dl"], declared["parameters"], task
                ),
            )
        failed = False
        for scenario in plan["configuration"]["scenarios"]:
            scene = folder / scenario
            scene.mkdir()
            load_mg = SCENARIOS[scenario]
            modes = REFERENCE_MODES if name is None else MODES[:2]
            for mode in modes:
                b = baseline(params, initial, 0 if mode == "native_zero" else 0.25, gamma)
                source = secretion.parameters(
                    p, b, 1 if mode in ("candidate", "bc008_reference") else 0
                )
                for solver in plan["protocol"]["numerical"]["solvers"]:
                    attempt = {
                        "scenario": scenario,
                        "mode": mode,
                        "solver": solver["name"],
                        "status": "started",
                    }
                    status["attempts"].append(attempt)
                    dump(folder / "worker.json", status)
                    try:
                        if name is None:
                            item, dense = coupled.integrate(p, params, b, source, load_mg, solver)
                            item["source_parameters"] = asdict(source)
                        else:
                            item, dense = supplied_integrate(
                                task,
                                p,
                                params,
                                b,
                                gamma,
                                load_mg,
                                solver,
                                model,
                                declared["parameters"],
                                mode,
                            )
                            item.update(
                                model_source_sha256=declared["source_sha256"], gamma_per_min=gamma
                            )
                        dump(scene / f"{mode}-{solver['name']}.json", item)
                        attempt["status"] = item["status"]
                        failed |= item["status"] != "completed"
                        if solver["name"] == "reference" and mode in (
                            "candidate",
                            "bc008_reference",
                        ):
                            replay(p, params, b, source, load_mg, item, dense, scene)
                    except Exception as exc:
                        attempt.update(
                            status="failed",
                            error={"type": type(exc).__name__, "message": str(exc)[:500]},
                        )
                        dump(
                            scene / f"{mode}-{solver['name']}.json",
                            {
                                "status": "failed",
                                "scenario": scenario,
                                "mode": mode,
                                "solver": solver,
                                "error": attempt["error"],
                            },
                        )
                        failed = True
                    dump(folder / "worker.json", status)
                    print(
                        label, name, scenario, mode, solver["name"], attempt["status"], flush=True
                    )
            if name is None:
                zero = baseline(params, initial, 0, gamma)
                source = secretion.parameters(p, zero, 0)
                item, _ = coupled.integrate(
                    p, params, zero, source, load_mg, p["solvers"][-1], native_only=True
                )
                dump(scene / "native-padded.json", item)
                dump(
                    scene / "native-class.json",
                    coupled.native_class(native, zero, load_mg, p["horizon_min"]),
                )
        status["status"] = "failed" if failed else "completed"
        if failed:
            raise RuntimeError("Numerical cases failed; inspect retained trajectories")
    except BaseException as exc:
        status.update(
            status="failed", error={"type": type(exc).__name__, "message": str(exc)[:500]}
        )
        raise
    finally:
        dump(folder / "worker.json", status)


def observation(directory, label, name):
    from experiments.m4.researcher_workflow.worker import case_record

    p = read(directory / "sources/experiments/m4/feedback_observation/protocol.json")
    plan = read(directory / "plan.json")
    folder = directory / "children" / name / "observations" / label
    (folder / "cases").mkdir(parents=True, exist_ok=False)
    status = {
        "schema": "m4-initial-load-observer/1",
        "kind": "observer",
        "label": label,
        "source": name,
        "status": "started",
        "runtime": runtime(p["runtime"]),
        "attempts": [],
    }
    dump(folder / "worker.json", status)
    try:
        verify_reference_snapshot(directory)
        failed = False
        for scenario in plan["configuration"]["scenarios"]:
            for mode in MODES:
                case_id = f"{scenario}--{mode}"
                attempt = {"scenario": scenario, "mode": mode, "status": "started"}
                status["attempts"].append(attempt)
                dump(folder / "worker.json", status)
                try:
                    item = case_record(p, case_id, *parent_records(directory, name, scenario, mode))
                    item["schema"] = "m4-initial-load-observation/1"
                    attempt["status"] = "completed"
                except Exception as exc:
                    attempt.update(
                        status="failed",
                        error={"type": type(exc).__name__, "message": str(exc)[:500]},
                    )
                    item = {
                        "schema": "m4-initial-load-observation/1",
                        "id": case_id,
                        "status": "failed",
                        "error": attempt["error"],
                    }
                    failed = True
                dump(folder / "cases" / f"{case_id}.json", item)
                dump(folder / "worker.json", status)
                print(label, name, case_id, attempt["status"], flush=True)
        status["status"] = "failed" if failed else "completed"
        if failed:
            raise RuntimeError("Observation cases failed; inspect retained cases")
    except BaseException as exc:
        status.update(
            status="failed", error={"type": type(exc).__name__, "message": str(exc)[:500]}
        )
        raise
    finally:
        dump(folder / "worker.json", status)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("directory", type=Path)
    parser.add_argument("--kind", choices=("reference", "source", "observer"), required=True)
    parser.add_argument("--label", choices=("primary", "repeat"), required=True)
    parser.add_argument("--source")
    args = parser.parse_args()
    require(
        (args.kind == "reference") == (args.source is None),
        "Source identity required only for source/observer stages",
    )
    interrupted = False

    def stop(_signum, _frame):
        nonlocal interrupted
        if not interrupted:
            interrupted = True
            raise KeyboardInterrupt("Numerical stage interrupted")

    from experiments.platform_process import handled_signals

    for signum in handled_signals():
        signal.signal(signum, stop)
    if args.kind == "observer":
        observation(args.directory, args.label, args.source)
    else:
        numerical(args.directory, args.label, args.source)


if __name__ == "__main__":
    main()
