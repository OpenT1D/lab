"""Strict C1 simglucose development reader; no native simulation imports."""

import hashlib
import json
from pathlib import Path

from experiments.m1.artifacts import strict_json
from experiments.m1.contracts import MEALS, Row, number, validate_rows
from experiments.m1.metrics import summarize
from experiments.m1.validation import HASH, REVISION, validate_warnings

from .core import TrendOverlay, finite
from .feedback import FeedbackController
from .simglucose_dev import SCHEMA, Config


def lines(path, name, *, sealed):
    result = []
    for raw in (path / name).read_bytes().splitlines(keepends=True):
        if not raw.endswith(b"\n"):
            if sealed:
                raise ValueError(f"Truncated sealed {name}")
            break
        result.append(strict_json(raw))
    return result


def validate_command(command, row, cfg):
    required = {
        "time_min",
        "controller_source_min",
        "controller_cgm_mg_dl",
        "sensor_available",
        "announced_g",
        "base_basal_u_h",
        "base_bolus_u_min",
        "final_basal_u_h",
        "final_bolus_u_min",
        "reason",
    }
    if cfg.method == "trend_overlay":
        method_fields = {"extra_u_h", "inventory_u", "rise_mg_dl_min"}
    elif cfg.method == "bounded_pid":
        method_fields = {"pid_correction_u_h", "requested_u_h"}
    else:
        method_fields = {
            "raw_total_u_h",
            "requested_total_u_h",
            "correction_u_h",
            "integral_mg_dl_min",
            "rise_mg_dl_min",
            "integral_frozen",
            "total_clamped",
            "slew_limited",
        }
    if not isinstance(command, dict) or set(command) != required | method_fields:
        raise ValueError("Invalid C1 command audit schema")
    if (
        command["time_min"] != row.start_min
        or command["controller_source_min"] != row.controller_source_min
        or command["controller_cgm_mg_dl"] != row.controller_cgm_mg_dl
        or command["announced_g"] != row.announced_g
        or command["final_basal_u_h"] / 60 != row.basal_u_min
        or command["final_bolus_u_min"] != row.bolus_u_min
        or command["base_bolus_u_min"] != row.bolus_u_min
    ):
        raise ValueError("C1 command/trace mismatch")
    if type(command["sensor_available"]) is not bool or command["sensor_available"] != (
        row.controller_source_min == row.start_min
    ):
        raise ValueError("C1 controller observation availability mismatch")
    for key in ("base_basal_u_h", "base_bolus_u_min", "final_basal_u_h", "final_bolus_u_min"):
        finite(command[key], key, 0)
    if not 0 <= command["final_basal_u_h"] <= cfg.settings.max_total_u_h:
        raise ValueError("C1 basal limit violated")
    if cfg.method == "trend_overlay":
        for key in ("extra_u_h", "inventory_u", "rise_mg_dl_min"):
            finite(command[key], key, 0)
        if command["base_basal_u_h"] + command["extra_u_h"] != command["final_basal_u_h"]:
            raise ValueError("C1 overlay amount mismatch")
        if not 0 <= command["extra_u_h"] <= cfg.settings.max_extra_u_h:
            raise ValueError("C1 overlay limit violated")
        if not command["sensor_available"] and command["extra_u_h"]:
            raise ValueError("Overlay on masked observation")
        if row.controller_cgm_mg_dl <= cfg.settings.low_cutoff_mg_dl and command["extra_u_h"]:
            raise ValueError("Overlay through low-glucose gate")
    elif cfg.method == "bounded_pid":
        finite(command["pid_correction_u_h"], "PID correction")
        if (
            not 0
            <= finite(command["requested_u_h"], "requested rate")
            <= cfg.settings.max_total_u_h
        ):
            raise ValueError("Comparator requested rate violates limit")
    else:
        for key in ("raw_total_u_h", "correction_u_h", "integral_mg_dl_min", "rise_mg_dl_min"):
            finite(command[key], key)
        requested = finite(command["requested_total_u_h"], "requested total rate", 0)
        if requested > cfg.settings.max_total_u_h:
            raise ValueError("Feedback requested rate violates limit")
        for key in ("integral_frozen", "total_clamped", "slew_limited"):
            if type(command[key]) is not bool:
                raise ValueError("Feedback limit flag must be Boolean")
        if command["correction_u_h"] != command["final_basal_u_h"] - command["base_basal_u_h"]:
            raise ValueError("Feedback correction differs from final action")
        if command["total_clamped"] != (command["raw_total_u_h"] != requested):
            raise ValueError("Feedback clamp flag differs")
        if not command["sensor_available"] and (
            command["final_basal_u_h"] != command["base_basal_u_h"]
            or command["integral_frozen"]
            or command["total_clamped"]
            or command["slew_limited"]
        ):
            raise ValueError("Feedback altered held-observation fallback")


