"""Build schedule-selection evidence from OT-054's shared development importer."""

from pathlib import Path

from experiments.catalogue.storage import decode
from experiments.m3.researcher.intake import read_regular
from experiments.observation_analysis.intake import INPUTS, verify_import
from experiments.observation_analysis.observations import validate_package

from .design import validate_design, validate_development_times


def development_inventory(archive, design):
    """Reject an evaluation roster before opening its observation CSV.

    The shared reader subsequently verifies the seal and revalidates raw bytes.
    There is no estimator state or fitted participant parameter in this boundary.
    """
    design = validate_design(design)
    archive = Path(archive)
    package = decode(read_regular(archive / "package.json", INPUTS["package.json"], "package"))
    validate_package(package)
    selected = set(design["selection_participants"])
    if {p["id"] for p in package["participants"]} != selected or any(
        p["allocation"] != "development" for p in package["participants"]
    ):
        raise ValueError("Use a development-only import containing exactly selection participants")
    checked_package, validation = verify_import(archive)
    if checked_package != package or validation is None or not validation["valid"]:
        raise ValueError("Development import invalid or changed; inspect shared import diagnostics")
    visits = [
        {
            "participant_id": visit["participant_id"],
            "visit_id": visit["visit_id"],
            "times_minutes": [row["time_min"] for row in visit["rows"]],
        }
        for visit in validation["visits"]
    ]
    return validate_development_times(design, visits)
