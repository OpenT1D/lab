"""Passive fixture bindings for the two selected routes, not runtime adapters."""

from pathlib import Path

from experiments.m1.artifacts import strict_json
from experiments.m4.secure_study import common as m4
from experiments.observation_analysis import plan as mmtt
from experiments.observation_analysis.observations import validate_package
from experiments.setup.core import requirements, selectors

from .core import digest, require

FIXTURES = Path(__file__).resolve().parent / "fixtures"
ROOT = FIXTURES.parents[2]


def hashes(names):
    return {name: digest((ROOT / name).read_bytes()) for name in sorted(names)}


def reader(task):
    require(task in {"m4-study-secure", "mmtt-sensitivity"}, "Unselected task")
    sources = hashes(m4.source_paths()) if task == "m4-study-secure" else mmtt.source_identity()
    return {
        "module": "experiments.m4.secure_study"
        if task == "m4-study-secure"
        else "experiments.observation_analysis",
        "report_schema": m4.REPORT_SCHEMA
        if task == "m4-study-secure"
        else "opent1d.observation-analysis/1",
        "trusted_sources_sha256": sources,
        "archived_code_execution": False,
    }


def boundary(task, payload):
    require(task in {"m4-study-secure", "mmtt-sensitivity"}, "Unselected task")
    binding = {
        "implementation_sha256": reader(task)["trusted_sources_sha256"],
        "runtime_files_sha256": {project: selectors(project) for project in requirements(task)},
    }
    if task == "m4-study-secure":
        require(set(payload) == {"config.json"}, "M4 config payload required")
        config = m4.validate_config(strict_json(payload["config.json"]))
        # This increment freezes these two existing fixtures. General source
        # intake stays with the task; no new plugin/source resolver is offered.
        expected = strict_json((FIXTURES / "m4-fasting.json").read_bytes())["sources"]
        require(config["sources"] == expected, "Unselected M4 fixture sources")
        sources = {}
        for item in config["sources"]:
            declaration_raw = (FIXTURES / item["declaration"]).read_bytes()
            declaration = m4.causal.declaration(strict_json(declaration_raw))
            source_hash = digest((FIXTURES / item["model"]).read_bytes())
            require(source_hash == declaration["source_sha256"], "M4 source changed")
            sources[item["id"]] = {
                "source_sha256": source_hash,
                "declaration_sha256": digest(declaration_raw),
            }
        binding.update(
            protocol_sha256=m4.PROTOCOL_SHA256,
            method=m4.protocol()["id"],
            source_sha256=sources,
        )
        return {
            "family": "causal-continuous-source/1-provisional",
            "binding": binding,
            "planned_slots": [
                f"{source['id']}/{scenario}"
                for source in config["sources"]
                for scenario in config["scenarios"]
            ],
        }
    require(
        set(payload) == {"package.json", "observations.csv", "settings.json"},
        "MMTT input payload required",
    )
    package = validate_package(strict_json(payload["package.json"]))
    settings = mmtt.validate_settings(strict_json(payload["settings.json"]), package)
    binding.update(
        protocol_sha256=digest(mmtt.PROTOCOL.read_bytes()),
        method=mmtt.VERSION,
        ancestry_sha256=hashes(mmtt.ANCESTRY),
    )
    return {
        "family": "offline-paired-observation-analysis/1-provisional",
        "binding": binding,
        "planned_slots": [
            f"{person['id']}/{variant['id']}"
            for person in package["participants"]
            for variant in settings["variants"]
        ],
    }


def outcome(task, report, execution, payload, binding):
    """Keep process completion distinct from the task's scientific completeness."""
    if task == "mmtt-sensitivity":
        require(
            report.get("schema") == "opent1d.observation-analysis/1"
            and report.get("task") == task
            and report.get("kind") == "synthetic"
            and report.get("human_evaluation") is False
            and execution.get("schema") == "opent1d.observation-analysis-execution/1"
            and execution.get("implementation_sha256") == binding["implementation_sha256"],
            "Unsupported native report/execution",
        )
        require(
            report.get("execution_status") == execution.get("status"),
            "Native report/execution status differs",
        )
        native_plan = report.get("plan")
        runtime = execution.get("runtime")
        require(
            isinstance(runtime, dict)
            and set(runtime) == {"python", "implementation", "platform", "numerical_dependencies"}
            and all(isinstance(value, str) and value.strip() for value in runtime.values())
            and runtime["numerical_dependencies"] == "Python standard library",
            "Native runtime record missing or invalid",
        )
        require(
            isinstance(native_plan, dict)
            and native_plan.get("schema") == mmtt.SCHEMA
            and native_plan.get("task") == task
            and native_plan.get("kind") == "synthetic"
            and native_plan.get("human_execution_authorized") is False
            and native_plan.get("method") == binding["method"]
            and native_plan.get("settings") == strict_json(payload["settings.json"])
            and native_plan.get("runtime") == execution.get("runtime")
            and native_plan.get("input_sha256")
            == {name: digest(raw) for name, raw in payload.items()}
            and native_plan.get("implementation_sha256") == binding["implementation_sha256"]
            and native_plan.get("ancestry_sha256") == binding["ancestry_sha256"]
            and native_plan.get("protocol_sha256") == binding["protocol_sha256"],
            "Native result plan differs",
        )
        package = strict_json(payload["package.json"])
        count = len(package["participants"])
        coverage = report["coverage"]
        require(
            coverage.get("planned_people") == count
            and coverage.get("planned_visits") == 2 * count
            and coverage.get("planned_variant_pairs")
            == count * len(native_plan["settings"]["variants"])
            and type(coverage.get("complete_cohort")) is bool,
            "Native result denominator differs",
        )
        slots = {}
        people = report.get("people")
        require(isinstance(people, dict), "Native result roster differs")
        expected_people = {person["id"] for person in package["participants"]}
        require(
            set(people) == (expected_people if execution["status"] == "completed" else set()),
            "Native result roster differs",
        )
        for person in package["participants"]:
            variants = people.get(person["id"], {}).get("variants", {})
            if execution["status"] == "completed":
                require(
                    set(variants) == {v["id"] for v in native_plan["settings"]["variants"]},
                    "Native result variants differ",
                )
            for variant in native_plan["settings"]["variants"]:
                status = variants.get(variant["id"], {}).get("status")
                require(status in {None, "complete", "incomplete"}, "Native variant state")
                slots[f"{person['id']}/{variant['id']}"] = (
                    "unavailable"
                    if status is None
                    else "complete"
                    if status == "complete"
                    else "failed"
                )
        require(
            coverage.get("completed_variant_pairs") == list(slots.values()).count("complete"),
            "Native completed denominator differs",
        )
        return execution["status"], coverage["complete_cohort"], slots
    require(task == "m4-study-secure", "Unselected task")
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
