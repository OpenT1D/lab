"""Compare the two sealed C1 feedback attempts without opening a simulator."""

import argparse
import json
import math
from pathlib import Path

from experiments.m0.simglucose.recording import write_json
from experiments.m1.artifacts import digest, strict_json

from .feedback_diagnose import action_summary, threshold_flow
from .feedback_study import reconstruct as reconstruct_first
from .feedback_target_study import assess as assess_second
from .feedback_target_study import reconstruct as reconstruct_second
from .report import lines

ROOT = Path(__file__).resolve().parents[2]
SCHEMA = "opent1d.c1-feedback-family-review/1"
CONDITIONS = "AB"
SOURCE_KEYS = (
    "experiments/c1/feedback.py",
    "experiments/c1/simglucose_dev.py",
    "experiments/m1/adapter.py",
    "experiments/m1/control.py",
    "experiments/m1/simulation.py",
)


def _check_matrix(study, section, reader, *, assessment=None):
    matrix = reader(study)
    indexed = strict_json((ROOT / "experiments/c1/evidence-index.json").read_bytes())[section]
    if strict_json((study / "report.json").read_bytes()) != matrix:
        raise ValueError("Saved C1 feedback report differs from reconstruction")
    plan_key = "plan_sha256" if section == "feedback_matrix" else "study_plan_sha256"
    if (
        study.name != indexed["directory"]
        or digest(study / "plan.json") != indexed[plan_key]
        or digest(study / "settings.json")
        != indexed["settings_sha256" if section == "feedback_matrix" else "declaration_sha256"]
        or digest(study / "report.json") != indexed["report_sha256"]
        or matrix["planned"] != 48
        or matrix["revisions"] != [indexed["native_commit"]]
        or matrix["feedback_source_inventory_count"] != 1
        or any(
            case["status"] != "completed"
            or case["completed_rows"] != 960
            or case["attempt"]["returncode"] != 0
            for case in matrix["cases"]
        )
    ):
        raise ValueError("Indexed C1 feedback matrix identity or coverage differs")
    if assessment is not None:
        if (
            strict_json(assessment.read_bytes()) != assess_second(study)
            or digest(assessment) != indexed["assessment_sha256"]
        ):
            raise ValueError("Target-alignment assessment differs from indexed result")
    return matrix


def _matched_inputs(first, second):
    old = {case["id"]: case for case in first["cases"]}
    new = {case["id"]: case for case in second["cases"]}
    if old.keys() != new.keys() or len(old) != 48:
        raise ValueError("Feedback method rosters differ")
    for identifier, earlier in old.items():
        later = new[identifier]
        if earlier["method"] != later["method"]:
            raise ValueError("Feedback method roster changed")
        a, b = earlier["config"], later["config"]
        if earlier["method"] == "basal_bolus":
            if a != b:
                raise ValueError("M1 base configuration changed")
        elif (
            {key: value for key, value in a.items() if key != "settings"}
            != {key: value for key, value in b.items() if key != "settings"}
            or {key: value for key, value in a["settings"].items() if key != "target_mg_dl"}
            != {key: value for key, value in b["settings"].items() if key != "target_mg_dl"}
            or (a["settings"]["target_mg_dl"], b["settings"]["target_mg_dl"]) != (160, 140)
        ):
            raise ValueError("Feedback comparison changed more than the target")


def _phase(rows, commands, start, end):
    selected = [row for row in rows if start <= row["start_min"] < end]
    actions = [command for command in commands if start <= command["time_min"] < end]
    return selected, action_summary(actions)


