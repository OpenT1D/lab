"""Bounded campaign admission, stable byte inventories and frozen runtime identities."""

import hashlib
import json
import os
import re
import subprocess
from pathlib import Path

from experiments.desktop.runtime import interpreter
from experiments.m1.artifacts import strict_json
from experiments.m1.validation import Snapshot
from experiments.platform_files import is_link
from experiments.platform_process import SOURCE_FILES as PROCESS_SOURCES

from . import native

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
VERSION = "opent1d.maintained-campaign/1"
REPORT_SCHEMA = "opent1d.maintained-campaign-report/1"
PREPARATION_SCHEMA = "opent1d.maintained-campaign-preparation/1"
TASK = "m4-study-secure"
RUNTIME_PROJECTS = (".", "experiments/m0/simglucose_secure", "experiments/m4/beta_cell/runtime")
CONFIG_SCHEMA = "opent1d.maintained-campaign-config/1"
PROTOCOL = HERE / "protocol.json"
PROTOCOL_SHA256 = "846e73854e4bbd91b28ed2adc3d98b5d994f818b033565a81b07093aa070afaf"
ID = re.compile(r"[a-z][a-z0-9_-]{0,63}\Z")
SHA = re.compile(r"[0-9a-f]{64}\Z")
REPORTS = {"report.json", "report.md"}
STATES = {"not_attempted", "started", "completed", "failed", "interrupted"}
SELF_SOURCES = (
    tuple(
        "experiments/maintained_campaigns/" + name
        for name in (
            "__init__.py",
            "__main__.py",
            "common.py",
            "native.py",
            "process.py",
            "runtime.py",
            "run.py",
            "report.py",
            "protocol.json",
        )
    )
    + (
        "pyproject.toml",
        "uv.lock",
        "experiments/desktop/runtime.py",
        "experiments/platform_files.py",
    )
    + PROCESS_SOURCES
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


def read(path, limit=64 * 1024 * 1024):
    # Session manifests can inventory 128 full native archives. Never open a
    # pipe/device as metadata, including excluded manifests and report caches.
    _, raw = regular(path, limit)
    return strict_json(raw)


def regular(path, limit=1024 * 1024):
    path = Path(path).absolute()
    require(path.is_file() and not is_link(path), "Input must be a regular file")
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
        and value["task"] == TASK,
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
    """Probe complete installed identities without importing a candidate or simulator."""
    from experiments.m4.comparison.run import worker_environment

    result = {}
    native_script = (
        "import json,sys; from experiments.m4.secure_study.runtime import attest; "
        "print(json.dumps(attest(sys.argv[1]),sort_keys=True))"
    )
    for project in RUNTIME_PROJECTS:
        script = (
            "import json; from experiments.maintained_campaigns.runtime import attest_root; "
            "print(json.dumps(attest_root(),sort_keys=True))"
            if project == "."
            else native_script
        )
        executable = interpreter(project)
        require(executable.is_file(), "Installed runtime unavailable: " + project)
        try:
            probe = subprocess.run(
                [str(executable), "-B", "-E", "-s", "-c", script, project],
                cwd=ROOT,
                env=worker_environment(),
                capture_output=True,
                timeout=30,
                check=False,
                stdin=subprocess.DEVNULL,
                creationflags=0x00000008 if os.name == "nt" else 0,  # DETACHED_PROCESS
            )
        except (OSError, subprocess.SubprocessError) as error:
            raise ValueError("Installed runtime probe failed: " + project) from error
        require(probe.returncode == 0, "Installed locked runtime differs: " + project)
        record = strict_json(probe.stdout)
        require(
            record["project"] == project,
            "Runtime probe project/schema differs",
        )
        result[project] = record
    validate_runtime_identity(result)
    return result


def validate_runtime_identity(value):
    """Verify recorded complete attestations passively against frozen lock bytes."""
    from experiments.m4.secure_study.common import package_records

    from .runtime import ROOT_RUNTIME_SCHEMA, root_selection

    require(
        isinstance(value, dict) and set(value) == set(RUNTIME_PROJECTS),
        "Incomplete installed runtime identity",
    )
    for project, record in value.items():
        require(
            isinstance(record, dict)
            and set(record)
            == (
                {
                    "schema",
                    "project",
                    "python",
                    "executable",
                    "distributions",
                    "upstream_revisions",
                    "runtime_files_sha256",
                }
                | ({"selection"} if project == "." else set())
            ),
            "Incomplete installed runtime attestation",
        )
        if project == ".":
            expected, selection = root_selection(
                record["selection"]["marker_environment"]["sys_platform"]
            )
            require(record["selection"] == selection, "Archived root platform selection differs")
        else:
            expected = package_records(project)
        require(
            record["schema"]
            == (ROOT_RUNTIME_SCHEMA if project == "." else "m4-secure-runtime-attestation/1")
            and record["project"] == project
            and isinstance(record["python"], str)
            and re.fullmatch(r"3\.12\.[0-9]+", record["python"])
            and isinstance(record["executable"], str)
            and record["executable"]
            and record["distributions"]
            == {name: item["version"] for name, item in expected.items()}
            and record["upstream_revisions"]
            == {
                name: item["source"]["git"].rsplit("#", 1)[1]
                for name, item in expected.items()
                if "git" in item["source"]
            }
            and record["runtime_files_sha256"]
            == {
                name: digest((ROOT / project / name).read_bytes())
                for name in ("pyproject.toml", "uv.lock")
            },
            "Installed runtime attestation differs from locked identity",
        )


def source_paths():
    """Explicit coordinator and native ancestry; GUI code is never a scientific input."""
    return tuple(sorted(set(SELF_SOURCES) | set(native.source_paths())))


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
    require(directory.is_dir() and not is_link(directory), "Archive must be a directory")
    files, snapshots = {}, {}
    for path in sorted(directory.rglob("*")):
        require(not is_link(path), "Archive contains a symlink or reparse point")
        require(path.is_dir() or path.is_file(), "Archive contains a nonregular artifact")
        if path.is_file():
            name = path.relative_to(directory).as_posix()
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


def prepare(path):
    """JSON-only passive admission metadata for the CLI and future GUI."""
    config, raw, bundles = intake(path)
    p = protocol()
    return {
        "schema": PREPARATION_SCHEMA,
        "task": TASK,
        "configuration": config,
        "config_sha256": digest(raw),
        "cell_order": [cell["id"] for cell in config["cells"]],
        "cells": {name: bundle["metadata"] for name, bundle in bundles.items()},
        "planned_slots": len(slots(config)),
        "planned_source_scenarios": config["repeats"]
        * sum(
            len(bundle["metadata"]["source_order"]) * len(bundle["metadata"]["scenarios"])
            for bundle in bundles.values()
        ),
        "timeout_seconds": config["timeout_seconds"],
        "protocol": p,
        "protocol_sha256": PROTOCOL_SHA256,
        "source_sha256": {name: digest((ROOT / name).read_bytes()) for name in source_paths()},
        "source_executed": False,
        "runtime_probed": False,
    }


def check(path):
    result = prepare(path)
    result.update(runtime_identity=runtime_identity(), runtime_probed=True, ready=True)
    return result


def root_inventory(directory):
    directory = Path(directory)
    require(directory.is_dir() and not directory.is_symlink(), "Campaign must be a directory")
    files = {}
    for entry in sorted(directory.iterdir()):
        require(not entry.is_symlink(), "Campaign contains a symlink")
        if entry.name in {"manifest.json", "sessions"}:
            require(
                entry.is_file() if entry.name == "manifest.json" else entry.is_dir(),
                "Campaign manifest/session path is nonregular",
            )
            continue
        if entry.is_dir():
            files.update({entry.name + "/" + name: raw for name, raw in inventory(entry).items()})
        else:
            # A 32-cell plan repeats each native protocol/execution descriptor.
            # Keep a bounded allowance for this declared matrix ceiling.
            _, files[entry.name] = regular(
                entry, 16 * 1024 * 1024 if entry.name == "plan.json" else 1024 * 1024
            )
    return files


def protocol():
    raw = PROTOCOL.read_bytes()
    require(digest(raw) == PROTOCOL_SHA256, "MAINTAINED-CAMPAIGN/1 protocol is frozen")
    return strict_json(raw)
