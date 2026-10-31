"""Controlled forward stand-in and independent affine-input two-pool oracle.

This is not native M4 qualification. Only M4 admission/reconstruction is replaced;
the connected bridge and downstream MMTT/sampling arithmetic remain unmodified.
The central/peripheral affine solution uses the published two-exponential kernel,
without importing either the forward solver or inverse estimator.
"""

import contextlib
import math
import shutil
from pathlib import Path
from unittest.mock import patch

from experiments.catalogue.storage import load_sealed, seal
from experiments.shared_services import execution, routes, store

KINETICS = {"k1": 0.037, "k2": 0.031, "k3": 0.052, "volume_l_kg": 0.0655}
SOURCES = ("dalla_man", "ultradian")
SCENARIOS = ("fasting", "gastric_load_15g")
SLOPES = {
    "dalla_man": {"fasting": 0.0, "gastric_load_15g": 0.01},
    "ultradian": {"fasting": 0.002, "gastric_load_15g": 0.012},
}


def affine_state(time, slope, basal=1.0):
    k1, k2, k3 = (KINETICS[key] for key in ("k1", "k2", "k3"))
    central = basal / k3
    peripheral = k1 / k2 * central
    if time == 0:
        return [central, peripheral, 0.0, 0.0]
    total = k1 + k2 + k3
    gap = math.sqrt(total * total - 4 * k2 * k3)
    alpha, beta = (total + gap) / 2, (total - gap) / 2

    def integrated_ramp(rate):
        return time / rate + math.expm1(-rate * time) / rate**2

    a, b = integrated_ramp(alpha), integrated_ramp(beta)
    q1 = central + slope * ((alpha - k2) * a + (k2 - beta) * b) / gap
    q2 = peripheral + slope * k1 * (b - a) / gap
    delivered = basal * time + slope * time * time / 2
    eliminated = central + peripheral + delivered - q1 - q2
    return [q1, q2, eliminated, delivered]


def forward_archive(path, *, weight=70.0, basal=1.0):
    path = Path(path)
    path.mkdir()
    times = [index / 4 for index in range(961)]
    parameters = {"BW": weight, "Vg": 1.0, "Vi": 1.0}
    report = {
        "status": "completed",
        "passed": True,
        "configuration": {"scenarios": list(SCENARIOS)},
        "reference": {"accepted": True},
        "common_controls": {"passed": True},
        "sources": {},
        "fixture_scope": "controlled affine source, not native M4 execution",
    }

    def write(name, value):
        target = path / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(store.encoded(value))

    write("reference/primary/native.json", {"parameters": parameters})
    initial = affine_state(0, 0, basal)
    for source in SOURCES:
        write(f"children/{source}/primary/native.json", {"parameters": parameters})
        selected = {"accepted": True, "scenarios": {}, "curves": {}}
        for scene in SCENARIOS:
            slope = SLOPES[source][scene]
            rates = [basal + slope * time for time in times]
            states = [affine_state(time, slope, basal) for time in times]
            glucose = [99.0] * len(times)
            insulin = [10.0] * len(times)
            parent = {
                "status": "completed",
                "failure": None,
                "mode": "candidate",
                "solver": {"name": "reference"},
                "times": times,
                "baseline": {"Sb_pmol_kg_min": basal},
                "source_rates": [[rate, rate * 0.5] for rate in rates],
                "states": [[0, 0, 0, g, 0, i] for g, i in zip(glucose, insulin, strict=True)],
            }
            observer = {
                "status": "completed",
                "boundary": {
                    "times": times,
                    "signal": "pancreatic",
                    "step_min": 0.25,
                    "appearance_scale": 1,
                    "parameters": KINETICS,
                    "basal_pmol_kg_min": basal,
                    "initial": initial,
                    "forcing": {
                        "edges": times,
                        "left": rates[:-1],
                        "right": rates[1:],
                        "units": "pmol/(kg min)",
                    },
                },
                "states": {"reference": states},
            }
            write(f"children/{source}/primary/{scene}/candidate-reference.json", parent)
            write(f"children/{source}/observations/primary/cases/{scene}--candidate.json", observer)
            selected["scenarios"][scene] = {"accepted": True}
            selected["curves"][scene] = {
                "candidate": {
                    "times": times,
                    "glucose": glucose,
                    "insulin": insulin,
                    "cpeptide": [state[0] / KINETICS["volume_l_kg"] for state in states],
                }
            }
        report["sources"][source] = selected
    write("report.json", report)
    (path / "report.md").write_text("# Controlled affine forward fixture\n")
    seal(path)
    return path


@contextlib.contextmanager
def controlled_forward():
    """Replace only the M4 boundary; real sampling runs/readers are untouched."""
    native_result = routes.native_result
    reconstruct = execution.reconstruct

    def result(archive, descriptor, plan):
        if descriptor["task"] != "m4-study-installed":
            return native_result(archive, descriptor, plan)
        load_sealed(archive)
        return {
            "payload": "native",
            "execution_status": "completed",
            "completeness": "complete",
            "slot_statuses": dict.fromkeys(descriptor["boundary"]["planned_slots"], "complete"),
            "reconstruction": "unchecked",
            "scientific_evidence": "synthetic-only",
            "report_sha256": {
                name: store.digest((archive / name).read_bytes())
                for name in ("report.json", "report.md")
            },
        }

    def read(project, attempt, output, *, allow_failed=False, backend=None):
        descriptor, _ = project.plans[project.attempts[attempt]["plan"]]
        if descriptor["task"] != "m4-study-installed":
            return reconstruct(project, attempt, output, allow_failed=allow_failed, backend=backend)
        record, evidence = project.finishes[attempt]
        archive = evidence / "native"
        output = Path(output)
        output.mkdir()
        for name in record["result"]["report_sha256"]:
            shutil.copyfile(archive / name, output / name)
        if project.writable:
            project.append(
                "reconstruct",
                {
                    "attempt": attempt,
                    "status": "verified",
                    "reader": descriptor["reader"],
                    "report_sha256": record["result"]["report_sha256"],
                },
            )
            project.inspect()
        return {
            "reconstruction": "verified",
            "completeness": record["result"]["completeness"],
            "report_sha256": record["result"]["report_sha256"],
        }

    with (
        patch.object(routes, "native_result", side_effect=result),
        patch.object(execution, "native_result", side_effect=result),
        patch.object(execution, "reconstruct", side_effect=read),
    ):
        yield


def finish_forward(project, plan, *, retry_of=None):
    attempt, work = execution.begin(project, plan, retry_of=retry_of)
    forward_archive(work / "native")
    execution.finish(
        project,
        attempt,
        work,
        {"status": "completed", "remaining_owned_processes": [], "fixture": "controlled forward"},
    )
    return attempt
