"""Frozen configuration, input snapshots and archive inventory; standard library only."""

import hashlib
import json
import platform
import re
import subprocess
import sys
from pathlib import Path

from experiments.m1.artifacts import strict_json
from experiments.m1.validation import Snapshot
from experiments.m4.causal_secretion import common as causal
from experiments.m4.feedback import common as feedback
from experiments.m4.researcher_workflow import common as child

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
VERSION = "m4-source-comparison/1"
CONFIG_SCHEMA = "m4-source-comparison-config/1"
PROTOCOL = HERE / "protocol.json"
GUIDANCE = ROOT / "docs/research/m4-source-comparison-protocol.md"
PROTOCOL_SHA256 = "1769545288eb65d72757a9330034abad5800c0fac75dc2ca105c801a2014282c"
PROTOCOL_OBJECT_SHA256 = "b7400a4ba339cafd6a2bc9fa23b17d23aa636dae6fac4ba2cd5a4842b5ffd99a"
ID = re.compile(r"[a-z][a-z0-9_-]{0,63}\Z")
STATES = ("not_attempted", "started", "completed", "failed", "interrupted")
ARTIFACTS = {"manifest.json", "report.json", "report.md", "figure.svg"}
SOURCES = tuple(
    sorted(
        {
            *(
                f"experiments/m1/{name}.py"
                for name in ("artifacts", "validation", "contracts", "metrics")
            ),
            "experiments/m0/simglucose/recording.py",
            "experiments/platform_files.py",
            *(
                f"experiments/m4/comparison/{name}"
                for name in (
                    "__init__.py",
                    "__main__.py",
                    "common.py",
                    "run.py",
                    "analysis.py",
                    "report.py",
                    "protocol.json",
                )
            ),
            "docs/research/m4-source-comparison-protocol.md",
            *(f"experiments/m4/researcher_workflow/{name}" for name in child.SOURCES),
            *child.REUSED,
            "experiments/m4/researcher_workflow/protocol.json",
            "experiments/m4/feedback_observation/protocol.json",
            *(f"experiments/m4/causal_secretion/{name}" for name in causal.SOURCES),
            *causal.REUSED,
            *(f"experiments/m4/feedback/{name}" for name in feedback.SOURCES),
            *feedback.REUSED,
            *(
                f"experiments/m4/feedback/{name}"
                for name in (
                    "protocol.json",
                    "source-cases.json",
                    "sources.json",
                )
            ),
            *(
                f"{project}/{name}"
                for project in (
                    "experiments/m0/simglucose",
                    "experiments/m4/beta_cell/runtime",
                )
                for name in ("uv.lock", "pyproject.toml")
            ),
        }
    )
)


def require(condition, message):
    if not condition:
        raise ValueError(message)


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def sha256(path):
    return digest(Path(path).read_bytes())


