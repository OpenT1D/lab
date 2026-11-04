"""Fresh invented producer, retaining bytes before fixture-only owned removal."""

import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / "tests")]
import lt1_bundle_removal_fixture as cycle  # noqa: E402


def main():
    parent, phase = Path(sys.argv[1]), sys.argv[2]
    if phase not in {"complete", "quarantined"}:
        raise ValueError("Fixed invented packet fixture phase required")
    raw, registry, context = cycle.prepare(parent)
    for member in ("manifest.json", "intent.json"):
        cycle.write_private(
            parent / ("retained-" + member), (parent / "bundle" / member).read_bytes()
        )

    def checkpoint(event, name):
        if event == phase:
            cycle.write_private(
                parent / "ready.pending", cycle.wire.encoded({"event": event, "name": name})
            )
            (parent / "ready.pending").rename(parent / "ready")
            while True:
                time.sleep(0.02)

    result = cycle.removal._remove_reviewed(raw, registry, context, checkpoint=checkpoint)
    cycle.write_private(parent / "outcome.json", cycle.wire.encoded(result))
    return 0 if result["status"] == "namespace-absence-observed" else 23


def inputs(parent, outer_raw, reconciliation):
    """Parent supplies bytes of the actual shared-owner receipt after exit."""
    allocation = json.loads((parent / "allocation.json").read_bytes())
    names = {
        "base": "base-register.json",
        "registration": "proposed-register.json",
        "policy": "policy.json",
        "allocation": "allocation.json",
        "manifest": "retained-manifest.json",
        "intent": "retained-intent.json",
        "request": "request.json",
        "context": "context.txt",
        "journal": "reports/remove-derived-bundle/events.jsonl",
    }
    raw = {role: (parent / name).read_bytes() for role, name in names.items()}
    raw["outer"] = outer_raw
    wire = reconciliation.wire
    provenance = {
        copy_id: (parent / (copy_id + ".json")).read_bytes()
        for copy_id in allocation["copies"].values()
    }
    return {
        **{role + "_raw": value for role, value in raw.items()},
        **{"expected_" + role + "_sha256": wire.digest(value) for role, value in raw.items()},
        "provenance_raw": provenance,
        "expected_provenance_sha256": {
            key: wire.digest(value) for key, value in provenance.items()
        },
        "as_of": "2026-11-05T12:00:00Z",
        "expected_reader_identity": reconciliation.source_identity(),
    }


if __name__ == "__main__":
    raise SystemExit(main())
