"""Run and reconstruct a bounded researcher-supplied M1 controller task."""

import argparse
import contextlib
import json
import platform
import subprocess
import sys
import time
import traceback
import warnings
from dataclasses import asdict
from pathlib import Path
from types import SimpleNamespace

from experiments.m0.simglucose.recording import failure_status, interruption, write_json
from experiments.m1.artifacts import ROOT, strict_json
from experiments.m1.contracts import HORIZON, MEALS, Action, Row, number, validate_rows
from experiments.m1.metrics import VERSION, summarize
from experiments.m1.validation import (
    PROTOCOL_SHA256,
    Snapshot,
    validate_native_provenance,
    validate_warnings,
)
from experiments.p1.__main__ import PROFILES, SEEDS, require_runtime

from .intake import SuppliedController, declaration, replay, sha256

WORKFLOW = "opent1d.p1-external-workflow/1"
CASE = "opent1d.p1-external-case/1"
REPORTS = ("report.json", "report.md")
CONDITIONS = "ABCD"
SOURCE_FILES = ("controller.json", "controller.py")
LOCAL_SOURCES = (
    "experiments/p1_external/__main__.py",
    "experiments/p1_external/intake.py",
    "experiments/p1/__main__.py",
    "experiments/m0/simglucose/recording.py",
    "experiments/platform_files.py",
    "experiments/m1/adapter.py",
    "experiments/m1/artifacts.py",
    "experiments/m1/control.py",
    "experiments/m1/contracts.py",
    "experiments/m1/metrics.py",
    "experiments/m1/simulation.py",
    "experiments/m1/runtime.py",
    "experiments/m1/validation.py",
)


def source_code_hashes():
    return {name: sha256((ROOT / name).read_bytes()) for name in LOCAL_SOURCES}


def plan(profile, seed, metadata):
    if profile not in PROFILES or type(seed) is not int or seed not in SEEDS:
        raise ValueError("P1 external supports adult#001/adult#002 and seeds 101/102")
    return {
        "schema": WORKFLOW,
        "profile": profile,
        "seed": seed,
        "controller": metadata,
        "implementation_sha256": source_code_hashes(),
    }, {
        "schema": WORKFLOW,
        "status": "started",
        "purpose": "One supplied rate controller in four synthetic M1 information conditions",
        "cases": list(CONDITIONS),
    }


def validate_source_copy(study):
    source = Path(study) / "source"
    metadata = declaration(source)
    if (Path(study) / "workflow.json").is_symlink():
        raise ValueError("P1 workflow marker must not be a symlink")
    marker = strict_json((Path(study) / "workflow.json").read_bytes())
    if not isinstance(marker, dict) or set(marker) != {
        "schema",
        "profile",
        "seed",
        "controller",
        "implementation_sha256",
    }:
        raise ValueError("Invalid P1 external workflow marker")
    expected, _ = plan(marker["profile"], marker["seed"], metadata)
    if marker != expected:
        raise ValueError("P1 external source or implementation differs from workflow")
    return marker


