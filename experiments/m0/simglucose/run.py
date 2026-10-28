"""Reproduce the pinned native tutorial; no OpenT1D model or adapter."""

import argparse
import contextlib
import hashlib
import importlib.metadata
import json
import os
import platform
import subprocess
import sys
import time
import traceback
from datetime import datetime, timedelta
from pathlib import Path

import numpy as np
import pandas as pd
from recording import failure_status, interruption, record_native, write_json
from runtime_context import expected_context

HERE = Path(__file__).resolve().parent
CONFIG = json.loads((HERE / "config.json").read_text())


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def check_baseline(path, manifest, baseline=None):
    baseline = baseline or json.loads((HERE / "baseline.json").read_text())
    key = manifest["platform_key"]
    if key not in baseline["environments"]:
        raise ValueError(f"No reviewed baseline for {key}; retain output for review")
    expected, extension = expected_context(
        "m0",
        baseline,
        manifest.get("lock_sha256"),
        platform_key=key,
        actual_packages=manifest.get("packages"),
    )
    for field, value in expected.items():
        observed = digest(path) if field == "output_sha256" else manifest.get(field)
        matches = observed in value if field == "output_sha256" else observed == value
        if not matches:
            raise ValueError(f"Historical baseline differs: {field}; investigate before updating")
    result = {"matched": True, "platform_key": key, "output_sha256": digest(path)}
    if extension is not None:
        result["runtime_extension"] = extension
    return result


def validate(path):
    """Validate native history, including its structural terminal action cells."""
    frame = pd.read_csv(path, index_col="Time", parse_dates=True, float_precision="round_trip")
    expected = ["BG", "CGM", "CHO", "insulin", "LBGI", "HBGI", "Risk"]
    if list(frame.columns) != expected or len(frame) != 481:
        raise ValueError("Expected native schema and 481 state rows")
    clock = pd.date_range(CONFIG["start"], periods=481, freq="3min")
    if not frame.index.equals(clock):
        raise ValueError("Unexpected timestamps, cadence or horizon")
    states = frame[["BG", "CGM", "LBGI", "HBGI", "Risk"]].to_numpy()
    actions = frame[["CHO", "insulin"]].iloc[:-1].to_numpy()
    if not np.isfinite(states).all() or not np.isfinite(actions).all():
        raise ValueError("Non-finite state or nonterminal action")
    if not frame[["CHO", "insulin"]].iloc[-1].isna().all():
        raise ValueError("Expected structural terminal action NaNs")
    if (actions < 0).any():
        raise ValueError("Negative meal or delivered insulin")
    expected_meals = np.zeros(480)
    for hour, grams in CONFIG["meals_hours_grams"]:
        expected_meals[int(hour * 60 / 3)] = grams / 3
    if not np.array_equal(frame.CHO.iloc[:-1].to_numpy(), expected_meals):
        raise ValueError("Meal events differ from native tutorial")
    return {
        "rows": len(frame),
        "interval_minutes": 3,
        "meal_total_g": float(frame.CHO.iloc[:-1].sum() * 3),
        "delivered_insulin_U": float(frame.insulin.iloc[:-1].sum() * 3),
        "final_BG_mg_dL": float(frame.BG.iloc[-1]),
        "BG_min_mg_dL": float(frame.BG.min()),
        "BG_max_mg_dL": float(frame.BG.max()),
        "native_threshold_events": int(
            ((frame.BG.iloc[1:] < 10) | (frame.BG.iloc[1:] > 600)).sum()
        ),
        "glucose_semantics": "initial Gsub then three-minute means of Gsub; not plasma glucose",
        "sha256": digest(path),
    }


def compare(left, right, *, report_only=False):
    validate(left)
    validate(right)
    a = pd.read_csv(left, index_col="Time", float_precision="round_trip")
    b = pd.read_csv(right, index_col="Time", float_precision="round_trip")
    differences = {
        column: float(np.nanmax(np.abs(a[column].to_numpy() - b[column].to_numpy())))
        for column in a.columns
    }
    if not a.equals(b) and not report_only:
        raise ValueError(f"Replay differs; absolute differences by column={differences}")
    return {
        "exact_numeric_replay": a.equals(b),
        "max_absolute_by_column": differences,
        "tolerance_applied": False,
    }


