"""Portable, prediction-only export of an already verified AZT1D learned freeze.

Export runs the original plan/fit/input/ledger checks in a compatible source
checkout. Loading the four-file bundle needs neither those inputs nor that
checkout. Its checksums bind the exporter's origin attestation; they are not a
signature, proof that fitting was executed, or an independent statistical audit.
No development observations, prediction traces or validation scores are copied.
Human bundles still contain private participant aliases and learned parameters.
"""

import os
import re
import stat
from pathlib import Path

from experiments.m3.azt1d.analysis import _equal, _hashes, _Snapshot
from experiments.m3.azt1d.common import PROTOCOL as SOURCE_PROTOCOL
from experiments.m3.azt1d.common import SCHEMA as SOURCE_SCHEMA
from experiments.m3.azt1d.common import outside_repository
from experiments.m3.azt1d.ledger import _identity_sha
from experiments.m3.azt1d.study import learned_read, private_directory
from experiments.m3.common import ID, SHA, digest, read, require, save
from experiments.m3.estimator import validate_model

SCHEMA = "opent1d.m3.external-model/1"
FILES = {"model.json", "freeze.json", "origin.json"}
VERIFICATION = {
    "method": "experiments.m3.azt1d.study.learned_read",
    "scope": "export-time-plan-fit-input-and-ledger-verification",
    "portable_scope": "checksums-model-and-attested-origin-only",
    "fit_recomputed": False,
}


def _sha(value):
    require(isinstance(value, str) and SHA.fullmatch(value), "Invalid model origin hash")


def _aliases(values):
    require(
        isinstance(values, list)
        and values
        and all(isinstance(value, str) and ID.fullmatch(value) for value in values)
        and len(values) == len(set(values)),
        "Invalid model participant aliases",
    )


def _provenance(value, kind):
    """Validate historical provenance without comparing it to the current tree."""
    require(isinstance(value, dict), "Missing historical model provenance")
    require(value.get("protocol") == SOURCE_PROTOCOL, "Wrong model source protocol")
    require(
        isinstance(value.get("revision"), str)
        and re.fullmatch(r"(?:[a-f0-9]{40}|[a-f0-9]{64})", value["revision"])
        and type(value.get("dirty")) is bool,
        "Invalid historical model revision",
    )
    require(kind != "human" or value["dirty"] is False, "Dirty human model freeze")
    require(bool(_hashes(value.get("sources"))), "Missing historical model sources")
    for field in ("python", "platform"):
        require(isinstance(value.get(field), str) and value[field], "Missing historical runtime")


def _validate(model, frozen, origin, model_sha):
    validate_model(model)  # Standard library only; this never imports/fits sklearn.
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
        isinstance(origin, dict)
        and set(origin)
        == {
            "schema",
            "kind",
            "source_protocol",
            "source_plan_sha256",
            "source_registry_sha256",
            "source_identity_sha256",
            "source_study_identity",
            "source_people",
            "training_people",
            "verification",
        }
        and origin["schema"] == SCHEMA
        and origin["kind"] in ("human", "synthetic")
        and origin["source_protocol"] == SOURCE_PROTOCOL
        and _equal(origin["verification"], VERIFICATION),
        "Invalid model origin attestation",
    )
    for field in ("source_plan_sha256", "source_registry_sha256", "source_identity_sha256"):
        _sha(origin[field])
    for field in ("source_people", "training_people"):
        _aliases(origin[field])
    require(
        origin["training_people"] == sorted(model["training_counts"])
        and set(origin["training_people"]) <= set(origin["source_people"]),
        "Model training participants differ from source attestation",
    )
    identity = origin["source_study_identity"]
    require(
        isinstance(identity, dict)
        and set(identity) == {"schema", "kind", "people"}
        and identity["schema"] == SOURCE_SCHEMA
        and identity["kind"] == origin["kind"]
        and isinstance(identity["people"], list)
        and len(identity["people"]) == len(origin["source_people"]),
        "Invalid model source study identity",
    )
    for person, alias in zip(identity["people"], origin["source_people"], strict=True):
        require(
            isinstance(person, dict)
            and set(person) == {"id", "source_sha256"}
            and person["id"] == alias,
            "Source study participant identity differs",
        )
        _sha(person["source_sha256"])
    require(
        len({person["source_sha256"] for person in identity["people"]}) == len(identity["people"]),
        "Repeated source in model origin",
    )
    require(
        isinstance(frozen, dict)
        and set(frozen)
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
        and frozen["schema"] == SOURCE_SCHEMA
        and frozen["stage"] == "learned"
        and frozen["model_sha256"] == model_sha
        and frozen["plan_sha256"] == origin["source_plan_sha256"],
        "Model differs from original learned freeze",
    )
    for field in ("validation_sha256", "result_sha256", "inputs_sha256"):
        _sha(frozen[field])
    anchor = frozen["ledger_anchor"]
    require(
        isinstance(anchor, dict)
        and anchor.get("identity_sha256") == origin["source_identity_sha256"]
        and anchor.get("kind") == origin["kind"]
        and anchor.get("event") == "created"
        and type(anchor.get("sequence")) is int
        and anchor["sequence"] == 0,
        "Model source access anchor differs",
    )
    _provenance(frozen["provenance"], origin["kind"])


