"""Invented OT-055 cases using OT-054's metadata and CSV constructors."""

import json
from copy import deepcopy
from pathlib import Path

from experiments.catalogue.storage import dump, fresh
from experiments.observation_analysis.fixtures import analysis_settings, csv_bytes
from experiments.observation_analysis.fixtures import package as base_package

DESIGN = Path(__file__).with_name("fixtures") / "design.json"
CASES = ("information-loss", "constant", "incomplete", "steep-response")


def example(development_only=False, case="steep-response"):
    design = json.loads(DESIGN.read_text())
    if case not in CASES:
        raise ValueError("Unknown invented sampling case")
    if case in ("information-loss", "constant"):
        rename = {
            "invented-evaluation-low": "invented-evaluation-02",
            "invented-evaluation-failure": "invented-evaluation-03",
        }
        design["allocation"] = {
            rename.get(key, key): value for key, value in design["allocation"].items()
        }
    package = base_package()
    template = package["participants"][0]
    package["provenance"] = (
        f"Invented OT-055 {case} software control; allocation exercises code only, "
        "not blinded empirical performance; no participant data or T1D kinetic inference"
    )
    package["participants"] = []
    rows = []
    for participant, allocation in design["allocation"].items():
        if development_only and allocation != "development":
            continue
        person = deepcopy(template)
        person.update(id=participant, allocation=allocation)
        package["participants"].append(person)
        low = participant.endswith("low")
        if case == "constant":
            baseline, followup = [0.2] * 6, [0.3] * 6
        elif case in ("information-loss", "incomplete"):
            baseline = [0.025] * 6 if low else [0.2] * 6
            followup = [0.0275] * 6 if low else [0.2, 0.28, 0.36, 0.195, 0.19, 0.185]
        else:
            baseline = [0.025] * 6 if low else [0.2, 0.8, 0.4, 0.3, 0.25, 0.2]
            followup = [1.1 * value for value in baseline]
        for visit_index, visit in enumerate(person["visits"]):
            for index, time in enumerate(design["full_times_minutes"]):
                censored = participant.endswith("failure") and visit_index == 1 and time == 60
                glucose = 5.5 + (1.0 if visit_index == 1 and case != "constant" else 0) + index / 5
                rows.append(
                    [
                        participant,
                        visit["id"],
                        visit["challenge_id"],
                        time,
                        glucose,
                        "observed",
                        "" if censored else (baseline if visit_index == 0 else followup)[index],
                        "below_loq" if censored else "observed",
                    ]
                )
    return package, csv_bytes(rows), design


def export_example(output, development_only=False, case="steep-response"):
    package, raw, design = example(development_only, case)
    output = fresh(output)
    dump(output / "package.json", package)
    (output / "observations.csv").write_bytes(raw)
    dump(output / "sampling-design.json", design)
    dump(output / "settings.json", analysis_settings())
    return output
