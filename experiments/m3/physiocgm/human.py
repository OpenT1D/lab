"""Source-bound private PhysioCGM conversion, with no predictor or evaluation route."""

import os
import platform
import stat
import subprocess
import sys
from collections import Counter
from pathlib import Path

from experiments.m1.artifacts import strict_json
from experiments.m3.azt1d.analysis import _equal, _hashes, _Snapshot
from experiments.m3.azt1d.study import private_directory
from experiments.m3.common import ID, ROOT, SHA, digest, encoded, require, sources
from experiments.m3.workflow import failure

from .access import record_access, verify_log
from .intake import CONTRACT, RELEASE, _convert_csv, validate_header

SCHEMA = REQUEST_SCHEMA = "opent1d.physiocgm.human/1"
PROTOCOL = "PHYSIOCGM-CONVERSION/1.0"
EVIDENCE_PATHS = {
    "acquisition": "acquisition.json",
    "audit_inventory": "audit/format-check-03/evidence-manifest.json",
    "prior_access": "audit/format-check-03/access-snapshot.jsonl",
    "rights_metadata": "metadata/release-v1.json",
    "audit_report": "audit/format-check-03/Bevindingen.md",
}
EVIDENCE = set(EVIDENCE_PATHS)
RULES = {
    "period": "complete-published-raw-CGM-export",
    "origin": "first-EGV",
    "end": "last-EGV-plus-300-seconds-administrative-exclusive",
    "clock": "one-assumed-naive-local-segment-no-timezone-inference",
    "availability": "measurement-time-assumed-available-retrospective-only",
    "timing": "exact-microseconds-no-rounding-interpolation-or-tolerance",
    "numeric_status": "exclude-at-or-outside-40-and-400-conservative-not-proven-censoring",
    "censoring": "Low-High-direction-only-no-numeric-bound",
    "duplicates": "equivalent-merge-conflicts-ambiguous-preserve-record-lineage",
    "roster": "all-ten-raw-exports-preserve-failures",
    "model_fit_or_evaluation": False,
}


def _private(path, *, existing=False):
    """Reject Git trees and unsafe leaf files, without inspecting source contents."""
    path = Path(path).absolute()
    require(not path.is_symlink(), "Symlink private path refused")
    resolved = path.resolve()
    require(not resolved.is_relative_to(ROOT), "Human material must remain outside repository")
    for parent in (resolved, *resolved.parents):
        require(not (parent / ".git").exists(), "Human material must remain outside Git")
    if existing:
        info = path.lstat()
        require(not info.st_mode & 0o077, "Private permissions required")
        require(
            stat.S_ISDIR(info.st_mode) or (stat.S_ISREG(info.st_mode) and info.st_nlink == 1),
            "Private regular file or directory required",
        )
    else:
        require(path.parent.is_dir(), "Existing private parent required")
    require(not path.parent.stat().st_mode & 0o077, "Private parent permissions required")
    return path


def _read_private(path):
    path = _private(path, existing=True)
    with _Snapshot(path.parent, only={path.name}) as snapshot:
        raw = snapshot.read(path.name)
        snapshot.verify()
    return raw


def _write(path, raw):
    """Write new evidence durably, never replace an earlier artifact."""
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    try:
        offset = 0
        while offset < len(raw):
            count = os.write(fd, raw[offset:])
            require(count > 0, "Evidence write failed")
            offset += count
        os.fsync(fd)
    finally:
        os.close(fd)
    directory = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY)
    try:
        os.fsync(directory)
    finally:
        os.close(directory)


def _state(path, value):
    # State checkpoints may advance; earlier attempts always use new directories.
    temporary = path.with_suffix(".pending")
    _write(temporary, encoded(value))
    os.replace(temporary, path)
    directory = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY)
    try:
        os.fsync(directory)
    finally:
        os.close(directory)


def _reference(ref):
    require(
        type(ref) is dict
        and set(ref) == {"file", "sha256"}
        and type(ref["file"]) is str
        and Path(ref["file"]).is_absolute()
        and type(ref["sha256"]) is str
        and SHA.fullmatch(ref["sha256"]),
        "Absolute source reference with SHA-256 required",
    )