def run_case(study, condition, marker, *, timeout_seconds=300):
    output = Path(study) / condition
    output.mkdir(exist_ok=False)
    manifest = {
        "schema": CASE,
        "condition": condition,
        "config": {"profile": marker["profile"], "seed": marker["seed"], "condition": condition},
        "metric_version": VERSION,
        "status": "started",
        "completed_rows": 0,
        "files_sha256": {},
        "source_sha256": marker["controller"]["source_sha256"],
        "implementation_sha256": marker["implementation_sha256"],
        "timeout_seconds": timeout_seconds,
    }
    write_json(output / "manifest.json", manifest)
    (output / "trace.jsonl").touch()
    (output / "run.log").touch()
    rows, caught = [], []
    started = time.monotonic()
    config = SimpleNamespace(**manifest["config"])
    try:
        with (
            interruption(timeout_seconds),
            warnings.catch_warnings(record=True) as caught,
            (output / "run.log").open("w") as log,
            contextlib.redirect_stdout(log),
            contextlib.redirect_stderr(log),
            (output / "trace.jsonl").open("a") as trace,
        ):
            warnings.simplefilter("always")
            controller = SuppliedController(
                Path(study) / "source", marker["controller"], seed=marker["seed"]
            )
            manifest.update(
                revision=subprocess.check_output(
                    ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True
                ).strip(),
                worktree_dirty=bool(
                    subprocess.check_output(["git", "status", "--porcelain"], cwd=ROOT, text=True)
                ),
                python=sys.version,
                platform=platform.platform(),
                implementation_sha256=marker["implementation_sha256"],
            )
            for name in ("uv.lock", "protocol-settings.json", "baseline.json"):
                (output / name).write_bytes(
                    (ROOT / "experiments/m0/simglucose" / name).read_bytes()
                )
            write_json(output / "manifest.json", manifest)

            def checkpoint(row):
                if row.start_min != (rows[-1].end_min if rows else 0):
                    raise ValueError("Noncontiguous controller trace")
                trace.write(json.dumps(asdict(row), allow_nan=False) + "\n")
                trace.flush()
                rows.append(row)

            def initial(snapshot):
                write_json(output / "initial.json", asdict(snapshot))

            from experiments.m1.runtime import native_run

            status = native_run(
                config, checkpoint, initial, output, manifest, controller=controller
            )
            completed = validate_rows(rows)
            if status == "completed" and (completed != HORIZON or rows[-1].terminal):
                raise ValueError("False native completion")
            if status == "terminated" and (not rows or not rows[-1].terminal):
                raise ValueError("Missing native terminal interval")
            if status not in ("completed", "terminated"):
                raise ValueError("Unsupported native status")
            replay(Path(study) / "source", marker["controller"], marker["seed"], rows)
            manifest["status"] = status
            if status == "terminated":
                manifest["error"] = "Native interval glucose outside 10–600 mg/dL"
    except BaseException as error:
        manifest.update(status=failure_status(error), error=f"{type(error).__name__}: {error}")
        (output / "failure.log").write_text(traceback.format_exc())
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
        manifest["completed_rows"] = (output / "trace.jsonl").read_bytes().count(b"\n")
        manifest["elapsed_seconds"] = time.monotonic() - started
        manifest["files_sha256"] = {
            p.name: sha256(p.read_bytes())
            for p in sorted(output.iterdir())
            if p.is_file() and p.name != "manifest.json"
        }
        write_json(output / "manifest.json", manifest)
    return manifest["status"]


