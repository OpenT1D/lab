"""Versioned local observations; retain a declared roster and every import failure.

This module has no estimator, kinetic defaults or empirical eligibility decision.
The initial route admits declared invented observations only.
"""

import csv
import io
import math
import re

from experiments.m3.common import require

SCHEMA = "opent1d.observations/1"
ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9_-]{0,63}\Z")
COLUMNS = (
    "participant_id",
    "visit_id",
    "challenge_id",
    "time_min",
    "glucose_mmol_l",
    "glucose_status",
    "cpeptide_nmol_l",
    "cpeptide_status",
)


def number(value, label, minimum=0, strict=False):
    require(type(value) in (int, float) and math.isfinite(value), f"Finite {label} required")
    require(value > minimum if strict else value >= minimum, f"Invalid {label}")
    return float(value)


def fields(value, expected, label):
    require(isinstance(value, dict) and set(value) == set(expected), f"Invalid {label} fields")


def text(value, label):
    require(isinstance(value, str) and 0 < len(value.strip()) <= 4096, f"Missing {label}")


def identifier(value, label):
    require(isinstance(value, str) and ID.fullmatch(value), f"Invalid {label}")


def validate_package(package):
    """Validate metadata without opening observations or interpreting medical context."""
    fields(package, ("schema", "data_kind", "provenance", "units", "participants"), "package")
    require(package["schema"] == SCHEMA, "Unsupported observation package schema")
    require(package["data_kind"] == "synthetic", "Only declared synthetic observations admitted")
    text(package["provenance"], "invented-data provenance")
    require(
        package["units"] == {"time": "min", "glucose": "mmol/L", "cpeptide": "nmol/L"},
        "Use explicit min, mmol/L glucose and nmol/L C-peptide; convert before import",
    )
    people = package["participants"]
    require(isinstance(people, list) and 0 < len(people) <= 256, "Declare 1–256 participants")
    seen = set()
    for person in people:
        fields(person, ("id", "allocation", "context", "visits"), "participant")
        identifier(person["id"], "participant id")
        require(person["id"] not in seen, "Duplicate participant id")
        seen.add(person["id"])
        require(person["allocation"] in ("development", "evaluation"), "Invalid allocation")
        # Allocation belongs to the person, so a visit cannot cross the split.
        fields(
            person["context"],
            ("age_years", "sex", "weight_kg", "height_cm", "renal_context", "population"),
            "participant context",
        )
        for key in ("age_years", "weight_kg", "height_cm"):
            number(person["context"][key], key, strict=True)
        for key in ("sex", "renal_context", "population"):
            text(person["context"][key], key)
        visits = person["visits"]
        require(isinstance(visits, list) and len(visits) == 2, "Declare exactly two linked visits")
        seen_visits = set()
        for visit in visits:
            fields(
                visit,
                ("id", "challenge_id", "protocol", "meal", "assay", "medication_context"),
                "visit",
            )
            identifier(visit["id"], "visit id")
            identifier(visit["challenge_id"], "challenge id")
            require(visit["id"] not in seen_visits, "Duplicate visit id")
            seen_visits.add(visit["id"])
            for key in ("protocol", "meal", "medication_context"):
                text(visit[key], key)
            assay = visit["assay"]
            fields(assay, ("id", "cpeptide_lod_nmol_l", "cpeptide_loq_nmol_l"), "assay")
            text(assay["id"], "assay id")
            lod = number(assay["cpeptide_lod_nmol_l"], "C-peptide LOD")
            loq = number(assay["cpeptide_loq_nmol_l"], "C-peptide LOQ")
            require(loq >= lod, "C-peptide LOQ must be >= LOD")
    return package


def parse_csv(raw, package):
    """Return all visits and errors; never silently discard or impute a row.

    Invalid CSV framing is a package-level error. Individual invalid records keep
    their row number and mark their declared visit invalid. Unknown identities are
    retained as global errors and make the entire analysis incomplete.
    """
    validate_package(package)
    visits = {
        (person["id"], visit["id"]): {
            "participant_id": person["id"],
            "visit_id": visit["id"],
            "challenge_id": visit["challenge_id"],
            "rows": [],
            "errors": [],
            "metadata": visit,
        }
        for person in package["participants"]
        for visit in person["visits"]
    }
    seen_times = {key: set() for key in visits}
    errors = []
    try:
        reader = csv.DictReader(io.StringIO(raw.decode("utf-8-sig")), strict=True)
        require(
            tuple(reader.fieldnames or ()) == COLUMNS, "CSV header must match documented columns"
        )
        for index, row in enumerate(reader, 2):
            require(index <= 100_001, "Observation row limit exceeded")
            key = (row.get("participant_id"), row.get("visit_id"))
            visit = visits.get(key)
            try:
                require(None not in row and None not in row.values(), "CSV field count differs")
                require(
                    visit is not None, "Undeclared participant/visit; amend the declared roster"
                )
                require(row["challenge_id"] == visit["challenge_id"], "Challenge identity differs")
                time = float(row["time_min"])
                require(math.isfinite(time) and 0 <= time <= 120, "Time must be within 0–120 min")
                require(
                    time not in seen_times[key],
                    "Duplicate sample time; resolve replicates explicitly before import",
                )
                seen_times[key].add(time)
                parsed = {"time_min": time, "row": index}
                for analyte, column in (
                    ("glucose", "glucose_mmol_l"),
                    ("cpeptide", "cpeptide_nmol_l"),
                ):
                    status = row[analyte + "_status"]
                    allowed = (
                        ("observed", "missing", "below_loq")
                        if analyte == "cpeptide"
                        else ("observed", "missing")
                    )
                    require(status in allowed, f"Invalid {analyte} observation status")
                    value = row[column]
                    if status != "observed":
                        require(value == "", f"Leave {analyte} blank for missing/censored values")
                        parsed[column] = None
                    else:
                        value = float(value)
                        require(math.isfinite(value) and value >= 0, f"Invalid {analyte} value")
                        scale = 120_000 if analyte == "cpeptide" else 120
                        require(
                            math.isfinite(value * scale),
                            f"{analyte} overflows canonical unit/AUC arithmetic",
                        )
                        if analyte == "cpeptide":
                            require(
                                value >= visit["metadata"]["assay"]["cpeptide_loq_nmol_l"],
                                "C-peptide below LOQ must be explicitly censored",
                            )
                        parsed[column] = value
                    parsed[analyte + "_status"] = status
                visit["rows"].append(parsed)
            except (ValueError, OverflowError) as error:
                # Do not echo source values or personal identifiers in diagnostics/logs.
                message = str(error)
                if message.startswith("could not convert"):
                    message = "Invalid numeric cell; use decimal numbers and explicit status"
                problem = {"row": index, "reason": message}
                (visit["errors"] if visit is not None else errors).append(problem)
    except (UnicodeError, csv.Error, ValueError) as error:
        errors.append(
            {
                "row": None,
                "reason": str(error)
                if isinstance(error, ValueError)
                else "Invalid UTF-8 or CSV framing",
            }
        )
    for visit in visits.values():
        times = [row["time_min"] for row in visit["rows"]]
        if times != sorted(times):
            visit["errors"].append({"row": None, "reason": "Sample times must increase"})
        if not times or times[0] != 0 or times[-1] != 120:
            visit["errors"].append({"row": None, "reason": "Measured 0 and 120 min required"})
        visit["valid"] = not visit["errors"]
    return {
        "visits": list(visits.values()),
        "errors": errors,
        "valid": not errors and all(visit["valid"] for visit in visits.values()),
    }
