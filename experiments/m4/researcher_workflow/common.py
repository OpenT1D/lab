"""Versioned composition/configuration boundaries; standard library only."""

import hashlib
import json
from pathlib import Path

from experiments.m4.causal_secretion.common import declaration, sha256
from experiments.m4.feedback_observation.common import validate as validate_observer
from experiments.m4.paired_kinetics.common import dump, read

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
VERSION = "m4-researcher-workflow/1"
PROTOCOL_HASH = "b43c83d2c91712a78c4882a7d4c114827dc4e14f4b5cfa57ba24022b4d2d0c28"
SOURCES = (
    "__init__.py",
    "common.py",
    "run.py",
    "process.py",
    "report.py",
    "observation.py",
    "worker.py",
    "test_numerical.py",
)
REUSED = (
    "experiments/m4/feedback_observation/adapter.py",
    "experiments/m4/feedback_observation/common.py",
    "experiments/m4/feedback_observation/report.py",
    "experiments/m4/feedback_observation/worker.py",
    "experiments/m4/c_peptide/model.py",
    "experiments/m4/c_peptide/reference.py",
    "experiments/m4/paired_kinetics/oracle.py",
    "experiments/m4/paired_kinetics/common.py",
    "experiments/m4/paired_kinetics/report.py",
    "experiments/m4/kinetic_inlet/forcing.py",
    "experiments/m4/paired_observation/run.py",
    "experiments/m4/paired_observation/contract.py",
)


def validate_protocol(p):
    raw = json.dumps(p, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
    if hashlib.sha256(raw).hexdigest() != PROTOCOL_HASH:
        raise ValueError("M4-RESEARCHER/1 protocol is frozen; use a versioned amendment")
    return p


def validate_config(value):
    if (
        not isinstance(value, dict)
        or set(value) != {"schema", "model", "declaration", "timeout_seconds"}
        or value["schema"] != "m4-researcher-config/1"
    ):
        raise ValueError("Config requires schema, model, declaration and timeout_seconds")
    for name in ("model", "declaration"):
        if not isinstance(value[name], str) or not value[name].strip() or "\0" in value[name]:
            raise ValueError(f"Config {name} must be a file path")
    timeout = value["timeout_seconds"]
    if isinstance(timeout, bool) or not isinstance(timeout, int) or not 1 <= timeout <= 1800:
        raise ValueError("timeout_seconds must be an integer between 1 and 1800")
    return value


def intake(config_path):
    config_path = Path(config_path).absolute()
    if config_path.is_symlink() or not config_path.is_file():
        raise ValueError("Config must be a regular JSON file")
    value = validate_config(read(config_path))
    paths = {}
    for name in ("model", "declaration"):
        path = Path(value[name])
        if not path.is_absolute():
            path = config_path.parent / path
        path = path.absolute()
        if path.is_symlink() or not path.is_file():
            raise ValueError(f"Config {name} must identify a regular file")
        paths[name] = path
    if paths["model"].suffix != ".py":
        raise ValueError("Model must be a Python source file")
    declared = declaration(read(paths["declaration"]))
    if sha256(paths["model"]) != declared["source_sha256"]:
        raise ValueError("Model source hash differs from declaration")
    return value, paths, declared


def observer_settings(directory):
    p = read(Path(directory) / "observation-protocol.json")
    validate_observer(p)
    return p


def dump_reports(output, report):
    from .report import figure, markdown

    dump(Path(output) / "report.json", report)
    (Path(output) / "report.md").write_text(markdown(report), encoding="utf-8")
    (Path(output) / "figure.svg").write_text(figure(report), encoding="utf-8")


def verify_reference_sources(directory):
    """Require reused BC-008 source/lock snapshots to match this checkout."""
    from experiments.m4.feedback import common as bc

    directory = Path(directory)
    pairs = [(directory / ("source-" + name), bc.HERE / name) for name in bc.SOURCES]
    pairs += [
        (directory / ("source-" + name.replace("/", "__")), ROOT / name) for name in bc.REUSED
    ]
    pairs += [
        (directory / name, ROOT / "experiments/m0/simglucose" / name)
        for name in ("uv.lock", "pyproject.toml")
    ]
    for archived, current in pairs:
        if not archived.is_file() or sha256(archived) != sha256(current):
            raise ValueError(
                f"Reference source/lock snapshot differs from checkout: {archived.name}"
            )