def encoded(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()


def dump(path, value):
    Path(path).write_text(json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n")


def read(path):
    return strict_json(Path(path).read_bytes())


def regular(path, limit, label):
    path = Path(path).absolute()
    require(not path.is_symlink() and path.is_file(), f"{label} must be a regular file")
    require(path.stat().st_size <= limit, f"{label} exceeds byte limit")
    snapshot = Snapshot(path.parent)
    raw = snapshot.read(path.name)
    snapshot.verify_unchanged()
    require(len(raw) <= limit, f"{label} exceeds byte limit")
    return path.resolve(), raw


def validate_protocol(value):
    require(digest(encoded(value)) == PROTOCOL_OBJECT_SHA256, "M4-COMPARISON/1 is frozen")
    return value


def protocol():
    raw = PROTOCOL.read_bytes()
    require(digest(raw) == PROTOCOL_SHA256, "Comparison protocol file identity changed")
    value = validate_protocol(strict_json(raw))
    conditions = value["conditions"]
    for group in ("protocol_files_sha256", "runtime_files_sha256"):
        for name, expected in conditions[group].items():
            require(sha256(ROOT / name) == expected, f"Frozen condition identity changed: {name}")
    return value


def validate_config(value):
    require(
        isinstance(value, dict)
        and set(value) == {"schema", "sources", "timeout_seconds", "source_timeout_seconds"}
        and value["schema"] == CONFIG_SCHEMA,
        "Comparison config requires schema, sources and both worker budgets",
    )
    sources = value["sources"]
    require(isinstance(sources, list) and 2 <= len(sources) <= 8, "Two to eight sources required")
    seen = set()
    for source in sources:
        require(
            isinstance(source, dict) and set(source) == {"id", "model", "declaration"},
            "Invalid source descriptor",
        )
        identity = source["id"]
        require(
            isinstance(identity, str)
            and ID.fullmatch(identity)
            and identity not in seen
            and identity not in {"host_constant_basal", "bc008_reference"},
            "Duplicate, unsafe or reserved source ID",
        )
        seen.add(identity)
        for name in ("model", "declaration"):
            path = source[name]
            require(
                isinstance(path, str) and path.strip() and "\0" not in path,
                f"Source {name} must be a file path",
            )
    for name, maximum in (("timeout_seconds", 1800), ("source_timeout_seconds", 10800)):
        budget = value[name]
        require(type(budget) is int and 1 <= budget <= maximum, f"Invalid {name} worker budget")
    return value


def intake(config_path):
    config_path, raw = regular(config_path, 64 * 1024, "Comparison config")
    config = validate_config(strict_json(raw))
    protocol()
    bundles = {}
    for item in config["sources"]:
        paths = {}
        for name, limit in (("model", 1024 * 1024), ("declaration", 64 * 1024)):
            path = Path(item[name])
            if not path.is_absolute():
                path = config_path.parent / path
            paths[name], paths[name + "_raw"] = regular(path, limit, f"Source {name}")
        require(paths["model"].suffix == ".py", "Model must be a Python source file")
        declared = causal.declaration(strict_json(paths["declaration_raw"]))
        require(
            digest(paths["model_raw"]) == declared["source_sha256"],
            "Model source hash differs from declaration",
        )
        bundles[item["id"]] = {**paths, "declared": declared, "config_raw": raw}
    return config, bundles


metadata = intake


def verify_reference(directory):
    directory = Path(directory).absolute()
    require(directory.is_dir() and not directory.is_symlink(), "Reference must be a directory")
    require(not any(p.is_symlink() for p in directory.rglob("*")), "Reference contains symlinks")
    result = causal.reference(directory)
    child.verify_reference_sources(directory)
    return result


def source_snapshots():
    return {name: (ROOT / name).read_bytes() for name in SOURCES}


def provenance(snapshots=None):
    snapshots = source_snapshots() if snapshots is None else snapshots
    return {
        "git_head": subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True
        ).strip(),
        "git_dirty": bool(subprocess.check_output(["git", "status", "--porcelain"], cwd=ROOT)),
        "python": sys.version,
        "platform": platform.platform(),
        "sources": {name: digest(raw) for name, raw in sorted(snapshots.items())},
    }


def check(config_path, reference_path=None):
    config, bundles = intake(config_path)
    if reference_path is not None:
        verify_reference(reference_path)
    return {
        "schema": CONFIG_SCHEMA,
        "source_order": [source["id"] for source in config["sources"]],
        "source_sha256": {
            identity: b["declared"]["source_sha256"] for identity, b in bundles.items()
        },
        "timeout_seconds": config["timeout_seconds"],
        "source_timeout_seconds": config["source_timeout_seconds"],
        "reference_verified": reference_path is not None,
        "source_executed": False,
    }


def inventory(directory):
    directory = Path(directory)
    require(directory.is_dir() and not directory.is_symlink(), "Archive must be a directory")
    files, snapshots = {}, {}
    for path in sorted(directory.rglob("*")):
        require(not path.is_symlink(), "Comparison archive contains symlink")
        if path.is_file():
            name = path.relative_to(directory).as_posix()
            if name not in ARTIFACTS:
                snapshot = snapshots.setdefault(path.parent, Snapshot(path.parent))
                files[name] = snapshot.read(path.name)
    for snapshot in snapshots.values():
        snapshot.verify_unchanged()
    return files


def seal(directory):
    dump(
        Path(directory) / "manifest.json",
        {
            "schema": VERSION,
            "files": {name: digest(raw) for name, raw in inventory(directory).items()},
        },
    )
