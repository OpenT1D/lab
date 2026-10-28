"""Reconstruct all scheduled results and paired descriptions without a simulator."""

import json
import statistics
from pathlib import Path

from .artifacts import read_run, source_hashes, strict_json
from .contracts import Config
from .validation import Snapshot, object_value, text_value

OUTCOMES = ("in_70_180_percent", "below_70_percent", "below_54_percent")


def paired(cases, left, right):
    """Pair seeds first, then average within profiles; never silently drop failures."""
    lookup = {
        (
            c["config"]["profile"],
            c["config"]["seed"],
            c["config"]["controller"],
            c["config"]["condition"],
        ): c
        for c in cases
    }
    profiles = sorted({c["config"]["profile"] for c in cases})
    result = {
        "left": left,
        "right": right,
        "profiles": [],
        "excluded_pairs": [],
        "scheduled_pairs": 0,
    }
    for profile in profiles:
        seeds = sorted({c["config"]["seed"] for c in cases if c["config"]["profile"] == profile})
        deltas = {metric: [] for metric in OUTCOMES}
        for seed in seeds:
            a, b = lookup[(profile, seed, *left)], lookup[(profile, seed, *right)]
            result["scheduled_pairs"] += 1
            if a["status"] != "completed" or b["status"] != "completed":
                result["excluded_pairs"].append(
                    {
                        "profile": profile,
                        "seed": seed,
                        "left_status": a["status"],
                        "right_status": b["status"],
                    }
                )
                continue
            for metric in OUTCOMES:
                deltas[metric].append(
                    b["metrics"]["glucose"][metric] - a["metrics"]["glucose"][metric]
                )
        result["profiles"].append(
            {
                "profile": profile,
                "complete_pairs": len(deltas[OUTCOMES[0]]),
                "changes_right_minus_left_pp": {
                    m: {
                        "mean": statistics.mean(v) if v else None,
                        "seed_min": min(v) if v else None,
                        "seed_max": max(v) if v else None,
                    }
                    for m, v in deltas.items()
                },
            }
        )
    result["across_profiles"] = {}
    for metric in OUTCOMES:
        values = [
            p["changes_right_minus_left_pp"][metric]["mean"]
            for p in result["profiles"]
            if p["complete_pairs"]
        ]
        result["across_profiles"][metric] = {
            "median": statistics.median(values) if values else None,
            "min": min(values) if values else None,
            "max": max(values) if values else None,
            "sign_reversal": min(values) < 0 < max(values) if len(values) >= 2 else None,
            "included_profiles": len(values),
            "scheduled_profiles": len(profiles),
        }
    return result


def reconstruct(study):
    study = Path(study)
    snapshot = Snapshot(study)
    schedule = strict_json(snapshot.read("study.json"))
    object_value(schedule, "study schedule")
    if schedule.get("status") not in ("started", "completed", "finished_with_failures"):
        raise ValueError("Unknown study status")
    text_value(schedule.get("purpose"), "study purpose")
    if (
        schedule.get("schema") != "opent1d.study/1"
        or not isinstance(schedule.get("cases"), list)
        or not schedule["cases"]
    ):
        raise ValueError("Unsupported or empty study schedule")
    cases, inventory, seen, conditions = [], {}, set(), set()
    consumed = {}
    for item in schedule["cases"]:
        object_value(item, "scheduled case")
        identifier = item["id"]
        text_value(identifier, "case id")
        if Path(identifier).name != identifier or identifier in seen or identifier in (".", ".."):
            raise ValueError("Invalid or duplicate case id")
        seen.add(identifier)
        config = Config(**item["config"])
        key = (config.profile, config.seed, config.controller, config.condition)
        if key in conditions:
            raise ValueError("Duplicate scheduled configuration")
        conditions.add(key)
        folder = study / identifier
        if not folder.exists():
            if schedule["status"] != "started":
                raise ValueError("Missing case from finalized study")
            cases.append(
                {
                    "id": identifier,
                    "config": config.to_dict(),
                    "status": "scheduled",
                    "metrics": None,
                }
            )
            continue
        saved = read_run(folder)
        manifest = saved["manifest"]
        if manifest["config"] is not None and manifest["config"] != config.to_dict():
            raise ValueError("Run differs from scheduled configuration")
        inventory[identifier] = saved["input_sha256"]["manifest.json"]
        consumed[identifier] = saved["input_sha256"]
        cases.append(
            {
                "id": identifier,
                "config": config.to_dict(),
                "status": manifest["status"],
                "error": manifest.get("error"),
                "elapsed_seconds": manifest.get("elapsed_seconds"),
                "metrics": saved["metrics"],
                "unsealed": saved["unsealed"],
                "discarded_trailing_fragment": saved["discarded_trailing_fragment"],
                "warning_count": len(saved["warnings"]) if saved["warnings"] is not None else None,
            }
        )
    statuses = {c["status"] for c in cases}
    if schedule["status"] == "completed" and statuses != {"completed"}:
        raise ValueError("Study completion contradicts run statuses")
    if schedule["status"] == "finished_with_failures" and (
        statuses & {"started", "scheduled"}
        or not statuses & {"failed", "interrupted", "terminated"}
    ):
        raise ValueError("Finalized failed study contradicts run statuses")
    expected_grid = {
        (p, s, c, d) for p, s, _, _ in conditions for c in ("basal_bolus", "pid") for d in "ABCD"
    }
    if conditions != expected_grid:
        raise ValueError(
            "Paired report requires both controllers and all four conditions for every profile/seed"
        )
    comparisons = [paired(cases, (c, "A"), (c, d)) for c in ("basal_bolus", "pid") for d in "BCD"]
    comparisons += [paired(cases, ("basal_bolus", d), ("pid", d)) for d in "ABCD"]
    result = {
        "schema": "opent1d.report/2",
        "study_status": schedule["status"],
        "run_inputs_sha256": consumed,
        "purpose": schedule["purpose"],
        "study_sha256": snapshot.sha256()["study.json"],
        "manifests_sha256": inventory,
        "analysis_source_sha256": source_hashes(),
        "scheduled": len(cases),
        "status_counts": {
            s: sum(c["status"] == s for c in cases) for s in sorted({c["status"] for c in cases})
        },
        "cases": cases,
        "comparisons": comparisons,
    }
    snapshot.verify_unchanged()
    return result


