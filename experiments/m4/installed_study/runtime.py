"""Actual dependency-overlay attestation, with passive archived validation."""

import platform
import sys

from . import context, profile
from .common import NATIVE_PROJECT, OBSERVER_PROJECT, digest, require


def attest(project):
    value = context.current()
    role = "native" if project == NATIVE_PROJECT else "observer"
    require(project in (NATIVE_PROJECT, OBSERVER_PROJECT), "Unknown numerical project")
    selected = value["record"]["roles"][role]
    return {
        "schema": "m4-installed-runtime-attestation/1",
        "project": project,
        "role": role,
        "python": platform.python_version(),
        "executable": sys.executable,
        "distributions": selected["distributions"],
        "upstream_revisions": selected["upstream_revisions"],
        "runtime_files_sha256": selected["selectors"],
        "attachment_sha256": value["sha256"],
        "dependency_files_sha256": digest(profile.canonical(selected["files"])),
    }


def validate(record, project, p, attachment=None):
    attachment = profile.evidence(attachment or context.current()["record"])
    role = "native" if project == NATIVE_PROJECT else "observer"
    require(project in (NATIVE_PROJECT, OBSERVER_PROJECT), "Unknown recorded numerical project")
    selected = attachment["roles"][role]
    expected = {
        "schema": "m4-installed-runtime-attestation/1",
        "project": project,
        "role": role,
        "python": attachment["interpreter"]["version"],
        "executable": attachment["interpreter"]["executable"],
        "distributions": selected["distributions"],
        "upstream_revisions": selected["upstream_revisions"],
        "runtime_files_sha256": selected["selectors"],
        "attachment_sha256": digest(profile.canonical(attachment)),
        "dependency_files_sha256": digest(profile.canonical(selected["files"])),
    }
    require(
        record == expected
        and isinstance(record["python"], str)
        and record["python"].startswith("3.12."),
        "Actual dependency overlay differs from frozen execution",
    )


def validate_numerical_runtime(receipt, runtime):
    require(
        runtime
        == {
            "python": receipt["python"],
            "numpy": receipt["distributions"]["numpy"],
            "scipy": receipt["distributions"]["scipy"],
        },
        "Numerical record and actual runtime disagree",
    )
