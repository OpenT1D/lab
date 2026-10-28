"""Independent, versioned frozen-model transfer preparation; no fitting API."""

from pathlib import Path

from experiments.m3.azt1d.common import provenance as upstream_provenance
from experiments.m3.common import ROOT, digest, require

SCHEMA = "opent1d.m3.external/1"
PROTOCOL = "M3-EXTERNAL/0.1"
METRIC = "external-cgm-forecast/1"
FORMAT = "normalized-cgm/1"
RULES = {
    "unit": "mg/dL",
    "history_offsets_minutes": [-25, -20, -15, -10, -5, 0],
    "horizon_minutes": 30,
    "warmup_minutes": 60,
    "matching": "exact",
    "fitting": "forbidden",
    "minimum_paired_windows": 288,
    "minimum_paired_span_minutes": 1440,
}


def provenance():
    value = upstream_provenance()
    paths = sorted((ROOT / "experiments/m3/external").glob("*.py"))
    paths += [ROOT / "docs/research/m3-external-protocol.md"]
    value["sources"].update({str(p.relative_to(ROOT)): digest(p.read_bytes()) for p in paths})
    value["protocol"] = PROTOCOL
    return value


def validate_provenance(value):
    require(
        isinstance(value, dict)
        and value.get("protocol") == PROTOCOL
        and value.get("sources") == provenance()["sources"],
        "External implementation or protocol changed; use the recorded checkout",
    )


def absolute(path):
    require(isinstance(path, str) and Path(path).is_absolute(), "Absolute local path required")
    return Path(path)
