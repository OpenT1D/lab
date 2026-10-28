"""Structurally matched invented observations, reusing the checked OT-055 fixture."""

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
from experiments.mmtt_sampling.fixtures import example
from experiments.observation_analysis.fixtures import case_csv, csv_bytes
from experiments.observation_analysis.intake import assess
from experiments.observation_analysis.observations import COLUMNS

SCHEMA = "ot056-technical-cases/1"
SOURCES = (
    "experiments/ot056_pilot/cases.py",
    "experiments/mmtt_sampling/fixtures.py",
    "experiments/mmtt_sampling/fixtures/design.json",
    "experiments/observation_analysis/fixtures.py",
)
MAIN_CLASSIFICATIONS = {
    "invented-development-01": "consistent within investigated assumptions",
    "invented-development-02": "insufficiently determined",
    "invented-evaluation-01": "assumption-dependent",
    "invented-evaluation-low": "insufficiently determined",
    "invented-evaluation-failure": "insufficiently determined",
}
SCHEDULE_CLASSIFICATIONS = {
    "full": MAIN_CLASSIFICATIONS,
    **{
        schedule: {
            **MAIN_CLASSIFICATIONS,
            "invented-development-02": "consistent within investigated assumptions",
            "invented-evaluation-01": conclusion,
        }
        for schedule, conclusion in (
            ("five-times", "assumption-dependent"),
            ("four-times", "insufficiently determined"),
            ("three-times", "consistent within investigated assumptions"),
        )
    },
}


def check_main_report(report, schedule="full"):
    actual = {key: person["classification"] for key, person in report["people"].items()}
    if actual != SCHEDULE_CLASSIFICATIONS[schedule]:
        raise ValueError("Main synthetic case does not cover the intended interpretations")
    return actual


def case_documents(scale, label):
    metadata, raw, design = example()
    metadata["provenance"] = (
        f"Invented OT-056 technical case {label}; OT-055 structure with OT-054 increase "
        f"and assumption-dependent controls, scaled by {scale}; invented minute-15 "
        "observations follow the declared piecewise-linear control; "
        "no participant observations or established human task-difficulty equivalence"
    )
    controls = {}
    for person, control in (
        ("invented-development-01", "increase"),
        ("invented-evaluation-01", "assumption-dependent"),
    ):
        observations = list(csv.reader(io.StringIO(case_csv(control).decode())))[1:]
        controls[person] = {(row[1], float(row[3])): float(row[6]) for row in observations}
    rows = list(csv.reader(io.StringIO(raw.decode())))[1:]
    for row in rows:
        if row[COLUMNS.index("cpeptide_status")] == "observed":
            index = COLUMNS.index("cpeptide_nmol_l")
            profile = controls.get(row[COLUMNS.index("participant_id")])
            value = float(row[index])
            if profile is not None:
                visit = row[COLUMNS.index("visit_id")]
                time = float(row[COLUMNS.index("time_min")])
                # This constructs an invented observation on a known synthetic
                # path; no missing participant measurement is imputed.
                value = (
                    (profile[visit, 0] + profile[visit, 30]) / 2
                    if time == 15
                    else profile[visit, time]
                )
            row[index] = format(value * scale, ".15g")
    return metadata, rows, design


def export_cases(output):
    output = fresh(output)
    records = []

    def write_case(case_id, metadata, rows, design, expected_valid):
        directory = output / case_id
        directory.mkdir()
        dump(directory / "package.json", metadata)
        (directory / "observations.csv").write_bytes(csv_bytes(rows))
        dump(directory / "sampling-design.json", design)
        raw = {
            name: (directory / name).read_bytes() for name in ("package.json", "observations.csv")
        }
        result = assess(raw)
        if (result["status"] == "valid") != expected_valid:
            raise ValueError("Generated case does not meet its declared import expectation")
        records.append(
            {
                "case": case_id,
                "expected_import_valid": expected_valid,
                "participants": len(metadata["participants"]),
                "rows": len(rows),
                "inputs": {name: digest(value) for name, value in raw.items()},
                "sampling_design_sha256": digest((directory / "sampling-design.json").read_bytes()),
            }
        )

    for task in ("task1", "task2"):
        for label, scale in (("A", 0.95), ("B", 1.0), ("C", 1.05)):
            metadata, rows, design = case_documents(scale, f"{task}-{label}")
            write_case(f"{task}-{label}", metadata, rows, design, True)
    metadata, rows, design = case_documents(1.0, "fault-controls")
    bad_units = deepcopy(metadata)
    bad_units["units"]["cpeptide"] = "unresolved-unit"
    write_case("bad-units", bad_units, rows, design, False)
    missing = deepcopy(rows)
    del missing[5]  # First declared visit's actual 120-minute measurement.
    write_case("missing-endpoint", metadata, missing, design, False)
    write_case("duplicate-time", metadata, rows + [deepcopy(rows[0])], design, False)
    receipt = {
        "schema": SCHEMA,
        "scope": "invented technical input preparation only",
        "human_sessions": 0,
        "human_difficulty_matching": "unassessed",
        "expected_model_interpretations": SCHEDULE_CLASSIFICATIONS,
        "source_sha256": source_hashes(SOURCES),
        "cases": records,
    }
    dump(output / "cases.json", receipt)
    seal(output)
    return receipt


def verify_cases(archive):
    archive = load_sealed(archive)
    receipt = read(archive / "cases.json")
    if receipt["schema"] != SCHEMA or receipt["source_sha256"] != source_hashes(SOURCES):
        raise ValueError("Unsupported case source identity")
    with tempfile.TemporaryDirectory() as temporary:
        expected_receipt = export_cases(Path(temporary) / "expected")
    if receipt != expected_receipt:
        raise ValueError("Case receipt differs from the trusted synthetic construction")
    expected = {f"{task}-{label}" for task in ("task1", "task2") for label in "ABC"}
    expected |= {"bad-units", "missing-endpoint", "duplicate-time"}
    if {case["case"] for case in receipt["cases"]} != expected or len(receipt["cases"]) != 9:
        raise ValueError("Case coverage differs")
    for case in receipt["cases"]:
        directory = Path(archive) / case["case"]
        raw = {
            name: (directory / name).read_bytes() for name in ("package.json", "observations.csv")
        }
        if {name: digest(value) for name, value in raw.items()} != case["inputs"]:
            raise ValueError("Case inputs differ")
        if (
            digest((directory / "sampling-design.json").read_bytes())
            != case["sampling_design_sha256"]
        ):
            raise ValueError("Sampling design differs")
        if (assess(raw)["status"] == "valid") != case["expected_import_valid"]:
            raise ValueError("Case import expectation differs")
    return receipt
