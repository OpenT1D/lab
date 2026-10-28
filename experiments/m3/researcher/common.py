"""Identities and strict metadata for the synthetic researcher route."""

import platform
import sys
from pathlib import Path

from experiments.desktop.provenance import SOURCE_FILES as PROVENANCE_SOURCES
from experiments.desktop.provenance import source_version
from experiments.m3.azt1d.data import integer_time
from experiments.m3.common import ID, ROOT, SHA, digest, finite, read, require, save
from experiments.platform_files import recorded_path
from experiments.platform_process import SOURCE_FILES as PROCESS_SOURCES

SCHEMA = "opent1d.m3.researcher/1"
FORMAT = "normalized-cgm/1"


def text(value):
    require(isinstance(value, str) and bool(value.strip()), "Nonempty reference required")


def validate_config(config, *, archived=False):
    require(
        isinstance(config, dict)
        and set(config) == {"schema", "kind", "source", "prior_access", "predictor", "people"}
        and config["schema"] == SCHEMA
        and config["kind"] == "synthetic",
        "Researcher workflow accepts explicit synthetic configuration only",
    )
    source = config["source"]
    require(
        isinstance(source, dict) and set(source) == {"id", "reference", "format"},
        "Invalid source declaration",
    )
    text(source["id"])
    text(source["reference"])
    require(source["format"] == FORMAT, "Unsupported observation format")
    prior = config["prior_access"]
    require(
        isinstance(prior, dict)
        and set(prior) == {"reviewed", "status", "reference"}
        and prior["reviewed"] is True
        and prior["status"] == "present",
        "Disclose prior synthetic generation and access",
    )
    text(prior["reference"])
    require(
        isinstance(config["predictor"], str)
        and (
            recorded_path(config["predictor"])
            if archived
            else Path(config["predictor"]).is_absolute()
        ),
        "Absolute predictor declaration path required",
    )
    require(isinstance(config["people"], list) and config["people"], "Planned cohort required")
    seen, files, hashes = set(), set(), set()
    for person in config["people"]:
        require(
            isinstance(person, dict) and set(person) == {"id", "input", "bounds_us", "origins_us"},
            "Invalid person descriptor",
        )
        pid = person["id"]
        require(
            isinstance(pid, str) and ID.fullmatch(pid) and pid not in seen,
            "Duplicate or unsafe person ID",
        )
        seen.add(pid)
        descriptor = person["input"]
        require(
            isinstance(descriptor, dict) and set(descriptor) == {"file", "sha256"},
            "Invalid input identity",
        )
        file, sha = descriptor["file"], descriptor["sha256"]
        normalized = (
            str(recorded_path(file) if archived else Path(file)) if isinstance(file, str) else None
        )
        require(
            isinstance(file, str)
            and (recorded_path(file) if archived else Path(file).is_absolute())
            and normalized not in files,
            "Repeated or nonabsolute input path",
        )
        require(
            isinstance(sha, str) and SHA.fullmatch(sha) and sha not in hashes,
            "Repeated or invalid input hash",
        )
        files.add(normalized)
        hashes.add(sha)
        bounds = person["bounds_us"]
        require(isinstance(bounds, list) and len(bounds) == 2, "Missing observation bounds")
        start, end = map(integer_time, bounds)
        require(end > start, "Empty observation period")
        origins = person["origins_us"]
        require(isinstance(origins, list) and origins, "Registered origins required")
        for origin in origins:
            integer_time(origin)
            require(start <= origin < end, "Origin outside observation bounds")
        require(origins == sorted(set(origins)), "Unordered or duplicate origins")
    return config


def fresh_directory(output):
    output = Path(output).absolute()
    require(not output.is_symlink(), "Output cannot be a symlink")
    output.mkdir(parents=True, exist_ok=False, mode=0o700)
    return output


def provenance():
    paths = list((ROOT / "experiments/m3/researcher").glob("*.py"))
    paths += [
        ROOT / name
        for name in (
            "experiments/platform_files.py",
            "experiments/m3/common.py",
            "experiments/m3/estimator.py",
            "experiments/m3/runtime/uv.lock",
            "experiments/m3/runtime/pyproject.toml",
            "experiments/m3/azt1d/common.py",
            "experiments/m3/azt1d/data.py",
            "experiments/m3/azt1d/metrics.py",
            "experiments/m1/artifacts.py",
            "experiments/m1/contracts.py",
            "experiments/m1/validation.py",
            "experiments/m0/simglucose/recording.py",
            "uv.lock",
            "docs/research/m3-researcher-protocol.md",
        )
    ]
    paths.extend(ROOT / name for name in (*PROCESS_SOURCES, *PROVENANCE_SOURCES))
    return {
        **source_version(ROOT),
        "sources": {p.relative_to(ROOT).as_posix(): digest(p.read_bytes()) for p in sorted(paths)},
        "python": sys.version,
        "platform": platform.platform(),
    }


__all__ = [
    "ROOT",
    "SCHEMA",
    "FORMAT",
    "digest",
    "finite",
    "read",
    "require",
    "save",
    "fresh_directory",
    "validate_config",
    "provenance",
]
