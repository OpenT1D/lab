"""Execution contracts; the historical preparation and scientific rules stay intact."""

import re
import subprocess
import sys
from pathlib import Path

from experiments.m1.artifacts import strict_json
from experiments.m3.azt1d.analysis import _equal, _hashes, _Snapshot
from experiments.m3.azt1d.data import validate_observations
from experiments.m3.azt1d.ledger import verify_evidence, verify_snapshot
from experiments.m3.common import ROOT, digest, encoded, require
from experiments.m3.external import human_freeze as frozen
from experiments.m3.physiocgm.human import _private, _read_private, _write

SCHEMA = "opent1d.physiocgm.evaluation/1"
PROTOCOL = frozen.PROTOCOL
VERIFICATION_FILES = {"state.json", "access.jsonl", "summary.json", "manifest.json"}


def _sources():
    paths = list((ROOT / "experiments/m3/physiocgm_evaluation").glob("*.py"))
    paths += [
        ROOT / "docs/research/physiocgm-execution-protocol.md",
        ROOT / "docs/decisions/0014-physiocgm-human-execution.md",
    ]
    return frozen._sources() | {str(p.relative_to(ROOT)): digest(p.read_bytes()) for p in paths}


def provenance():
    return {
        "sources": _sources(),
        "revision": subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True
        ).strip(),
        "dirty": bool(subprocess.check_output(["git", "status", "--porcelain"], cwd=ROOT)),
        "python": sys.version,
    }


def validate_provenance(value):
    require(
        type(value) is dict
        and set(value) == {"sources", "revision", "dirty", "python"}
        and value["sources"] == _sources()
        and type(value["dirty"]) is bool
        and isinstance(value["revision"], str)
        and re.fullmatch(r"[a-f0-9]{40}|[a-f0-9]{64}", value["revision"])
        and isinstance(value["python"], str)
        and value["python"],
        "Execution implementation changed",
    )


def validate_request(request):
    require(
        type(request) is dict
        and set(request) == {"schema", "kind", "freeze", "authorization", "prior_access"}
        and request["schema"] == SCHEMA
        and request["kind"] == "human",
        "Invalid execution request",
    )
    source = request["freeze"]
    require(
        type(source) is dict and set(source) == {"directory", "manifest_sha256"},
        "Frozen source identity required",
    )
    frozen.conversion._reference({"file": source["directory"], "sha256": source["manifest_sha256"]})
    auth = request["authorization"]
    require(
        type(auth) is dict
        and set(auth) == {"confirmed", "scope", "reference"}
        and auth["confirmed"] is True
        and auth["scope"] == "local-external-evaluation"
        and type(auth["reference"]) is str
        and auth["reference"].strip(),
        "Explicit human scoring authorization required",
    )
    prior = request["prior_access"]
    require(
        type(prior) is dict
        and set(prior) == {"reviewed", "status", "reference"}
        and prior["reviewed"] is True
        and prior["status"] == "present"
        and type(prior["reference"]) is str
        and prior["reference"].strip(),
        "Disclose conversion, preparation and any earlier execution",
    )


def identity(registry, manifest_sha):
    return {
        "schema": SCHEMA,
        "kind": "human",
        "freeze_manifest_sha256": manifest_sha,
        "registry_sha256": digest(encoded(registry)),
    }


def read_plan(path):
    """Read control metadata only, never observations or learned parameters."""
    path = _private(path, existing=True)
    folder = path.parent
    raw = _read_private(path)
    plan = strict_json(raw)
    require(
        type(plan) is dict
        and set(plan)
        == {
            "schema",
            "protocol",
            "kind",
            "stage",
            "request_sha256",
            "freeze_manifest_sha256",
            "registry",
            "identity",
            "rules",
            "model_sha256",
            "donor_verification",
            "ledger",
            "provenance",
        }
        and plan["schema"] == SCHEMA
        and plan["protocol"] == PROTOCOL
        and plan["kind"] == "human"
        and plan["stage"] == "execution"
        and _equal(plan["rules"], frozen.RULES)
        and _equal(plan["donor_verification"], frozen.VERIFICATION),
        "Invalid execution plan or changed scientific rules",
    )
    request_raw = _read_private(folder / "request.json")
    request = strict_json(request_raw)
    validate_request(request)
    require(
        digest(request_raw) == plan["request_sha256"]
        and request["freeze"]["manifest_sha256"] == plan["freeze_manifest_sha256"],
        "Execution authorization changed",
    )
    control = strict_json(_read_private(folder / "freeze/plan.json"))
    registry_raw = _read_private(folder / "freeze/registry.json")
    original = strict_json(_read_private(folder / "freeze/request.json"))
    require(
        control["schema"] == frozen.SCHEMA
        and control["protocol"] == PROTOCOL
        and control["stage"] == "pre-scoring"
        and control["evaluation_enabled"] is False
        and control["execution_supported"] is False
        and _equal(control["rules"], plan["rules"])
        and control["provenance"]["sources"] == frozen._sources()
        and digest(registry_raw) == control["registry_sha256"]
        and _equal(strict_json(registry_raw), plan["registry"])
        and plan["model_sha256"] == original["donor"]["model"]["sha256"]
        and plan["identity"] == identity(plan["registry"], plan["freeze_manifest_sha256"])
        and digest(_read_private(folder / "freeze/manifest.json"))
        == plan["freeze_manifest_sha256"],
        "Execution differs from the original preparation",
    )
    require(Path(plan["ledger"]).is_absolute(), "Absolute live ledger required")
    validate_provenance(plan["provenance"])
    for name, sha in plan["provenance"]["sources"].items():
        require(
            digest(_read_private(folder / "code" / name)) == sha, "Saved execution code changed"
        )
    return plan, digest(raw)


