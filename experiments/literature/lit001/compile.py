"""Reconcile recorded screening decisions without changing historical review passes."""

from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent


def read(name: str) -> dict | list:
    return json.loads((HERE / name).read_text())


def decisions(value: dict | list) -> list[dict]:
    if isinstance(value, list):
        return value
    return value.get("decisions", value.get("records", []))


def compile_screening() -> dict:
    bibliography = {row["key"]: row for row in read("bibliography.json")}
    summary = read("search-summary.json")
    aliases = {row["key"]: row["canonical_key"] for row in summary["aliases"]}
    inputs = ["bibliography.json", "search-summary.json", "screening-audit.json"]
    inputs += [f"{stage}-{shard}.json" for stage in ("screening", "fulltext") for shard in "abc"]
    original, final = {}, {}
    for shard in "abc":
        name = f"screening-{shard}.json"
        for row in decisions(read(name)):
            key = row["key"]
            if key in original:
                raise ValueError(f"Duplicate screening decision: {key}")
            original[key] = row
            if key not in aliases:
                final[key] = {
                    "key": key,
                    "title": bibliography[key]["title"],
                    "decision": row["decision"],
                    "reason": row["reason"],
                    "reviewed_material": row["reviewed_material"],
                    "decision_record": name,
                }
    if set(original) != set(bibliography) | set(aliases):
        raise ValueError("Screening and bibliography coverage differ")
    for key, canonical in aliases.items():
        if original[key]["decision"] != original[canonical]["decision"]:
            raise ValueError(f"Conflicting identity alias: {key}")
    expected = {
        key for key, row in final.items() if row["decision"] in {"primary_candidate", "unresolved"}
    }
    followed = set()
    for shard in "abc":
        name = f"fulltext-{shard}.json"
        for row in decisions(read(name)):
            key = row["key"]
            if key not in expected or key in followed:
                raise ValueError(f"Unexpected or duplicate follow-up: {key}")
            followed.add(key)
            final[key].update(
                decision=row.get("decision", row.get("status")),
                reason=row.get("reason", row.get("reference_feasibility")),
                reviewed_material=row["reviewed_material"],
                decision_record=name,
            )
    if expected != followed:
        raise ValueError(f"Missing follow-up: {sorted(expected - followed)}")
    for row in read("screening-audit.json")["overrides"]:
        key = row["key"]
        if original[key]["decision"] != "excluded":
            raise ValueError("Audit override no longer matches first pass")
        final[key].update(
            decision=row["recommended_decision"],
            reason=row["basis"],
            reviewed_material="title_abstract_separate_audit",
            decision_record="screening-audit.json",
        )
    allowed = {"primary", "background", "excluded", "unresolved"}
    if any(row["decision"] not in allowed for row in final.values()):
        raise ValueError("Unresolved workflow status, not an evidence decision")
    return {
        "schema": "lit001-reconciled-screening/1",
        "publication_records": len(final),
        "first_pass_accession_keys": len(original),
        "candidate_followups": len(followed),
        "exclusion_audit_overrides": len(read("screening-audit.json")["overrides"]),
        "counts": dict(Counter(row["decision"] for row in final.values())),
        "interpretation": (
            "Primary is a retained evidence record, not a count of independent studies, "
            "full journal articles, verified U100 cohorts or clinically validated models. "
            "Follow-up records preserve formulation, access and overlap restrictions. "
            "This reconciliation covers the main search; tracing has separate records."
        ),
        "input_sha256": {
            name: hashlib.sha256((HERE / name).read_bytes()).hexdigest() for name in inputs
        },
        "decisions": list(final.values()),
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = compile_screening()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("x") as stream:
        stream.write(json.dumps(result, indent=2, ensure_ascii=False) + "\n")
    print(json.dumps({key: result[key] for key in ("publication_records", "counts")}))
