"""Comparison configuration, frozen metadata and source provenance."""

import copy
import platform
import sys
from pathlib import Path

from experiments.desktop.provenance import source_version
from experiments.m1.artifacts import strict_json
from experiments.m3.common import ID, ROOT, digest, encoded, finite, require, save
from experiments.m3.researcher.common import provenance as child_provenance
from experiments.m3.researcher.common import validate_config as validate_child_config
from experiments.m3.researcher.intake import (
    MAX_DECLARATION_BYTES,
    MAX_SETTINGS_BYTES,
    MAX_SOURCE_BYTES,
    read_regular,
    validate_bundle,
)
from experiments.platform_files import recorded_path

SCHEMA = "opent1d.m3.comparison/1"
PROTOCOL = ROOT / "docs/research/m3-candidate-comparison-protocol.md"
METHOD = "persistence"
STATES = ("started", "finished", "failed", "interrupted", "not_attempted")


def child_config(config, declaration):
    return {
        "schema": "opent1d.m3.researcher/1",
        **{key: copy.deepcopy(config[key]) for key in ("kind", "source", "prior_access", "people")},
        "predictor": str(declaration),
    }


def validate_config(config, *, archived=False):
    require(
        isinstance(config, dict)
        and set(config)
        == {"schema", "kind", "source", "prior_access", "people", "candidates", "timeout_seconds"}
        and config["schema"] == SCHEMA
        and config["kind"] == "synthetic",
        "Synthetic comparison configuration required",
    )
    candidates = config["candidates"]
    require(
        isinstance(candidates, list) and len(candidates) >= 2, "At least two candidates required"
    )
    seen = set()
    for candidate in candidates:
        require(
            isinstance(candidate, dict) and set(candidate) == {"id", "declaration"},
            "Invalid candidate descriptor",
        )
        identity, path = candidate["id"], candidate["declaration"]
        require(
            isinstance(identity, str)
            and ID.fullmatch(identity)
            and identity != METHOD
            and identity not in seen,
            "Duplicate, unsafe or reserved candidate ID",
        )
        seen.add(identity)
        require(
            isinstance(path, str)
            and (recorded_path(path) if archived else Path(path).is_absolute()),
            "Absolute declaration required",
        )
        validate_child_config(child_config(config, path), archived=archived)
    finite(config["timeout_seconds"], "worker budget", 0)
    require(config["timeout_seconds"] > 0, "Positive shared worker budget required")
    return config


def metadata(path):
    raw = read_regular(path, 16 * 1024 * 1024, "comparison configuration")
    config = validate_config(strict_json(raw))
    bundles = {}
    for candidate in config["candidates"]:
        declaration_raw = read_regular(
            candidate["declaration"], MAX_DECLARATION_BYTES, "predictor declaration"
        )
        declaration = strict_json(declaration_raw)
        require(
            isinstance(declaration, dict) and declaration.get("id") == candidate["id"],
            "Candidate identity differs from declaration",
        )
        # Validate the declaration before using its source/settings paths.
        from experiments.m3.researcher.intake import validate_declaration

        validate_declaration(declaration)
        source = read_regular(declaration["source"]["file"], MAX_SOURCE_BYTES, "predictor source")
        settings = read_regular(
            declaration["settings"]["file"], MAX_SETTINGS_BYTES, "predictor settings"
        )
        validate_bundle(declaration, source, settings)
        bundles[candidate["id"]] = {
            "declaration": declaration,
            "declaration_raw": declaration_raw,
            "source": source,
            "settings": settings,
        }
    return config, bundles


def provenance():
    paths = sorted((ROOT / "experiments/m3/comparison").glob("*.py"))
    sources = dict(child_provenance()["sources"])
    sources.update({path.relative_to(ROOT).as_posix(): digest(path.read_bytes()) for path in paths})
    sources[PROTOCOL.relative_to(ROOT).as_posix()] = digest(PROTOCOL.read_bytes())
    return {
        **source_version(ROOT),
        "sources": dict(sorted(sources.items())),
        "python": sys.version,
        "platform": platform.platform(),
    }


def check(path):
    config, bundles = metadata(path)
    return {
        "schema": SCHEMA,
        "kind": "synthetic",
        "candidate_order": [candidate["id"] for candidate in config["candidates"]],
        "planned_people": len(config["people"]),
        "planned_origins": {person["id"]: len(person["origins_us"]) for person in config["people"]},
        "timeout_seconds": config["timeout_seconds"],
        "candidate_source_sha256": {
            identity: bundle["declaration"]["source"]["sha256"]
            for identity, bundle in bundles.items()
        },
        "observation_bytes_verified": False,
        "candidate_executed": False,
    }


__all__ = [
    "SCHEMA",
    "PROTOCOL",
    "METHOD",
    "STATES",
    "ROOT",
    "child_config",
    "validate_config",
    "metadata",
    "provenance",
    "check",
    "digest",
    "encoded",
    "finite",
    "require",
    "save",
]
