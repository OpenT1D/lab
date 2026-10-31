"""Immutable preexecution rosters and ledger-prefix comparison reconstruction."""

import copy
import json
import re
import tempfile
from pathlib import Path

from experiments.shared_contracts.inventory import reader_source_inventory

from . import comparison_tasks as tasks
from . import store

SCHEMA = "opent1d.plan-comparison/1"
REPORT_SCHEMA = "opent1d.plan-comparison-report/1"
ROOT = Path(__file__).resolve().parents[2]


def reader():
    return {
        "schema": REPORT_SCHEMA,
        **reader_source_inventory("experiments.shared_services.comparisons"),
        "archived_code_execution": False,
    }


def text(value, limit):
    store.require(
        isinstance(value, str)
        and 1 <= len(value.strip()) <= limit
        and all(c.isprintable() or c == "\n" for c in value),
        "Comparison text required",
    )
    return value.strip()


def changes(before, after, path=""):
    if type(before) is type(after) and before == after:
        return []
    if isinstance(before, dict) and isinstance(after, dict):
        result = []
        for key in sorted(before.keys() | after.keys()):
            child = path + "/" + key.replace("~", "~0").replace("/", "~1")
            if key in before and key in after:
                result.extend(changes(before[key], after[key], child))
            else:
                result.append(
                    {
                        "path": child,
                        "before": before.get(key),
                        "after": after.get(key),
                        "change": "added" if key in after else "removed",
                    }
                )
        return result
    if isinstance(before, list) and isinstance(after, list) and len(before) == len(after):
        return [
            row
            for i, (a, b) in enumerate(zip(before, after, strict=True))
            for row in changes(a, b, path + "/" + str(i))
        ]
    return [{"path": path or "/", "before": before, "after": after, "change": "changed"}]


def definition(project, request):
    project.require_lease()
    store.require(
        isinstance(request, dict)
        and set(request) == {"schema", "name", "question", "baseline", "variants"}
        and request["schema"] == SCHEMA,
        "Explicit comparison definition required",
    )
    name, question = text(request["name"], 100), text(request["question"], 1000)
    members = request["variants"]
    store.require(
        isinstance(members, list) and 2 <= len(members) <= 16, "Freeze 2–16 comparison members"
    )
    infos, ids, labels, unique = [], set(), set(), set()
    for member in members:
        store.require(
            isinstance(member, dict) and set(member) == {"id", "label", "plan", "selector"},
            "Explicit member ID, label, plan and selector required",
        )
        identity = member["id"]
        store.require(
            isinstance(identity, str) and re.fullmatch(r"[a-z][a-z0-9_-]{0,31}", identity),
            "Invalid comparison member ID",
        )
        label = text(member["label"], 100)
        store.require(
            label == member["label"] and identity not in ids and label not in labels,
            "Unique comparison IDs and labels required",
        )
        info = tasks.selected(project, member)
        key = store.encoded({"plan": member["plan"], "selector": member["selector"]})
        store.require(key not in unique, "Duplicate plan/selector member")
        ids.add(identity)
        labels.add(label)
        unique.add(key)
        infos.append(info)
    store.require(
        isinstance(request["baseline"], str) and request["baseline"] in ids,
        "Choose a frozen baseline member",
    )
    base_index = next(i for i, m in enumerate(members) if m["id"] == request["baseline"])
    baseline = infos[base_index]
    for info in infos:
        store.require(
            info["task"] == baseline["task"]
            and info["binding"] == baseline["binding"]
            and info["reader"] == baseline["reader"],
            "Incompatible task, endpoint, source, protocol or reader",
        )
        store.require(
            info["support"] == baseline["support"],
            "Incompatible observations, allocation, visits, development evidence or units/support",
        )
    plan_ids = {member["plan"] for member in members}
    store.require(
        not any(a["plan"] in plan_ids for a in project.attempts.values()),
        "Comparison roster must precede execution; "
        "derive fresh plans for previously attempted inputs",
    )
    base_view = tasks.scientific_view(baseline, members[base_index]["selector"])
    diff = [
        {
            "member": member["id"],
            "fields": changes(base_view, tasks.scientific_view(info, member["selector"])),
        }
        for member, info in zip(members, infos, strict=True)
    ]
    result = {
        "schema": SCHEMA,
        "name": name,
        "question": question,
        "baseline": request["baseline"],
        "variants": members,
        "task": baseline["task"],
        "support": baseline["support"],
        "attempt_policy": "first-attempt-only/1",
        "reader": reader(),
        "changes": diff,
    }
    store.require(
        len(store.encoded(result)) <= 512 * 1024, "Comparison definition exceeds byte limit"
    )
    return result


