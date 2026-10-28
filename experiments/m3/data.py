"""Narrow normalized observation contract and causal window preparation."""

import math
from pathlib import Path

from .common import ID, SCHEMA, SHA, digest, finite, read, require, validate_provenance

STATUSES = ("measured", "missing", "invalid", "censored_low", "censored_high")
CLOCKS = ("elapsed_synthetic", "shifted_local", "UTC")


def registry(path):
    value, sha = read(path)
    validate_registry(value, path)
    return value, sha


def validate_registry(value, path):
    require(isinstance(value, dict), "Registry must be an object")
    require(
        set(value) == {"schema", "kind", "source", "release", "rights", "clock", "people"},
        "Invalid registry fields",
    )
    require(
        value["schema"] == SCHEMA and value["kind"] in ("synthetic", "human"),
        "Invalid data identity",
    )
    require(value["clock"] in CLOCKS, "Clock semantics required")
    for key in ("source", "release"):
        require(isinstance(value[key], str) and value[key], "Missing source/release")
    rights = value["rights"]
    require(isinstance(rights, dict), "Missing rights record")
    if value["kind"] == "human":
        require(value["source"] == "OhioT1DM-2018", "M3/1 supports direct OhioT1DM 2018 only")
        for key in (
            "authorized_processing",
            "derived_retention",
            "release_verified",
            "format_verified",
            "identity_reviewed",
            "availability_reviewed",
        ):
            require(rights.get(key) is True, "Human release/rights review incomplete")
        for key in ("terms_sha256", "dictionary_sha256", "archive_sha256"):
            require(
                isinstance(rights.get(key), str) and SHA.fullmatch(rights[key]),
                "Missing private source identity",
            )
        for key in (
            "authorization_reference",
            "retention_plan",
            "availability_assumption",
            "reserved_material",
        ):
            require(
                isinstance(rights.get(key), str) and rights[key],
                "Missing private authorization convention",
            )
        # Refuse accidental retention of health records in the repository, including ignored paths.
        from .common import ROOT

        require(
            not Path(path).resolve().is_relative_to(ROOT), "Human input must be outside repository"
        )
    else:
        require(
            set(rights) == {"synthetic"} and rights["synthetic"] is True,
            "Synthetic rights must be explicit",
        )
    people = value["people"]
    require(isinstance(people, list) and people, "Empty planned cohort")
    if value["kind"] == "human":
        require(len(people) == 6, "Account for all six planned participants")
    seen, source_seen, paths = set(), set(), set()
    for p in people:
        require(
            isinstance(p, dict) and set(p) == {"id", "source_person", "train", "evaluation"},
            "Invalid person record",
        )
        require(
            isinstance(p["id"], str) and ID.fullmatch(p["id"]) and p["id"] not in seen,
            "Duplicate/invalid participant",
        )
        require(
            isinstance(p["source_person"], str)
            and p["source_person"]
            and p["source_person"] not in source_seen,
            "Source-person overlap",
        )
        seen.add(p["id"])
        source_seen.add(p["source_person"])
        for role in ("train", "evaluation"):
            f = p[role]
            require(
                isinstance(f, dict)
                and set(f)
                == (
                    {"file", "sha256", "start", "end"}
                    | (
                        {"conversion_file", "conversion_sha256"}
                        if value["kind"] == "human"
                        else set()
                    )
                ),
                "Invalid input descriptor",
            )
            if value["kind"] == "human":
                receipt = f["conversion_file"]
                require(
                    isinstance(receipt, str)
                    and Path(receipt).name == receipt
                    and receipt not in (".", ".."),
                    "Invalid conversion receipt path",
                )
                require(
                    isinstance(f["conversion_sha256"], str)
                    and SHA.fullmatch(f["conversion_sha256"]),
                    "Missing conversion provenance",
                )
            name = f["file"]
            require(
                isinstance(name, str)
                and Path(name).name == name
                and name not in (".", "..")
                and name not in paths,
                "Duplicate/unsafe input filename",
            )
            paths.add(name)
            require(
                isinstance(f["sha256"], str) and SHA.fullmatch(f["sha256"]), "Missing input hash"
            )
            finite(f["start"], "period start", 0)
            finite(f["end"], "period end", 0)
            require(f["end"] > f["start"], "Empty period")
        require(p["train"]["end"] <= p["evaluation"]["start"], "Training/evaluation time overlap")
    if value["kind"] == "human":
        require(
            source_seen == {f"OhioT1DM:2018:{p}" for p in (559, 563, 570, 575, 588, 591)},
            "Unverified 2018 cohort membership",
        )


