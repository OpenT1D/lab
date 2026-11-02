"""Owned scripted setup stop cases, with fixed invented bytes only."""

import json
import platform
import socket
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from experiments.lt1_diagnostic import frozen_setup as stage  # noqa: E402


def main(parent, behavior):
    parent = Path(parent).resolve()
    blobs = {"one": b"invented-first", "two": b"invented-second", "review": b"invented-unapproved"}
    inputs = {name: {"bytes": len(raw), "sha256": stage.digest(raw)} for name, raw in blobs.items()}
    request = {
        "schema": "opent1d.lt1-materialization-request/1",
        "kind": "invented",
        "parent": str(parent),
        "name": "attempt",
        "inputs": inputs,
        "files": {
            path: {"input": name, **inputs[name], "mode": 0o400}
            for path, name in (("a.txt", "one"), ("b.txt", "two"))
        },
        "review_receipts": {role: "review" for role in ("rights", "security", "harness")},
        "stager_identity": stage.source_identity(),
        "host": socket.gethostname(),
        "platform": sys.platform,
        "machine": platform.machine(),
    }
    raw = json.dumps(request).encode()
    registry = {"schema": "opent1d.lt1-setup-request-admissions/1", "requests": [stage.digest(raw)]}
    original = stage._write_at

    def block(folder, name, value, mode):
        if (behavior == "prefix" and name == "b.txt") or (
            behavior == "pending" and name == ".inventory.pending"
        ):
            # In the pending case retain the full temporary marker, but never
            # link it to the published inventory before the outer stop.
            if behavior == "pending":
                original(folder, name, value, mode)
            (parent / "ready").write_bytes(b"invented ready")
            while True:
                time.sleep(0.1)
        return original(folder, name, value, mode)

    stage._write_at = block
    stage._materialize_reviewed(raw, registry, lambda name, limit: blobs[name])


if __name__ == "__main__":
    main(*sys.argv[1:])
