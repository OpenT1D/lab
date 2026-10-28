"""Versioned execution locations; archived paths are evidence, never authority."""

from experiments.platform_files import recorded_path

from .common import NATIVE_PROJECT, OBSERVER_PROJECT, require

SCHEMA = "opent1d.execution-locations/1"
PROJECTS = (NATIVE_PROJECT, OBSERVER_PROJECT)


def join_recorded(value, *parts):
    return str(recorded_path(value).joinpath(*parts))


def capture(projects=PROJECTS):
    from experiments.desktop.runtime import interpreter

    return {"schema": SCHEMA, "executables": {name: str(interpreter(name)) for name in projects}}


def validate(value, projects=PROJECTS):
    require(
        isinstance(value, dict)
        and set(value) == {"schema", "executables"}
        and value["schema"] == SCHEMA
        and isinstance(value["executables"], dict)
        and set(value["executables"]) == set(projects),
        "Incomplete execution locations",
    )
    for path in value["executables"].values():
        require(".." not in recorded_path(path).parts, "Runtime location must be normalized")
    return value


def executable(record, project, checkout, projects=PROJECTS):
    if "execution_locations" in record:
        return validate(record["execution_locations"], projects)["executables"][project]
    # Historical archives retain their original command contract and spelling.
    return checkout + "/" + project + "/.venv/bin/python"
