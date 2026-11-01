"""Bounded M3 adapter: freeze resources; reuse unchanged coordinator and readers."""

import copy
import json
from pathlib import Path

from experiments.catalogue.storage import decode, digest, encoded
from experiments.m3.comparison import common, study
from experiments.m3.researcher.intake import read_regular, validate_bundle
from experiments.platform_files import recorded_path
from experiments.shared_contracts.inventory import reader_source_inventory

from .store import Budget, inventory, read, require, write

TASK = "m3-compare"
MODULE = "experiments.m3.comparison"
ROOT = Path(__file__).resolve().parents[2]


def reader():
    return {
        "module": MODULE,
        "report_schema": common.SCHEMA,
        "trusted_sources_sha256": common.provenance()["sources"],
        "archived_code_execution": False,
    }


def hashes(folder):
    files, _ = inventory(folder, Budget())
    return {name: entry["sha256"] for name, entry in files["files"].items()}


def trusted():
    identity = {**reader(), **reader_source_inventory(MODULE)}
    names = set(identity["trusted_sources_sha256"]) | set(
        identity["reader_static_dependencies_sha256"]
    )
    return identity | {"compatibility": "exact-trusted-reader/1"}, {
        name: digest(read_regular(ROOT / name, 4 * 1024 * 1024, "M3 trusted source"))
        for name in sorted(names)
    }


def boundary(config, original):
    common.validate_config(config, archived=True)
    sources = {}
    for candidate in config["candidates"]:
        folder = original / "candidates" / candidate["id"]
        declaration = read(folder / "declaration.json")
        require(declaration["id"] == candidate["id"], "M3 candidate identity differs")
        source = read_regular(folder / "source.py", 1024 * 1024, "M3 source")
        settings = read_regular(folder / "settings.json", 1024 * 1024, "M3 settings")
        validate_bundle(declaration, source, settings)
        sources[candidate["id"]] = {
            "declaration_sha256": digest((folder / "declaration.json").read_bytes()),
            "source_sha256": digest(source),
            "settings_sha256": digest(settings),
        }
    return {
        "family": "frozen-causal-forecast/1-provisional",
        "binding": {
            "method": common.SCHEMA,
            "implementation_sha256": common.provenance()["sources"],
            "runtime_files_sha256": {},
            "predictors": sources,
            "contract": {
                "history_minutes": [-25, -20, -15, -10, -5, 0],
                "horizon_minutes": 30,
                "unit": "mg/dL",
            },
        },
        "planned_slots": [
            f"{c['id']}/{p['id']}" for c in config["candidates"] for p in config["people"]
        ],
    }


def capture(inputs, target):
    require(set(inputs) == {"config.json"}, "M3 requires one comparison config")
    raw = read_regular(inputs["config.json"], 16 * 1024 * 1024, "M3 config")
    config, bundles = common.metadata(inputs["config.json"])
    require(decode(raw) == config, "M3 configuration changed during capture")
    target.mkdir()
    original = target / "original"
    original.mkdir()
    (original / "config.json").write_bytes(raw)
    access = {}
    # Freeze predictors before opening any assessment observation bytes.
    for identity, bundle in bundles.items():
        folder = original / "candidates" / identity
        folder.mkdir(parents=True)
        for name, key in (
            ("declaration.json", "declaration_raw"),
            ("source.py", "source"),
            ("settings.json", "settings"),
        ):
            (folder / name).write_bytes(bundle[key])
    (original / "observations").mkdir()
    for person in config["people"]:
        try:
            observed = read_regular(person["input"]["file"], 64 * 1024 * 1024, "M3 observation")
        except (OSError, ValueError) as error:
            access[person["id"]] = {"status": "unavailable", "error_type": type(error).__name__}
        else:
            (original / "observations" / (person["id"] + ".json")).write_bytes(observed)
            access[person["id"]] = {"status": "captured", "error_type": None}
    write(original / "capture.json", access)
    (target / "input").mkdir()
    (target / "input/config.json").write_bytes(raw)
    identity, sources = trusted()
    for name in sources:
        path = target / "trusted" / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(read_regular(ROOT / name, 4 * 1024 * 1024, "trusted snapshot"))
    descriptor = {
        "schema": "opent1d.service-freeze/1",
        "task": TASK,
        "boundary": boundary(config, original),
        "reader": identity,
        "original_sha256": hashes(original),
        "trusted_sha256": sources,
    }
    write(target / "descriptor.json", descriptor)
    validate_freeze(target, descriptor, current=True)
    return descriptor


