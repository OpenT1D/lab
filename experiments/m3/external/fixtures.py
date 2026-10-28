"""Self-authored external observations; no provider or human-format claims."""

import datetime as dt
import math
from pathlib import Path

from experiments.m3.azt1d.common import MINUTE
from experiments.m3.azt1d.common import SCHEMA as OBSERVATION_SCHEMA
from experiments.m3.azt1d.study import private_directory
from experiments.m3.common import digest, require, save

from .common import FORMAT, SCHEMA


def generate(output, *, people=2, days=3, gaps=False):
    """Create a separate synthetic cohort already in the normalized contract.

    The optional defects exercise missing measured values, missing registered
    timestamps, and delayed availability without changing the exact-time rules.
    This is deliberately not an importer for any named external dataset.
    """
    require(type(people) is int and people > 0, "Positive synthetic participant count required")
    require(type(days) is int and days > 0, "Positive synthetic duration required")
    require(type(gaps) is bool, "Synthetic coverage choice must be explicit")
    output = Path(output).resolve()
    with private_directory(output):
        registry = {
            "schema": SCHEMA,
            "kind": "synthetic",
            "source": {
                "id": "invented-external-cohort",
                "reference": "Self-authored normalized fixtures; no human or provider records",
                "format": FORMAT,
            },
            "ledger": str(output / "evaluation-access.jsonl"),
            "prior_access": {
                "reviewed": True,
                "status": "present",
                "reference": "Self-authored generation and prior conversion into normalized inputs",
            },
            "people": [],
        }
        count = days * 288
        bounds = [0, count * 5 * MINUTE]
        for person in range(people):
            pid = f"external-invented-{person + 1}"
            origin = dt.datetime(2021, 1, 1) + dt.timedelta(days=person)
            rows = []
            for index in range(count):
                if gaps and index % 173 == 59:
                    continue
                time = index * 5 * MINUTE
                status = "missing" if gaps and index % 137 == 23 else "measured"
                value = 120 + 25 * math.sin(index / 31 + person) + person * 7
                rows.append(
                    {
                        "time_us": time,
                        "available_us": time + (MINUTE if gaps and index % 191 == 67 else 0),
                        "segment": "invented-clock-segment",
                        "raw_time": (origin + dt.timedelta(minutes=5 * index)).isoformat(sep=" "),
                        "status": status,
                        "value": value if status == "measured" else None,
                        "bound": None,
                        "source_rows": [index + 1],
                    }
                )
            path = output / f"{pid}.json"
            save(
                path,
                {
                    "schema": OBSERVATION_SCHEMA,
                    "person": pid,
                    "clock": "local_elapsed",
                    "unit": "mg/dL",
                    "bounds_us": bounds,
                    "rows": rows,
                },
            )
            registry["people"].append(
                {
                    "id": pid,
                    "input": {"file": str(path), "sha256": digest(path.read_bytes())},
                    "bounds_us": bounds,
                    "origins_us": [row["time_us"] for row in rows],
                }
            )
        save(output / "registry.json", registry)
    return registry
