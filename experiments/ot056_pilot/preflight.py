"""Exercise the actual shared import and development-selection boundaries."""

import csv
import io
import tempfile
from copy import deepcopy
from pathlib import Path

from experiments.catalogue.storage import (
    digest,
    dump,
    fresh,
    load_sealed,
    read,
    seal,
    source_hashes,
)
from experiments.mmtt_sampling.__main__ import freeze_import
from experiments.mmtt_sampling.intake import development_inventory
from experiments.observation_analysis.fixtures import csv_bytes
from experiments.observation_analysis.intake import import_observations, verify_import
from experiments.observation_analysis.observations import COLUMNS

from .cases import export_cases, verify_cases

SCHEMA = "ot056-technical-preflight/1"
SOURCES = (
    "experiments/ot056_pilot/preflight.py",
    "experiments/observation_analysis/intake.py",
    "experiments/observation_analysis/observations.py",
    "experiments/mmtt_sampling/__main__.py",
    "experiments/mmtt_sampling/design.py",
    "experiments/mmtt_sampling/intake.py",
    "experiments/catalogue/storage.py",
)


def development_copy(case, destination):
    """Select by the frozen metadata roster, before any future estimation."""
    metadata = deepcopy(read(case / "package.json"))
    metadata["participants"] = [
        person for person in metadata["participants"] if person["allocation"] == "development"
    ]
    identities = {person["id"] for person in metadata["participants"]}
    rows = list(csv.reader(io.StringIO((case / "observations.csv").read_text())))[1:]
    rows = [row for row in rows if row[COLUMNS.index("participant_id")] in identities]
    destination.mkdir()
    dump(destination / "package.json", metadata)
    (destination / "observations.csv").write_bytes(csv_bytes(rows))


def preflight(output):
    output = fresh(output)
    receipt = export_cases(output / "cases")
    records = []
    for case in receipt["cases"]:
        case_id = case["case"]
        inputs = output / "cases" / case_id
        archive = output / f"{case_id}-import"
        record = import_observations(inputs / "package.json", inputs / "observations.csv", archive)
        _, validation = verify_import(archive)
        if (record["status"] == "valid") != case["expected_import_valid"]:
            raise ValueError("Actual shared import disagrees with the case's expected boundary")
        evidence = {
            "case": case_id,
            "import_status": record["status"],
            "import_manifest_sha256": digest((archive / "manifest.json").read_bytes()),
            "planned_visits": 2 * case["participants"],
            "parsed_visits": len(validation["visits"]) if validation else None,
            "selection": None,
        }
        if case["expected_import_valid"]:
            source = output / f"{case_id}-development-input"
            development_copy(inputs, source)
            development = output / f"{case_id}-development-import"
            imported = import_observations(
                source / "package.json", source / "observations.csv", development
            )
            if imported["status"] != "valid":
                raise ValueError("Development projection is invalid")
            selection = freeze_import(
                inputs / "sampling-design.json", development, output / f"{case_id}-selection.json"
            )
            evidence["selection"] = selection
        records.append(evidence)
    result = {
        "schema": SCHEMA,
        "source_sha256": source_hashes(SOURCES),
        "status": "imports-and-selection-verified",
        "analysis_stage": "input-only-no-estimation",
        "human_sessions": 0,
        "human_observations_written": False,
        "case_manifest_sha256": digest((output / "cases/manifest.json").read_bytes()),
        "records": records,
    }
    dump(output / "preflight.json", result)
    seal(output)
    verify_preflight(output)
    return result


def verify_preflight(archive):
    archive = load_sealed(archive)
    receipt = read(archive / "preflight.json")
    if receipt["schema"] != SCHEMA or receipt["source_sha256"] != source_hashes(SOURCES):
        raise ValueError("Unsupported preflight source identity")
    if receipt["status"] != "imports-and-selection-verified" or (
        receipt["analysis_stage"] != "input-only-no-estimation"
    ):
        raise ValueError("Import preflight cannot claim task execution acceptance")
    cases = verify_cases(archive / "cases")
    if receipt["case_manifest_sha256"] != digest((archive / "cases/manifest.json").read_bytes()):
        raise ValueError("Case manifest identity differs")
    if [r["case"] for r in receipt["records"]] != [c["case"] for c in cases["cases"]]:
        raise ValueError("Preflight coverage differs")
    if receipt["human_sessions"] != 0 or receipt["human_observations_written"] is not False:
        raise ValueError("Technical preflight cannot contain human findings")
    for case, record in zip(cases["cases"], receipt["records"], strict=True):
        case_id = case["case"]
        imported = archive / f"{case_id}-import"
        _, validation = verify_import(imported)
        actual_status = read(imported / "import.json")["status"]
        if (
            actual_status != record["import_status"]
            or (actual_status == "valid") != case["expected_import_valid"]
        ):
            raise ValueError("Import outcome differs")
        if record["import_manifest_sha256"] != digest((imported / "manifest.json").read_bytes()):
            raise ValueError("Import manifest identity differs")
        if record["planned_visits"] != 2 * case["participants"] or record["parsed_visits"] != (
            len(validation["visits"]) if validation else None
        ):
            raise ValueError("Visit accounting differs")
        if case["expected_import_valid"]:
            selection = read(archive / f"{case_id}-selection.json")
            development = archive / f"{case_id}-development-import"
            with tempfile.TemporaryDirectory() as temporary:
                expected_source = Path(temporary) / "expected"
                development_copy(archive / "cases" / case_id, expected_source)
                for name in ("package.json", "observations.csv"):
                    expected_bytes = (expected_source / name).read_bytes()
                    if (development / name).read_bytes() != expected_bytes or (
                        (archive / f"{case_id}-development-input" / name).read_bytes()
                        != expected_bytes
                    ):
                        raise ValueError(
                            "Development input differs from the original case projection"
                        )
            expected = development_inventory(development, selection["design"])
            if selection != record["selection"] or selection["development_times"] != expected:
                raise ValueError("Development selection differs")
            if selection["design_sha256"] != case["sampling_design_sha256"] or (
                selection["development_import_seal_sha256"]
                != digest((development / "manifest.json").read_bytes())
            ):
                raise ValueError("Development selection identity differs")
        elif record["selection"] is not None:
            raise ValueError("Invalid observation package cannot qualify for selection")
    return receipt
