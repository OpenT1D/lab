"""Reconstruct C1/0.4 method failure diagnostics without a simulator."""

import argparse
import hashlib
import json
from pathlib import Path

from experiments.m0.simglucose.recording import write_json
from experiments.m1.artifacts import strict_json
from experiments.m1.contracts import MEALS

from .development_study import METHODS, reconstruct
from .report import lines

SCHEMA = "opent1d.c1-method-diagnostic/1"
ROOT = Path(__file__).resolve().parents[2]
FIRST_SCORED_MEAL_MIN = next(minute for minute, grams in MEALS if minute >= 1440 and grams)


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def signs(values):
    return {
        "positive": sum(value > 0 for value in values),
        "zero": sum(value == 0 for value in values),
        "negative": sum(value < 0 for value in values),
    }


def pid_bounds(commands, *, start_min=1440, limit_u_h=4):
    """Count post-clamp requests and upward slew use; no physiological inference."""
    scored = [command for command in commands if command["time_min"] >= start_min]
    return {
        "intervals": len(scored),
        "request_at_zero": sum(command["requested_u_h"] == 0 for command in scored),
        "request_at_max": sum(command["requested_u_h"] == limit_u_h for command in scored),
        "upward_slew_limited": sum(
            command["final_basal_u_h"] < command["requested_u_h"] for command in scored
        ),
        "max_final_u_h": max(command["final_basal_u_h"] for command in scored),
    }


def build(study):
    study = Path(study)
    matrix = reconstruct(study)
    saved = strict_json((study / "report.json").read_bytes())
    if saved != matrix:
        raise ValueError("Saved development report differs from reconstruction")
    index = strict_json((ROOT / "experiments/c1/evidence-index.json").read_bytes())
    evidence = index["development_matrix"]
    if (
        study.name != evidence["directory"]
        or sha256(study / "plan.json") != evidence["plan_sha256"]
        or sha256(study / "report.json") != evidence["report_sha256"]
    ):
        raise ValueError("Development evidence index differs")
    if matrix["planned"] != 64 or any(
        sum(row["status"] == "completed" and row["method"] == method for row in matrix["cases"])
        != 16
        for method in METHODS
    ):
        raise ValueError("Incomplete known-case matrix")
    if any(case["attempt"]["returncode"] != 0 for case in matrix["cases"]):
        raise ValueError("A development worker did not exit successfully")
    configs = {
        case["id"]: case["config"]
        for case in strict_json((study / "plan.json").read_bytes())["cases"]
    }

    revisions = set()
    source_maps = {"basal_bolus": set(), "c1": set()}
    for case in matrix["cases"]:
        manifest = strict_json((study / case["id"] / "manifest.json").read_bytes())
        if manifest.get("worktree_dirty") is not False or manifest.get("completed_rows") != 960:
            raise ValueError("Development case was not clean and complete")
        revisions.add(manifest["revision"])
        group = "basal_bolus" if case["method"] == "basal_bolus" else "c1"
        source_maps[group].add(json.dumps(manifest["source_sha256"], sort_keys=True))
    if revisions != {evidence["native_commit"]} or any(
        len(values) != 1 for values in source_maps.values()
    ):
        raise ValueError("Development source revision or inventory differs")

    paired = {row["id"]: row for row in matrix["paired"]}
    b_cases = []
    for profile in ("adult#001", "adult#002"):
        for seed in (101, 102):
            stem = f"{profile}-{seed}-B"
            methods = {}
            for method in METHODS[1:]:
                identifier = f"{stem}-{method}"
                pair = paired[identifier]
                detail = {"delta_percent_points": pair["delta_percent_points"]}
                if method.startswith("trend_overlay"):
                    diagnostic = pair["diagnostic"]
                    first = diagnostic["first_scored_extra_min"]
                    detail.update(
                        warmup_extra_u=diagnostic["warmup_commanded_extra_u"],
                        scored_extra_u=diagnostic["scored_commanded_extra_u"],
                        first_scored_extra_min=first,
                        first_extra_after_breakfast_min=(
                            first - FIRST_SCORED_MEAL_MIN if first is not None else None
                        ),
                        added_below_70_starts_min=diagnostic["added_below_70_starts_min"],
                    )
                else:
                    detail["bounds"] = pid_bounds(
                        lines(study / identifier, "commands.jsonl", sealed=True),
                        limit_u_h=configs[identifier]["settings"]["max_total_u_h"],
                    )
                methods[method] = detail
            b_cases.append({"profile": profile, "seed": seed, "methods": methods})

    outcome_signs = {}
    for method in METHODS[1:]:
        cases = [
            paired[f"{profile}-{seed}-B-{method}"]["delta_percent_points"]
            for profile in ("adult#001", "adult#002")
            for seed in (101, 102)
        ]
        outcome_signs[method] = {
            key: signs([case[key] for case in cases])
            for key in (
                "in_70_180_percent",
                "below_70_percent",
                "below_54_percent",
                "above_250_percent",
            )
        }
    pid_all_bounds = []
    for case in matrix["cases"]:
        if case["method"] == "bounded_pid":
            pid_all_bounds.append(
                {
                    "id": case["id"],
                    "bounds": pid_bounds(
                        lines(study / case["id"], "commands.jsonl", sealed=True),
                        limit_u_h=configs[case["id"]]["settings"]["max_total_u_h"],
                    ),
                }
            )
    return {
        "schema": SCHEMA,
        "source_revision": evidence["native_commit"],
        "plan_sha256": evidence["plan_sha256"],
        "report_sha256": evidence["report_sha256"],
        "first_scored_meal_min": FIRST_SCORED_MEAL_MIN,
        "b_cases": b_cases,
        "b_outcome_signs": outcome_signs,
        "pid_all_bounds": pid_all_bounds,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--study", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    write_json(args.output, build(args.study))


if __name__ == "__main__":
    main()
