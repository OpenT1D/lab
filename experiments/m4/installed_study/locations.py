"""Inert locations; current context alone selects execution dependencies."""

import re

from experiments.platform_files import recorded_path

from . import context
from .common import NATIVE_PROJECT, OBSERVER_PROJECT, require

SCHEMA = "opent1d.m4-execution-locations/1"
PROJECTS = (NATIVE_PROJECT, OBSERVER_PROJECT)


def join_recorded(value, *parts):
    return str(recorded_path(value).joinpath(*parts))


def capture(projects=PROJECTS):
    return context.capture()


def validate(value, projects=PROJECTS):
    require(
        isinstance(value, dict)
        and set(value) == {"schema", "python", "bootstrap", "attachment", "attachment_sha256"}
        and value["schema"] == SCHEMA
        and re.fullmatch("[a-f0-9]{64}", value["attachment_sha256"]),
        "Incomplete explicit execution locations",
    )
    for key in ("python", "bootstrap", "attachment"):
        path = recorded_path(value[key])
        require(
            path.is_absolute() and ".." not in path.parts, "Normalized recorded location required"
        )
    return value


def executable(record, project, checkout, projects=PROJECTS):
    require(project in projects, "Unknown recorded dependency role")
    return validate(record["execution_locations"])["python"]


def command(record, role, entry, arguments):
    return context.command(role, entry, arguments, record=validate(record["execution_locations"]))
