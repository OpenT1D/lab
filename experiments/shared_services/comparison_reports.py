"""Descriptive comparison tables over verified native results, retaining failures."""

import csv
import io
import json

from experiments.mmtt_sampling.comparison import direction_comparison, endpoint_comparison

from . import comparison_tasks as tasks
from .store import encoded, require


def build(project, definition, directories):
    from .comparisons import REPORT_SCHEMA

    members = definition["variants"]
    baseline = next(member for member in members if member["id"] == definition["baseline"])
    m4 = definition["task"] == "m4-study-installed"
    curves = {m["id"]: tasks.m4_curve(m, directories[m["plan"]]) for m in members} if m4 else {}
    entries = []
    for member in members:
        attempt = definition["attempts"][member["plan"]]
        reason = (
            None
            if attempt["completeness"] == "complete"
            else (
                "First attempt: "
                + attempt["status"]
                + "; evidence: "
                + str(attempt["completeness"] or "not available")
            )
        )
        info = tasks.selected(project, member)
        rows = (
            tasks.m4_rows(curves[member["id"]], curves[baseline["id"]], reason)
            if m4
            else (tasks.mmtt_rows(info, member, directories[member["plan"]], reason))
        )
        entries.append({**member, "attempt": attempt, "rows": rows})
    base = next(entry for entry in entries if entry["id"] == baseline["id"])
    planned = compared = complete = 0
    for entry in entries:
        require(len(entry["rows"]) == len(base["rows"]), "Comparison case roster differs")
        for row, reference in zip(entry["rows"], base["rows"], strict=True):
            require(
                all(row[k] == reference[k] for k in ("case", "allocation", "endpoint", "unit")),
                "Incompatible endpoint/support/units; no intersected comparison",
            )
            planned += 1
            complete += row["status"] == "complete"
            if m4:
                compared += row["metrics"] is not None
            else:
                row["reference_value"] = reference["value"]
                result = endpoint_comparison([(reference["value"], row["value"])])["rows"][0]
                row["difference"] = result["difference_pmol"]
                row["absolute_difference"] = result["absolute_difference_pmol"]
                row["direction_comparison"] = direction_comparison(
                    [(reference["direction"], row["direction"])]
                )["rows"][0]["status"]
                compared += row["difference"] is not None
    require(planned <= 20000, "Comparison planned case limit exceeded")
    return {
        "schema": REPORT_SCHEMA,
        "definition": definition,
        "difference_convention": "member minus explicitly frozen baseline",
        "completeness": "complete"
        if complete == planned
        and all(entry["attempt"]["completeness"] == "complete" for entry in entries)
        else "incomplete",
        "coverage": {
            "planned_members": len(entries),
            "planned_cases": planned,
            "complete_cases": complete,
            "compared_cases": compared,
            "unavailable_contrasts": planned - compared,
        },
        "members": entries,
        "limitations": [
            "Invented synthetic inputs only; no biological ranking or treatment effect",
            "No pooled allocation, cohort uncertainty, equivalence or new interval for differences",
            "First attempts only; later retries cannot replace failures",
            "Native point completeness and conditional interval completeness remain separate",
        ],
    }


def safe(value):
    return (
        str(value)
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace("|", "\\|")
        .replace("\n", " ")
        .replace("[", "\\[")
        .replace("]", "\\]")
    )


def number(value):
    return "unavailable" if value is None else str(value)


