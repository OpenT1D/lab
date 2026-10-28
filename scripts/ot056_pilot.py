"""Prepare and audit OT-056 bookkeeping; never infer biological or product validity."""

import argparse
import csv
import hashlib
import itertools
import json
import math
import statistics
from pathlib import Path

SCHEMA = "ot056-pilot/0.1"
TOOLS = ("opent1d", "current", "notebook")
TASKS = ("task1", "task2")
SLOTS = tuple(f"R{i:02}" for i in range(1, 7))
FIELDS = {
    "roster": ("researcher", "team", "experience_ref", "participation_ref"),
    "sessions": (
        "researcher",
        "task",
        "tool",
        "case",
        "status",
        "active_seconds",
        "elapsed_seconds",
        "compute_seconds",
        "assistance_count",
        "report_sha256",
        "evidence_ref",
    ),
    "reviews": (
        "researcher",
        "task",
        "tool",
        "report_sha256",
        "correct_complete",
        "critical_errors",
        "review_ref",
    ),
    "effort": (
        "tool",
        "category",
        "study",
        "person_seconds",
        "elapsed_seconds",
        "evidence_ref",
    ),
}
GATES = (
    "ot053_disposition",
    "ot054_verified_commit",
    "ot055_verified_commit",
    "case_manifest_and_answer_key",
    "data_and_handoff_rights",
    "comparator_access_and_exports",
    "experienced_comparator_preparer",
    "independent_domain_reviewer",
    "matched_information_and_support",
    "approved_session_and_analysis_freeze",
)
CATEGORIES = ("installation", "preparation", "integration", "maintenance", "analysis")


def schedule() -> list[dict]:
    """Six tool permutations; case/tool balance and reversed second-task order."""
    rows = []
    for index, order in enumerate(itertools.permutations(TOOLS)):
        task_order = TASKS if index < 3 else TASKS[::-1]
        for block, task in enumerate(task_order, 1):
            tool_order = order if task == "task1" else order[::-1]
            for period, tool in enumerate(tool_order, 1):
                # Each tool sees each case twice across the six slots in each task.
                case_index = (TOOLS.index(tool) + index // 2 + TASKS.index(task)) % 3
                rows.append(
                    {
                        "researcher": SLOTS[index],
                        "task": task,
                        "block": block,
                        "period": period,
                        "tool": tool,
                        "case": f"{task}-{'ABC'[case_index]}",
                    }
                )
    return rows


def initialize(destination: Path) -> None:
    # Require a new directory: never overwrite observations or a frozen packet.
    destination.mkdir(parents=True, exist_ok=False)
    plan = {
        "schema": SCHEMA,
        "status": "draft",
        "evidence_kind": "unconfirmed",
        "active_timeout_seconds": 3600,
        "primary_comparator": {task: None for task in TASKS},
        "gates": dict.fromkeys(GATES, ""),
    }
    (destination / "plan.json").write_text(json.dumps(plan, indent=2) + "\n")
    for name, fields in FIELDS.items():
        with (destination / f"{name}.csv").open("w", newline="") as stream:
            csv.writer(stream).writerow(fields)
    with (destination / "allocation.csv").open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=tuple(schedule()[0]))
        writer.writeheader()
        writer.writerows(schedule())


def read_rows(root: Path, name: str) -> list[dict]:
    with (root / f"{name}.csv").open(newline="") as stream:
        reader = csv.DictReader(stream)
        if reader.fieldnames != list(FIELDS[name]):
            raise ValueError(f"{name}: unexpected CSV columns")
        rows = list(reader)
    if any(None in row or any(value is None for value in row.values()) for row in rows):
        raise ValueError(f"{name}: malformed CSV row")
    return rows


def number(value: str | int, name: str, *, integer: bool = False) -> float:
    if isinstance(value, bool):
        raise ValueError(f"{name}: boolean is not a measured number")
    result = float(value)
    if not math.isfinite(result) or result < 0 or (integer and not result.is_integer()):
        raise ValueError(
            f"{name}: expected finite nonnegative {'integer' if integer else 'number'}"
        )
    return result


def digest(value: str) -> bool:
    return len(value) == 64 and all(c in "0123456789abcdef" for c in value)


def key(row: dict) -> tuple:
    return tuple(row[field] for field in ("researcher", "task", "tool"))


def meets_targets(
    open_successes: int,
    comparator_successes: int,
    paired_successes: int,
    reduction: float | None,
    scored_reduction: float | None,
    open_errors: float,
    comparator_errors: float,
) -> bool:
    """Quantitative arithmetic only; evidence and independent review stay separate."""
    return (
        open_successes >= 5
        and comparator_successes >= 5
        and paired_successes >= 5
        and reduction is not None
        and reduction >= 0.30 - 1e-12
        and scored_reduction is not None
        and scored_reduction >= 0.30 - 1e-12
        and open_errors <= comparator_errors
    )


