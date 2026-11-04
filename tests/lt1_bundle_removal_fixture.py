"""One fresh invented bundle cycle; never admits an existing removal request."""

import os
import stat
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / "tests")]
from test_lt1_recovery_readback import RecoveryReadbackTests  # noqa: E402

from experiments.lt1_diagnostic import bundle_registration as registration  # noqa: E402

bundle, wire, removal = (
    registration.review_bundle,
    registration.wire,
    registration.review_bundle.removal,
)
ORIGINAL = b"invented original object, outside the derived bundle\n"


def write_private(path, raw):
    with os.fdopen(os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600), "wb") as stream:
        stream.write(raw)
        stream.flush()
        os.fsync(stream.fileno())


def prepare(parent):
    """Construct every consumed byte in an empty, owned disposable directory."""
    parent = Path(parent)
    if parent.resolve() != parent or any(parent.iterdir()):
        raise ValueError("Fresh empty canonical fixture directory required")
    info = parent.stat()
    if info.st_uid != os.getuid() or stat.S_IMODE(info.st_mode) != 0o700:
        raise ValueError("Owned private fixture directory required")
    f = RecoveryReadbackTests()
    f.setUp()
    context = b"invented bundle-cycle storage/process context\n"
    context_sha = wire.digest(context)
    f.fixture.context = context_sha
    f.current["coverage"].update(
        context_sha256=context_sha, recoverable_until="2026-12-01T00:00:00Z"
    )
    f.fixture.scope["context_sha256"] = context_sha
    f.mapping["context_sha256"] = context_sha
    f.current["subjects"]["unknown-object"] = {
        "retained_since": None,
        "origin_evidence_sha256": None,
        "hold": True,
        "copies": {"unknown-original": {"state": "present", "evidence_sha256": "d" * 64}},
    }
    f.fixture.scope["copy_channels"]["unknown-original"] = "live"
    inputs = f.args()
    target, reports = parent / "bundle", parent / "reports"
    reports.mkdir(mode=0o700)
    saved = bundle.save_review_bundle(target, **inputs)
    if saved["status"] != "published" or not saved["durability_confirmed"]:
        raise RuntimeError("Fresh invented bundle did not publish")
    allocation = {
        "schema": "opent1d.lt1-bundle-copy-allocation/1",
        "kind": "invented",
        "manifest_sha256": saved["manifest_sha256"],
        "register_sha256": inputs["expected_register_sha256"],
        "policy_sha256": inputs["expected_policy_sha256"],
        "context_sha256": context_sha,
        "source_identity": registration.source_identity(),
        "copies": {name: f"derived-{i}" for i, name in enumerate(sorted(f.current["subjects"]))},
    }
    allocation_raw = wire.encoded(allocation)
    proposed = registration.propose_registration(
        target,
        saved["manifest_sha256"],
        inputs["register_raw"],
        inputs["expected_register_sha256"],
        inputs["policy_raw"],
        inputs["expected_policy_sha256"],
        allocation_raw,
        wire.digest(allocation_raw),
        as_of=inputs["as_of"],
        expected_context_sha256=context_sha,
    )
    # The immutable bundle still contains the old base; the unsaved successor
    # does not become the reader's external current-register identity.
    try:
        bundle.prepare_removal_request(
            target,
            saved["manifest_sha256"],
            proposed["register_sha256"],
            context_sha,
            as_of=inputs["as_of"],
            context_raw=context,
            evidence_parent=reports,
            attempt="wrong-base",
        )
    except ValueError as error:
        if "current register identity" not in str(error):
            raise
    else:
        raise AssertionError("Successor register silently rebased immutable bundle")
    prepared = bundle.prepare_removal_request(
        target,
        saved["manifest_sha256"],
        inputs["expected_register_sha256"],
        context_sha,
        as_of=inputs["as_of"],
        context_raw=context,
        evidence_parent=reports,
        attempt="remove-derived-bundle",
    )
    raw = prepared["request_raw"]
    try:
        removal.remove(raw, context)
    except ValueError as error:
        if "no reviewed removal request" not in str(error):
            raise
    else:
        raise AssertionError("Invented cycle unexpectedly passed production removal gate")
    if list(reports.iterdir()):
        raise AssertionError("Unadmitted request created removal evidence")
    retained = {
        "original-object.txt": ORIGINAL,
        "base-register.json": inputs["register_raw"],
        "policy.json": inputs["policy_raw"],
        "allocation.json": allocation_raw,
        "proposed-register.json": proposed["register_raw"],
        "request.json": raw,
        "context.txt": context,
        **{copy_id + ".json": value for copy_id, value in proposed["provenance_raw"].items()},
    }
    for name, value in retained.items():
        write_private(parent / name, value)
    cycle = {
        "schema": "opent1d.invented-bundle-removal-cycle/1",
        "kind": "invented",
        "production_gate_refused": True,
        "successor_cannot_rebase_bundle": True,
        "manifest_sha256": saved["manifest_sha256"],
        "base_register_sha256": inputs["expected_register_sha256"],
        "proposal_register_sha256": proposed["register_sha256"],
        "retained_sha256": {name: wire.digest(value) for name, value in retained.items()},
        "proposal_flags": {key: proposed[key] for key in registration.AUTHORITY},
        "prepared_flags": {key: prepared[key] for key in bundle.AUTHORITY},
        "proposal_saved_or_approved": proposed["saved_or_approved"],
        "global_copy_coverage_verified": proposed["global_copy_coverage_verified"],
        "proposal_deadlines": proposed["assessment"]["deadlines"],
        "isolated": bool(sys.flags.isolated),
        "no_site": bool(sys.flags.no_site),
    }
    write_private(parent / "cycle.json", wire.encoded(cycle))
    # Only bytes just constructed above enter this fixture-only injection.
    registry = {"schema": "opent1d.lt1-removal-admissions/1", "requests": [wire.digest(raw)]}
    return raw, registry, context


def main():
    parent, phase = Path(sys.argv[1]), sys.argv[2]
    if phase not in {"complete", "removed", "quarantined"}:
        raise ValueError("Fixed invented cycle phase required")
    raw, registry, context = prepare(parent)

    def checkpoint(event, name):
        if event == phase:
            write_private(parent / "ready.pending", wire.encoded({"event": event, "name": name}))
            (parent / "ready.pending").rename(parent / "ready")
            while True:
                time.sleep(0.02)

    outcome = removal._remove_reviewed(raw, registry, context, checkpoint=checkpoint)
    write_private(parent / "outcome.json", wire.encoded(outcome))
    return 0 if outcome["status"] == "namespace-absence-observed" else 23


if __name__ == "__main__":
    raise SystemExit(main())