def build(first_study, second_study, assessment):
    first_study, second_study, assessment = map(Path, (first_study, second_study, assessment))
    first = _check_matrix(first_study, "feedback_matrix", reconstruct_first)
    second = _check_matrix(
        second_study, "feedback_target_matrix", reconstruct_second, assessment=assessment
    )
    old_plan = strict_json((first_study / "plan.json").read_bytes())
    new_plan = strict_json((second_study / "plan.json").read_bytes())
    _matched_inputs(old_plan, new_plan)
    base_identity = 0
    for case in old_plan["cases"]:
        if case["method"] != "basal_bolus":
            continue
        identifier = case["id"]
        if any(
            digest(first_study / identifier / name) != digest(second_study / identifier / name)
            for name in ("initial.json", "trace.jsonl", "native-diagnostic.csv")
        ):
            raise ValueError(f"M1 base native output changed across feedback rounds: {identifier}")
        base_identity += 1
    old_manifest = strict_json(
        (first_study / "adult#001-101-B-feedback_trend/manifest.json").read_bytes()
    )
    new_manifest = strict_json(
        (second_study / "adult#001-101-B-feedback_trend/manifest.json").read_bytes()
    )
    if any(
        old_manifest["source_sha256"].get(key) != new_manifest["source_sha256"].get(key)
        for key in SOURCE_KEYS
    ):
        raise ValueError("Controller or M1 adapter source changed across rounds")
    old_native = strict_json(
        (first_study / "adult#001-101-B-feedback_trend/runtime.json").read_bytes()
    )
    new_native = strict_json(
        (second_study / "adult#001-101-B-feedback_trend/runtime.json").read_bytes()
    )
    if old_native["upstream_files_digest"] != new_native["upstream_files_digest"]:
        raise ValueError("Native simglucose implementation changed across rounds")

    old_pairs = {(p["profile"], p["seed"], p["condition"]): p for p in first["paired"]}
    new_pairs = {(p["profile"], p["seed"], p["condition"]): p for p in second["paired"]}
    cells = []
    for profile in ("adult#001", "adult#002"):
        for seed in (101, 102):
            for condition in CONDITIONS:
                key = (profile, seed, condition)
                old_pair, new_pair = old_pairs[key], new_pairs[key]
                rounds = {}
                for label, study, pair in (
                    ("target_160", first_study, old_pair),
                    ("target_140", second_study, new_pair),
                ):
                    rows = {
                        method: lines(study / pair["case_ids"][method], "trace.jsonl", sealed=True)
                        for method in ("basal_bolus", "feedback_trend")
                    }
                    commands = lines(
                        study / pair["case_ids"]["feedback_trend"], "commands.jsonl", sealed=True
                    )
                    if any(len(value) != 960 for value in (*rows.values(), commands)):
                        raise ValueError("Feedback review requires complete interval traces")
                    scored = {
                        method: [r for r in rows[method] if r["start_min"] >= 1440]
                        for method in rows
                    }
                    flow = threshold_flow(scored["basal_bolus"], scored["feedback_trend"])
                    delta = pair["delta_percent_points"]["candidate_vs_base"]
                    if not math.isclose(
                        flow["net_in_intervals"] * 100 / 480,
                        delta["in_70_180_percent"],
                        abs_tol=1e-10,
                    ):
                        raise ValueError("C1 cross-round threshold flow differs from scored metric")
                    before_rows, before_actions = _phase(
                        rows["feedback_trend"], commands, 1440, 1860
                    )
                    if len(before_rows) != 140 or before_actions["intervals"] != 140:
                        raise ValueError("Pre-breakfast phase differs")
                    first_positive = next(
                        (
                            c["time_min"]
                            for c in commands
                            if c["time_min"] >= 1860 and c["correction_u_h"] > 0
                        ),
                        None,
                    )
                    rounds[label] = {
                        "candidate_vs_base_delta_percent_points": delta,
                        "scored_threshold_flow": flow,
                        "pre_breakfast_action": before_actions,
                        "first_positive_after_breakfast_min": first_positive,
                    }
                cells.append(
                    {"profile": profile, "seed": seed, "condition": condition, "rounds": rounds}
                )
    return {
        "schema": SCHEMA,
        "first_report_sha256": digest(first_study / "report.json"),
        "second_report_sha256": digest(second_study / "report.json"),
        "second_assessment_sha256": digest(assessment),
        "native_revisions": {
            "target_160": first["revisions"][0],
            "target_140": second["revisions"][0],
        },
        "identical_base_bundles": base_identity,
        "native_upstream_files_digest": old_native["upstream_files_digest"],
        "unchanged_source_keys": list(SOURCE_KEYS),
        "cells": cells,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--first-study", type=Path, required=True)
    parser.add_argument("--second-study", type=Path, required=True)
    parser.add_argument("--second-assessment", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = build(args.first_study, args.second_study, args.second_assessment)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    write_json(args.output, result)
    print(
        json.dumps(
            {
                "cells": len(result["cells"]),
                "identical_base_bundles": result["identical_base_bundles"],
            }
        )
    )


if __name__ == "__main__":
    main()
