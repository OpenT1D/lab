"""Fresh generated trees and externally pinned invented copy records only."""

from pathlib import Path

from experiments.lt1_diagnostic import native_tree_removal as tree
from experiments.lt1_diagnostic import native_tree_removal_exec as runner


def signature(path):
    return tree.directory_signature(Path(path).stat())


def pin(root):
    root = Path(root)
    files, directories = {}, {}
    for path in sorted(root.iterdir()):
        if path.is_dir():
            directories[path.name] = signature(path)
            leaves = sorted(path.iterdir())
        else:
            leaves = [path]
        for leaf in leaves:
            files[leaf.relative_to(root).as_posix()] = {
                **tree.removal.signature(leaf.stat()),
                "sha256": tree.digest(leaf.read_bytes()),
            }
    return {"files": files, "directories": directories}


def prepare(
    parent,
    *,
    role="output",
    root=None,
    cleanup=None,
    attempt="remove-once",
    context=None,
    files=None,
    producer=None,
    retained_since="2026-11-01T00:00:00Z",
    hold=False,
    copy_id="original-copy",
):
    parent = Path(parent).resolve()
    parent.chmod(0o700)
    root = Path(root) if root is not None else parent / "original"
    cleanup = Path(cleanup) if cleanup is not None else parent / "cleanup"
    if not root.exists():
        root.mkdir(mode=0o700)
        for name, raw in (files or {}).items():
            leaf = root / name
            if leaf.parent != root:
                leaf.parent.mkdir(mode=0o700, exist_ok=True)
            leaf.write_bytes(raw)
            leaf.chmod(0o600)
    cleanup.mkdir(mode=0o700, exist_ok=True)
    context_raw = tree.encoded(context or {"kind": "invented"})
    inherited = {
        "retained_since": retained_since,
        "origin_evidence_sha256": "a" * 64 if retained_since else None,
        "hold": hold,
    }
    producer = producer or {
        "implementation": {"tests/invented-producer.py": "b" * 64},
        "python": "invented",
        "executable_sha256": "c" * 64,
    }
    root_id = {"path": str(root), **signature(root)}
    allocation = {
        "schema": "opent1d.lt1-native-tree-copy-allocation/1",
        "kind": "invented",
        "role": role,
        "subject": "subject-one",
        "copy": copy_id,
        "root": root_id,
        "producer": producer,
        "context_sha256": tree.digest(context_raw),
        "inherited": inherited,
    }
    allocation_raw = tree.encoded(allocation)
    audit = tree.source_identity()
    request = {
        "schema": "opent1d.lt1-native-tree-removal-request/1",
        "kind": "invented",
        "role": role,
        "subject": "subject-one",
        "copy": copy_id,
        "allocation_sha256": tree.digest(allocation_raw),
        "root": root_id,
        "parent": {"path": str(root.parent), **signature(root.parent)},
        "cleanup_parent": {"path": str(cleanup), **signature(cleanup)},
        "attempt": attempt,
        "inventory": pin(root),
        "code_source": tree.code_source(audit),
        "host": tree.host(),
        "context_sha256": tree.digest(context_raw),
        "producer": producer,
    }
    raw = tree.encoded(request)
    policy_raw = tree.encoded(
        {
            "schema": "opent1d.lt1-retention-policy/1",
            "maximum_age_seconds": 30 * 86400,
            "extensions_allowed": False,
            "exports_allowed": False,
        }
    )
    register_raw = tree.encoded(
        {
            "schema": "opent1d.lt1-retention-register/1",
            "policy_sha256": tree.digest(policy_raw),
            "previous_sha256": None,
            "subjects": {
                "subject-one": {
                    **inherited,
                    "copies": {
                        copy_id: {
                            "state": "present",
                            "evidence_sha256": tree.digest(allocation_raw),
                        },
                        "other-copy": {"state": "present", "evidence_sha256": "d" * 64},
                    },
                }
            },
            "coverage": {
                "all_copies_registered": False,
                "recovery_scope_reviewed": False,
                "recoverable_until": None,
                "processes_stopped": False,
                "context_sha256": tree.digest(context_raw),
            },
        }
    )
    return dict(
        raw=raw,
        context=context_raw,
        audit=audit,
        request=request,
        allocation_raw=allocation_raw,
        register_raw=register_raw,
        policy_raw=policy_raw,
        root=root,
        cleanup=cleanup,
        grants={"schema": "opent1d.lt1-removal-admissions/1", "requests": [tree.digest(raw)]},
    )


def run(value, **kwargs):
    return runner._run_reviewed(
        value["raw"], value["grants"], value["context"], value["audit"], invented=True, **kwargs
    )


def journal(value):
    path = value["cleanup"] / value["request"]["attempt"] / "events.jsonl"
    return path.read_bytes() if path.exists() else b""


def inspect(value, outer, *, reader_audit=None):
    return tree.inspect(
        value["raw"],
        tree.digest(value["raw"]),
        value["context"],
        tree.digest(journal(value)),
        outer,
        audit=value["audit"],
        expected_outer_sha256=tree.digest(tree.encoded(outer)),
        expected_audit_sha256=tree.digest(tree.encoded(value["audit"])),
        reader_audit=reader_audit or value["audit"],
        invented=True,
    )


def proposal(value, outer):
    return dict(
        register_raw=value["register_raw"],
        expected_register_sha256=tree.digest(value["register_raw"]),
        policy_raw=value["policy_raw"],
        expected_policy_sha256=tree.digest(value["policy_raw"]),
        provenance_raw={"original-copy": value["allocation_raw"]},
        expected_provenance_sha256={"original-copy": tree.digest(value["allocation_raw"])},
        request_raw=value["raw"],
        expected_request_sha256=tree.digest(value["raw"]),
        context_raw=value["context"],
        journal_raw=journal(value),
        expected_journal_sha256=tree.digest(journal(value)),
        outer_receipt=outer,
        expected_outer_sha256=tree.digest(tree.encoded(outer)),
        audit=value["audit"],
        expected_audit_sha256=tree.digest(tree.encoded(value["audit"])),
        reader_audit=value["audit"],
        allocation_raw=value["allocation_raw"],
        expected_allocation_sha256=tree.digest(value["allocation_raw"]),
        record_copy_ids={
            name: "record-" + name
            for name in ("request", "control", "journal", "launch-log", "outer", "readback")
        },
        as_of="2026-11-05T12:00:00Z",
        invented=True,
    )
