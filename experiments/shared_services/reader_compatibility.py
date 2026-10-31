"""One packaged, reviewed comparison transition; project snapshots stay opaque."""

from pathlib import Path

from experiments.m3.researcher.intake import read_regular

from .store import decode, digest, encoded, require

REGISTRY = Path(__file__).with_name("reader_compatibility.json")
SCHEMA = "opent1d.comparison-reader-transition/1"
TASKS = ["mmtt-sensitivity", "mmtt-sampling"]


def policy():
    return {"schema": SCHEMA, "registry_sha256": digest(registry_bytes())}


def registry_bytes():
    return read_regular(REGISTRY, 1024 * 1024, "packaged comparison compatibility registry")


def same(left, right):
    return isinstance(left, dict) and isinstance(right, dict) and encoded(left) == encoded(right)


def accepts(saved, current, task):
    if same(saved, current):
        return True
    raw = registry_bytes()
    registry = decode(raw)
    require(
        isinstance(registry, dict)
        and set(registry) == {"schema", "predecessor_revision", "tasks", "predecessor", "successor"}
        and registry["schema"] == SCHEMA
        and registry["tasks"] == TASKS,
        "Unsupported comparison compatibility registry",
    )
    return (
        task in TASKS
        and same(saved, registry["predecessor"])
        and same(current.get("compatibility"), {"schema": SCHEMA, "registry_sha256": digest(raw)})
        and same(
            {key: value for key, value in current.items() if key != "compatibility"},
            registry["successor"],
        )
    )


def receipt(saved, current, task):
    require(accepts(saved, current, task), "Unsupported comparison reader transition")
    return {
        "policy": "exact-current" if same(saved, current) else SCHEMA,
        "original_reader_sha256": digest(encoded(saved)),
        "current_reader_sha256": digest(encoded(current)),
        "registry_sha256": policy()["registry_sha256"],
    }
