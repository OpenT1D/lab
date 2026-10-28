"""Reconstruct separate tracks, pairing, coverage and conditional rank reversals."""

import hashlib
import json
from pathlib import Path

from experiments.m0.simglucose.recording import write_json
from experiments.m1.artifacts import digest, strict_json
from experiments.m1.historical import check_record
from experiments.m1.report import OUTCOMES, paired
from experiments.m1.validation import Snapshot

from .analysis import read_run as cambridge_run
from .run import ROOT, source_hashes
from .simglucose import read_run as simglucose_run
from .study import cases as schedule_cases
from .study import validate_plan_data

CONTROLLERS = {"simglucose": ("basal_bolus", "pid"), "lt1_cambridge": ("lt1_pid", "lt1_mpc")}


def normalize(engine, metrics):
    result = dict(metrics)
    if engine == "lt1_cambridge":
        result["glucose"] = dict(
            metrics["glucose"], in_70_180_percent=metrics["glucose"]["in_range_percent"]
        )
    elif not metrics["delivered_interval_minutes"]:
        result["delivered_insulin_u"] = None
    return result


def comparisons(cases, engine):
    controllers = CONTROLLERS[engine]
    paired_results = [paired(cases, [c, "A"], [c, d]) for c in controllers for d in "BCD"]
    paired_results += [paired(cases, [controllers[0], d], [controllers[1], d]) for d in "ABCD"]
    reversals = []
    for profile in sorted({c["config"]["profile"] for c in cases}):
        per_condition = {}
        for comparison in paired_results[-4:]:
            entry = next(p for p in comparison["profiles"] if p["profile"] == profile)
            per_condition[comparison["left"][1]] = entry
        changes = {}
        for metric in OUTCOMES:
            values = {
                condition: p["changes_right_minus_left_pp"][metric]["mean"]
                for condition, p in per_condition.items()
            }
            known = [v for v in values.values() if v is not None]
            changes[metric] = {
                "controller_difference_by_condition_pp": values,
                "rank_reversal_across_conditions": min(known) < 0 < max(known)
                if len(known) == 4
                else None,
                "conditions_with_complete_pairs": len(known),
            }
        reversals.append({"profile": profile, "outcomes": changes})
    return {"paired": paired_results, "rank_reversals": reversals}


def reconstruct(study_path):
    study_path = Path(study_path)
    snapshot = Snapshot(study_path)
    study = strict_json(snapshot.read("study.json"))
    if study.get("schema") != "opent1d.m2-study/1" or study.get("phase") not in (
        "development",
        "evaluation",
    ):
        raise ValueError("Unsupported study")
    if study.get("cases") != schedule_cases(study["phase"]):
        raise ValueError("Study must retain the entire prespecified schedule")
    if study.get("status") not in ("started", "completed", "finished_with_failures"):
        raise ValueError("Invalid study status")
    if study["phase"] == "evaluation":
        plan = strict_json(snapshot.read("evaluation-plan.json"))
        validate_plan_data(plan)
        if plan["cases"] != study["cases"]:
            raise ValueError("Study differs from frozen evaluation")
    results, consumed = [], {}
    for case in study["cases"]:
        folder = study_path / case["id"]
        if not folder.exists():
            if study["status"] != "started":
                raise ValueError("Finalized study has missing attempted cases")
            results.append(
                dict(case, status="scheduled", metrics=None, revision=None, worktree_dirty=None)
            )
            continue
        reader = cambridge_run if case["config"]["engine"] == "lt1_cambridge" else simglucose_run
        saved = reader(folder)
        m = saved["manifest"]
        if m["config"] is not None and m["config"] != case["config"]:
            raise ValueError("Run ownership differs from schedule")
        consumed[case["id"]] = saved["input_sha256"]
        results.append(
            dict(
                case,
                status=m["status"],
                error=m.get("error"),
                revision=m.get("revision"),
                worktree_dirty=m.get("worktree_dirty"),
                runtime_seconds=m.get("elapsed_seconds"),
                metrics=normalize(case["config"]["engine"], saved["metrics"]),
                unsealed=saved["unsealed"],
                discarded_trailing_fragment=saved["discarded_trailing_fragment"],
            )
        )
    statuses = {c["status"] for c in results}
    if study["status"] == "completed" and statuses != {"completed"}:
        raise ValueError("Study completion contradicts individual statuses")
    if study["status"] == "finished_with_failures" and (
        statuses & {"started", "scheduled"}
        or not statuses & {"terminated", "failed", "interrupted"}
    ):
        raise ValueError("Finalized study failure status contradicts individual statuses")
    tracks = {}
    for engine in CONTROLLERS:
        subset = [c for c in results if c["config"]["engine"] == engine]
        tracks[engine] = dict(
            comparisons(subset, engine),
            scheduled=len(subset),
            status_counts={
                s: sum(c["status"] == s for c in subset)
                for s in sorted({c["status"] for c in subset})
            },
            condition_status_counts={
                condition: {
                    status: sum(
                        c["config"]["condition"] == condition and c["status"] == status
                        for c in subset
                    )
                    for status in sorted({c["status"] for c in subset})
                }
                for condition in "ABCD"
            },
            evidence_track=study["phase"] if engine == "simglucose" else "structural_development",
            glucose_semantics="three-minute mean subcutaneous exposure"
            if engine == "simglucose"
            else "left-point plasma exposure; separate quadrature convention",
            uncertainty="seed variability and equal-weight profile median/range"
            if engine == "simglucose"
            else "one deterministic parameterization; no cohort uncertainty estimate",
        )
    directions = []
    for engine, track in tracks.items():
        for comparison in track["paired"][:6]:
            for metric, aggregate in comparison["across_profiles"].items():
                value = aggregate["median"]
                directions.append(
                    {
                        "engine": engine,
                        "controller": comparison["left"][0],
                        "condition_vs_A": comparison["right"][1],
                        "outcome": metric,
                        "direction": None
                        if value is None
                        else ("positive" if value > 0 else "negative" if value < 0 else "zero"),
                        "included_profiles": aggregate["included_profiles"],
                        "excluded_pairs": len(comparison["excluded_pairs"]),
                        "scheduled_pairs": comparison["scheduled_pairs"],
                    }
                )
    snapshot.verify_unchanged()
    return {
        "schema": "opent1d.m2-report/1",
        "study_status": study["status"],
        "phase": study["phase"],
        "study_inputs_sha256": snapshot.sha256(),
        "run_inputs_sha256": consumed,
        "analysis_source_sha256": source_hashes(),
        "scheduled": len(results),
        "cases": results,
        "tracks": tracks,
        "condition_effect_directions": directions,
        "interpretation": "Separate complete-system tracks: no matched patients, pooled glucose ranking, or physiology-only causal attribution. Comparisons condition on complete pairs; inspect exclusions. Cambridge is not held-out population evaluation.",  # noqa: E501 — generated report text
        "independent_human_reproduction": "open",
    }


