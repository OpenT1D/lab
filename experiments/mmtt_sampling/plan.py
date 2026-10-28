"""Frozen Task 2 inputs and development evidence; no evaluation fitting at freeze."""

import csv
import io
import shutil
from pathlib import Path

from experiments.catalogue.storage import ROOT, decode, digest, dump, fresh, load_sealed, seal
from experiments.m3.researcher.intake import read_regular
from experiments.observation_analysis.estimator import VERSION
from experiments.observation_analysis.intake import INPUTS
from experiments.observation_analysis.observations import COLUMNS, fields, validate_package
from experiments.observation_analysis.plan import ANCESTRY, runtime_identity, validate_settings
from experiments.observation_analysis.plan import PROTOCOL as SHARED_PROTOCOL
from experiments.observation_analysis.plan import source_identity as shared_source_identity

from .design import validate_design
from .intake import development_inventory

SCHEMA = "opent1d.mmtt-sampling-plan/1"
TASK = "mmtt-sampling"
DIRECTORY = Path(__file__).resolve().parent
PROTOCOL = DIRECTORY / "protocol.json"
RAW_LIMITS = {**INPUTS, "settings.json": 1024 * 1024, "design.json": 1024 * 1024}
ANCESTRY_FILES = (
    *ANCESTRY,
    "docs/decisions/0068-synthetic-observation-analysis-contract.md",
    "docs/decisions/0069-mmtt-sampling-reuse.md",
)


def source_identity():
    names = [p.relative_to(ROOT).as_posix() for p in sorted(DIRECTORY.glob("*.py"))]
    return {
        **shared_source_identity(),
        **{
            name: digest(read_regular(ROOT / name, 2 * 1024 * 1024, "trusted sampling source"))
            for name in names
        },
    }


def ancestry_identity():
    return {
        name: digest(read_regular(ROOT / name, 1024 * 1024, "ancestry")) for name in ANCESTRY_FILES
    }


def development_rows(raw, participants):
    """Compare provenance cells only; never calculate an evaluation outcome."""
    try:
        reader = csv.DictReader(io.StringIO(raw.decode("utf-8-sig")), strict=True)
        if tuple(reader.fieldnames or ()) != COLUMNS:
            raise ValueError("CSV header differs from shared observation contract")
        rows = []
        for index, row in enumerate(reader, 2):
            if index > 100_001 or None in row or None in row.values():
                raise ValueError("Invalid CSV framing or row limit")
            if row["participant_id"] in participants:
                rows.append(tuple(row[column] for column in COLUMNS))
        return sorted(rows)
    except (UnicodeError, csv.Error) as error:
        raise ValueError("Invalid UTF-8 or CSV framing") from error


def validate_inputs(raw, development):
    package = validate_package(decode(raw["package.json"]))
    design = validate_design(decode(raw["design.json"]))
    settings = decode(raw["settings.json"])
    if "required_times_min" in settings:
        raise ValueError(
            "Task 2 owns required_times_min; supply the shared base settings without it"
        )
    validate_settings(settings, package)
    if {person["id"]: person["allocation"] for person in package["participants"]} != design[
        "allocation"
    ]:
        raise ValueError("Study roster/allocation differs from the frozen sampling design")
    inventory = development_inventory(development, design)
    selected = set(design["selection_participants"])
    dev_package = decode(
        read_regular(development / "package.json", INPUTS["package.json"], "development")
    )
    people = {person["id"]: person for person in package["participants"]}
    if dev_package["units"] != package["units"] or any(
        person != people[person["id"]] for person in dev_package["participants"]
    ):
        raise ValueError("Development metadata differ from study metadata")
    dev_csv = read_regular(
        development / "observations.csv", INPUTS["observations.csv"], "development"
    )
    if development_rows(raw["observations.csv"], selected) != development_rows(dev_csv, selected):
        raise ValueError("Development observation cells differ from the selection evidence")
    return package, design, settings, inventory