def freeze(project, request):
    project.require_lease(write_access=True)
    value = definition(project, request)
    identity = project.append("comparison", {"definition": value})
    project.inspect()
    return {"comparison": identity, **value}


def validate(project, value):
    store.require(isinstance(value, dict), "Invalid frozen comparison")
    request = {key: value[key] for key in ("schema", "name", "question", "baseline", "variants")}
    store.require(
        store.encoded(value) == store.encoded(definition(project, request)),
        "Frozen comparison/source identity differs",
    )


def prefix(project, at):
    project.require_lease()
    if at is None:
        return project.events
    store.require(isinstance(at, str), "Explicit ledger tip required")
    for i, (identity, _, _) in enumerate(project.events):
        if identity == at:
            return project.events[: i + 1]
    raise ValueError("Unknown comparison ledger prefix")


def view(project, identity, *, at=None):
    project.require_lease()
    store.require(
        isinstance(identity, str) and identity in project.comparisons, "Unknown frozen comparison"
    )
    events = prefix(project, at)
    store.require(any(key == identity for key, _, _ in events), "Prefix predates the comparison")
    value = project.comparisons[identity]
    starts, finishes = {}, set()
    for key, event, _ in events:
        if event["kind"] == "start" and event["data"]["ordinal"] == 1:
            starts[event["data"]["plan"]] = key
        if event["kind"] == "finish":
            finishes.add(event["data"]["attempt"])
    attempts = {}
    for plan in dict.fromkeys(m["plan"] for m in value["variants"]):
        attempt = starts.get(plan)
        result = project.finishes[attempt][0]["result"] if attempt in finishes else None
        attempts[plan] = {
            "attempt": attempt,
            "status": "unattempted"
            if attempt is None
            else "unfinished"
            if result is None
            else result["execution_status"],
            "completeness": None if result is None else result["completeness"],
            "payload": None if result is None else result["payload"],
            "report_sha256": {} if result is None else result["report_sha256"],
        }
    return copy.deepcopy(
        {
            "comparison": identity,
            **value,
            "snapshot": {"sequence": len(events), "tip": events[-1][0]},
            "attempts": attempts,
            "changes_text": json.dumps(value["changes"], indent=2, sort_keys=True, allow_nan=False),
        }
    )


def reconstruct(project, identity, output, *, at=None, backend=None):
    from . import comparison_reports as reports
    from . import execution

    project.require_lease()
    store.require(not project.writable, "Comparison reconstruction requires a read-only lease")
    value = view(project, identity, at=at)
    output = store.safe_path(output, fresh=True)
    store.require(
        not output.exists() and not output.is_relative_to(project.path),
        "Fresh comparison output outside the project required",
    )
    with tempfile.TemporaryDirectory(prefix="opent1d-comparison-reader-") as tmp:
        directories = {}
        for index, (plan, attempt) in enumerate(value["attempts"].items()):
            directory = None
            if attempt["payload"] == "native":
                directory = Path(tmp).resolve() / str(index)
                result = execution.reconstruct(
                    project, attempt["attempt"], directory, allow_failed=True, backend=backend
                )
                store.require(
                    result["report_sha256"] == attempt["report_sha256"],
                    "Selected native report identity differs",
                )
            directories[plan] = directory
        report = reports.build(project, value, directories)
        output.mkdir()
        files = reports.render(report)
        for name, raw in files.items():
            (output / name).write_bytes(raw)
        store.seal(output)
    return {
        "comparison": identity,
        "snapshot": value["snapshot"],
        "reconstruction": "verified",
        "completeness": report["completeness"],
        "report_sha256": {name: store.digest(raw) for name, raw in files.items()},
    }
