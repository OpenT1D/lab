"""Bounded campaign admission, stable byte inventories and frozen runtime identities."""

import hashlib
import json
import re
from pathlib import Path

from experiments.m1.artifacts import strict_json
from experiments.m1.validation import Snapshot
from experiments.workflows.checks import NATIVE_VERSIONS, OBSERVER_VERSIONS, probe_runtime

from . import native

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
VERSION = "opent1d.local-campaign/1"
CONFIG_SCHEMA = "opent1d.local-campaign-config/1"
PROTOCOL = HERE / "protocol.json"
PROTOCOL_SHA256 = "a06f1790d5c7afd669fb8af8b269b40b8413f723ffaef459f16b1deb6f5c2974"
ID = re.compile(r"[a-z][a-z0-9_-]{0,63}\Z")
SHA = re.compile(r"[0-9a-f]{64}\Z")
REPORTS = {"report.json", "report.md"}
STATES = {"not_attempted", "started", "completed", "failed", "interrupted"}
SELF_SOURCES = tuple(
    sorted(
        {
            *(
                f"experiments/campaigns/{name}"
                for name in (
                    "__init__.py",
                    "__main__.py",
                    "common.py",
                    "native.py",
                    "process.py",
                    "run.py",
                    "report.py",
                    "protocol.json",
                )
            ),
            *(
                f"experiments/m1/{name}.py"
                for name in ("artifacts", "validation", "contracts", "metrics")
            ),
            "experiments/m0/simglucose/recording.py",
            "experiments/platform_files.py",
            *(f"experiments/workflows/{name}.py" for name in ("checks", "registry")),
            *(f"experiments/m4/comparison/{name}.py" for name in ("__init__", "common", "run")),
            "uv.lock",
            "pyproject.toml",
        }
    )
)


