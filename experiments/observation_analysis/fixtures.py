"""Invented import example; no empirical assay or population parameters."""

import csv
import io

from experiments.catalogue.storage import dump, fresh

from .observations import COLUMNS


def package():
    return {
        "schema": "opent1d.observations/1",
        "data_kind": "synthetic",
        "provenance": "Invented validation fixture; no participant observations",
        "units": {"time": "min", "glucose": "mmol/L", "cpeptide": "nmol/L"},
        "participants": [
            {
                "id": "invented-01",
                "allocation": "development",
                "context": {
                    "age_years": 30,
                    "sex": "unspecified",
                    "weight_kg": 70,
                    "height_cm": 170,
                    "renal_context": "invented; no renal inference",
                    "population": "invented; no T1D applicability claimed",
                },
                "visits": [
                    {
                        "id": visit,
                        "challenge_id": "meal-01",
                        "protocol": "invented 0–120 min",
                        "meal": "invented challenge",
                        "medication_context": "invented; none supplied",
                        "assay": {
                            "id": "invented-assay",
                            "cpeptide_lod_nmol_l": 0.01,
                            "cpeptide_loq_nmol_l": 0.02,
                        },
                    }
                    for visit in ("before", "after")
                ],
            }
        ],
    }


def csv_bytes(rows=None):
    stream = io.StringIO(newline="")
    writer = csv.writer(stream)
    writer.writerow(COLUMNS)
    if rows is None:
        rows = [
            [
                "invented-01",
                visit,
                "meal-01",
                time,
                5.5,
                "observed",
                0.2 if visit == "before" else 0.3,
                "observed",
            ]
            for visit in ("before", "after")
            for time in (0, 30, 60, 90, 120)
        ]
    writer.writerows(rows)
    return stream.getvalue().encode()


CASES = ("increase", "assumption-dependent", "unresolved", "censored")


def case_csv(case):
    if case not in CASES:
        raise ValueError("Unknown invented example case")
    rows = []
    for visit in ("before", "after"):
        for t in (0, 30, 60, 90, 120):
            cp = 0.2 if visit == "before" or case == "unresolved" else 0.3
            if case == "assumption-dependent" and visit == "after":
                # Engineered development counterexample: the fixed nominal
                # linear functional changes by -10 pmol, while the declared
                # initial-inventory stress changes it by +123.495... pmol.
                cp = 0.3 if t == 0 else 0.2176708372104129
            rows.append(["invented-01", visit, "meal-01", t, 5.5, "observed", cp, "observed"])
    if case == "censored":
        rows[1][-2:] = ["", "below_loq"]
    return csv_bytes(rows)


def export_example(output, case="increase"):
    output = fresh(output)
    declared = package()
    declared["provenance"] += f" Case: {case}; engineered development control."
    dump(output / "package.json", declared)
    (output / "observations.csv").write_bytes(case_csv(case))
    dump(output / "settings.json", analysis_settings())
    return output


def analysis_settings():
    """Prespecified engineering stresses, never demographic or T1D defaults."""
    nominal = {
        "id": "nominal",
        "rationale": "BC-003 nominal T1D group coefficients as synthetic controls; "
        "4.585 L explicitly supplied whole-body volume, not inferred from demographics",
        "k1_per_min": 0.037,
        "k2_per_min": 0.031,
        "k3_per_min": 0.052,
        "volume_l": 4.585,
        "initial_peripheral_factor": 1.0,
    }
    return {
        "schema": "opent1d.observation-analysis-settings/1",
        "visit_order": ["before", "after"],
        "variants": [
            nominal,
            {
                **nominal,
                "id": "volume-120",
                "volume_l": 5.502,
                "rationale": "Deliberate 20 percent volume engineering stress; no human range",
            },
            {
                **nominal,
                "id": "peripheral-075",
                "initial_peripheral_factor": 0.75,
                "rationale": "Deliberate 75 percent initial peripheral inventory stress; "
                "no empirical fasting-prehistory distribution",
            },
        ],
        "uncertainty": {
            "draws": 128,
            "seed": 117,
            "independent_sd_pmol_l": 2.0,
            "paired_offset_sd_pmol_l": 1.0,
            "scope": "synthetic-engineering",
        },
    }
