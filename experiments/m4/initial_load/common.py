"""Passive intake and frozen implementation identities for M4-STUDY/2."""

import ast
import hashlib
import json
import platform
import re
import sys
from pathlib import Path

from experiments.desktop.admission_sources import SOURCE_FILES as ADMISSION_SOURCES
from experiments.desktop.provenance import source_version
from experiments.m1.artifacts import strict_json
from experiments.m1.validation import Snapshot
from experiments.m4.causal_secretion import common as causal
from experiments.m4.comparison import common as comparison
from experiments.platform_files import is_link

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
VERSION = "m4-initial-load-run/1"
CONFIG_SCHEMA = "m4-initial-load-config/1"
REPORT_SCHEMA = "m4-initial-load-report/1"
PROTOCOL_SHA256 = "d2ed95617dd22db1e8204da6b35a2b28119ef4e4f67f8ca64f80395917cf6eb2"
PROTOCOL_OBJECT_SHA256 = "ee9ecd421645c3acf11857037e2304fe10b0931c7c9f7cb6301659219d2d60cb"
SCENARIOS = {"fasting": 0, "gastric_load_15g": 15000, "gastric_load_30g": 30000}
SOLVERS = ("coarse", "tight", "reference")
MODES = ("candidate", "host_constant_basal", "bc008_reference")
REFERENCE_MODES = ("native_zero", "host_constant_basal", "bc008_reference")
ARTIFACTS = {"manifest.json", "report.json", "report.md", "figure.svg"}
ID = re.compile(r"[a-z][a-z0-9_-]{0,63}\Z")


def require(condition, message):
    if not condition:
        raise ValueError(message)


def validate_native_record(current, historical):
    """Compare scientific identity, retaining installation paths as provenance."""
    locations = {"patient_file", "parameter_file"}
    require(
        isinstance(current, dict)
        and isinstance(historical, dict)
        and set(current) == set(historical) == {"identity", "parameters", "runtime"},
        "Incomplete native identity record",
    )
    identities = []
    for record in (current, historical):
        identity = record["identity"]
        require(
            isinstance(identity, dict)
            and all(isinstance(identity.get(key), str) and identity[key] for key in locations),
            "Missing native installation provenance",
        )
        identities.append({key: value for key, value in identity.items() if key not in locations})
    require(
        identities[0] == identities[1]
        and current["parameters"] == historical["parameters"]
        and current["runtime"] == historical["runtime"],
        "Native scientific identity, parameters or runtime changed",
    )


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


def sha256(path):
    return digest(Path(path).read_bytes())


def regular(path, maximum, label):
    path = Path(path).absolute()
    require(path.is_file() and not is_link(path), f"{label} must be a regular file")
    snapshot = Snapshot(path.parent)
    raw = snapshot.read(path.name)
    snapshot.verify_unchanged()
    require(len(raw) <= maximum, f"{label} exceeds byte limit")
    return path.resolve(), raw


def protocol():
    raw = (HERE / "protocol.json").read_bytes()
    require(digest(raw) == PROTOCOL_SHA256, "M4-STUDY/2 protocol bytes changed")
    p = strict_json(raw)
    require(digest(encoded(p)) == PROTOCOL_OBJECT_SHA256, "M4-STUDY/2 conditions are frozen")
    for group in ("protocol_files_sha256", "runtime_files_sha256"):
        for name, expected in p["conditions"][group].items():
            require(sha256(ROOT / name) == expected, f"Frozen condition changed: {name}")
    return p


def validate_config(config):
    require(
        isinstance(config, dict)
        and set(config)
        == {"schema", "sources", "scenarios", "timeout_seconds", "source_timeout_seconds"}
        and config["schema"] == CONFIG_SCHEMA,
        "Study config requires schema, sources, scenarios and both worker budgets",
    )
    sources = config["sources"]
    require(isinstance(sources, list) and 2 <= len(sources) <= 8, "Two to eight sources required")
    seen = set()
    for item in sources:
        require(
            isinstance(item, dict) and set(item) == {"id", "model", "declaration"},
            "Invalid source descriptor",
        )
        name = item["id"]
        require(
            isinstance(name, str)
            and ID.fullmatch(name)
            and name not in seen
            and name not in REFERENCE_MODES,
            "Duplicate, unsafe or reserved source ID",
        )
        seen.add(name)
        for key in ("model", "declaration"):
            require(
                isinstance(item[key], str) and item[key].strip() and "\0" not in item[key],
                "Source paths must be strings",
            )
    scenarios = config["scenarios"]
    require(
        isinstance(scenarios, list)
        and 1 <= len(scenarios) <= 3
        and all(isinstance(name, str) and name in SCENARIOS for name in scenarios)
        and len(set(scenarios)) == len(scenarios),
        "Scenarios must be an ordered unique nonempty subset of "
        "fasting, gastric_load_15g, gastric_load_30g",
    )
    for key, maximum in (("timeout_seconds", 1800), ("source_timeout_seconds", 10800)):
        require(type(config[key]) is int and 1 <= config[key] <= maximum, f"Invalid {key}")
    return config


