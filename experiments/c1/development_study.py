"""Run and reconstruct the declared, known-case C1 simglucose matrix.

This is development material. It does not allocate a held-out evaluation set.
Every native case runs in a separate process; reporting imports no simulator.
"""

import argparse
import json
import os
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from experiments.m0.simglucose.recording import write_json
from experiments.m1.artifacts import digest, read_run, strict_json
from experiments.m1.contracts import Config as M1Config

from .report import lines, read_case
from .simglucose_dev import Config as C1Config

SCHEMA = "opent1d.c1-known-development/1"
PROFILES = ("adult#001", "adult#002")
SEEDS = (101, 102)
CONDITIONS = "ABCD"
METHODS = ("basal_bolus", "trend_overlay", "bounded_pid", "trend_overlay_high_target")
METRICS = ("in_70_180_percent", "below_70_percent", "below_54_percent", "above_250_percent")
ROOT = Path(__file__).resolve().parents[2]


def roster():
    """The entire development roster is materialized before any native work."""
    example = strict_json((ROOT / "experiments/c1/simglucose-overlay.example.json").read_bytes())
    pid = strict_json((ROOT / "experiments/c1/simglucose-pid.example.json").read_bytes())
    if example["settings"] != pid["settings"]:
        raise ValueError("Example action settings differ")
    cases = []
    for profile in PROFILES:
        for seed in SEEDS:
            for condition in CONDITIONS:
                for method in METHODS:
                    if method == "basal_bolus":
                        config = M1Config(profile, seed, method, condition).to_dict()
                    else:
                        config = {
                            "profile": profile,
                            "seed": seed,
                            "condition": condition,
                            "method": "bounded_pid" if method == "bounded_pid" else "trend_overlay",
                            "settings": dict(example["settings"]),
                        }
                        if method == "trend_overlay_high_target":
                            # One declared sensitivity attempt: suppress responses to
                            # modest rises while retaining the same action bounds.
                            config["settings"]["target_mg_dl"] = 180
                        C1Config.parse(config)
                    identifier = f"{profile}-{seed}-{condition}-{method}"
                    cases.append({"id": identifier, "method": method, "config": config})
    return cases


def plan():
    return {
        "schema": SCHEMA,
        "purpose": (
            "Known M1 development profiles/seeds and existing A-D schedule only; no held-out claim"
        ),
        "variant_reason": (
            "Raise overlay activation target from 140 to 180 mg/dL to test whether "
            "modest-rise responses during warmup explain the observed low-boundary "
            "regression; all other settings fixed."
        ),
        "cases": roster(),
    }


def _execute_case(study, case, timeout_seconds):
    identifier = case["id"]
    base = study / identifier
    config = study / "inputs" / f"{identifier}.json"
    module = (
        "experiments.m1" if case["method"] == "basal_bolus" else "experiments.c1.simglucose_dev"
    )
    cmd = [sys.executable, "-m", module, "--config", str(config), "--output", str(base)]
    if module.endswith("simglucose_dev"):
        cmd += ["--timeout-seconds", str(timeout_seconds)]
    else:
        cmd = [
            sys.executable,
            "-m",
            module,
            "run",
            "--config",
            str(config),
            "--output",
            str(base),
            "--timeout-seconds",
            str(timeout_seconds),
        ]
    env = dict(os.environ)
    env["MPLCONFIGDIR"] = str(study / "mpl-cache" / identifier)
    try:
        result = subprocess.run(
            cmd,
            cwd=ROOT,
            env=env,
            capture_output=True,
            text=True,
            timeout=timeout_seconds + 30,
            check=False,
        )
        record = {
            "id": identifier,
            "returncode": result.returncode,
            "stdout": result.stdout[-2000:],
            "stderr": result.stderr[-2000:],
        }
    except subprocess.TimeoutExpired as error:
        record = {
            "id": identifier,
            "returncode": None,
            "error": f"Worker timeout after {error.timeout} seconds",
        }
    except OSError as error:
        record = {"id": identifier, "returncode": None, "error": f"{type(error).__name__}: {error}"}
    write_json(study / "attempts" / f"{identifier}.json", record)
    return record


