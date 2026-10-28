"""Fixed, invented OT-027 prognostic comparison; no human-data input route."""

import argparse
import hashlib
import json
import math
import shutil
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
ARCHIVE_FILES = {"fixture.json", "report.json", "source-run.py"}


def fixture():
    """Create a bounded toy cohort; values and associations are invented."""
    people = []
    for number in range(1, 33):
        alias = f"SYN{number:03d}"
        day = 75 + number % 5 - 2
        prior = 18.0 + (number * 7) % 15
        glycemia = 105.0 + (number * 11) % 37
        fasting_glucose = 105.0 + (number * 3) % 25
        stimulated_glucose = fasting_glucose + 25.0 + number % 9
        fasting_c = 0.2 + (number % 4) * 0.04
        stimulated_c = fasting_c + 0.55 + (number * 7 % 13) * 0.07
        function_index = stimulated_c / (stimulated_glucose / 100.0)
        insulin_mean = max(
            1.0,
            6.0
            + 0.45 * prior
            + 0.035 * (glycemia - 120.0)
            - 5.0 * function_index
            + (number % 4 - 1.5) * 0.4,
        )
        infusion_days = [0, 150] if number % 6 == 0 else [0]
        collection_state = {
            5: "protocol_not_collected_confirmed_graft_failure",
            10: "unavailable",
            15: "below_assay_limit",
        }.get(number, "observed")
        mmtt = {
            "visit": "V10",
            "day": day,
            "challenge": "MMTT",
            "collection_state": collection_state,
            "fasting_c_peptide": fasting_c if collection_state == "observed" else None,
            "stimulated_c_peptide_90": stimulated_c if collection_state == "observed" else None,
            "fasting_glucose": fasting_glucose if collection_state == "observed" else None,
            "stimulated_glucose_90": stimulated_glucose if collection_state == "observed" else None,
        }
        diary = [
            {"day": d, "reported_insulin_units": round(insulin_mean + (d % 3 - 1) * 0.3, 3)}
            for d in range(359, 366)
        ]
        if number == 25:
            diary.pop(2)
        outcomes = [] if number == 20 else [{"visit": "Y1", "day": 365, "diary": diary}]
        if number % 6 == 0 or number == 20:
            # Visit 15 follows its transplant clock and cannot replace first-infusion Y1.
            visit15_day = 365 + infusion_days[-1]
            visit15_diary = [
                {"day": d, "reported_insulin_units": round(insulin_mean, 3)}
                for d in range(visit15_day - 6, visit15_day + 1)
            ]
            outcomes.append({"visit": "V15", "day": visit15_day, "diary": visit15_diary})
        people.append(
            {
                "alias": alias,
                "infusion_days": infusion_days,
                "prior_insulin": {"day": 60, "units_per_day": prior},
                "glycemic_status": {"day": 70, "mg_dl": glycemia},
                "mmtt": mmtt,
                "outcomes": outcomes,
            }
        )
    return {"schema": "ot027-invented-prognosis-fixture/1", "people": people}


def features(person):
    """Return a row and reasons; retain all exclusions in the report."""
    issues = []
    mmtt = person["mmtt"]
    day = mmtt["day"]
    if person["infusion_days"].count(0) != 1 or person["infusion_days"] != sorted(
        set(person["infusion_days"])
    ):
        issues.append("invalid_first_infusion_clock")
    if mmtt["visit"] != "V10" or mmtt["challenge"] != "MMTT" or not 70 <= day <= 80:
        issues.append("invalid_day75_landmark")
    if mmtt["collection_state"] != "observed":
        issues.append(mmtt["collection_state"])
    values = [
        mmtt[name]
        for name in (
            "fasting_c_peptide",
            "stimulated_c_peptide_90",
            "fasting_glucose",
            "stimulated_glucose_90",
        )
    ]
    if any(value is None or not math.isfinite(value) or value <= 0 for value in values):
        issues.append("paired_function_values_unavailable")
    if person["prior_insulin"]["day"] > day or person["glycemic_status"]["day"] > day:
        issues.append("baseline_after_landmark")
    if any(
        not math.isfinite(value) or value < 0
        for value in (
            person["prior_insulin"]["units_per_day"],
            person["glycemic_status"]["mg_dl"],
        )
    ):
        issues.append("baseline_unavailable")
    y1 = [outcome for outcome in person["outcomes"] if outcome["visit"] == "Y1"]
    if len(y1) != 1 or not 351 <= y1[0]["day"] <= 379:
        issues.append("missing_or_ambiguous_first_infusion_y1")
    else:
        days = [item["day"] for item in y1[0]["diary"]]
        if Counter(days) != Counter(range(359, 366)) or max(days, default=0) > y1[0]["day"]:
            issues.append("seven_day_diary_unverified")
        if any(
            not math.isfinite(item["reported_insulin_units"]) or item["reported_insulin_units"] < 0
            for item in y1[0]["diary"]
        ):
            issues.append("diary_value_unavailable")
    if issues:
        return None, sorted(set(issues))
    baseline = [
        person["prior_insulin"]["units_per_day"],
        person["glycemic_status"]["mg_dl"],
        day,
    ]
    function_index = mmtt["stimulated_c_peptide_90"] / (mmtt["stimulated_glucose_90"] / 100.0)
    outcome = sum(item["reported_insulin_units"] for item in y1[0]["diary"]) / 7
    return {"baseline": baseline, "function_index": function_index, "outcome": outcome}, []


