"""Trusted internal successor registration; historical ten-route packet stays frozen."""

from pathlib import Path

from experiments.m1.artifacts import strict_json
from experiments.m4.installed_study import common as m4
from experiments.setup.core import selectors
from experiments.workflows.registry import Task

from .store import digest, require

ROOT = Path(__file__).resolve().parents[2]
FIXTURES = ROOT / "experiments/m4/installed_study/fixtures"
TASK_ID = "m4-study-installed"
TASK = Task(
    TASK_ID,
    "M4 initial-load study with reviewed dependency overlays",
    "config",
    "docs/installed-m4.md",
    "experiments.m4.installed_study",
    "experiments.m4.installed_study",
)


def reader():
    return {
        "module": "experiments.m4.installed_study",
        "report_schema": m4.REPORT_SCHEMA,
        "trusted_sources_sha256": {
            name: digest((ROOT / name).read_bytes()) for name in m4.source_paths()
        },
        "archived_code_execution": False,
    }


def boundary(payload):
    require(set(payload) == {"config.json"}, "M4 config payload required")
    config = m4.validate_config(strict_json(payload["config.json"]))
    expected = strict_json((FIXTURES / "m4-fasting.json").read_bytes())["sources"]
    require(config["sources"] == expected, "Unselected installed M4 sources")
    sources = {}
    for item in config["sources"]:
        raw = (FIXTURES / item["declaration"]).read_bytes()
        declaration = m4.causal.declaration(strict_json(raw))
        source = digest((FIXTURES / item["model"]).read_bytes())
        require(source == declaration["source_sha256"], "Installed M4 source changed")
        sources[item["id"]] = {"source_sha256": source, "declaration_sha256": digest(raw)}
    projects = (
        m4.NATIVE_PROJECT,
        m4.OBSERVER_PROJECT,
        "experiments/m4/installed_study/build_inputs",
    )
    return {
        "family": "causal-continuous-source/1-provisional",
        "binding": {
            "implementation_sha256": reader()["trusted_sources_sha256"],
            "runtime_files_sha256": {project: selectors(project) for project in projects},
            "protocol_sha256": m4.PROTOCOL_SHA256,
            "method": m4.protocol()["id"],
            "source_sha256": sources,
        },
        "planned_slots": [
            f"{source['id']}/{scenario}"
            for source in config["sources"]
            for scenario in config["scenarios"]
        ],
    }


def outcome(task, report, execution, payload, binding):
    require(task == TASK_ID, "Unselected task")
    require(
        report.get("schema") == m4.REPORT_SCHEMA and execution.get("schema") == m4.VERSION,
        "Unsupported native report/execution",
    )
    require(
        report.get("configuration") == strict_json(payload["config.json"]),
        "Native result plan differs",
    )
    require(report.get("protocol") == binding["method"], "Native result method differs")
    require(type(report.get("passed")) is bool, "Native result completeness differs")
    require(
        report.get("status") == execution.get("status"), "Native report/execution status differs"
    )
    provenance = report.get("provenance")
    require(
        isinstance(provenance, dict)
        and provenance.get("sources") == binding["implementation_sha256"],
        "Native result implementation differs",
    )
    require(
        report.get("execution") == m4.protocol()["execution"],
        "Native execution contract differs",
    )
    config = report["configuration"]
    require(
        set(report["sources"]) == set(execution["sources"]) == {s["id"] for s in config["sources"]},
        "Native result roster differs",
    )
    slots = {}
    for source in config["sources"]:
        name = source["id"]
        saved = report["sources"][name]
        require(
            saved["source_sha256"] == binding["source_sha256"][name]["source_sha256"]
            and saved["declaration_sha256"] == binding["source_sha256"][name]["declaration_sha256"]
            and saved["status"] == execution["sources"][name]["status"]
            and set(saved["scenarios"]) == set(config["scenarios"]),
            "Native source result differs",
        )
        require(
            type(saved.get("accepted")) is bool
            and saved["accepted"] == (saved["status"] == "completed"),
            "Native source acceptance/status differs",
        )
        for scenario in config["scenarios"]:
            cell = saved["scenarios"][scenario]
            require(
                type(cell.get("accepted")) is bool
                and cell["accepted"] == saved["accepted"]
                and (not cell["accepted"] or cell["status"] == "completed"),
                "Native scenario acceptance/status differs",
            )
            slots[f"{name}/{scenario}"] = (
                "complete"
                if cell["accepted"] is True and saved["accepted"] is True
                else "failed"
                if cell["status"] == "failed"
                else "unavailable"
            )
    denominator = report["denominators"]
    require(
        denominator.get("sources") == len(config["sources"])
        and denominator.get("source_scenarios") == len(slots)
        and denominator.get("accepted_source_scenarios") == list(slots.values()).count("complete"),
        "Native result denominator differs",
    )
    require(
        report["passed"]
        == (
            execution["status"] == "completed"
            and report["reference"]["accepted"] is True
            and report["common_controls"]["passed"] is True
            and all(value["accepted"] for value in report["sources"].values())
        ),
        "Native result acceptance/status differs",
    )
    return execution["status"], report["passed"], slots
