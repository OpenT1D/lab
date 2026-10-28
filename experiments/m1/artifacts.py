"""Persist attempts before initialization; reconstruct with the standard library only."""

import contextlib
import hashlib
import json
import os
import platform
import subprocess
import sys
import time
import traceback
import warnings
from dataclasses import asdict
from pathlib import Path

from experiments.m0.simglucose.recording import failure_status, interruption, write_json

from .contracts import HORIZON, SCHEMA, Config, Row, number, validate_rows
from .metrics import VERSION, summarize
from .validation import (
    PROTOCOL_SHA256,
    Snapshot,
    validate_manifest,
    validate_native_provenance,
    validate_warnings,
)

ROOT = Path(__file__).resolve().parents[2]


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def strict_json(text):
    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                raise ValueError(f"Duplicate JSON key: {key}")
            result[key] = value
        return result

    def constant(value):
        raise ValueError(f"Nonfinite JSON constant: {value}")

    return json.loads(
        text,
        object_pairs_hook=pairs,
        parse_constant=constant,
        parse_float=lambda value: number(float(value), "JSON number"),
    )


def source_hashes():
    paths = sorted((ROOT / "experiments/m1").glob("*.py"))
    paths.append(ROOT / "experiments/m0/simglucose/recording.py")
    paths.append(ROOT / "experiments/platform_files.py")
    return {p.relative_to(ROOT).as_posix(): digest(p) for p in paths}


def execute(config_path, output, timeout_seconds=300, *, _implementation=None):
    """Existing output is always rejected, even for a previous failed attempt."""
    output = Path(output)
    output.mkdir(parents=True, exist_ok=False)
    manifest = {
        "schema": SCHEMA,
        "metric_version": VERSION,
        "status": "started",
        "config": None,
        "completed_rows": 0,
        "files_sha256": {},
        "timeout_seconds": repr(timeout_seconds),
    }
    # Record before reading any potentially missing input or importing the runtime.
    write_json(output / "manifest.json", manifest)
    (output / "run.log").touch()
    (output / "trace.jsonl").touch()
    rows = []
    started = time.monotonic()
    caught = []
    try:
        number(timeout_seconds, "timeout_seconds", 0)
        with (
            interruption(timeout_seconds),
            warnings.catch_warnings(record=True) as caught,
            (output / "run.log").open("w") as log,
            contextlib.redirect_stdout(log),
            contextlib.redirect_stderr(log),
            (output / "trace.jsonl").open("a") as trace,
        ):
            warnings.simplefilter("always")
            original = Path(config_path).read_bytes()
            (output / "config.json").write_bytes(original)
            config = Config(**strict_json(original))
            manifest.update(
                config=config.to_dict(),
                source_sha256=source_hashes(),
                revision=subprocess.check_output(
                    ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True
                ).strip(),
                worktree_dirty=bool(
                    subprocess.check_output(["git", "status", "--porcelain"], cwd=ROOT, text=True)
                ),
                python=sys.version,
                platform=platform.platform(),
                command=sys.argv,
                process_id=os.getpid(),
            )
            for name in ("uv.lock", "protocol-settings.json", "baseline.json"):
                (output / name).write_bytes(
                    (ROOT / "experiments/m0/simglucose" / name).read_bytes()
                )
            if digest(output / "protocol-settings.json") != PROTOCOL_SHA256:
                raise ValueError("Protocol differs from supported OT-001 version 1.0")
            write_json(output / "manifest.json", manifest)

            def checkpoint(row):
                # One write and flush per completed record. A hard kill may leave a trailing
                # fragment; only newline-terminated records are recoverable as completed.
                if row.start_min != (rows[-1].end_min if rows else 0):
                    raise ValueError("Noncontiguous checkpoint")
                trace.write(json.dumps(asdict(row), allow_nan=False) + "\n")
                trace.flush()
                rows.append(row)

            def initial(snapshot):
                write_json(output / "initial.json", asdict(snapshot))

            if _implementation is None:
                from .runtime import native_run

                _implementation = native_run
            status = _implementation(config, checkpoint, initial, output, manifest)
            completed = validate_rows(rows)
            if status == "completed" and (completed != HORIZON or rows[-1].terminal):
                raise ValueError("False completion")
            if status == "terminated" and (not rows or not rows[-1].terminal):
                raise ValueError("Missing terminal interval")
            if status not in ("completed", "terminated"):
                raise ValueError("Invalid simulation status")
            manifest["status"] = status
            if status == "terminated":
                manifest["error"] = "Native interval glucose below 10 or above 600 mg/dL"
    except BaseException as exc:
        manifest.update(status=failure_status(exc), error=f"{type(exc).__name__}: {exc}")
        (output / "failure.log").write_text(traceback.format_exc())
        raise
    finally:
        write_json(
            output / "warnings.json",
            [
                {
                    "category": w.category.__name__,
                    "message": str(w.message),
                    "filename": w.filename,
                    "line": w.lineno,
                }
                for w in caught
            ],
        )
        # The signal may arrive after the file write but before rows.append().
        # Count committed newline records from disk instead of trusting in-memory length.
        trace_bytes = (output / "trace.jsonl").read_bytes()
        manifest.update(
            completed_rows=trace_bytes.count(b"\n"), elapsed_seconds=time.monotonic() - started
        )
        manifest["files_sha256"] = {
            p.name: digest(p)
            for p in sorted(output.iterdir())
            if p.is_file() and p.name != "manifest.json" and not p.name.endswith(".tmp")
        }
        write_json(output / "manifest.json", manifest)
    return manifest