def observations(value, person, clock, start, end):
    require(
        isinstance(value, dict) and set(value) == {"schema", "person", "clock", "unit", "rows"},
        "Invalid observation document",
    )
    require(
        value["schema"] == SCHEMA and value["person"] == person and value["clock"] == clock,
        "Observation identity mismatch",
    )
    require(value["unit"] in ("mg/dL", "mmol/L"), "Unsupported glucose unit")
    require(isinstance(value["rows"], list), "Invalid observations")
    factor = 18 if value["unit"] == "mmol/L" else 1
    output, previous, segments = {}, -math.inf, set()
    segment = None
    for row in value["rows"]:
        require(
            isinstance(row, dict)
            and set(row)
            == {"time", "available", "segment", "raw_time", "status", "value", "bound"},
            "Invalid observation fields",
        )
        t = finite(row["time"], "measurement time", 0)
        available = finite(row["available"], "availability time", 0)
        require(
            start <= t < end and t > previous and available >= t,
            "Invalid, duplicate or nonmonotone clock",
        )
        require(isinstance(row["segment"], str) and row["segment"], "Missing clock segment")
        require(isinstance(row["raw_time"], str) and row["raw_time"], "Missing original timestamp")
        if row["segment"] != segment:
            require(row["segment"] not in segments, "Repeated clock segment")
            segments.add(row["segment"])
            segment = row["segment"]
        status = row["status"]
        require(status in STATUSES, "Unknown observation category")
        val, bound = row["value"], row["bound"]
        if status == "measured":
            finite(val, "measured CGM", 0)
            require(val > 0 and bound is None, "Measured CGM requires positive value and no bound")
        elif status.startswith("censored"):
            require(val is None, "Censoring is not a measured value")
            if bound is not None:
                finite(bound, "censor bound", 0)
                require(bound > 0, "Invalid censor bound")
        else:
            require(
                val is None and bound is None,
                "Unavailable signal must not carry a numeric estimate",
            )
        converted = dict(
            row,
            value=None if val is None else val * factor,
            bound=None if bound is None else bound * factor,
        )
        for field in ("value", "bound"):
            if converted[field] is not None:
                finite(converted[field], "converted CGM", 0)
        output[t] = converted
        previous = t
    return output


def validate_conversion(receipt, person, output_sha):
    require(
        receipt.get("kind") == "human" and receipt.get("schema") == SCHEMA,
        "Invalid conversion provenance",
    )
    require(
        receipt.get("person") == person["id"]
        and isinstance(receipt.get("source_person"), str)
        and f"OhioT1DM:2018:{receipt.get('source_person')}" == person["source_person"],
        "Conversion participant identity differs",
    )
    require(receipt.get("output_sha256") == output_sha, "Conversion output mismatch")
    for key in ("source_sha256", "intake_sha256"):
        require(
            isinstance(receipt.get(key), str) and SHA.fullmatch(receipt[key]),
            "Missing consumed native input/intake identity",
        )
    validate_provenance(receipt.get("provenance"))


def load_observations(root, person, role, clock):
    descriptor = person[role]
    value, sha = read(Path(root) / descriptor["file"])
    require(sha == descriptor["sha256"], "Input bytes changed")
    if "conversion_file" in descriptor:
        receipt, receipt_sha = read(Path(root) / descriptor["conversion_file"])
        require(receipt_sha == descriptor["conversion_sha256"], "Conversion bytes changed")
        validate_conversion(receipt, person, sha)
    return observations(value, person["id"], clock, descriptor["start"], descriptor["end"]), sha


