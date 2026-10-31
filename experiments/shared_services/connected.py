"""Prospective connected studies over unchanged native task plans and runners."""

import copy
import tempfile
from pathlib import Path

from experiments.catalogue.storage import load_sealed, seal
from experiments.m3.researcher.intake import read_regular
from experiments.shared_contracts.inventory import reader_source_inventory

from . import comparisons, connected_bridge, execution, routes, store

HERE = Path(__file__).resolve().parent
SCHEMA = "opent1d.connected-study/1"
REPORT_SCHEMA = "opent1d.connected-study-report/1"


def protocol():
    value = store.read(HERE / "connected_protocol.json")
    store.require(value["schema"] == "opent1d.connected-study-protocol/1", "Study protocol differs")
    return value


def reader():
    return {
        "schema": REPORT_SCHEMA,
        **reader_source_inventory("experiments.shared_services.connected"),
        "protocol_sha256": store.digest((HERE / "connected_protocol.json").read_bytes()),
        "archived_code_execution": False,
    }


def definition(project, request):
    project.require_lease()
    store.require(
        isinstance(request, dict)
        and set(request) == {"name", "question", "forward_plan", "observation_case"},
        "Explicit connected study definition required",
    )
    p = protocol()
    plan = request["forward_plan"]
    store.require(isinstance(plan, str) and plan in project.plans, "Unknown forward plan")
    descriptor, folder = project.plans[plan]
    store.require(
        descriptor["task"] == p["forward_task"], "Selected native M4 forward plan required"
    )
    config = store.read(folder / "original/config.json")
    store.require(
        config["scenarios"] == [p["scenarios"][v] for v in ("before", "after")]
        and [s["id"] for s in config["sources"]] == p["sources"],
        "Both frozen sources and fasting/15-g scenarios required",
    )
    store.require(
        not any(a["plan"] == plan for a in project.attempts.values()),
        "Freeze the connected study before forward execution",
    )
    store.require(request["observation_case"] in p["observation_cases"], "Unknown observation case")
    return {
        "schema": SCHEMA,
        "name": comparisons.text(request["name"], 100),
        "question": comparisons.text(request["question"], 1000),
        "forward_plan": plan,
        "observation_case": request["observation_case"],
        "protocol": p,
        "forward_binding": descriptor["boundary"],
        "reader": reader(),
        "attempt_policy": "first-executed-attempt-only/1",
    }


def validate(project, value):
    store.require(isinstance(value, dict), "Invalid frozen study")
    request = {key: value[key] for key in ("name", "question", "forward_plan", "observation_case")}
    store.require(
        store.encoded(value) == store.encoded(definition(project, request)),
        "Study/source identity differs",
    )


def freeze(project, request):
    project.require_lease(write_access=True)
    value = definition(project, request)
    identity = project.append("study", {"definition": value})
    project.inspect()
    return {"study": identity, **copy.deepcopy(value)}


def first_attempt(project, plan, events):
    start = finish = None
    for identity, event, _ in events:
        data = event["data"]
        if event["kind"] == "start" and data["plan"] == plan and data["ordinal"] == 1:
            start = identity
        if event["kind"] == "finish" and data["attempt"] == start:
            finish = data
    result = None if finish is None else finish["result"]
    return {
        "plan": plan,
        "attempt": start,
        "status": "unattempted"
        if start is None
        else "unfinished"
        if result is None
        else result["execution_status"],
        "completeness": None if result is None else result["completeness"],
        "payload": None if result is None else result["payload"],
        "report_sha256": {} if result is None else result["report_sha256"],
    }


