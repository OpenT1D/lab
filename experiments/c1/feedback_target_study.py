"""Run and assess the declared C1/0.9 target-alignment development matrix.

Assessment reads sealed native artifacts but imports no simulator. All 48
attempts remain in the denominator, including missing and failed attempts.
"""

import argparse
import hashlib
import json
import math
from pathlib import Path

from experiments.m0.simglucose.recording import write_json
from experiments.m1.artifacts import digest, strict_json

from .feedback_diagnose import action_summary, threshold_flow
from .feedback_study import METHODS, execute_plan, reconstruct_plan
from .feedback_target_plan import DECLARATION, ROOT, plan
from .report import lines

SCHEMA = "opent1d.c1-feedback-target-study/1"
ASSESSMENT_SCHEMA = "opent1d.c1-feedback-target-assessment/1"
METRICS = ("in_70_180_percent", "below_70_percent", "below_54_percent", "above_250_percent")


def _declared_plan():
    specification = plan()
    indexed = strict_json((ROOT / "experiments/c1/evidence-index.json").read_bytes())[
        "feedback_target_plan"
    ]
    canonical = json.dumps(specification, sort_keys=True, indent=2) + "\n"
    if (
        hashlib.sha256(canonical.encode()).hexdigest() != indexed["plan_sha256"]
        or digest(DECLARATION) != indexed["declaration_sha256"]
    ):
        raise ValueError("C1/0.9 plan differs from predeclared hash")
    return specification


def execute(study, *, workers=4, timeout_seconds=300):
    return execute_plan(
        study,
        _declared_plan(),
        DECLARATION,
        "declaration_sha256",
        reconstruct,
        workers=workers,
        timeout_seconds=timeout_seconds,
    )


def reconstruct(study):
    return reconstruct_plan(study, _declared_plan(), "declaration_sha256", SCHEMA)


def _insulin_summary(rows, commands=None):
    scored = [row for row in rows if row["start_min"] >= 1440]
    result = {
        "modeled_delivered_u": sum(row["delivered_u_min"] * 3 for row in scored),
        "commanded_basal_u": sum(row["basal_u_min"] * 3 for row in scored),
        "commanded_bolus_u": sum(row["bolus_u_min"] * 3 for row in scored),
    }
    if commands is not None:
        scored_commands = [c for c in commands if c["time_min"] >= 1440]
        if len(scored_commands) != len(scored):
            raise ValueError("Scored commands and trace differ")
        result["commanded_correction_u"] = sum(
            c["correction_u_h"] * 3 / 60 for c in scored_commands
        )
        result["limit_events"] = {
            key: sum(c[key] for c in commands)
            for key in ("total_clamped", "slew_limited", "integral_frozen")
        }
        result["held_base_fallback_intervals"] = sum(
            c["reason"] == "held_base_fallback" for c in commands
        )
        result["pre_breakfast_actions"] = action_summary(
            [c for c in commands if 1440 <= c["time_min"] < 1860]
        )
    return result


def advancement_criteria(condition, delta):
    """The C1/0.8 development gate, applied to a single known cell."""
    if condition == "B":
        return {
            "positive_in_70_180": delta["in_70_180_percent"] > 0,
            "no_below_70_increase": delta["below_70_percent"] <= 0,
            "no_below_54_increase": delta["below_54_percent"] <= 0,
            "no_above_250_increase": delta["above_250_percent"] <= 0,
        }
    if condition == "A":
        return {
            "no_in_70_180_decrease": delta["in_70_180_percent"] >= 0,
            "no_below_70_increase": delta["below_70_percent"] <= 0,
            "no_below_54_increase": delta["below_54_percent"] <= 0,
        }
    return None


