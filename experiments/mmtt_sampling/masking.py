"""Select raw observed rows before shared analyte parsing and numerical analysis.

Only CSV framing, declared identities and actual sample times are inspected.
Original bytes remain in the parent shared import archive; this creates a child
CSV with opaque retained glucose/C-peptide/status cells, not interpolated values.
"""

import csv
import io
import math

from experiments.observation_analysis.observations import COLUMNS, validate_package

from .design import times


def mask_csv(raw, package, schedule):
    """Return (retained CSV bytes, complete planned visit-time inventory).

    A missing requested time is a visit-level preflight failure, retained in the
    inventory even if the shared numerical importer could fit remaining rows.
    The task runner must honor that failure before calling the shared estimator.
    Invalid framing/identity/time structure is rejected without inspecting or
    echoing analyte values. No participant-specific fit state is accepted.
    """
    validate_package(package)
    requested = times(schedule)
    inventory = {
        (person["id"], visit["id"]): {
            "participant_id": person["id"],
            "visit_id": visit["id"],
            "challenge_id": visit["challenge_id"],
            "actual_times_minutes": [],
            "retained_times_minutes": [],
            "omitted_rows": 0,
        }
        for person in package["participants"]
        for visit in person["visits"]
    }
    retained = []
    try:
        reader = csv.DictReader(io.StringIO(raw.decode("utf-8-sig")), strict=True)
        if tuple(reader.fieldnames or ()) != COLUMNS:
            raise ValueError("CSV header must match the shared observation contract")
        for index, row in enumerate(reader, 2):
            if index > 100_001 or None in row or None in row.values():
                raise ValueError("Invalid CSV framing or observation row limit")
            visit = inventory.get((row["participant_id"], row["visit_id"]))
            if visit is None or row["challenge_id"] != visit["challenge_id"]:
                raise ValueError("Observation identity differs from the declared roster")
            try:
                time = float(row["time_min"])
            except (ValueError, OverflowError) as error:
                raise ValueError("Invalid actual sample time") from error
            if not math.isfinite(time) or not 0 <= time <= 120:
                raise ValueError("Actual sample times must be finite within 0–120 minutes")
            actual = visit["actual_times_minutes"]
            if actual and time <= actual[-1]:
                raise ValueError("Actual sample times must be unique and increasing per visit")
            actual.append(time)
            if time in requested:
                retained.append([row[column] for column in COLUMNS])
                visit["retained_times_minutes"].append(time)
            else:
                visit["omitted_rows"] += 1
    except (UnicodeError, csv.Error) as error:
        raise ValueError("Invalid UTF-8 or CSV framing") from error
    for visit in inventory.values():
        visit["requested_times_minutes"] = list(requested)
        visit["missing_requested_times_minutes"] = [
            time for time in requested if time not in visit["retained_times_minutes"]
        ]
        visit["status"] = (
            "missing_requested_times" if visit["missing_requested_times_minutes"] else "complete"
        )
    stream = io.StringIO(newline="")
    writer = csv.writer(stream)
    writer.writerow(COLUMNS)
    writer.writerows(retained)
    return stream.getvalue().encode("utf-8"), list(inventory.values())
