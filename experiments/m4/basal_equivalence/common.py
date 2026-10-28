"""Frozen task and deterministic, source-free search decisions."""

import hashlib
import json
import math
from pathlib import Path

from experiments.m4.causal_secretion.common import (
    BC008_FILE_SHA256,
    baseline_context,
    declaration,
    reference,
    sha256,
)
from experiments.m4.feedback.report import outcomes
from experiments.m4.paired_kinetics.common import read

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
VERSION = "m4-basal-equivalence/1"
PROTOCOL_SHA256 = "b18e90a1868b996c198b51a68931eb3af42f6b854ba7fceb3d60336211d409c3"
REFERENCE_ADAPTER_DECLARATION_SHA256 = (
    "f43cf983496cd6e271e46301db77f1bd09e5e5742befc5a466bd48228fc373aa"
)
SLOTS = ("reference_adapter", "synthetic_variant")
SOURCES = ("protocol.json", "common.py", "worker.py", "report.py", "run.py")
REUSED = (
    "experiments/m4/causal_secretion/common.py",
    "experiments/m4/causal_secretion/coupled.py",
    "experiments/m4/causal_secretion/report.py",
    "experiments/m4/feedback/contract.py",
    "experiments/m4/feedback/report.py",
    "experiments/m4/feedback/preflight.py",
    "experiments/m4/feedback/source_oracle.py",
    "experiments/m4/feedback/coupled.py",
    "experiments/m4/kinetic_inlet/native.py",
    "experiments/m4/paired_kinetics/common.py",
    "experiments/m4/paired_kinetics/report.py",
)


def protocol(value, bc):
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
    if hashlib.sha256(encoded).hexdigest() != PROTOCOL_SHA256:
        raise ValueError("M4 basal-equivalence protocol is frozen")
    if (
        value.get("schema") != "m4-basal-equivalence-protocol/1"
        or value.get("id") != "M4-BASAL-EQUIVALENCE/1"
        or value.get("reference_id") != bc["id"]
        or value.get("reference_protocol_file_sha256") != BC008_FILE_SHA256
        or value.get("source_slots") != list(SLOTS)
        or value["target"]
        != {
            "scenario": "gastric_load_30g",
            "case": "feedback_full",
            "solver": "reference",
            "metric": "auc_above_initial_mg_min_dl",
            "unit": "mg min/dL",
        }
        or value["sc_rate_multipliers_of_native_u2ss"] != [0.5, 0.625, 0.75, 0.875, 1.0]
        or value["search_solver"] != "tight"
        or value["confirmation_solver"] != "reference"
        or value["max_bisections"] != 18
    ):
        raise ValueError("Unsupported basal-equivalence task")
    return value


def context(reference_path, task_path):
    bc, native, probe, report = reference(reference_path)
    task = protocol(read(task_path), bc)
    task = {
        **task,
        "horizon_min": bc["horizon_min"],
        "sample_step_min": bc["sample_step_min"],
        "glucose_envelope_mg_dl": bc["glucose_envelope_mg_dl"],
    }
    basal, gamma = baseline_context(bc, native, probe)
    params = native["parameters"]
    parent = read(reference_path / "gastric_load_30g" / "feedback_full-reference.json")
    target = outcomes(parent["times"], parent["states"], params["Vg"])[
        "auc_above_initial_mg_min_dl"
    ]
    if not math.isfinite(target) or not report["passed"]:
        raise ValueError("Invalid BC-008 target")
    return bc, native, basal, gamma, task, target


def sc_context(basal, params, factor):
    """Change the post-zero infusion only; keep all initial states and Sb fixed."""
    if isinstance(factor, bool) or not isinstance(factor, (int, float)) or not 0 <= factor <= 1:
        raise ValueError("SC factor outside task domain")
    rate = factor * params["u2ss"]
    return {
        **basal,
        "u_sc_pmol_kg_min": rate,
        "action_insulin_u_min": rate * params["BW"] / 6000,
    }


def declared_sources(directory):
    values = {}
    for slot in SLOTS:
        if slot == SLOTS[0]:
            verify_reference_adapter(directory / f"{slot}.json")
        item = declaration(read(directory / f"{slot}.json"))
        if sha256(directory / f"{slot}.py") != item["source_sha256"]:
            raise ValueError(f"Source hash differs from {slot} declaration")
        values[slot] = item
    if values[SLOTS[0]]["model_id"] == values[SLOTS[1]]["model_id"]:
        raise ValueError("The two comparison model IDs must differ")
    return values


def verify_reference_adapter(path):
    if sha256(path) != REFERENCE_ADAPTER_DECLARATION_SHA256:
        raise ValueError("Reference adapter must use the pinned BC-008 example declaration")


def next_step(history, target, task):
    """Return (kind, factor): grid, bisect, matched or no_solution."""
    grid = task["sc_rate_multipliers_of_native_u2ss"]
    if len(history) < len(grid):
        return "grid", grid[len(history)]
    points = sorted((item["factor"], item["auc"]) for item in history)
    if len({factor for factor, _ in points}) != len(points) or any(
        not math.isfinite(auc) for _, auc in points
    ):
        raise ValueError("Invalid or duplicate search observation")
    slack = task["monotonicity_slack_mg_min_dl"]
    if any(left[1] < right[1] - slack for left, right in zip(points, points[1:])):
        return "nonmonotonic", None
    best = min(history, key=lambda item: abs(item["auc"] - target))
    if abs(best["auc"] - target) <= task["auc_match_tolerance_mg_min_dl"]:
        return "matched", best["factor"]
    if target > points[0][1] or target < points[-1][1]:
        return "unbracketed", None
    if len(history) - len(grid) >= task["max_bisections"]:
        return "resolution_limit", None
    for left, right in zip(points, points[1:]):
        if left[1] >= target >= right[1]:
            return "bisect", (left[0] + right[0]) / 2
    return "unbracketed", None


def no_solution_confirmation_factors(history, target, task):
    """Confirm the full prespecified grid and any final bisection bracket."""
    decision, _ = next_step(history, target, task)
    if decision not in ("nonmonotonic", "unbracketed", "resolution_limit"):
        raise ValueError("Reference grid confirmation requires a no-solution decision")
    factors = list(task["sc_rate_multipliers_of_native_u2ss"])
    if decision == "resolution_limit":
        points = sorted((item["factor"], item["auc"]) for item in history)
        for left, right in zip(points, points[1:]):
            if left[1] >= target >= right[1]:
                factors.extend((left[0], right[0]))
                break
    return list(dict.fromkeys(factors))