def model(folder):
    raw = {
        name: _read_private(Path(folder) / "freeze/model" / (name + ".json"))
        for name in frozen.DONOR_FILES
    }
    frozen._validate_donor(raw)
    request = strict_json(_read_private(Path(folder) / "freeze/request.json"))
    require(
        all(digest(raw[n]) == request["donor"][n]["sha256"] for n in raw),
        "Frozen donor bytes changed",
    )
    return strict_json(raw["model"])


def observations(raw, person):
    require(digest(raw) == person["sha256"], "External observation bytes changed")
    rows = validate_observations(strict_json(raw), person["id"], *person["bounds_us"])
    require(sorted(rows) == person["origins_us"], "Frozen origin schedule changed")
    return rows


def access_check(plan, plan_sha, anchor, receipt, pid, event, *, raw_ledger=None):
    def check(evidence):
        if raw_ledger is not None:
            return verify_snapshot(raw_ledger, plan["identity"], evidence)
        _private(plan["ledger"], existing=True)
        return verify_evidence(plan["ledger"], plan["identity"], evidence)

    require(anchor.get("event") == "created" and anchor.get("sequence") == 0, "Invalid anchor")
    context = check(anchor)
    require(context["kind"] == "human", "Wrong access kind")
    check(receipt)
    require(
        receipt["freeze_sha256"] == plan_sha
        and receipt["person"] == pid
        and receipt["event"] == event
        and receipt["phase"] == "evaluation",
        "Wrong execution access receipt",
    )
    return context


def verify_verification(folder, freeze_manifest_sha):
    """Validate saved preparation verification evidence, without original paths."""
    with _Snapshot(folder) as snapshot:
        require(snapshot.names == VERIFICATION_FILES, "Unexpected verification files")
        manifest = snapshot.parsed("manifest.json")
        require(manifest["schema"] == frozen.SCHEMA, "Wrong verification schema")
        hashes = _hashes(manifest["files"])
        require(set(hashes) == VERIFICATION_FILES - {"manifest.json"}, "Verification inventory")
        for name, sha in hashes.items():
            require(digest(snapshot.read(name)) == sha, "Verification evidence changed")
        state = snapshot.parsed("state.json")
        require(
            state["schema"] == frozen.SCHEMA
            and state["kind"] == "human"
            and state["status"] == "completed"
            and state["model_fit_or_evaluation"] is False
            and state["bundle_manifest_sha256"] == freeze_manifest_sha,
            "Incomplete or mismatched freeze verification",
        )
        entries = frozen.verify_log(snapshot.read("access.jsonl"), state["request_sha256"])
        require(
            len(entries) == 1
            and entries[0]["payload"]["action"] == "before_bundle_read"
            and entries[0]["payload"]["subject"] == "freeze"
            and entries[0]["payload"]["source_sha256"] == freeze_manifest_sha,
            "Verification access changed",
        )
        snapshot.verify()


def prepared_members(folder):
    """Fixed roles and frozen inventories define membership before content hashing."""
    folder = Path(folder)
    plan, _ = read_plan(folder / "plan.json")
    manifest = strict_json(_read_private(folder / "freeze/manifest.json"))
    return (
        {
            "request.json",
            "plan.json",
            "ledger-anchor.json",
            "copy-access.jsonl",
            "manifest.json",
        }
        | {"freeze/" + n for n in set(_hashes(manifest["files"])) | {"manifest.json"}}
        | {"verification/" + n for n in VERIFICATION_FILES}
        | {"code/" + n for n in plan["provenance"]["sources"]}
    )


def verify_prepared(folder):
    """Call only under a read receipt, after frozen.verify checked the embedded freeze."""
    folder = Path(folder)
    expected = prepared_members(folder)
    with _Snapshot(folder) as snapshot:
        require(
            snapshot.names - {"ledger.jsonl", "execution-claim.json"} == expected,
            "Unexpected prepared artifacts",
        )
        manifest = snapshot.parsed("manifest.json")
        require(manifest["schema"] == SCHEMA, "Wrong prepared inventory")
        hashes = _hashes(manifest["files"])
        require(set(hashes) == expected - {"manifest.json"}, "Prepared membership changed")
        for name, sha in hashes.items():
            _private(folder / name, existing=True)
            require(digest(snapshot.read(name)) == sha, "Prepared artifact changed")
        plan, _ = read_plan(folder / "plan.json")
        verify_verification(folder / "verification", plan["freeze_manifest_sha256"])
        require(
            _equal(
                snapshot.parsed("verification/summary.json"), snapshot.parsed("freeze/summary.json")
            )
            and snapshot.parsed("verification/state.json")["request_sha256"]
            == digest(snapshot.read("freeze/request.json")),
            "Preparation verification differs from frozen source",
        )
        request = snapshot.parsed("request.json")
        entries = frozen.verify_log(snapshot.read("copy-access.jsonl"), plan["request_sha256"])
        require(
            len(entries) == 1
            and entries[0]["payload"]["subject"] == "freeze"
            and entries[0]["payload"]["action"] == "before_bundle_read"
            and entries[0]["payload"]["source_sha256"] == plan["freeze_manifest_sha256"],
            "Missing preparation copy receipt",
        )
        anchor = snapshot.parsed("ledger-anchor.json")
        require(anchor["prior_access"] == request["prior_access"], "Disclosure changed")
        snapshot.verify()


def seal_output(folder, *, exclude=()):
    with _Snapshot(folder) as snapshot:
        hashes = {}
        for name in sorted(snapshot.names - {"manifest.json"} - set(exclude)):
            _private(Path(folder) / name, existing=True)
            hashes[name] = digest(snapshot.read(name))
        snapshot.verify()
    _write(Path(folder) / "manifest.json", encoded({"schema": SCHEMA, "files": hashes}))
