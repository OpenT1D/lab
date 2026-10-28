"""IV-001 byte-identified reconstruction and duration-weighted numerical comparisons."""

import json
from datetime import timedelta
from pathlib import Path

from experiments.m1.artifacts import strict_json
from experiments.m1.contracts import Row, number
from experiments.m1.validation import HASH, REVISION, hashes, text_value
from experiments.m2.analysis import FIELDS, exposure

from .common import meals, sha, start, validate
from .conditions import announcements, available, boundary, parameter

STATUSES = ("started", "completed", "terminated", "input_exhausted", "failed", "interrupted")


def validate_trace(rows, cfg, initial=None):
    horizon = cfg["warmup"] + 1440
    events = meals(cfg)
    announced = {t: (m, g) for t, m, g in announcements(cfg, events)}
    if cfg["engine"] == "simglucose":
        held = None if initial is None else initial.get("cgm_mg_dl")
        source = 0
        if rows:
            number(held, "initial CGM", 0)
        for i, p in enumerate(rows):
            if not isinstance(p, dict) or set(p) != set(Row.__dataclass_fields__):
                raise ValueError("Invalid simglucose interval fields")
            for k in p:
                if k in ("terminal", "sensor_available"):
                    if type(p[k]) is not bool:
                        raise ValueError("Invalid boolean flag")
                else:
                    number(p[k], k, None if k in ("basal_u_min", "bolus_u_min") else 0)
            if p["start_min"] != i * 3 or p["end_min"] != (i + 1) * 3 or p["end_min"] > horizon:
                raise ValueError("Invalid simglucose interval clock")
            if p["terminal"] and i != len(rows) - 1:
                raise ValueError("Output after native stop")
            if (
                p["sensor_available"] != available(cfg, p["end_min"])
                or p["controller_source_min"] != source
                or p["controller_cgm_mg_dl"] != held
            ):
                raise ValueError("Controller observation differs from available sensor")
            if p["announced_g"] != announced.get(i * 3, (0, 0))[1] or p["true_meal_g"] != dict(
                events
            ).get(i * 3, 0):
                raise ValueError("Incorrect announcement interval")
            if available(cfg, p["end_min"]):
                held = p["raw_cgm_mg_dl"]
                source = p["end_min"]
    else:
        held = None
        history = {}
        for i, p in enumerate(rows):
            if not isinstance(p, dict) or set(p) != FIELDS:
                raise ValueError("Invalid Cambridge fields")
            if type(p["time_min"]) not in (int, float) or p["time_min"] != i or i > horizon:
                raise ValueError("Invalid Cambridge callback clock")
            for k in (
                "glucose_mg_dl",
                "controller_cgm_mg_dl",
                "controller_source_min",
                "delivered_u_h",
                "intake_g_min",
                "true_meal_g",
            ):
                number(p[k], k, 0)
            number(p["command_u_h"], "command")
            if type(p["sensor_available"]) is not bool or p["sensor_available"] != available(
                cfg, i
            ):
                raise ValueError("Invalid sensor availability")
            if i % 5 == 0:
                number(p["raw_cgm_mg_dl"], "raw CGM", 0)
                if p["raw_cgm_mg_dl"] != p["glucose_mg_dl"]:
                    raise ValueError("Ideal sensor differs from plasma glucose")
                if available(cfg, i):
                    held = (i, p["raw_cgm_mg_dl"])
            elif p["raw_cgm_mg_dl"] is not None:
                raise ValueError("Unexpected sensor sample")
            if (p["controller_source_min"], p["controller_cgm_mg_dl"]) != held:
                raise ValueError("Controller observation differs from available sensor")
            grams = dict(events).get(i, 0)
            if p["true_meal_g"] != grams or p["intake_g_min"] != sum(
                g / 15 for t, g in events if t <= i < t + 15
            ):
                raise ValueError("Incorrect true meal/ingestion")
            newly = []
            if i in announced:
                meal_min, announced_g = announced[i]
                stamp = (start(cfg) + timedelta(minutes=i)).isoformat(timespec="milliseconds") + "Z"
                meal_stamp = (start(cfg) + timedelta(minutes=meal_min)).isoformat(
                    timespec="milliseconds"
                ) + "Z"
                key = str(i + 1440 - cfg["warmup"])
                history[key] = {"time": stamp, "start": meal_stamp, "carbs": announced_g}
                newly = [dict(id=key, **history[key])]
            if p["new_announcements"] != newly or p["announced_history"] != history:
                raise ValueError("Incorrect announcement or future information")