def execute(study, *, workers=4, timeout_seconds=300):
    study = Path(study)
    if type(workers) is not int or not 1 <= workers <= 4:
        raise ValueError("workers must be 1-4")
    if type(timeout_seconds) not in (int, float) or timeout_seconds <= 0:
        raise ValueError("timeout_seconds must be positive")
    specification = plan()
    study.mkdir(parents=True, exist_ok=False)
    (study / "inputs").mkdir()
    (study / "attempts").mkdir()
    write_json(study / "plan.json", specification)
    for case in specification["cases"]:
        write_json(study / "inputs" / f"{case['id']}.json", case["config"])
    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = [
            pool.submit(_execute_case, study, case, timeout_seconds)
            for case in specification["cases"]
        ]
        for future in as_completed(futures):
            future.result()
    result = reconstruct(study)
    write_json(study / "report.json", result)
    return result


def _diagnostic(study, overlay_id, base_id):
    overlay = study / overlay_id
    commands = lines(overlay, "commands.jsonl", sealed=True)
    rows = lines(overlay, "trace.jsonl", sealed=True)
    base_rows = lines(study / base_id, "trace.jsonl", sealed=True)
    if len(commands) != len(rows) or len(rows) != len(base_rows):
        raise ValueError("Diagnostic requires matched complete traces")
    if any(a["start_min"] != b["start_min"] for a, b in zip(rows, base_rows)):
        raise ValueError("Diagnostic clocks differ")
    added_low = [
        a["start_min"]
        for a, b in zip(rows, base_rows)
        if a["start_min"] >= 1440 and a["glucose_mg_dl"] < 70 <= b["glucose_mg_dl"]
    ]
    removed_low = [
        a["start_min"]
        for a, b in zip(rows, base_rows)
        if a["start_min"] >= 1440 and b["glucose_mg_dl"] < 70 <= a["glucose_mg_dl"]
    ]
    scored_pairs = [(a, b) for a, b in zip(rows, base_rows) if a["start_min"] >= 1440]
    return {
        "warmup_commanded_extra_u": sum(
            c["extra_u_h"] * 3 / 60 for c in commands if c["time_min"] < 1440
        ),
        "scored_commanded_extra_u": sum(
            c["extra_u_h"] * 3 / 60 for c in commands if c["time_min"] >= 1440
        ),
        "warmup_active_intervals": sum(
            c["extra_u_h"] > 0 and c["time_min"] < 1440 for c in commands
        ),
        "scored_active_intervals": sum(
            c["extra_u_h"] > 0 and c["time_min"] >= 1440 for c in commands
        ),
        "first_scored_extra_min": next(
            (c["time_min"] for c in commands if c["time_min"] >= 1440 and c["extra_u_h"] > 0), None
        ),
        "added_below_70_starts_min": added_low,
        "removed_below_70_starts_min": removed_low,
        "paired_mean_scored_glucose_delta_mg_dl": (
            sum(a["glucose_mg_dl"] - b["glucose_mg_dl"] for a, b in scored_pairs)
            / len(scored_pairs)
        ),
    }


