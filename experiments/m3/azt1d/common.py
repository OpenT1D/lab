"""Versioned AZT1D preparation identities; no patient acquisition or fitting."""

import platform
import re
import subprocess
import sys
from pathlib import Path

from experiments.m3.common import ROOT, digest, finite, read, require, save

__all__ = ["ROOT", "digest", "finite", "read", "require", "save"]

SCHEMA = "opent1d.m3.azt1d/1"
PROTOCOL = "AZT1D-M3/0.1"
METRIC = "azt1d-cgm-forecast/1"
MINUTE = 60_000_000
PHASES = ("development", "validation", "evaluation")


def provenance():
    paths = sorted((ROOT / "experiments/m3/azt1d").glob("*.py"))
    paths += [
        ROOT / name
        for name in (
            "experiments/m3/common.py",
            "experiments/m3/estimator.py",
            "experiments/m3/data.py",
            "experiments/m3/workflow.py",
            "experiments/m1/artifacts.py",
            "experiments/m1/contracts.py",
            "experiments/m1/validation.py",
            "experiments/m0/simglucose/recording.py",
            "experiments/platform_files.py",
            "experiments/m3/runtime/uv.lock",
            "experiments/m3/runtime/pyproject.toml",
            "uv.lock",
            "docs/research/m3-azt1d-protocol.md",
            "docs/decisions/0008-azt1d-causal-forecast.md",
        )
    ]
    return {
        "protocol": PROTOCOL,
        "revision": subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True
        ).strip(),
        "dirty": bool(subprocess.check_output(["git", "status", "--porcelain"], cwd=ROOT)),
        "python": sys.version,
        "platform": platform.platform(),
        "sources": {str(p.relative_to(ROOT)): digest(p.read_bytes()) for p in paths},
    }


def validate_provenance(value):
    require(isinstance(value, dict) and value.get("protocol") == PROTOCOL, "Wrong protocol")
    require(
        isinstance(value.get("revision"), str)
        and re.fullmatch(r"(?:[a-f0-9]{40}|[a-f0-9]{64})", value["revision"])
        and type(value.get("dirty")) is bool,
        "Invalid source revision metadata",
    )
    require(value.get("sources") == provenance()["sources"], "Preparation sources changed")


def outside_repository(*paths):
    for path in paths:
        require(
            not Path(path).resolve().is_relative_to(ROOT),
            "Human material must remain outside repository",
        )