def freeze(package_path, csv_path, settings_path, design_path, development, output):
    development = Path(development).absolute()
    raw = {
        name: read_regular(path, RAW_LIMITS[name], name)
        for name, path in (
            ("package.json", package_path),
            ("observations.csv", csv_path),
            ("settings.json", settings_path),
            ("design.json", design_path),
        )
    }
    package, design, settings, inventory = validate_inputs(raw, development)
    dev_manifest = read_regular(development / "manifest.json", 2 * 1024 * 1024, "development seal")
    plan = {
        "schema": SCHEMA,
        "task": TASK,
        "kind": "synthetic",
        "method": VERSION,
        "input_sha256": {name: digest(value) for name, value in raw.items()},
        "protocol_sha256": digest(PROTOCOL.read_bytes()),
        "shared_protocol_sha256": digest(SHARED_PROTOCOL.read_bytes()),
        "implementation_sha256": source_identity(),
        "ancestry_sha256": ancestry_identity(),
        "runtime": runtime_identity(),
        "design": design,
        "settings": settings,
        "selection_times": inventory,
        "development_manifest_sha256": digest(dev_manifest),
        "human_execution_authorized": False,
    }
    output = fresh(output, (package_path, csv_path, settings_path, design_path, development))
    for name, value in raw.items():
        (output / name).write_bytes(value)
    (output / "protocol.json").write_bytes(PROTOCOL.read_bytes())
    (output / "shared-protocol.json").write_bytes(SHARED_PROTOCOL.read_bytes())
    shutil.copytree(development, output / "development", symlinks=True)
    validate_inputs(raw, output / "development")
    if (output / "development/manifest.json").read_bytes() != dev_manifest:
        raise ValueError("Development evidence changed during snapshot")
    for name in {**plan["implementation_sha256"], **plan["ancestry_sha256"]}:
        target = output / "sources" / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(read_regular(ROOT / name, 2 * 1024 * 1024, "opaque source snapshot"))
    dump(output / "plan.json", plan)
    seal(output)
    return plan


def load_plan(directory, *, check_runtime=False):
    directory = load_sealed(directory)
    plan = decode(read_regular(directory / "plan.json", 8 * 1024 * 1024, "sampling plan"))
    fields(
        plan,
        (
            "schema",
            "task",
            "kind",
            "method",
            "input_sha256",
            "protocol_sha256",
            "shared_protocol_sha256",
            "implementation_sha256",
            "ancestry_sha256",
            "runtime",
            "design",
            "settings",
            "selection_times",
            "development_manifest_sha256",
            "human_execution_authorized",
        ),
        "sampling plan",
    )
    if (
        plan["schema"] != SCHEMA
        or plan["task"] != TASK
        or plan["kind"] != "synthetic"
        or plan["method"] != VERSION
        or plan["human_execution_authorized"] is not False
        or plan["implementation_sha256"] != source_identity()
        or plan["ancestry_sha256"] != ancestry_identity()
    ):
        raise ValueError("Sampling plan source, ancestry or scope differs; freeze explicitly again")
    for name, path, field in (
        ("protocol.json", PROTOCOL, "protocol_sha256"),
        ("shared-protocol.json", SHARED_PROTOCOL, "shared_protocol_sha256"),
    ):
        if (directory / name).read_bytes() != path.read_bytes() or plan[field] != digest(
            path.read_bytes()
        ):
            raise ValueError("Frozen protocol differs")
    if check_runtime and plan["runtime"] != runtime_identity():
        raise ValueError("Sampling execution runtime differs; freeze explicitly again")
    for name, sha in {**plan["implementation_sha256"], **plan["ancestry_sha256"]}.items():
        if (
            digest(read_regular(directory / "sources" / name, 2 * 1024 * 1024, "saved source"))
            != sha
        ):
            raise ValueError("Opaque sampling source snapshot differs")
    raw = {name: read_regular(directory / name, limit, name) for name, limit in RAW_LIMITS.items()}
    if plan["input_sha256"] != {name: digest(value) for name, value in raw.items()}:
        raise ValueError("Sampling input identities differ")
    package, design, settings, inventory = validate_inputs(raw, directory / "development")
    if (
        plan["design"] != design
        or plan["settings"] != settings
        or plan["selection_times"] != inventory
        or plan["development_manifest_sha256"]
        != digest((directory / "development/manifest.json").read_bytes())
    ):
        raise ValueError("Sampling settings or development selection evidence differ")
    return plan, package, raw
