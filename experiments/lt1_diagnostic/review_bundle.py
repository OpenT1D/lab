"""Private immutable recovery proposals; no active register or removal admission.

Only supplied metadata bytes are saved. Interrupted staging is retained. Quiet
owned storage is assumed; publication is exclusive, not hostile-owner isolation.
"""

import os
import stat
from contextlib import contextmanager
from pathlib import Path

from experiments.durable_archives.storage import exclusive_rename
from experiments.lt1_diagnostic import recovery_readback as bridge
from experiments.lt1_diagnostic import removal, retention
from experiments.lt1_diagnostic.control_identity import ROOT, identity
from experiments.lt1_diagnostic.frozen_setup import _private_directory, _read_at, _write_at
from experiments.lt1_diagnostic.native_launcher import _overlap

INPUTS = ("register", "policy", "scope", "mapping", "probe")
MANIFEST = "manifest.json"
INTENT = "intent.json"
AUTHORITY = {**bridge.AUTHORITY, "removal_admitted": False, "new_authority_granted": False}
COPY_SCOPE = {
    "new_bundle_copy_registration_required": True,
    "global_copy_coverage_verified": False,
}


def need(ok, reason):
    if not ok:
        raise ValueError("LT1 review bundle refused: " + reason)


def source_identity():
    return identity(__file__)


def _manifest(files):
    return bridge.encoded(
        {
            "schema": "opent1d.lt1-review-bundle/1",
            "files": {
                name: {"bytes": len(raw), "sha256": bridge.digest(raw)}
                for name, raw in sorted(files.items())
            },
        }
    )


def _material(inputs, output_name):
    """Recompute before path intake; caller dictionaries/bytes are not modified."""
    removal.safe_name(output_name)
    need(not output_name.endswith(".pending"), "reserved pending leaf")
    proposal = bridge.propose(**inputs)
    current = retention.register(inputs["register_raw"], inputs["expected_register_sha256"])
    files = {name + ".json": inputs[name + "_raw"] for name in INPUTS}
    if inputs.get("previous_raw") is not None:
        files["previous.json"] = inputs["previous_raw"]
    intent = {
        "schema": "opent1d.lt1-review-bundle-intent/1",
        "kind": proposal["kind"],
        "output_name": output_name,
        "source_identity": source_identity(),
        "as_of": inputs["as_of"],
        "context_sha256": inputs["expected_context_sha256"],
        "inputs": {
            name: {"bytes": len(raw), "sha256": bridge.digest(raw)}
            for name, raw in sorted(files.items())
        },
        **COPY_SCOPE,
        "subjects": {
            name: {
                **{
                    key: subject[key]
                    for key in ("retained_since", "origin_evidence_sha256", "hold")
                },
                "copies": sorted(subject["copies"]),
            }
            for name, subject in current["subjects"].items()
        },
    }
    files[INTENT] = bridge.encoded(intent)
    files["proposed-register.json"] = proposal["register_raw"]
    files["observations.json"] = proposal["observations_raw"]
    files["assessment.json"] = bridge.encoded(proposal["assessment"])
    index = {}
    for ordinal, (copy_id, raw) in enumerate(sorted(proposal["provenance_raw"].items())):
        name = f"copy-{ordinal:04d}.json"
        index[copy_id] = name
        files[name] = raw
    files["provenance-index.json"] = bridge.encoded(index)
    files[MANIFEST] = _manifest(files)
    _bounds(files)
    return files, proposal, intent


def _bounds(files):
    need(isinstance(files, dict) and 0 < len(files) <= removal.MAX_FILES, "flat file count")
    for name, raw in files.items():
        removal.safe_name(name)
        need(isinstance(raw, bytes) and len(raw) <= removal.FILE_LIMIT, "member byte bound")
    need(sum(map(len, files.values())) <= removal.TOTAL_LIMIT, "aggregate byte bound")


def _directory(path):
    path = Path(path)
    need(
        path.is_absolute() and path.resolve() == path and not _overlap(path, ROOT),
        "canonical private directory outside checkout",
    )
    fd = _private_directory(path)
    try:
        need(stat.S_IMODE(os.fstat(fd).st_mode) == 0o700, "directory mode 0700")
        removal._binding(path, fd)
        return path, fd
    except BaseException:
        os.close(fd)
        raise


@contextmanager
def _opened(path):
    path, fd = _directory(path)
    try:
        yield path, fd
    finally:
        os.close(fd)


def _root(fd):
    info = os.fstat(fd)
    return {
        key: value
        for key, value in removal.signature(info).items()
        if key in ("device", "inode", "uid")
    }


