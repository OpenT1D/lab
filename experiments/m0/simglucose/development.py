"""Native feasibility only, restricted to development profiles; no evaluation ranking."""

import argparse
import contextlib
import importlib.metadata
import json
import os
import platform
import subprocess
import sys
import traceback
from datetime import datetime, timedelta
from pathlib import Path

import numpy as np
import pandas as pd
from recording import failure_status, interruption, record_native
from run import HERE, digest, write_json


def validate_settings(settings):
    if settings["development_profiles"] != ["adult#001", "adult#002"]:
        raise ValueError("This feasibility probe is restricted to the two development profiles")
    expected = {
        "duration_minutes": 2880,
        "warmup_minutes": 1440,
        "outer_interval_minutes": 3,
        "sensor": "Dexcom",
        "pump": "Insulet",
    }
    if any(settings[key] != value for key, value in expected.items()):
        raise ValueError("The native feasibility fixture requires its frozen timing and devices")


def execute(output, timeout_seconds=300):
    settings_path = HERE / "protocol-settings.json"
    settings = json.loads(settings_path.read_text())
    validate_settings(settings)
    output.mkdir(parents=True, exist_ok=False)
    manifest = {
        "status": "started",
        "purpose": "native feasibility; no announcement filtering or ranking",
        "settings": settings,
        "settings_sha256": digest(settings_path),
        "harness_sha256": digest(Path(__file__)),
        "recorder_sha256": digest(HERE / "recording.py"),
        "lock_sha256": digest(HERE / "uv.lock"),
        "revision": subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=HERE, text=True
        ).strip(),
        "worktree_dirty": bool(
            subprocess.check_output(["git", "status", "--porcelain"], cwd=HERE, text=True)
        ),
        "python": sys.version,
        "platform": platform.platform(),
        "sensor_seed": 101,
        "timeout_seconds": timeout_seconds,
        "pid": os.getpid(),
        "host": platform.node(),
        "packages": dict(
            sorted((p.metadata["Name"], p.version) for p in importlib.metadata.distributions())
        ),
        "cases": [],
    }
    write_json(output / "manifest.json", manifest)
    obj = None
    try:
        with (
            interruption(timeout_seconds),
            (output / "run.log").open("w") as log,
            contextlib.redirect_stdout(log),
            contextlib.redirect_stderr(log),
        ):
            os.environ["MPLBACKEND"] = "Agg"
            from simglucose.actuator.pump import InsulinPump
            from simglucose.controller.basal_bolus_ctrller import BBController
            from simglucose.controller.pid_ctrller import PIDController
            from simglucose.patient.t1dpatient import T1DPatient
            from simglucose.sensor.cgm import CGMSensor
            from simglucose.simulation.env import T1DSimEnv
            from simglucose.simulation.scenario import CustomScenario
            from simglucose.simulation.sim_engine import SimObj

            meals = [
                (hour + 24 * day, grams)
                for day in range(2)
                for hour, grams in settings["daily_meals_hours_grams"]
            ]
            for patient in settings["development_profiles"]:
                for name in ["basal_bolus", "pid"]:
                    obj = None
                    case = {"profile": patient, "controller": name, "status": "started"}
                    manifest["cases"].append(case)
                    write_json(output / "manifest.json", manifest)
                    controller = (
                        BBController(target=settings["basal_bolus"]["target"])
                        if name == "basal_bolus"
                        else PIDController(
                            **{key: settings["pid"][key] for key in ["P", "I", "D", "target"]}
                        )
                    )
                    env = T1DSimEnv(
                        T1DPatient.withName(patient),
                        CGMSensor.withName("Dexcom", seed=101),
                        InsulinPump.withName("Insulet"),
                        CustomScenario(datetime.fromisoformat(settings["start"]), meals),
                    )
                    obj = SimObj(
                        env,
                        controller,
                        timedelta(minutes=2880),
                        animate=False,
                        path=str(output / f"{patient}-{name}"),
                    )
                    frame = record_native(obj)
                    expected = pd.date_range(settings["start"], periods=961, freq="3min")
                    if not frame.index.equals(expected):
                        raise ValueError("Incomplete or unexpected development horizon")
                    if not np.isfinite(frame[["BG", "CGM", "LBGI", "HBGI", "Risk"]]).all().all():
                        raise ValueError("Non-finite development state")
                    if not np.isfinite(frame[["CHO", "insulin"]].iloc[:-1]).all().all():
                        raise ValueError("Non-finite development action")
                    expected_meals = np.zeros(960)
                    for hour, grams in meals:
                        expected_meals[int(hour * 20)] = grams / 3
                    if not np.array_equal(frame.CHO.iloc[:-1], expected_meals):
                        raise ValueError("Incorrect repeated meal schedule")
                    case.update(
                        status="completed",
                        rows=len(frame),
                        native_threshold_events=int(((frame.BG < 10) | (frame.BG > 600)).sum()),
                        warmup_end_BG=float(frame.BG.iloc[480]),
                        final_BG=float(frame.BG.iloc[-1]),
                        csv_sha256=digest(Path(obj.path) / f"{patient}.csv"),
                    )
                    write_json(output / "manifest.json", manifest)
        manifest["status"] = "completed"
    except BaseException as exc:
        manifest["status"] = failure_status(exc)
        manifest["error"] = str(exc)
        if manifest["cases"] and manifest["cases"][-1]["status"] == "started":
            manifest["cases"][-1].update(status=failure_status(exc), error=str(exc))
        (output / "failure.log").write_text(traceback.format_exc())
        raise
    finally:
        write_json(output / "manifest.json", manifest)
    print(json.dumps({"status": manifest["status"], "cases": manifest["cases"]}, indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--timeout-seconds", type=float, default=300)
    args = parser.parse_args()
    execute(args.output.resolve(), args.timeout_seconds)
