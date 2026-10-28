"""Private PhysioCGM/model binding before scoring; no forecasting entrypoint."""

import subprocess
import sys
from pathlib import Path

from experiments.m1.artifacts import strict_json
from experiments.m3.azt1d.analysis import _equal, _hashes, _Snapshot
from experiments.m3.azt1d.common import SCHEMA as DONOR_SCHEMA
from experiments.m3.azt1d.data import validate_observations
from experiments.m3.azt1d.ledger import _identity_sha
from experiments.m3.azt1d.study import private_directory
from experiments.m3.common import ID, ROOT, SHA, digest, encoded, finite, require
from experiments.m3.estimator import validate_model
from experiments.m3.physiocgm import human as conversion
from experiments.m3.physiocgm.access import record_access, verify_log
from experiments.m3.workflow import failure

from .common import RULES as FORECAST_RULES
from .model import _provenance

SCHEMA = "opent1d.physiocgm.external-freeze/1"
PROTOCOL = "M3-PHYSIOCGM-EXTERNAL/0.1"
MODEL_SCHEMA = "opent1d.physiocgm.frozen-model-metadata/1"
RULES = dict(FORECAST_RULES) | {
    "conversion_protocol": conversion.PROTOCOL,
    "primary": "equal-person-mean-paired-MAE-Ridge-minus-persistence",
    "uncertainty": {
        "unit": "person",
        "draws": 2000,
        "seed": 301,
        "order_statistics_one_based": [50, 1950],
    },
    "secondary": ["equal-person-MAE", "equal-person-RMSE", "equal-person-bias", "origin-strata"],
    "planned_people": 10,
    "incomplete_cohort": "any-planned-person-not-contributing",
    "source_overlap": "different-source-studies-person-overlap-unverified",
}
VERIFICATION = {
    "scope": "metadata-and-original-model-byte-consistency-only",
    "donor_observations_read": False,
    "fit_recomputed": False,
    "historical_validation_recomputed": False,
    "independent_training_reproduction": False,
}
DONOR_FILES = {"plan", "model", "freeze", "state"}


def validate_request(request):
    require(
        type(request) is dict
        and set(request)
        == {
            "schema",
            "kind",
            "authorization",
            "donor",
            "conversion",
            "reconstruction",
            "prior_access",
            "overlap",
        }
        and request["schema"] == SCHEMA
        and request["kind"] == "human",
        "Invalid pre-scoring request",
    )
    auth = request["authorization"]
    require(
        type(auth) is dict
        and set(auth) == {"confirmed", "scope", "reference"}
        and auth["confirmed"] is True
        and auth["scope"] == "local-external-freeze-only"
        and type(auth["reference"]) is str
        and auth["reference"].strip(),
        "Explicit pre-scoring authorization required",
    )
    prior = request["prior_access"]
    require(
        type(prior) is dict
        and set(prior) == {"reviewed", "status", "reference"}
        and prior["reviewed"] is True
        and prior["status"] == "present"
        and type(prior["reference"]) is str
        and prior["reference"].strip(),
        "Prior audit, conversion and reconstruction access must be disclosed",
    )
    overlap = request["overlap"]
    require(
        type(overlap) is dict
        and set(overlap) == {"assessment", "reference"}
        and overlap["assessment"] == RULES["source_overlap"]
        and type(overlap["reference"]) is str
        and overlap["reference"].strip(),
        "Bounded source-overlap assessment required",
    )
    require(
        type(request["donor"]) is dict and set(request["donor"]) == DONOR_FILES,
        "Four original donor control files required",
    )
    for role, ref in request["donor"].items():
        conversion._reference(ref)
        require(Path(ref["file"]).name == role + ".json", "Unexpected donor control filename")
    require(
        len({Path(request["donor"][n]["file"]).parent for n in ("model", "freeze", "state")}) == 1,
        "Donor fit metadata must come from one directory",
    )
    for name in ("conversion", "reconstruction"):
        value = request[name]
        require(
            type(value) is dict
            and set(value) == {"directory", "manifest_sha256"}
            and type(value["directory"]) is str
            and Path(value["directory"]).is_absolute()
            and type(value["manifest_sha256"]) is str
            and SHA.fullmatch(value["manifest_sha256"]),
            "Pinned private conversion/reconstruction manifest required",
        )


