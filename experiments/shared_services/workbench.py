"""Passive installed intake and original-input export for editable studies."""

from pathlib import Path

from experiments.catalogue.storage import decode, encoded
from experiments.m3.researcher.intake import read_regular
from experiments.observation_analysis.intake import import_observations
from experiments.observation_analysis.observations import parse_csv, validate_package

from . import routes, store


def observations(raw):
    package = validate_package(decode(raw["package.json"]))
    checked = parse_csv(raw["observations.csv"], package)
    result = {
        "valid": checked["valid"],
        "errors": [str(error)[:256] for error in checked["errors"][:20]],
        "error_count": len(checked["errors"]),
        "errors_truncated": len(checked["errors"]) > 20
        or any(len(str(e)) > 256 for e in checked["errors"][:20]),
        "visits": [
            {
                "participant_id": visit["participant_id"],
                "visit_id": visit["visit_id"],
                "valid": visit["valid"],
                "rows": len(visit["rows"]),
                "errors": [str(error)[:128] for error in visit["errors"][:2]],
                "error_count": len(visit["errors"]),
                "errors_truncated": len(visit["errors"]) > 2
                or any(len(str(e)) > 128 for e in visit["errors"][:2]),
                "missing_or_censored": sum(
                    row["cpeptide_status"] != "observed" or row["glucose_status"] != "observed"
                    for row in visit["rows"]
                ),
            }
            for visit in checked["visits"]
        ],
    }
    # Preserve complete roster/counts while bounding diagnostic text, not data.
    if len(encoded(result)) > 256 * 1024:
        for visit in result["visits"]:
            visit["errors"] = []
            visit["errors_truncated"] = visit["error_count"] > 0
    store.require(len(encoded(result)) <= 256 * 1024, "Observation summary exceeds bounded roster")
    return result


def inspect(task, inputs, target):
    metadata = routes.capture(task, inputs, target)
    result = {
        "valid": True,
        "task": task,
        "planned_slots": metadata["boundary"]["planned_slots"],
        "input_sha256": metadata["original_sha256"],
        "estimation_performed": False,
    }
    if task == "m3-compare":
        result["capture"] = store.read(target / "original/capture.json")
        result["observation_bytes_verified"] = False
    if task in {"mmtt-sensitivity", "mmtt-sampling"}:
        result["observations"] = observations(
            {
                name: read_regular(target / "original" / name, 16 * 1024 * 1024, name)
                for name in ("package.json", "observations.csv")
            }
        )
    return result


def development(package, csv, design, output):
    from experiments.mmtt_sampling.design import validate_design
    from experiments.mmtt_sampling.intake import development_inventory

    selected = validate_design(decode(read_regular(design, 1024 * 1024, "sampling design")))
    raw = read_regular(package, 1024 * 1024, "development metadata")
    people = validate_package(decode(raw))["participants"]
    # Preserve the native split boundary before reading development observations.
    store.require(
        {person["id"] for person in people} == set(selected["selection_participants"])
        and all(person["allocation"] == "development" for person in people),
        "Use a development-only package containing exactly selection participants",
    )
    record = import_observations(package, csv, output)
    store.require(record["status"] == "valid", "Development import invalid; correct its inputs")
    inventory = development_inventory(output, selected)
    store.require((output / "package.json").read_bytes() == raw, "Development metadata changed")
    return {"development": str(output), "selection_times": inventory, "estimation_performed": False}


def export(project, plan, output):
    descriptor, folder = project.plans[plan]
    task = descriptor["task"]
    store.require(
        task in {"mmtt-sensitivity", "mmtt-sampling", "m4-study-installed", "m3-compare"},
        "Historical inputs are not editable through this interface",
    )
    if task == "m3-compare":
        from .forecasting import materialize

        result = materialize(folder, output)
    elif task == "m4-study-installed":
        from .installed import example

        # Sources come from the trusted selected bundle, never archived Python.
        result = example(task, output, "fasting")
        raw = (folder / "original/config.json").read_bytes()
        routes.boundary(task, {"config.json": raw})
        Path(result["inputs"]["config.json"]).write_bytes(raw)
    else:
        store.snapshot(folder / "original", output)
        names = {"package.json", "observations.csv", "settings.json"}
        if task == "mmtt-sampling":
            names |= {"design.json", "development"}
        result = {"inputs": {name: str(output / name) for name in sorted(names)}}
    return {
        **result,
        "task": task,
        "parent": plan,
        "original_sha256": descriptor["original_sha256"],
    }
