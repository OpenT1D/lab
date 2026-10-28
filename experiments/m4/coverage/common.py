"""Frozen BC-014 design, source inventory and artifact helpers."""

import hashlib
import json
from pathlib import Path

from experiments.m4.profile_likelihood import common as profile_common
from experiments.m4.profile_likelihood.common import digest as digest
from experiments.m4.profile_likelihood.common import dump as dump
from experiments.m4.profile_likelihood.common import file_hashes as file_hashes
from experiments.m4.profile_likelihood.common import read as read
from experiments.m4.profile_likelihood.common import verify_files as verify_files

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
VERSION = "bc014-synthetic-coverage/1"
PROTOCOL_SHA256 = "49dee210bbab249afc43804f7a07a3144c82ae3f30b2f63bdd1c2a7004d3027c"
GROUPS = ("interior", "gain_boundary")
SOURCES = ("common.py", "worker.py", "report.py", "plot.py", "run.py", "test_numerical.py")
REUSED = tuple(
    dict.fromkeys(
        (
            "experiments/m4/profile_likelihood/protocol.json",
            *("experiments/m4/profile_likelihood/" + n for n in profile_common.SOURCES),
            *profile_common.REUSED,
        )
    )
)


def validate(protocol):
    raw = json.dumps(protocol, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
    if hashlib.sha256(raw).hexdigest() != PROTOCOL_SHA256:
        raise ValueError("BC-014/1 is frozen; changes require a versioned amendment")


def observation_specs(protocol):
    return [
        {"group": group, "seed": seed, "id": f"{group}-{seed}"}
        for group in GROUPS
        for design in [protocol["design"][group]]
        for seed in range(
            design["seeds"]["first"], design["seeds"]["first"] + design["seeds"]["count"]
        )
    ]


def specifications(protocol):
    return [
        {**obs, "design": design, "id": f"{obs['id']}-{design}"}
        for obs in observation_specs(protocol)
        for design in protocol["design"][obs["group"]]["observation_designs"]
    ]


def numerical_files(protocol):
    return (
        {"worker.json", "verification.json"}
        | {"observations/" + spec["id"] + ".json" for spec in observation_specs(protocol)}
        | {"cases/" + spec["id"] + ".json" for spec in specifications(protocol)}
    )


def required_files(protocol):
    numeric = numerical_files(protocol)
    return (
        {
            "protocol.json",
            "parent-profile.json",
            "parent-volume.json",
            "parent-joint.json",
            "uv.lock",
            "pyproject.toml",
            "worker.log",
            "repeat.log",
        }
        | {"source-" + name for name in SOURCES}
        | {"source-" + name.replace("/", "__") for name in REUSED}
        | numeric
        | {"repeat/" + name for name in numeric}
    )


def adapted_profile(protocol):
    """Change only the dataset label required by the inherited Problem API."""
    profile_common.validate(protocol)
    result = json.loads(json.dumps(protocol))
    result["observation"]["data_cases"] = ["assessment"]
    return result
