"""BC-008 archive inventory; no numerical runtime needed."""

import hashlib
import json
from pathlib import Path

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
VERSION = "bc008-feedback/1"


def validate_source_cases(spec):
    frozen = "3be51344deb00db458654f08c408fca299ac702d56aefd37d1d7d896d86fe8a2"
    encoded = json.dumps(spec, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
    if hashlib.sha256(encoded).hexdigest() != frozen:
        raise ValueError("Source verification fixtures were frozen before execution")


SOURCES = (
    "contract.py",
    "secretion.py",
    "source_oracle.py",
    "verify_source.py",
    "coupled.py",
    "worker.py",
    "common.py",
    "run.py",
    "report.py",
    "plot.py",
    "test_numerical.py",
    "preflight.py",
)
REUSED = (
    "experiments/m4/kinetic_inlet/native.py",
    "experiments/m4/kinetic_inlet/forcing.py",
    "experiments/m4/kinetic_inlet/protocol.json",
    "experiments/m4/paired_kinetics/common.py",
    "experiments/m4/paired_kinetics/report.py",
    "experiments/m4/paired_observation/run.py",
    "experiments/m4/paired_observation/contract.py",
)


def numerical_files(p):
    files = {
        "source-reference.json",
        "source-assessment.json",
        "probe.json",
        "preflight.json",
        "native.json",
    }
    for scenario in p["scenarios"]:
        names = {"native-padded.json", "native-class.json"}
        for case in [c["id"] for c in p["cases"]] + ["equal-arrival"]:
            names.update(f"{case}-{s['name']}.json" for s in p["solvers"])
        names.update(f"replay-{step}.json" for step in p["refinement"]["replay_sample_steps_min"])
        files.update(scenario["id"] + "/" + name for name in names)
    return files


def required_files(p):
    base = {
        "protocol.json",
        "source-cases.json",
        "sources.json",
        "uv.lock",
        "pyproject.toml",
        "worker.log",
        "repeat.log",
    }
    base.update("source-" + name for name in SOURCES)
    base.update("source-" + name.replace("/", "__") for name in REUSED)
    numerics = numerical_files(p)
    return (
        base
        | numerics
        | {"repeat/" + name for name in numerics}
        | {"repeat/protocol.json", "repeat/source-cases.json"}
    )