def _validate_donor(raw):
    """Check only the four saved control files, never historical observations/traces."""
    plan, model, frozen, state = (strict_json(raw[n]) for n in ("plan", "model", "freeze", "state"))
    require(
        set(plan)
        == {
            "schema",
            "kind",
            "registry",
            "registry_sha256",
            "registry_source_utf8",
            "identity",
            "provenance",
        }
        and plan["schema"] == DONOR_SCHEMA
        and plan["kind"] == "human",
        "Original human donor plan required",
    )
    _provenance(plan["provenance"], "human")
    require(
        digest(plan["registry_source_utf8"].encode()) == plan["registry_sha256"]
        and _equal(strict_json(plan["registry_source_utf8"].encode()), plan["registry"]),
        "Donor registry metadata differs from original bytes",
    )
    validate_model(model)
    require(
        set(model)
        == {
            "method",
            "settings",
            "mean",
            "scale",
            "coef",
            "intercept",
            "feature_rank",
            "singular_values",
            "training_counts",
            "packages",
        },
        "Unexpected model fields",
    )
    require(
        set(frozen)
        == {
            "schema",
            "stage",
            "plan_sha256",
            "model_sha256",
            "validation_sha256",
            "result_sha256",
            "inputs_sha256",
            "ledger_anchor",
            "provenance",
        }
        and frozen["schema"] == DONOR_SCHEMA
        and frozen["stage"] == "learned"
        and frozen["plan_sha256"] == digest(raw["plan"])
        and frozen["model_sha256"] == digest(raw["model"]),
        "Model differs from original donor freeze",
    )
    _provenance(frozen["provenance"], "human")
    identity = plan["identity"]
    require(
        identity.get("schema") == DONOR_SCHEMA
        and identity.get("kind") == "human"
        and type(identity.get("people")) is list
        and identity["people"],
        "Invalid donor identity",
    )
    registry = plan["registry"]
    require(
        registry.get("schema") == DONOR_SCHEMA
        and registry.get("kind") == identity["kind"]
        and type(registry.get("people")) is list
        and [p["id"] for p in registry["people"]] == [p["id"] for p in identity["people"]],
        "Donor registry and identity roster differ",
    )
    people = [{"id": p["id"], "source_sha256": p["source_sha256"]} for p in identity["people"]]
    require(
        all(
            type(p["id"]) is str
            and ID.fullmatch(p["id"])
            and type(p["source_sha256"]) is str
            and SHA.fullmatch(p["source_sha256"])
            for p in people
        )
        and len({p["id"] for p in people}) == len(people)
        and len({p["source_sha256"] for p in people}) == len(people)
        and set(model["training_counts"]) <= {p["id"] for p in people},
        "Invalid donor roster",
    )
    anchor = frozen["ledger_anchor"]
    require(
        anchor.get("kind") == "human"
        and anchor.get("event") == "created"
        and type(anchor.get("sequence")) is int
        and anchor["sequence"] == 0
        and anchor.get("identity_sha256") == _identity_sha(identity),
        "Donor access anchor mismatch",
    )
    require(
        state.get("schema") == DONOR_SCHEMA and state.get("status") == "completed",
        "Incomplete donor fit metadata",
    )
    _provenance(state["provenance"], "human")
    hashes = _hashes(state["files"])
    for name, expected in {
        "model.json": digest(raw["model"]),
        "freeze.json": digest(raw["freeze"]),
        "trace.jsonl": frozen["validation_sha256"],
        "inputs.json": frozen["inputs_sha256"],
        "result.json": frozen["result_sha256"],
    }.items():
        require(hashes.get(name) == expected, "Donor state and learned identities differ")
    finite(state["elapsed_seconds"], "Historical elapsed time", 0)
    return {
        "schema": MODEL_SCHEMA,
        "kind": "human",
        "verification": VERIFICATION,
        "source_files_sha256": {name: digest(raw[name]) for name in sorted(DONOR_FILES)},
        "source_people": people,
        "training_people": sorted(model["training_counts"]),
        "source_identity_sha256": _identity_sha(identity),
    }


class _Prefix:
    def __init__(self, snapshot, prefix=""):
        self.snapshot, self.prefix = snapshot, prefix
        self.names = {name[len(prefix) :] for name in snapshot.names if name.startswith(prefix)}

    def read(self, name):
        return self.snapshot.read(self.prefix + name)

    def parsed(self, name):
        return strict_json(self.read(name))


