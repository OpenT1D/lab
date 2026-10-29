"""Authoritative successor reader; unchanged scientific assessment, standard library."""

from pathlib import Path

from experiments.m4.causal_secretion.common import declaration
from experiments.m4.initial_load import report as inherited

from . import locations, profile
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
    attachment = profile.evidence(read(directory / "runtime-context.json"))
    provenance = plan.get("provenance", {})
    require(
        provenance.get("application") == attachment["application"]
        and provenance.get("git_head") == attachment["application"]["source"]["revision"]
        and provenance.get("git_dirty") == attachment["application"]["source"]["dirty"]
        and provenance.get("sources")
        == {name: value["sha256"] for name, value in attachment["source_files"].items()},
        "Frozen application/source provenance differs from runtime attachment",
    )
    require(
        digest(files["runtime-context.json"])
        == plan["execution_locations"]["attachment_sha256"]
        == plan["provenance"]["runtime_attachment_sha256"],
        "Frozen runtime attachment changed",
    )
    require(
        attachment["interpreter"]["executable"]
        == plan["coordinator_executable"]
        == plan["execution_locations"]["python"],
        "Coordinator identity differs",
    )
    config = validate_config(read(directory / "config.json"))
    require(config == plan.get("configuration"), "Frozen config changed")
    p = plan.get("protocol")
    name = "sources/experiments/m4/installed_study/protocol.json"
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
    validate_ownership(directory, plan, read(directory / "state.json"))
    return plan


def expected_stage(plan, stage, name=None):
    output = plan["archive_original_path"]
    if stage == "historical":
        return locations.command(
            plan,
            "coordinator",
            "reference",
            [
                "--output",
                locations.join_recorded(output, "historical"),
                "--timeout-seconds",
                str(plan["configuration"]["timeout_seconds"]),
            ],
        ), "historical.log"
    kind, label = stage.rsplit("_", 1)
    arguments = [output, "--kind", kind, "--label", label]
    if name is not None:
        arguments += ["--source", name]
    args = locations.command(
        plan, "observer" if kind == "observer" else "native", "worker", arguments
    )
    return args, f"{name}-{kind}-{label}.log" if name is not None else f"reference-{label}.log"


def validate_ownership(directory, plan, state):
    from .process import validate_receipt

    for name, owner in [(None, state["reference"]), *state["sources"].items()]:
        for attempt in owner["attempts"]:
            args, logfile = expected_stage(plan, attempt["stage"], name)
            require(attempt["argv"] == args, "Stage ledger command differs from frozen execution")
            validate_receipt(
                directory / "logs" / logfile,
                args,
                attempt["timeout_seconds"],
                attempt["exit_code"],
                attempt["status"],
                20 if attempt["stage"] == "historical" else 10,
            )


def assessment(directory, plan, state):
    validate_ownership(directory, plan, state)
    attachment = profile.evidence(read(directory / "runtime-context.json"))

    def receipt(path, project, owner):
        if path.is_file():
            record = read(path)
            validate(record, project, plan["protocol"], attachment)
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

    archive = profile.archive(archive)
    with activate():
        return INHERITED_RECONSTRUCT(archive, write_to=write_to, allow_failed=allow_failed)
