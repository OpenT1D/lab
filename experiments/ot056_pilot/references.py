"""Turn OT-055's independent numerical vectors into actual shared CSV inputs."""

from copy import deepcopy
from decimal import Decimal
from pathlib import Path

from experiments.catalogue.storage import (
    dump,
    encoded,
    fresh,
    load_sealed,
    read,
    seal,
    source_hashes,
)
from experiments.mmtt_sampling.fixtures import DESIGN
from experiments.observation_analysis.fixtures import csv_bytes, package
from experiments.observation_analysis.intake import assess

VECTORS = Path(__file__).parents[1] / "mmtt_sampling/fixtures/numerical-reference.json"
SOURCES = (
    "experiments/ot056_pilot/references.py",
    "experiments/mmtt_sampling/fixtures/numerical-reference.json",
    "experiments/observation_analysis/fixtures.py",
)


def reference_documents():
    vectors = read(VECTORS)
    metadata = package()
    template = metadata["participants"][0]
    metadata["participants"] = []
    metadata["provenance"] = (
        "Manufactured OT-055 analytical vectors converted to OT-056 shared inputs; "
        "no human measurements or biological reference truth"
    )
    rows, answers = [], []
    for index, vector in enumerate(vectors["cases"]):
        person = deepcopy(template)
        person["id"] = f"reference-{vector['id']}"
        person["allocation"] = "development" if index < 2 else "evaluation"
        metadata["participants"].append(person)
        before = vector["baseline_cpeptide_pmol_l"]
        after = vector.get("followup_cpeptide_pmol_l", before)
        for visit, concentrations in zip(person["visits"], (before, after), strict=True):
            for time, concentration in zip(vectors["times_minutes"], concentrations, strict=True):
                rows.append(
                    [
                        person["id"],
                        visit["id"],
                        visit["challenge_id"],
                        time,
                        "5.5",
                        "observed",
                        str(Decimal(concentration) / Decimal(1000)),
                        "observed",
                    ]
                )
        answers.append(
            {
                "participant_id": person["id"],
                "before_total_pmol": vector["expected_total_pmol"],
                "after_total_pmol": vector.get(
                    "expected_followup_total_pmol", vector["expected_total_pmol"]
                ),
                "paired_change_pmol": vector.get("expected_paired_change_pmol", "0"),
                "before_auc_pmol_min_l": vector["expected_cpeptide_auc_pmol_min_l"],
                "negative_terminal_rate_expected": "expected_terminal_rate_pmol_min" in vector,
                "terminal_rate_pmol_min": vector.get("expected_terminal_rate_pmol_min"),
            }
        )
    design = deepcopy(read(DESIGN))
    design["allocation"] = {p["id"]: p["allocation"] for p in metadata["participants"]}
    design["selection_participants"] = [
        p["id"] for p in metadata["participants"] if p["allocation"] == "development"
    ]
    design["selection_rationale"] = (
        "Manufactured constant and linear reference curves; subset equality is a numerical "
        "control only, not evidence of information preservation in peaked or human observations"
    )
    expected = {
        "schema": "ot056-manufactured-answers/1",
        "kinetics": vectors["kinetics"],
        "tolerance_pmol": vectors["absolute_software_tolerance_pmol"],
        "scope": "formal unclipped source-model totals; negative-rate acceptance remains explicit",
        "answers": answers,
        "source_sha256": source_hashes(SOURCES),
    }
    return metadata, csv_bytes(rows), design, expected


def export_references(output):
    output = fresh(output)
    metadata, raw, design, expected = reference_documents()
    dump(output / "package.json", metadata)
    (output / "observations.csv").write_bytes(raw)
    dump(output / "sampling-design.json", design)
    dump(output / "expected.json", expected)
    if (
        assess({"package.json": (output / "package.json").read_bytes(), "observations.csv": raw})[
            "status"
        ]
        != "valid"
    ):
        raise ValueError("Manufactured reference inputs failed the shared importer")
    seal(output)
    verify_references(output)
    return expected


def verify_references(archive):
    archive = load_sealed(archive)
    metadata, raw, design, expected = reference_documents()
    for name, value in {
        "package.json": encoded(metadata),
        "observations.csv": raw,
        "sampling-design.json": encoded(design),
        "expected.json": encoded(expected),
    }.items():
        if (archive / name).read_bytes() != value:
            raise ValueError(
                "Reference inputs or expected answers differ from the controlled vectors"
            )
    return expected