def _conversion_evidence(c, r, request, *, native_present):
    """Verify controls and completed reconstruction attestation without native replay."""
    require(
        digest(c.read("manifest.json")) == request["conversion"]["manifest_sha256"]
        and digest(r.read("manifest.json")) == request["reconstruction"]["manifest_sha256"],
        "Conversion or reconstruction identity changed",
    )
    plan, names = conversion._plan(c)
    plan_sha = digest(c.read("plan.json"))
    controls = names | {
        "manifest.json",
        "state.json",
        "aggregate.json",
        "cohort.json",
        "access.jsonl",
    }
    expected = controls | {
        p["id"] + "/" + name
        for p in plan["request"]["people"]
        for name in ("native.csv", "observations.json", "audit.json")
    }
    manifest = c.parsed("manifest.json")
    require(
        manifest.get("schema") == conversion.SCHEMA
        and set(_hashes(manifest["files"])) == expected - {"manifest.json"}
        and c.names == (expected if native_present else controls),
        "Conversion membership changed",
    )
    for name in controls - {"manifest.json"}:
        require(
            digest(c.read(name)) == manifest["files"][name], "Conversion control artifact changed"
        )
    state, cohort = c.parsed("state.json"), c.parsed("cohort.json")
    require(
        state.get("schema") == conversion.SCHEMA
        and state.get("kind") == "human"
        and state.get("status") == "completed"
        and state.get("evaluation_enabled") is False
        and state.get("plan_sha256") == plan_sha,
        "Completed conversion required",
    )
    require(
        cohort.get("schema") == conversion.SCHEMA
        and cohort.get("kind") == "human"
        and cohort.get("protocol") == conversion.PROTOCOL
        and cohort.get("evaluation_enabled") is False,
        "Bound human conversion cohort required",
    )
    entries = verify_log(c.read("access.jsonl"), plan_sha)
    people = plan["request"]["people"]
    require(
        len(entries) == len(state["cases"]) == len(cohort["people"]) == len(people) == 10,
        "Incomplete conversion cohort",
    )
    for source, case, person, entry in zip(
        people, state["cases"], cohort["people"], entries, strict=True
    ):
        pid = source["id"]
        require(
            case == {"id": pid, "status": "completed", "access_sha256": entry["sha256"]}
            and entry["payload"]["action"] == "before_native_read"
            and entry["payload"]["subject"] == pid
            and entry["payload"]["source_sha256"] == source["input"]["sha256"]
            and person["id"] == pid
            and person["observations"] == pid + "/observations.json"
            and person["sha256"] == manifest["files"][person["observations"]],
            "Conversion roster or source/read identity differs",
        )
    require(
        r.names == {"manifest.json", "state.json", "aggregate.json", "access.jsonl"},
        "Unexpected reconstruction files",
    )
    r_manifest = r.parsed("manifest.json")
    require(
        r_manifest.get("schema") == conversion.SCHEMA
        and set(_hashes(r_manifest["files"])) == r.names - {"manifest.json"},
        "Invalid reconstruction inventory",
    )
    for name, sha in r_manifest["files"].items():
        require(digest(r.read(name)) == sha, "Reconstruction evidence changed")
    state = r.parsed("state.json")
    require(
        state.get("schema") == conversion.SCHEMA
        and state.get("kind") == "human"
        and state.get("status") == "completed"
        and state.get("evaluation_enabled") is False
        and state.get("plan_sha256") == plan_sha
        and state.get("bundle_manifest_sha256") == request["conversion"]["manifest_sha256"],
        "Reconstruction does not attest this conversion",
    )
    entries = verify_log(r.read("access.jsonl"), plan_sha)
    require(
        len(entries) == 1
        and entries[0]["payload"]["action"] == "before_bundle_read"
        and entries[0]["payload"]["source_sha256"] == request["conversion"]["manifest_sha256"]
        and _equal(r.parsed("aggregate.json"), c.parsed("aggregate.json")),
        "Reconstruction read/aggregate differs",
    )
    return plan, cohort["people"], controls


def _sources():
    paths = list((ROOT / "experiments/m3/external").glob("*.py"))
    paths += [
        ROOT / "docs/research/physiocgm-external-freeze-protocol.md",
        ROOT / "docs/decisions/0013-physiocgm-external-freeze.md",
    ]
    return conversion._sources() | {str(p.relative_to(ROOT)): digest(p.read_bytes()) for p in paths}