def solve(matrix, vector):
    """Small Gaussian solve with partial pivoting for the fixed ridge problem."""
    a = [row[:] + [value] for row, value in zip(matrix, vector, strict=True)]
    size = len(a)
    for column in range(size):
        pivot = max(range(column, size), key=lambda index: abs(a[index][column]))
        if abs(a[pivot][column]) < 1e-12:
            raise ValueError("Singular synthetic fit")
        a[column], a[pivot] = a[pivot], a[column]
        scale = a[column][column]
        a[column] = [value / scale for value in a[column]]
        for row in range(size):
            if row != column:
                factor = a[row][column]
                a[row] = [
                    value - factor * origin for value, origin in zip(a[row], a[column], strict=True)
                ]
    return [row[-1] for row in a]


def fit(rows, *, include_function):
    """Fit toy ridge coefficients and scaling on development rows only."""
    x = [row["baseline"] + ([row["function_index"]] if include_function else []) for row in rows]
    y = [row["outcome"] for row in rows]
    count = len(rows)
    if count < 8:
        raise ValueError("Insufficient synthetic development rows")
    means = [sum(column) / count for column in zip(*x, strict=True)]
    scales = [
        max(1e-12, (sum((value - mean) ** 2 for value in column) / count) ** 0.5)
        for column, mean in zip(zip(*x, strict=True), means, strict=True)
    ]
    z = [
        [1.0]
        + [(value - mean) / scale for value, mean, scale in zip(row, means, scales, strict=True)]
        for row in x
    ]
    size = len(z[0])
    gram = [
        [sum(row[i] * row[j] for row in z) + (1.0 if i == j and i else 0.0) for j in range(size)]
        for i in range(size)
    ]
    rhs = [sum(row[i] * target for row, target in zip(z, y, strict=True)) for i in range(size)]
    return {"means": means, "scales": scales, "coefficients": solve(gram, rhs)}


def predict(model, row, *, include_function):
    values = row["baseline"] + ([row["function_index"]] if include_function else [])
    standardized = [
        (value - mean) / scale
        for value, mean, scale in zip(values, model["means"], model["scales"], strict=True)
    ]
    return model["coefficients"][0] + sum(
        coefficient * value
        for coefficient, value in zip(model["coefficients"][1:], standardized, strict=True)
    )