def render(result):
    lines = [
        "# OpenT1D M1 development demonstration",
        "",
        result["purpose"],
        "",
        "Software demonstration on synthetic development profiles; no clinical or "
        "superiority claim.",
        "Glucose means exposure of three-minute mean subcutaneous glucose. Sensor "
        "metrics use only available raw observations.",
        "",
        f"Study status: {result['study_status']}. Scheduled runs: {result['scheduled']}; statuses: "
        f"{json.dumps(result['status_counts'], sort_keys=True)}.",
        "",
        "| Case | Status | In 70–180 (%) | Below 70 (%) | Below 54 (%) | Delivered U "
        "| Observed scored min | End min | CGM coverage (%) | Runtime s |",
        "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |",
    ]

    def fmt(value):
        return "undefined" if value is None else f"{value:.6g}"

    for case in result["cases"]:
        m = case["metrics"]
        values = (
            (
                [m["glucose"][k] for k in OUTCOMES]
                + [
                    m["delivered_insulin_u"] if m["delivered_interval_minutes"] else None,
                    m["delivered_interval_minutes"],
                    m["completed_minutes"],
                    m["sensor"]["coverage_percent"],
                ]
            )
            if m
            else [None] * 7
        )
        lines.append(
            f"| {case['id']} | {case['status']} | "
            + " | ".join(fmt(v) for v in values)
            + f" | {fmt(case.get('elapsed_seconds'))} |"
        )
    lines.extend(
        [
            "",
            "Delivered insulin covers only the observed scored minutes; "
            "an unobserved scored day is undefined in this table, never a zero-dose day. "
            "End time and status retain incomplete runs.",
            "",
        ]
    )
    errors = [c for c in result["cases"] if c.get("error")]
    if errors:
        lines.extend(["", "## Failures and incomplete runs", ""])
        lines.extend(f"- `{c['id']}`: {c['error']}" for c in errors)
    lines.extend(
        [
            "",
            "## Paired descriptive changes",
            "",
            "Right minus left, percentage points. Seeds are averaged within profiles "
            "before equal-profile summaries. Seed ranges describe simulator randomness, "
            "not human uncertainty.",
            "",
        ]
    )
    for comparison in result["comparisons"]:
        lines.extend(
            [
                f"### {'/'.join(comparison['right'])} minus {'/'.join(comparison['left'])}",
                "",
                f"Scheduled pairs: {comparison['scheduled_pairs']}; "
                f"excluded: {len(comparison['excluded_pairs'])}.",
                "",
                "| Profile | Complete pairs | In 70–180 change | "
                "Below 70 change | Below 54 change |",
                "| --- | --- | --- | --- | --- |",
            ]
        )
        for profile in comparison["profiles"]:
            values = [profile["changes_right_minus_left_pp"][key] for key in OUTCOMES]
            cells = [
                f"{fmt(v['mean'])} [{fmt(v['seed_min'])}, {fmt(v['seed_max'])}]" for v in values
            ]
            lines.append(
                f"| {profile['profile']} | {profile['complete_pairs']} | "
                + " | ".join(cells)
                + " |"
            )
        cells = [
            f"{fmt(v['median'])} [{fmt(v['min'])}, {fmt(v['max'])}]"
            for v in (comparison["across_profiles"][key] for key in OUTCOMES)
        ]
        lines.extend(["| Profile median [range] | — | " + " | ".join(cells) + " |", ""])
        reversals = [k for k, v in comparison["across_profiles"].items() if v["sign_reversal"]]
        assessable = all(
            v["sign_reversal"] is not None for v in comparison["across_profiles"].values()
        )
        label = (
            (", ".join(reversals) or "none")
            if assessable
            else "not assessable (fewer than two included profiles)"
        )
        lines.extend(["Profile sign reversals: " + label + ".", ""])
        for excluded in comparison["excluded_pairs"]:
            lines.append(
                f"- Excluded {excluded['profile']}, seed {excluded['seed']}: "
                f"{excluded['left_status']} / {excluded['right_status']}."
            )
        if comparison["excluded_pairs"]:
            lines.append("")
    lines.extend(
        [
            "## Full per-run metrics and provenance",
            "",
            "The companion JSON includes weighted mean, population SD/CV, all "
            "thresholds, coverage, runtime, warnings, failures and manifest hashes. Each "
            "run directory retains its inputs, native diagnostics, source/environment "
            "hashes and logs.",
            "",
            "No evaluation profiles were used. PID settings are unchanged and can "
            "produce low glucose. The 24-hour initialization is a protocol convention, "
            "not proven convergence. Independent reproduction, a stronger comparator and "
            "external validation remain open.",
            "",
        ]
    )
    return "\n".join(lines)


def write_report(study, output):
    result = reconstruct(study)
    output = Path(output)
    output.mkdir(parents=True, exist_ok=False)
    (output / "report.json").write_text(json.dumps(result, indent=2, allow_nan=False) + "\n")
    (output / "report.md").write_text(render(result))
    return result
