"""Exact packaged comparison transitions; historical registry stays immutable."""

from pathlib import Path

from experiments.m3.researcher.intake import read_regular

from .store import decode, digest, encoded, require

REGISTRY = Path(__file__).with_name("reader_compatibility.json")
CURRENT_REGISTRY = Path(__file__).with_name("reader_compatibility_m3.json")
LEGACY_SCHEMA = "opent1d.comparison-reader-transition/1"
SCHEMA = "opent1d.comparison-reader-transition/2"
LEGACY_SHA256 = "6b50b5b97f9888e55f2fdddd86388a35963ce090291f37850cffb4863ed6f0e0"
M3_PREDECESSOR_REVISION = "6e77f7b86d3418ac5702dfb1efdd0edf68cabd90"
M3_PREDECESSOR_SHA256 = "b6fb575b6bf5532a53f0fb2fd20a3efad5bfadc162dae9f010a2e0d6442e24ec"
TASKS = ["mmtt-sensitivity", "mmtt-sampling"]


def registry_bytes():
    raw = read_regular(REGISTRY, 1024 * 1024, "historical comparison compatibility registry")
    require(digest(raw) == LEGACY_SHA256, "Historical comparison registry identity differs")
    return raw


def historical():
    registry = decode(registry_bytes())
    require(
        isinstance(registry, dict)
        and set(registry) == {"schema", "predecessor_revision", "tasks", "predecessor", "successor"}
        and registry["schema"] == LEGACY_SCHEMA
        and registry["tasks"] == TASKS,
        "Unsupported historical comparison compatibility registry",
    )
    return registry


def current_bytes():
    raw = read_regular(CURRENT_REGISTRY, 1024 * 1024, "current comparison compatibility packet")
    registry = decode(raw)
    require(
        isinstance(registry, dict)
        and set(registry)
        == {
            "schema",
            "historical_registry_sha256",
            "tasks",
            "successor",
            "m3_predecessor_revision",
            "m3_predecessor",
        }
        and registry["schema"] == SCHEMA
        and registry["historical_registry_sha256"] == LEGACY_SHA256
        and registry["tasks"] == TASKS
        and registry["m3_predecessor_revision"] == M3_PREDECESSOR_REVISION
        and digest(encoded(registry["m3_predecessor"])) == M3_PREDECESSOR_SHA256
        and isinstance(registry["successor"], dict),
        "Unsupported current comparison compatibility packet",
    )
    registry_bytes()
    return raw


def policy():
    return {"schema": SCHEMA, "registry_sha256": digest(current_bytes())}


def same(left, right):
    return isinstance(left, dict) and isinstance(right, dict) and encoded(left) == encoded(right)


def historical_successor():
    return historical()["successor"] | {
        "compatibility": {"schema": LEGACY_SCHEMA, "registry_sha256": LEGACY_SHA256}
    }


def accepts(saved, current, task):
    if same(saved, current):
        return True
    if task not in TASKS or not isinstance(current, dict):
        return False
    legacy = historical()
    # Retain the original complete A -> B entry; no historical bytes are refreshed.
    if same(current, historical_successor()):
        return same(saved, legacy["predecessor"])
    raw = current_bytes()
    qualified = decode(raw)
    return (
        (
            same(saved, legacy["predecessor"])
            or same(saved, historical_successor())
            or same(saved, qualified["m3_predecessor"])
        )
        and same(current.get("compatibility"), {"schema": SCHEMA, "registry_sha256": digest(raw)})
        and same(
            {key: value for key, value in current.items() if key != "compatibility"},
            qualified["successor"],
        )
    )


def receipt(saved, current, task):
    require(accepts(saved, current, task), "Unsupported comparison reader transition")
    selected = current.get("compatibility") or policy()
    return {
        "policy": "exact-current" if same(saved, current) else selected["schema"],
        "original_reader_sha256": digest(encoded(saved)),
        "current_reader_sha256": digest(encoded(current)),
        "registry_sha256": selected["registry_sha256"],
    }