def read_case(study, condition, marker):
    output = Path(study) / condition
    if not output.exists():
        return {"condition": condition, "status": "scheduled", "metrics": None, "rows": []}
    snapshot = Snapshot(output)
    manifest = strict_json(snapshot.read("manifest.json"))
    if (
        not isinstance(manifest, dict)
        or manifest.get("schema") != CASE
        or manifest.get("condition") != condition
        or manifest.get("config")
        != {
            "profile": marker["profile"],
            "seed": marker["seed"],
            "condition": condition,
        }
        or manifest.get("metric_version") != VERSION
        or manifest.get("source_sha256") != marker["controller"]["source_sha256"]
        or manifest.get("implementation_sha256") != marker["implementation_sha256"]
        or manifest.get("status")
        not in ("started", "completed", "terminated", "failed", "interrupted")
    ):
        raise ValueError(f"Invalid P1 case manifest: {condition}")
    inventory = manifest.get("files_sha256")
    if not isinstance(inventory, dict) or not {"trace.jsonl", "run.log", "warnings.json"} <= set(
        inventory
    ):
        raise ValueError("Incomplete case inventory")
    actual = {p.name for p in output.iterdir() if p.name != "manifest.json"}
    if actual != set(inventory):
        raise ValueError("Uninventoried or missing P1 case files")
    for name, expected in inventory.items():
        if not isinstance(expected, str) or sha256(snapshot.read(name)) != expected:
            raise ValueError(f"P1 case artifact differs: {name}")
    warning_data = strict_json(snapshot.read("warnings.json"))
    validate_warnings(warning_data)
    rows = []
    fragment = False
    for line in snapshot.read("trace.jsonl").splitlines(keepends=True):
        if not line.endswith(b"\n"):
            if manifest["status"] in ("completed", "terminated"):
                raise ValueError("Truncated successful P1 trace")
            fragment = True
            break
        rows.append(Row(**strict_json(line)))
    completed = validate_rows(rows)
    if manifest.get("completed_rows") != len(rows):
        raise ValueError("P1 trace count differs")
    if manifest["status"] == "completed" and (
        completed != HORIZON or not rows or rows[-1].terminal
    ):
        raise ValueError("Incomplete P1 case labeled completed")
    if manifest["status"] == "terminated" and (not rows or not rows[-1].terminal):
        raise ValueError("P1 termination lacks terminal row")
    if manifest["status"] in ("completed", "terminated") and not {
        "initial.json",
        "native-diagnostic.csv",
        "uv.lock",
        "protocol-settings.json",
        "baseline.json",
    } <= set(inventory):
        raise ValueError("Successful P1 case lacks native artifacts")
    if (
        "protocol-settings.json" in inventory
        and sha256(snapshot.read("protocol-settings.json")) != PROTOCOL_SHA256
    ):
        raise ValueError("P1 case uses unsupported native protocol")
    if manifest["status"] in ("terminated", "failed", "interrupted") and not manifest.get("error"):
        raise ValueError("P1 case lacks failure or termination reason")
    if manifest["status"] in ("completed", "terminated", "failed", "interrupted"):
        if "initial.json" in inventory:
            validate_native_provenance(manifest)
    initial = strict_json(snapshot.read("initial.json")) if "initial.json" in inventory else None
    if initial is not None:
        if not isinstance(initial, dict) or set(initial) != {
            "time_min",
            "glucose_mg_dl",
            "cgm_mg_dl",
            "true_meal_g",
            "delivered_u_min",
            "terminal",
        }:
            raise ValueError("Invalid P1 initial snapshot")
        if initial["time_min"] != 0 or initial["terminal"] is not False:
            raise ValueError("Invalid P1 initial clock or state")
        for key in ("glucose_mg_dl", "cgm_mg_dl", "true_meal_g", "delivered_u_min"):
            number(initial[key], key, 0)
        if initial["true_meal_g"] != 0 or initial["delivered_u_min"] != 0:
            raise ValueError("P1 initial snapshot carries a delivered amount")
    if rows and initial is None:
        raise ValueError("P1 trace lacks initial snapshot")
    held_time = 0
    held_value = initial["cgm_mg_dl"] if initial else None
    for row in rows:
        if (row.controller_source_min, row.controller_cgm_mg_dl) != (held_time, held_value):
            raise ValueError("P1 controller input differs from causal history")
        if row.true_meal_g != dict(MEALS).get(row.start_min, 0):
            raise ValueError("P1 true meal differs from M1 task")
        fraction = 1 if row.start_min < 1440 else {"A": 1, "B": 0, "C": 0.5, "D": 1}[condition]
        if row.announced_g != dict(MEALS).get(row.start_min, 0) * fraction:
            raise ValueError("P1 announcement differs from task")
        expected = not (condition == "D" and 2160 <= row.end_min < 2190)
        if row.sensor_available != expected:
            raise ValueError("P1 sensor availability differs from task")
        Action(row.basal_u_min, row.bolus_u_min)
        if not 0 <= row.basal_u_min <= 0.2 or not 0 <= row.bolus_u_min <= 2.0:
            raise ValueError("P1 action exceeds declared bound")
        if row.sensor_available:
            held_time, held_value = row.end_min, row.raw_cgm_mg_dl
        if row.terminal != (row.glucose_mg_dl < 10 or row.glucose_mg_dl > 600):
            raise ValueError("P1 terminal flag differs from native glucose bounds")
    snapshot.verify_unchanged()
    return {
        "condition": condition,
        "status": manifest["status"],
        "error": manifest.get("error"),
        "metrics": summarize(rows),
        "rows": rows,
        "discarded_trailing_fragment": fragment,
        "manifest_sha256": sha256(snapshot.read("manifest.json")),
    }