def validate_freeze(folder, descriptor, *, current):
    require(
        set(descriptor)
        == {"schema", "task", "boundary", "reader", "original_sha256", "trusted_sha256"}
        and descriptor["schema"] == "opent1d.service-freeze/1"
        and descriptor["task"] == TASK
        and read(folder / "descriptor.json") == descriptor,
        "Unsupported M3 service freeze",
    )
    original = folder / "original"
    config = read(original / "config.json")
    require(hashes(original) == descriptor["original_sha256"], "M3 originals differ")
    require(descriptor["boundary"] == boundary(config, original), "M3 boundary differs")
    require(
        (folder / "input/config.json").read_bytes() == (original / "config.json").read_bytes(),
        "M3 displayed configuration differs",
    )
    access = read(original / "capture.json")
    require(set(access) == {p["id"] for p in config["people"]}, "M3 capture roster differs")
    expected = {"config.json", "capture.json"}
    for candidate in config["candidates"]:
        expected.update(
            f"candidates/{candidate['id']}/{name}"
            for name in ("declaration.json", "source.py", "settings.json")
        )
    for pid, record in access.items():
        require(
            isinstance(record, dict)
            and set(record) == {"status", "error_type"}
            and (
                (record["status"] == "captured" and record["error_type"] is None)
                or (
                    record["status"] == "unavailable"
                    and isinstance(record["error_type"], str)
                    and bool(record["error_type"])
                )
            ),
            "Invalid M3 capture status",
        )
        if record["status"] == "captured":
            expected.add(f"observations/{pid}.json")
    require(set(descriptor["original_sha256"]) == expected, "M3 frozen resource roster differs")
    identity, sources = trusted()
    require(descriptor["reader"] == identity, "Unsupported trusted M3 reader")
    require(
        descriptor["trusted_sha256"] == sources and hashes(folder / "trusted") == sources,
        "M3 source/protocol/lock snapshots differ",
    )


def effective(config, base):
    config = copy.deepcopy(config)
    for person in config["people"]:
        person["input"]["file"] = str(base / "observations" / (person["id"] + ".json"))
    for candidate in config["candidates"]:
        candidate["declaration"] = str(base / "candidates" / candidate["id"] / "declaration.json")
    return config


def materialize(folder, output):
    """Only location spelling changes; no hash repair, fitting or assessment."""
    from .store import snapshot

    snapshot(folder / "original", output)
    config = effective(read(folder / "original/config.json"), output)
    (output / "config.json").write_bytes(encoded(config))
    for candidate in config["candidates"]:
        location = output / "candidates" / candidate["id"]
        declaration = read(location / "declaration.json")
        declaration["source"]["file"] = str(location / "source.py")
        declaration["settings"]["file"] = str(location / "settings.json")
        (location / "declaration.json").write_bytes(encoded(declaration))
    return {"inputs": {"config.json": str(output / "config.json")}}


def native_result(archive, descriptor, folder):
    # The authoritative reader checks every native child, causal window, support
    # rule and metric, without importing a supplied callback or original input.
    report = study.reconstruct(archive)
    require(
        (archive / "report.json").read_bytes()
        == (json.dumps(report, indent=2, allow_nan=False) + "\n").encode()
        and (archive / "report.md").read_bytes() == study.markdown(report).encode(),
        "Saved M3 report differs from authoritative reader",
    )
    native = read(archive / "plan.json")
    config = read(folder / "original/config.json")
    first = native["config"]["candidates"][0]
    invocation = recorded_path(first["declaration"]).parents[2]
    require(native["config"] == effective(config, invocation), "M3 invocation differs from freeze")
    require(
        native["provenance"]["sources"]
        == descriptor["boundary"]["binding"]["implementation_sha256"],
        "M3 native implementation differs",
    )
    for candidate in config["candidates"]:
        identity = candidate["id"]
        original = folder / "original/candidates" / identity
        frozen = archive / "frozen" / identity
        expected = read(original / "declaration.json")
        expected["source"]["file"] = str(invocation / "candidates" / identity / "source.py")
        expected["settings"]["file"] = str(invocation / "candidates" / identity / "settings.json")
        require(
            native["candidates"][identity]["declaration"] == expected,
            "M3 predictor declaration differs from freeze",
        )
        for name in ("source.py", "settings.json"):
            require(
                (original / name).read_bytes() == (frozen / name).read_bytes(),
                "M3 predictor bytes differ from freeze",
            )
        child = archive / "children" / identity
        for person in config["people"]:
            name = f"observations/{person['id']}.json"
            saved = child / "cases" / person["id"] / "observations.json"
            if saved.exists():
                require(
                    name in descriptor["original_sha256"]
                    and digest(saved.read_bytes()) == descriptor["original_sha256"][name],
                    "M3 observed bytes differ from freeze",
                )
    statuses = {}
    for identity in report["candidate_order"]:
        child = report["candidates"][identity]["single_candidate"]
        for person in config["people"]:
            status = (
                "unavailable"
                if child is None
                else child["evaluation"]["people"][person["id"]]["execution_status"]
            )
            statuses[f"{identity}/{person['id']}"] = "complete" if status == "completed" else status
    coordinator = report["candidates"][report["candidate_order"][0]]["coordinator"][
        "comparison_status"
    ]
    completed = coordinator == "finished" and all(s == "complete" for s in statuses.values())
    return {
        "payload": "native",
        "execution_status": "completed"
        if completed
        else "interrupted"
        if coordinator == "interrupted"
        else "failed",
        "completeness": "complete"
        if completed and report["common"]["complete_cohort"]
        else "incomplete",
        "slot_statuses": statuses,
        "reconstruction": "unchecked",
        "scientific_evidence": "synthetic-only",
        "report_sha256": {
            name: digest((archive / name).read_bytes()) for name in ("report.json", "report.md")
        },
    }