def _registry(people, observations, origin, request, source_people):
    donor_ids = {p["id"] for p in origin["source_people"]}
    donor_hashes = {p["source_sha256"] for p in origin["source_people"]}
    native_hashes = {p["id"]: p["input"]["sha256"] for p in source_people}
    require(set(native_hashes) == {p["id"] for p in people}, "Conversion source roster differs")
    registry = {
        "schema": SCHEMA,
        "kind": "human",
        "source_release": conversion.RELEASE,
        "prior_access": request["prior_access"],
        "overlap": request["overlap"],
        "people": [],
    }
    for person in people:
        pid = person["id"]
        raw = observations[pid]
        require(digest(raw) == person["sha256"], "Normalized source changed")
        require(
            pid not in donor_ids
            and person["sha256"] not in donor_hashes
            and native_hashes[pid] not in donor_hashes,
            "External alias or bytes overlap donor",
        )
        rows = validate_observations(strict_json(raw), pid, *person["bounds_us"])
        registry["people"].append(
            {
                "id": pid,
                "input": "inputs/" + pid + ".json",
                "sha256": person["sha256"],
                "native_sha256": native_hashes[pid],
                "bounds_us": person["bounds_us"],
                "origins_us": sorted(rows),
            }
        )
    return registry


def _summary(registry):
    return {
        "schema": SCHEMA,
        "kind": "human",
        "planned_people": len(registry["people"]),
        "registered_origins": sum(len(p["origins_us"]) for p in registry["people"]),
        "model_bytes_unchanged": True,
        "model_fit_or_evaluation": False,
        "historical_validation_recomputed": False,
        "execution_supported": False,
        "evaluation_enabled": False,
    }


def _seal(folder):
    with _Snapshot(folder) as snapshot:
        files = {}
        for name in sorted(snapshot.names):
            conversion._private(folder / name, existing=True)
            if name != "manifest.json":
                files[name] = digest(snapshot.read(name))
        snapshot.verify()
    conversion._write(folder / "manifest.json", encoded({"schema": SCHEMA, "files": files}))


