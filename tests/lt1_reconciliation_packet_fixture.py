"""Fresh invented producer, retaining bytes before fixture-only owned removal."""

import json
import os
import stat
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / "tests")]
import lt1_bundle_removal_fixture as cycle  # noqa: E402


def need(ok, reason):
    if not ok:
        raise ValueError("Invented packet producer refused: " + reason)


def directory_identity(path):
    info = path.lstat()
    need(
        path.resolve() == path
        and stat.S_ISDIR(info.st_mode)
        and info.st_uid == os.getuid()
        and stat.S_IMODE(info.st_mode) == 0o700,
        "private canonical directory",
    )
    return {"device": info.st_dev, "inode": info.st_ino, "uid": info.st_uid}


def prepare(parent):
    """Construct fresh invented inputs before the 30-second removal owner starts.

    cycle.json honestly records this preparation process's flags. The separate
    fixed worker checks its own -I/-S/-B flags instead of relabeling preparation.
    """
    raw, _registry, context = cycle.prepare(parent)
    for member in ("manifest.json", "intent.json"):
        cycle.write_private(
            parent / ("retained-" + member), (parent / "bundle" / member).read_bytes()
        )
    request = json.loads(raw)
    records = {}
    for path in parent.iterdir():
        if path.is_file():
            value = path.read_bytes()
            records[path.name] = {"bytes": len(value), "sha256": cycle.wire.digest(value)}
    return {
        "request_sha256": cycle.wire.digest(raw),
        "context_sha256": cycle.wire.digest(context),
        "source_sha256": cycle.wire.digest(cycle.wire.encoded(cycle.removal.source_identity())),
        "helper_sha256": cycle.wire.digest(Path(__file__).read_bytes()),
        "parent": directory_identity(parent),
        "root": request["root"],
        "evidence": directory_identity(parent / "reports"),
        "files": records,
    }


def _read_private(folder, name, record):
    fd = os.open(name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK | os.O_CLOEXEC, dir_fd=folder)
    try:
        before = os.fstat(fd)
        need(
            stat.S_ISREG(before.st_mode)
            and before.st_nlink == 1
            and before.st_uid == os.getuid()
            and stat.S_IMODE(before.st_mode) == 0o600
            and before.st_size == record["bytes"],
            "private prepared input",
        )
        value = b""
        while part := os.read(fd, min(65536, record["bytes"] + 1 - len(value))):
            value += part
            need(len(value) <= record["bytes"], "prepared input grew")
        live = os.stat(name, dir_fd=folder, follow_symlinks=False)
        need(
            cycle.removal.signature(before)
            == cycle.removal.signature(os.fstat(fd))
            == cycle.removal.signature(live)
            and live.st_nlink == 1
            and len(value) == record["bytes"]
            and cycle.wire.digest(value) == record["sha256"],
            "prepared input bytes/binding",
        )
        return value
    finally:
        os.close(fd)


