"""Deterministic native-observation bridge; no physiological or inverse execution."""

import copy
import csv
import io
import math
from decimal import Decimal, localcontext

from experiments.catalogue.storage import decode
from experiments.m3.researcher.intake import read_regular
from experiments.observation_analysis.fixtures import package as example_package
from experiments.observation_analysis.intake import assess
from experiments.observation_analysis.observations import COLUMNS

from .store import digest, encoded, read, require


def numeric(value, *, positive=False):
    require(type(value) in (int, float) and math.isfinite(value), "Finite bridge number required")
    require(value > 0 if positive else value >= 0, "Invalid bridge number")
    return value


def decimal_area(times, values):
    """Independent finite-interpolant amount, without Forcing or inverse helpers."""
    require(len(times) == len(values) and len(times) >= 2, "Complete area support required")
    with localcontext() as context:
        context.prec = 50
        total = Decimal(0)
        for a, b, left, right in zip(times[:-1], times[1:], values[:-1], values[1:], strict=True):
            numeric(a)
            numeric(b)
            numeric(left)
            numeric(right)
            require(b > a, "Area times must increase")
            total += (
                (Decimal(str(b)) - Decimal(str(a))) * (Decimal(str(left)) + Decimal(str(right))) / 2
            )
        return total


def csv_bytes(rows):
    stream = io.StringIO(newline="")
    writer = csv.writer(stream, lineterminator="\n")
    writer.writerow(COLUMNS)
    writer.writerows(rows)
    return stream.getvalue().encode()


