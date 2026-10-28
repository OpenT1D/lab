"""Reconstruct LIT-002 engineering results from sealed artifacts, with stdlib only.

Hashes detect changed artifacts; they are not an authenticated scientific signature.
No simulator, kinetic implementation or source checkout is imported by this report.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from itertools import combinations
from pathlib import Path, PurePosixPath

STATES = {"Q1", "Q2", "S1", "S2", "I", "x1", "x2", "x3", "D1", "D2"}
FIELDS = {
    "time_min",
    "glucose_mg_dl",
    "insulin_mU_L",
    "appearance_mU_min",
    "delivered_u_h",
    "delayed_delivered_u_h",
    "intake_g_min",
    "depot_mU",
    "delay_queue_mU",
    "total_subcutaneous_mU",
    "cumulative_delivered_mU",
    "cumulative_delayed_delivered_mU",
    "cumulative_carbohydrates_g",
    "balance_derived_absorbed_mU",
    "state",
}
CONFIG_SHARED = (
    "horizon_min",
    "sample_step_min",
    "relative_tolerance",
    "equilibrium_glucose_mg_dl",
    "absorption",
)
CLAIM = (
    "Synthetic structural sensitivity and numerical verification only. "
    "No physiological superiority, clinical prediction, patient reproduction or "
    "full-Faggionato model reproduction is established."
)


def finite(value: object, name: str, minimum: float | None = None) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        raise ValueError(f"Nonfinite or nonnumeric {name}")
    if minimum is not None and value < minimum:
        raise ValueError(f"Invalid negative {name}")
    return float(value)


def reject_constant(value: str) -> None:
    raise ValueError(f"Nonstandard JSON constant: {value}")


def read_json(path: Path) -> dict:
    try:
        value = json.loads(path.read_text(), parse_constant=reject_constant)
    except (OSError, json.JSONDecodeError, ValueError) as error:
        raise ValueError(f"Cannot read strict JSON {path.name}: {error}") from error
    if not isinstance(value, dict):
        raise ValueError(f"Expected object in {path.name}")
    return value


def contained(study: Path, name: str) -> Path:
    if not isinstance(name, str) or not name or "\\" in name:
        raise ValueError("Invalid artifact path")
    relative = PurePosixPath(name)
    if relative.is_absolute() or any(part in ("", ".", "..") for part in name.split("/")):
        raise ValueError(f"Unsafe artifact path: {name}")
    path = study.joinpath(*relative.parts)
    if not path.resolve().is_relative_to(study.resolve()):
        raise ValueError(f"Artifact escapes study: {name}")
    return path


def seal(study: Path, manifest: dict) -> dict[str, str]:
    artifacts = manifest.get("artifacts")
    if not isinstance(artifacts, dict) or not artifacts:
        raise ValueError("Missing artifact hash inventory")
    for name, digest in artifacts.items():
        path = contained(study, name)
        if (
            not isinstance(digest, str)
            or len(digest) != 64
            or any(c not in "0123456789abcdef" for c in digest)
        ):
            raise ValueError(f"Invalid artifact hash: {name}")
        if not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest() != digest:
            raise ValueError(f"Missing or changed artifact: {name}")
    return artifacts


def required(study: Path, artifacts: dict, name: str) -> Path:
    if name not in artifacts:
        raise ValueError(f"Required artifact absent from hash inventory: {name}")
    return contained(study, name)


def close(actual: float, expected: float, tolerance: float) -> bool:
    return abs(actual - expected) <= tolerance * max(1.0, abs(expected))


def amount(scenario: dict, basal: float, start: float, end: float) -> float:
    return basal * (end - start) / 60 + sum(
        max(0, min(end, item["end_min"]) - max(start, item["start_min"])) * item["extra_u_h"] / 60
        for item in scenario["insulin_segments"]
    )


def rate(scenario: dict, basal: float, time: float) -> float:
    return basal + sum(
        item["extra_u_h"]
        for item in scenario["insulin_segments"]
        if item["start_min"] <= time < item["end_min"]
    )


def meal_amount(scenario: dict, time: float) -> float:
    return sum(
        max(0, min(time, item["start_min"] + item["duration_min"]) - item["start_min"])
        * item["grams"]
        / item["duration_min"]
        for item in scenario["meals"]
    )


def meal_rate(scenario: dict, time: float) -> float:
    return sum(
        item["grams"] / item["duration_min"]
        for item in scenario["meals"]
        if item["start_min"] <= time < item["start_min"] + item["duration_min"]
    )


def sample_times(protocol: dict, scenario: dict) -> list[float]:
    horizon, step = protocol["horizon_min"], protocol["sample_step_min"]
    times = {0.0, float(horizon)}
    for i in range(math.floor(horizon / step) + 1):
        times.add(round(i * step, 10))
    for item in scenario["insulin_segments"]:
        for time in (item["start_min"], item["end_min"]):
            times.add(float(time))
            delayed = time + protocol["absorption"]["tau_min"]
            if delayed <= horizon:
                times.add(round(delayed, 10))
    for item in scenario["meals"]:
        times.update((float(item["start_min"]), float(item["start_min"] + item["duration_min"])))
    return sorted(times)


def read_trace(path: Path, expected_times: list[float]) -> list[dict]:
    rows = []
    try:
        for line in path.read_text().splitlines():
            row = json.loads(line)
            if (
                not isinstance(row, dict)
                or set(row) != FIELDS
                or not isinstance(row["state"], dict)
                or set(row["state"]) != STATES
            ):
                raise ValueError("Unexpected native trace schema")
            for key, value in row.items():
                if key == "state":
                    for state, number in value.items():
                        finite(number, f"state.{state}")
                else:
                    finite(value, key)
            rows.append(row)
    except (OSError, json.JSONDecodeError, ValueError) as error:
        raise ValueError(f"Invalid trace {path}: {error}") from error
    if len(rows) != len(expected_times) or any(
        abs(row["time_min"] - time) > 1e-9 for row, time in zip(rows, expected_times, strict=True)
    ):
        raise ValueError(f"Incomplete or unexpected trace sample grid: {path}")
    return rows


def extremes(rows: list[dict], field: str) -> dict:
    low = min(rows, key=lambda row: row[field])
    high = max(rows, key=lambda row: row[field])
    return {
        "minimum": low[field],
        "maximum": high[field],
        "min_time_min": low["time_min"],
        "max_time_min": high["time_min"],
    }


def curve_difference(rows: list[dict], reference: list[dict]) -> dict:
    if [r["time_min"] for r in rows] != [r["time_min"] for r in reference]:
        raise ValueError("Comparison curves have different sample grids")
    output = {}
    for label, field, unit in (
        ("glucose", "glucose_mg_dl", "mg_dl"),
        ("insulin", "insulin_mU_L", "mU_per_L"),
    ):
        values = [row[field] - ref[field] for row, ref in zip(rows, reference, strict=True)]
        index = max(range(len(values)), key=lambda i: abs(values[i]))
        output[f"max_abs_{label}_difference_{unit}"] = abs(values[index])
        output[f"signed_{label}_difference_at_max_{unit}"] = values[index]
        output[f"time_of_max_{label}_difference_min"] = rows[index]["time_min"]
    return output


def contrast(rows: list[dict], reference: list[dict]) -> list[dict]:
    if [r["time_min"] for r in rows] != [r["time_min"] for r in reference]:
        raise ValueError("Contrast curves have different sample grids")
    return [
        {
            "time_min": row["time_min"],
            "glucose_mg_dl": row["glucose_mg_dl"] - ref["glucose_mg_dl"],
            "insulin_mU_L": row["insulin_mU_L"] - ref["insulin_mU_L"],
        }
        for row, ref in zip(rows, reference, strict=True)
    ]


def check_case(
    rows: list[dict], scenario: dict, arm: str, runtime: dict, verification: dict, protocol: dict
) -> dict:
    criteria = protocol["criteria"]
    settings = runtime["settings"]
    basal = finite(settings["basal_u_h"], "basal", 0)
    bw = finite(settings["native_parameters"]["BW"], "body weight", 0)
    if bw == 0:
        raise ValueError("Zero body weight")
    delay = protocol["absorption"]["tau_min"] if arm == "faggionato_sc" else 0
    tol = criteria["input_amount_relative_tolerance"]
    parameters = settings["native_parameters"]
    tmax = finite(parameters["tmaxI"], "tmaxI", 0)
    if not tmax:
        raise ValueError("Zero native absorption time")
    source = protocol["absorption"]
    mean = (
        source["tau_min"]
        + 1 / (source["ka1_per_min"] + source["kd_per_min"])
        + source["kd_per_min"]
        / (source["ka1_per_min"] + source["kd_per_min"])
        / source["ka2_per_min"]
    )
    if not close(tmax, mean / 2 if arm == "cambridge_mean_matched" else 55, 1e-12):
        raise ValueError("Native absorption parameter differs from frozen arm")
    input_ok, internal_ok = True, True
    for row in rows:
        time = row["time_min"]
        expected = {
            "delivered_u_h": rate(scenario, basal, time),
            "delayed_delivered_u_h": rate(scenario, basal, time - delay),
            "intake_g_min": meal_rate(scenario, time),
            "cumulative_delivered_mU": 1000 * amount(scenario, basal, 0, time),
            "cumulative_delayed_delivered_mU": 1000 * amount(scenario, basal, -delay, time - delay),
            "cumulative_carbohydrates_g": meal_amount(scenario, time),
        }
        input_ok &= all(close(row[key], value, tol) for key, value in expected.items())
        queue = 1000 * amount(scenario, basal, time - delay, time) if delay else 0
        depot = row["state"]["S1"] + row["state"]["S2"]
        appearance = (
            source["ka1_per_min"] * row["state"]["S1"] + source["ka2_per_min"] * row["state"]["S2"]
            if arm == "faggionato_sc"
            else row["state"]["S2"] / tmax
        )
        internal = {
            "appearance_mU_min": appearance,
            "insulin_mU_L": row["state"]["I"],
            "depot_mU": depot,
            "delay_queue_mU": queue,
            "total_subcutaneous_mU": depot + queue,
            "balance_derived_absorbed_mU": row["cumulative_delayed_delivered_mU"]
            - depot
            + rows[0]["depot_mU"],
        }
        internal_ok &= all(close(row[key], value, tol) for key, value in internal.items())
    source_checks = verification.get("checks")
    if (
        not isinstance(source_checks, dict)
        or not source_checks
        or any(type(value) is not bool for value in source_checks.values())
    ):
        raise ValueError("Invalid case verification checks")
    mass_scale = max(
        1, (rows[0]["total_subcutaneous_mU"] + rows[-1]["cumulative_delivered_mU"]) / bw
    )
    checks = {
        "frozen_input_schedule": bool(input_ok),
        "trace_internal_consistency": bool(internal_ok),
        "state_positivity": min(
            value
            for row in rows
            for value in (
                *row["state"].values(),
                row["glucose_mg_dl"],
                row["insulin_mU_L"],
                row["appearance_mU_min"],
                row["delay_queue_mU"],
            )
        )
        >= -criteria["negative_state_tolerance"],
        "case_verification": all(source_checks.values()),
    }
    for name in ("max_sc_state_error_mU_per_kg", "max_appearance_error_mU_per_kg_min"):
        checks[name] = finite(verification.get(name), name, 0) <= criteria[name]
    checks["mass_residual"] = (
        finite(verification.get("max_mass_residual_mU_per_kg"), "mass residual", 0)
        <= criteria["relative_mass_tolerance"] * mass_scale
    )
    if scenario["id"] == "basal":
        checks["basal_glucose_invariance"] = (
            max(abs(row["glucose_mg_dl"] - protocol["equilibrium_glucose_mg_dl"]) for row in rows)
            <= criteria["max_basal_glucose_deviation_mg_dl"]
        )
        checks["basal_insulin_invariance"] = (
            max(abs(row["insulin_mU_L"] - rows[0]["insulin_mU_L"]) for row in rows)
            <= criteria["max_basal_insulin_deviation_mU_per_L"]
        )
    return checks


def reconstruct(study: Path) -> dict:
    """Verify the frozen matrix and reconstruct metrics without model dependencies."""
    study = Path(study).resolve()
    manifest = read_json(study / "manifest.json")
    if manifest.get("schema") != "lit002-study/1" or manifest.get("status") not in (
        "completed",
        "completed_with_failures",
    ):
        raise ValueError("Expected sealed LIT-002 study manifest")
    artifacts = seal(study, manifest)
    protocol = read_json(required(study, artifacts, "protocol.json"))
    if manifest.get("protocol_sha256") != artifacts["protocol.json"]:
        raise ValueError("Manifest protocol hash differs from artifact inventory")
    source_parameters = "source/experiments/literature/lit001/parameters.json"
    required(study, artifacts, source_parameters)
    if artifacts[source_parameters] != protocol.get("source_parameter_record_sha256"):
        raise ValueError("Source parameter snapshot differs from frozen protocol")
    if not manifest.get("preparation_error"):
        required(study, artifacts, "impulse.csv")
        required(study, artifacts, "impulse_metrics.json")
    if protocol.get("schema") != "lit002-protocol/1":
        raise ValueError("Unexpected protocol schema")
    arms, scenarios = protocol["arms"], protocol["scenarios"]
    if (
        len(arms) != 3
        or len(set(arms)) != 3
        or len(scenarios) != 3
        or len({s["id"] for s in scenarios}) != 3
    ):
        raise ValueError("Expected three distinct arms and scenarios")
    if set(arms) != {"cambridge_native", "cambridge_mean_matched", "faggionato_sc"} or {
        s["id"] for s in scenarios
    } != {"basal", "pulse", "meal_pulse"}:
        raise ValueError("Unexpected frozen arms or scenarios")
    scenario_by_id = {s["id"]: s for s in scenarios}
    resolutions = {
        "standard": protocol["max_step_min"],
        "refined": protocol["refinement_max_step_min"],
    }
    expected = {
        (s["id"], arm, resolution) for s in scenarios for arm in arms for resolution in resolutions
    }
    cases = manifest.get("cases")
    if (
        manifest.get("expected_case_count") != 18
        or not isinstance(cases, list)
        or len(cases) != len(expected)
    ):
        raise ValueError("Incomplete frozen case matrix")
    seen, ids = set(), set()
    for case in cases:
        key = (case.get("scenario"), case.get("arm"), case.get("resolution"))
        case_id = case.get("id")
        if (
            key not in expected
            or key in seen
            or not isinstance(case_id, str)
            or not case_id
            or case_id in ids
        ):
            raise ValueError("Duplicate or unexpected case in frozen matrix")
        if (
            case.get("path") != f"cases/{case_id}"
            or "/" in case_id
            or "\\" in case_id
            or case_id in (".", "..")
        ):
            raise ValueError("Invalid case path")
        if case.get("max_step_min") != resolutions[key[2]] or case.get("status") not in (
            "completed",
            "failed",
        ):
            raise ValueError("Invalid case resolution or status")
        seen.add(key)
        ids.add(case_id)
    if seen != expected:
        raise ValueError("Missing planned case")
    failures, metrics, traces, runtimes = [], {}, {}, {}
    checks = {
        "artifact_integrity": True,
        "complete_planned_matrix": True,
        "preparation_completed": not bool(manifest.get("preparation_error")),
    }
    for case in sorted(cases, key=lambda c: c["id"]):
        case_id, prefix = case["id"], case["path"]
        key = (case["scenario"], case["arm"], case["resolution"])
        scenario = scenario_by_id[case["scenario"]]
        config = read_json(required(study, artifacts, prefix + "/config.json"))
        expected_config = {name: protocol[name] for name in CONFIG_SHARED}
        expected_config.update(
            arm=case["arm"],
            max_step_min=case["max_step_min"],
            insulin_segments=scenario["insulin_segments"],
            meals=scenario["meals"],
        )
        if config != expected_config:
            raise ValueError(f"Case configuration differs from frozen protocol: {case_id}")
        if case["status"] == "failed":
            failures.append(
                {
                    "case_id": case_id,
                    "scenario": case["scenario"],
                    "arm": case["arm"],
                    "resolution": case["resolution"],
                    "error": case.get("error"),
                    "path": prefix,
                }
            )
            continue
        runtime = read_json(required(study, artifacts, prefix + "/runtime.json"))
        result = read_json(required(study, artifacts, prefix + "/result.json"))
        verification = read_json(required(study, artifacts, prefix + "/verification.json"))
        rows = read_trace(
            required(study, artifacts, prefix + "/trace.jsonl"), sample_times(protocol, scenario)
        )
        if (
            result.get("status") != "completed"
            or result.get("rows") != len(rows)
            or result.get("final_minute") != protocol["horizon_min"]
        ):
            raise ValueError(f"Completed case has inconsistent result: {case_id}")
        if (
            runtime.get("upstream_revision") != protocol["native_revision"]
            or runtime.get("node") != protocol["node_version"]
            or runtime.get("settings", {}).get("arm") != case["arm"]
        ):
            raise ValueError(f"Case runtime differs from protocol: {case_id}")
        upstream_hashes = runtime.get("source_sha256")
        if (
            not isinstance(upstream_hashes, dict)
            or not upstream_hashes
            or any(
                not isinstance(digest, str)
                or len(digest) != 64
                or any(c not in "0123456789abcdef" for c in digest)
                for digest in upstream_hashes.values()
            )
        ):
            raise ValueError("Missing or malformed upstream source hash inventory")
        case_checks = check_case(rows, scenario, case["arm"], runtime, verification, protocol)
        for name, passed in case_checks.items():
            checks[f"{case_id}:{name}"] = passed
        metrics[case_id] = {
            "scenario": case["scenario"],
            "arm": case["arm"],
            "resolution": case["resolution"],
            "row_count": len(rows),
            "glucose": extremes(rows, "glucose_mg_dl"),
            "insulin": extremes(rows, "insulin_mU_L"),
            "appearance": extremes(rows, "appearance_mU_min"),
            "delivered_U": rows[-1]["cumulative_delivered_mU"] / 1000,
            "carbohydrates_g": rows[-1]["cumulative_carbohydrates_g"],
            "remaining_depot_mU": rows[-1]["depot_mU"],
            "remaining_delay_queue_mU": rows[-1]["delay_queue_mU"],
            "final_balance_derived_absorbed_mU": rows[-1]["balance_derived_absorbed_mU"],
            "minimum_native_state": min(value for row in rows for value in row["state"].values()),
            "verification": verification,
            "checks": case_checks,
        }
        traces[key], runtimes[key] = rows, runtime
    checks["all_cases_completed"] = not failures
    if bool(failures) != (manifest["status"] == "completed_with_failures"):
        raise ValueError("Study status contradicts case statuses")
    common_native = []
    basals, upstream_sources = [], []
    for runtime in runtimes.values():
        settings = runtime["settings"]
        common_native.append(
            {k: v for k, v in settings["native_parameters"].items() if k != "tmaxI"}
        )
        basals.append(settings["basal_u_h"])
        upstream_sources.append(runtime["source_sha256"])
    checks["unchanged_nonabsorption_native_parameters"] = bool(common_native) and all(
        p == common_native[0] for p in common_native
    )
    checks["common_basal_delivery"] = bool(basals) and all(b == basals[0] for b in basals)
    checks["common_upstream_source_hashes"] = bool(upstream_sources) and all(
        s == upstream_sources[0] for s in upstream_sources
    )
    comparisons, refinements, contrast_refinements = [], [], []
    criteria = protocol["criteria"]
    for scenario in scenario_by_id:
        for resolution in resolutions:
            for reference_arm, arm in combinations(arms, 2):
                key, refkey = (scenario, arm, resolution), (scenario, reference_arm, resolution)
                identity = {
                    "scenario": scenario,
                    "resolution": resolution,
                    "arm": arm,
                    "reference_arm": reference_arm,
                }
                if key not in traces or refkey not in traces:
                    comparisons.append(
                        {**identity, "status": "unavailable", "reason": "A scheduled case failed"}
                    )
                    continue
                comparison = curve_difference(traces[key], traces[refkey])
                comparisons.append({**identity, "status": "available", **comparison})
                input_equal = all(
                    close(row[name], ref[name], criteria["input_amount_relative_tolerance"])
                    for row, ref in zip(traces[key], traces[refkey], strict=True)
                    for name in (
                        "delivered_u_h",
                        "intake_g_min",
                        "cumulative_delivered_mU",
                        "cumulative_carbohydrates_g",
                    )
                )
                checks[f"inputs:{scenario}:{resolution}:{arm}:{reference_arm}"] = input_equal
        for arm in arms:
            key, refkey = (scenario, arm, "refined"), (scenario, arm, "standard")
            identity = {"scenario": scenario, "arm": arm}
            if key not in traces or refkey not in traces:
                refinements.append(
                    {**identity, "status": "unavailable", "reason": "A scheduled case failed"}
                )
                continue
            difference = curve_difference(traces[key], traces[refkey])
            passed = (
                difference["max_abs_glucose_difference_mg_dl"]
                <= criteria["max_glucose_refinement_mg_dl"]
                and difference["max_abs_insulin_difference_mU_per_L"]
                <= criteria["max_insulin_refinement_mU_per_L"]
            )
            checks[f"refinement:{scenario}:{arm}"] = passed
            refinements.append({**identity, "status": "available", **difference, "passed": passed})
        for reference_arm, arm in combinations(arms, 2):
            identity = {"scenario": scenario, "arm": arm, "reference_arm": reference_arm}
            needed = [(scenario, a, r) for r in resolutions for a in (arm, reference_arm)]
            if any(key not in traces for key in needed):
                contrast_refinements.append(
                    {**identity, "status": "unavailable", "reason": "A scheduled case failed"}
                )
                continue
            curves = {
                resolution: contrast(
                    traces[(scenario, arm, resolution)],
                    traces[(scenario, reference_arm, resolution)],
                )
                for resolution in resolutions
            }
            difference = curve_difference(curves["refined"], curves["standard"])
            passed = (
                difference["max_abs_glucose_difference_mg_dl"]
                <= criteria["max_glucose_contrast_refinement_mg_dl"]
                and difference["max_abs_insulin_difference_mU_per_L"]
                <= criteria["max_insulin_contrast_refinement_mU_per_L"]
            )
            checks[f"contrast_refinement:{scenario}:{arm}:{reference_arm}"] = passed
            contrast_refinements.append(
                {**identity, "status": "available", **difference, "passed": passed}
            )
    return {
        "schema": "lit002-report/1",
        "claim": CLAIM,
        "planned_cases": len(expected),
        "completed_cases": len(metrics),
        "failed_cases": len(failures),
        "failures": failures,
        "preparation_error": manifest.get("preparation_error"),
        "checks": checks,
        "all_passed": all(checks.values()),
        "criteria": criteria,
        "case_metrics": metrics,
        "comparisons": comparisons,
        "refinements": refinements,
        "contrast_refinements": contrast_refinements,
        "limitations": [
            "Extrema and difference times are sampled on the archived output grid; "
            "ties use the first sample.",
            "Finite-horizon cumulative absorption includes basal input and is balance-derived, "
            "not an independent mass measurement.",
            "Parameter matching equates analytical mean appearance time; "
            "no data fitting or outcome ranking occurs.",
            "Failed scheduled cases remain in coverage and make affected comparisons unavailable.",
            "Artifact hashes check consistency with the local manifest, "
            "not independent scientific authenticity.",
        ],
    }


def markdown(report: dict) -> str:
    lines = [
        "# LIT-002 reconstructed engineering report",
        "",
        report["claim"],
        "",
        f"Completed {report['completed_cases']} of {report['planned_cases']} scheduled cases; "
        f"failed {report['failed_cases']}. "
        f"All checks passed: {str(report['all_passed']).lower()}.",
        "",
        "## Sampled between-arm differences",
        "",
        "Signed differences use the first-listed arm minus its reference; "
        "no model ranking is implied.",
        "",
        "| Scenario | Resolution | Arm | Reference | "
        "Max absolute glucose difference (mg/dL) | Max absolute insulin difference (mU/L) |",
        "| --- | --- | --- | --- | --- | --- |",
    ]
    for item in report["comparisons"]:
        glucose = (
            f"{item['max_abs_glucose_difference_mg_dl']:.6g}"
            if item["status"] == "available"
            else "unavailable"
        )
        insulin = (
            f"{item['max_abs_insulin_difference_mU_per_L']:.6g}"
            if item["status"] == "available"
            else "unavailable"
        )
        lines.append(
            f"| {item['scenario']} | {item['resolution']} | {item['arm']} | "
            f"{item['reference_arm']} | {glucose} | {insulin} |"
        )
    lines.extend(["", "## Verification", ""])
    failed_checks = [name for name, passed in report["checks"].items() if not passed]
    lines.append(
        "All recorded engineering checks passed."
        if not failed_checks
        else "Failed checks: " + ", ".join(failed_checks) + "."
    )
    lines.extend(
        [
            "",
            "Individual curve refinement and refinement of each between-arm contrast are "
            "assessed separately against the frozen numerical criteria. "
            "Full values are retained in report.json.",
            "",
            "## Failed scheduled cases",
            "",
        ]
    )
    lines.extend(
        [
            f"- {item['case_id']}: {str(item['error']).replace(chr(10), ' ')}"
            for item in report["failures"]
        ]
        or ["None."]
    )
    lines.extend(
        ["", "## Interpretation limits", ""] + ["- " + item for item in report["limitations"]]
    )
    return "\n".join(lines) + "\n"


def write_report(study: Path, output: Path) -> dict:
    report = reconstruct(study)
    output = Path(output)
    output.mkdir(parents=True, exist_ok=False)
    (output / "report.json").write_text(
        json.dumps(report, indent=2, sort_keys=True, allow_nan=False) + "\n"
    )
    (output / "report.md").write_text(markdown(report))
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("study", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    report = write_report(args.study, args.output)
    print(
        json.dumps(
            {
                "all_passed": report["all_passed"],
                "completed_cases": report["completed_cases"],
                "failed_cases": report["failed_cases"],
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