def _read_run(folder):
    folder = Path(folder)
    entries = sorted(folder.iterdir())
    if any(p.is_symlink() or not p.is_file() for p in entries):
        raise ValueError("Evidence contains a non-regular or nested entry")
    files = {p.name: p.read_bytes() for p in entries}
    manifest = strict_json(files["manifest.json"])
    status = manifest.get("status")
    if manifest.get("schema") != "iv001.run/1" or status not in STATUSES:
        raise ValueError("Invalid IV-001 run manifest")
    sealed = status != "started"
    hashes(manifest.get("files_sha256"), "artifact inventory")
    if sealed:
        number(manifest.get("elapsed_seconds"), "runtime", 0)
        if set(files) - {"manifest.json"} != set(manifest["files_sha256"]):
            raise ValueError("Missing or uninventoried artifact")
        for name, expected in manifest["files_sha256"].items():
            if sha(files[name]) != expected:
                raise ValueError(f"Artifact changed: {name}")
        if not {"trace.jsonl", "native.jsonl", "run.log"} <= files.keys():
            raise ValueError("Incomplete required inventory")
    if status in ("failed", "interrupted"):
        text_value(manifest.get("error"), "failure reason")
    cfg = None
    try:
        cfg = validate(strict_json(files["config.json"]))
    except (ValueError, KeyError):
        if status not in ("failed", "interrupted", "started"):
            raise
    raw = files.get("trace.jsonl", b"")
    lines = raw.splitlines(keepends=True)
    tail = 0
    sensor_tail = 0
    if lines and not lines[-1].endswith(b"\n"):
        if status in ("completed", "terminated", "input_exhausted"):
            raise ValueError("Successful trace contains unfinished row")
        tail = len(lines.pop())
    rows = [strict_json(line) for line in lines]
    if rows and cfg is None:
        raise ValueError("Trace without valid configuration")
    if cfg is not None and (
        "source_sha256" in manifest
        or rows
        or status in ("completed", "terminated", "input_exhausted")
    ):
        hashes(
            manifest.get("source_sha256"),
            "implementation sources",
            (
                "experiments/verification/run.py",
                "experiments/verification/analysis.py",
                "experiments/verification/simglucose_worker.py",
                "experiments/verification/cambridge_worker.mjs",
            ),
        )
        hashes(
            manifest.get("locks_sha256"),
            "locks",
            (
                "uv.lock",
                "experiments/m0/simglucose/uv.lock",
                "experiments/m0/lt1/package-lock.json",
            ),
        )
        if (
            not REVISION.fullmatch(manifest.get("revision", ""))
            or type(manifest.get("dirty")) is not bool
        ):
            raise ValueError("Missing implementation revision/dirty state")
        if sha(files.get("protocol.md", b"")) != manifest.get("protocol_sha256"):
            raise ValueError("Missing or changed protocol")
        for name, value in manifest["locks_sha256"].items():
            if sha(files.get(name.replace("/", "_"), b"")) != value:
                raise ValueError("Missing or changed dependency lock")
    if rows or status in ("completed", "terminated", "input_exhausted"):
        runtime = strict_json(files["runtime.json"])
        validate_runtime(runtime, cfg)
        if cfg.get("variant") is not None:
            if strict_json(files["boundary.json"]) != boundary(cfg, meals(cfg)):
                raise ValueError("Robustness boundary differs from prescribed condition")
            sensor_lines = files["sensor-audit.jsonl"].splitlines(keepends=True)
            if sensor_lines and not sensor_lines[-1].endswith(b"\n"):
                if status in ("completed", "terminated", "input_exhausted"):
                    raise ValueError("Successful sensor audit contains unfinished row")
                sensor_tail = len(sensor_lines.pop())
            samples = [strict_json(line) for line in sensor_lines]
            if cfg["engine"] == "simglucose":
                # Native reset measures twice at t=0; retain both calls in the audit.
                if (
                    len(samples) < 2
                    or not isinstance(samples[0], dict)
                    or set(samples[0]) != {"time_min", "raw"}
                ):
                    raise ValueError("Missing native reset sensor calls")
                number(samples[0]["time_min"], "first sensor reset time", 0)
                if samples[0]["time_min"] != 0:
                    raise ValueError("Invalid first sensor reset time")
                number(samples[0]["raw"], "first reset sample", 0)
                samples = samples[1:]
                if samples[0]["raw"] != strict_json(files["initial.json"])["cgm_mg_dl"]:
                    raise ValueError("Initial sensor sample differs")
            for i, sample in enumerate(samples):
                if (
                    set(sample) != {"time_min", "raw"}
                    or type(sample["time_min"]) not in (int, float)
                    or sample["time_min"] != i
                ):
                    raise ValueError("Native sensor generation clock differs")
                if cfg["engine"] == "simglucose" or i % 5 == 0:
                    number(sample["raw"], "generated sensor value", 0)
                elif sample["raw"] is not None:
                    raise ValueError("Unexpected generated sensor sample")
            observed_end = (
                rows[-1]["end_min" if cfg["engine"] == "simglucose" else "time_min"] if rows else -1
            )
            if len(samples) < observed_end + 1 or (
                status in ("completed", "terminated") and len(samples) != observed_end + 1
            ):
                raise ValueError("Missing or excess native sensor generation")
            for row in rows:
                value = (
                    sum(
                        samples[t]["raw"] / 3
                        for t in range(row["start_min"] + 1, row["end_min"] + 1)
                    )
                    if cfg["engine"] == "simglucose"
                    else samples[row["time_min"]]["raw"]
                )
                if value != row["raw_cgm_mg_dl"]:
                    raise ValueError("Trace differs from generated native sensor values")
        expected = (
            "a6f6777586c860457a2a1e6cce6d0bd3fd33d1cc"
            if cfg["engine"] == "simglucose"
            else "9a6092065bd821f88691cd8d03b0550acd665573"
        )
        if runtime.get("upstream_revision") != expected:
            raise ValueError("Missing native provenance")
        source = runtime.get(
            "upstream_files_sha256" if cfg["engine"] == "simglucose" else "source_sha256"
        )
        hashes(source, "native source")
        if not source or not isinstance(runtime.get("packages"), dict) or not runtime["packages"]:
            raise ValueError("Empty native provenance")
        solver = runtime["settings"]["solver"]
        if cfg["engine"] == "simglucose":
            if sha(
                json.dumps(source, sort_keys=True, separators=(",", ":")).encode()
            ) != runtime.get("upstream_files_digest"):
                raise ValueError("Native source fingerprint differs")
            expected_solver = {"rtol": 1e-6 / cfg["factor"], "atol": 1e-12 / cfg["factor"]}
            if solver.get("method") != "dopri5" or solver.get("effective") != expected_solver:
                raise ValueError("Effective solver settings differ")
            for v in solver["effective"].values():
                number(v, "solver tolerance", 0)
        elif (
            solver.get("effective_relative") != 0.001 / cfg["factor"]
            or solver.get("name") != "SolverRK1_2"
        ):
            raise ValueError("Effective solver settings differ")
        validate_trace(
            rows, cfg, strict_json(files["initial.json"]) if "initial.json" in files else None
        )
        end = rows[-1]["end_min" if cfg["engine"] == "simglucose" else "time_min"] if rows else 0
        if status == "completed" and (
            end != cfg["warmup"] + 1440 or (cfg["engine"] == "simglucose" and rows[-1]["terminal"])
        ):
            raise ValueError("False completion: native horizon not reached")
        if status == "terminated" and (cfg["engine"] != "simglucose" or not rows[-1]["terminal"]):
            raise ValueError("False native stop")
        if status in ("completed", "terminated", "input_exhausted"):
            result = strict_json(files["result.json"])
            if (
                result.get("status") != status
                or type(manifest.get("returncode")) is not int
                or manifest["returncode"] != 0
            ):
                raise ValueError("Worker and supervisor disagree")
        if status == "input_exhausted" and (cfg["mode"] != "replay" or end >= cfg["warmup"] + 1440):
            raise ValueError("False input exhaustion")
        if cfg["mode"] == "replay":
            replay = strict_json(files["replay.json"])
            if not HASH.fullmatch(replay.get("trace_sha256", "")):
                raise ValueError("Missing replay source identity")
            if replay.get("config") != cfg | dict(factor=1, mode="feedback"):
                raise ValueError("Replay configuration differs")
            for p, q in zip(rows, replay["rows"]):
                keys = (
                    ("basal_u_min", "bolus_u_min")
                    if cfg["engine"] == "simglucose"
                    else ("command_u_h",)
                )
                if any(p[k] != q[k] for k in keys):
                    raise ValueError("Replayed commands differ")
            if len(rows) > len(replay["rows"]):
                raise ValueError("Replay exceeded available input")
            if status == "input_exhausted" and len(rows) != len(replay["rows"]):
                raise ValueError("False input exhaustion")
    return dict(
        config=cfg,
        status=status,
        manifest=manifest,
        rows=rows,
        unfinished_bytes=tail,
        unfinished_sensor_bytes=sensor_tail,
        inputs_sha256={name: sha(raw) for name, raw in files.items()},
    )