def execute(output, timeout_seconds=300):
    output.mkdir(parents=True, exist_ok=False)
    started = time.monotonic()
    manifest = {
        "status": "started",
        "config": CONFIG,
        "python": sys.version,
        "python_version": platform.python_version(),
        "platform": platform.platform(),
        "platform_key": f"{platform.system()}/{platform.machine()}",
        "numpy_cpu_features": {
            key: bool(value) for key, value in np.core._multiarray_umath.__cpu_features__.items()
        },
        "numpy_disabled_features": os.environ.get("NPY_DISABLE_CPU_FEATURES"),
        "packages": dict(
            sorted((p.metadata["Name"], p.version) for p in importlib.metadata.distributions())
        ),
        "config_sha256": digest(HERE / "config.json"),
        "harness_sha256": digest(Path(__file__)),
        "recorder_sha256": digest(HERE / "recording.py"),
        "baseline_sha256": digest(HERE / "baseline.json"),
        "lock_sha256": digest(HERE / "uv.lock"),
        "opent1d_revision": subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=HERE, text=True
        ).strip(),
        "worktree_dirty": bool(
            subprocess.check_output(["git", "status", "--porcelain"], cwd=HERE, text=True)
        ),
        "command": sys.argv,
        "timeout_seconds": timeout_seconds,
        "pid": os.getpid(),
        "host": platform.node(),
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
            import simglucose
            from simglucose.actuator.pump import InsulinPump
            from simglucose.controller.basal_bolus_ctrller import BBController
            from simglucose.patient.t1dpatient import T1DPatient
            from simglucose.sensor.cgm import CGMSensor
            from simglucose.simulation.env import T1DSimEnv
            from simglucose.simulation.scenario import CustomScenario
            from simglucose.simulation.sim_engine import SimObj

            package = Path(simglucose.__file__).parent
            manifest["upstream_files_sha256"] = {
                str(p.relative_to(package)): digest(p)
                for p in sorted(package.rglob("*"))
                if p.suffix in {".py", ".csv"}
            }
            manifest["upstream_files_digest"] = hashlib.sha256(
                json.dumps(
                    manifest["upstream_files_sha256"], sort_keys=True, separators=(",", ":")
                ).encode()
            ).hexdigest()
            env = T1DSimEnv(
                T1DPatient.withName(CONFIG["patient"]),
                CGMSensor.withName(CONFIG["sensor"], seed=CONFIG["sensor_seed"]),
                InsulinPump.withName(CONFIG["pump"]),
                CustomScenario(
                    start_time=datetime.fromisoformat(CONFIG["start"]),
                    scenario=[tuple(m) for m in CONFIG["meals_hours_grams"]],
                ),
            )
            manifest["solver"] = {
                "method": "dopri5",
                "rtol": float(env.patient._odesolver._integrator.rtol),
                "atol": float(env.patient._odesolver._integrator.atol),
            }
            obj = SimObj(
                env,
                BBController(),
                timedelta(minutes=CONFIG["duration_minutes"]),
                animate=False,
                path=str(output / "first"),
            )
            manifest["phase"] = "first"
            write_json(output / "manifest.json", manifest)
            record_native(obj)
            first = output / "first" / f"{CONFIG['patient']}.csv"
            manifest["first"] = validate(first)
            manifest["phase"] = "reset"
            write_json(output / "manifest.json", manifest)
            obj.reset()
            obj.path = str(output / "reset")
            write_json(output / "manifest.json", manifest)
            record_native(obj)
            second = output / "reset" / f"{CONFIG['patient']}.csv"
            manifest["reset"] = validate(second)
            manifest["comparison"] = compare(first, second)
            manifest["baseline"] = check_baseline(first, manifest)
        manifest["status"] = "completed"
    except BaseException as exc:
        manifest["status"] = failure_status(exc)
        manifest["error"] = f"{type(exc).__name__}: {exc}"
        (output / "failure.log").write_text(traceback.format_exc())
        raise
    finally:
        manifest["elapsed_seconds"] = time.monotonic() - started
        write_json(output / "manifest.json", manifest)
    print(
        json.dumps(
            {
                "status": manifest["status"],
                "first": manifest["first"],
                "comparison": manifest["comparison"],
            },
            indent=2,
        )
    )


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path)
    parser.add_argument("--compare", nargs=2, type=Path)
    parser.add_argument("--report-differences", action="store_true")
    parser.add_argument("--timeout-seconds", type=float, default=300)
    args = parser.parse_args()
    if bool(args.output) == bool(args.compare):
        parser.error("Select --output or --compare")
    if args.compare:
        print(json.dumps(compare(*args.compare, report_only=args.report_differences), indent=2))
    else:
        execute(args.output.resolve(), args.timeout_seconds)


if __name__ == "__main__":
    main()