def freeze(request_path, output):
    """Snapshot all ten normalized sources and unchanged donor model without scoring."""
    request_raw = conversion._read_private(request_path)
    request = strict_json(request_raw)
    validate_request(request)
    output = conversion._private(output)
    request_sha = digest(request_raw)
    state = {
        "schema": SCHEMA,
        "kind": "human",
        "status": "started",
        "request_sha256": request_sha,
        "evaluation_enabled": False,
        "execution_supported": False,
        "cases": [],
    }
    with private_directory(output):
        conversion._write(output / "request.json", request_raw)
        conversion._state(output / "state.json", state)
        try:
            # The reused read-receipt field plan_sha256 binds this exact pre-read request.
            record_access(
                output / "access.jsonl",
                request_sha,
                "before_bundle_read",
                "donor",
                digest(encoded(request["donor"])),
            )
            raw_model = {}
            for role, ref in request["donor"].items():
                raw = conversion._read_private(ref["file"])
                require(digest(raw) == ref["sha256"], "Donor control file changed")
                raw_model[role] = raw
                conversion._write(output / "model" / (role + ".json"), raw)
            origin = _validate_donor(raw_model)
            conversion._write(output / "model/origin.json", encoded(origin))
            record_access(
                output / "access.jsonl",
                request_sha,
                "before_bundle_read",
                "conversion",
                request["conversion"]["manifest_sha256"],
            )
            cdir = conversion._private(request["conversion"]["directory"], existing=True)
            rdir = conversion._private(request["reconstruction"]["directory"], existing=True)
            with _Snapshot(cdir) as c, _Snapshot(rdir) as r:
                conversion_plan, people, controls = _conversion_evidence(
                    _Prefix(c), _Prefix(r), request, native_present=True
                )
                state["cases"] = [{"id": p["id"], "status": "not_attempted"} for p in people]
                conversion._state(output / "state.json", state)
                for name in controls:
                    conversion._private(cdir / name, existing=True)
                    conversion._write(output / "conversion-evidence" / name, c.read(name))
                for name in r.names:
                    conversion._private(rdir / name, existing=True)
                    conversion._write(output / "reconstruction-evidence" / name, r.read(name))
                observations = {}
                for person, case in zip(people, state["cases"], strict=True):
                    try:
                        receipt = record_access(
                            output / "access.jsonl",
                            request_sha,
                            "before_bundle_read",
                            person["id"],
                            person["sha256"],
                        )
                        case["access_sha256"] = receipt["sha256"]
                        conversion._state(output / "state.json", state)
                        raw = conversion._read_private(cdir / person["observations"])
                        require(digest(raw) == person["sha256"], "Normalized source changed")
                        conversion._write(output / "inputs" / (person["id"] + ".json"), raw)
                        observations[person["id"]] = raw
                        case["status"] = "completed"
                    except BaseException as error:
                        case.update(status="failed", error=failure(error))
                        if not isinstance(error, Exception):
                            raise
                    finally:
                        conversion._state(output / "state.json", state)
                require(
                    all(p["status"] == "completed" for p in state["cases"]),
                    "Incomplete external roster; no partial freeze",
                )
                registry = _registry(
                    people, observations, origin, request, conversion_plan["request"]["people"]
                )
                c.verify()
                r.verify()
            source_hashes = _sources()
            plan = {
                "schema": SCHEMA,
                "protocol": PROTOCOL,
                "kind": "human",
                "stage": "pre-scoring",
                "evaluation_enabled": False,
                "execution_supported": False,
                "rules": RULES,
                "request_sha256": request_sha,
                "registry_sha256": digest(encoded(registry)),
                "model_origin_sha256": digest(encoded(origin)),
                "conversion_manifest_sha256": request["conversion"]["manifest_sha256"],
                "reconstruction_manifest_sha256": request["reconstruction"]["manifest_sha256"],
                "provenance": {
                    "sources": source_hashes,
                    "python": sys.version,
                    "revision": subprocess.check_output(
                        ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True
                    ).strip(),
                    "dirty": bool(
                        subprocess.check_output(["git", "status", "--porcelain"], cwd=ROOT)
                    ),
                },
            }
            for name, sha in source_hashes.items():
                raw = (ROOT / name).read_bytes()
                require(digest(raw) == sha, "Bridge code changed during freeze")
                conversion._write(output / "code" / name, raw)
            conversion._write(output / "registry.json", encoded(registry))
            conversion._write(output / "plan.json", encoded(plan))
            summary = _summary(registry)
            conversion._write(output / "summary.json", encoded(summary))
            state["status"] = "completed"
        except BaseException as error:
            state.update(status="failed", error=failure(error))
            raise
        finally:
            conversion._state(output / "state.json", state)
            _seal(output)
    return summary