def _snapshot(path, fd, expected_manifest):
    removal._binding(path, fd)
    need(retention.sha(expected_manifest), "external manifest identity")

    def read(name, limit):
        before = os.stat(name, dir_fd=fd, follow_symlinks=False)
        need(
            stat.S_ISREG(before.st_mode)
            and before.st_uid == os.getuid()
            and before.st_nlink == 1
            and stat.S_IMODE(before.st_mode) == 0o600,
            "private ordinary single-link member",
        )
        raw = _read_at(fd, name, limit)
        after = os.stat(name, dir_fd=fd, follow_symlinks=False)
        need(removal.signature(before) == removal.signature(after), "member binding changed")
        return raw, {**removal.signature(after), "sha256": bridge.digest(raw)}

    manifest_raw, manifest_sig = read(MANIFEST, removal.REQUEST_LIMIT)
    need(bridge.digest(manifest_raw) == expected_manifest, "manifest bytes")
    manifest = bridge.decoded(manifest_raw, expected_manifest)
    retention.fields(manifest, "schema files")
    need(manifest["schema"] == "opent1d.lt1-review-bundle/1", "manifest schema")
    members = manifest["files"]
    need(isinstance(members, dict) and MANIFEST not in members, "manifest member map")
    need(0 < len(members) < removal.MAX_FILES, "manifest file count")
    total = len(manifest_raw)
    for name, item in members.items():
        removal.safe_name(name)
        retention.fields(item, "bytes sha256")
        need(
            type(item["bytes"]) is int
            and 0 <= item["bytes"] <= removal.FILE_LIMIT
            and retention.sha(item["sha256"]),
            "manifest member identity",
        )
        total += item["bytes"]
    need(total <= removal.TOTAL_LIMIT, "manifest aggregate bound")
    expected_names = set(members) | {MANIFEST}
    need(removal.names(fd) == expected_names, "closed bundle namespace")
    files, signatures = {MANIFEST: manifest_raw}, {MANIFEST: manifest_sig}
    for name, item in sorted(members.items()):
        raw, signature = read(name, item["bytes"])
        need(len(raw) == item["bytes"] and signature["sha256"] == item["sha256"], "member bytes")
        files[name], signatures[name] = raw, signature
    removal._binding(path, fd)
    need(removal.names(fd) == expected_names, "bundle namespace changed")
    return files, signatures, _root(fd)


def save_review_bundle(output, *, stop=lambda: False, checkpoint=lambda *_: None, **inputs):
    """Save only a fresh proposal, never update a register. Callbacks are trusted.

    No staging prefix is removed on failure/cancellation. A committed rename with
    failed final verification/fsync is reported uncertain and never overwritten.
    """
    output = Path(output)
    need(output.is_absolute(), "absolute output")
    files, _, intent = _material(inputs, output.name)
    published, pending, created, stage_fd = False, None, False, None
    manifest_sha = bridge.digest(files[MANIFEST])
    with _opened(output.parent) as (parent, parent_fd):
        pending = parent / (output.name + ".pending")
        need(
            not os.path.lexists(output) and not os.path.lexists(pending), "fresh output and pending"
        )
        if stop():
            return {
                "status": "interrupted",
                "published": False,
                "pending": None,
                **AUTHORITY,
                **COPY_SCOPE,
            }
        try:
            os.mkdir(pending.name, 0o700, dir_fd=parent_fd)
            created = True
            os.fsync(parent_fd)
            _, stage_fd = _directory(pending)
            _write_at(stage_fd, INTENT, files[INTENT], 0o600)
            checkpoint("intent", INTENT)
            for name in [*sorted(set(files) - {INTENT, MANIFEST}), MANIFEST]:
                if stop():
                    raise InterruptedError("review bundle cancelled")
                removal._binding(parent, parent_fd)
                removal._binding(pending, stage_fd)
                _write_at(stage_fd, name, files[name], 0o600)
                checkpoint("member", name)
            need(_snapshot(pending, stage_fd, manifest_sha)[0] == files, "staged readback")
            need(source_identity() == intent["source_identity"], "writer source changed")
            checkpoint("prepared", None)
            if stop():
                raise InterruptedError("review bundle cancelled")
            removal._binding(parent, parent_fd)
            removal._binding(pending, stage_fd)
            exclusive_rename(pending, output)
            published = True
            checkpoint("published", None)
            need(_snapshot(output, stage_fd, manifest_sha)[0] == files, "published readback")
            os.fsync(parent_fd)
            return {
                "status": "published",
                "published": True,
                "durability_confirmed": True,
                "path": str(output),
                "manifest_sha256": manifest_sha,
                **AUTHORITY,
                **COPY_SCOPE,
            }
        except (Exception, KeyboardInterrupt) as error:
            if created and stage_fd is not None:
                try:
                    named = os.stat(output.name, dir_fd=parent_fd, follow_symlinks=False)
                    opened = os.fstat(stage_fd)
                    published = published or (named.st_dev, named.st_ino) == (
                        opened.st_dev,
                        opened.st_ino,
                    )
                except OSError:
                    pass
            return {
                "status": "publication-uncertain"
                if published
                else "interrupted"
                if isinstance(error, (InterruptedError, KeyboardInterrupt))
                else "failed",
                "published": published,
                "durability_confirmed": False,
                "pending": str(pending) if created and not published else None,
                "path": str(output) if published else None,
                "manifest_sha256": manifest_sha,
                "error_type": type(error).__name__,
                **AUTHORITY,
                **COPY_SCOPE,
            }
        finally:
            if stage_fd is not None:
                os.close(stage_fd)


