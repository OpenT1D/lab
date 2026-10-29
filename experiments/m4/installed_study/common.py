"""Passive successor intake and frozen execution identities; standard library only."""

import copy
import tomllib
from pathlib import Path

from experiments.m4.causal_secretion import common as causal
from experiments.m4.initial_load import common as inherited
from experiments.m4.initial_load.common import (
    ROOT,
    digest,
    encoded,
    read,
    regular,
    require,
    sha256,
)
from experiments.m4.initial_load.common import (
    dump as dump,
)

HERE = Path(__file__).resolve().parent
VERSION = "m4-installed-study-run/1"
CONFIG_SCHEMA = "m4-installed-study-config/1"
REPORT_SCHEMA = "m4-installed-study-report/1"
REFERENCE_SCHEMA = "m4-installed-reference-run/1"
PROTOCOL_SHA256 = "19f453052babcb4d8e6df3e4a18545d5a5af00389d76d9cecc0cad781fe24687"
PROTOCOL_OBJECT_SHA256 = "2cb0074e4b0575c8fc28b93287d5f6fca8a343925ba9a4ec603959c8e712f923"
NATIVE_PROJECT = "experiments/m4/installed_study/native"
OBSERVER_PROJECT = "experiments/m4/installed_study/observer"
# Capture the original function before adapter.activate replaces the public
# inherited entrypoint. Workers that only attest/import need no source inventory.
INHERITED_SOURCE_ROOTS = inherited.source_roots
INHERITED_VALIDATE = inherited.validate_config
INHERITED_PROTOCOL = inherited.protocol


def package_records(project):
    return {
        item["name"]: {key: item[key] for key in ("version", "source") if key in item}
        for item in tomllib.loads((ROOT / project / "uv.lock").read_text())["package"]
        if "virtual" not in item["source"]
    }


def protocol():
    raw = (HERE / "protocol.json").read_bytes()
    require(digest(raw) == PROTOCOL_SHA256, "Maintained protocol bytes changed")
    p = read(HERE / "protocol.json")
    require(digest(encoded(p)) == PROTOCOL_OBJECT_SHA256, "Maintained conditions changed")
    for group in ("protocol_files_sha256", "runtime_files_sha256"):
        for name, expected in p["conditions"][group].items():
            require(sha256(ROOT / name) == expected, f"Frozen condition changed: {name}")
    require(
        sha256(ROOT / "experiments/m4/initial_load/protocol.json")
        == p["execution"]["inherited_study_protocol_sha256"],
        "Inherited scientific protocol changed",
    )
    require(
        package_records(NATIVE_PROJECT) == p["execution"]["package_records"],
        "Maintained package inventory changed",
    )
    require(
        sha256(HERE / "runtime-review.json") == p["execution"]["runtime_review_sha256"],
        "Runtime review identity changed",
    )
    for project, key in (
        (OBSERVER_PROJECT, "observer_package_records"),
        ("experiments/m4/installed_study/build_inputs", "build_package_records"),
    ):
        require(
            package_records(project) == p["execution"][key], "Reviewed package inventory changed"
        )
    return p


def validate_config(config):
    require(
        isinstance(config, dict) and config.get("schema") == CONFIG_SCHEMA,
        "Explicit maintained study config required",
    )
    original = copy.deepcopy(config)
    original["schema"] = "m4-initial-load-config/1"
    INHERITED_VALIDATE(original)
    return config


def intake(path):
    from experiments.m1.artifacts import strict_json

    path, raw = regular(path, 65536, "Maintained study config")
    config = validate_config(strict_json(raw))
    protocol()
    bundles = {}
    for item in config["sources"]:
        bundle = {"config_raw": raw}
        for key, limit in (("model", 1048576), ("declaration", 65536)):
            target = Path(item[key])
            if not target.is_absolute():
                target = path.parent / target
            bundle[key + "_path"], bundle[key + "_raw"] = regular(target, limit, key)
        require(bundle["model_path"].suffix == ".py", "Model must be Python source")
        bundle["declared"] = causal.declaration(strict_json(bundle["declaration_raw"]))
        require(
            digest(bundle["model_raw"]) == bundle["declared"]["source_sha256"],
            "Model hash differs from declaration",
        )
        bundles[item["id"]] = bundle
    return config, bundles


def source_paths():
    names = set(INHERITED_SOURCE_ROOTS()) | {
        *(path.relative_to(ROOT).as_posix() for path in HERE.glob("*.py")),
        "experiments/m4/installed_study/protocol.json",
        "experiments/m4/installed_study/runtime-review.json",
        "experiments/m4/secure_study/protocol.json",
        "docs/research/m4-installed-runtime-protocol.md",
        "experiments/m4/beta_cell/runtime/test_model.py",
        "experiments/m4/beta_cell/runtime/model.py",
        "experiments/m4/beta_cell/runtime/verify.py",
        "experiments/m4/beta_cell/runtime/run.py",
        "experiments/m4/beta_cell/runtime/report.py",
        "experiments/m4/beta_cell/runtime/plot.py",
        "experiments/m4/beta_cell/protocol.json",
        "experiments/m4/c_peptide/test_model.py",
        *(
            "experiments/m4/installed_study/" + role + "/" + name
            for role in ("native", "observer", "build_inputs")
            for name in ("pyproject.toml", "uv.lock")
        ),
    }
    conditions = protocol()["conditions"]
    names.update(conditions["runtime_files_sha256"])
    names.update(conditions["protocol_files_sha256"])
    while True:
        closed = set(inherited.source_closure(names))
        parents = {
            (parent / "__init__.py").as_posix()
            for name in closed
            for parent in Path(name).parents
            if parent.parts and (ROOT / parent / "__init__.py").is_file()
        }
        if parents <= closed:
            return sorted(closed)
        names = closed | parents


def source_snapshots():
    return {name: (ROOT / name).read_bytes() for name in source_paths()}


def prepare(path):
    config, bundles = intake(path)
    p = protocol()
    return {
        "schema": "m4-installed-study-preparation/1",
        "configuration": config,
        "config_sha256": digest(next(iter(bundles.values()))["config_raw"]),
        "source_order": [item["id"] for item in config["sources"]],
        "sources": {
            name: {
                "declaration": bundle["declared"],
                "source_sha256": digest(bundle["model_raw"]),
                "declaration_sha256": digest(bundle["declaration_raw"]),
                "model_path": str(bundle["model_path"]),
                "declaration_path": str(bundle["declaration_path"]),
            }
            for name, bundle in bundles.items()
        },
        "scenarios": [
            {"id": name, "initial_gastric_solid_mg": inherited.SCENARIOS[name]}
            for name in config["scenarios"]
        ],
        "protocol": p,
        "protocol_sha256": PROTOCOL_SHA256,
        "runtime_files_sha256": p["conditions"]["runtime_files_sha256"],
        "implementation_sources_sha256": {
            name: digest(raw) for name, raw in source_snapshots().items()
        },
        "execution": p["execution"],
    }
