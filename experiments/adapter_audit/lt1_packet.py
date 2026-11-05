"""Trusted reader for invented LT1 ledger fixtures; never accepts native evidence."""

import argparse
import hashlib
import json
import re
from pathlib import Path

from experiments.m1.artifacts import strict_json
from experiments.m3.researcher.intake import read_regular

from .check import HERE, check_case, fields, require

SCHEMA = "opent1d.ot062-lt1-fixture-ledger/1"
SLOTS = ("control", "failure-retry", "unattempted")


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def inspect(path):
    """Check internal fixture lineage, not historical authenticity; import no archived code."""
    raw = read_regular(path, 1024 * 1024, "LT1 fixture ledger")
    packet = strict_json(raw)
    fields(packet, "schema kind fixture_sha256 slots attempts", "packet-fields")
    require(packet["schema"] == SCHEMA and packet["kind"] == "invented", "fixture-only")
    fixture_raw = read_regular(HERE / "cases.json", 1024 * 1024, "trusted audit fixture")
    require(packet["fixture_sha256"] == sha(fixture_raw), "fixture-identity")
    control = strict_json(fixture_raw)["lt1_cambridge"]
    pins = strict_json(read_regular(HERE / "pins.json", 4096, "trusted audit pins"))
    require(packet["slots"] == list(SLOTS), "planned-support")
    require(isinstance(packet["attempts"], list), "attempts")
    seen, previous, first, outcomes = set(), {}, {}, {}
    for attempt in packet["attempts"]:
        fields(attempt, "id slot ordinal retry_of transcript", "attempt-fields")
        identifier, slot = attempt["id"], attempt["slot"]
        require(
            isinstance(identifier, str)
            and re.fullmatch(r"[a-z][a-z0-9-]{0,63}", identifier) is not None
            and identifier not in seen,
            "attempt-id",
        )
        require(isinstance(slot, str) and slot in SLOTS, "slot")
        prior = previous.get(slot)
        require(
            type(attempt["ordinal"]) is int
            and attempt["ordinal"] == (prior["ordinal"] + 1 if prior else 1)
            and attempt["retry_of"] == (prior["id"] if prior else None)
            and (not prior or prior["transcript"]["status"] != "started"),
            "retry-lineage",
        )
        transcript = attempt["transcript"]
        require(isinstance(transcript, dict), "transcript")
        require(transcript.get("input") == control["input"], "fixture-input")
        result = check_case(transcript, pins)
        seen.add(identifier)
        previous[slot] = attempt
        first.setdefault(slot, transcript["status"])
        outcomes[identifier] = result
    return {
        "kind": "invented; no native acceptance",
        "packet_bytes_sha256": sha(raw),
        "fixture_bytes_sha256": sha(fixture_raw),
        "planned_slots": len(SLOTS),
        "unattempted": [slot for slot in SLOTS if slot not in first],
        "first_attempt_status": first,
        "attempts": outcomes,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("packet", type=Path)
    args = parser.parse_args()
    print(json.dumps(inspect(args.packet), sort_keys=True))


if __name__ == "__main__":
    main()
