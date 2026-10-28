"""Run/reconstruct the single-attempt C1/0.7 known-case feedback matrix.

The setting file is committed before native scoring. Every case runs in a
separate process; reconstruction imports no simulator.
"""

import argparse
import json
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import asdict
from pathlib import Path

from experiments.m0.simglucose.recording import write_json
from experiments.m1.artifacts import digest, read_run, strict_json
from experiments.m1.contracts import Config as M1Config

from .development_study import _execute_case
from .feedback import FeedbackSettings, without_rise
from .report import read_case
from .simglucose_dev import Config as C1Config

ROOT = Path(__file__).resolve().parents[2]
SETTINGS = ROOT / "experiments/c1/feedback-development.json"
SCHEMA = "opent1d.c1-feedback-development/1"
METHODS = ("basal_bolus", "feedback_trend", "feedback_no_rise")
METRICS = ("in_70_180_percent", "below_70_percent", "below_54_percent", "above_250_percent")


def plan():
    declared = strict_json(SETTINGS.read_bytes())
    if (
        set(declared)
        != {
            "schema",
            "max_setting_attempts_per_method",
            "profiles",
            "seeds",
            "conditions",
            "candidate_settings",
        }
        or declared["schema"] != "opent1d.c1-feedback-settings/1"
        or declared["max_setting_attempts_per_method"] != 1
        or declared["profiles"] != ["adult#001", "adult#002"]
        or declared["seeds"] != [101, 102]
        or declared["conditions"] != list("ABCD")
        or set(declared["candidate_settings"]) != set(FeedbackSettings.__dataclass_fields__)
    ):
        raise ValueError("Unsupported feedback development declaration")
    candidate = FeedbackSettings(**declared["candidate_settings"])
    if candidate.rise_gain_u_h_per_mg_dl_min <= 0:
        raise ValueError("Candidate rise gain must be positive")
    comparator = without_rise(candidate)
    cases = []
    for profile in declared["profiles"]:
        for seed in declared["seeds"]:
            for condition in declared["conditions"]:
                for method in METHODS:
                    if method == "basal_bolus":
                        config = M1Config(profile, seed, method, condition).to_dict()
                    else:
                        config = {
                            "profile": profile,
                            "seed": seed,
                            "condition": condition,
                            "method": method,
                            "settings": asdict(
                                candidate if method == "feedback_trend" else comparator
                            ),
                        }
                        C1Config.parse(config)
                    cases.append(
                        {
                            "id": f"{profile}-{seed}-{condition}-{method}",
                            "method": method,
                            "config": config,
                        }
                    )
    return {
        "schema": SCHEMA,
        "purpose": "Known synthetic M1 development cells; no held-out or human claim",
        "max_setting_attempts_per_method": 1,
        "settings_sha256": digest(SETTINGS),
        "cases": cases,
    }


def execute(study, *, workers=4, timeout_seconds=300):
    return execute_plan(
        study,
        plan(),
        SETTINGS,
        "settings_sha256",
        reconstruct,
        workers=workers,
        timeout_seconds=timeout_seconds,
    )


def execute_plan(
    study, specification, declaration, hash_field, reader, *, workers=4, timeout_seconds=300
):
    study = Path(study)
    if type(workers) is not int or not 1 <= workers <= 4:
        raise ValueError("workers must be 1-4")
    if type(timeout_seconds) not in (int, float) or timeout_seconds <= 0:
        raise ValueError("timeout_seconds must be positive")
    study.mkdir(parents=True, exist_ok=False)
    (study / "inputs").mkdir()
    (study / "attempts").mkdir()
    write_json(study / "plan.json", specification)
    (study / "settings.json").write_bytes(declaration.read_bytes())
    for case in specification["cases"]:
        write_json(study / "inputs" / f"{case['id']}.json", case["config"])
    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = [
            pool.submit(_execute_case, study, case, timeout_seconds)
            for case in specification["cases"]
        ]
        for future in as_completed(futures):
            future.result()
    result = reader(study)
    write_json(study / "report.json", result)
    return result


def reconstruct(study):
    return reconstruct_plan(study, plan(), "settings_sha256", SCHEMA)