def reconstruct(study):
    """Rebuild the full planned denominator from saved inputs and sealed runs."""
    study = Path(study)
    specification = strict_json((study / "plan.json").read_bytes())
    if specification != plan():
        raise ValueError("Development plan differs from declared roster/settings")
    expected = {case["id"] for case in specification["cases"]}
    if {p.stem for p in (study / "inputs").glob("*.json")} != expected:
        raise ValueError("Development input roster differs")
    recorded = {p.stem for p in (study / "attempts").glob("*.json")}
    if not recorded <= expected:
        raise ValueError("Development attempt roster differs")
    result = []
    for case in specification["cases"]:
        identifier = case["id"]
        if strict_json((study / "inputs" / f"{identifier}.json").read_bytes()) != case["config"]:
            raise ValueError(f"Development input changed: {identifier}")
        if identifier not in recorded:
            result.append(
                {
                    "id": identifier,
                    "method": case["method"],
                    "profile": case["config"]["profile"],
                    "seed": case["config"]["seed"],
                    "condition": case["config"]["condition"],
                    "status": "attempt_unrecorded",
                    "completed_rows": None,
                    "glucose": None,
                    "manifest_sha256": (
                        digest(study / identifier / "manifest.json")
                        if (study / identifier / "manifest.json").exists()
                        else None
                    ),
                    "attempt": None,
                }
            )
            continue
        attempt = strict_json((study / "attempts" / f"{identifier}.json").read_bytes())
        if attempt.get("id") != identifier:
            raise ValueError("Attempt identity differs")
        path = study / identifier
        try:
            report = read_run(path) if case["method"] == "basal_bolus" else read_case(path)
            status = (
                report["manifest"]["status"]
                if case["method"] == "basal_bolus"
                else report["status"]
            )
            metrics = report["metrics"]
            completed_rows = (
                report["manifest"]["completed_rows"]
                if case["method"] == "basal_bolus"
                else report["completed_rows"]
            )
            manifest_sha256 = digest(path / "manifest.json")
        except (FileNotFoundError, ValueError, KeyError, TypeError) as error:
            status, metrics, manifest_sha256 = "unverifiable", None, None
            completed_rows = None
            attempt = dict(attempt, verification_error=f"{type(error).__name__}: {error}")
        if attempt.get("returncode") == 0 and status != "completed":
            raise ValueError(f"Worker claimed success without complete evidence: {identifier}")
        result.append(
            {
                "id": identifier,
                "method": case["method"],
                "profile": case["config"]["profile"],
                "seed": case["config"]["seed"],
                "condition": case["config"]["condition"],
                "status": status,
                "completed_rows": completed_rows,
                "glucose": metrics["glucose"] if metrics else None,
                "manifest_sha256": manifest_sha256,
                "attempt": attempt,
            }
        )
    lookup = {(r["profile"], r["seed"], r["condition"], r["method"]): r for r in result}
    paired = []
    for row in result:
        if row["method"] == "basal_bolus":
            continue
        base = lookup[row["profile"], row["seed"], row["condition"], "basal_bolus"]
        if row["status"] == base["status"] == "completed":
            differences = {key: row["glucose"][key] - base["glucose"][key] for key in METRICS}
            diagnostic = (
                _diagnostic(study, row["id"], base["id"])
                if row["method"].startswith("trend_overlay")
                else None
            )
        else:
            differences, diagnostic = None, None
        paired.append(
            {
                "id": row["id"],
                "base_id": base["id"],
                "delta_percent_points": differences,
                "diagnostic": diagnostic,
            }
        )
    counts = {
        method: {
            status: sum(r["method"] == method and r["status"] == status for r in result)
            for status in sorted({r["status"] for r in result})
        }
        for method in METHODS
    }
    return {
        "schema": SCHEMA,
        "plan_sha256": digest(study / "plan.json"),
        "planned": len(result),
        "status_counts": counts,
        "cases": result,
        "paired": paired,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    run = sub.add_parser("run")
    run.add_argument("--output", type=Path, required=True)
    run.add_argument("--workers", type=int, default=4)
    run.add_argument("--timeout-seconds", type=float, default=300)
    report = sub.add_parser("report")
    report.add_argument("--study", type=Path, required=True)
    args = parser.parse_args()
    result = (
        execute(args.output, workers=args.workers, timeout_seconds=args.timeout_seconds)
        if args.command == "run"
        else reconstruct(args.study)
    )
    if args.command == "report":
        print(json.dumps(result, sort_keys=True, separators=(",", ":")))
    else:
        print(
            json.dumps(
                {"planned": result["planned"], "status_counts": result["status_counts"]},
                sort_keys=True,
            )
        )


if __name__ == "__main__":
    main()
