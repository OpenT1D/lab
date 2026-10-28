"""M3 identities and safe serialization; no estimator dependencies."""

import hashlib
import json
import platform
import re
import subprocess
import sys
from pathlib import Path

from experiments.m0.simglucose.recording import write_json
from experiments.m1.artifacts import strict_json
from experiments.m1.contracts import number
from experiments.m1.validation import Snapshot

ROOT = Path(__file__).resolve().parents[2]
PROTOCOL = ROOT / "docs/research/m3-protocol.md"
SCHEMA = "opent1d.m3/1"
METRIC = "m3-cgm-forecast/1"
SHA = re.compile(r"[0-9a-f]{64}\Z")
ID = re.compile(r"[A-Za-z0-9_-]{1,64}\Z")


def require(condition, message):
    if not condition:
        raise ValueError(message)


def digest(data):
    return hashlib.sha256(data).hexdigest()


def encoded(value):
    return (json.dumps(value, sort_keys=True, indent=2, allow_nan=False) + "\n").encode()


def save(path, value):
    write_json(Path(path), value)


def read(path):
    path = Path(path)
    snap = Snapshot(path.parent)
    raw = snap.read(path.name)
    value = strict_json(raw)
    snap.verify_unchanged()
    return value, digest(raw)


def sources():
    paths = list((ROOT / "experiments/m3").glob("*.py"))
    paths += [PROTOCOL, ROOT / "experiments/m3/runtime/uv.lock"]
    paths += [ROOT / "experiments/m3/runtime/pyproject.toml", ROOT / "uv.lock"]
    paths += [
        ROOT / p
        for p in (
            "experiments/m1/artifacts.py",
            "experiments/m1/contracts.py",
            "experiments/m1/validation.py",
            "experiments/m0/simglucose/recording.py",
            "experiments/platform_files.py",
        )
    ]
    return {str(p.relative_to(ROOT)): digest(p.read_bytes()) for p in sorted(paths)}


def provenance():
    return {
        "revision": subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True
        ).strip(),
        "dirty": bool(subprocess.check_output(["git", "status", "--porcelain"], cwd=ROOT)),
        "sources": sources(),
        "python": sys.version,
        "platform": platform.platform(),
    }


def validate_provenance(value):
    require(isinstance(value, dict), "Missing provenance")
    require(
        isinstance(value.get("revision"), str) and re.fullmatch(r"[a-f0-9]{40}", value["revision"]),
        "Invalid revision",
    )
    require(type(value.get("dirty")) is bool, "Missing dirty state")
    require(
        value.get("sources") == sources(), "Source/lock/protocol changed; use recorded checkout"
    )
    for key in ("python", "platform"):
        require(isinstance(value.get(key), str) and value[key], "Missing runtime provenance")


def finite(value, name="numeric signal", minimum=None):
    # Reuse M1's strict bool/string/null/nonfinite rejection.
    number(value, name)
    if minimum is not None:
        require(value >= minimum, f"Invalid {name} range")
    return value