def report(study, marker, schedule):
    cases = [read_case(study, c, marker) for c in CONDITIONS]
    if schedule["status"] != "started" and any(c["status"] == "scheduled" for c in cases):
        raise ValueError("Finalized study lacks a planned P1 case")
    if schedule["status"] == "completed" and any(c["status"] != "completed" for c in cases):
        raise ValueError("P1 study falsely labeled completed")
    if schedule["status"] == "finished_with_failures" and all(
        c["status"] == "completed" for c in cases
    ):
        raise ValueError("P1 study falsely labeled failed")
    statuses = {
        s: sum(c["status"] == s for c in cases) for s in sorted({c["status"] for c in cases})
    }
    data = {
        "schema": "opent1d.p1-external-report/1",
        "study_status": schedule["status"],
        "controller": marker["controller"],
        "profile": marker["profile"],
        "seed": marker["seed"],
        "status_counts": statuses,
        "cases": [{k: v for k, v in c.items() if k != "rows"} for c in cases],
        "limits": "One synthetic development profile and seed; no efficacy or clinical claim",
    }
    lines = [
        "# P1 external controller: synthetic M1 information conditions",
        "",
        (
            f"Controller `{marker['controller']['name']}`; "
            f"profile `{marker['profile']}`, seed `{marker['seed']}`."
        ),
        "Four scheduled 48-hour cases; only the second day is scored. This is a",
        "software and simulation result, not evidence of clinical benefit or dosing advice.",
        "",
        (
            "| Condition | Status | 70–180 (%) | Below 70 (%) | Scored minutes "
            "| Delivered insulin (U) |"
        ),
        "| --- | --- | ---: | ---: | ---: | ---: |",
    ]

    def fmt(value):
        return "undefined" if value is None else f"{value:.3f}"

    for c in cases:
        m = c["metrics"]
        g = m["glucose"] if m else {}
        lines.append(
            f"| {c['condition']} | {c['status']} | {fmt(g.get('in_70_180_percent'))} | "
            f"{fmt(g.get('below_70_percent'))} | "
            f"{fmt(m['delivered_interval_minutes'] if m else None)} | "
            f"{fmt(m['delivered_insulin_u'] if m and m['delivered_interval_minutes'] else None)} |"
        )
    lines.extend(
        [
            "",
            "A: full announcements; B: none; C: half; D: a 30-minute noon sensor mask.",
            "True meals are unchanged. Incomplete exposure stays incomplete.",
            "",
            "## Failures and interpretation",
            "",
        ]
    )
    for c in cases:
        if c.get("error"):
            lines.append(f"- {c['condition']}: {c['status']} — {c['error']}")
    if not any(c.get("error") for c in cases):
        lines.append("No recorded case failure.")
    lines.extend(
        [
            "",
            "These four cases describe one supplied method in one synthetic profile.",
            "The M1 references remain in P1/0.1; no matched efficacy comparator is claimed.",
            "Retain the full study directory for simulator-free reconstruction and",
            "separate source-only action replay.",
            "",
        ]
    )
    return data, "\n".join(lines)


def validate_study(study):
    study = Path(study)
    if study.is_symlink() or not study.is_dir():
        raise ValueError("P1 study must be a regular directory")
    if (study / "study.json").is_symlink():
        raise ValueError("P1 study schedule must not be a symlink")
    marker = validate_source_copy(study)
    schedule = strict_json((study / "study.json").read_bytes())
    if not isinstance(schedule, dict) or schedule.get("status") not in (
        "started",
        "completed",
        "finished_with_failures",
    ):
        raise ValueError("Invalid P1 study status")
    _, expected = plan(marker["profile"], marker["seed"], marker["controller"])
    expected["status"] = schedule["status"]
    if schedule != expected:
        raise ValueError("P1 study differs from four-case schedule")
    return marker, schedule


