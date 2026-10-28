"""Rehearse CIT-07/08 source-shaped joins with invented CSV rows only."""

import argparse
import csv
import hashlib
import json
import math
import re
from collections import Counter, defaultdict
from pathlib import Path

from experiments.m5.source_crosswalk.run import MANIFEST

HERE = Path(__file__).resolve().parent
TABLES = {
    "patient_status.xlsx": "patient_status.csv",
    "ieq_infused.xlsx": "ieq_infused.csv",
    "cpeptide.xlsx": "cpeptide.csv",
    "insulin.xlsx": "insulin.csv",
    "mean_insulin.xlsx": "mean_insulin.csv",
}
ALIAS = re.compile(r"SYN[0-9]{3}")


def read_intent(path):
    path = Path(path)
    if path.is_symlink() or not path.is_file() or path.stat().st_size > 10_000:
        raise ValueError("A regular small intent file is required")
    intent = json.loads(path.read_text())
    if not isinstance(intent, dict) or intent != {
        "schema": "ot027-native-rehearsal-intent/1",
        "kind": "synthetic",
        "source": "invented",
        "clock": "days_since_first_infusion",
    }:
        raise ValueError("Only invented synthetic CSV rehearsal is enabled")
    return intent


def input_tables(source_dir):
    source_dir = Path(source_dir)
    if source_dir.is_symlink() or not source_dir.is_dir():
        raise ValueError("A regular synthetic source directory is required")
    manifest = json.loads(MANIFEST.read_text())
    tables, hashes = {}, {}
    for dictionary, filename in TABLES.items():
        path = source_dir / filename
        if path.is_symlink() or not path.is_file() or path.stat().st_size > 200_000:
            raise ValueError(f"Missing, linked or oversized synthetic table: {filename}")
        raw = path.read_bytes()
        hashes[filename] = hashlib.sha256(raw).hexdigest()
        text = raw.decode("utf-8-sig")
        reader = csv.DictReader(text.splitlines(), strict=True)
        expected = set(manifest["files"][dictionary]["required_variables"])
        if reader.fieldnames is None or len(reader.fieldnames) != len(set(reader.fieldnames)):
            raise ValueError(f"Missing or duplicate CSV header: {filename}")
        if set(reader.fieldnames) != expected:
            raise ValueError(f"Source-shaped header differs: {filename}")
        records = list(reader)
        if len(records) > 5000 or any(None in row for row in records):
            raise ValueError(f"Invalid CSV record width or size: {filename}")
        for row in records:
            if any(value is None for value in row.values()):
                raise ValueError(f"Missing CSV cell: {filename}")
            if not ALIAS.fullmatch(row["ACCESSION"]):
                raise ValueError("Only invented SYNnnn aliases are accepted")
            if row["StudyID"] != "CIT07-SYNTHETIC":
                raise ValueError("Only invented CIT07 study labels are accepted")
        tables[filename] = records
    return tables, hashes


def integer(value, label, *, missing=False):
    if value == "" and missing:
        return None
    if not re.fullmatch(r"0|[1-9][0-9]*", value):
        raise ValueError(f"Invalid synthetic integer: {label}")
    result = int(value)
    if result > 10000:
        raise ValueError(f"Synthetic integer outside bound: {label}")
    return result


def number(value, label, *, missing=False):
    if value == "" and missing:
        return None
    try:
        result = float(value)
    except ValueError as error:
        raise ValueError(f"Invalid synthetic number: {label}") from error
    if not math.isfinite(result) or result < 0:
        raise ValueError(f"Nonfinite or negative synthetic number: {label}")
    return result


