"""Frozen BC-010 conventions and file inventory; standard library only."""

import hashlib
import json
from pathlib import Path

from experiments.m4.hepatic.common import case_specs, key
from experiments.m4.paired_kinetics.common import digest as digest
from experiments.m4.paired_kinetics.common import dump as dump
from experiments.m4.paired_kinetics.common import file_hashes as file_hashes
from experiments.m4.paired_kinetics.common import read as read
from experiments.m4.paired_kinetics.common import verify_files as verify_files

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
VERSION = "bc010-feedback-observation/1"
SOURCES = (
    "common.py",
    "adapter.py",
    "worker.py",
    "report.py",
    "run.py",
    "plot.py",
    "test_numerical.py",
)
REUSED = (
    "experiments/m4/c_peptide/model.py",
    "experiments/m4/c_peptide/reference.py",
    "experiments/m4/c_peptide/protocol.json",
    "experiments/m4/paired_kinetics/oracle.py",
    "experiments/m4/paired_kinetics/common.py",
    "experiments/m4/paired_kinetics/report.py",
    "experiments/m4/paired_observation/run.py",
    "experiments/m4/paired_observation/contract.py",
    "experiments/m4/kinetic_inlet/forcing.py",
)


def validate(p):
    raw = json.dumps(p, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
    if (
        hashlib.sha256(raw).hexdigest()
        != "fb7b08297d78a78846c900785b5497250ea81996550dfe328d02bd5ae23f064e"
    ):
        raise ValueError("BC-010 is frozen; changes require a versioned amendment")


def labels(directory):
    parent = Path(directory) / "hepatic"
    hp, fp = read(parent / "protocol.json"), read(parent / "parent.json")
    return [key(s, c, v) for s, c, v in case_specs(hp, fp)]


def source(directory, label, solver="reference"):
    return read(Path(directory) / "hepatic" / "cases" / f"{label}--{solver}.json")


def numerical_files(names):
    return {"worker.json"} | {f"cases/{name}.json" for name in names}


def required_files(names):
    numeric = numerical_files(names)
    return (
        {
            "protocol.json",
            "hepatic/manifest.json",
            "worker.log",
            "repeat.log",
            "uv.lock",
            "pyproject.toml",
        }
        | {"source-" + name for name in SOURCES}
        | {"source-" + name.replace("/", "__") for name in REUSED}
        | numeric
        | {"repeat/" + name for name in numeric}
    )
