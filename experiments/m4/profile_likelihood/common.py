"""Frozen BC-013 scope, source inventory and deterministic analysis design."""

import hashlib
import itertools
import json
import math
from pathlib import Path

from experiments.m4.volume_sensitivity import common as volume_common
from experiments.m4.volume_sensitivity.common import digest as digest
from experiments.m4.volume_sensitivity.common import file_hashes as file_hashes
from experiments.m4.volume_sensitivity.common import read as read
from experiments.m4.volume_sensitivity.common import verify_files as verify_files

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
VERSION = "bc013-profile-likelihood/1"
NAMES = ("evoked_gain", "m4_scale", "k3_scale", "volume_scale")
SOURCES = (
    "common.py",
    "optimizer.py",
    "verify.py",
    "profiles.py",
    "worker.py",
    "report.py",
    "run.py",
    "plot.py",
    "test_numerical.py",
)
REUSED = tuple(
    dict.fromkeys(
        (
            "experiments/m4/volume_sensitivity/protocol.json",
            *("experiments/m4/volume_sensitivity/" + n for n in volume_common.SOURCES),
            *volume_common.REUSED,
        )
    )
)


def dump(path, value):
    """Replace a checkpoint only after complete finite JSON has been written."""
    path = Path(path)
    content = json.dumps(value, indent=2, allow_nan=False) + "\n"
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(content)
    temporary.replace(path)


def validate(p):
    raw = json.dumps(p, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
    if (
        hashlib.sha256(raw).hexdigest()
        != "365b69343943e70175693aaa0abc14dd998c4a304dbce33b1760e2879c9167b6"
    ):
        raise ValueError("BC-013/1 is frozen; changes need a versioned amendment")


def specifications(p):
    return [
        {"id": f"{design}-{data}", "design": design, "data": data}
        for design, data in itertools.product(p["designs"], p["observation"]["data_cases"])
    ]


def selection(p, spec):
    return [
        t * 3 + c
        for t in range(0, 241, p["observation"]["step_min"])
        for c in p["designs"][spec["design"]]["columns"]
        if t != 0 or c == 2
    ]


def best(records):
    completed = [r for r in records if r["status"] == "completed"]
    if not completed:
        raise ValueError("No completed optimization start; partial evidence retained")
    return min(completed, key=lambda r: r["objective"])


def profile_starts(p, spec, baseline, parameter):
    first = list(baseline["evaluated_parameters"])
    nuisance = [j for j in p["designs"][spec["design"]]["estimated"] if j != parameter]

    def distance(start):
        return sum(math.log(start[j] / first[j]) ** 2 for j in nuisance)

    # max preserves the first inherited start on an exact tie.
    second = max(p["inference"]["unrestricted_starts"][:2], key=distance)
    return [first, list(second)]


def numerical_files(p):
    return {"worker.json", "verification.json", "observations.json"} | {
        "cases/" + s["id"] + ".json" for s in specifications(p)
    }


def required_files(p):
    numeric = numerical_files(p)
    return (
        {
            "protocol.json",
            "parent-volume.json",
            "parent-joint.json",
            "uv.lock",
            "pyproject.toml",
            "worker.log",
            "repeat.log",
        }
        | {"source-" + n for n in SOURCES}
        | {"source-" + n.replace("/", "__") for n in REUSED}
        | numeric
        | {"repeat/" + n for n in numeric}
    )