def verify_development(study):
    report = reconstruct(study)
    if report["phase"] != "development" or report["study_status"] not in (
        "completed",
        "finished_with_failures",
    ):
        raise ValueError("Need a finalized development study")
    observed = {}
    for case in report["cases"]:
        if case["config"]["engine"] != "simglucose":
            if case["status"] != "completed":
                raise ValueError("Cambridge development did not complete")
            continue
        saved = simglucose_run(Path(study) / case["id"])
        m, n = saved["manifest"], saved["runtime"]
        cfg = {k: v for k, v in case["config"].items() if k != "engine"} | {
            "schema": "opent1d.simglucose/1"
        }
        identifier = f"{cfg['profile']}-{cfg['seed']}-{cfg['controller']}-{cfg['condition']}"
        observed[identifier] = {
            "config": cfg,
            "status": m["status"],
            "completed_rows": m["completed_rows"],
            **{
                k: n[k]
                for k in (
                    "upstream_revision",
                    "upstream_files_digest",
                    "packages",
                    "effective_settings",
                )
            },
            "lock_sha256": saved["input_sha256"]["simglucose-uv.lock"],
            "protocol_sha256": saved["input_sha256"]["simglucose-protocol-settings.json"],
            "trace_sha256": saved["input_sha256"]["trace.jsonl"],
            "initial_sha256": saved["input_sha256"]["initial.json"],
        }
    m1 = check_record(observed, strict_json((ROOT / "experiments/m1/baseline.json").read_bytes()))
    target = Path(study) / "lt1_cambridge-reference-101-lt1_mpc-A"
    native = strict_json((target / "runtime.json").read_bytes())
    baseline = strict_json((ROOT / "experiments/m2/baseline.json").read_bytes())
    expected = baseline["environments"].get(native["platform"])
    if expected is None:
        raise ValueError("No retained Cambridge M2 baseline for this platform")
    context = {
        "node": native["node"],
        "upstream_revision": native["upstream_revision"],
        "source_sha256": hashlib.sha256(
            json.dumps(native["source_sha256"], sort_keys=True).encode()
        ).hexdigest(),
        "settings_sha256": hashlib.sha256(
            json.dumps(native["settings"], sort_keys=True).encode()
        ).hexdigest(),
        "lock_sha256": digest(target / "package-lock.json"),
    }
    if context != expected["context"]:
        raise ValueError("Historical Cambridge native context differs")
    for key, value in expected.items():
        if key.endswith("_sha256"):
            path = key.removesuffix("_sha256") + ".jsonl"
            if digest(target / path) != value:
                raise ValueError(
                    f"Historical Cambridge M2 output differs: {path}; preserve and investigate"
                )
    return {
        "m1_historical_collection": m1,
        "cambridge_historical_output": expected,
        "scheduled": 40,
        "tolerance_applied": False,
    }