def intake(path):
    path, raw = regular(path, 65536, "Study config")
    config = validate_config(strict_json(raw))
    protocol()
    bundles = {}
    for item in config["sources"]:
        bundle = {"config_raw": raw}
        for key, limit in (("model", 1048576), ("declaration", 65536)):
            target = Path(item[key])
            if not target.is_absolute():
                target = path.parent / target
            bundle[key + "_path"], bundle[key + "_raw"] = regular(target, limit, f"Source {key}")
        require(bundle["model_path"].suffix == ".py", "Model must be Python source")
        bundle["declared"] = causal.declaration(strict_json(bundle["declaration_raw"]))
        require(
            digest(bundle["model_raw"]) == bundle["declared"]["source_sha256"],
            "Model hash differs from declaration",
        )
        bundles[item["id"]] = bundle
    return config, bundles


def source_roots():
    """Select the explicit ancestry roots without walking imports."""
    files = set(comparison.SOURCES) | set(ADMISSION_SOURCES)
    files.update(path.relative_to(ROOT).as_posix() for path in HERE.glob("*.py"))
    files.update(
        {
            "experiments/m4/initial_load/protocol.json",
            "experiments/m4/initial_load/protocol-v1.json",
            "docs/research/m4-configurable-study-protocol.md",
            "experiments/integration/ot032-midpoint-v1-probe.json",
            "experiments/integration/ot032-midpoint-v1-probe.source.txt",
        }
    )
    return files


def source_paths():
    """Freeze local import ancestry without importing numerical or supplied code."""
    return source_closure(source_roots())


def source_closure(names):
    """Include imported local helpers without importing optional scientific runtimes."""
    files = set(names)
    pending = list(files)
    examined = set(files)
    while pending:
        name = pending.pop()
        if not name.endswith(".py"):
            continue
        package = name[:-3].replace("/", ".").rsplit(".", 1)[0]
        for node in ast.walk(ast.parse((ROOT / name).read_bytes())):
            modules = []
            if isinstance(node, ast.Import):
                modules = [item.name for item in node.names]
            elif isinstance(node, ast.ImportFrom):
                base = node.module or ""
                if node.level:
                    parts = package.split(".")
                    base = ".".join(parts[: len(parts) - node.level + 1] + ([base] if base else []))
                modules = [base, *(base + "." + item.name for item in node.names)]
            for module in modules:
                if not module.startswith("experiments."):
                    continue
                relative = module.replace(".", "/")
                for candidate in (relative + ".py", relative + "/__init__.py"):
                    # Many imports name the same helper or missing attribute.
                    # Inspect each candidate once per walk, never across checks.
                    if candidate in examined:
                        continue
                    examined.add(candidate)
                    if (ROOT / candidate).is_file():
                        files.add(candidate)
                        pending.append(candidate)
    return tuple(sorted(files))


def source_snapshots():
    return {name: (ROOT / name).read_bytes() for name in source_paths()}


def prepare(path):
    config, bundles = intake(path)
    return {
        "schema": "m4-initial-load-preparation/1",
        "configuration": config,
        "config_sha256": digest(next(iter(bundles.values()))["config_raw"]),
        "source_order": [item["id"] for item in config["sources"]],
        "sources": {
            name: {
                "declaration": bundle["declared"],
                "source_sha256": digest(bundle["model_raw"]),
                "declaration_sha256": digest(bundle["declaration_raw"]),
                "model_path": str(bundle["model_path"]),
                "declaration_path": str(bundle["declaration_path"]),
            }
            for name, bundle in bundles.items()
        },
        "scenarios": [
            {"id": name, "initial_gastric_solid_mg": SCENARIOS[name]}
            for name in config["scenarios"]
        ],
        "protocol": protocol(),
        "protocol_sha256": PROTOCOL_SHA256,
        "runtime_files_sha256": protocol()["conditions"]["runtime_files_sha256"],
        "implementation_sources_sha256": {
            name: digest(raw) for name, raw in source_snapshots().items()
        },
    }


verify_reference = comparison.verify_reference


def provenance(snapshots):
    version = source_version(ROOT)
    return {
        "git_head": version["revision"],
        "git_dirty": version["dirty"],
        "python": sys.version,
        "platform": platform.platform(),
        "checkout_path": str(ROOT),
        "sources": {name: digest(raw) for name, raw in sorted(snapshots.items())},
    }


def inventory(directory):
    directory = Path(directory)
    require(directory.is_dir() and not is_link(directory), "Archive must be a regular directory")
    snapshots, files = {}, {}
    for path in sorted(directory.rglob("*")):
        require(not is_link(path), "Archive contains symlink or reparse point")
        if path.is_file() and path.relative_to(directory).as_posix() not in ARTIFACTS:
            snap = snapshots.setdefault(path.parent, Snapshot(path.parent))
            files[path.relative_to(directory).as_posix()] = snap.read(path.name)
    for snap in snapshots.values():
        snap.verify_unchanged()
    return files


def seal(directory):
    dump(
        Path(directory) / "manifest.json",
        {
            "schema": VERSION,
            "files": {name: digest(raw) for name, raw in inventory(directory).items()},
        },
    )


def reference_snapshot(directory):
    return {name: digest(raw) for name, raw in inventory(Path(directory) / "reference").items()}


def verify_reference_snapshot(directory):
    path = Path(directory) / "reference-manifest.json"
    require(path.is_file(), "Missing pre-callback common reference seal")
    require(
        read(path)
        == {"schema": "m4-initial-load-reference-seal/1", "files": reference_snapshot(directory)},
        "Scenario-specific reference changed after verification",
    )
