"""Freeze one source-model synthetic protocol before evaluation; no inferred defaults."""

import platform
import sys
from pathlib import Path

from experiments.catalogue.storage import ROOT, decode, digest, dump, fresh, load_sealed, seal
from experiments.m3.researcher.intake import read_regular
from experiments.platform_process import SOURCE_FILES as PROCESS_SOURCES

from .estimator import VERSION, validate_variant
from .intake import INPUTS
from .observations import fields, identifier, number, validate_package

SCHEMA = "opent1d.observation-analysis-plan/1"
SETTINGS = "opent1d.observation-analysis-settings/1"
DIRECTORY = Path(__file__).resolve().parent
PROTOCOL = DIRECTORY / "protocol.json"
SHARED_SOURCES = (
    "experiments/catalogue/storage.py",
    "experiments/m3/researcher/intake.py",
    "experiments/m3/common.py",
    "experiments/m1/artifacts.py",
    "experiments/platform_files.py",
) + PROCESS_SOURCES
ANCESTRY = (
    "experiments/m4/c_peptide/model.py",
    "experiments/m4/c_peptide/reference.py",
    "experiments/m4/c_peptide/protocol.json",
    "experiments/ot053_feasibility/handoff.json",
    "docs/decisions/0067-mmtt-feasibility-boundary.md",
)


def source_identity():
    names = [
        path.relative_to(ROOT).as_posix()
        for path in sorted(DIRECTORY.glob("*.py"))
        if not path.name.startswith("test_")
    ]
    names.extend(SHARED_SOURCES)
    return {
        name: digest(read_regular(ROOT / name, 2 * 1024 * 1024, "trusted source")) for name in names
    }


def runtime_identity():
    return {
        "python": sys.version,
        "implementation": platform.python_implementation(),
        "platform": platform.platform(),
        "numerical_dependencies": "Python standard library",
    }


def validate_settings(settings, package):
    expected = ("schema", "visit_order", "variants", "uncertainty")
    if isinstance(settings, dict) and "required_times_min" in settings:
        expected += ("required_times_min",)
    fields(settings, expected, "analysis settings")
    if settings["schema"] != SETTINGS:
        raise ValueError("Unsupported analysis settings schema")
    order = settings["visit_order"]
    if not isinstance(order, list) or len(order) != 2 or order[0] == order[1]:
        raise ValueError("Explicit distinct baseline/followup visit order required")
    for value in order:
        identifier(value, "ordered visit")
    for person in package["participants"]:
        if set(order) != {visit["id"] for visit in person["visits"]}:
            raise ValueError("Plan visit order differs from declared participant visits")
    if "required_times_min" in settings:
        required = settings["required_times_min"]
        if not isinstance(required, list) or len(required) < 2:
            raise ValueError("Declare required actual measurement times including 0 and 120")
        for value in required:
            number(value, "required measurement time")
        if (
            required[0] != 0
            or required[-1] != 120
            or any(b <= a for a, b in zip(required, required[1:]))
        ):
            raise ValueError("Required measurement times must increase from 0 to 120 minutes")
    variants = settings["variants"]
    if not isinstance(variants, list) or not 2 <= len(variants) <= 8:
        raise ValueError("Freeze 2–8 required engineering variants")
    for variant in variants:
        validate_variant(variant)
    if len({value["id"] for value in variants}) != len(variants):
        raise ValueError("Duplicate variant id")
    uncertainty = settings["uncertainty"]
    fields(
        uncertainty,
        ("draws", "seed", "independent_sd_pmol_l", "paired_offset_sd_pmol_l", "scope"),
        "uncertainty",
    )
    if (
        type(uncertainty["draws"]) is not int
        or not 32 <= uncertainty["draws"] <= 1024
        or type(uncertainty["seed"]) is not int
        or not 0 <= uncertainty["seed"] < 2**64
        or uncertainty["scope"] != "synthetic-engineering"
    ):
        raise ValueError("Declare synthetic uncertainty, 32–1024 draws and a 64-bit integer seed")
    number(uncertainty["independent_sd_pmol_l"], "independent synthetic SD", strict=True)
    number(uncertainty["paired_offset_sd_pmol_l"], "paired synthetic offset SD")
    return settings