def assess(study):
    study = Path(study)
    report = reconstruct(study)
    if strict_json((study / "report.json").read_bytes()) != report:
        raise ValueError("Saved C1/0.9 report differs from reconstruction")
    by_id = {case["id"]: case for case in report["cases"]}
    pairs = []
    failures = []
    source_maps = {"basal_bolus": set(), "feedback": set()}
    upstream = set()
    for case in report["cases"]:
        if case["status"] == "attempt_unrecorded":
            continue
        path = study / case["id"]
        if case["status"] == "completed" and case["completed_rows"] == 960:
            manifest = strict_json((path / "manifest.json").read_bytes())
            source_maps["basal_bolus" if case["method"] == "basal_bolus" else "feedback"].add(
                json.dumps(manifest["source_sha256"], sort_keys=True)
            )
            upstream.add(
                manifest["upstream_files_digest"]
                if case["method"] == "basal_bolus"
                else strict_json((path / "runtime.json").read_bytes())["upstream_files_digest"]
            )
    provenance_ok = (
        len(report["revisions"]) == 1
        and report["feedback_source_inventory_count"] == 1
        and all(len(values) == 1 for values in source_maps.values())
        and len(upstream) == 1
    )
    for pair in report["paired"]:
        key = (pair["profile"], pair["seed"], pair["condition"])
        group = {method: by_id[pair["case_ids"][method]] for method in METHODS}
        complete = all(
            case["status"] == "completed"
            and case["completed_rows"] == 960
            and case["attempt"]["returncode"] == 0
            for case in group.values()
        )
        criteria = None
        flow = None
        insulin = None
        if complete:
            rows = {
                method: lines(study / group[method]["id"], "trace.jsonl", sealed=True)
                for method in METHODS
            }
            commands = {
                method: lines(study / group[method]["id"], "commands.jsonl", sealed=True)
                for method in METHODS[1:]
            }
            if any(len(value) != 960 for value in (*rows.values(), *commands.values())):
                raise ValueError(f"C1/0.9 trace or command roster differs: {key}")
            insulin = {
                method: _insulin_summary(rows[method], commands.get(method)) for method in METHODS
            }
            if pair["condition"] in ("A", "B"):
                flow = {
                    name: threshold_flow(
                        [r for r in rows[left] if r["start_min"] >= 1440],
                        [r for r in rows[right] if r["start_min"] >= 1440],
                    )
                    for name, left, right in (
                        ("candidate_vs_base", "basal_bolus", "feedback_trend"),
                        ("candidate_vs_no_rise", "feedback_no_rise", "feedback_trend"),
                    )
                }
                delta = pair["delta_percent_points"]["candidate_vs_base"]["in_70_180_percent"]
                if not math.isclose(
                    flow["candidate_vs_base"]["net_in_intervals"] * 100 / 480, delta, abs_tol=1e-10
                ):
                    raise ValueError(f"C1/0.9 threshold flow differs from metric: {key}")
            delta = pair["delta_percent_points"]["candidate_vs_base"]
            criteria = advancement_criteria(pair["condition"], delta)
            if criteria:
                failures.extend(
                    {"profile": key[0], "seed": key[1], "condition": key[2], "criterion": name}
                    for name, passed in criteria.items()
                    if not passed
                )
        pairs.append(
            {**pair, "complete": complete, "criteria": criteria, "flow": flow, "insulin": insulin}
        )
    all_complete = all(pair["complete"] for pair in pairs)
    if not all_complete:
        failures.append({"criterion": "all_48_complete_and_verified"})
    if not provenance_ok:
        failures.append({"criterion": "single_clean_native_revision_and_sources"})
    return {
        "schema": ASSESSMENT_SCHEMA,
        "matrix_report_sha256": digest(study / "report.json"),
        "planned": report["planned"],
        "status_counts": report["status_counts"],
        "revisions": report["revisions"],
        "provenance_ok": provenance_ok,
        "development_screen_pass": not failures,
        "failures": failures,
        "pairs": pairs,
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
    score = sub.add_parser("assess")
    score.add_argument("--study", type=Path, required=True)
    score.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.command == "run":
        result = execute(args.output, workers=args.workers, timeout_seconds=args.timeout_seconds)
        print(
            json.dumps(
                {"planned": result["planned"], "status_counts": result["status_counts"]},
                sort_keys=True,
            )
        )
    elif args.command == "report":
        print(json.dumps(reconstruct(args.study), sort_keys=True, separators=(",", ":")))
    else:
        result = assess(args.study)
        write_json(args.output, result)
        print(
            json.dumps(
                {
                    "development_screen_pass": result["development_screen_pass"],
                    "failures": result["failures"],
                },
                sort_keys=True,
            )
        )


if __name__ == "__main__":
    main()