def render(report):
    lines = [
        "# M2 structural sensitivity report",
        "",
        f"Study: **{report['study_status']}**. Planned runs: {report['scheduled']}.",
        "",
        report["interpretation"],
        "",
    ]
    lines += [
        "## Condition-effect directions across separate systems",
        "",
        "Positive/negative describes the median right-minus-A metric change, not benefit. "
        "Controllers and populations are not matched.",
        "",
        "| Engine | Controller | Condition | Outcome | Direction | Included profiles "
        "| Excluded / planned pairs |",
        "| --- | --- | --- | --- | --- | --- | --- |",
    ]
    for item in report["condition_effect_directions"]:
        values = [
            item["engine"],
            item["controller"],
            item["condition_vs_A"],
            item["outcome"],
            str(item["direction"]),
            str(item["included_profiles"]),
            f"{item['excluded_pairs']}/{item['scheduled_pairs']}",
        ]
        lines.append("| " + " | ".join(values) + " |")
    lines.append("")
    for engine, track in report["tracks"].items():
        lines += [
            f"## {engine}",
            "",
            f"Track: {track['evidence_track']}. Signal: {track['glucose_semantics']}.",
            "",
            track["uncertainty"] + ".",
            "",
            f"Status counts: `{json.dumps(track['status_counts'], sort_keys=True)}`.",
            "",
            "| Profile | Seed | Controller | Condition | Status | Scored min | In range % | Below 70 % | Below 54 % | Delivered U |",  # noqa: E501 — generated report text
            "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |",
        ]

        def fmt(value):
            return "undefined" if value is None else f"{value:.6g}"

        for case in report["cases"]:
            cfg = case["config"]
            if cfg["engine"] != engine:
                continue
            m = case["metrics"]
            g = m["glucose"] if m else {}
            values = [
                g.get("observed_minutes"),
                g.get("in_70_180_percent"),
                g.get("below_70_percent"),
                g.get("below_54_percent"),
                m.get("delivered_insulin_u") if m else None,
            ]
            lines.append(
                f"| {cfg['profile']} | {cfg['seed']} | {cfg['controller']} | {cfg['condition']} | {case['status']} | "  # noqa: E501 — generated report text
                + " | ".join(fmt(v) for v in values)
                + " |"
            )
        lines += [
            "",
            "### Paired changes",
            "",
            "All changes are right minus left, in percentage points. Full per-profile means, seed ranges and excluded pairs are in report.json.",  # noqa: E501 — generated report text
            "",
            "| Left | Right | Outcome | Median | Profile range | Included profiles | Excluded / planned pairs | Sign reversal across profiles |",  # noqa: E501 — generated report text
            "| --- | --- | --- | --- | --- | --- | --- | --- |",
        ]
        for comparison in track["paired"]:
            for metric, result in comparison["across_profiles"].items():
                lines.append(
                    f"| {'/'.join(comparison['left'])} | {'/'.join(comparison['right'])} | {metric} | {fmt(result['median'])} | {fmt(result['min'])}–{fmt(result['max'])} | {result['included_profiles']}/{result['scheduled_profiles']} | {len(comparison['excluded_pairs'])}/{comparison['scheduled_pairs']} | {result['sign_reversal']} |"  # noqa: E501 — generated report text
                )
        lines += [
            "",
            "### Controller rank reversals across conditions",
            "",
            "Null means insufficient complete comparisons, not absence of reversal.",
            "",
            "```json",
            json.dumps(track["rank_reversals"], indent=2),
            "```",
            "",
        ]
    lines += [
        "## Evidence limits",
        "",
        "Independent human reproduction remains open. Sensor seeds describe simulator variability, not human confidence intervals. No clinical or broad controller-superiority claim is supported.",  # noqa: E501 — generated report text
        "",
        "The JSON report identifies every consumed input file by SHA-256, including unfinished traces, and records analysis sources.",  # noqa: E501 — generated report text
        "",
    ]
    return "\n".join(lines)


def write_report(study, output):
    report = reconstruct(study)
    output.mkdir(parents=True, exist_ok=False)
    write_json(output / "report.json", report)
    (output / "report.md").write_text(render(report))
    return report