def reconstruct_plan(study, specification, hash_field, schema):
    study = Path(study)
    if (
        strict_json((study / "plan.json").read_bytes()) != specification
        or digest(study / "settings.json") != specification[hash_field]
    ):
        raise ValueError("Feedback plan/settings differ from declaration")
    expected = {case["id"] for case in specification["cases"]}
    if {p.stem for p in (study / "inputs").glob("*.json")} != expected:
        raise ValueError("Feedback input roster differs")
    attempts = {p.stem for p in (study / "attempts").glob("*.json")}
    if not attempts <= expected:
        raise ValueError("Unknown feedback attempt")
    cases = []
    revisions = set()
    feedback_sources = set()
    for case in specification["cases"]:
        identifier = case["id"]
        if strict_json((study / "inputs" / f"{identifier}.json").read_bytes()) != case["config"]:
            raise ValueError(f"Feedback input changed: {identifier}")
        attempt = (
            strict_json((study / "attempts" / f"{identifier}.json").read_bytes())
            if identifier in attempts
            else None
        )
        if attempt is not None and attempt.get("id") != identifier:
            raise ValueError("Feedback attempt identity differs")
        status, metrics, rows, manifest_hash = "attempt_unrecorded", None, None, None
        if attempt is not None:
            bundle = study / identifier
            try:
                report = read_run(bundle) if case["method"] == "basal_bolus" else read_case(bundle)
                manifest = strict_json((bundle / "manifest.json").read_bytes())
                status = (
                    report["manifest"]["status"]
                    if case["method"] == "basal_bolus"
                    else report["status"]
                )
                metrics = report["metrics"]
                rows = manifest["completed_rows"]
                manifest_hash = digest(bundle / "manifest.json")
                if manifest.get("worktree_dirty") is not False:
                    raise ValueError("Native attempt used a dirty worktree")
                revisions.add(manifest["revision"])
                if case["method"] != "basal_bolus":
                    feedback_sources.add(json.dumps(manifest["source_sha256"], sort_keys=True))
            except (FileNotFoundError, ValueError, KeyError, TypeError) as error:
                status, metrics, rows, manifest_hash = "unverifiable", None, None, None
                attempt = dict(attempt, verification_error=f"{type(error).__name__}: {error}")
            if attempt.get("returncode") == 0 and status != "completed":
                raise ValueError(f"Worker claimed success without complete evidence: {identifier}")
        cases.append(
            {
                "id": identifier,
                "method": case["method"],
                "profile": case["config"]["profile"],
                "seed": case["config"]["seed"],
                "condition": case["config"]["condition"],
                "status": status,
                "completed_rows": rows,
                "glucose": metrics["glucose"] if metrics else None,
                "manifest_sha256": manifest_hash,
                "attempt": attempt,
            }
        )
    if len(revisions) > 1 or len(feedback_sources) > 1:
        raise ValueError("Feedback native revisions or source inventories differ")
    lookup = {(r["profile"], r["seed"], r["condition"], r["method"]): r for r in cases}
    paired = []
    for profile in ("adult#001", "adult#002"):
        for seed in (101, 102):
            for condition in "ABCD":
                group = {m: lookup[profile, seed, condition, m] for m in METHODS}
                deltas = None
                if all(
                    row["status"] == "completed" and row["completed_rows"] == 960
                    for row in group.values()
                ):
                    deltas = {
                        "candidate_vs_base": {
                            k: group["feedback_trend"]["glucose"][k]
                            - group["basal_bolus"]["glucose"][k]
                            for k in METRICS
                        },
                        "comparator_vs_base": {
                            k: group["feedback_no_rise"]["glucose"][k]
                            - group["basal_bolus"]["glucose"][k]
                            for k in METRICS
                        },
                        "candidate_vs_comparator": {
                            k: group["feedback_trend"]["glucose"][k]
                            - group["feedback_no_rise"]["glucose"][k]
                            for k in METRICS
                        },
                    }
                paired.append(
                    {
                        "profile": profile,
                        "seed": seed,
                        "condition": condition,
                        "case_ids": {m: group[m]["id"] for m in METHODS},
                        "delta_percent_points": deltas,
                    }
                )
    status_counts = {
        method: {
            status: sum(r["method"] == method and r["status"] == status for r in cases)
            for status in sorted({r["status"] for r in cases})
        }
        for method in METHODS
    }
    return {
        "schema": schema,
        "plan_sha256": digest(study / "plan.json"),
        hash_field: specification[hash_field],
        "planned": len(cases),
        "status_counts": status_counts,
        "revisions": sorted(revisions),
        "feedback_source_inventory_count": len(feedback_sources),
        "cases": cases,
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
