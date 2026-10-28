"""Root tooling lock admission with explicit, recorded platform applicability."""

import importlib.metadata
import platform
import re
import sys
import tomllib

ROOT_RUNTIME_SCHEMA = "opent1d.maintained-campaign-root-runtime/1"
MARKER = re.compile(r"sys_platform\s*(==|!=)\s*(['\"])([a-z0-9_]+)\2\Z")


def root_selection(sys_platform, lock=None):
    """Walk the fixed dev group; unsupported marker/extra selection fails closed."""
    from .common import ROOT, regular, require

    require(
        isinstance(sys_platform, str) and re.fullmatch(r"[a-z0-9_]+", sys_platform),
        "Invalid recorded root platform",
    )
    if lock is None:
        _, raw = regular(ROOT / "uv.lock")
        lock = tomllib.loads(raw.decode())
    roots = lock["manifest"]["dependency-groups"]["dev"]
    require(isinstance(roots, list) and roots, "Root dev dependency group is missing")
    by_name = {}
    for item in lock["package"]:
        require(item["name"] not in by_name, "Ambiguous root lock package version")
        require(
            "virtual" not in item["source"]
            and not item.get("optional-dependencies")
            and not item.get("dev-dependencies"),
            "Unsupported root optional/project dependency selection",
        )
        by_name[item["name"]] = item
    root_names = []
    for item in roots:
        require(set(item) <= {"name", "specifier"}, "Unsupported root dev dependency selector")
        root_names.append(item["name"])
    selected, markers = set(), []
    pending = list(root_names)
    while pending:
        name = pending.pop()
        if name in selected:
            continue
        require(name in by_name, "Root dependency absent from lock: " + name)
        selected.add(name)
        for dependency in by_name[name].get("dependencies", []):
            require(
                isinstance(dependency, dict) and set(dependency) <= {"name", "marker"},
                "Unsupported root dependency selector",
            )
            child, included = dependency["name"], True
            if "marker" in dependency:
                expression = dependency["marker"]
                matched = MARKER.fullmatch(expression) if isinstance(expression, str) else None
                require(matched is not None, "Unsupported root lock environment marker")
                operator, _, target = matched.groups()
                included = sys_platform == target if operator == "==" else sys_platform != target
                markers.append(
                    {
                        "package": name,
                        "dependency": child,
                        "marker": expression,
                        "included": included,
                    }
                )
            if included:
                pending.append(child)
    selection = {
        "dependency_group": "dev",
        "marker_environment": {"sys_platform": sys_platform},
        "roots": sorted(root_names),
        "packages": sorted(selected),
        "markers": sorted(markers, key=lambda item: (item["package"], item["dependency"])),
    }
    records = {
        name: {key: by_name[name][key] for key in ("version", "source")}
        for name in sorted(selected)
    }
    return records, selection


def attest_root():
    """Check installed applicable distributions; never import tooling or a candidate."""
    from .common import ROOT, digest, require

    records, selection = root_selection(sys.platform)
    distributions, revisions = {}, {}
    for name, expected in records.items():
        installed = importlib.metadata.distribution(name)
        require(installed.version == expected["version"], "Wrong installed root " + name)
        require("git" not in expected["source"], "Unsupported root VCS runtime dependency")
        distributions[name] = installed.version
    require(platform.python_version().startswith("3.12."), "Wrong root Python runtime")
    return {
        "schema": ROOT_RUNTIME_SCHEMA,
        "project": ".",
        "python": platform.python_version(),
        "executable": sys.executable,
        "distributions": distributions,
        "upstream_revisions": revisions,
        "runtime_files_sha256": {
            name: digest((ROOT / name).read_bytes()) for name in ("pyproject.toml", "uv.lock")
        },
        "selection": selection,
    }