def verify(bundle, output):
    """Independently recheck frozen inputs/metadata, with no prediction arithmetic."""
    bundle = conversion._private(bundle, existing=True)
    output = conversion._private(output)
    # Only fixed control metadata before the durable new read receipt.
    request_raw = conversion._read_private(bundle / "request.json")
    request = strict_json(request_raw)
    validate_request(request)
    request_sha = digest(request_raw)
    manifest_sha = digest(conversion._read_private(bundle / "manifest.json"))
    state = {
        "schema": SCHEMA,
        "kind": "human",
        "status": "started",
        "request_sha256": request_sha,
        "bundle_manifest_sha256": manifest_sha,
        "model_fit_or_evaluation": False,
    }
    with private_directory(output):
        conversion._state(output / "state.json", state)
        try:
            record_access(
                output / "access.jsonl", request_sha, "before_bundle_read", "freeze", manifest_sha
            )
            with _Snapshot(bundle) as snapshot:
                require(
                    digest(snapshot.read("request.json")) == request_sha
                    and digest(snapshot.read("manifest.json")) == manifest_sha,
                    "Freeze changed before read",
                )
                plan = snapshot.parsed("plan.json")
                require(
                    plan.get("schema") == SCHEMA
                    and plan.get("protocol") == PROTOCOL
                    and plan.get("kind") == "human"
                    and plan.get("stage") == "pre-scoring"
                    and plan.get("evaluation_enabled") is False
                    and plan.get("execution_supported") is False
                    and _equal(plan.get("rules"), RULES)
                    and plan.get("request_sha256") == request_sha
                    and plan.get("conversion_manifest_sha256")
                    == request["conversion"]["manifest_sha256"]
                    and plan.get("reconstruction_manifest_sha256")
                    == request["reconstruction"]["manifest_sha256"],
                    "Pre-scoring plan changed",
                )
                require(
                    plan["provenance"]["sources"] == _sources(), "Frozen bridge sources changed"
                )
                conversion_plan, people, controls = _conversion_evidence(
                    _Prefix(snapshot, "conversion-evidence/"),
                    _Prefix(snapshot, "reconstruction-evidence/"),
                    request,
                    native_present=False,
                )
                expected = {
                    "request.json",
                    "plan.json",
                    "registry.json",
                    "state.json",
                    "access.jsonl",
                    "summary.json",
                    "manifest.json",
                    "model/origin.json",
                }
                expected.update("model/" + name + ".json" for name in DONOR_FILES)
                expected.update("conversion-evidence/" + name for name in controls)
                expected.update(
                    "reconstruction-evidence/" + name
                    for name in ("manifest.json", "state.json", "access.jsonl", "aggregate.json")
                )
                expected.update("inputs/" + p["id"] + ".json" for p in people)
                expected.update("code/" + name for name in plan["provenance"]["sources"])
                require(snapshot.names == expected, "Unexpected frozen inputs")
                manifest = snapshot.parsed("manifest.json")
                require(
                    manifest.get("schema") == SCHEMA
                    and set(_hashes(manifest["files"])) == expected - {"manifest.json"},
                    "Invalid freeze inventory",
                )
                for name, sha in manifest["files"].items():
                    conversion._private(bundle / name, existing=True)
                    require(digest(snapshot.read(name)) == sha, "Frozen artifact changed")
                for name, sha in plan["provenance"]["sources"].items():
                    require(
                        digest(snapshot.read("code/" + name)) == sha, "Saved bridge code changed"
                    )
                raw_model = {role: snapshot.read("model/" + role + ".json") for role in DONOR_FILES}
                require(
                    all(digest(raw_model[n]) == request["donor"][n]["sha256"] for n in DONOR_FILES),
                    "Donor source snapshot changed",
                )
                origin = _validate_donor(raw_model)
                require(
                    _equal(origin, snapshot.parsed("model/origin.json"))
                    and digest(snapshot.read("model/origin.json")) == plan["model_origin_sha256"],
                    "Model metadata attestation changed",
                )
                observations = {
                    p["id"]: snapshot.read("inputs/" + p["id"] + ".json") for p in people
                }
                registry = _registry(
                    people, observations, origin, request, conversion_plan["request"]["people"]
                )
                require(
                    _equal(registry, snapshot.parsed("registry.json"))
                    and digest(snapshot.read("registry.json")) == plan["registry_sha256"],
                    "External roster or schedule changed",
                )
                entries = verify_log(snapshot.read("access.jsonl"), request_sha)
                require(
                    len(entries) == 2 + len(people)
                    and [
                        (
                            e["payload"]["action"],
                            e["payload"]["subject"],
                            e["payload"]["source_sha256"],
                        )
                        for e in entries
                    ]
                    == [
                        ("before_bundle_read", "donor", digest(encoded(request["donor"]))),
                        (
                            "before_bundle_read",
                            "conversion",
                            request["conversion"]["manifest_sha256"],
                        ),
                    ]
                    + [("before_bundle_read", p["id"], p["sha256"]) for p in people],
                    "Frozen read history changed",
                )
                frozen_state = snapshot.parsed("state.json")
                require(
                    frozen_state.get("schema") == SCHEMA
                    and frozen_state.get("kind") == "human"
                    and frozen_state.get("status") == "completed"
                    and frozen_state.get("request_sha256") == request_sha
                    and frozen_state.get("evaluation_enabled") is False
                    and frozen_state.get("execution_supported") is False
                    and frozen_state["cases"]
                    == [
                        {"id": p["id"], "status": "completed", "access_sha256": e["sha256"]}
                        for p, e in zip(people, entries[2:], strict=True)
                    ],
                    "Incomplete frozen cohort",
                )
                summary = _summary(registry)
                require(_equal(summary, snapshot.parsed("summary.json")), "Freeze summary changed")
                snapshot.verify()
            conversion._write(output / "summary.json", encoded(summary))
            state["status"] = "completed"
        except BaseException as error:
            state.update(status="failed", error=failure(error))
            raise
        finally:
            conversion._state(output / "state.json", state)
            _seal(output)
    return summary
