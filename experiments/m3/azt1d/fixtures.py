"""Invented native CSV example; no human source statistics or records."""

import csv
import datetime as dt
import io
from pathlib import Path

from .common import MINUTE, PHASES, SCHEMA, digest, save
from .intake import HEADER


def generate(output):
    output = Path(output)
    output.mkdir(parents=True, exist_ok=False)
    origin = dt.datetime(2020, 1, 1, 0, 0, 7)
    points = []
    for index in range(180):
        time = index * 5 * MINUTE + (1_000_001 if index >= 80 else 0)
        value = str(100 + index % 17)
        if index == 20:
            value = ""
        points.append((time, value))
        if index in (12, 24):
            points.append((time, value if index == 12 else "135"))
    stream = io.StringIO(newline="")
    writer = csv.writer(stream)
    writer.writerow(HEADER)
    for time, value in points:
        stamp = (origin + dt.timedelta(microseconds=time)).isoformat(sep=" ")
        writer.writerow([stamp, "fixture", "", "", "", "", "", "", value])
    raw = stream.getvalue().encode()
    (output / "source.csv").write_bytes(raw)
    end = points[-1][0] + 5 * MINUTE
    bounds = (0, (3 * end + 4) // 5, (4 * end + 4) // 5, end)
    for index, phase in enumerate(PHASES):
        start, stop = bounds[index : index + 2]
        indices = [i for i, (t, _) in enumerate(points, 1) if start <= t < stop]
        save(
            output / f"{phase}-intake.json",
            {
                "schema": SCHEMA,
                "kind": "synthetic",
                "person": "invented-person",
                "phase": phase,
                "source_sha256": digest(raw),
                "origin_local": origin.isoformat(sep=" "),
                "start_us": start,
                "end_us": stop,
                "row_start": indices[0],
                "row_stop": indices[-1] + 1,
                "policy": {
                    "numeric_boundary": "verified_exact",
                    "reference": "Self-authored synthetic point values; not a device convention",
                },
            },
        )


def generate_study(output, *, people=2, days=10, unsupported_last=False):
    """Invent full-length study inputs; only development/validation are converted."""
    import math

    from .service import normalize
    from .study import private_directory, reference

    output = Path(output).resolve()
    with private_directory(output):
        registry = {
            "schema": SCHEMA,
            "kind": "synthetic",
            "ledger": str(output / "evaluation-access.jsonl"),
            "prior_access": {
                "reviewed": True,
                "status": "none",
                "reference": "Self-authored synthetic observations",
            },
            "people": [],
        }
        for person in range(people):
            pid = f"invented-{person + 1}"
            folder = output / pid
            folder.mkdir()
            origin = dt.datetime(2020, 1, 1 + person, 0, 0, 7)
            count = days * 288
            end = count * 5 * MINUTE
            bounds = [0, (3 * end + 4) // 5, (4 * end + 4) // 5, end]
            stream = io.StringIO(newline="")
            writer = csv.writer(stream)
            header = list(HEADER)
            if unsupported_last and person == people - 1:
                header[-1] = "Readings (CGM / BGM)"
            writer.writerow(header)
            for index in range(count):
                value = 130 + 20 * math.sin(index / 29) + person * 3
                stamp = (origin + dt.timedelta(minutes=5 * index)).isoformat(sep=" ")
                writer.writerow([stamp, "fixture", "", "", "", "", "", "", format(value, ".8f")])
            raw = stream.getvalue().encode()
            source = folder / "source.csv"
            source.write_bytes(raw)
            entry = {"id": pid, "source": str(source)}
            for phase_index, phase in enumerate(PHASES):
                start, stop = bounds[phase_index : phase_index + 2]
                first = (start + 5 * MINUTE - 1) // (5 * MINUTE)
                last = (stop + 5 * MINUTE - 1) // (5 * MINUTE)
                request = {
                    "schema": SCHEMA,
                    "kind": "synthetic",
                    "person": pid,
                    "phase": phase,
                    "source_sha256": digest(raw),
                    "origin_local": origin.isoformat(sep=" "),
                    "start_us": start,
                    "end_us": stop,
                    "row_start": first + 1,
                    "row_stop": last + 1,
                    "policy": {
                        "numeric_boundary": "verified_exact",
                        "reference": "Self-authored synthetic point measurements",
                    },
                }
                intake_path = folder / f"{phase}-intake.json"
                save(intake_path, request)
                if phase != "evaluation":
                    normalize(source, intake_path, folder / phase)
                    entry[phase] = reference(folder / phase)
                else:
                    entry[phase] = {
                        "intake_reference": {
                            "file": str(intake_path),
                            "sha256": digest(intake_path.read_bytes()),
                        },
                        "origins_us": [index * 5 * MINUTE for index in range(first, last)],
                    }
            registry["people"].append(entry)
        save(output / "registry.json", registry)