def read_run(output):
    """Validate saved artifacts and compute metrics; does not import simglucose."""
    output = Path(output)
    snapshot = Snapshot(output)
    manifest = strict_json(snapshot.read("manifest.json"))
    validate_manifest(manifest)
    if manifest.get("schema") != SCHEMA or manifest.get("metric_version") != VERSION:
        raise ValueError("Unsupported artifact or metric version")
    status = manifest["status"]
    sealed = status != "started"
    if sealed:
        files = manifest["files_sha256"]
        if not {"run.log", "trace.jsonl", "warnings.json"} <= files.keys():
            raise ValueError("Missing required artifact inventory")
        for name, expected in files.items():
            data = snapshot.read(name)
            if hashlib.sha256(data).hexdigest() != expected:
                raise ValueError(f"Artifact hash mismatch: {name}")
        actual = {
            p.name
            for p in output.iterdir()
            if p.name != "manifest.json" and not p.name.endswith(".tmp")
        }
        if actual != set(files):
            raise ValueError("Uninventoried or missing artifact files")
    config = Config(**manifest["config"]) if manifest["config"] is not None else None
    if config is not None:
        if strict_json(snapshot.read("config.json")) != config.to_dict():
            # Omitted defaults are allowed in the original config.
            if Config(**strict_json(snapshot.read("config.json"))) != config:
                raise ValueError("Configuration differs from manifest")
    rows, fragment = [], False
    data = snapshot.read("trace.jsonl", optional=not sealed)
    if data is not None:
        for line in data.splitlines(keepends=True):
            if not line.endswith(b"\n"):
                if status in ("completed", "terminated"):
                    raise ValueError("Truncated successful trace")
                fragment = True
                break
            rows.append(Row(**strict_json(line)))
    elif status in ("completed", "terminated") or manifest["completed_rows"]:
        raise ValueError("Missing trace")
    completed = validate_rows(rows)
    initial_data = snapshot.read("initial.json", optional=True)
    initial = strict_json(initial_data) if initial_data is not None else None
    if initial is not None:
        if set(initial) != {
            "time_min",
            "glucose_mg_dl",
            "cgm_mg_dl",
            "true_meal_g",
            "delivered_u_min",
            "terminal",
        }:
            raise ValueError("Invalid initial snapshot schema")
        for key in ("glucose_mg_dl", "cgm_mg_dl", "true_meal_g", "delivered_u_min"):
            number(initial[key], key, 0)
        if (
            type(initial["time_min"]) is not int
            or initial["time_min"] != 0
            or initial["terminal"] is not False
        ):
            raise ValueError("Invalid initial clock/status")
        if initial["true_meal_g"] != 0 or initial["delivered_u_min"] != 0:
            raise ValueError("Initial point must not represent delivered amounts")
    if rows and (initial is None or config is None):
        raise ValueError("Missing initial observation or owning configuration")
    if config is not None:
        for name in ("experiments/m1/metrics.py", "experiments/m1/contracts.py"):
            if manifest["source_sha256"][name] != source_hashes()[name]:
                raise ValueError("Saved analysis source differs; use its recorded revision")
    if rows or status in ("completed", "terminated"):
        validate_native_provenance(manifest)
        for name in ("uv.lock", "baseline.json"):
            snapshot.read(name)
        if hashlib.sha256(snapshot.read("protocol-settings.json")).hexdigest() != PROTOCOL_SHA256:
            raise ValueError("Saved protocol differs from supported OT-001 version 1.0")
    if sealed and len(rows) != manifest["completed_rows"]:
        raise ValueError("Manifest row count differs from trace")
    if status in ("completed", "terminated"):
        if (
            config is None
            or not {
                "trace.jsonl",
                "config.json",
                "initial.json",
                "native-diagnostic.csv",
                "uv.lock",
                "protocol-settings.json",
                "baseline.json",
            }
            <= manifest["files_sha256"].keys()
        ):
            raise ValueError("Missing successful-run artifacts")
        if status == "completed" and (completed != HORIZON or rows[-1].terminal):
            raise ValueError("Incomplete run labeled completed")
        if status == "terminated" and (not rows or not rows[-1].terminal):
            raise ValueError("Missing termination evidence")
    if config is not None:
        # Reconstruct event/availability semantics independently from saved native outputs.
        from .contracts import MEALS

        held_time, held_value = (0, initial["cgm_mg_dl"]) if initial else (0, None)
        for row in rows:
            if (row.controller_source_min, row.controller_cgm_mg_dl) != (held_time, held_value):
                raise ValueError("Controller observation differs from available history")
            if row.terminal != (row.glucose_mg_dl < 10 or row.glucose_mg_dl > 600):
                raise ValueError("Terminal flag differs from native glucose bounds")
            if row.sensor_available:
                held_time, held_value = row.end_min, row.raw_cgm_mg_dl
            fraction = (
                1 if row.start_min < 1440 else {"A": 1, "B": 0, "C": 0.5, "D": 1}[config.condition]
            )
            if row.true_meal_g != dict(MEALS).get(row.start_min, 0):
                raise ValueError("True meal differs from protocol")
            if row.announced_g != dict(MEALS).get(row.start_min, 0) * fraction:
                raise ValueError("Announcement differs from protocol")
            expected = not (config.condition == "D" and 2160 <= row.end_min < 2190)
            if row.sensor_available != expected:
                raise ValueError("Sensor availability differs from protocol")
    warnings_data = snapshot.read("warnings.json", optional=not sealed)
    saved_warnings = strict_json(warnings_data) if warnings_data is not None else None
    if warnings_data is not None:
        validate_warnings(saved_warnings)
    snapshot.verify_unchanged()
    return {
        "input_sha256": snapshot.sha256(),
        "warnings": saved_warnings,
        "manifest": manifest,
        "metrics": summarize(rows),
        "unsealed": not sealed,
        "discarded_trailing_fragment": fragment,
    }
