"""Passive AST/TOML inspection of pinned source buffers; never a native admission."""

import ast
import re
import tomllib

from .contract import AUTHORITY, decode, digest, encode, require, source_contract, source_identity

CONTEXTS = (
    ast.If,
    ast.Try,
    ast.TryStar,
    ast.ExceptHandler,
    ast.FunctionDef,
    ast.AsyncFunctionDef,
    ast.ClassDef,
    ast.Lambda,
    ast.For,
    ast.AsyncFor,
    ast.While,
    ast.With,
    ast.AsyncWith,
    ast.Match,
)
SENSITIVE = {
    "__import__",
    "import_module",
    "eval",
    "exec",
    "compile",
    "resource_filename",
    "read_csv",
    "register",
    "parse",
    "load",
    "shim",
}
BLOCKERS = (
    "No new OT-062 project/lock, exact interpreter or platform/ABI selection.",
    "External package initializers, Gym registration/EntryPoint and compat hook sources unbound.",
    "Native/stdlib/vendor/OS libraries, distribution metadata and import hooks unqualified.",
    "Matplotlib font/data/backend/cache closure and actual headless behavior unqualified.",
    "Actual import roots, rllab absence, environment and owned host/process evidence missing.",
    "Three whole-file CSV hashes and specific asset-use rights decisions missing.",
    "Built artifact membership, Quest exclusion, provenance and complete notices unproved.",
    "Native direct/wrapped consumer/bootstrap, parity and host qualification remain unrun.",
    "Separate risk/rights, setup receipt and host/execution admissions remain required.",
)


def _raw(raw, limit, reason, empty=False):
    require(type(raw) is bytes and (empty or len(raw) > 0) and len(raw) <= limit, reason)
    return raw


def _target(node):
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        parent = _target(node.value)
        return parent + "." + node.attr if parent else None
    return None


def analyze_python(module, package_initializer, raw):
    """Syntax observations only; context fields are lexical, not an effect solver."""
    require(type(module) is str and module and type(package_initializer) is bool, "module-label")
    tree = ast.parse(
        _raw(raw, 1024 * 1024, "bounded-source-bytes", empty=True), filename="<source-buffer>"
    )
    imports, calls = [], []

    def walk(node, context):
        common = {"line": getattr(node, "lineno", 0), "context": context}
        if isinstance(node, ast.Import):
            for alias in node.names:
                imports.append({**common, "kind": "import", "module": alias.name, "names": []})
        elif isinstance(node, ast.ImportFrom):
            target = node.module or ""
            if node.level:
                parent = module.split(".") if package_initializer else module.split(".")[:-1]
                require(node.level <= len(parent), "relative-import-outside-package")
                base = parent[: len(parent) - node.level + 1]
                target = ".".join(base + ([target] if target else []))
            imports.append(
                {**common, "kind": "from", "module": target, "names": [a.name for a in node.names]}
            )
        elif isinstance(node, ast.Call):
            target = _target(node.func)
            if target and target.split(".")[-1] in SENSITIVE:
                calls.append(
                    {
                        **common,
                        "target_syntax": target,
                        "positional_literals": [
                            a.value
                            if isinstance(a, ast.Constant) and type(a.value) is str
                            else None
                            for a in node.args
                        ],
                        "all_positional_arguments_string_literals": all(
                            isinstance(a, ast.Constant) and type(a.value) is str for a in node.args
                        ),
                        "keyword_names": [a.arg for a in node.keywords],
                        "keyword_string_literals": [
                            a.value.value
                            if isinstance(a.value, ast.Constant) and type(a.value.value) is str
                            else None
                            for a in node.keywords
                        ],
                    }
                )
        for field, value in ast.iter_fields(node):
            nested = context
            if isinstance(node, CONTEXTS):
                item = {"node": type(node).__name__, "field": field, "line": node.lineno}
                if isinstance(node, ast.If):
                    item["test_syntax"] = ast.unparse(node.test)
                if isinstance(node, ast.ExceptHandler):
                    item["exception_syntax"] = ast.unparse(node.type) if node.type else None
                nested = context + [item]
            for child in value if isinstance(value, list) else [value]:
                if isinstance(child, ast.AST):
                    walk(child, nested)

    walk(tree, [])
    return {
        "module": module,
        "package_initializer": package_initializer,
        "sha256": digest(raw),
        "bytes": len(raw),
        "imports": imports,
        "sensitive_call_syntax": calls,
        "execution_order_inferred": False,
        "dynamic_or_alias_effects_resolved": False,
        "source_executed": False,
    }


def _name(value):
    require(type(value) is str and value, "package-name")
    return re.sub(r"[-_.]+", "-", value).lower()


