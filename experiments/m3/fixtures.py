"""Self-authored synthetic data, not a sample of any patient release."""

import math
from pathlib import Path

from .common import SCHEMA, digest, save


def generate(output):
    output = Path(output)
    output.mkdir(parents=True, exist_ok=False)
    people = []
    for index in range(6):
        person = {"id": f"synthetic-{index + 1}", "source_person": f"invented-person-{index + 1}"}
        for role, start, end in (("train", 0, 2880), ("evaluation", 3000, 4440)):
            rows = []
            for t in range(start, end, 5):
                if (t - start) in (200, 205, 210):
                    continue
                value = 120 + 30 * math.sin(t / 180 + index) + index * 4
                status, bound = "measured", None
                if t - start == 350:
                    status, value = "missing", None
                if t - start == 400:
                    status, value = "invalid", None
                if t - start in (600, 605):
                    status, value, bound = "censored_high", None, 400
                if t - start == 700:
                    status, value, bound = "censored_low", None, 40
                time = t + 0.5 if t - start == 900 else t
                rows.append(
                    {
                        "time": time,
                        "available": time + (10 if t - start == 1000 else 0),
                        "segment": "after-clock-shift" if t - start >= 1100 else "initial",
                        "raw_time": f"synthetic-minute-{time}",
                        "status": status,
                        "value": value,
                        "bound": bound,
                    }
                )
            name = f"{person['id']}-{role}.json"
            save(
                output / name,
                {
                    "schema": SCHEMA,
                    "person": person["id"],
                    "clock": "elapsed_synthetic",
                    "unit": "mg/dL",
                    "rows": rows,
                },
            )
            person[role] = {
                "file": name,
                "sha256": digest((output / name).read_bytes()),
                "start": start,
                "end": end,
            }
        people.append(person)
    value = {
        "schema": SCHEMA,
        "kind": "synthetic",
        "source": "self-authored",
        "release": "m3-fixtures/1",
        "rights": {"synthetic": True},
        "clock": "elapsed_synthetic",
        "people": people,
    }
    save(output / "registry.json", value)
    save(
        output / "supplemental-signals.json",
        {
            "purpose": "synthetic semantics fixture; not predictors",
            "meals": {"coverage": "unknown", "events": []},
            "recorded_delivery": {"coverage": "unknown", "events": []},
            "basal_commands": [
                {
                    "start": 0,
                    "end": 2,
                    "kind": "basal_command_u_h",
                    "status": "measured",
                    "value": 0.6,
                },
                {
                    "start": 2,
                    "end": 5,
                    "kind": "basal_command_u_h",
                    "status": "measured",
                    "value": 1.2,
                },
                {
                    "start": 5,
                    "end": 12,
                    "kind": "basal_command_u_h",
                    "status": "missing",
                    "value": None,
                },
            ],
        },
    )
    return value