def replay_commands(rows, commands, cfg):
    """Check saved commands against the declared state update without a simulator."""
    overlay = TrendOverlay(cfg.settings) if cfg.method == "trend_overlay" else None
    feedback = FeedbackController(cfg.settings) if cfg.method.startswith("feedback_") else None
    pid_integral = 0.0
    pid_previous = 0.0
    previous_final = None
    for row, command in zip(rows, commands):
        glucose = row.controller_cgm_mg_dl
        base = command["base_basal_u_h"]
        if feedback is not None:
            decision = feedback.command(
                time_min=row.start_min,
                glucose_mg_dl=glucose,
                source_time_min=row.controller_source_min,
                available=command["sensor_available"],
                base_u_h=base,
            )
            expected = (
                decision.raw_total_u_h,
                decision.requested_total_u_h,
                decision.final_u_h,
                decision.correction_u_h,
                decision.integral_mg_dl_min,
                decision.rise_mg_dl_min,
                decision.integral_frozen,
                decision.total_clamped,
                decision.slew_limited,
                decision.reason,
            )
            actual = (
                command["raw_total_u_h"],
                command["requested_total_u_h"],
                command["final_basal_u_h"],
                command["correction_u_h"],
                command["integral_mg_dl_min"],
                command["rise_mg_dl_min"],
                command["integral_frozen"],
                command["total_clamped"],
                command["slew_limited"],
                command["reason"],
            )
        elif overlay is not None:
            decision = overlay.command(
                time_min=row.start_min,
                glucose_mg_dl=glucose,
                source_time_min=row.controller_source_min,
                available=command["sensor_available"],
                base_u_h=base,
            )
            expected = (
                decision.extra_u_h,
                decision.inventory_u,
                decision.rise_mg_dl_min,
                decision.final_u_h,
                decision.reason,
            )
            actual = (
                command["extra_u_h"],
                command["inventory_u"],
                command["rise_mg_dl_min"],
                command["final_basal_u_h"],
                command["reason"],
            )
        else:
            correction = (
                0.001 * (glucose - 140)
                + 0.00001 * pid_integral
                + 0.001 * (glucose - pid_previous) / 3
            ) * 60
            pid_previous = glucose
            pid_integral += (glucose - 140) * 3
            requested = max(0.0, min(cfg.settings.max_total_u_h, base + correction))
            final = (
                requested
                if previous_final is None
                else min(requested, previous_final + cfg.settings.max_extra_step_u_h)
            )
            expected = (correction, requested, final, "bounded_pid")
            actual = (
                command["pid_correction_u_h"],
                command["requested_u_h"],
                command["final_basal_u_h"],
                command["reason"],
            )
        if actual != expected:
            raise ValueError("C1 command state replay differs")
        previous_final = command["final_basal_u_h"]