def analyze_lock(raw):
    """Preserve all declared packages/edges; never select wheels, extras or markers."""
    data = tomllib.loads(_raw(raw, 4 * 1024 * 1024, "bounded-lock-bytes").decode("utf-8"))
    packages = data.get("package")
    require(type(packages) is list and 0 < len(packages) <= 256, "bounded-lock-packages")
    names = [_name(p.get("name")) for p in packages if type(p) is dict]
    require(len(names) == len(packages) and len(set(names)) == len(names), "unique-lock-packages")
    inventory = []
    for package in packages:
        require(
            set(package)
            <= {"name", "version", "source", "dependencies", "sdist", "wheels", "metadata"},
            "unsupported-lock-package-fields",
        )
        require(
            type(package.get("version")) is str and type(package.get("source")) is dict,
            "lock-package-identity",
        )
        dependencies = package.get("dependencies", [])
        require(type(dependencies) is list, "lock-dependencies")
        for edge in dependencies:
            require(type(edge) is dict and _name(edge.get("name")) in names, "lock-edge-target")
            target = packages[names.index(_name(edge["name"]))]
            require(
                ("version" not in edge or edge["version"] == target["version"])
                and ("source" not in edge or edge["source"] == target["source"]),
                "lock-edge-identity",
            )
        wheels = package.get("wheels", [])
        require(type(wheels) is list, "lock-wheels")
        artifacts = {k: package[k] for k in ("sdist", "wheels") if k in package}
        inventory.append(
            {
                "name": _name(package["name"]),
                "version": package["version"],
                "source": package["source"],
                "virtual": "virtual" in package["source"],
                "dependencies": dependencies,
                "declared_wheels": len(wheels),
                "declared_sdist": "sdist" in package,
                "artifact_metadata_sha256": digest(encode(artifacts)),
                "whole_package_record_sha256": digest(encode(package)),
                "artifact_bytes_observed": False,
            }
        )
    return {
        "sha256": digest(raw),
        "bytes": len(raw),
        "requires_python": data.get("requires-python"),
        "packages": sorted(inventory, key=lambda p: p["name"]),
        "nonvirtual_packages": sum(not p["virtual"] for p in inventory),
        "virtual_projects": sum(p["virtual"] for p in inventory),
        "markers_or_extras_evaluated": False,
        "packages_pruned": False,
        "lock_resolved": False,
        "artifact_selected_or_read": False,
    }


def inspect_runtime_sources(source_buffers, native_lock_raw, build_lock_raw):
    """Bind exactly the historical manifest sources and two predecessor locks as data."""
    identity, contract = source_identity(), source_contract()
    code = contract["code"]
    require(
        type(source_buffers) is dict and set(source_buffers) == {r["upstream_path"] for r in code},
        "exact-selected-source-buffers",
    )
    # Complete input binding before parsing any selected source or lock.
    for row in code:
        raw = _raw(
            source_buffers[row["upstream_path"]], 1024 * 1024, "bounded-source-bytes", empty=True
        )
        require(len(raw) == row["bytes"] and digest(raw) == row["sha256"], "source-byte-pin")
    runtime = contract["bootstrap_semantics"]["runtime"]
    for role, raw in (("native", native_lock_raw), ("build", build_lock_raw)):
        _raw(raw, 4 * 1024 * 1024, "bounded-lock-bytes")
        require(digest(raw) == runtime[f"predecessor_{role}_lock_sha256"], "predecessor-lock-pin")
    sources = [
        analyze_python(
            row["module"], row["package_initializer"], source_buffers[row["upstream_path"]]
        )
        for row in code
    ]
    modules = {s["module"]: s for s in sources}
    initializers = {s["module"] for s in sources if s["package_initializer"]}
    roots = [row["module"] for row in contract["consumer_semantics"]["exact_entrypoints"]]
    reached, pending, external, unknown = set(), list(roots), set(), set()
    while pending:
        module = pending.pop()
        if module in reached:
            continue
        if module not in modules:
            unknown.add(module)
            continue
        reached.add(module)
        parts = module.split(".")
        for i in range(1, len(parts)):
            parent = ".".join(parts[:i])
            require(parent in initializers, "selected-parent-initializer-missing")
            pending.append(parent)
        for edge in modules[module]["imports"]:
            target = edge["module"]
            if target == "simglucose" or target.startswith("simglucose."):
                pending.append(target)
                for name in edge["names"]:
                    child = target + "." + name
                    if child in modules:
                        pending.append(child)
            else:
                external.add(target)
    require(not unknown and reached == set(modules), "conservative-selected-module-closure")
    locks = {"native": analyze_lock(native_lock_raw), "build": analyze_lock(build_lock_raw)}
    require(
        all(
            locks[role]["nonvirtual_packages"] == count
            for role, count in (("native", 34), ("build", 8))
        )
        and all(lock["virtual_projects"] == 1 for lock in locks.values()),
        "exact-predecessor-package-counts",
    )
    require(source_identity() == identity, "source-changed-during-inspection")
    return {
        "schema": "opent1d.simglucose-audit1-static-runtime-scope/1",
        "kind": "passive-source-and-predecessor-lock-metadata",
        "status": "blocked",
        "source_identity": identity,
        "upstream_revision": contract["upstream_revision"],
        "selected_source_modules": len(sources),
        "package_initializers": len(initializers),
        "entry_roots": roots,
        "conservative_reachable_modules": sorted(reached),
        "sources": sources,
        "external_import_syntax_including_guarded_demo_edges": sorted(external),
        "locks": locks,
        "resources": contract["resources"],
        "artifact_and_Quest_exclusion_proved": False,
        "runtime_closure_complete": False,
        "native_execution_or_process_observed": False,
        "new_OT062_lock_created": False,
        "blockers": list(BLOCKERS),
        "authority": dict(AUTHORITY),
    }


def inspect_runtime_report(
    report_raw, expected_report_sha256, source_buffers, native_raw, build_raw
):
    """Cold deterministic readback using fixed trusted inspection, not supplied code."""
    _raw(report_raw, 1024 * 1024, "bounded-runtime-report")
    require(digest(report_raw) == expected_report_sha256, "external-runtime-report-pin")
    expected = inspect_runtime_sources(source_buffers, native_raw, build_raw)
    require(encode(decode(report_raw)) == encode(expected), "static-runtime-report-mismatch")
    return {
        "kind": expected["kind"],
        "status": "blocked",
        "selected_source_modules": expected["selected_source_modules"],
        "predecessor_nonvirtual_packages": {
            role: lock["nonvirtual_packages"] for role, lock in expected["locks"].items()
        },
        "native_acceptance": False,
        "new_authority_granted": False,
        "native_execution_deferred": True,
    }
