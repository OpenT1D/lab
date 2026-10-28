"""Simulator-free timing and action audit of the sealed C1/0.7 matrix."""

import argparse
import hashlib
import json
import math
from pathlib import Path

from experiments.m0.simglucose.recording import write_json
from experiments.m1.artifacts import strict_json

from .feedback_study import METHODS, reconstruct
from .report import lines

ROOT = Path(__file__).resolve().parents[2]
SCHEMA = "opent1d.c1-feedback-diagnostic/1"
STEP_MIN = 3
SCORED_INTERVALS = 480
PHASES = (
    ("warmup", 0, 1440),
    ("pre_breakfast", 1440, 1860),
    ("breakfast_to_lunch", 1860, 2160),
    ("lunch_to_snack", 2160, 2400),
    ("snack_to_dinner", 2400, 2520),
    ("dinner_to_late", 2520, 2820),
    ("late", 2820, 2880),
)


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def threshold_flow(base_rows, other_rows):
    """Classify paired intervals using the existing M1 scored-glucose rule."""
    if len(base_rows) != len(other_rows) or any(
        a["start_min"] != b["start_min"] or a["end_min"] != b["end_min"]
        for a, b in zip(base_rows, other_rows)
    ):
        raise ValueError("Paired interval clocks differ")
    result = {
        "intervals": len(base_rows),
        "gained_in_from_below_70": 0,
        "gained_in_from_above_180": 0,
        "lost_in_to_below_70": 0,
        "lost_in_to_above_180": 0,
        "first_gain_start_min": None,
        "first_loss_start_min": None,
    }
    for base, other in zip(base_rows, other_rows):
        a, b = base["glucose_mg_dl"], other["glucose_mg_dl"]
        in_a, in_b = 70 <= a <= 180, 70 <= b <= 180
        if in_b and not in_a:
            key = "gained_in_from_below_70" if a < 70 else "gained_in_from_above_180"
            result[key] += 1
            if result["first_gain_start_min"] is None:
                result["first_gain_start_min"] = base["start_min"]
        elif in_a and not in_b:
            key = "lost_in_to_below_70" if b < 70 else "lost_in_to_above_180"
            result[key] += 1
            if result["first_loss_start_min"] is None:
                result["first_loss_start_min"] = base["start_min"]
    result["gained_in_intervals"] = (
        result["gained_in_from_below_70"] + result["gained_in_from_above_180"]
    )
    result["lost_in_intervals"] = result["lost_in_to_below_70"] + result["lost_in_to_above_180"]
    result["net_in_intervals"] = result["gained_in_intervals"] - result["lost_in_intervals"]
    return result


def action_summary(commands):
    if any(command["time_min"] % STEP_MIN for command in commands):
        raise ValueError("Feedback command clock is off the M1 interval grid")
    return {
        "intervals": len(commands),
        "positive_correction_intervals": sum(c["correction_u_h"] > 0 for c in commands),
        "negative_correction_intervals": sum(c["correction_u_h"] < 0 for c in commands),
        "zero_correction_intervals": sum(c["correction_u_h"] == 0 for c in commands),
        "net_commanded_correction_u": sum(c["correction_u_h"] * STEP_MIN / 60 for c in commands),
        "rise_active_intervals": sum(c["rise_mg_dl_min"] > 0 for c in commands),
        "held_base_fallback_intervals": sum(c["reason"] == "held_base_fallback" for c in commands),
        "total_clamped_intervals": sum(c["total_clamped"] for c in commands),
        "slew_limited_intervals": sum(c["slew_limited"] for c in commands),
        "integral_frozen_intervals": sum(c["integral_frozen"] for c in commands),
        "first_positive_correction_min": next(
            (c["time_min"] for c in commands if c["correction_u_h"] > 0), None
        ),
        "first_rise_min": next((c["time_min"] for c in commands if c["rise_mg_dl_min"] > 0), None),
        "max_final_basal_u_h": max((c["final_basal_u_h"] for c in commands), default=None),
    }


