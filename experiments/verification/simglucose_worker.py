"""IV-001 native simglucose probe; equations and devices remain upstream-owned."""

import hashlib
import importlib.metadata
import json
import os
import platform
import sys
import traceback
from dataclasses import asdict
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import simglucose
from simglucose.simulation.scenario import CustomScenario

from experiments.m0.simglucose.recording import write_json
from experiments.m1.adapter import Simglucose
from experiments.m1.artifacts import digest, strict_json
from experiments.m1.contracts import Action, Observation
from experiments.m1.control import Controller

from .common import ROOT, emit, meals, replay_input, start, validate
from .conditions import announcements, available, parameter


def run(output):
    cfg = validate(strict_json((output / "config.json").read_bytes()))
    replay = replay_input(output / "replay.json", cfg) if cfg["mode"] == "replay" else None
    package = Path(simglucose.__file__).parent
    upstream = {
        str(p.relative_to(package)): digest(p)
        for p in sorted(package.rglob("*"))
        if p.suffix in (".py", ".csv")
    }
    fingerprint = hashlib.sha256(
        json.dumps(upstream, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    baseline = strict_json((ROOT / "experiments/m0/simglucose/baseline.json").read_bytes())
    if fingerprint not in {x["upstream_files_digest"] for x in baseline["environments"].values()}:
        raise ValueError("Native source differs from reviewed M0 fingerprint")
    runtime = dict(
        upstream_revision="a6f6777586c860457a2a1e6cce6d0bd3fd33d1cc",
        upstream_files_sha256=upstream,
        upstream_files_digest=fingerprint,
        python=sys.version,
        platform=platform.platform(),
        packages=dict(
            sorted((p.metadata["Name"], p.version) for p in importlib.metadata.distributions())
        ),
        numpy_disabled_features=os.environ.get("NPY_DISABLE_CPU_FEATURES"),
        numpy_cpu_features={
            k: bool(v) for k, v in np.core._multiarray_umath.__cpu_features__.items()
        },
    )
    write_json(output / "runtime.json", runtime)
    events = meals(cfg)
    engine = Simglucose(cfg["profile"], cfg["seed"], events)
    engine._start = start(cfg)
    engine._env.scenario = CustomScenario(engine._start, [(t / 60, g) for t, g in events])
    original_parameters = engine._env.patient._params.copy()
    change = parameter(cfg)
    if change:
        engine._env.patient._params = original_parameters.copy()
        engine._env.patient._params[change["name"]] *= change["factor"]
    if cfg.get("variant") is not None:
        measure = engine._env.sensor.measure

        def audited_measure(patient):
            value = measure(patient)
            with (output / "sensor-audit.jsonl").open("a") as stream:
                emit(stream, {"time_min": float(patient.t), "raw": float(value)})
            return value

        engine._env.sensor.measure = audited_measure
    controller = Controller(SimpleNamespace(**cfg))
    controller.reset()
    snap = engine.reset()
    solver = engine._env.patient._odesolver
    native = {"rtol": float(solver._integrator.rtol), "atol": float(solver._integrator.atol)}
    if native != {"rtol": 1e-6, "atol": 1e-12}:
        raise ValueError("Unexpected native solver defaults")
    before = solver.y.copy(), solver.t
    if cfg["factor"] != 1:
        solver.set_integrator("dopri5", **{k: v / cfg["factor"] for k, v in native.items()})
    if not np.array_equal(before[0], solver.y) or before[1] != solver.t:
        raise ValueError("Tolerance configuration changed native initial state/time")
    runtime["settings"] = dict(
        solver=dict(
            method="dopri5",
            native=native,
            effective={k: float(getattr(solver._integrator, k)) for k in native},
        ),
        parameters={
            k: (str(v) if isinstance(v, str) else float(v))
            for k, v in engine._env.patient._params.items()
        },
        start=engine._start.isoformat(),
        sensor="Dexcom",
        pump="Insulet",
        sensor_seed=cfg["seed"],
        random_initialization=False,
        controller=dict(target=140, P=0.001, I=0.00001, D=0.001),
        glucose="interval mean subcutaneous mg/dL",
        insulin="modeled U/min",
    )
    if cfg["controller"] == "basal_bolus":
        entry = controller._native.quest[controller._native.quest.Name == cfg["profile"]].iloc[0]
        runtime["settings"]["controller"].update(CR_g_U=float(entry.CR), CF_mg_dl_U=float(entry.CF))
    if cfg.get("variant") is not None:
        runtime["settings"]["parameter_probe"] = {
            "change": change,
            "original": {
                k: str(v) if isinstance(v, str) else float(v)
                for k, v in original_parameters.items()
            },
            "reset": "native table initial state retained; controller settings unchanged",
        }
    write_json(output / "runtime.json", runtime)
    write_json(output / "initial.json", asdict(snap))
    announce = {t: g for t, _, g in announcements(cfg, events)}
    held = (snap.time_min, snap.cgm_mg_dl)
    horizon = cfg["warmup"] + 1440
    limit = replay["rows"][-1]["end_min"] if replay else horizon
    try:
        with (
            (output / "trace.jsonl").open("a") as trace,
            (output / "native.jsonl").open("a") as native_trace,
        ):
            while snap.time_min < limit and not snap.terminal:
                if os.environ.get("OPENT1D_PARENT_PID") and os.getppid() != int(
                    os.environ["OPENT1D_PARENT_PID"]
                ):
                    raise RuntimeError("Supervisor disappeared")
                announced = float(announce.get(snap.time_min, 0))
                observation = Observation(
                    snap.time_min, held[1], held[0], available(cfg, snap.time_min)
                )
                if replay:
                    p = replay["rows"][snap.time_min // 3]
                    if p["start_min"] != snap.time_min:
                        raise ValueError("Replay clock mismatch")
                    action = Action(p["basal_u_min"], p["bolus_u_min"])
                else:
                    action = controller.command(observation, announced)
                following = engine.step(action)
                emit(
                    native_trace,
                    dict(
                        time_min=following.time_min, state=engine._env.patient._odesolver.y.tolist()
                    ),
                )
                emit(
                    trace,
                    dict(
                        start_min=snap.time_min,
                        end_min=following.time_min,
                        glucose_mg_dl=following.glucose_mg_dl,
                        raw_cgm_mg_dl=following.cgm_mg_dl,
                        sensor_available=available(cfg, following.time_min),
                        controller_cgm_mg_dl=observation.glucose_mg_dl,
                        controller_source_min=observation.source_time_min,
                        announced_g=announced,
                        true_meal_g=following.true_meal_g,
                        basal_u_min=action.basal_u_min,
                        bolus_u_min=action.bolus_u_min,
                        delivered_u_min=following.delivered_u_min,
                        terminal=following.terminal,
                    ),
                )
                snap = following
                if available(cfg, snap.time_min):
                    held = (snap.time_min, snap.cgm_mg_dl)
        return (
            "terminated"
            if snap.terminal
            else "completed"
            if snap.time_min == horizon
            else "input_exhausted"
        )
    finally:
        # A diagnostic error must not replace an active simulation error.
        active = sys.exc_info()[0] is not None
        try:
            (output / "native-diagnostic.csv").write_text(engine.native_history().to_csv())
        except Exception:
            (output / "diagnostic-error.log").write_text(traceback.format_exc())
            if not active:
                raise


if __name__ == "__main__":
    target = Path(sys.argv[1])
    try:
        write_json(target / "result.json", {"status": run(target)})
    except BaseException as error:
        (target / "failure.log").write_text(traceback.format_exc())
        write_json(target / "result.json", {"status": "failed", "error": str(error)})
        raise