def load_model(folder):
    """Return ``(model, origin, bundle_sha256)`` without historical input access.

    The returned identity hashes the complete bundle inventory. Keep it in the
    external study's frozen plan: a self-contained inventory alone cannot detect an
    actor replacing all its files and hashes together.
    """
    with _Snapshot(folder) as snapshot:
        require(
            set(os.listdir(snapshot.fd)) == FILES | {"bundle.json"}
            and snapshot.names == FILES | {"bundle.json"},
            "Unexpected portable model files",
        )
        inventory = snapshot.parsed("bundle.json")
        require(
            isinstance(inventory, dict)
            and set(inventory) == {"schema", "files"}
            and inventory["schema"] == SCHEMA
            and set(_hashes(inventory["files"])) == FILES,
            "Invalid portable model inventory",
        )
        for name, sha in inventory["files"].items():
            require(digest(snapshot.read(name)) == sha, "Portable model artifact changed")
        model = snapshot.parsed("model.json")
        origin = snapshot.parsed("origin.json")
        _validate(model, snapshot.parsed("freeze.json"), origin, inventory["files"]["model.json"])
        if origin["kind"] == "human":
            outside_repository(folder)
            require(
                stat.S_IMODE(os.fstat(snapshot.fd).st_mode) == 0o700,
                "Private model directory required",
            )
            for name in snapshot.names:
                mode = os.stat(name, dir_fd=snapshot.fd, follow_symlinks=False).st_mode
                require(stat.S_IMODE(mode) == 0o600, "Private model file required")
        identity = digest(snapshot.read("bundle.json"))
        snapshot.verify()
        return model, origin, identity


def export_model(plan_path, fit_path, output):
    """Verify an existing AZT1D freeze and export it unchanged; never fit/refit.

    Source identity and human/synthetic kind come solely from the verified plan.
    This operation can require the original compatible checkout and local inputs;
    subsequent portable loads do not. Export does not grant redistribution rights.
    """
    plan_path, fit_path, output = Path(plan_path), Path(fit_path), Path(output)
    # Check the metadata kind before any expensive original-input verification.
    initial, _ = read(plan_path)
    if initial.get("kind") == "human":
        outside_repository(plan_path, fit_path, output)
    require(not output.exists() and not output.is_symlink(), "Model output already exists")
    with (
        _Snapshot(plan_path.parent, only={plan_path.name}) as source,
        _Snapshot(fit_path) as fit,
    ):
        raw_plan = source.read(plan_path.name)
        # Cache and pin every existing fit file across original semantic checks.
        for name in fit.names:
            fit.read(name)
        plan, frozen, freeze_sha = learned_read(plan_path, fit_path)
        require(_equal(source.parsed(plan_path.name), plan), "Source plan changed during export")
        require(
            _equal(fit.parsed("freeze.json"), frozen)
            and digest(fit.read("freeze.json")) == freeze_sha,
            "Source fit changed during export",
        )
        if plan["kind"] == "human":
            outside_repository(plan_path, fit_path, output)
        model = fit.parsed("model.json")
        origin = {
            "schema": SCHEMA,
            "kind": plan["kind"],
            "source_protocol": SOURCE_PROTOCOL,
            "source_plan_sha256": digest(raw_plan),
            "source_registry_sha256": plan["registry_sha256"],
            "source_identity_sha256": _identity_sha(plan["identity"]),
            "source_study_identity": {
                "schema": SOURCE_SCHEMA,
                "kind": plan["kind"],
                "people": [
                    {"id": person["id"], "source_sha256": person["source_sha256"]}
                    for person in plan["identity"]["people"]
                ],
            },
            "source_people": [person["id"] for person in plan["identity"]["people"]],
            "training_people": sorted(model["training_counts"]),
            "verification": VERIFICATION,
        }
        _validate(model, frozen, origin, digest(fit.read("model.json")))
        source.verify()
        fit.verify()
        with private_directory(output):
            for name in ("model.json", "freeze.json"):
                (output / name).write_bytes(fit.read(name))
            save(output / "origin.json", origin)
            save(
                output / "bundle.json",
                {
                    "schema": SCHEMA,
                    "files": {name: digest((output / name).read_bytes()) for name in sorted(FILES)},
                },
            )
        # A failed check retains an incomplete bundle rather than publishing it.
        _, verified_origin, _ = load_model(output)
        return verified_origin