def build(study):
    study = Path(study)
    matrix = reconstruct(study)
    if strict_json((study / "report.json").read_bytes()) != matrix:
        raise ValueError("Saved feedback report differs from reconstruction")
    evidence = strict_json((ROOT / "experiments/c1/evidence-index.json").read_bytes())[
        "feedback_matrix"
    ]
    if (
        study.name != evidence["directory"]
        or sha256(study / "plan.json") != evidence["plan_sha256"]
        or sha256(study / "settings.json") != evidence["settings_sha256"]
        or sha256(study / "report.json") != evidence["report_sha256"]
        or matrix["planned"] != 48
        or matrix["revisions"] != [evidence["native_commit"]]
        or matrix["feedback_source_inventory_count"] != 1
    ):
        raise ValueError("Indexed C1/0.7 matrix identity differs")
    if any(
        case["status"] != "completed"
        or case["completed_rows"] != 960
        or case["attempt"]["returncode"] != 0
        for case in matrix["cases"]
    ):
        raise ValueError("C1/0.7 matrix is incomplete")
    source_maps = {"basal_bolus": set(), "feedback": set()}
    upstream = set()
    for case in matrix["cases"]:
        path = study / case["id"]
        manifest = strict_json((path / "manifest.json").read_bytes())
        if (
            manifest.get("worktree_dirty") is not False
            or manifest["revision"] != evidence["native_commit"]
        ):
            raise ValueError("Native attempt source revision or cleanliness differs")
        source_maps["basal_bolus" if case["method"] == "basal_bolus" else "feedback"].add(
            json.dumps(manifest["source_sha256"], sort_keys=True)
        )
        upstream.add(
            manifest["upstream_files_digest"]
            if case["method"] == "basal_bolus"
            else strict_json((path / "runtime.json").read_bytes())["upstream_files_digest"]
        )
    if any(len(values) != 1 for values in source_maps.values()) or len(upstream) != 1:
        raise ValueError("Native implementation or upstream source inventory differs")

    pairs = {(p["profile"], p["seed"], p["condition"]): p for p in matrix["paired"]}
    cells = []
    for profile in ("adult#001", "adult#002"):
        for seed in (101, 102):
            for condition in "ABCD":
                key = (profile, seed, condition)
                pair = pairs[key]
                rows = {
                    method: lines(study / pair["case_ids"][method], "trace.jsonl", sealed=True)
                    for method in METHODS
                }
                commands = {
                    method: lines(study / pair["case_ids"][method], "commands.jsonl", sealed=True)
                    for method in METHODS[1:]
                }
                if any(len(value) != 960 for value in (*rows.values(), *commands.values())):
                    raise ValueError("C1/0.7 audit interval roster differs")
                phases = {}
                for name, start, end in PHASES:
                    selected_rows = {
                        method: [r for r in rows[method] if start <= r["start_min"] < end]
                        for method in METHODS
                    }
                    selected_commands = {
                        method: [c for c in commands[method] if start <= c["time_min"] < end]
                        for method in METHODS[1:]
                    }
                    candidate_base = threshold_flow(
                        selected_rows["basal_bolus"], selected_rows["feedback_trend"]
                    )
                    candidate_no_rise = threshold_flow(
                        selected_rows["feedback_no_rise"], selected_rows["feedback_trend"]
                    )
                    phases[name] = {
                        "candidate_vs_base": candidate_base,
                        "candidate_vs_no_rise": candidate_no_rise,
                        "actions": {
                            method: action_summary(selected_commands[method])
                            for method in METHODS[1:]
                        },
                    }
                scored_net = sum(
                    phases[name]["candidate_vs_base"]["net_in_intervals"]
                    for name, _, _ in PHASES
                    if name != "warmup"
                )
                expected_pp = pair["delta_percent_points"]["candidate_vs_base"]["in_70_180_percent"]
                if not math.isclose(
                    scored_net * 100 / SCORED_INTERVALS, expected_pp, abs_tol=1e-10
                ):
                    raise ValueError("Threshold-flow counts do not reconstruct scored TIR")
                cells.append(
                    {
                        "profile": profile,
                        "seed": seed,
                        "condition": condition,
                        "delta_percent_points": pair["delta_percent_points"],
                        "phases": phases,
                    }
                )
    return {
        "schema": SCHEMA,
        "source_revision": evidence["native_commit"],
        "plan_sha256": evidence["plan_sha256"],
        "report_sha256": evidence["report_sha256"],
        "analysis_source_sha256": {
            str(path.relative_to(ROOT)): sha256(path)
            for path in (
                ROOT / "experiments/c1/feedback_diagnose.py",
                ROOT / "experiments/c1/feedback_study.py",
                ROOT / "experiments/c1/feedback.py",
                ROOT / "experiments/c1/report.py",
            )
        },
        "phase_boundaries_min": [
            {"name": name, "start": start, "end": end} for name, start, end in PHASES
        ],
        "cells": cells,
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
