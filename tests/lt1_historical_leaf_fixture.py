"""Fresh invented mixed-parent data only; never accepts an existing audit path."""

import json
import os
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from experiments.lt1_diagnostic import historical_leaf_removal as leaf  # noqa: E402


def directory(path):
    info = path.stat()
    return {"path": str(path), **{k: v for k, v in leaf.signature(info).items() if k != "bytes"}}


def command(parent, phase="complete"):
    return [sys.executable, "-I", "-S", "-B", str(Path(__file__).resolve()), str(parent), phase]


def prepare(parent, phase="complete"):
    parent = Path(parent).resolve()
    parent.chmod(0o700)
    root, reports = parent / "mixed", parent / "reports"
    root.mkdir(mode=0o700)
    reports.mkdir(mode=0o700)
    target = root / "invented-decision.json"
    target.write_bytes(b'{"invented": true}\n')
    target.chmod(0o600)
    sibling = root / "preserved.txt"
    sibling.write_bytes(b"invented unrelated sibling\n")
    sibling.chmod(0o600)
    nested = root / "preserved-folder"
    nested.mkdir(mode=0o700)
    (nested / "untouched.txt").write_bytes(b"invented nested sentinel\n")
    context = (
        json.dumps(
            {
                "schema": "opent1d.lt1-historical-leaf-context/1",
                "acl_scope_reviewed": True,
                "process_quiescent": True,
                "exclusive_ownership_reviewed": True,
                "recovery_disposition_sha256": leaf.digest(b"invented scoped recovery disposition"),
                "outer_argv_sha256": leaf.command_digest(command(parent, phase)),
            },
            sort_keys=True,
        )
        + "\n"
    ).encode()
    request = {
        "schema": leaf.SCHEMA,
        "kind": "invented",
        "root": directory(root),
        "evidence_parent": directory(reports),
        "attempt": "attempt-one",
        "target": {
            "name": target.name,
            "file": {**leaf.signature(target.stat()), "sha256": leaf.digest(target.read_bytes())},
        },
        "siblings": {p.name: leaf.sibling_signature(p.lstat()) for p in (sibling, nested)},
        "source_identity": leaf.source_identity(),
        "host": leaf.host(),
        "context_sha256": leaf.digest(context),
    }
    raw = (json.dumps(request, sort_keys=True) + "\n").encode()
    registry = {"schema": "opent1d.lt1-removal-admissions/1", "requests": [leaf.digest(raw)]}
    return raw, registry, context, target, reports / request["attempt"]


def outer(raw, supervision=None):
    if supervision is None:
        request = json.loads(raw)
        parent = Path(request["root"]["path"]).parent
        supervision = {
            "status": "completed",
            "error": None,
            "exit_code": 0,
            "remaining_owned_processes": [],
            "received_signals": [],
            "argv": command(parent),
            "cleanup_forced": False,
            "owned_processes": [
                {
                    "pid": 12345,
                    "ppid": 12344,
                    "pgid": 12345,
                    "start": "invented-fixture-identity",
                    "alive": False,
                }
            ],
        }
    return (
        json.dumps(
            {
                "schema": "opent1d.lt1-historical-leaf-outer/1",
                "request_sha256": leaf.digest(raw),
                "supervision": supervision,
            },
            sort_keys=True,
        )
        + "\n"
    ).encode()


def main():
    parent, phase = Path(sys.argv[1]), sys.argv[2]
    raw, registry, context, _target, _attempt = prepare(parent, phase)
    (parent / "request.json").write_bytes(raw)
    (parent / "context.json").write_bytes(context)

    def checkpoint(event, _name):
        if event == phase:
            with (parent / "ready").open("xb") as stream:
                stream.write(event.encode())
                stream.flush()
                os.fsync(stream.fileno())
            while True:
                time.sleep(0.02)

    result = leaf._remove_reviewed(raw, registry, context, checkpoint=checkpoint)
    with (parent / "outcome.json").open("x") as stream:
        json.dump(result, stream)
        stream.flush()
        os.fsync(stream.fileno())
    return 0 if result["status"] == leaf.STATUS else 23


if __name__ == "__main__":
    raise SystemExit(main())
