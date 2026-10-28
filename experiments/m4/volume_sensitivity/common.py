"""Frozen BC-012 design and explicit source/analysis inventory."""

import hashlib
import itertools
import json
from pathlib import Path

from experiments.m4.joint_identifiability import common as parent_common
from experiments.m4.joint_identifiability.common import digest as digest
from experiments.m4.joint_identifiability.common import dump as dump
from experiments.m4.joint_identifiability.common import file_hashes as file_hashes
from experiments.m4.joint_identifiability.common import read as read
from experiments.m4.joint_identifiability.common import verify_files as verify_files

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
VERSION = "bc012-volume-sensitivity/1"
NAMES = ("evoked_gain", "m4_scale", "k3_scale", "volume_scale")
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
REUSED = tuple(
    dict.fromkeys(
        (
            "experiments/m4/joint_identifiability/protocol.json",
            *("experiments/m4/joint_identifiability/" + n for n in parent_common.SOURCES),
            *parent_common.REUSED,
        )
    )
)
VOLUME = {"correct": 1.0, "low": 0.8, "high": 1.2}
VOLUME_CHECKS = (
    "correct_volume_parent_error",
    "volume_state_error",
    "volume_GI_error",
    "volume_scaling_relative_error",
    "analytic_log_volume_scaled_error",
    "basal_product_relative_error",
    "solver_scaled_output_error",
)


def validate(p):
    raw = json.dumps(p, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
    if (
        hashlib.sha256(raw).hexdigest()
        != "b24e81fd1c5538024499719bd918884d827efa16a4602eec5f4b9d3a5125c1ad"
    ):
        raise ValueError("BC-012/1 is frozen; changes need a versioned amendment")


def specifications(p):
    return [
        {
            "id": f"{r}-{a}-{s}-{d}",
            "regime": r,
            "arm": a,
            "step": s,
            "data": d,
            "modality": "GI" if a == "control" else "GIC",
        }
        for r, a, s, d in itertools.product(
            p["inference"]["regimes"],
            [*p["inference"]["volume_arms"], "control"],
            p["observation"]["sample_steps_min"],
            p["observation"]["data_cases"],
        )
    ]


def active_parameters(spec):
    result = (
        [0]
        if spec["regime"] == "known_rates"
        else ([0, 1] if spec["arm"] == "control" else [0, 1, 2])
    )
    return result + [3] if spec["arm"] == "estimated" else result


def declared_parameters(spec):
    result = [0] if spec["regime"] == "known_rates" else [0, 1, 2]
    return result + [3] if spec["arm"] in ("estimated", "control") else result


def unobservable(spec):
    if spec["arm"] != "control":
        return []
    return [3] if spec["regime"] == "known_rates" else [2, 3]


def fixed_parameters(spec):
    result = {"m4_scale": 1.0, "k3_scale": 1.0} if spec["regime"] == "known_rates" else {}
    if spec["arm"] in VOLUME:
        result["volume_scale"] = VOLUME[spec["arm"]]
    return result


def numerical_files(p):
    return {"worker.json", "verification.json", "observations.json", "sensitivity.json"} | {
        f"cases/{s['id']}.json" for s in specifications(p)
    }


def required_files(p):
    numeric = numerical_files(p)
    return (
        {"protocol.json", "parent.json", "uv.lock", "pyproject.toml", "worker.log", "repeat.log"}
        | {"source-" + n for n in SOURCES}
        | {"source-" + n.replace("/", "__") for n in REUSED}
        | numeric
        | {"repeat/" + n for n in numeric}
    )