def view(project, identity, *, at=None):
    project.require_lease()
    store.require(
        isinstance(identity, str) and identity in project.studies, "Unknown connected study"
    )
    events = comparisons.prefix(project, at)
    store.require(any(key == identity for key, _, _ in events), "Prefix predates the study")
    value = project.studies[identity]
    intent = bridge = child = comparison = None
    for key, event, _ in events:
        data = event["data"]
        if event["kind"] == "study-intent" and data["study"] == identity:
            intent = key
        if intent and data.get("study_intent") == intent:
            if event["kind"] == "freeze":
                child = key
            elif event["kind"] == "comparison":
                comparison = key
        if event["kind"] == "study-bridge" and data["study"] == identity:
            bridge = key
    forward = first_attempt(project, value["forward_plan"], events)
    sampling = (
        first_attempt(project, child, events)
        if child
        else {
            "plan": None,
            "attempt": None,
            "status": "unmaterialized",
            "completeness": None,
            "payload": None,
            "report_sha256": {},
        }
    )
    if forward["status"] == "unattempted":
        next_step = {
            "action": "run",
            "plan": value["forward_plan"],
            "reason": "Run fixed forward plan",
        }
    elif forward["status"] == "unfinished":
        next_step = {
            "action": "blocked",
            "reason": "Recover the unfinished forward attempt explicitly",
        }
    elif forward["completeness"] != "complete":
        next_step = {
            "action": "blocked",
            "reason": "Fixed first forward attempt incomplete; descendants remain unavailable",
        }
    elif bridge is None:
        next_step = {
            "action": "materialize",
            "reason": "Verify forward evidence and resume exact observation/plan publication",
        }
    elif sampling["status"] == "unattempted":
        next_step = {
            "action": "run",
            "plan": child,
            "reason": "Run full inverse and both reduced schedules",
        }
    elif sampling["status"] == "unfinished":
        next_step = {
            "action": "blocked",
            "reason": "Recover the unfinished inverse/sampling attempt explicitly",
        }
    else:
        next_step = {
            "action": "finished",
            "reason": "Verify the connected report; failures remain selected",
        }
    return copy.deepcopy(
        {
            "study": identity,
            **value,
            "snapshot": {"sequence": len(events), "tip": events[-1][0]},
            "intent": intent,
            "bridge": bridge,
            "sampling_plan": child,
            "comparison": comparison,
            "stages": {"forward": forward, "inverse_sampling": sampling},
            "next": next_step,
            "planned": {
                "forward_source_scenarios": 4,
                "synthetic_cases": 2,
                "visits": 4,
                "schedules": 3,
                "variants": 4,
                "native_variant_pairs": 24,
                "truth_endpoint_rows": 72,
                "comparison_members": 6,
            },
        }
    )


def intent_record(project, intent):
    project.require_lease()
    for value in project.study_intents.values():
        if value[0] == intent:
            return value
    raise ValueError("Unknown materialization intent")


def validate_intent(project, data, folder):
    store.require(
        set(data) == {"study", "forward_attempt", "source_report_sha256", "artifacts_sha256"}
        and data["study"] in project.studies
        and data["study"] not in project.study_intents,
        "Invalid or duplicate study materialization intent",
    )
    selected = view(project, data["study"])["stages"]["forward"]
    store.require(
        selected["attempt"] == data["forward_attempt"]
        and selected["completeness"] == "complete"
        and selected["payload"] == "native"
        and selected["report_sha256"] == data["source_report_sha256"],
        "Intent requires the fixed complete forward attempt",
    )
    archive = project.finishes[selected["attempt"]][1] / "native"
    expected = connected_bridge.generated(project.studies[data["study"]], archive)
    bridge = folder / "bridge"
    load_sealed(bridge)
    from .sampling import hashes

    store.require(hashes(bridge) == data["artifacts_sha256"], "Bridge artifact roster/hash differs")
    store.require(
        set(data["artifacts_sha256"])
        == set(expected) | {"development/manifest.json", "manifest.json"},
        "Unexpected bridge artifact family",
    )
    for name, raw in expected.items():
        store.require(
            read_regular(bridge / name, 16 * 1024 * 1024, "bridge bytes") == raw,
            "Bridge conversion bytes differ",
        )
    from experiments.mmtt_sampling.intake import development_inventory

    development_inventory(bridge / "development", store.read(bridge / "design.json"))


def validate_child(project, intent, descriptor, folder):
    _, data, _ = intent_record(project, intent)
    store.require(intent not in project.study_children, "Materialization already owns a child plan")
    store.require(descriptor["task"] == "mmtt-sampling", "Connected child must use native sampling")
    from .sampling import hashes

    expected = {
        name: digest
        for name, digest in data["artifacts_sha256"].items()
        if name in {"package.json", "observations.csv", "settings.json", "design.json"}
        or name.startswith("development/")
    }
    store.require(
        hashes(folder / "original") == expected, "Child inputs differ from immutable intent"
    )


def comparison_definition(project, intent):
    _, data, _ = intent_record(project, intent)
    value = project.studies[data["study"]]
    plan = project.study_children[intent]
    return {
        "schema": comparisons.SCHEMA,
        "name": value["name"],
        "question": value["question"],
        "baseline": "member-1",
        "variants": [
            {
                "id": f"member-{i + 1}",
                "label": item["schedule"] + " / " + item["variant"],
                "plan": plan,
                "selector": item,
            }
            for i, item in enumerate(value["protocol"]["comparison_selectors"])
        ],
    }