def render(report):
    definition = report["definition"]
    lines = [
        "# " + safe(definition["name"]),
        "",
        safe(definition["question"]),
        "",
        "Difference: **member minus frozen baseline**. Baseline: "
        + safe(definition["baseline"])
        + ".",
        "",
        "First attempts only. Complete roster frozen before execution. "
        "Later retries do not replace these results.",
        "",
        "Snapshot: `"
        + definition["snapshot"]["tip"]
        + "` (ledger event "
        + str(definition["snapshot"]["sequence"])
        + ").",
        "",
        "Completeness: **"
        + report["completeness"]
        + "**. "
        + str(report["coverage"]["compared_cases"])
        + "/"
        + str(report["coverage"]["planned_cases"])
        + " planned cases have available contrasts.",
        "",
        "## Frozen changes",
        "",
        "| Member | Field | Before | After |",
        "| --- | --- | --- | --- |",
    ]
    for change in definition["changes"]:
        for field in change["fields"]:
            lines.append(
                "| "
                + " | ".join(
                    safe(value)
                    for value in (
                        change["member"],
                        field["path"],
                        json.dumps(field["before"], ensure_ascii=False),
                        json.dumps(field["after"], ensure_ascii=False),
                    )
                )
                + " |"
            )
    lines += [
        "",
        "## All planned members and cases",
        "",
        "MMTT: whole-body secretion including basal, 0–120 min, pmol; paired change "
        "is follow-up minus baseline. Points and native conditional intervals are separate. "
        "No new uncertainty interval is calculated for a difference."
        if definition["task"] != "m4-study-installed"
        else "M4: accepted candidate trajectories over 0–240 min on the full quarter-minute grid. "
        "Glucose is mg/dL; insulin and C-peptide are pmol/L. "
        "Signed AUC units are concentration × min. "
        "Loads are initial conditions, not timed meals.",
        "",
    ]
    csv_file = io.StringIO(newline="")
    writer = csv.writer(csv_file, lineterminator="\n")
    writer.writerow(
        [
            "member",
            "plan",
            "attempt",
            "case",
            "allocation",
            "endpoint",
            "unit",
            "status",
            "value",
            "baseline_value",
            "difference",
            "interval",
            "direction",
            "metrics",
            "metric_units",
            "reason",
        ]
    )
    for entry in report["members"]:
        attempt = entry["attempt"]
        lines += [
            "### " + safe(entry["label"]),
            "",
            "Plan: `"
            + entry["plan"]
            + "`. First attempt: "
            + ("`" + attempt["attempt"] + "`" if attempt["attempt"] else "unattempted")
            + ". Status: **"
            + safe(attempt["status"])
            + "**.",
            "",
            "| Case / allocation | Endpoint | Unit | Status | Value | Difference | "
            "Interval / direction |",
            "| --- | --- | --- | --- | --- | --- | --- |",
        ]
        for row in entry["rows"]:
            metrics = row.get("metrics")
            difference = (
                json.dumps({"values": metrics, "units": row["metric_units"]}, sort_keys=True)
                if metrics is not None
                else number(row.get("difference"))
            )
            lines.append(
                "| "
                + " | ".join(
                    safe(value)
                    for value in (
                        row["case"] + " / " + row["allocation"],
                        row["endpoint"],
                        row["unit"],
                        row["status"],
                        "saved trajectory" if metrics is not None else number(row["value"]),
                        difference,
                        str(row["interval"])
                        + " / "
                        + str(row["direction"])
                        + ("; " + row["reason"] if row["reason"] else ""),
                    )
                )
                + " |"
            )
            writer.writerow(
                [
                    entry["id"],
                    entry["plan"],
                    attempt["attempt"],
                    row["case"],
                    row["allocation"],
                    row["endpoint"],
                    row["unit"],
                    row["status"],
                    row["value"],
                    row.get("reference_value"),
                    row.get("difference"),
                    json.dumps(row["interval"]),
                    row["direction"],
                    json.dumps(metrics, sort_keys=True),
                    json.dumps(row.get("metric_units"), sort_keys=True),
                    row["reason"],
                ]
            )
    lines += ["", "## Limits", "", *["- " + safe(limit) for limit in report["limitations"]], ""]
    result = {
        "report.json": encoded(report),
        "report.md": "\n".join(lines).encode(),
        "comparison.csv": csv_file.getvalue().encode(),
    }
    require(
        sum(len(raw) for raw in result.values()) <= 32 * 1024 * 1024,
        "Comparison report exceeds byte limit",
    )
    return result
