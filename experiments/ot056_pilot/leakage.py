"""Retain poisoned omitted cells and actual OT-055 raw-mask evidence."""

import csv
import io
from copy import deepcopy

from experiments.catalogue.storage import digest, dump, fresh, read, seal, source_hashes
from experiments.mmtt_sampling.masking import mask_csv
from experiments.observation_analysis.fixtures import csv_bytes
from experiments.observation_analysis.intake import assess
from experiments.observation_analysis.observations import COLUMNS

SOURCES = (
    "experiments/ot056_pilot/leakage.py",
    "experiments/mmtt_sampling/masking.py",
    "experiments/observation_analysis/intake.py",
    "experiments/observation_analysis/observations.py",
)


def omitted_cell_controls(case, output):
    output = fresh(output)
    package_raw = (case / "package.json").read_bytes()
    metadata = read(case / "package.json")
    evaluation = {p["id"] for p in metadata["participants"] if p["allocation"] == "evaluation"}
    design = read(case / "sampling-design.json")
    original = (case / "observations.csv").read_bytes()
    rows = list(csv.reader(io.StringIO(original.decode())))[1:]
    (output / "package.json").write_bytes(package_raw)
    (output / "original.csv").write_bytes(original)
    records = []
    for label in ("invalid-omitted-cells", "extreme-omitted-cells"):
        changed = deepcopy(rows)
        for row in changed:
            if (
                row[COLUMNS.index("participant_id")] in evaluation
                and float(row[COLUMNS.index("time_min")]) == 15
            ):
                for analyte in ("glucose", "cpeptide"):
                    value_field = "glucose_mmol_l" if analyte == "glucose" else "cpeptide_nmol_l"
                    row[COLUMNS.index(value_field)] = (
                        "invalid" if label.startswith("invalid") else "1e100"
                    )
                    row[COLUMNS.index(f"{analyte}_status")] = (
                        "invalid" if label.startswith("invalid") else "observed"
                    )
        poisoned = csv_bytes(changed)
        (output / f"{label}.csv").write_bytes(poisoned)
        full_status = assess({"package.json": package_raw, "observations.csv": poisoned})["status"]
        for schedule, times in design["subsets"].items():
            if 15 in times:
                raise ValueError("This fixed omitted-cell control requires omission of minute 15")
            retained, inventory = mask_csv(original, metadata, times)
            altered, changed_inventory = mask_csv(poisoned, metadata, times)
            if retained != altered or inventory != changed_inventory:
                raise ValueError("Omitted values affected the retained numerical input")
            reduced_status = assess({"package.json": package_raw, "observations.csv": altered})[
                "status"
            ]
            if reduced_status != "valid":
                raise ValueError("Retained synthetic input unexpectedly invalid")
            (output / f"{label}-{schedule}.csv").write_bytes(altered)
            records.append(
                {
                    "control": label,
                    "schedule": schedule,
                    "times_minutes": times,
                    "poisoned_full_import_status": full_status,
                    "retained_import_status": reduced_status,
                    "identical_retained_csv_sha256": digest(altered),
                    "visits": inventory,
                }
            )
    result = {
        "schema": "ot056-omitted-cell-controls/1",
        "source_sha256": source_hashes(SOURCES),
        "source_package_sha256": digest(package_raw),
        "source_csv_sha256": digest(original),
        "status": "raw-mask-controls-passed",
        "estimator_executed": False,
        "human_sessions": 0,
        "records": records,
    }
    dump(output / "mask-controls.json", result)
    seal(output)
    return result


def schedule_gap_control(reference_inputs, output):
    """One held-out visit misses minute 90; development selection stays untouched."""
    output = fresh(output)
    package_raw = (reference_inputs / "package.json").read_bytes()
    metadata = read(reference_inputs / "package.json")
    design = read(reference_inputs / "sampling-design.json")
    person = next(p for p in metadata["participants"] if p["allocation"] == "evaluation")
    identity = (person["id"], person["visits"][0]["id"])
    rows = list(csv.reader(io.StringIO((reference_inputs / "observations.csv").read_text())))[1:]
    rows = [
        row
        for row in rows
        if not (
            (row[COLUMNS.index("participant_id")], row[COLUMNS.index("visit_id")]) == identity
            and float(row[COLUMNS.index("time_min")]) == 90
        )
    ]
    raw = csv_bytes(rows)
    (output / "package.json").write_bytes(package_raw)
    (output / "observations.csv").write_bytes(raw)
    dump(output / "sampling-design.json", design)
    outcomes = {}
    for schedule, times in {"full": design["full_times_minutes"], **design["subsets"]}.items():
        retained, inventory = mask_csv(raw, metadata, times)
        blocked = [r for r in inventory if r["status"] != "complete"]
        outcomes[schedule] = {
            "missing_visits": blocked,
            "retained_csv_sha256": digest(retained),
            "must_block_affected_visit_before_estimation": 90 in times,
        }
    result = {
        "schema": "ot056-schedule-gap-control/1",
        "human_sessions": 0,
        "affected_participant": identity[0],
        "affected_visit": identity[1],
        "missing_time_min": 90,
        "outcomes": outcomes,
        "shared_import_status": assess({"package.json": package_raw, "observations.csv": raw})[
            "status"
        ],
        "estimator_executed": False,
    }
    dump(output / "gap-control.json", result)
    seal(output)
    return result