def assess(intent, tables, hashes):
    if intent["kind"] != "synthetic":
        raise ValueError("Human release assessment is disabled")
    roster = tables["patient_status.csv"]
    aliases = [row["ACCESSION"] for row in roster]
    if len(aliases) != len(set(aliases)) or len(aliases) > 100:
        raise ValueError("Duplicate or oversized synthetic roster")
    known = set(aliases)
    for filename, rows in tables.items():
        if any(row["ACCESSION"] not in known for row in rows):
            raise ValueError(f"{filename} references an alias outside the roster")
    by_table = {
        filename: defaultdict(list)
        for filename in TABLES.values()
        if filename != "patient_status.csv"
    }
    for filename, grouped in by_table.items():
        for row in tables[filename]:
            grouped[row["ACCESSION"]].append(row)
    persons = []
    for status in roster:
        alias = status["ACCESSION"]
        issues = []
        n_transplants = integer(status["NumTX"], "NumTX")
        if n_transplants not in (1, 2, 3):
            issues.append("unsupported_transplant_count")
        second = integer(status["Numdays2ndTX"], "Numdays2ndTX", missing=True)
        third = integer(status["Numdays3rdTX"], "Numdays3rdTX", missing=True)
        infusion_days = [0] + [value for value in (second, third) if value is not None]
        if (
            len(infusion_days) != n_transplants
            or infusion_days != sorted(set(infusion_days))
            or (n_transplants < 2 and second is not None)
            or (n_transplants < 3 and third is not None)
        ):
            issues.append("infusion_history_inconsistent")
        ieq_rows = by_table["ieq_infused.csv"][alias]
        ieq_orders = [integer(row["TX"], "TX") for row in ieq_rows]
        for row in ieq_rows:
            number(row["PostTransplantIEQ"], "PostTransplantIEQ")
        if sorted(ieq_orders) != list(range(1, n_transplants + 1)):
            issues.append("ieq_transplant_orders_inconsistent")
        cpep_rows = [
            row
            for row in by_table["cpeptide.csv"][alias]
            if 70 <= integer(row["NumDaysInitial"], "MMTT candidate day") <= 80
        ]
        if len(cpep_rows) != 1:
            issues.append("missing_or_ambiguous_day75_candidate")
        else:
            for name in (
                "Fasting_cpeptide",
                "Stimulated_cpeptide_90",
                "Fasting_glucose",
                "Stimulated_glucose_90",
            ):
                if number(cpep_rows[0][name], name, missing=True) is None:
                    issues.append("incomplete_paired_function_values")
        mean_rows = [
            row
            for row in by_table["mean_insulin.csv"][alias]
            if 351 <= integer(row["EndDay"], "Mean interval end") <= 379
        ]
        if len(mean_rows) != 1:
            issues.append("missing_or_ambiguous_one_year_interval")
            interval = None
        else:
            mean = mean_rows[0]
            start = integer(mean["NumDaysInitial"], "Mean interval start")
            end = integer(mean["EndDay"], "Mean interval end")
            interval = [start, end]
            if end - start != 6:
                issues.append("mean_interval_not_seven_inclusive_days")
            if number(mean["Mean_Insulin"], "Mean_Insulin", missing=True) is None:
                issues.append("mean_insulin_missing")
            weight = number(mean["Weight"], "Weight", missing=True)
            if weight == 0:
                issues.append("zero_weight")
            number(mean["Ins_kg"], "Ins_kg", missing=True)
            daily = by_table["insulin.csv"][alias]
            days = [integer(row["NumDaysInitial"], "Daily insulin day") for row in daily]
            for row in daily:
                number(row["Insulin"], "Daily insulin", missing=True)
            counts = Counter(day for day in days if start <= day <= end)
            if end - start != 6 or counts != Counter(range(start, end + 1)):
                issues.append("daily_insulin_interval_unverified")
            if any(
                number(row["Insulin"], "Daily insulin", missing=True) is None
                for row in daily
                if start <= integer(row["NumDaysInitial"], "Daily insulin day") <= end
            ):
                issues.append("daily_insulin_value_missing")
        persons.append(
            {
                "alias": alias,
                "candidate_structure_complete": not issues,
                "issues": sorted(set(issues)),
                "infusion_days_from_first": infusion_days,
                "candidate_mean_interval": interval,
                "intervening_infusions_before_interval_end": [
                    day
                    for day in infusion_days[1:]
                    if len(cpep_rows) == 1
                    and interval
                    and int(cpep_rows[0]["NumDaysInitial"]) < day < interval[1]
                ],
            }
        )
    return {
        "schema": "ot027-native-rehearsal-report/1",
        "claim": "synthetic_source_shaped_structure_only",
        "dictionary_manifest_sha256": hashlib.sha256(MANIFEST.read_bytes()).hexdigest(),
        "source_sha256": hashes,
        "roster_count": len(persons),
        "candidate_structure_count": sum(row["candidate_structure_complete"] for row in persons),
        "people": persons,
        "mmtt_challenge_identity_verified": False,
        "one_year_visit_linkage_verified": False,
        "cit07_cit08_partition_verified": False,
        "diary_semantics_and_arithmetic_verified": False,
        "human_execution_authorized": False,
        "fit_or_treatment_evaluation_performed": False,
    }


def execute(intent_path, source_dir, output):
    intent = read_intent(intent_path)  # Reject non-synthetic intent before opening CSVs.
    tables, hashes = input_tables(source_dir)
    report = assess(intent, tables, hashes)
    output = Path(output)
    if output.exists():
        raise ValueError("Choose a new output path")
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2, sort_keys=True, allow_nan=False) + "\n")
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--intent", type=Path, required=True)
    parser.add_argument("--source-dir", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(execute(args.intent, args.source_dir, args.output), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
