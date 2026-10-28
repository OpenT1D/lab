"""Verify public CIT-07 variable dictionaries without reading participant data."""

import argparse
import hashlib
import json
import re
import xml.etree.ElementTree as ET
from pathlib import Path
from zipfile import ZipFile

HERE = Path(__file__).resolve().parent
MANIFEST = HERE / "public-dictionaries.json"
NS = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def dictionary_rows(path):
    """Read only the first sheet's text cells from a source-pinned XLSX."""
    with ZipFile(path) as workbook:
        names = set(workbook.namelist())
        if "xl/worksheets/sheet1.xml" not in names:
            raise ValueError(f"Missing first worksheet: {path.name}")
        shared = []
        if "xl/sharedStrings.xml" in names:
            root = ET.fromstring(workbook.read("xl/sharedStrings.xml"))
            shared = ["".join(t.text or "" for t in item.iter(f"{NS}t")) for item in root]
        root = ET.fromstring(workbook.read("xl/worksheets/sheet1.xml"))
        rows = []
        for row in root.iter(f"{NS}row"):
            values = {}
            for cell in row.iter(f"{NS}c"):
                match = re.fullmatch(r"([A-Z]+)[1-9][0-9]*", cell.get("r", ""))
                if not match:
                    raise ValueError("Malformed dictionary cell coordinate")
                value = cell.find(f"{NS}v")
                if cell.get("t") == "s" and value is not None:
                    text = shared[int(value.text)]
                elif cell.get("t") == "inlineStr":
                    text = "".join(t.text or "" for t in cell.iter(f"{NS}t"))
                else:
                    text = value.text if value is not None else ""
                values[match.group(1)] = text or ""
            rows.append(values)
        return rows


def fields(path):
    rows = dictionary_rows(path)
    if not rows or rows[0].get("B") != "Variable Name":
        raise ValueError(f"Unexpected dictionary heading: {path.name}")
    names = {}
    tables = set()
    for row in rows[1:]:
        table, name, label = (row.get(key, "") for key in ("A", "B", "C"))
        if not name:
            continue
        tables.add(table)
        if name in names and names[name] != label:
            raise ValueError(f"Conflicting description for {name} in {path.name}")
        names[name] = label
    return tables, names


def interpret(inventories):
    fsigt = inventories["fsigt.xlsx"]
    cpep = inventories["cpeptide.xlsx"]
    rudbeck = inventories["rudbeck.xlsx"]
    insulin_use = inventories["insulin_use.xlsx"]
    mean_insulin = inventories["mean_insulin.xlsx"]
    return {
        "shared_subject_key_documented": all(
            "ACCESSION" in names for names in (fsigt, cpep, rudbeck)
        ),
        "shared_transplant_day_field_documented": all(
            "NumDaysInitial" in names for names in (fsigt, cpep, rudbeck)
        ),
        "fsigt_dynamic_glucose_insulin_columns": all(
            key in fsigt for key in ("Time ", "glu", "ins_tosoh")
        ),
        "fsigt_raw_has_cpeptide_column": any("pept" in key.lower() for key in fsigt),
        "aggregate_cpeptide_baseline_60_90_without_sample_clock": all(
            key in cpep
            for key in (
                "Fasting_cpeptide",
                "Stimulated_cpeptide_60",
                "Stimulated_cpeptide_90",
            )
        )
        and "Time " not in cpep,
        "rudbeck_has_sample_label_but_no_glucose_insulin": "Sample" in rudbeck
        and "C_Peptid" in rudbeck
        and not any(key in rudbeck for key in ("glu", "ins_tosoh")),
        "insulin_use_is_daily_not_test_input": insulin_use.get("Insulin")
        == "Insulin Use (Units/Day)"
        and "Mean Insulin (units/day)" in mean_insulin.get("Mean_Insulin", ""),
        "verified_same_challenge_gic_crosswalk": False,
        "human_execution_authorized": False,
    }


def assess(source_dir):
    source_dir = Path(source_dir)
    if source_dir.is_symlink():
        raise ValueError("Source directory cannot be a symlink")
    manifest = json.loads(MANIFEST.read_text())
    if manifest.get("schema") != "bc015-public-dictionaries/1":
        raise ValueError("Unexpected public dictionary manifest")
    inventories = {}
    observed_hashes = {}
    for filename, specification in manifest["files"].items():
        path = source_dir / filename
        if path.is_symlink() or not path.is_file() or path.stat().st_size > 1_000_000:
            raise ValueError(f"Missing, linked or oversized public dictionary: {filename}")
        observed = sha256(path)
        if observed != specification["sha256"]:
            raise ValueError(f"Unexpected source bytes: {filename}")
        tables, names = fields(path)
        if tables != {specification["table"]} or not set(
            specification["required_variables"]
        ).issubset(names):
            raise ValueError(f"Unexpected dictionary fields: {filename}")
        observed_hashes[filename] = observed
        inventories[filename] = names
    return {
        "schema": "bc015-public-crosswalk-report/1",
        "protocol": manifest["id"],
        "release": manifest["release"],
        "manifest_sha256": sha256(MANIFEST),
        "source_sha256": observed_hashes,
        "variables": {name: sorted(fields) for name, fields in inventories.items()},
        "key_labels": {
            "fsigt_glucose": inventories["fsigt.xlsx"]["glu"],
            "fsigt_insulin": inventories["fsigt.xlsx"]["ins_tosoh"],
            "cpeptide_creatinine": inventories["cpeptide.xlsx"]["Creatinine"],
            "cpeptide_90": inventories["cpeptide.xlsx"]["Stimulated_cpeptide_90"],
            "rudbeck_cpeptide": inventories["rudbeck.xlsx"]["C_Peptid"],
        },
        "findings": interpret(inventories),
        "claim": "public_dictionary_field_compatibility_only",
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-dir", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    report = assess(args.source_dir)
    if args.output.exists():
        raise ValueError("Choose a new output path")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    print(json.dumps(report["findings"], sort_keys=True))
