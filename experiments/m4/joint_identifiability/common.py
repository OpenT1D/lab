"""Frozen BC-011 inventory and standard-library artifact helpers."""

import hashlib
import itertools
import json
from pathlib import Path

from experiments.m4.paired_kinetics.common import digest as digest
from experiments.m4.paired_kinetics.common import dump as dump
from experiments.m4.paired_kinetics.common import file_hashes as file_hashes
from experiments.m4.paired_kinetics.common import read as read
from experiments.m4.paired_kinetics.common import verify_files as verify_files

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
VERSION = "bc011-joint-recovery/1"
SOURCES = (
    "common.py",
    "model.py",
    "verify.py",
    "inference.py",
    "worker.py",
    "report.py",
    "run.py",
    "plot.py",
    "test_numerical.py",
)
REUSED = (
    "experiments/m4/feedback/protocol.json",
    "experiments/m4/feedback/contract.py",
    "experiments/m4/feedback/secretion.py",
    "experiments/m4/feedback/coupled.py",
    "experiments/m4/feedback_observation/protocol.json",
    "experiments/m4/kinetic_inlet/native.py",
    "experiments/m4/kinetic_inlet/protocol.json",
    "experiments/m4/kinetic_inlet/forcing.py",
    "experiments/m4/c_peptide/model.py",
    "experiments/m4/paired_kinetics/oracle.py",
    "experiments/m4/paired_kinetics/common.py",
    "experiments/m4/paired_observation/run.py",
    "experiments/m4/paired_observation/contract.py",
)


def validate(p):
    data = json.dumps(p, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
    if hashlib.sha256(data).hexdigest() != (
        "0ff08aebe9d7d78219843f1b9c9e053564bfddb213109fee8f57ceab916bc0b5"
    ):
        raise ValueError("BC-011/2 is frozen; changed design requires an amendment")


def specifications(p):
    return [
        {"id": f"{r}-{m}-{s}-{d}", "regime": r, "modality": m, "step": s, "data": d}
        for r, m, s, d in itertools.product(
            p["inference"]["regimes"],
            p["observation"]["modalities"],
            p["observation"]["sample_steps_min"],
            p["observation"]["data_cases"],
        )
    ]


def active_parameters(spec):
    if spec["regime"] == "known_kinetics":
        return [0]
    return [0, 1, 2] if spec["modality"] == "GIC" else [0, 1]


def forward_check_specifications(p):
    """Required forward gate names mapped to their frozen limits."""
    criteria = p["criteria"]
    result = {}
    for name in ("truth", "lower_corner", "upper_corner"):
        result[name + "/fasting_derivative"] = criteria["baseline_derivative_error"]
        for solver in p["solvers"]:
            prefix = name + "/" + solver + "/"
            result[prefix + "output"] = criteria["solver_scaled_output_error"]
            for key in ("insulin_pmol_kg", "cpeptide_pmol_kg", "paired_pancreatic_ledgers_pmol_kg"):
                result[prefix + key] = criteria["mass_balance_error_pmol_kg"]
    result["original_BC008_GI"] = criteria["parent_GI_scaled_error"]
    for scale in ("0.5", "2.0"):
        result["gain_beta_K_symmetry/" + scale] = criteria["exact_symmetry_scaled_error"]
    for scale in ("0.5", "1.5"):
        result["passive_k3/" + scale] = criteria["passive_GI_scaled_error"]
    result["passive_k3/equation_locality"] = 0.0
    result["independent_cpeptide"] = criteria["cp_oracle_error_pmol_l"]
    return result


def numerical_files(p):
    return {"worker.json", "verification.json", "observations.json", "sensitivity.json"} | {
        f"cases/{s['id']}.json" for s in specifications(p)
    }


def required_files(p):
    numeric = numerical_files(p)
    return (
        {"protocol.json", "uv.lock", "pyproject.toml", "worker.log", "repeat.log"}
        | {"source-" + n for n in SOURCES}
        | {"source-" + n.replace("/", "__") for n in REUSED}
        | numeric
        | {"repeat/" + n for n in numeric}
    )