def write_report(study, output):
    marker, schedule = validate_study(study)
    data, markdown = report(study, marker, schedule)
    output = Path(output)
    output.mkdir(exist_ok=False)
    write_json(output / "report.json", data)
    (output / "report.md").write_text(markdown)
    return data


def run(source, output, profile, seed):
    metadata = declaration(source)
    from .intake import check_dependencies

    check_dependencies(metadata)
    require_runtime()
    marker, schedule = plan(profile, seed, metadata)
    output = Path(output)
    output.mkdir(parents=True, exist_ok=False)
    copied = output / "source"
    copied.mkdir()
    for name in SOURCE_FILES:
        (copied / name).write_bytes((Path(source) / name).read_bytes())
    declaration(copied)
    write_json(output / "workflow.json", marker)
    write_json(output / "study.json", schedule)
    failed = False
    for condition in CONDITIONS:
        status = run_case(output, condition, marker)
        failed |= status != "completed"
        if status == "interrupted":
            break
    if any(not (output / condition).exists() for condition in CONDITIONS):
        # Preserve an interrupted schedule and its unattempted cases.
        write_report(output, output / "report")
        raise RuntimeError("P1 external study interrupted; inspect saved report")
    schedule["status"] = "finished_with_failures" if failed else "completed"
    write_json(output / "study.json", schedule)
    data = write_report(output, output / "report")
    if failed:
        raise RuntimeError("P1 external cases failed; inspect report/report.md")
    return data


def reconstruct(study, output):
    data = write_report(study, output)
    original = Path(study) / "report"
    present = [((original / name).exists()) for name in REPORTS]
    if any(present) and not all(present):
        raise ValueError("Incomplete original P1 report")
    if all(present):
        for name in REPORTS:
            if (original / name).is_symlink() or (original / name).read_bytes() != (
                Path(output) / name
            ).read_bytes():
                raise ValueError(f"P1 report reconstruction differs: {name}")
    write_json(
        Path(output) / "reconstruction.json",
        {
            "schema": "opent1d.p1-external-reconstruction/1",
            "byte_identical_to_original": all(present),
            "files_sha256": {name: sha256((Path(output) / name).read_bytes()) for name in REPORTS},
        },
    )
    return data


def verify_actions(study):
    marker, _ = validate_study(study)
    count = 0
    for condition in CONDITIONS:
        case = read_case(study, condition, marker)
        if case["status"] == "scheduled":
            continue
        replay(Path(study) / "source", marker["controller"], marker["seed"], case["rows"])
        count += len(case["rows"])
    return count


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    preflight = sub.add_parser("preflight")
    preflight.add_argument("--source", required=True)
    run_parser = sub.add_parser("run")
    run_parser.add_argument("--source", required=True)
    run_parser.add_argument("--output", required=True)
    run_parser.add_argument("--profile", default="adult#001", choices=PROFILES)
    run_parser.add_argument("--seed", type=int, default=101, choices=SEEDS)
    rebuild = sub.add_parser("reconstruct")
    rebuild.add_argument("--study", required=True)
    rebuild.add_argument("--output", required=True)
    verify = sub.add_parser("verify-actions")
    verify.add_argument("--study", required=True)
    args = parser.parse_args()
    if args.command == "preflight":
        from .intake import check_dependencies, smoke

        metadata = declaration(args.source)
        check_dependencies(metadata)
        smoke(args.source, metadata)
        print(json.dumps({"status": "contract_checked", "controller": metadata["name"]}))
    elif args.command == "run":
        result = run(args.source, args.output, args.profile, args.seed)
        print(
            json.dumps(
                {
                    "status_counts": result["status_counts"],
                    "report": str(Path(args.output) / "report" / "report.md"),
                }
            )
        )
    elif args.command == "reconstruct":
        result = reconstruct(args.study, args.output)
        print(
            json.dumps(
                {
                    "status_counts": result["status_counts"],
                    "report": str(Path(args.output) / "report.md"),
                }
            )
        )
    else:
        print(json.dumps({"replayed_actions": verify_actions(args.study)}))


if __name__ == "__main__":
    main()