def generated(definition, archive):
    """Consume fixed primary/reference/candidate paths after native verification."""
    p = definition["protocol"]
    report = read(archive / "report.json")
    require(
        report.get("passed") is True
        and report["reference"]["accepted"] is True
        and report["common_controls"]["passed"] is True,
        "Complete accepted forward reference and controls required",
    )
    require(
        report["configuration"]["scenarios"] == [p["scenarios"][v] for v in ("before", "after")]
        and list(report["sources"]) == sorted(p["sources"]),
        "Forward source/scenario roster differs",
    )
    sources = {}

    def source_file(name):
        path = archive / name
        raw = read_regular(path, 16 * 1024 * 1024, "fixed bridge parent artifact")
        sources[name] = digest(raw)
        return decode(raw)

    native = source_file("reference/primary/native.json")
    weight = numeric(native["parameters"]["BW"], positive=True)
    glucose_volume = numeric(native["parameters"]["Vg"], positive=True)
    kinetics = p["kinetics"]
    volume = weight * kinetics["volume_l_kg"]
    times = [i / 4 for i in range(961)]
    observed_times = times[:481]
    require(times[0] == 0 and times[-1] == 240 and observed_times[-1] == 120, "Window differs")
    people, rows, truth = [], [], {}
    template = example_package()["participants"][0]
    for person, source in p["case_sources"].items():
        saved = report["sources"][source]
        require(saved["accepted"] is True, "Entire forward source acceptance required")
        local_native = source_file(f"children/{source}/primary/native.json")
        require(local_native["parameters"] == native["parameters"], "Shared native profile differs")
        metadata = copy.deepcopy(template)
        metadata.update(id=person, allocation=p["allocation"][person])
        metadata["context"].update(
            weight_kg=weight,
            population="Synthetic source-method case using adult#001; not a person/cohort",
            renal_context="Fixed nominal kinetics; no renal or human calibration",
        )
        truth[person] = {}
        for visit in metadata["visits"]:
            identity = visit["id"]
            scenario = p["scenarios"][identity]
            visit.update(
                protocol="Connected synthetic study: original 0–120 prefix of 0–240 min",
                meal="Fasting"
                if identity == "before"
                else "Initial gastric amount 15 g; not timed meal",
                medication_context="Retained native parent context; no treatment inference",
                assay=copy.deepcopy(p["assay"]),
            )
            require(saved["scenarios"][scenario]["accepted"] is True, "Forward scenario rejected")
            parent = source_file(f"children/{source}/primary/{scenario}/candidate-reference.json")
            observation = source_file(
                f"children/{source}/observations/primary/cases/{scenario}--candidate.json"
            )
            require(
                parent["status"] == observation["status"] == "completed"
                and parent["failure"] is None
                and parent["mode"] == "candidate"
                and parent["solver"]["name"] == "reference"
                and parent["times"] == times,
                "Incomplete or wrong forward trajectory",
            )
            require(
                len(parent["source_rates"]) == len(parent["states"]) == len(times)
                and all(len(row) == 2 for row in parent["source_rates"]),
                "Complete pancreatic rate/state grid required",
            )
            rates = [numeric(row[0]) for row in parent["source_rates"]]
            boundary = observation["boundary"]
            basal = numeric(parent["baseline"]["Sb_pmol_kg_min"])
            initial = [basal / kinetics["k3"], 0, 0, 0]
            initial[1] = kinetics["k1"] * initial[0] / kinetics["k2"]
            require(
                boundary["times"] == times
                and boundary["signal"] == "pancreatic"
                and boundary["step_min"] == 0.25
                and boundary["appearance_scale"] == 1
                and boundary["parameters"] == kinetics
                and boundary["basal_pmol_kg_min"] == basal
                and boundary["initial"] == initial
                and boundary["forcing"]
                == {
                    "edges": times,
                    "left": rates[:-1],
                    "right": rates[1:],
                    "units": "pmol/(kg min)",
                },
                "Pancreatic inlet, units, basal, kinetics or initial inventories differ",
            )
            states = observation["states"]["reference"]
            require(
                len(states) == len(times) and all(len(row) == 4 for row in states),
                "Complete observer state grid required",
            )
            for state in states:
                for value in state:
                    numeric(value)
                require(
                    abs(sum(state[:3]) - sum(initial[:2]) - state[3])
                    <= p["criteria"]["observer_mass_error_pmol_kg"],
                    "Observer mass accounting differs",
                )
            require(states[0] == initial, "Observer initial state differs")
            cp = [state[0] / kinetics["volume_l_kg"] for state in states]
            glucose = [numeric(state[3]) / glucose_volume for state in parent["states"]]
            require(
                saved["curves"][scenario]["candidate"]
                == {
                    "times": times,
                    "glucose": glucose,
                    "cpeptide": cp,
                    "insulin": [
                        state[5] / native["parameters"]["Vi"] for state in parent["states"]
                    ],
                },
                "Selected observer/parent report paths differ",
            )
            per_kg = decimal_area(observed_times, rates[:481])
            require(
                abs(float(per_kg) - states[480][3]) <= p["criteria"]["observer_mass_error_pmol_kg"],
                "Prefix input accounting differs",
            )
            cp_area = decimal_area(observed_times, cp[:481])
            truth[person][identity] = {
                "known_total_pmol": float(per_kg * Decimal(str(weight))),
                "known_total_decimal_pmol": str(per_kg * Decimal(str(weight))),
                "cpeptide_auc_pmol_min_l": float(cp_area),
                "cpeptide_auc_nmol_min_l": float(cp_area / 1000),
                "initial_cpeptide_pmol_l": cp[0],
                "parent_240min_total_pmol": float(
                    decimal_area(times, rates) * Decimal(str(weight))
                ),
                "initial_amounts_pmol_kg": initial[:2],
            }
            for i, time in enumerate(observed_times):
                missing = (
                    definition["observation_case"] == "missing-evaluation"
                    and person == "synthetic-ultradian"
                    and identity == "after"
                    and time == 60
                )
                rows.append(
                    [
                        person,
                        identity,
                        visit["challenge_id"],
                        time,
                        glucose[i] / p["glucose_mg_dl_per_mmol_l"],
                        "observed",
                        "" if missing else cp[i] / p["cpeptide_pmol_l_per_nmol_l"],
                        "missing" if missing else "observed",
                    ]
                )
        truth[person]["paired_change_pmol"] = (
            truth[person]["after"]["known_total_pmol"] - truth[person]["before"]["known_total_pmol"]
        )
        people.append(metadata)
    package = example_package()
    package.update(
        provenance="Accepted M4 source outputs; noiseless synthetic cases, not people",
        participants=people,
    )
    settings = {
        "schema": "opent1d.observation-analysis-settings/1",
        "visit_order": ["before", "after"],
        "uncertainty": copy.deepcopy(p["uncertainty"]),
        "variants": [],
    }
    for name in p["variants"]:
        settings["variants"].append(
            {
                "id": name,
                "rationale": "Predeclared connected-study engineering control: " + name,
                "k1_per_min": kinetics["k1"],
                "k2_per_min": kinetics["k2"],
                "k3_per_min": kinetics["k3"] * (1.2 if name == "k3-120" else 1),
                "volume_l": volume * (1.2 if name == "volume-120" else 1),
                "initial_peripheral_factor": 0.75 if name == "peripheral-075" else 1,
            }
        )
    design = {
        "schema": "opent1d.mmtt-sampling-design/1",
        "scope": "synthetic-preparation",
        "window_minutes": [0, 120],
        "allocation": copy.deepcopy(p["allocation"]),
        "selection_participants": ["synthetic-dalla-man"],
        "selection_rationale": (
            "1/15-minute engineering subsets fixed before forward execution; "
            "no evaluation outcome selection"
        ),
        "full_times_minutes": observed_times,
        "subsets": {
            name: list(range(0, 121, step))
            for name, step in p["schedules"].items()
            if name != "full"
        },
    }
    development = copy.deepcopy(package)
    development["participants"] = [
        person for person in people if person["allocation"] == "development"
    ]
    files = {
        "package.json": encoded(package),
        "observations.csv": csv_bytes(rows),
        "settings.json": encoded(settings),
        "design.json": encoded(design),
        "development/package.json": encoded(development),
        "development/observations.csv": csv_bytes(
            [row for row in rows if row[0] == "synthetic-dalla-man"]
        ),
    }
    raw_dev = {name: files["development/" + name] for name in ("package.json", "observations.csv")}
    files["development/import.json"] = encoded(assess(raw_dev))
    manifest = {
        "schema": "opent1d.connected-bridge/1",
        "protocol": p["id"],
        "observation_case": definition["observation_case"],
        "body_weight_kg": weight,
        "whole_body_volume_l": volume,
        "window_min": [0, 120],
        "parent_window_min": [0, 240],
        "source_artifacts_sha256": sources,
        "truth": truth,
        "assumptions": (
            "Noiseless observations; positive engineering perturbations; "
            "source-method split, not people"
        ),
    }
    files["bridge.json"] = encoded(manifest)
    return files