def validate_request(request):
    require(
        type(request) is dict
        and set(request)
        == {"schema", "kind", "release", "authorization", "prior_access", "evidence", "people"}
        and request["schema"] == SCHEMA
        and request["kind"] == "human"
        and request["release"] == RELEASE,
        "Invalid human conversion request",
    )
    auth = request["authorization"]
    require(
        type(auth) is dict
        and set(auth) == {"confirmed", "scope", "reference", "retention"}
        and auth["confirmed"] is True
        and auth["scope"] == "local-conversion-only"
        and auth["retention"] == "private-local-reproducibility"
        and type(auth["reference"]) is str
        and auth["reference"].strip(),
        "Explicit conversion-only authorization and retention required",
    )
    prior = request["prior_access"]
    require(
        type(prior) is dict
        and set(prior) == {"reviewed", "status", "reference"}
        and prior["reviewed"] is True
        and prior["status"] == "present"
        and type(prior["reference"]) is str
        and prior["reference"].strip(),
        "Prior audit access must be disclosed",
    )
    require(
        type(request["evidence"]) is dict and set(request["evidence"]) == EVIDENCE,
        "Complete review evidence required",
    )
    for ref in request["evidence"].values():
        _reference(ref)
    audit_path = Path(request["evidence"]["audit_inventory"]["file"])
    require(len(audit_path.parents) >= 3, "Invalid audited release root")
    audit_root = audit_path.parents[2]
    for role, relative in EVIDENCE_PATHS.items():
        require(
            Path(request["evidence"][role]["file"]) == audit_root / relative,
            "Unexpected review evidence location",
        )
    people = request["people"]
    require(type(people) is list and len(people) == 10, "All ten raw exports required")
    aliases, paths, hashes, archives = set(), set(), set(), set()
    for person in people:
        require(
            type(person) is dict
            and set(person) == {"id", "input", "header", "archive", "audit_member"},
            "Invalid planned source",
        )
        pid = person["id"]
        require(
            type(pid) is str
            and ID.fullmatch(pid)
            and pid not in aliases
            and pid not in {"code", "evidence", "model"},
            "Repeated or invalid local alias",
        )
        aliases.add(pid)
        _reference(person["input"])
        path = os.path.normpath(person["input"]["file"])
        sha = person["input"]["sha256"]
        require(path not in paths and sha not in hashes, "Repeated native input")
        paths.add(path)
        hashes.add(sha)
        archive = person["archive"]
        require(
            type(archive) is str
            and archive in {f"archive-{n:02d}" for n in range(1, 11)}
            and archive not in archives,
            "Repeated or unsupported raw archive",
        )
        archives.add(archive)
        require(
            person["audit_member"] == f"audit/format-check-01/cgm/{archive}.csv",
            "Unexpected audited native member",
        )
        require(
            Path(person["input"]["file"]) == audit_root / person["audit_member"],
            "Native input differs from audited member location",
        )
        validate_header(person["header"])


def _review(request, evidence):
    """Bind the selected sources to the prior audited release, not just a checkbox."""
    acquisition = strict_json(evidence["acquisition"])
    inventory = strict_json(evidence["audit_inventory"])
    rights = strict_json(evidence["rights_metadata"])
    require(
        acquisition["release_doi"] == RELEASE
        and acquisition["all_verified"] is True
        and acquisition["model_evaluation"] is False
        and inventory["release"] == RELEASE,
        "Release audit identity mismatch",
    )
    require(
        rights["doi"] == RELEASE and rights["license"]["name"] == "CC0",
        "Pinned CC0 release evidence required",
    )
    for role, relative in EVIDENCE_PATHS.items():
        if role != "audit_inventory":
            require(
                inventory["private_evidence_files_sha256"][relative]
                == request["evidence"][role]["sha256"],
                "Review evidence differs from prior audit inventory",
            )
    require(
        inventory["access_snapshot_sha256"] == request["evidence"]["prior_access"]["sha256"],
        "Prior access snapshot is not audit-bound",
    )
    archives = {p["archive"].removesuffix(".zip"): p["sha256"] for p in acquisition["files"]}
    require(
        len(archives) == 10 and len(acquisition["files"]) == 10, "Incomplete acquisition evidence"
    )
    for person in request["people"]:
        require(
            inventory["private_evidence_files_sha256"][person["audit_member"]]
            == person["input"]["sha256"],
            "Native source is not bound to audit",
        )
        require(
            archives[person["archive"]] == inventory["archive_sha256"][person["archive"]],
            "Raw archive audit identity mismatch",
        )


