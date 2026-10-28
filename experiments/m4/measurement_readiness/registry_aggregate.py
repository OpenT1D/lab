"""Audit a pinned public trial-registry aggregate, never participant data."""

import argparse
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
PROTOCOL = HERE / "registry-aggregate-protocol.json"


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def assess_record(record, protocol):
    """Check published result structure without treating group cells as trajectories."""
    if (
        record.get("protocolSection", {}).get("identificationModule", {}).get("nctId")
        != protocol["source"]["nct_id"]
    ):
        raise ValueError("Unexpected NCT identifier")
    outcomes = (
        record.get("resultsSection", {}).get("outcomeMeasuresModule", {}).get("outcomeMeasures", [])
    )
    expected_labels = {
        f"{sample} - {visit}"
        for visit in protocol["expected_visit_labels"]
        for sample in protocol["expected_sample_labels"]
    }
    observations = {}
    for signal, title in protocol["required_outcome_title_prefixes"].items():
        matches = [outcome for outcome in outcomes if outcome.get("title") == title]
        if len(matches) != 1:
            raise ValueError(f"Expected exactly one published {signal} outcome")
        outcome = matches[0]
        if outcome.get("unitOfMeasure") != protocol["expected_units"][signal]:
            raise ValueError(f"Unexpected {signal} unit")
        groups = {group["id"]: group["title"] for group in outcome.get("groups", [])}
        if len(groups) != 2:
            raise ValueError(f"Unexpected {signal} treatment groups")
        labels = {}
        for row in outcome.get("classes", []):
            label = row.get("title")
            if not isinstance(label, str) or label in labels:
                raise ValueError(f"Missing or duplicate {signal} result label")
            denoms = row.get("denoms", [])
            categories = row.get("categories", [])
            if len(denoms) != 1 or denoms[0].get("units") != "Participants" or len(categories) != 1:
                raise ValueError(f"Unexpected {signal} result structure")
            counts = {item["groupId"]: int(item["value"]) for item in denoms[0].get("counts", [])}
            values = {item["groupId"]: item for item in categories[0].get("measurements", [])}
            if (
                set(counts) != set(groups)
                or set(values) != set(groups)
                or any(n < 0 for n in counts.values())
            ):
                raise ValueError(f"Incomplete {signal} group summary")
            labels[label] = counts
        observations[signal] = {
            "unit": outcome["unitOfMeasure"],
            "dispersion": outcome.get("dispersionType"),
            "groups": groups,
            "row_count": len(labels),
            "missing_expected_labels": sorted(expected_labels - set(labels)),
            "unexpected_labels": sorted(set(labels) - expected_labels),
            "counts": labels,
        }
    group_maps = [value["groups"] for value in observations.values()]
    if any(groups != group_maps[0] for groups in group_maps[1:]):
        raise ValueError("Published treatment-group identities differ by signal")
    common = set.intersection(*(set(value["counts"]) for value in observations.values()))
    count_disagreements = []
    for label in sorted(common):
        for group in observations["glucose"]["groups"]:
            sample_counts = {
                signal: value["counts"][label][group] for signal, value in observations.items()
            }
            if len(set(sample_counts.values())) > 1:
                count_disagreements.append(
                    {"label": label, "group": group, "counts": sample_counts}
                )
    return {
        "published_group_summaries": observations,
        "common_labels": len(common),
        "common_expected_labels": len(common & expected_labels),
        "group_count_disagreements": count_disagreements,
        "finding": "aggregate_mixed_meal_only_not_participant_linked_ivgtt",
        "human_execution_authorized": False,
    }


def assess(path):
    path = Path(path)
    if path.is_symlink() or not path.is_file() or path.stat().st_size > 2_000_000:
        raise ValueError("Missing, linked or oversized registry snapshot")
    protocol = json.loads(PROTOCOL.read_text())
    if protocol.get("schema") != "bc015-registry-aggregate-protocol/1":
        raise ValueError("Unexpected registry audit protocol")
    source_hash = sha256(path)
    if source_hash != protocol["source"]["snapshot_sha256"]:
        raise ValueError("Registry snapshot differs from frozen public source")
    result = assess_record(json.loads(path.read_text()), protocol)
    return {
        "schema": "bc015-registry-aggregate-report/1",
        "source": protocol["source"]["url"],
        "source_sha256": source_hash,
        "protocol_sha256": sha256(PROTOCOL),
        "nct_id": protocol["source"]["nct_id"],
        **result,
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-json", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise ValueError("Choose a new output path")
    report = assess(args.source_json)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    print(
        json.dumps(
            {
                "finding": report["finding"],
                "common_labels": report["common_labels"],
                "count_disagreements": len(report["group_count_disagreements"]),
            },
            sort_keys=True,
        )
    )
