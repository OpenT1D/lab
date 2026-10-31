"""Known-input comparisons and complete native failure support, standard library."""

import csv
import io
import json
import math

from . import comparison_tasks, store
from .comparison_reports import safe


def known(truth, person, endpoint):
    if truth is None:
        return None
    if endpoint == "paired_change":
        return truth[person]["paired_change_pmol"]
    return truth[person][endpoint.split(":", 1)[1]]["known_total_pmol"]


def bias(truth, person, endpoint, variant, nominal, p, volume):
    if variant == "volume-120":
        return nominal * 0.2
    if variant == "nominal":
        return 0

    def visit_offset(visit):
        detail = truth[person][visit]
        if variant == "k3-120":
            return 0.2 * p["kinetics"]["k3"] * volume * detail["cpeptide_auc_pmol_min_l"]
        return (
            0.25
            * p["kinetics"]["k1"]
            / p["kinetics"]["k2"]
            * volume
            * detail["initial_cpeptide_pmol_l"]
            * -math.expm1(-p["kinetics"]["k2"] * 120)
        )

    return (
        visit_offset("after") - visit_offset("before")
        if endpoint == "paired_change"
        else visit_offset(endpoint.split(":", 1)[1])
    )


def build(project, definition, bridge, directory):
    from .connected import REPORT_SCHEMA

    p = definition["protocol"]
    stage = definition["stages"]["inverse_sampling"]
    truth = None if bridge is None else bridge["truth"]
    info = (
        comparison_tasks.plan_data(project, stage["plan"])
        if stage["plan"]
        else {
            "task": "mmtt-sampling",
            "support": {
                "participants": [
                    {"id": key, "allocation": value} for key, value in p["allocation"].items()
                ],
                "visit_order": ["before", "after"],
            },
        }
    )
    rows, native = [], {}
    for schedule in ("full", "one-minute", "fifteen-minute"):
        path = None if directory is None else directory / "studies" / schedule / "report.json"
        native[schedule] = store.read(path) if path is not None and path.exists() else None
        for variant in p["variants"]:
            member = {"selector": {"schedule": schedule, "variant": variant}}
            selected = comparison_tasks.mmtt_rows(
                info, member, directory, "Study stage: " + stage["status"]
            )
            for row in selected:
                expected = known(truth, row["case"], row["endpoint"])
                delta = (
                    None if expected is None or row["value"] is None else row["value"] - expected
                )
                point_pass = None
                if schedule == "full" and variant == "nominal":
                    point_pass = delta is not None and abs(delta) <= p["criteria"][
                        "matched_relative_error"
                    ] * max(p["criteria"]["amount_floor_pmol"], abs(expected))
                reference = None
                report = native[schedule]
                if (
                    report
                    and not report.get("import_errors")
                    and row["endpoint"] != "paired_change"
                ):
                    person = report.get("people", {}).get(row["case"], {})
                    reference = (
                        person.get("references", {})
                        .get(row["endpoint"].split(":", 1)[1], {})
                        .get("cpeptide_auc_pmol_min_l")
                    )
                rows.append(
                    {
                        **row,
                        "schedule": schedule,
                        "variant": variant,
                        "plan": stage["plan"],
                        "attempt": stage["attempt"],
                        "known_pmol": expected,
                        "difference_from_known_pmol": delta,
                        "matched_point_pass": point_pass,
                        "cpeptide_auc_pmol_min_l": reference,
                        "cpeptide_auc_nmol_min_l": None if reference is None else reference / 1000,
                    }
                )
    nominal = {
        (row["case"], row["endpoint"]): row
        for row in rows
        if row["schedule"] == "full" and row["variant"] == "nominal"
    }
    checks = []
    for row in rows:
        row.update(expected_bias_pmol=None, bias_error_pmol=None, bias_pass=None)
        if row["schedule"] != "full" or row["variant"] == "nominal":
            continue
        base = nominal[(row["case"], row["endpoint"])]["value"]
        if bridge is not None and row["value"] is not None and base is not None:
            expected = bias(
                truth,
                row["case"],
                row["endpoint"],
                row["variant"],
                base,
                p,
                bridge["whole_body_volume_l"],
            )
            error = row["value"] - base - expected
            passed = abs(error) <= p["criteria"]["mismatch_relative_error"] * max(
                1, abs(base), abs(expected)
            )
            row.update(expected_bias_pmol=expected, bias_error_pmol=error, bias_pass=passed)
            checks.append(passed)
        else:
            checks.append(False)
    matched = [row for row in rows if row["matched_point_pass"] is not None]
    points = sum(row["value"] is not None for row in rows)
    complete = sum(row["status"] == "complete" for row in rows)
    store.require(
        len(rows) == 72 and len(matched) == 6 and len(checks) == 18,
        "Connected endpoint denominator differs",
    )
    return {
        "schema": REPORT_SCHEMA,
        "definition": definition,
        "bridge": bridge,
        "completeness": "complete"
        if definition["bridge"]
        and complete == len(rows)
        and all(stage["completeness"] == "complete" for stage in definition["stages"].values())
        else "incomplete",
        "coverage": {
            "planned_rows": len(rows),
            "available_point_rows": points,
            "unavailable_point_rows": len(rows) - points,
            "complete_rows": complete,
            "planned_native_variant_pairs": 24,
            "planned_comparison_members": 6,
        },
        "point_recovery": {
            "planned": 6,
            "passed": sum(row["matched_point_pass"] for row in matched),
            "all_passed": all(row["matched_point_pass"] for row in matched),
        },
        "mismatch_controls": {"planned": 18, "passed": sum(checks), "all_passed": all(checks)},
        "rows": rows,
        "limitations": [
            "Two synthetic source-method cases, not two people or an independent cohort",
            "Fasting versus initial15g is a stimulus contrast, not treatment or restored capacity",
            "Known truth is the 0–120 pancreatic interpolant integral, including basal",
            "C-peptide AUC: native pmol min/L divided by 1000 gives nmol min/L",
            "Point recovery does not establish interval completeness or biological validity",
            "No reduced-schedule equivalence, clinical sampling claim or new uncertainty interval",
            "Fixed first attempts; all twelve native schedule/variant combinations retained",
        ],
    }


