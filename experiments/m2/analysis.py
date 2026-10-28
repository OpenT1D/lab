"""Cambridge point-sample analysis and strict artifact reconstruction, without LT1."""

import hashlib
import json
import math
from datetime import UTC, datetime, timedelta
from pathlib import Path

from experiments.m1.artifacts import digest, strict_json
from experiments.m1.contracts import MEALS, number
from experiments.m1.validation import REVISION, Snapshot, hashes, text_value

from .run import ROOT, source_hashes, validate_config

VERSION = "ot014-plasma-point/1"
FIELDS = {
    "time_min",
    "controller_cgm_mg_dl",
    "controller_source_min",
    "new_announcements",
    "announced_history",
    "glucose_mg_dl",
    "raw_cgm_mg_dl",
    "sensor_available",
    "command_u_h",
    "delivered_u_h",
    "intake_g_min",
    "true_meal_g",
}


def exposure(weighted):
    duration = sum(w for _, w in weighted)
    if not duration:
        return {
            k: None
            for k in (
                "mean_mg_dl",
                "sd_mg_dl",
                "cv_percent",
                "in_range_percent",
                "below_70_percent",
                "below_54_percent",
                "above_180_percent",
                "above_250_percent",
            )
        } | {"observed_minutes": 0}
    mean = sum(v * w for v, w in weighted) / duration
    sd = math.sqrt(sum(w * (v - mean) ** 2 for v, w in weighted) / duration)
    result = {
        "observed_minutes": duration,
        "mean_mg_dl": mean,
        "sd_mg_dl": sd,
        "cv_percent": 100 * sd / mean if mean else None,
    }
    for key, predicate in {
        "in_range_percent": lambda v: 70 <= v <= 180,
        "below_70_percent": lambda v: v < 70,
        "below_54_percent": lambda v: v < 54,
        "above_180_percent": lambda v: v > 180,
        "above_250_percent": lambda v: v > 250,
    }.items():
        result[key] = 100 * sum(w for v, w in weighted if predicate(v)) / duration
    return result


def summarize(points):
    glucose, sensor = [], []
    insulin, observed = 0, 0
    latest_sample = None
    previous = -1
    for p in points:
        t = number(p["time_min"], "point time", 0)
        if t <= previous or t > 2880:
            raise ValueError("Non-increasing point time or point beyond horizon")
        previous = t
        for key in ("glucose_mg_dl", "delivered_u_h"):
            number(p[key], key, 0)
    for p, following in zip(points, points[1:]):
        if p["raw_cgm_mg_dl"] is not None:
            number(p["raw_cgm_mg_dl"], "raw sensor", 0)
            latest_sample = (p["raw_cgm_mg_dl"], p["sensor_available"])
        dt = max(0, min(following["time_min"], 2880) - max(p["time_min"], 1440))
        if not dt:
            continue
        glucose.append((p["glucose_mg_dl"], dt))
        # Five-minute left sample represents the following interval; unavailable samples
        # contribute no sensor exposure. This is not the held controller substitute.
        if latest_sample and latest_sample[1]:
            sensor.append((latest_sample[0], dt))
        insulin += p["delivered_u_h"] * dt / 60
        observed += dt
    return {
        "version": VERSION,
        "glucose": exposure(glucose),
        "sensor": exposure(sensor),
        "scheduled_minutes": 1440,
        "observed_minutes": observed,
        "missing_minutes": 1440 - observed,
        "delivered_insulin_u": insulin if observed else None,
    }


