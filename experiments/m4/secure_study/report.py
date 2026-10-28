"""Authoritative successor reader; unchanged scientific assessment, standard library."""

from pathlib import Path

from experiments.m4.causal_secretion.common import declaration
from experiments.m4.initial_load import report as inherited

from . import locations
from .common import (
    NATIVE_PROJECT,
    OBSERVER_PROJECT,
    PROTOCOL_OBJECT_SHA256,
    PROTOCOL_SHA256,
    REFERENCE_SCHEMA,
    VERSION,
    digest,
    encoded,
    read,
    require,
    source_paths,
    validate_config,
)
from .runtime import validate, validate_numerical_runtime

INHERITED_ASSESSMENT = inherited.assessment
INHERITED_RECONSTRUCT = inherited.reconstruct


def validate_frozen(directory, files):
    plan = read(directory / "plan.json")
    require(plan.get("schema") == VERSION, "Unsupported maintained study plan")
    if "execution_locations" in plan:
        locations.validate(plan["execution_locations"])
    require(digest(files["config.json"]) == plan.get("config_sha256"), "Config binding changed")
    config = validate_config(read(directory / "config.json"))
    require(config == plan.get("configuration"), "Frozen config changed")
    p = plan.get("protocol")
    name = "sources/experiments/m4/secure_study/protocol.json"
    require(
        digest(encoded(p)) == PROTOCOL_OBJECT_SHA256
        and digest(files[name]) == PROTOCOL_SHA256
        and read(directory / name) == p,
        "Maintained protocol changed",
    )
    hashes = plan.get("provenance", {}).get("sources")
    require(
        isinstance(hashes, dict) and set(hashes) == set(source_paths()),
        "Incomplete maintained/helper inventory",
    )
    for name, expected in hashes.items():
        require(digest(files["sources/" + name]) == expected, "Implementation snapshot changed")
    for group in ("protocol_files_sha256", "runtime_files_sha256"):
        for name, expected in p["conditions"][group].items():
            require(digest(files["sources/" + name]) == expected, "Frozen condition changed")
    require(
        digest(files["sources/experiments/m4/initial_load/protocol.json"])
        == p["execution"]["inherited_study_protocol_sha256"],
        "Inherited science changed",
    )
    require(
        set(plan.get("sources", {})) == {item["id"] for item in config["sources"]},
        "Frozen source roster changed",
    )
    for item in config["sources"]:
        name = item["id"]
        frozen = plan["sources"][name]
        declared = declaration(read(directory / "frozen" / name / "model.json"))
        require(
            declared == frozen.get("declaration")
            and digest(files[f"frozen/{name}/model.json"]) == frozen.get("declaration_sha256")
            and digest(files[f"frozen/{name}/model.py"])
            == frozen.get("source_sha256")
            == declared["source_sha256"],
            "Frozen source/declaration changed",
        )
    return plan


def expected_stage(plan, stage, name=None):
    output, checkout = plan["archive_original_path"], plan["provenance"]["checkout_path"]
    if stage == "historical":
        return [
            plan["coordinator_executable"],
            "-B",
            "-S",
            "-m",
            "experiments.m4.secure_study.reference",
            "--output",
            locations.join_recorded(output, "historical"),
            "--timeout-seconds",
            str(plan["configuration"]["timeout_seconds"]),
        ], "historical.log"
    kind, label = stage.rsplit("_", 1)
    project = OBSERVER_PROJECT if kind == "observer" else NATIVE_PROJECT
    args = [
        locations.executable(plan, project, checkout),
        "-B",
        "-E",
        "-s",
        "-m",
        "experiments.m4.secure_study.worker",
        output,
        "--kind",
        kind,
        "--label",
        label,
    ]
    if name is not None:
        args += ["--source", name]
    return args, f"{name}-{kind}-{label}.log" if name is not None else f"reference-{label}.log"


def assessment(directory, plan, state):
    def receipt(path, project, owner):
        if path.is_file():
            record = read(path)
            validate(record, project, plan["protocol"])
            require(
                record["executable"]
                == locations.executable(plan, project, plan["provenance"]["checkout_path"]),
                "Actual interpreter differs from frozen command",
            )
            worker_path = path.with_name("worker.json")
            if worker_path.is_file():
                worker = read(worker_path)
                if isinstance(worker.get("runtime"), dict):
                    validate_numerical_runtime(record, worker["runtime"])
        require(
            path.is_file() or owner["status"] != "completed",
            "Missing accepted numerical runtime attestation",
        )

    for label in ("primary", "repeat"):
        path = directory / "reference" / label / "runtime.json"
        receipt(path, NATIVE_PROJECT, state["reference"])
    for name, owner in state["sources"].items():
        for label in ("primary", "repeat"):
            for part, project in (
                (Path(label), NATIVE_PROJECT),
                (Path("observations") / label, OBSERVER_PROJECT),
            ):
                path = directory / "children" / name / part / "runtime.json"
                receipt(path, project, owner)
    result = INHERITED_ASSESSMENT(directory, plan, state)
    result["execution"] = plan["protocol"]["execution"]
    if (directory / "historical/manifest.json").is_file():
        schema = read(directory / "historical/manifest.json").get("schema")
        result["reference"]["baseline_execution"] = {
            "schema": schema,
            "kind": "maintained_owned_execution"
            if schema == REFERENCE_SCHEMA
            else "verified_historical_evidence",
            "scientific_protocol": "BC-008/2",
        }
    return result


def reconstruct(archive, write_to=None, allow_failed=False):
    from .adapter import activate

    with activate():
        return INHERITED_RECONSTRUCT(archive, write_to=write_to, allow_failed=allow_failed)
