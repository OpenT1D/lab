"""Check source-pinned public CIT-07 dictionaries for OT-027 metadata semantics."""

import argparse
import json
from pathlib import Path

from experiments.m4.measurement_readiness.public_crosswalk import fields, sha256

HERE = Path(__file__).resolve().parent
MANIFEST = HERE / "public-dictionaries.json"


def assess(source_dir):
    source_dir = Path(source_dir)
    if source_dir.is_symlink() or not source_dir.is_dir():
        raise ValueError("A regular public-dictionary directory is required")
    manifest = json.loads(MANIFEST.read_text())
    if manifest.get("schema") != "ot027-public-dictionaries/1":
        raise ValueError("Wrong public-dictionary manifest")
    inventories = {}
    source_hashes = {}
    for filename, specification in manifest["files"].items():
        path = source_dir / filename
        if path.is_symlink() or not path.is_file() or path.stat().st_size > 1_000_000:
            raise ValueError(f"Missing, linked or oversized public dictionary: {filename}")
        observed = sha256(path)
        if observed != specification["sha256"]:
            raise ValueError(f"Unexpected public dictionary bytes: {filename}")
        tables, names = fields(path)
        if tables != {specification["table"]} or not set(
            specification["required_variables"]
        ).issubset(names):
            raise ValueError(f"Unexpected public dictionary fields: {filename}")
        inventories[filename] = names
        source_hashes[filename] = observed
    status = inventories["patient_status.xlsx"]
    ieq = inventories["ieq_infused.xlsx"]
    cpep = inventories["cpeptide.xlsx"]
    insulin = inventories["insulin.xlsx"]
    mean = inventories["mean_insulin.xlsx"]
    expected_labels = {
        "status_second_infusion": (
            status,
            "Numdays2ndTX",
            "Number of Days Since 1st Transplant for Patients with at Least 2 transplants",
        ),
        "status_third_infusion": (
            status,
            "Numdays3rdTX",
            "Number of Days Since 1st Transplant for Patients with 3 transplants",
        ),
        "ieq_transplant_order": (ieq, "TX", "Transplant Number"),
        "mmtt_day": (cpep, "NumDaysInitial", "Number of Days From Initial Transplant"),
        "insulin_day": (insulin, "NumDaysInitial", "Number of Days From Initial Transplant"),
        "mean_interval_start": (
            mean,
            "NumDaysInitial",
            "Number of Days From Initial Transplant "
            "(Start of 7 Day Interval used for Mean Insulin Calculation)",
        ),
        "mean_interval_end": (
            mean,
            "EndDay",
            "End of 7 Day Interval used for Mean Insulin Calculation",
        ),
        "mean_amount": (
            mean,
            "Mean_Insulin",
            "Mean Insulin (units/day) over 7 consecutive days "
            "(7 closest days Prior to Transplant for baseline)",
        ),
    }
    for role, (names, variable, label) in expected_labels.items():
        if names[variable] != label:
            raise ValueError(f"Changed source meaning for {role}")
    return {
        "schema": "ot027-public-crosswalk-report/1",
        "source": manifest["study"],
        "catalogue_release": manifest["catalogue_release"],
        "catalogue_url": manifest["catalogue_url"],
        "manifest_sha256": sha256(MANIFEST),
        "source_sha256": source_hashes,
        "field_roles": {
            role: {"variable": variable, "source_label": label}
            for role, (_, variable, label) in expected_labels.items()
        },
        "shared_masked_subject_key_documented": all(
            names.get("ACCESSION") == "Masked Subject ID" for names in inventories.values()
        ),
        "repeat_infusion_relative_days_documented": True,
        "ieq_table_has_transplant_order_but_no_infusion_day": not any(
            "day" in name.lower() or "date" in name.lower() for name in ieq
        ),
        "mean_start_is_visit_day": False,
        "verified_same_visit_join": False,
        "verified_daily_diary_coverage": False,
        "verified_participant_coverage": False,
        "human_execution_authorized": False,
        "claim": "public_dictionary_semantics_only",
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-dir", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    report = assess(args.source_dir)
    if args.output.exists():
        raise ValueError("Choose a new report path")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    print(json.dumps(report, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
