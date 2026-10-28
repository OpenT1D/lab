"""Fixed follow-up conventions, independent of the historical exact-time route."""

import subprocess
import sys

from experiments.m3.common import ROOT, digest
from experiments.m3.physiocgm_evaluation.common import _sources as historical_sources

SCHEMA = "opent1d.physiocgm.timing/1"
PROTOCOL = "M3-PHYSIOCGM-TIMING/0.1"
METRIC = "physiocgm-timing-forecast/1"
SECOND = 1_000_000
MINUTE = 60 * SECOND
RADII_US = RADII = (0, SECOND, 5 * SECOND)
RULES = {
    "radii_us": list(RADII_US),
    "primary_radius_us": SECOND,
    "sensitivity_radius_us": 5 * SECOND,
    "history_offsets_minutes": [-25, -20, -15, -10, -5, 0],
    "nominal_horizon_minutes": 30,
    "warmup_minutes": 60,
    "matching": "unique-nearest-time-first-inclusive-radius-no-fallback",
    "history_available_by_origin": True,
    "origin_exact": True,
    "target_does_not_select_forecast": True,
    "interpolation_rounding_or_refitting": False,
    "primary": "equal-person-paired-MAE-ridge-minus-persistence",
    "contributor_floor": {"paired_origins": 288, "span_minutes": 1440},
    "bootstrap": {"people": True, "draws": 2000, "seed": 301, "orders": [50, 1950]},
    "added_subsets": "at-least-one-paired-origin-per-person-no-zero-imputation-no-bootstrap",
    "interpretation": "post-hoc-followup-on-known-material-not-a-fresh-external-test",
}


def provenance():
    paths = list((ROOT / "experiments/m3/physiocgm_timing").glob("*.py"))
    paths += [
        ROOT / "docs/research/physiocgm-timing-protocol.md",
        ROOT / "docs/decisions/0015-physiocgm-timing-followup.md",
    ]
    return {
        "sources": historical_sources()
        | {str(path.relative_to(ROOT)): digest(path.read_bytes()) for path in paths},
        "revision": subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True
        ).strip(),
        "dirty": bool(subprocess.check_output(["git", "status", "--porcelain"], cwd=ROOT)),
        "python": sys.version,
    }