def intervals(run):
    cfg = run["config"]
    if cfg is None:
        return []
    rows = run["rows"]
    if cfg["engine"] == "simglucose":
        return [
            (
                p["start_min"] - cfg["warmup"],
                p["end_min"] - cfg["warmup"],
                p["glucose_mg_dl"],
                p["delivered_u_min"],
                p["true_meal_g"] / 3,
            )
            for p in rows
        ]
    return [
        (
            p["time_min"] - cfg["warmup"],
            q["time_min"] - cfg["warmup"],
            p["glucose_mg_dl"],
            p["delivered_u_h"] / 60,
            p["intake_g_min"],
        )
        for p, q in zip(rows, rows[1:])
    ]


def summarize(run):
    values = [
        (max(a, 0), min(b, 1440), g, u, m) for a, b, g, u, m in intervals(run) if b > 0 and a < 1440
    ]
    duration = sum(b - a for a, b, *_ in values)
    return dict(
        glucose=exposure([(g, b - a) for a, b, g, _, _ in values]),
        observed_minutes=duration,
        missing_minutes=1440 - duration,
        delivered_insulin_u=sum((b - a) * u for a, b, _, u, _ in values) if duration else None,
    )


def compare(left, right, limits=None, fixed=False):
    if any(
        left["config"][k] != right["config"][k] for k in ("engine", "profile", "seed", "controller")
    ):
        raise ValueError("No cross-compartment pooling")
    left_intervals = {
        (a, b): (g, u, m) for a, b, g, u, m in intervals(left) if a >= 0 and b <= 1440
    }
    right_intervals = {
        (a, b): (g, u, m) for a, b, g, u, m in intervals(right) if a >= 0 and b <= 1440
    }
    common = sorted(left_intervals.keys() & right_intervals.keys())
    duration = sum(b - a for a, b in common)
    # Fixed inputs must match over the entire common trace, including warmup.
    if fixed:
        la = {(a, b): (u, m) for a, b, _, u, m in intervals(left)}
        ra = {(a, b): (u, m) for a, b, _, u, m in intervals(right)}
        if any(la[k] != ra[k] for k in la.keys() & ra.keys()):
            raise ValueError("Fixed-input meal or modeled delivery differs")
    deltas = [(abs(left_intervals[k][0] - right_intervals[k][0]), k[1] - k[0]) for k in common]
    lm = exposure([(left_intervals[k][0], k[1] - k[0]) for k in common])
    rm = exposure([(right_intervals[k][0], k[1] - k[0]) for k in common])
    metrics = dict(
        max_abs_glucose_mg_dl=max((x for x, _ in deltas), default=None),
        mean_abs_glucose_mg_dl=sum(x * w for x, w in deltas) / duration if duration else None,
        max_abs_exposure_pp=max(
            (abs(lm[k] - rm[k]) for k in lm if k.endswith("_percent") and k != "cv_percent"),
            default=None,
        )
        if duration
        else None,
        abs_insulin_u=abs(
            sum((k[1] - k[0]) * (left_intervals[k][1] - right_intervals[k][1]) for k in common)
        )
        if duration
        else None,
    )
    sufficient = duration == 1440 and left["status"] == right["status"] == "completed"
    classification = "inconclusive"
    if sufficient and limits is not None:
        classification = (
            "stable_within_prespecified_limits"
            if all(metrics[k] <= v for k, v in limits.items())
            else "sensitive"
        )
    return dict(
        **metrics,
        common_scored_minutes=duration,
        excluded_minutes=1440 - duration,
        statuses=[left["status"], right["status"]],
        end_minutes=[intervals(x)[-1][1] if intervals(x) else None for x in (left, right)],
        classification=classification,
        fixed_input=fixed,
    )