def assess(packet):
    if packet != fixture():
        raise ValueError("Only the fixed invented fixture can be assessed")
    people = []
    development, evaluation = [], []
    for person in packet["people"]:
        row, issues = features(person)
        alias = person["alias"]
        split = "evaluation" if int(alias[-3:]) % 4 == 0 else "development"
        infusions = [
            day for day in person["infusion_days"][1:] if person["mmtt"]["day"] < day < 365
        ]
        people.append(
            {
                "alias": alias,
                "split": split,
                "paired_comparison_eligible": row is not None,
                "issues": issues,
                "intervening_infusion_days": infusions,
                "y1_present": any(item["visit"] == "Y1" for item in person["outcomes"]),
                "visit15_present": any(item["visit"] == "V15" for item in person["outcomes"]),
            }
        )
        if row is not None:
            (evaluation if split == "evaluation" else development).append((alias, row))
    baseline = fit([row for _, row in development], include_function=False)
    added = fit([row for _, row in development], include_function=True)
    scored = []
    for alias, row in evaluation:
        scored.append(
            {
                "alias": alias,
                "observed_reported_insulin_mean_u_day": row["outcome"],
                "baseline_prediction_u_day": predict(baseline, row, include_function=False),
                "added_prediction_u_day": predict(added, row, include_function=True),
            }
        )
    baseline_mae = sum(
        abs(item["baseline_prediction_u_day"] - item["observed_reported_insulin_mean_u_day"])
        for item in scored
    ) / len(scored)
    added_mae = sum(
        abs(item["added_prediction_u_day"] - item["observed_reported_insulin_mean_u_day"])
        for item in scored
    ) / len(scored)
    return {
        "schema": "ot027-synthetic-prognosis-report/1",
        "claim": "invented_pipeline_check_only",
        "human_execution_authorized": False,
        "treatment_effect_or_cure_estimated": False,
        "roster_count": len(people),
        "development_roster_count": sum(item["split"] == "development" for item in people),
        "evaluation_roster_count": sum(item["split"] == "evaluation" for item in people),
        "development_paired_count": len(development),
        "evaluation_paired_count": len(evaluation),
        "split_rule": "SYN number divisible by four is evaluation; assigned before fitting",
        "function_index": "invented C-peptide at 90 min / (concurrent glucose at 90 min / 100)",
        "model": "development-only standardized ridge, penalty 1 on slopes, intercept unpenalized",
        "baseline_features": [
            "prior_diary_insulin_u_day",
            "prior_glycemic_status_mg_dl",
            "day75_elapsed_days",
        ],
        "added_feature": "day75_observed_function_index",
        "metric": "paired held-out mean absolute error in reported insulin U/day",
        "baseline_mae_u_day": baseline_mae,
        "added_mae_u_day": added_mae,
        "mae_change_added_minus_baseline_u_day": added_mae - baseline_mae,
        "people": people,
        "evaluation_predictions": scored,
    }


def write(path, value):
    Path(path).write_text(json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n")


def digest(path):
    path = Path(path)
    if path.is_symlink() or not path.is_file() or path.stat().st_size > 300_000:
        raise ValueError("Synthetic artifact must be a regular file of at most 300 kB")
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read(path):
    digest(path)
    return json.loads(Path(path).read_text())


def execute(output):
    output = Path(output)
    if output.exists():
        raise ValueError("Choose a new output directory")
    packet = fixture()
    report = assess(packet)
    output.mkdir(parents=True)
    try:
        write(output / "fixture.json", packet)
        write(output / "report.json", report)
        shutil.copyfile(__file__, output / "source-run.py")
        write(
            output / "manifest.json",
            {
                "schema": "ot027-synthetic-prognosis-archive/1",
                "files": {name: digest(output / name) for name in sorted(ARCHIVE_FILES)},
            },
        )
        reconstruct(output)
    except BaseException:
        shutil.rmtree(output)
        raise
    return report


def reconstruct(directory):
    directory = Path(directory)
    if (
        directory.is_symlink()
        or not directory.is_dir()
        or {item.name for item in directory.iterdir()} != ARCHIVE_FILES | {"manifest.json"}
    ):
        raise ValueError("Incomplete synthetic archive")
    manifest = read(directory / "manifest.json")
    if (
        manifest.get("schema") != "ot027-synthetic-prognosis-archive/1"
        or set(manifest.get("files", {})) != ARCHIVE_FILES
    ):
        raise ValueError("Wrong synthetic archive manifest")
    for name, expected in manifest["files"].items():
        if digest(directory / name) != expected:
            raise ValueError(f"Changed synthetic artifact: {name}")
    if digest(directory / "source-run.py") != digest(__file__):
        raise ValueError("Different synthetic prognosis implementation")
    if assess(read(directory / "fixture.json")) != read(directory / "report.json"):
        raise ValueError("Report differs from synthetic reconstruction")
    return read(directory / "report.json")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("run").add_argument("output", type=Path)
    commands.add_parser("reconstruct").add_argument("archive", type=Path)
    args = parser.parse_args()
    result = execute(args.output) if args.command == "run" else reconstruct(args.archive)
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
