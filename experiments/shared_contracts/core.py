"""Validate a small content-bound metadata packet, without running archived code."""

import hashlib
import json
from pathlib import Path, PurePosixPath

from experiments.m1.artifacts import strict_json
from experiments.m3.researcher.intake import read_regular
from experiments.platform_files import is_link

PREFIX = "opent1d.shared-"
VERSION = "/1"


def require(condition, message):
    if not condition:
        raise ValueError(message)


def encoded(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def identity(record):
    """The ID binds every field except itself; paths remain project-relative."""
    return digest(encoded({key: value for key, value in record.items() if key != "id"}))


def record(kind, **fields):
    value = {"schema": PREFIX + kind + VERSION, **fields}
    return {**value, "id": identity(value)}


def shape(value, kind, fields):
    require(
        isinstance(value, dict) and set(value) == {"schema", "id", *fields},
        f"Invalid {kind} fields",
    )
    require(value["schema"] == PREFIX + kind + VERSION, f"Unsupported {kind} schema")
    require(value["id"] == identity(value), f"Changed {kind} identity")


def read_asset(directory, asset):
    relative = asset["path"]
    require(isinstance(relative, str) and relative, "Asset path required")
    path = PurePosixPath(relative)
    require(
        not path.is_absolute()
        and ".." not in path.parts
        and "\\" not in relative
        and ":" not in relative
        and "\0" not in relative
        and path.as_posix() == relative,
        "Use a canonical relative asset path",
    )
    target = Path(directory)
    require(target.is_dir() and not is_link(target), "Regular project directory required")
    for part in path.parts:
        target /= part
        require(not is_link(target), "Symlink asset refused")
    require(target.is_file(), "Regular asset required")
    raw = read_regular(target, 128 * 1024 * 1024, "packet asset")
    require(digest(raw) == asset["sha256"], "Asset bytes changed")
    return raw


def asset(directory, path, role):
    return record(
        "asset",
        path=path,
        sha256=digest((Path(directory) / path).read_bytes()),
        role=role,
        rights="public-synthetic-fixture",
    )


def validate(packet, directory):
    """Metadata admission only; authoritative native readers verify result arithmetic.

    Exact field sets make unsupported versions and accidental semantic widening
    explicit. This fixture contract intentionally has no code-loading mechanism.
    """
    require(
        isinstance(packet, dict)
        and set(packet) == {"schema", "project", "assets", "plans", "attempts", "results"}
        and packet["schema"] == "opent1d.contract-packet/1",
        "Unsupported packet",
    )
    project = packet["project"]
    shape(project, "project", {"name"})
    require(isinstance(project["name"], str) and project["name"], "Project name required")
    tables = {}
    for kind in ("assets", "plans", "attempts", "results"):
        rows = packet[kind]
        require(isinstance(rows, list), f"Invalid {kind} roster")
        require(all(isinstance(row, dict) and "id" in row for row in rows), "Missing ID")
        table = {row["id"]: row for row in rows}
        require(len(table) == len(rows), f"Duplicate {kind} identity")
        tables[kind] = table
    assets, plans, attempts, results = (tables[name] for name in tables)
    raw_assets = {}
    for key, value in assets.items():
        shape(value, "asset", {"path", "sha256", "role", "rights"})
        require(value["rights"] == "public-synthetic-fixture", "Unsupported asset rights")
        require(value["role"] in {"scientific-input", "native-report", "execution"}, "Asset role")
        raw_assets[key] = read_asset(directory, value)
    seen = set()
    for key, plan in plans.items():
        shape(
            plan,
            "plan",
            {"project_id", "parent_id", "task", "family", "payload", "binding", "planned_slots"},
        )
        require(plan["project_id"] == project["id"], "Wrong plan project")
        parent = plan["parent_id"]
        require(parent is None or parent in seen, "Parent must be a prior frozen plan")
        if parent is not None:
            require(plans[parent]["task"] == plan["task"], "Derived task differs")
        require(isinstance(plan["payload"], dict) and plan["payload"], "Payload required")
        require(all(ref in assets for ref in plan["payload"].values()), "Missing payload asset")
        require(
            all(assets[ref]["role"] == "scientific-input" for ref in plan["payload"].values()),
            "Wrong payload asset role",
        )
        # Only installed, explicitly selected metadata adapters; never a module
        # or entry point named by a packet or its opaque assets.
        from .selected import boundary

        expected = boundary(
            plan["task"], {name: raw_assets[ref] for name, ref in plan["payload"].items()}
        )
        for field in ("family", "binding", "planned_slots"):
            require(plan[field] == expected[field], f"Task {field} differs")
        seen.add(key)
    ordinals = {}
    for key, attempt in attempts.items():
        shape(
            attempt,
            "attempt",
            {"plan_id", "ordinal", "execution_status", "slot_statuses"},
        )
        require(attempt["plan_id"] in plans, "Missing attempt plan")
        plan = plans[attempt["plan_id"]]
        require(type(attempt["ordinal"]) is int and attempt["ordinal"] > 0, "Attempt ordinal")
        ordinals.setdefault(plan["id"], []).append(attempt["ordinal"])
        require(
            attempt["execution_status"] in {"completed", "failed", "interrupted"},
            "Execution state",
        )
        statuses = attempt["slot_statuses"]
        require(
            isinstance(statuses, dict) and set(statuses) == set(plan["planned_slots"]), "Lost slots"
        )
        require(
            all(s in {"complete", "failed", "unavailable"} for s in statuses.values()), "Slot state"
        )
        require(
            sum(result.get("attempt_id") == key for result in results.values()) == 1,
            "Every terminal attempt needs exactly one result",
        )
    for values in ordinals.values():
        require(sorted(values) == list(range(1, len(values) + 1)), "Lost or duplicate attempt")
    for key, result in results.items():
        shape(
            result, "result", {"attempt_id", "report_asset", "execution_asset", "reader", "states"}
        )
        require(result["attempt_id"] in attempts, "Missing result attempt")
        attempt = attempts[result["attempt_id"]]
        plan = plans[attempt["plan_id"]]
        for field, role in (("report_asset", "native-report"), ("execution_asset", "execution")):
            require(
                result[field] in assets and assets[result[field]]["role"] == role, "Result asset"
            )
        from .selected import outcome, reader

        require(result["reader"] == reader(plan["task"]), "Unsupported reader identity")
        execution, complete, slots = outcome(
            plan["task"],
            strict_json(raw_assets[result["report_asset"]]),
            strict_json(raw_assets[result["execution_asset"]]),
            {name: raw_assets[ref] for name, ref in plan["payload"].items()},
            plan["binding"],
        )
        require(attempt["execution_status"] == execution, "Execution payload differs")
        require(attempt["slot_statuses"] == slots, "Native slot states differ")
        states = result["states"]
        require(
            isinstance(states, dict)
            and set(states) == {"completeness", "reconstruction", "scientific_evidence"}
            and states["completeness"] == ("complete" if complete else "incomplete")
            and states["reconstruction"] in {"unchecked", "verified", "refused"}
            and states["scientific_evidence"] == "synthetic-only",
            "Evidence states differ",
        )
        require(
            not complete or all(s == "complete" for s in attempt["slot_statuses"].values()),
            "Complete result lost required slots",
        )
    return packet