def require(condition, message):
    if not condition:
        raise ValueError(message)


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def encoded(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()


def dump(path, value):
    Path(path).write_bytes(
        json.dumps(value, indent=2, sort_keys=True, allow_nan=False).encode() + b"\n"
    )


def read(path):
    return strict_json(Path(path).read_bytes())


def regular(path, limit=1024 * 1024):
    path = Path(path).absolute()
    require(path.is_file() and not path.is_symlink(), "Input must be a regular file")
    require(path.stat().st_size <= limit, "Input exceeds byte limit")
    snapshot = Snapshot(path.parent)
    raw = snapshot.read(path.name)
    snapshot.verify_unchanged()
    require(len(raw) <= limit, "Input exceeds byte limit")
    return path.resolve(), raw


def validate_config(value):
    require(
        isinstance(value, dict)
        and set(value)
        == {
            "schema",
            "task",
            "cells",
            "repeats",
            "timeout_seconds",
        }
        and value["schema"] == CONFIG_SCHEMA
        and value["task"] == "m4-study",
        "Unsupported campaign configuration",
    )
    require(
        isinstance(value["cells"], list) and 1 <= len(value["cells"]) <= 32,
        "One to 32 cells required",
    )
    require(
        type(value["repeats"]) is int and 1 <= value["repeats"] <= 8,
        "One to eight repetitions required",
    )
    require(len(value["cells"]) * value["repeats"] <= 128, "Campaign exceeds 128 slots")
    require(
        type(value["timeout_seconds"]) is int and 1 <= value["timeout_seconds"] <= 10800,
        "Invalid outer study budget",
    )
    seen = set()
    for cell in value["cells"]:
        require(isinstance(cell, dict) and set(cell) == {"id", "config"}, "Invalid campaign cell")
        identity, path = cell["id"], cell["config"]
        require(
            isinstance(identity, str) and ID.fullmatch(identity) and identity not in seen,
            "Duplicate or unsafe cell ID",
        )
        require(
            isinstance(path, str) and path.strip() and "\0" not in path,
            "Cell requires a configuration path",
        )
        seen.add(identity)
    return value


def slots(config):
    return [
        {"id": f"{cell['id']}--r{repeat:03d}", "cell": cell["id"], "repeat": repeat}
        for cell in config["cells"]
        for repeat in range(1, config["repeats"] + 1)
    ]


def runtime_identity():
    probes = [
        probe_runtime(project, packages)
        for project, packages in (
            (".", {}),
            ("experiments/m0/simglucose", NATIVE_VERSIONS),
            ("experiments/m4/beta_cell/runtime", OBSERVER_VERSIONS),
        )
    ]
    require(
        all(probe["ready"] for probe in probes),
        "Installed runtimes unavailable; use explicit uv sync --locked setup",
    )
    return {probe["project"]: probe["actual"] for probe in probes}


def intake(path):
    path, raw = regular(path, 64 * 1024)
    config = validate_config(strict_json(raw))
    bundles = {}
    for cell in config["cells"]:
        child = Path(cell["config"])
        if not child.is_absolute():
            child = path.parent / child
        child, config_raw = regular(child, 64 * 1024)
        metadata = native.prepare(child)
        require(
            metadata["config_sha256"] == digest(config_raw)
            and encoded(metadata["configuration"]) == encoded(strict_json(config_raw)),
            "Native configuration changed during admission",
        )
        sources = {}
        for identity in metadata["source_order"]:
            declared = metadata["sources"][identity]
            model_path, model = regular(declared["model_path"])
            declaration_path, declaration = regular(declared["declaration_path"], 64 * 1024)
            require(
                digest(model) == declared["source_sha256"]
                and digest(declaration) == declared["declaration_sha256"],
                "Native source/declaration changed during admission",
            )
            sources[identity] = {
                "model": model,
                "declaration": declaration,
                "paths": [model_path, declaration_path],
            }
        bundles[cell["id"]] = {
            "metadata": metadata,
            "config_raw": config_raw,
            "config_path": child,
            "sources": sources,
        }
    return config, raw, bundles


def inventory(directory, exclude=()):
    directory = Path(directory)
    require(directory.is_dir() and not directory.is_symlink(), "Archive must be a directory")
    files, snapshots = {}, {}
    for path in sorted(directory.rglob("*")):
        require(not path.is_symlink(), "Archive contains a symlink")
        if path.is_file():
            name = str(path.relative_to(directory))
            if name not in exclude:
                snapshot = snapshots.setdefault(path.parent, Snapshot(path.parent))
                files[name] = snapshot.read(path.name)
    for snapshot in snapshots.values():
        snapshot.verify_unchanged()
    return files


def seal(directory, exclude=()):
    files = inventory(directory, {"manifest.json", *exclude})
    dump(
        Path(directory) / "manifest.json",
        {"schema": VERSION, "files": {name: digest(raw) for name, raw in files.items()}},
    )


def sealed(directory, exclude=()):
    manifest = read(Path(directory) / "manifest.json")
    files = inventory(directory, {"manifest.json", *exclude})
    require(
        isinstance(manifest, dict)
        and set(manifest) == {"schema", "files"}
        and manifest["schema"] == VERSION
        and manifest["files"] == {name: digest(raw) for name, raw in files.items()},
        "Sealed campaign/session inventory changed",
    )
    return files


def check(path):
    config, raw, bundles = intake(path)
    return {
        "schema": CONFIG_SCHEMA,
        "task": "m4-study",
        "config_sha256": digest(raw),
        "cell_order": [cell["id"] for cell in config["cells"]],
        "planned_slots": len(slots(config)),
        "timeout_seconds": config["timeout_seconds"],
        "native_config_sha256": {
            identity: bundle["metadata"]["config_sha256"] for identity, bundle in bundles.items()
        },
        "source_executed": False,
        "runtime_identity": runtime_identity(),
    }


def root_inventory(directory):
    directory = Path(directory)
    require(directory.is_dir() and not directory.is_symlink(), "Campaign must be a directory")
    files = {}
    for entry in sorted(directory.iterdir()):
        require(not entry.is_symlink(), "Campaign contains a symlink")
        if entry.name in {"manifest.json", "sessions"}:
            continue
        if entry.is_dir():
            files.update({entry.name + "/" + name: raw for name, raw in inventory(entry).items()})
        else:
            _, files[entry.name] = regular(entry)
    return files


def protocol():
    raw = PROTOCOL.read_bytes()
    require(digest(raw) == PROTOCOL_SHA256, "LOCAL-CAMPAIGN/1 protocol is frozen")
    return strict_json(raw)