def load_prepared(parent, pins):
    """Validate only the externally pinned fresh invented fixture namespace."""
    removal, wire = cycle.removal, cycle.wire
    removal.fields(
        pins, "request_sha256 context_sha256 source_sha256 helper_sha256 parent root evidence files"
    )
    for key in ("request_sha256", "context_sha256", "source_sha256", "helper_sha256"):
        need(removal.sha(pins[key]), "external hash pin")
    for key in ("parent", "evidence", "root"):
        removal.fields(pins[key], "path device inode uid" if key == "root" else "device inode uid")
        need(
            all(
                type(pins[key][k]) is int and pins[key][k] >= 0 for k in ("device", "inode", "uid")
            ),
            "typed directory pin",
        )
    records = pins["files"]
    need(
        isinstance(records, dict) and 0 < len(records) <= removal.MAX_FILES, "prepared record count"
    )
    for name, record in records.items():
        removal.safe_name(name)
        removal.fields(record, "bytes sha256")
        need(
            type(record["bytes"]) is int
            and 0 <= record["bytes"] <= removal.REQUEST_LIMIT
            and removal.sha(record["sha256"]),
            "bounded prepared record",
        )
    need(
        sum(row["bytes"] for row in records.values()) <= removal.TOTAL_LIMIT,
        "prepared aggregate bound",
    )
    need(
        wire.digest(Path(__file__).read_bytes()) == pins["helper_sha256"], "fixed helper source pin"
    )
    need(
        wire.digest(wire.encoded(removal.source_identity())) == pins["source_sha256"],
        "current removal source pin",
    )
    need(directory_identity(parent) == pins["parent"], "parent identity pin")
    fd = removal._private_directory(parent)
    try:
        removal._binding(parent, fd)
        need(removal.names(fd) == set(records) | {"bundle", "reports"}, "closed prepared prefix")
        values = {name: _read_private(fd, name, record) for name, record in records.items()}
        required = {
            "original-object.txt",
            "base-register.json",
            "policy.json",
            "allocation.json",
            "proposed-register.json",
            "request.json",
            "context.txt",
            "cycle.json",
            "retained-manifest.json",
            "retained-intent.json",
        }
        need(required <= values.keys(), "fixed prepared roles")
        allocation = json.loads(values["allocation.json"], object_pairs_hook=removal.unique_object)
        intent = json.loads(values["retained-intent.json"], object_pairs_hook=removal.unique_object)
        need(isinstance(allocation, dict) and isinstance(intent, dict), "prepared metadata objects")
        assigned = allocation.get("copies")
        need(
            isinstance(assigned, dict) and assigned.keys() == intent.get("subjects", {}).keys(),
            "invented allocation subjects",
        )
        need(
            assigned == {name: f"derived-{i}" for i, name in enumerate(sorted(assigned))},
            "fixed invented copy names",
        )
        need(
            set(values) == required | {name + ".json" for name in assigned.values()},
            "closed prepared roles",
        )
        raw, context = values["request.json"], values["context.txt"]
        need(
            wire.digest(raw) == pins["request_sha256"]
            and wire.digest(context) == pins["context_sha256"],
            "request/context pins",
        )
        request = removal._request(raw, context)
        need(
            request["kind"] == "invented"
            and request["root"] == pins["root"]
            and request["root"]["path"] == str(parent / "bundle")
            and request["evidence_parent"] == str(parent / "reports")
            and request["attempt"] == "remove-derived-bundle"
            and allocation.get("kind") == intent.get("kind") == "invented"
            and intent.get("output_name") == "bundle",
            "fixed invented removal boundary",
        )
        manifest_raw = values["retained-manifest.json"]
        manifest = json.loads(manifest_raw, object_pairs_hook=removal.unique_object)
        removal.fields(manifest, "schema files")
        need(
            manifest["schema"] == "opent1d.lt1-review-bundle/1"
            and isinstance(manifest["files"], dict),
            "retained manifest container",
        )
        need(
            {
                name: {key: row[key] for key in ("bytes", "sha256")}
                for name, row in request["files"].items()
            }
            == {
                **manifest["files"],
                "manifest.json": {"bytes": len(manifest_raw), "sha256": wire.digest(manifest_raw)},
            },
            "exact whole invented bundle",
        )
        need(
            manifest["files"].get("intent.json")
            == {
                "bytes": len(values["retained-intent.json"]),
                "sha256": wire.digest(values["retained-intent.json"]),
            },
            "retained intent pin",
        )
        need(
            directory_identity(parent / "bundle")
            == {k: request["root"][k] for k in ("device", "inode", "uid")},
            "target identity pin",
        )
        need(
            directory_identity(parent / "reports") == pins["evidence"]
            and not any((parent / "reports").iterdir()),
            "fresh evidence identity pin",
        )
        need(directory_identity(parent) == pins["parent"], "final parent pin")
        removal._binding(parent, fd)
        return raw, context
    finally:
        os.close(fd)


def main():
    need(len(sys.argv) == 4 and len(sys.argv[3]) <= 16384, "bounded external fixture pins")
    need(
        sys.flags.isolated and sys.flags.no_site and sys.flags.dont_write_bytecode,
        "fixed isolated removal worker",
    )
    parent, phase = Path(sys.argv[1]), sys.argv[2]
    need(phase in {"complete", "quarantined"}, "fixed invented packet fixture phase")
    raw, context = load_prepared(
        parent, json.loads(sys.argv[3], object_pairs_hook=cycle.removal.unique_object)
    )
    try:
        cycle.removal.remove(raw, context)
    except ValueError as error:
        need("no reviewed removal request" in str(error), "production gate refusal")
    else:
        raise AssertionError("Production gate admitted invented bundle removal")

    def checkpoint(event, name):
        if event == phase:
            cycle.write_private(
                parent / "ready.pending", cycle.wire.encoded({"event": event, "name": name})
            )
            (parent / "ready.pending").rename(parent / "ready")
            while True:
                time.sleep(0.02)

    registry = {"schema": "opent1d.lt1-removal-admissions/1", "requests": [cycle.wire.digest(raw)]}
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