def read_run(folder):
    """Normalize malformed required structures to a useful artifact error."""
    try:
        return _read_run(folder)
    except (KeyError, TypeError, AttributeError, IndexError) as error:
        raise ValueError(f"Invalid or missing required IV-001 artifact field: {error}") from error


def validate_runtime(runtime, cfg):
    """Require the model, controller and environment context, not just a revision label."""
    settings = runtime.get("settings")
    if not isinstance(settings, dict):
        raise ValueError("Missing effective settings")
    packages = runtime.get("packages")
    if not isinstance(packages, dict):
        raise ValueError("Missing native packages")
    if cfg["engine"] == "simglucose":
        hashes(
            runtime.get("upstream_files_sha256"),
            "native source",
            (
                "patient/t1dpatient.py",
                "simulation/env.py",
                "sensor/cgm.py",
                "actuator/pump.py",
                "controller/pid_ctrller.py",
                "controller/basal_bolus_ctrller.py",
                "params/vpatient_params.csv",
                "params/Quest.csv",
            ),
        )
        for key in ("simglucose", "numpy", "scipy", "pandas", "setuptools"):
            text_value(packages.get(key), f"package {key}")
        if packages["setuptools"] != "80.9.0":
            raise ValueError("Unexpected compatibility runtime")
        text_value(runtime.get("python"), "native Python")
        params = settings.get("parameters")
        if not isinstance(params, dict) or params.get("Name") != cfg["profile"]:
            raise ValueError("Missing or mismatched physiological parameters")
        for key in ("BW", "Vg", "u2ss", "kabs", "kd"):
            number(params.get(key), f"patient.{key}", 0)
        for key, value in params.items():
            if key != "Name":
                number(value, f"patient.{key}")
        if (
            settings.get("sensor") != "Dexcom"
            or settings.get("pump") != "Insulet"
            or type(settings.get("sensor_seed")) is not int
            or settings["sensor_seed"] != cfg["seed"]
            or settings.get("random_initialization") is not False
            or settings.get("start") != start(cfg).isoformat()
        ):
            raise ValueError("Missing or changed native device/initialization settings")
        controller = settings.get("controller")
        if not isinstance(controller, dict):
            raise ValueError("Missing controller settings")
        for key in ("target", "P", "I", "D"):
            number(controller.get(key), f"controller.{key}")
        if cfg["controller"] == "basal_bolus":
            for key in ("CR_g_U", "CF_mg_dl_U"):
                if number(controller.get(key), f"controller.{key}", 0) <= 0:
                    raise ValueError("Invalid basal-bolus profile setting")
    else:
        hashes(
            runtime.get("source_sha256"),
            "native source",
            (
                "src/core/Simulator.ts",
                "src/core/models/Cambridge.ts",
                "src/core/controllers/PID.ts",
                "src/core/controllers/MPC_Hovorka2004.ts",
                "src/core/solvers/SolverRK1_2.ts",
                "LICENSE.md",
            ),
        )
        if runtime.get("node") != "v22.22.2":
            raise ValueError("Unexpected native Node runtime")
        text_value(runtime.get("platform"), "native platform")
        for key in ("node_modules/typescript", "node_modules/ts-node"):
            if not isinstance(packages.get(key), dict):
                raise ValueError("Missing locked TypeScript toolchain")
            text_value(packages[key].get("version"), key)
        required = {
            "patient": "Gpeq BW k12 ka1 ka2 ka3 ke VI VG AG tmaxG SIT SID SIE EGP0 F01 tmaxI",
            "sensor": "samplingTime min max resolution",
            "pump": (
                "inc_bolus inc_basal max_bolus max_basal relerr_bolus "
                "abserr_bolus bias_basal relerr_basal abserr_basal"
            ),
            "controller": "samplingTime targetBG basalRate kP kI kD"
            if cfg["controller"] == "lt1_pid"
            else (
                "samplingTime targetBG kaggr predictionHorizon predictionStep lowerBound upperBound"
            ),
        }
        for group, fields in required.items():
            if not isinstance(settings.get(group), dict):
                raise ValueError(f"Missing effective settings: {group}")
            for key in fields.split():
                number(settings[group].get(key), f"{group}.{key}")
        if settings.get("seeds") != dict(
            base=101, sensor=102, controller=103, pump=104, patient=105
        ):
            raise ValueError("Component seeds differ")
        if settings.get("start") != start(cfg).isoformat(timespec="milliseconds") + "Z":
            raise ValueError("Native initialization clock differs")
        if cfg["controller"] == "lt1_mpc":
            noise = settings["controller"].get("processNoise")
            if not isinstance(noise, dict) or set(noise) != set(
                "Q1 Q2 x1 x2 x3 S1 S2 I D1 D2".split()
            ):
                raise ValueError("Missing MPC process noise")
            for value in noise.values():
                number(value, "process noise", 0)
            measurement = settings["controller"].get("measurementNoise")
            if not isinstance(measurement, list) or len(measurement) != 1:
                raise ValueError("Missing MPC measurement noise")
            number(measurement[0], "measurement noise", 0)

    if cfg.get("variant") is not None:
        probe = settings.get("parameter_probe")
        if not isinstance(probe, dict) or probe.get("change") != parameter(cfg):
            raise ValueError("Missing or changed parameter probe provenance")
        original = probe.get("original")
        actual = settings["parameters" if cfg["engine"] == "simglucose" else "patient"]
        if not isinstance(original, dict) or set(original) != set(actual):
            raise ValueError("Missing original parameter vector")
        text_value(probe.get("reset"), "native reset semantics")
        for key, value in original.items():
            if key in ("Name", "name"):
                text_value(value, "original profile name")
                if key == "Name" and value != cfg["profile"]:
                    raise ValueError("Original profile differs")
            else:
                number(value, f"original parameter {key}")
        expected = dict(original)
        change = parameter(cfg)
        if change:
            if number(original[change["name"]], "positive native parameter", 0) <= 0:
                raise ValueError("Expected positive local parameter")
            expected[change["name"]] *= change["factor"]
        if expected != actual:
            raise ValueError("Effective parameters differ from the one-factor condition")