def validate_comparison(project, intent, definition):
    store.require(
        intent not in project.study_comparisons, "Materialization already owns a comparison"
    )
    expected = comparison_definition(project, intent)
    store.require(
        {key: definition[key] for key in expected} == expected,
        "Comparison differs from prospectively selected study roster",
    )


def validate_bridge(project, data):
    store.require(
        set(data) == {"study", "intent", "sampling_plan", "comparison"}
        and all(isinstance(value, str) for value in data.values())
        and data["study"] in project.study_intents
        and data["study"] not in project.study_bridges,
        "Invalid or duplicate final study bridge",
    )
    store.require(
        data["intent"] == project.study_intents[data["study"]][0]
        and data["intent"] in project.study_children
        and data["intent"] in project.study_comparisons
        and project.study_children.get(data["intent"]) == data["sampling_plan"]
        and project.study_comparisons.get(data["intent"]) == data["comparison"],
        "Materialized child/comparison binding differs",
    )


def materialize(project, identity, *, backend=None, application=None):
    project.require_lease(write_access=True)
    value = view(project, identity)
    if value["bridge"]:
        return {
            "study": identity,
            "bridge": value["bridge"],
            "sampling_plan": value["sampling_plan"],
            "comparison": value["comparison"],
            "reused": True,
        }
    store.require(value["next"]["action"] == "materialize", value["next"]["reason"])
    forward = value["stages"]["forward"]
    with tempfile.TemporaryDirectory(prefix="connected-materialize-") as temporary:
        root = Path(temporary).resolve()
        execution.reconstruct(project, forward["attempt"], root / "verified", backend=backend)
        if not value["intent"]:
            archive = project.finishes[forward["attempt"]][1] / "native"
            generated = connected_bridge.generated(value, archive)
            prepared = root / "bridge"
            prepared.mkdir()
            for name, raw in generated.items():
                target = prepared / name
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(raw)
            seal(prepared / "development")
            seal(prepared)
            from .sampling import hashes

            project.append(
                "study-intent",
                {
                    "study": identity,
                    "forward_attempt": forward["attempt"],
                    "source_report_sha256": forward["report_sha256"],
                    "artifacts_sha256": hashes(prepared),
                },
                lambda folder: store.snapshot(prepared, folder / "bridge"),
            )
            project.inspect()
        intent, _, folder = project.study_intents[identity]
        inputs = folder / "bridge"
        if intent not in project.study_children:
            routes.freeze(
                project,
                "mmtt-sampling",
                {
                    name: inputs / name
                    for name in (
                        "package.json",
                        "observations.csv",
                        "settings.json",
                        "design.json",
                        "development",
                    )
                },
                application=application,
                study_intent=intent,
            )
        if intent not in project.study_comparisons:
            comparisons.freeze(project, comparison_definition(project, intent), study_intent=intent)
        data = {
            "study": identity,
            "intent": intent,
            "sampling_plan": project.study_children[intent],
            "comparison": project.study_comparisons[intent],
        }
        validate_bridge(project, data)
        bridge = project.append("study-bridge", data)
        project.inspect()
    return {"bridge": bridge, **data, "reused": False}


def reconstruct(project, identity, output, *, at=None, backend=None):
    from . import connected_reports

    project.require_lease()
    store.require(not project.writable, "Connected reconstruction requires a read-only lease")
    value = view(project, identity, at=at)
    output = store.safe_path(output, fresh=True)
    store.require(
        not output.exists() and not output.is_relative_to(project.path),
        "Fresh study output outside project required",
    )
    with tempfile.TemporaryDirectory(prefix="connected-reader-") as temporary:
        root = Path(temporary).resolve()
        for name, stage in value["stages"].items():
            if stage["payload"] == "native":
                verified = execution.reconstruct(
                    project, stage["attempt"], root / name, allow_failed=True, backend=backend
                )
                store.require(
                    verified["report_sha256"] == stage["report_sha256"],
                    "Native study report identity differs",
                )
        bridge = None
        if value["intent"]:
            _, _, folder = intent_record(project, value["intent"])
            bridge = store.read(folder / "bridge/bridge.json")
        native = root / "inverse_sampling"
        report = connected_reports.build(
            project, value, bridge, native if native.exists() else None
        )
        files = connected_reports.render(report)
        output.mkdir()
        for name, raw in files.items():
            (output / name).write_bytes(raw)
        seal(output)
    return {
        "study": identity,
        "snapshot": value["snapshot"],
        "reconstruction": "verified",
        "completeness": report["completeness"],
        "report_sha256": {name: store.digest(raw) for name, raw in files.items()},
    }
