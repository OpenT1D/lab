"""Actual installed-runtime attestation; dependency imports occur only in workers."""

import importlib.metadata
import json
import platform
import sys

from .common import ROOT, package_records, require, sha256


def attest(project):
    records = package_records(project)
    distributions, revisions = {}, {}
    for name, expected in records.items():
        installed = importlib.metadata.distribution(name)
        require(installed.version == expected["version"], f"Wrong installed {name}")
        distributions[name] = installed.version
        if "git" in expected["source"]:
            direct = json.loads(installed.read_text("direct_url.json") or "null")
            wanted = expected["source"]["git"].rsplit("#", 1)[1]
            require(
                isinstance(direct, dict) and direct.get("vcs_info", {}).get("commit_id") == wanted,
                f"Wrong installed upstream revision: {name}",
            )
            revisions[name] = wanted
    require(platform.python_version().startswith("3.12."), "Wrong Python runtime")
    return {
        "schema": "m4-secure-runtime-attestation/1",
        "project": project,
        "python": platform.python_version(),
        "executable": sys.executable,
        "distributions": distributions,
        "upstream_revisions": revisions,
        "runtime_files_sha256": {
            name: sha256(ROOT / project / name) for name in ("pyproject.toml", "uv.lock")
        },
    }


def validate(record, project, p):
    expected = (
        p["execution"]["package_records"]
        if project == p["execution"]["native_project"]
        else package_records(project)
    )
    require(
        isinstance(record, dict)
        and set(record)
        == {
            "schema",
            "project",
            "python",
            "executable",
            "distributions",
            "upstream_revisions",
            "runtime_files_sha256",
        },
        "Incomplete runtime attestation",
    )
    require(
        record["schema"] == "m4-secure-runtime-attestation/1"
        and record["project"] == project
        and isinstance(record["python"], str)
        and record["python"].startswith("3.12.")
        and isinstance(record["executable"], str)
        and record["executable"]
        and record["distributions"] == {name: item["version"] for name, item in expected.items()}
        and record["upstream_revisions"]
        == {
            name: item["source"]["git"].rsplit("#", 1)[1]
            for name, item in expected.items()
            if "git" in item["source"]
        }
        and record["runtime_files_sha256"]
        == {
            name: p["conditions"]["runtime_files_sha256"][project + "/" + name]
            for name in ("pyproject.toml", "uv.lock")
        },
        "Archived actual runtime differs from frozen successor execution",
    )


def validate_numerical_runtime(receipt, runtime):
    require(
        runtime
        == {
            "python": receipt["python"],
            "numpy": receipt["distributions"]["numpy"],
            "scipy": receipt["distributions"]["scipy"],
        },
        "Numerical record and actual installed runtime disagree",
    )