def _sources():
    paths = list((ROOT / "experiments/m3/physiocgm").glob("*.py"))
    paths += list((ROOT / "experiments/m3/azt1d").glob("*.py"))
    paths += [
        ROOT / "docs/research/physiocgm-conversion-protocol.md",
        ROOT / "docs/decisions/0012-physiocgm-human-conversion.md",
    ]
    return sources() | {str(p.relative_to(ROOT)): digest(p.read_bytes()) for p in paths}


def _seal(folder):
    with _Snapshot(folder) as snapshot:
        files = {}
        for name in sorted(snapshot.names):
            _private(folder / name, existing=True)
            if name != "manifest.json":
                files[name] = digest(snapshot.read(name))
        snapshot.verify()
    _write(folder / "manifest.json", encoded({"schema": SCHEMA, "files": files}))


def freeze(request_path, output):
    """Freeze metadata/evidence/code only; no native source is opened or hashed."""
    raw_request = _read_private(request_path)
    request = strict_json(raw_request)
    validate_request(request)
    output = _private(output)
    evidence = {}
    for name, ref in request["evidence"].items():
        raw = _read_private(ref["file"])
        require(digest(raw) == ref["sha256"], "Review evidence bytes changed")
        evidence[name] = raw
    _review(request, evidence)
    plan = {
        "schema": SCHEMA,
        "kind": "human",
        "protocol": PROTOCOL,
        "rules": RULES,
        "request": request,
        "request_sha256": digest(raw_request),
        "evaluation_enabled": False,
        "provenance": {
            "sources": _sources(),
            "python": sys.version,
            "platform": platform.platform(),
            "synthetic_parser_contract": CONTRACT,
            "revision": subprocess.check_output(
                ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True
            ).strip(),
            "dirty": bool(subprocess.check_output(["git", "status", "--porcelain"], cwd=ROOT)),
        },
    }
    with private_directory(output):
        _write(output / "request.json", raw_request)
        _write(output / "plan.json", encoded(plan))
        for name, raw in evidence.items():
            _write(output / "evidence" / name, raw)
        for name, sha in plan["provenance"]["sources"].items():
            raw = (ROOT / name).read_bytes()
            require(digest(raw) == sha, "Conversion code changed during freeze")
            _write(output / "code" / name, raw)
        _seal(output)
    return plan


def _plan(snapshot):
    plan = snapshot.parsed("plan.json")
    require(
        plan.get("schema") == SCHEMA
        and plan.get("kind") == "human"
        and plan.get("protocol") == PROTOCOL
        and plan.get("evaluation_enabled") is False
        and _equal(plan.get("rules"), RULES),
        "Conversion plan or rules changed",
    )
    validate_request(plan["request"])
    require(
        plan["request_sha256"] == digest(snapshot.read("request.json"))
        and _equal(plan["request"], snapshot.parsed("request.json")),
        "Frozen request changed",
    )
    require(
        plan["provenance"]["sources"] == _sources()
        and plan["provenance"]["synthetic_parser_contract"] == CONTRACT,
        "Conversion sources changed; use the saved implementation",
    )
    names = {"plan.json", "request.json"}
    evidence = {}
    for name, ref in plan["request"]["evidence"].items():
        member = "evidence/" + name
        raw = snapshot.read(member)
        require(digest(raw) == ref["sha256"], "Saved review evidence changed")
        evidence[name] = raw
        names.add(member)
    _review(plan["request"], evidence)
    for name, sha in plan["provenance"]["sources"].items():
        member = "code/" + name
        require(digest(snapshot.read(member)) == sha, "Saved converter code changed")
        names.add(member)
    return plan, names