def validate_points(points, cfg):
    held = None
    history = {}
    start = datetime(2024, 7, 20, tzinfo=UTC)
    for i, p in enumerate(points):
        if not isinstance(p, dict) or set(p) != FIELDS:
            raise ValueError("Invalid Cambridge point schema")
        if type(p["time_min"]) not in (int, float) or p["time_min"] != i or i > 2880:
            raise ValueError("Unexpected supported Cambridge callback cadence")
        for key in (
            "glucose_mg_dl",
            "controller_cgm_mg_dl",
            "controller_source_min",
            "delivered_u_h",
            "intake_g_min",
            "true_meal_g",
        ):
            number(p[key], key, 0)
        number(p["command_u_h"], "command U/h")
        present = not (cfg["condition"] == "D" and 2160 <= i < 2190)
        if type(p["sensor_available"]) is not bool or p["sensor_available"] != present:
            raise ValueError("Sensor availability differs from protocol")
        if i % 5 == 0:
            number(p["raw_cgm_mg_dl"], "required sampled CGM", 0)
            if p["raw_cgm_mg_dl"] != p["glucose_mg_dl"]:
                raise ValueError("IdealCGM must sample plasma glucose")
            if present:
                held = (i, p["raw_cgm_mg_dl"])
        elif p["raw_cgm_mg_dl"] is not None:
            raise ValueError("Unexpected sensor sample between five-minute boundaries")
        if (p["controller_source_min"], p["controller_cgm_mg_dl"]) != held:
            raise ValueError("Controller observation differs from available sensor history")
        grams = dict(MEALS).get(i, 0)
        if p["true_meal_g"] != grams or p["intake_g_min"] != sum(
            g / 15 for t, g in MEALS if t <= i < t + 15
        ):
            raise ValueError("Actual meal event or intake differs from protocol")
        fraction = 1 if i < 1440 else {"A": 1, "B": 0, "C": 0.5, "D": 1}[cfg["condition"]]
        newly = []
        if grams * fraction:
            stamp = (
                (start + timedelta(minutes=i))
                .isoformat(timespec="milliseconds")
                .replace("+00:00", "Z")
            )
            announcement = {"time": stamp, "start": stamp, "carbs": grams * fraction}
            history[str(i)] = announcement
            newly = [{"id": str(i), **announcement}]
        if p["new_announcements"] != newly or p["announced_history"] != history:
            raise ValueError("Announcement delivery/history differs from permitted information")