def render(report):
    value = report["definition"]
    lines = [
        "# " + safe(value["name"]),
        "",
        safe(value["question"]),
        "",
        "Connected synthetic study. Native0–240-minute evidence is preserved; "
        "only its unchanged0–120-minute prefix enters the inverse analysis.",
        "",
        "Snapshot: `"
        + value["snapshot"]["tip"]
        + "`. Completeness: **"
        + report["completeness"]
        + "**.",
        "",
        "## Fixed stage evidence",
        "",
    ]
    for name, stage in value["stages"].items():
        lines += [
            "- "
            + name
            + ": "
            + stage["status"]
            + "; evidence "
            + str(stage["completeness"])
            + "; first attempt "
            + str(stage["attempt"])
        ]
    lines += [
        "",
        "Known truth: whole-body pmol, basal included; paired change is after minus before.",
        "",
        "Matched full points: " + str(report["point_recovery"]["passed"]) + "/6; "
        "mismatch algebra: " + str(report["mismatch_controls"]["passed"]) + "/18. "
        "Point/interval/failure states remain separate.",
        "",
        "## Every planned schedule, variant and endpoint",
        "",
        "| Case / allocation | Schedule / variant | Endpoint | Status | Known pmol | "
        "Inverse pmol | Difference pmol | Interval / direction | C-peptide AUC nmol min/L |",
        "| --- | --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    columns = [
        "case",
        "allocation",
        "schedule",
        "variant",
        "plan",
        "attempt",
        "endpoint",
        "unit",
        "status",
        "known_pmol",
        "value",
        "difference_from_known_pmol",
        "interval",
        "direction",
        "matched_point_pass",
        "expected_bias_pmol",
        "bias_error_pmol",
        "bias_pass",
        "cpeptide_auc_pmol_min_l",
        "cpeptide_auc_nmol_min_l",
        "reason",
    ]
    stream = io.StringIO(newline="")
    writer = csv.writer(stream, lineterminator="\n")
    writer.writerow(columns)
    for row in report["rows"]:
        cells = [
            row["case"] + " / " + row["allocation"],
            row["schedule"] + " / " + row["variant"],
            row["endpoint"],
            row["status"],
            row["known_pmol"],
            row["value"],
            row["difference_from_known_pmol"],
            str(row["interval"]) + " / " + str(row["direction"]),
            row["cpeptide_auc_nmol_min_l"],
        ]
        lines.append(
            "| " + " | ".join(safe("unavailable" if x is None else x) for x in cells) + " |"
        )
        writer.writerow(
            [json.dumps(row[key]) if key == "interval" else row[key] for key in columns]
        )
    lines += ["", "## Limits", "", *["- " + safe(text) for text in report["limitations"]], ""]
    files = {
        "report.json": store.encoded(report),
        "report.md": "\n".join(lines).encode(),
        "study.csv": stream.getvalue().encode(),
    }
    store.require(
        sum(len(raw) for raw in files.values()) <= 32 * 1024 * 1024,
        "Connected report exceeds limit",
    )
    return files