def _inventory(snapshot):
    manifest = snapshot.parsed("manifest.json")
    require(
        set(manifest) == {"schema", "files"} and manifest["schema"] == SCHEMA,
        "Invalid conversion inventory",
    )
    hashes = _hashes(manifest["files"])
    require(set(hashes) == snapshot.names - {"manifest.json"}, "Conversion inventory changed")
    for name, sha in hashes.items():
        require(digest(snapshot.read(name)) == sha, "Conversion artifact changed")
    return hashes


def _cohort(plan, documents):
    return {
        "schema": SCHEMA,
        "kind": "human",
        "evaluation_enabled": False,
        "protocol": PROTOCOL,
        "people": [
            {
                "id": person["id"],
                "observations": person["id"] + "/observations.json",
                "sha256": digest(encoded(documents[person["id"]][0])),
                "bounds_us": documents[person["id"]][0]["bounds_us"],
            }
            for person in plan["request"]["people"]
        ],
    }


def _aggregate(documents):
    statuses, variants = Counter(), Counter()
    total = Counter()
    for _, audit in documents.values():
        statuses.update(audit["statuses"])
        variants.update(audit["format_variants"])
        for name in (
            "source_record_count",
            "egv_record_count",
            "excluded_non_egv_records",
            "registered_origins",
            "duplicate_egv_records",
        ):
            total[name] += audit[name]
    return {
        "schema": SCHEMA,
        "kind": "human",
        "planned_people": 10,
        "converted_sources": len(documents),
        "counts": dict(total),
        "statuses": dict(statuses),
        "format_variants": dict(variants),
        "model_fit_or_evaluation": False,
        "evaluation_enabled": False,
    }


def prepare(plan_path, output):
    """Convert all planned sources, recording each attempted read before access."""
    plan_path = _private(plan_path, existing=True)
    require(plan_path.name == "plan.json", "Expected plan.json")
    output = _private(output)
    with _Snapshot(plan_path.parent) as snapshot:
        plan, names = _plan(snapshot)
        require(names == snapshot.names - {"manifest.json"}, "Unexpected frozen plan files")
        _inventory(snapshot)
        saved = {name: snapshot.read(name) for name in names}
        snapshot.verify()
    plan_sha = digest(saved["plan.json"])
    state = {
        "schema": SCHEMA,
        "kind": "human",
        "status": "started",
        "plan_sha256": plan_sha,
        "evaluation_enabled": False,
        "cases": [{"id": p["id"], "status": "not_attempted"} for p in plan["request"]["people"]],
    }
    documents = {}
    with private_directory(output):
        for name, raw in saved.items():
            _write(output / name, raw)
        _state(output / "state.json", state)
        try:
            for person, case in zip(plan["request"]["people"], state["cases"], strict=True):
                pid = person["id"]
                try:
                    receipt = record_access(
                        output / "access.jsonl",
                        plan_sha,
                        "before_native_read",
                        pid,
                        person["input"]["sha256"],
                    )
                    case["access_sha256"] = receipt["sha256"]
                    _state(output / "state.json", state)
                    raw = _read_private(person["input"]["file"])
                    _write(output / pid / "native.csv", raw)
                    require(digest(raw) == person["input"]["sha256"], "Native source bytes changed")
                    document, audit = _convert_csv(
                        raw, person=pid, expected_header=person["header"], kind="human"
                    )
                    _write(output / pid / "observations.json", encoded(document))
                    _write(output / pid / "audit.json", encoded(audit))
                    documents[pid] = document, audit
                    case["status"] = "completed"
                except BaseException as error:
                    case.update(status="failed", error=failure(error))
                    if not isinstance(error, Exception):
                        raise
                finally:
                    _state(output / "state.json", state)
            require(
                all(c["status"] == "completed" for c in state["cases"]),
                "Human conversion incomplete; no partial cohort created",
            )
            _write(output / "cohort.json", encoded(_cohort(plan, documents)))
            state["status"] = "completed"
        except BaseException as error:
            state.update(status="failed", error=failure(error))
            raise
        finally:
            _state(output / "state.json", state)
            _write(output / "aggregate.json", encoded(_aggregate(documents)))
            _seal(output)
    return _aggregate(documents)


