"""Fixed invented data for removal tests; never consumes an existing audit."""

import json
import os
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from experiments.lt1_diagnostic import removal  # noqa: E402


def prepare(parent):
    parent = Path(parent).resolve()
    parent.chmod(0o700)
    target, reports = parent / "target", parent / "reports"
    target.mkdir(mode=0o700)
    reports.mkdir(mode=0o700)
    files = {}
    for name, content in {"a.txt": b"invented-first", "b.txt": b"invented-second"}.items():
        path = target / name
        path.write_bytes(content)
        path.chmod(0o400)
        files[name] = {**removal.signature(path.stat()), "sha256": removal.digest(content)}
    root = target.stat()
    context = b"invented independently reviewed storage/process context\n"
    request = {
        "schema": "opent1d.lt1-removal-request/1",
        "kind": "invented",
        "root": {
            "path": str(target),
            "device": root.st_dev,
            "inode": root.st_ino,
            "uid": root.st_uid,
        },
        "evidence_parent": str(reports),
        "attempt": "attempt-one",
        "files": files,
        "source_identity": removal.source_identity(),
        "host": removal.host(),
        "context_sha256": removal.digest(context),
    }
    raw = (json.dumps(request, sort_keys=True) + "\n").encode()
    registry = {"schema": "opent1d.lt1-removal-admissions/1", "requests": [removal.digest(raw)]}
    return raw, registry, context, target, reports / request["attempt"]


def main():
    parent, behavior = Path(sys.argv[1]), sys.argv[2]
    raw, registry, context, _target, _attempt = prepare(parent)
    (parent / "request.json").write_bytes(raw)
    (parent / "context.txt").write_bytes(context)

    def checkpoint(event, name):
        if event == behavior:
            with (parent / "ready").open("xb") as stream:
                stream.write(event.encode())
                stream.flush()
                os.fsync(stream.fileno())
            while True:
                time.sleep(0.02)

    outcome = removal._remove_reviewed(raw, registry, context, checkpoint=checkpoint)
    with (parent / "outcome.json").open("x") as stream:
        json.dump(outcome, stream)
        stream.flush()
        os.fsync(stream.fileno())
    return 0 if outcome["status"] == "namespace-absence-observed" else 23


if __name__ == "__main__":
    raise SystemExit(main())
