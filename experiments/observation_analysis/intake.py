"""Retain exact local input bytes and import diagnostics in a fresh sealed archive."""

import json
from pathlib import Path

from experiments.catalogue.storage import decode, digest, dump, fresh, load_sealed, seal
from experiments.m3.researcher.intake import read_regular

from .observations import parse_csv, validate_package

SCHEMA = "opent1d.observation-import/1"
INPUTS = {"package.json": 1024 * 1024, "observations.csv": 16 * 1024 * 1024}


def validate_inputs(package_raw, csv_raw):
    package = decode(package_raw)
    validate_package(package)
    return package, parse_csv(csv_raw, package)


def assess(raw):
    """Deterministically record admissible bytes or their import failure."""
    record = {
        "schema": SCHEMA,
        "status": "invalid",
        "inputs": {name: digest(value) for name, value in raw.items()},
        "validation": None,
    }
    if set(raw) != set(INPUTS):
        record["error"] = "Input snapshot incomplete; check named regular files and byte limits"
        return record
    try:
        _, validation = validate_inputs(raw["package.json"], raw["observations.csv"])
        record.update(status="valid" if validation["valid"] else "invalid", validation=validation)
    except (ValueError, TypeError, KeyError, OverflowError, RecursionError) as error:
        record["error_type"] = type(error).__name__
        record["error"] = (
            "Invalid JSON encoding or framing"
            if isinstance(error, (json.JSONDecodeError, UnicodeError))
            else str(error)
            if isinstance(error, ValueError)
            else "Invalid metadata structure"
        )
    return record


def import_observations(package_path, csv_path, output):
    """No numerical estimation, source execution or data access beyond named files."""
    output = fresh(output, (package_path, csv_path))
    raw_inputs = {}
    dump(output / "import.json", {"schema": SCHEMA, "status": "started"})
    try:
        for name, path in (("package.json", package_path), ("observations.csv", csv_path)):
            try:
                raw = read_regular(path, INPUTS[name], name)
            except (OSError, ValueError):
                continue  # Attempt the other named input even when this one is unavailable.
            (output / name).write_bytes(raw)
            raw_inputs[name] = raw
    finally:
        record = assess(raw_inputs)
        dump(output / "import.json", record)
        seal(output)
    return record


def verify_import(archive):
    """Revalidate raw observations with trusted code; no archived Python is imported."""
    archive = load_sealed(archive)
    raw = {
        name: read_regular(archive / name, limit, name)
        for name, limit in INPUTS.items()
        if (archive / name).exists()
    }
    saved = decode(read_regular(archive / "import.json", 64 * 1024 * 1024, "import record"))
    if saved != assess(raw):
        raise ValueError("Observation import diagnostics differ")
    package = decode(raw["package.json"]) if saved["validation"] is not None else None
    return package, saved["validation"]


def load_input_bytes(archive):
    """Only the fixed input files are handed to later task-specific plan builders."""
    _, validation = verify_import(archive)
    if validation is None or not validation["valid"]:
        raise ValueError("Observation package is invalid; inspect retained import diagnostics")
    return {name: (Path(archive) / name).read_bytes() for name in INPUTS}