def verify(bundle, output):
    """Record a new private access, then reconstruct without original source paths."""
    bundle = _private(bundle, existing=True)
    output = _private(output)
    # Only control metadata before the durable read event; never hash native inputs here.
    with _Snapshot(bundle, only={"plan.json", "manifest.json"}) as metadata:
        plan_raw = metadata.read("plan.json")
        plan_sha = digest(plan_raw)
        manifest_sha = digest(metadata.read("manifest.json"))
        metadata.verify()
    with private_directory(output):
        state = {
            "schema": SCHEMA,
            "kind": "human",
            "status": "started",
            "plan_sha256": plan_sha,
            "bundle_manifest_sha256": manifest_sha,
            "evaluation_enabled": False,
        }
        _state(output / "state.json", state)
        try:
            record_access(
                output / "access.jsonl", plan_sha, "before_bundle_read", "cohort", manifest_sha
            )
            with _Snapshot(bundle) as snapshot:
                require(
                    digest(snapshot.read("plan.json")) == plan_sha
                    and digest(snapshot.read("manifest.json")) == manifest_sha,
                    "Bundle changed before verification",
                )
                for name in snapshot.names:
                    _private(bundle / name, existing=True)
                plan, names = _plan(snapshot)
                expected_names = names | {
                    "cohort.json",
                    "aggregate.json",
                    "state.json",
                    "access.jsonl",
                    "manifest.json",
                }
                expected_names.update(
                    person["id"] + "/" + name
                    for person in plan["request"]["people"]
                    for name in ("native.csv", "observations.json", "audit.json")
                )
                require(expected_names == snapshot.names, "Unexpected conversion contents")
                _inventory(snapshot)
                conversion = snapshot.parsed("state.json")
                require(
                    conversion.get("schema") == SCHEMA
                    and conversion.get("kind") == "human"
                    and conversion.get("status") == "completed"
                    and conversion.get("plan_sha256") == plan_sha
                    and conversion.get("evaluation_enabled") is False,
                    "Only complete human conversions may verify",
                )
                entries = verify_log(snapshot.read("access.jsonl"), plan_sha)
                require(len(entries) == 10, "Incomplete conversion access history")
                cases = conversion["cases"]
                people = plan["request"]["people"]
                require(len(cases) == len(people), "Planned conversion roster changed")
                documents = {}
                for person, case, entry in zip(people, cases, entries, strict=True):
                    pid = person["id"]
                    require(
                        case == {"id": pid, "status": "completed", "access_sha256": entry["sha256"]}
                        and entry["payload"]["action"] == "before_native_read"
                        and entry["payload"]["subject"] == pid
                        and entry["payload"]["source_sha256"] == person["input"]["sha256"],
                        "Conversion read receipt differs from source",
                    )
                    prefix = pid + "/"
                    raw = snapshot.read(prefix + "native.csv")
                    require(digest(raw) == person["input"]["sha256"], "Native snapshot changed")
                    document, audit = _convert_csv(
                        raw, person=pid, expected_header=person["header"], kind="human"
                    )
                    require(
                        _equal(document, snapshot.parsed(prefix + "observations.json"))
                        and _equal(audit, snapshot.parsed(prefix + "audit.json")),
                        "Saved conversion differs from native source",
                    )
                    documents[pid] = document, audit
                    names.update(
                        prefix + name for name in ("native.csv", "observations.json", "audit.json")
                    )
                require(
                    _equal(_cohort(plan, documents), snapshot.parsed("cohort.json"))
                    and _equal(_aggregate(documents), snapshot.parsed("aggregate.json")),
                    "Cohort or aggregate differs from native conversion",
                )
                names.update(
                    {"cohort.json", "aggregate.json", "state.json", "access.jsonl", "manifest.json"}
                )
                require(names == snapshot.names, "Unexpected conversion contents")
                snapshot.verify()
            state["status"] = "completed"
            report = _aggregate(documents)
            _write(output / "aggregate.json", encoded(report))
        except BaseException as error:
            state.update(status="failed", error=failure(error))
            raise
        finally:
            _state(output / "state.json", state)
            _seal(output)
    return report
