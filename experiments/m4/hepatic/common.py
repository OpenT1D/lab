"""Frozen BC-009 specification and artifact inventory; standard library only."""

import hashlib
import json
from pathlib import Path

from experiments.m4.feedback.contract import validate as validate_parent
from experiments.m4.paired_kinetics.common import (
    digest as digest,
)
from experiments.m4.paired_kinetics.common import (
    dump as dump,
)
from experiments.m4.paired_kinetics.common import (
    file_hashes as file_hashes,
)
from experiments.m4.paired_kinetics.common import (
    read as read,
)
from experiments.m4.paired_kinetics.common import (
    verify_files as verify_files,
)

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
VERSION = "bc009-hepatic/1"
SOURCES = (
    "common.py",
    "model.py",
    "numerical.py",
    "worker.py",
    "report.py",
    "run.py",
    "plot.py",
    "test_numerical.py",
)
REUSED = (
    "experiments/m4/feedback/contract.py",
    "experiments/m4/feedback/secretion.py",
    "experiments/m4/feedback/source_oracle.py",
    "experiments/m4/feedback/verify_source.py",
    "experiments/m4/feedback/coupled.py",
    "experiments/m4/feedback/preflight.py",
    "experiments/m4/feedback/common.py",
    "experiments/m4/feedback/report.py",
    "experiments/m4/feedback/source-cases.json",
    "experiments/m4/kinetic_inlet/native.py",
    "experiments/m4/kinetic_inlet/forcing.py",
    "experiments/m4/kinetic_inlet/protocol.json",
    "experiments/m4/paired_kinetics/common.py",
    "experiments/m4/paired_kinetics/report.py",
    "experiments/m4/paired_observation/run.py",
    "experiments/m4/paired_observation/contract.py",
)


def validate(p, parent):
    encoded = json.dumps(p, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
    if (
        hashlib.sha256(encoded).hexdigest()
        != "be344cf0f8a2cca75b00561a4f1d4ecf3727a48bbb74765a007112e4b54b5314"
    ):
        raise ValueError("BC-009 is frozen; changes require a versioned amendment")
    validate_parent(parent)
    if parent["id"] != p["parent_id"]:
        raise ValueError("Wrong parent protocol")


def case_specs(p, parent):
    for scenario in parent["scenarios"]:
        for case in parent["cases"]:
            if case["id"] not in p["cases"]:
                continue
            for variant in p["variants"]:
                yield scenario, case, variant


def key(scenario, case, variant):
    return f"{scenario['id']}--{case['id']}--{variant['id']}"


def numerical_files(p, parent):
    names = {
        "native.json",
        "preflight.json",
        "source-check/source-reference.json",
        "source-check/source-assessment.json",
    }
    names.update(
        f"cases/{key(s, c, v)}--{solver['name']}.json"
        for s, c, v in case_specs(p, parent)
        for solver in parent["solvers"]
    )
    names.update(f"parent/{s}--{c}.json" for s in p["scenarios"] for c in p["cases"])
    return names


def required_files(p, parent):
    files = {
        "protocol.json",
        "parent.json",
        "sources.json",
        "uv.lock",
        "pyproject.toml",
        "worker.log",
        "repeat.log",
    }
    files.update("source-" + name for name in SOURCES)
    files.update("source-" + name.replace("/", "__") for name in REUSED)
    for prefix in ("", "repeat/"):
        files.update(
            prefix + name
            for name in (
                "protocol.json",
                "parent.json",
                "source-check/protocol.json",
                "source-check/source-cases.json",
            )
        )
    numerical = numerical_files(p, parent)
    return files | numerical | {"repeat/" + name for name in numerical}