def read_run(output):
    snapshot = Snapshot(output)
    manifest = strict_json(snapshot.read("manifest.json"))
    if not isinstance(manifest, dict) or manifest.get("schema") != "opent1d.cambridge/1":
        raise ValueError("Unsupported Cambridge manifest")
    status = manifest.get("status")
    if status not in ("started", "completed", "failed", "interrupted"):
        raise ValueError("Invalid run status")
    sealed = status != "started"
    count = manifest.get("completed_rows")
    if type(count) is not int or count < 0:
        raise ValueError("Invalid completed row count")
    hashes(manifest.get("files_sha256"), "artifact inventory")
    if sealed:
        number(manifest.get("elapsed_seconds"), "runtime", 0)
        files = manifest["files_sha256"]
        if not {"trace.jsonl", "native.jsonl", "run.log"} <= files.keys():
            raise ValueError("Incomplete required inventory")
        actual = {
            p.name
            for p in Path(output).iterdir()
            if p.name != "manifest.json" and not p.name.endswith(".tmp")
        }
        if actual != set(files):
            raise ValueError("Missing or uninventoried artifact")
        for name, expected in files.items():
            if hashlib.sha256(snapshot.read(name)).hexdigest() != expected:
                raise ValueError(f"Artifact changed: {name}")
    if status in ("failed", "interrupted"):
        text_value(manifest.get("error"), "failure reason")
    cfg = manifest.get("config")
    if cfg is not None:
        validate_config(cfg)
        if strict_json(snapshot.read("config.json")) != cfg:
            raise ValueError("Configuration ownership mismatch")
        hashes(manifest.get("source_sha256"), "implementation", source_hashes())
        if not isinstance(manifest.get("revision"), str) or not REVISION.fullmatch(
            manifest["revision"]
        ):
            raise ValueError("Missing implementation revision")
        if type(manifest.get("worktree_dirty")) is not bool:
            raise ValueError("Invalid dirty-worktree flag")
        for path in ("experiments/m2/analysis.py", "experiments/m2/run.py"):
            if (
                path in source_hashes()
                and manifest["source_sha256"].get(path) != source_hashes()[path]
            ):
                raise ValueError("Analysis changed; use recorded source revision")
        if hashlib.sha256(snapshot.read("protocol.md")).hexdigest() != digest(
            ROOT / "docs/research/m2-protocol.md"
        ):
            raise ValueError("Unsupported protocol bytes")
        for name in ("package-lock.json", "package.json", "baseline.json"):
            if snapshot.read(name) != (ROOT / "experiments/m0/lt1" / name).read_bytes():
                raise ValueError(f"Unsupported locked context: {name}")
    points, fragment = [], False
    raw = snapshot.read("trace.jsonl")
    for line in raw.splitlines(keepends=True):
        if not line.endswith(b"\n"):
            if status == "completed":
                raise ValueError("Truncated completed trace")
            fragment = True
            break
        points.append(strict_json(line))
    if points or status == "completed":
        if cfg is None:
            raise ValueError("Trace lacks configuration")
        runtime = strict_json(snapshot.read("runtime.json"))
        if (
            runtime.get("upstream_revision") != "9a6092065bd821f88691cd8d03b0550acd665573"
            or runtime.get("node") != "v22.22.2"
        ):
            raise ValueError("Missing or unsupported native provenance")
        text_value(runtime.get("platform"), "native platform")
        hashes(
            runtime.get("source_sha256"),
            "native sources",
            (
                "src/core/Simulator.ts",
                "src/core/models/Cambridge.ts",
                "src/core/controllers/MPC_Hovorka2004.ts",
                "src/core/controllers/PID.ts",
                "LICENSE.md",
            ),
        )
        if not runtime.get("packages") or not isinstance(runtime["packages"], dict):
            raise ValueError("Missing native package provenance")
        locked_packages = strict_json(snapshot.read("package-lock.json"))["packages"]
        if json.dumps(runtime["packages"], sort_keys=True) != json.dumps(
            locked_packages, sort_keys=True
        ):
            raise ValueError("Native package provenance differs from locked toolchain")
        settings = runtime.get("settings", {})
        for group in ("patient", "sensor", "pump", "controller", "solver", "seeds"):
            if not isinstance(settings.get(group), dict) or not settings[group]:
                raise ValueError(f"Missing effective settings: {group}")
        if settings["seeds"] != {
            "base": 101,
            "sensor": 102,
            "controller": 103,
            "pump": 104,
            "patient": 105,
        }:
            raise ValueError("Component seeds differ")
        required = {
            "patient": (
                "Gpeq BW k12 ka1 ka2 ka3 ke VI VG AG tmaxG SIT SID SIE EGP0 F01 tmaxI"
            ).split(),
            "sensor": "samplingTime min max resolution".split(),
            "pump": (
                "inc_bolus inc_basal max_bolus max_basal relerr_bolus "
                "abserr_bolus bias_basal relerr_basal abserr_basal"
            ).split(),
            "controller": (
                "samplingTime targetBG basalRate kP kI kD"
                if cfg["controller"] == "lt1_pid"
                else (
                    "samplingTime targetBG kaggr predictionHorizon "
                    "predictionStep lowerBound upperBound"
                )
            ).split(),
            "solver": ["relative_error_target", "default_dt_minutes"],
        }
        for group, keys in required.items():
            for key in keys:
                number(settings[group].get(key), f"{group}.{key}")
        if cfg["controller"] == "lt1_mpc":
            noise = settings["controller"].get("processNoise")
            if not isinstance(noise, dict) or set(noise) != {
                "Q1",
                "Q2",
                "x1",
                "x2",
                "x3",
                "S1",
                "S2",
                "I",
                "D1",
                "D2",
            }:
                raise ValueError("Missing MPC process noise configuration")
            for value in noise.values():
                number(value, "process noise", 0)
            measurement = settings["controller"].get("measurementNoise")
            if not isinstance(measurement, list) or len(measurement) != 1:
                raise ValueError("Missing MPC measurement noise configuration")
            number(measurement[0], "measurement noise", 0)
        if settings["sensor"]["samplingTime"] != 5 or settings["controller"]["samplingTime"] != 5:
            raise ValueError("Unsupported sensor/controller cadence")
        if settings["solver"].get("name") != "SolverRK1_2":
            raise ValueError("Missing native solver identity")
        validate_points(points, cfg)
    if sealed and count != len(points):
        raise ValueError("Trace row count differs from manifest")
    if status == "completed":
        if len(points) != 2881 or strict_json(snapshot.read("result.json")) != {
            "status": "completed"
        }:
            raise ValueError("False completion")
    snapshot.verify_unchanged()
    return {
        "manifest": manifest,
        "metrics": summarize(points),
        "input_sha256": snapshot.sha256(),
        "unsealed": not sealed,
        "discarded_trailing_fragment": fragment,
    }
