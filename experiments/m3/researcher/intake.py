"""Hash-bound intake for one trusted, stateless synthetic CGM forecaster."""

import os
import stat
from pathlib import Path

from experiments.m1.artifacts import strict_json
from experiments.m3.common import ID, SHA, digest, require
from experiments.platform_files import is_link, open_regular, recorded_path, regular_info

SCHEMA = "opent1d.m3.forecaster/1"
HISTORY_MINUTES = (-25, -20, -15, -10, -5, 0)
HORIZON_MINUTES = 30
MAX_SOURCE_BYTES = 1024 * 1024
MAX_SETTINGS_BYTES = 1024 * 1024
MAX_DECLARATION_BYTES = 64 * 1024


def read_regular(path, limit, label):
    """Bound reads, refuse file/direct-parent symlinks and detect changed bytes."""
    path = Path(path)
    require(not is_link(path) and not is_link(path.parent), f"Symlink {label}")
    require(
        stat.S_ISREG(path.stat(follow_symlinks=False).st_mode), f"{label} must be a regular file"
    )
    descriptor = open_regular(path)
    try:
        before = os.fstat(descriptor)
        require(stat.S_ISREG(before.st_mode), f"{label} must be a regular file")
        require(before.st_size <= limit, f"{label} exceeds byte limit")
        with os.fdopen(descriptor, "rb", closefd=False) as stream:
            raw = stream.read(limit + 1)
        after = os.fstat(descriptor)
        current = regular_info(path)

        def signature(value):
            return (
                value.st_dev,
                value.st_ino,
                value.st_size,
                value.st_mtime_ns,
                value.st_ctime_ns,
            )

        require(
            signature(before) == signature(after) == signature(current),
            f"{label} changed during read",
        )
        require(len(raw) <= limit, f"{label} exceeds byte limit")
        return raw
    finally:
        os.close(descriptor)


def _text(value, label):
    require(isinstance(value, str) and bool(value.strip()), f"Missing {label}")


def validate_declaration(value, *, archived=False):
    """Validate the declared boundary without opening or executing source code."""
    require(
        isinstance(value, dict)
        and set(value)
        == {"schema", "id", "reference", "rights", "source", "settings", "training", "contract"},
        "Unsupported forecaster declaration fields",
    )
    require(value["schema"] == SCHEMA, "Unsupported forecaster declaration schema")
    require(isinstance(value["id"], str) and ID.fullmatch(value["id"]), "Invalid forecaster id")
    _text(value["reference"], "forecaster reference")
    require(value["rights"] in ("self-authored", "licensed"), "Unsupported forecaster rights")
    for label in ("source", "settings"):
        identity = value[label]
        require(
            isinstance(identity, dict) and set(identity) == {"file", "sha256"},
            f"Unsupported {label} identity",
        )
        _text(identity["file"], f"{label} file")
        require(
            recorded_path(identity["file"]) if archived else Path(identity["file"]).is_absolute(),
            f"{label} file must be absolute",
        )
        require(
            isinstance(identity["sha256"], str) and SHA.fullmatch(identity["sha256"]),
            f"Invalid {label} hash",
        )
    training = value["training"]
    require(
        isinstance(training, dict)
        and set(training) == {"kind", "reference"}
        and training["kind"] == "synthetic",
        "Only declared synthetic training is supported",
    )
    _text(training["reference"], "synthetic training reference")
    contract = value["contract"]
    require(
        isinstance(contract, dict)
        and set(contract) == {"history_minutes", "horizon_minutes", "unit", "stateless"},
        "Unsupported forecaster contract fields",
    )
    history = contract["history_minutes"]
    require(
        isinstance(history, list)
        and all(type(value) is int for value in history)
        and history == list(HISTORY_MINUTES)
        and type(contract["horizon_minutes"]) is int
        and contract["horizon_minutes"] == HORIZON_MINUTES
        and contract["unit"] == "mg/dL"
        and contract["stateless"] is True,
        "Unsupported causal forecaster contract",
    )


def validate_bundle(declaration, source_bytes, settings_bytes):
    """Check saved raw identities, including original settings whitespace."""
    validate_declaration(declaration, archived=True)
    require(
        isinstance(source_bytes, bytes) and 0 < len(source_bytes) <= MAX_SOURCE_BYTES,
        "Invalid source bytes or byte limit",
    )
    require(
        isinstance(settings_bytes, bytes) and 0 < len(settings_bytes) <= MAX_SETTINGS_BYTES,
        "Invalid settings bytes or byte limit",
    )
    require(digest(source_bytes) == declaration["source"]["sha256"], "Source hash mismatch")
    require(digest(settings_bytes) == declaration["settings"]["sha256"], "Settings hash mismatch")
    settings = strict_json(settings_bytes)
    require(isinstance(settings, dict), "Forecaster settings must be a JSON object")
    try:
        compile(source_bytes, "<m3-forecaster>", "exec")
    except (SyntaxError, ValueError):
        raise ValueError("Invalid forecaster Python source") from None
    return settings


def load_declaration(path):
    """Read and bind all three regular files before any predictor execution."""
    declaration = strict_json(read_regular(path, MAX_DECLARATION_BYTES, "declaration"))
    validate_declaration(declaration)
    source = read_regular(declaration["source"]["file"], MAX_SOURCE_BYTES, "source")
    settings = read_regular(declaration["settings"]["file"], MAX_SETTINGS_BYTES, "settings")
    validate_bundle(declaration, source, settings)
    return declaration, source, settings