def _inspect(
    path, expected_manifest_sha256, expected_current_register_sha256, expected_context_sha256, as_of
):
    with _opened(path) as (path, fd):
        snapshot = _snapshot(path, fd, expected_manifest_sha256)
        files = snapshot[0]
        need(INTENT in files, "intent required")
        intent = bridge.decoded(files[INTENT], bridge.digest(files[INTENT]))
        retention.fields(
            intent,
            "schema kind output_name source_identity as_of context_sha256 inputs subjects "
            "new_bundle_copy_registration_required global_copy_coverage_verified",
        )
        need(
            intent["schema"] == "opent1d.lt1-review-bundle-intent/1"
            and intent["context_sha256"] == expected_context_sha256
            and retention.sha(expected_context_sha256),
            "external context identity",
        )
        need(intent["output_name"] == path.name, "intended published leaf")
        metadata = intent["inputs"]
        need(
            isinstance(metadata, dict)
            and set(metadata)
            in ({n + ".json" for n in INPUTS}, {n + ".json" for n in (*INPUTS, "previous")}),
            "fixed input members",
        )
        args = {"as_of": intent["as_of"], "expected_context_sha256": expected_context_sha256}
        for name, item in metadata.items():
            retention.fields(item, "bytes sha256")
            need(
                name in files
                and item == {"bytes": len(files[name]), "sha256": bridge.digest(files[name])},
                "stored input identity",
            )
            role = name[:-5]
            args[role + "_raw"] = files[name]
            args["expected_" + role + "_sha256"] = item["sha256"]
        need(
            args["expected_register_sha256"] == expected_current_register_sha256,
            "external current register identity",
        )
        replay_files, proposal, _ = _material(args, intent["output_name"])
        need(replay_files == files, "exact stored proposal replay")
        need(
            retention.stamp(as_of) >= retention.stamp(intent["as_of"]),
            "current assessment clock reversed",
        )
        current = bridge.propose(**{**args, "as_of": as_of})
        need(source_identity() == intent["source_identity"], "reader source changed")
        need(
            _snapshot(path, fd, expected_manifest_sha256) == snapshot,
            "bundle changed during replay",
        )
        return {
            "schema": "opent1d.lt1-review-bundle-readback/1",
            "status": "verified-proposal",
            "manifest_sha256": expected_manifest_sha256,
            "stored_assessment": proposal["assessment"],
            "current_assessment": current["assessment"],
            "intent": intent,
            **AUTHORITY,
            **COPY_SCOPE,
        }, snapshot


def inspect_bundle(
    path,
    expected_manifest_sha256,
    expected_current_register_sha256,
    expected_context_sha256,
    *,
    as_of,
):
    """Verify exact stored replay, then assess the same observations at external now."""
    return _inspect(
        path,
        expected_manifest_sha256,
        expected_current_register_sha256,
        expected_context_sha256,
        as_of,
    )[0]


def prepare_removal_request(
    path,
    expected_manifest_sha256,
    expected_current_register_sha256,
    expected_context_sha256,
    *,
    as_of,
    context_raw,
    evidence_parent,
    attempt,
):
    """Return an unadmitted request for this entire bundle; never save or remove.

    The request, context and any future removal journal belong outside the bundle.
    Inherited unknown clocks and holds remain visible in the returned assessment.
    """
    need(
        isinstance(context_raw, bytes)
        and len(context_raw) <= removal.REQUEST_LIMIT
        and bridge.digest(context_raw) == expected_context_sha256,
        "exact externally reviewed context bytes",
    )
    report, snapshot = _inspect(
        path,
        expected_manifest_sha256,
        expected_current_register_sha256,
        expected_context_sha256,
        as_of,
    )
    path = Path(path)
    removal.safe_name(attempt)
    with _opened(evidence_parent) as (evidence, evidence_fd):
        need(not _overlap(path, evidence), "separate removal evidence root")
        need(not os.path.lexists(evidence / attempt), "fresh removal attempt")
        request = {
            "schema": "opent1d.lt1-removal-request/1",
            "kind": "invented" if report["intent"]["kind"] == "invented" else "private-data",
            "root": {"path": str(path), **snapshot[2]},
            "evidence_parent": str(evidence),
            "attempt": attempt,
            "files": snapshot[1],
            "source_identity": removal.source_identity(),
            "host": removal.host(),
            "context_sha256": expected_context_sha256,
        }
        raw = bridge.encoded(request)
        removal._request(raw, context_raw)
        removal._binding(evidence, evidence_fd)
        with _opened(path) as (path, fd):
            need(
                _snapshot(path, fd, expected_manifest_sha256) == snapshot,
                "bundle changed during request preparation",
            )
        return {
            "request_raw": raw,
            "request_sha256": bridge.digest(raw),
            "assessment": report["current_assessment"],
            **AUTHORITY,
            **COPY_SCOPE,
        }