def blocks(person):
    train = person["train"]
    cut = train["start"] + 0.8 * (train["end"] - train["start"])
    return {
        "development": (train["start"], cut),
        "validation": (cut, train["end"]),
        "evaluation": (person["evaluation"]["start"], person["evaluation"]["end"]),
    }


def origins(person, phase):
    start, end = blocks(person)[phase]
    return list(range(math.ceil(start / 5) * 5, math.ceil(end / 5) * 5, 5))


def history(rows, origin, start, phase):
    if phase == "evaluation" and origin < start + 60:
        return None, "evaluation_warmup"
    if origin - 25 < start:
        return None, "history_outside_split"
    points = [rows.get(origin - 25 + i * 5) for i in range(6)]
    if any(p is None for p in points):
        return None, "history_gap"
    if any(p["status"] != "measured" for p in points):
        return None, "history_unmeasured"
    if any(p["available"] > origin for p in points):
        return None, "history_unavailable"
    if len({p["segment"] for p in points}) != 1:
        return None, "clock_discontinuity"
    return [p["value"] for p in points], None


def target(rows, origin, end):
    if origin + 30 >= end:
        return {"status": "outside_split", "value": None, "bound": None}
    point = rows.get(origin + 30)
    if point is None:
        return {"status": "missing", "value": None, "bound": None}
    if rows.get(origin) is not None and point["segment"] != rows[origin]["segment"]:
        return {"status": "clock_discontinuity", "value": None, "bound": None}
    return {k: point[k] for k in ("status", "value", "bound")}


def training_windows(rows, person):
    start, end = blocks(person)["development"]
    output = []
    for origin in origins(person, "development"):
        x, _ = history(rows, origin, start, "development")
        y = target(rows, origin, end)
        if x is not None and y["status"] == "measured" and rows[origin + 30]["available"] < end:
            # Delayed labels arriving after the development block cannot fit this model.
            output.append((origin, x, y["value"]))
    return output


def integrate_intervals(events, start, end, kind):
    """Known disjoint intervals only; unknown coverage never becomes zero."""
    require(
        kind
        in ("basal_command_u_h", "recorded_delivery_u_h", "bolus_rate_u_min", "meal_rate_g_min"),
        "Unsupported rate semantics; amounts are not rates",
    )
    finite(start)
    finite(end)
    require(end > start, "Invalid integration window")
    total, covered, previous = 0.0, 0.0, -math.inf
    for e in events:
        require(
            set(e) == {"start", "end", "kind", "status", "value"} and e["kind"] == kind,
            "Mixed signal meaning",
        )
        a, b = finite(e["start"]), finite(e["end"])
        require(b > a and a >= previous, "Overlapping/nonpositive event intervals")
        previous = b
        require(e["status"] in ("measured", "missing", "invalid"), "Invalid rate status")
        if e["status"] != "measured":
            require(e["value"] is None, "Unknown rate must remain unknown")
            continue
        value = finite(e["value"], "rate", 0)
        duration = max(0, min(end, b) - max(start, a))
        covered += duration
        total += value * duration / (60 if kind.endswith("u_h") else 1)
    finite(total, "integrated amount", 0)
    return {
        "kind": kind,
        "known_amount": total if covered else None,
        "covered_minutes": covered,
        "unknown_minutes": end - start - covered,
    }


def verify_bytes(root, value):
    # Custodian-level byte identity only; no evaluation JSON is parsed here.
    for p in value["people"]:
        for role in ("train", "evaluation"):
            from experiments.m1.validation import Snapshot

            snap = Snapshot(root)
            raw = snap.read(p[role]["file"])
            require(digest(raw) == p[role]["sha256"], "Input bytes changed")
            snap.verify_unchanged()
            if "conversion_file" in p[role]:
                receipt, receipt_sha = read(Path(root) / p[role]["conversion_file"])
                require(receipt_sha == p[role]["conversion_sha256"], "Conversion bytes changed")
                validate_conversion(receipt, p, p[role]["sha256"])
