"""Exact packaged comparison transitions; historical registry stays immutable."""

from pathlib import Path

from experiments.m3.researcher.intake import read_regular

from .store import decode, digest, encoded, require

REGISTRY = Path(__file__).with_name("reader_compatibility.json")
CURRENT_REGISTRY = Path(__file__).with_name("reader_compatibility_m3.json")
SUCCESSOR_REGISTRY = Path(__file__).with_name("reader_compatibility_mmtt_input_limits.json")
LEGACY_SCHEMA = "opent1d.comparison-reader-transition/1"
SCHEMA = "opent1d.comparison-reader-transition/2"
SUCCESSOR_SCHEMA = "opent1d.mmtt-input-limits-reader-transition/1"
LEGACY_SHA256 = "6b50b5b97f9888e55f2fdddd86388a35963ce090291f37850cffb4863ed6f0e0"
M3_PREDECESSOR_REVISION = "6e77f7b86d3418ac5702dfb1efdd0edf68cabd90"
M3_PREDECESSOR_SHA256 = "b6fb575b6bf5532a53f0fb2fd20a3efad5bfadc162dae9f010a2e0d6442e24ec"
TASKS = ["mmtt-sensitivity", "mmtt-sampling"]
PREDECESSOR_SHA256 = {
    "comparison": "abf50add6bec0044a5fcdb127161cf24b739144b5f4363d76dcf16b2ba968d0d",
    "connected": "c1ca24dc17f0c67071efa32f0ca954fff57ba619d3d833ac7cfa34608a1add8e",
    "m4-attachment-sources": "cf93b96d90347b05233a83ab320600e5ea208b15ed37b2ae8e4aa6bb2ee26d33",
    "m4-study-installed": "2b858e66eb933ab56aef39163500b5f11c08fe9ea524a498874bea08c701ac34",
}


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


def successor_packet():
    raw = read_regular(SUCCESSOR_REGISTRY, 4096, "MMTT input-limit reader qualification")
    packet = decode(raw)
    require(
        isinstance(packet, dict)
        and set(packet) == {"schema", "successor_sha256"}
        and packet["schema"] == SUCCESSOR_SCHEMA
        and isinstance(packet["successor_sha256"], dict)
        and set(packet["successor_sha256"]) == set(PREDECESSOR_SHA256),
        "Unsupported MMTT input-limit reader qualification",
    )
    return {"schema": SUCCESSOR_SCHEMA, "registry_sha256": digest(raw)}, packet["successor_sha256"]


def policy():
    return successor_packet()[0]


def same(left, right):
    return isinstance(left, dict) and isinstance(right, dict) and encoded(left) == encoded(right)


def historical_successor():
    return historical()["successor"] | {
        "compatibility": {"schema": LEGACY_SCHEMA, "registry_sha256": LEGACY_SHA256}
    }


def qualified_successor(kind, current):
    policy, successors = successor_packet()
    if kind == "comparison":
        # Verify the packet binding separately because it contains the packet's own digest.
        if not same(current.get("compatibility"), policy):
            return False
        current = {key: value for key, value in current.items() if key != "compatibility"}
    return digest(encoded(current)) == successors[kind]


def accepts_predecessor(kind, saved, current):
    return (
        isinstance(saved, dict)
        and isinstance(current, dict)
        and digest(encoded(saved)) == PREDECESSOR_SHA256[kind]
        and qualified_successor(kind, current)
    )


def accepts(saved, current, task):
    if same(saved, current):
        return True
    if task in (*TASKS, "m4-study-installed") and accepts_predecessor("comparison", saved, current):
        return True
    if task not in TASKS or not isinstance(current, dict):
        return False
    legacy = historical()
    # Retain the original complete A -> B entry; no historical bytes are refreshed.
    if same(current, historical_successor()):
        return same(saved, legacy["predecessor"])
    raw = current_bytes()
    qualified = decode(raw)
    binding = {"schema": SCHEMA, "registry_sha256": digest(raw)}
    previous = qualified["successor"] | {"compatibility": binding}
    if accepts_predecessor("comparison", previous, current):
        current = previous
    return (
        (
            same(saved, legacy["predecessor"])
            or same(saved, historical_successor())
            or same(saved, qualified["m3_predecessor"])
        )
        and same(current.get("compatibility"), binding)
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