def read_case(output):
    output = Path(output)
    manifest = strict_json((output / "manifest.json").read_bytes())
    if not isinstance(manifest, dict) or manifest.get("schema") != SCHEMA:
        raise ValueError("Unsupported C1 development manifest")
    status = manifest.get("status")
    if status not in ("started", "completed", "terminated", "failed", "interrupted"):
        raise ValueError("Invalid C1 development status")
    sealed = status != "started"
    files = manifest.get("files_sha256")
    if not isinstance(files, dict):
        raise ValueError("Missing artifact inventory")
    if sealed:
        actual = {p.name for p in output.iterdir() if p.is_file() and p.name != "manifest.json"}
        if actual != set(files):
            raise ValueError("Artifact inventory differs")
        if (
            status in ("completed", "terminated")
            and not {
                "config.json",
                "initial.json",
                "runtime.json",
                "native-diagnostic.csv",
                "simglucose-uv.lock",
                "simglucose-protocol-settings.json",
                "simglucose-baseline.json",
                "c1-method.md",
                "trace.jsonl",
                "commands.jsonl",
                "run.log",
                "warnings.json",
            }
            <= files.keys()
        ):
            raise ValueError("Missing successful C1 native artifacts")
        for name, digest in files.items():
            if not isinstance(digest, str) or not HASH.fullmatch(digest):
                raise ValueError("Invalid artifact digest")
            if hashlib.sha256((output / name).read_bytes()).hexdigest() != digest:
                raise ValueError(f"Artifact hash mismatch: {name}")
    config = manifest.get("config")
    if config is None:
        return {"status": status, "metrics": None, "completed_rows": 0}
    cfg = Config.parse(config)
    if strict_json((output / "config.json").read_bytes()) != config:
        raise ValueError("C1 configuration differs")
    if not isinstance(manifest.get("revision"), str) or not REVISION.fullmatch(
        manifest["revision"]
    ):
        raise ValueError("Missing C1 revision")
    source = manifest.get("source_sha256")
    if (
        not isinstance(source, dict)
        or not source
        or any(
            not isinstance(digest, str) or not HASH.fullmatch(digest) for digest in source.values()
        )
    ):
        raise ValueError("Invalid C1 source inventory")
    if hashlib.sha256((output / "c1-method.md").read_bytes()).hexdigest() != manifest.get(
        "method_sha256"
    ):
        raise ValueError("C1 method identity differs")
    for name in ("uv.lock", "protocol-settings.json", "baseline.json"):
        if (output / ("simglucose-" + name)).read_bytes() != (
            Path(__file__).resolve().parents[2] / "experiments/m0/simglucose" / name
        ).read_bytes():
            raise ValueError("C1 native lock/context differs")
    if (output / "runtime.json").exists():
        runtime = strict_json((output / "runtime.json").read_bytes())
        mapping = runtime.get("upstream_files_sha256")
        if not isinstance(mapping, dict) or not mapping:
            raise ValueError("Missing native source inventory")
        fingerprint = hashlib.sha256(
            json.dumps(mapping, sort_keys=True, separators=(",", ":")).encode()
        ).hexdigest()
        baseline = strict_json((output / "simglucose-baseline.json").read_bytes())
        if fingerprint != runtime.get("upstream_files_digest") or fingerprint not in {
            env["upstream_files_digest"] for env in baseline["environments"].values()
        }:
            raise ValueError("Native source fingerprint differs")
    validate_warnings(strict_json((output / "warnings.json").read_bytes()))
    rows = [Row(**row) for row in lines(output, "trace.jsonl", sealed=sealed)]
    commands = lines(output, "commands.jsonl", sealed=sealed)
    validate_rows(rows)
    if sealed and (
        len(rows) != manifest.get("completed_rows") or len(commands) != manifest.get("command_rows")
    ):
        raise ValueError("C1 row counts differ")
    if len(commands) < len(rows) or (
        sealed and status in ("completed", "terminated") and len(commands) != len(rows)
    ):
        raise ValueError("Missing or surplus completed C1 commands")
    held = None
    if rows:
        initial = strict_json((output / "initial.json").read_bytes())
        if (
            set(initial)
            != {
                "time_min",
                "glucose_mg_dl",
                "cgm_mg_dl",
                "true_meal_g",
                "delivered_u_min",
                "terminal",
            }
            or initial["time_min"] != 0
            or initial["terminal"] is not False
        ):
            raise ValueError("Invalid C1 initial point")
        for key in ("glucose_mg_dl", "cgm_mg_dl", "true_meal_g", "delivered_u_min"):
            number(initial[key], key, 0)
        if initial["true_meal_g"] or initial["delivered_u_min"]:
            raise ValueError("Invalid C1 initial meal or delivery")
        held = (0, initial["cgm_mg_dl"])
    for row, command in zip(rows, commands):
        if (row.controller_source_min, row.controller_cgm_mg_dl) != held:
            raise ValueError("C1 observed future or unavailable sensor")
        validate_command(command, row, cfg)
        if row.sensor_available:
            held = (row.end_min, row.raw_cgm_mg_dl)
        fraction = 1 if row.start_min < 1440 else {"A": 1, "B": 0, "C": 0.5, "D": 1}[cfg.condition]
        grams = dict(MEALS).get(row.start_min, 0)
        if row.announced_g != grams * fraction or row.true_meal_g != grams:
            raise ValueError("C1 meal/announcement boundary differs")
        if row.sensor_available != (not (cfg.condition == "D" and 2160 <= row.end_min < 2190)):
            raise ValueError("C1 sensor mask differs")
        if row.terminal != (row.glucose_mg_dl < 10 or row.glucose_mg_dl > 600):
            raise ValueError("C1 native terminal flag differs")
    replay_commands(rows, commands, cfg)
    completed = rows[-1].end_min if rows else 0
    if status == "completed" and (completed != 2880 or rows[-1].terminal):
        raise ValueError("False C1 completion")
    if status == "terminated" and (not rows or not rows[-1].terminal):
        raise ValueError("False C1 termination")
    return {
        "status": status,
        "config": config,
        "completed_rows": len(rows),
        "command_rows": len(commands),
        "metrics": summarize(rows),
        "method_sha256": manifest["method_sha256"],
    }
