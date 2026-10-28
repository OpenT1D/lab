"""Six-case C-peptide composition boundary; artifact assessment uses only stdlib.

BC-010 supplies the unchanged forward-observation equations, inlet conventions,
diagnostics and numerical limits. This composition does not execute BC-010's
historical 24-case hepatic study.
"""

from pathlib import Path

from experiments.m4.feedback_observation.common import read, validate
from experiments.m4.feedback_observation.report import assess_case

SCENARIOS = ("fasting", "gastric_load_30g")
MODES = ("candidate", "host_constant_basal", "bc008_reference")
WORKER_SCHEMA = "m4-researcher-observer/1"
CASE_SCHEMA = "m4-researcher-observation/1"


def case_ids():
    return tuple(f"{scenario}--{mode}" for scenario in SCENARIOS for mode in MODES)


def split_case(case_id):
    if case_id not in case_ids():
        raise ValueError("Unknown researcher observation case")
    return case_id.split("--", 1)


def validate_parent(case_id, item, solver):
    """Bind a saved trajectory to its selected scenario, mode and solver."""
    scenario, mode = split_case(case_id)
    schema = "bc008-trajectory/1" if mode == "bc008_reference" else "m4-causal-trajectory/1"
    load = 0 if scenario == "fasting" else 30000
    if (
        item.get("schema") != schema
        or item.get("status") != "completed"
        or item.get("failure") is not None
        or not isinstance(item.get("solver"), dict)
        or item["solver"].get("name") != solver
        or item.get("load_mg") != load
        or (mode != "bc008_reference" and item.get("mode") != mode)
        or (mode == "bc008_reference" and item.get("source_active") is not True)
    ):
        raise ValueError("Mismatched or incomplete observation parent")


def parent_records(directory, case_id):
    scenario, mode = split_case(case_id)
    parent = Path(directory) / "causal"
    folder, name = (
        ("reference", "feedback_full") if mode == "bc008_reference" else ("primary", mode)
    )
    records = tuple(
        read(parent / folder / scenario / f"{name}-{solver}.json")
        for solver in ("reference", "tight")
    )
    for item, solver in zip(records, ("reference", "tight"), strict=True):
        validate_parent(case_id, item, solver)
    return records


def numerical_files():
    return {"worker.json"} | {f"cases/{case_id}.json" for case_id in case_ids()}


def validate_worker(p, worker, label):
    validate(p)
    if (
        label not in ("primary", "repeat")
        or worker.get("schema") != WORKER_SCHEMA
        or worker.get("label") != label
        or worker.get("status") != "completed"
        or worker.get("failures") != []
    ):
        raise ValueError("Incomplete or mismatched researcher observation worker")
    runtime = worker.get("runtime")
    if (
        not isinstance(runtime, dict)
        or set(runtime) != {"python", "numpy", "scipy"}
        or any(runtime[k] != p["runtime"][k] for k in ("numpy", "scipy"))
        or not isinstance(runtime["python"], str)
        or not runtime["python"].startswith(p["runtime"]["python"] + ".")
    ):
        raise ValueError("Wrong locked researcher observation runtime")


def assess(p, item, reference, tight):
    validate(p)
    case_id = item.get("id")
    _, mode = split_case(case_id)
    if item.get("schema") != CASE_SCHEMA:
        raise ValueError("Unsupported researcher observation record")
    validate_parent(case_id, reference, "reference")
    validate_parent(case_id, tight, "tight")
    # BC-010 recognizes its historical --constant_basal-- case marker. Adapt
    # only this temporary identifier so meal host controls receive the same
    # equilibrium check, without changing archived IDs or the frozen assessor.
    assessed = item.copy()
    if mode == "host_constant_basal":
        assessed["id"] = case_id.replace("--host_constant_basal", "--constant_basal--host")
    return assess_case(p, assessed, reference, tight)