def summarize(root: Path) -> dict:
    plan = json.loads((root / "plan.json").read_text())
    if plan["schema"] != SCHEMA:
        raise ValueError("unsupported pilot schema")
    if not isinstance(plan["gates"], dict) or not isinstance(plan["primary_comparator"], dict):
        raise ValueError("plan gates and primary comparators must be objects")
    if any(not isinstance(plan["gates"].get(name), str) for name in GATES):
        raise ValueError("each prerequisite requires a string evidence reference")
    limit = number(plan["active_timeout_seconds"], "timeout")
    if limit <= 0:
        raise ValueError("timeout must be positive")
    blockers = [
        f"Missing freeze evidence: {name}" for name in GATES if not plan["gates"][name].strip()
    ]
    if plan["status"] != "frozen" or plan["evidence_kind"] != "human_sessions":
        blockers.append("A frozen human-session protocol and actual human evidence are required")
    roster = read_rows(root, "roster")
    if {r["researcher"] for r in roster} != set(SLOTS) or len(roster) != 6:
        blockers.append("Six actual researchers must occupy the six allocation slots")
    if any(not all(r.values()) for r in roster):
        blockers.append("Roster requires team, experience and participation evidence")
    if len({r["team"] for r in roster if r["team"]}) < 2:
        blockers.append("At least two actual teams are required")
    primary = plan["primary_comparator"]
    if any(primary.get(task) not in TOOLS[1:] for task in TASKS):
        blockers.append("Freeze the strongest applicable comparator for each task before sessions")
    allocation = {key(row): row for row in schedule()}
    # The allocation is immutable in this protocol version; changes need a new version.
    with (root / "allocation.csv").open(newline="") as stream:
        if list(csv.DictReader(stream)) != [
            {k: str(v) for k, v in row.items()} for row in schedule()
        ]:
            raise ValueError("allocation differs from this protocol's counterbalanced schedule")
    sessions, reviews = {}, {}
    for row in read_rows(root, "sessions"):
        identity = key(row)
        if identity not in allocation or identity in sessions:
            raise ValueError("unknown or duplicate session")
        if row["case"] != allocation[identity]["case"]:
            raise ValueError("session does not match allocated case")
        if row["status"] not in {"complete", "timeout", "blocked", "withdrawn"}:
            raise ValueError("invalid session status")
        for field in ("active_seconds", "elapsed_seconds", "compute_seconds", "assistance_count"):
            row[field] = number(row[field], field, integer=field == "assistance_count")
        if row["elapsed_seconds"] < max(row["active_seconds"], row["compute_seconds"]):
            raise ValueError("elapsed time cannot be shorter than active or compute time")
        if row["status"] == "complete" and not digest(row["report_sha256"]):
            raise ValueError("complete session requires report SHA-256")
        if row["status"] == "complete" and row["active_seconds"] <= 0:
            raise ValueError("complete session requires positive measured active time")
        if not row["evidence_ref"]:
            raise ValueError("session requires retained observation evidence")
        sessions[identity] = row
    for row in read_rows(root, "reviews"):
        identity = key(row)
        if identity not in sessions or identity in reviews:
            raise ValueError("unmatched or duplicate review")
        if row["report_sha256"] != sessions[identity]["report_sha256"]:
            raise ValueError("review must bind the submitted report bytes")
        if row["correct_complete"] not in {"yes", "no"} or not row["review_ref"]:
            raise ValueError("review requires a verdict and evidence reference")
        row["critical_errors"] = number(row["critical_errors"], "critical_errors", integer=True)
        if row["correct_complete"] == "yes" and (
            row["critical_errors"] or sessions[identity]["status"] != "complete"
        ):
            raise ValueError("incomplete or critically incorrect report cannot pass")
        reviews[identity] = row
    if len(sessions) != 36 or len(reviews) != 36:
        blockers.append(
            f"All 36 cells need observations and review; have {len(sessions)}/{len(reviews)}"
        )
    effort = read_rows(root, "effort")
    totals = {}
    for row in effort:
        if row["tool"] not in TOOLS or row["category"] not in CATEGORIES:
            raise ValueError("invalid effort tool/category")
        if row["study"] not in {"first", "repeat"} or not row["evidence_ref"]:
            raise ValueError("effort requires first/repeat study and evidence")
        for field in ("person_seconds", "elapsed_seconds"):
            value = number(row[field], field)
            total_key = f"{row['tool']}/{row['study']}/{field}"
            totals[total_key] = totals.get(total_key, 0) + value
    for tool, study, category in itertools.product(TOOLS, ("first", "repeat"), CATEGORIES):
        if not any(
            r["tool"] == tool and r["study"] == study and r["category"] == category for r in effort
        ):
            blockers.append(f"Unmeasured effort: {tool}/{study}/{category}")

    def success(identity: tuple) -> bool:
        session, review = sessions.get(identity), reviews.get(identity)
        return bool(
            session
            and review
            and review["correct_complete"] == "yes"
            and session["assistance_count"] == 0
            and session["active_seconds"] <= limit
        )

    comparisons = {}
    for task, comparator in itertools.product(TASKS, TOOLS[1:]):
        pairs = []
        for slot in SLOTS:
            left, right = (slot, task, "opent1d"), (slot, task, comparator)
            a, b = sessions.get(left), sessions.get(right)
            a_ok, b_ok = success(left), success(right)
            pairs.append(
                {
                    "researcher": slot,
                    "opent1d_status": a["status"] if a else "missing",
                    "comparator_status": b["status"] if b else "missing",
                    "opent1d_success": a_ok,
                    "comparator_success": b_ok,
                    "opent1d_active_seconds": a["active_seconds"] if a else None,
                    "comparator_active_seconds": b["active_seconds"] if b else None,
                    "difference_seconds": a["active_seconds"] - b["active_seconds"]
                    if a_ok and b_ok
                    else None,
                    "opent1d_scored_seconds": a["active_seconds"] if a_ok else limit,
                    "comparator_scored_seconds": b["active_seconds"] if b_ok else limit,
                    "opent1d_session": a,
                    "comparator_session": b,
                    "opent1d_review": reviews.get(left),
                    "comparator_review": reviews.get(right),
                }
            )
        paired = [p for p in pairs if p["difference_seconds"] is not None]
        denominator = (
            statistics.median([p["comparator_active_seconds"] for p in paired]) if paired else 0
        )
        reduction = (
            1 - statistics.median([p["opent1d_active_seconds"] for p in paired]) / denominator
            if denominator > 0
            else None
        )
        score_denominator = statistics.median([p["comparator_scored_seconds"] for p in pairs])
        scored_reduction = (
            1 - statistics.median([p["opent1d_scored_seconds"] for p in pairs]) / score_denominator
            if score_denominator > 0
            and all(
                p["opent1d_session"]
                and p["comparator_session"]
                and p["opent1d_review"]
                and p["comparator_review"]
                for p in pairs
            )
            else None
        )

        def errors(tool: str) -> float:
            return sum(reviews.get((s, task, tool), {}).get("critical_errors", 0) for s in SLOTS)

        gates_met = meets_targets(
            sum(p["opent1d_success"] for p in pairs),
            sum(p["comparator_success"] for p in pairs),
            len(paired),
            reduction,
            scored_reduction,
            errors("opent1d"),
            errors(comparator),
        )
        comparisons[f"{task}/{comparator}"] = {
            "pairs": pairs,
            "paired_successes": len(paired),
            "independent_success_counts": {
                "opent1d": sum(p["opent1d_success"] for p in pairs),
                comparator: sum(p["comparator_success"] for p in pairs),
            },
            "paired_difference_seconds": {
                "median": statistics.median(p["difference_seconds"] for p in paired),
                "minimum": min(p["difference_seconds"] for p in paired),
                "maximum": max(p["difference_seconds"] for p in paired),
            }
            if paired
            else None,
            "median_active_time_reduction": reduction,
            "failure_penalized_median_reduction": scored_reduction,
            "critical_errors": {tool: errors(tool) for tool in ("opent1d", comparator)},
            "quantitative_gates_met": gates_met if not blockers else None,
        }
    # A report describes recorded evidence; it never supplies a continuation decision.
    return {
        "schema": SCHEMA,
        "plan_sha256": hashlib.sha256((root / "plan.json").read_bytes()).hexdigest(),
        "status": "not_evaluable" if blockers else "requires_independent_product_decision",
        "blockers": blockers,
        "planned_cells": 36,
        "observed_cells": len(sessions),
        "reviewed_cells": len(reviews),
        "comparisons": comparisons,
        "primary_comparator": primary,
        "effort_totals": totals,
        "input_sha256": {
            p.name: hashlib.sha256(p.read_bytes()).hexdigest()
            for p in sorted(root.iterdir())
            if p.name in {"plan.json", "allocation.csv", *(f"{name}.csv" for name in FIELDS)}
        },
        "product_decision": None,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("init", "summarize"))
    parser.add_argument("directory", type=Path)
    args = parser.parse_args()
    try:
        if args.command == "init":
            initialize(args.directory)
            print("Created draft packet with blank observation forms; no human evidence recorded.")
        else:
            print(json.dumps(summarize(args.directory), indent=2, allow_nan=False))
    except (ValueError, OSError, KeyError, TypeError) as error:
        parser.exit(2, f"Pilot packet error: {error}\n")


if __name__ == "__main__":
    main()