def freeze(package_path, csv_path, settings_path, output):
    """Read metadata and bind raw bytes, without inspecting evaluation outcomes."""
    raw = {
        "package.json": read_regular(package_path, INPUTS["package.json"], "package"),
        "observations.csv": read_regular(csv_path, INPUTS["observations.csv"], "observations"),
        "settings.json": read_regular(settings_path, 1024 * 1024, "analysis settings"),
    }
    package = validate_package(decode(raw["package.json"]))
    validate_settings(decode(raw["settings.json"]), package)
    protocol = read_regular(PROTOCOL, 1024 * 1024, "protocol")
    plan = {
        "schema": SCHEMA,
        "task": "mmtt-sensitivity",
        "kind": "synthetic",
        "method": VERSION,
        "protocol_sha256": digest(protocol),
        "input_sha256": {name: digest(value) for name, value in raw.items()},
        "implementation_sha256": source_identity(),
        "runtime": runtime_identity(),
        "ancestry_sha256": {
            name: digest(read_regular(ROOT / name, 1024 * 1024, "ancestry")) for name in ANCESTRY
        },
        "settings": decode(raw["settings.json"]),
        "human_execution_authorized": False,
    }
    output = fresh(output, (package_path, csv_path, settings_path))
    for name, value in raw.items():
        (output / name).write_bytes(value)
    (output / "protocol.json").write_bytes(protocol)
    dump(output / "plan.json", plan)
    # Source snapshots are opaque provenance; only the installed trusted reader executes.
    for name in (*plan["implementation_sha256"], *plan["ancestry_sha256"]):
        target = output / "sources" / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(read_regular(ROOT / name, 2 * 1024 * 1024, "source snapshot"))
    seal(output)
    return plan


def load_plan(directory, *, check_runtime=False):
    directory = load_sealed(directory)
    plan = decode(read_regular(directory / "plan.json", 2 * 1024 * 1024, "analysis plan"))
    fields(
        plan,
        (
            "schema",
            "task",
            "kind",
            "method",
            "protocol_sha256",
            "input_sha256",
            "implementation_sha256",
            "runtime",
            "ancestry_sha256",
            "settings",
            "human_execution_authorized",
        ),
        "analysis plan",
    )
    if (
        plan["schema"] != SCHEMA
        or plan["task"] != "mmtt-sensitivity"
        or plan["kind"] != "synthetic"
        or plan["method"] != VERSION
        or plan["human_execution_authorized"] is not False
        or plan["protocol_sha256"] != digest(PROTOCOL.read_bytes())
        or (directory / "protocol.json").read_bytes() != PROTOCOL.read_bytes()
        or plan["implementation_sha256"] != source_identity()
    ):
        raise ValueError(
            "Plan method, protocol or trusted implementation differs; freeze a new plan"
        )
    expected_ancestry = {name: digest((ROOT / name).read_bytes()) for name in ANCESTRY}
    if plan["ancestry_sha256"] != expected_ancestry:
        raise ValueError("Source-model ancestry differs")
    for name, sha in {**plan["implementation_sha256"], **plan["ancestry_sha256"]}.items():
        if (
            digest(read_regular(directory / "sources" / name, 2 * 1024 * 1024, "saved source"))
            != sha
        ):
            raise ValueError("Opaque source snapshot differs")
    if check_runtime and plan["runtime"] != runtime_identity():
        raise ValueError("Execution runtime differs from frozen plan; freeze explicitly again")
    raw = {
        name: read_regular(directory / name, limit, name)
        for name, limit in {**INPUTS, "settings.json": 1024 * 1024}.items()
    }
    if plan["input_sha256"] != {name: digest(value) for name, value in raw.items()}:
        raise ValueError("Plan input identities differ")
    package = validate_package(decode(raw["package.json"]))
    settings = validate_settings(decode(raw["settings.json"]), package)
    if settings != plan["settings"]:
        raise ValueError("Saved settings differ from plan")
    return plan, package, raw
