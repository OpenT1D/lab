"""Display admission for the registered sampling report; native reader owns verification."""

from experiments.mmtt_sampling.report import SCHEMA, coverage_counts

from .library_observations import require
from .library_observations import validate_report as validate_native

TASK = "mmtt-sampling"
ARTIFACTS = ("report.json", "report.md")


def validate_report(report):
    require(
        isinstance(report, dict)
        and report.get("schema") == SCHEMA
        and report.get("task") == TASK
        and report.get("kind") == "synthetic"
        and report.get("human_evaluation") is False
        and report.get("execution_status") in ("completed", "failed", "interrupted")
    )
    plan = report["plan"]
    require(plan["schema"] == "opent1d.mmtt-sampling-plan/1")
    require(plan["human_execution_authorized"] is False)
    design = plan["design"]
    schedules = {"full": design["full_times_minutes"], **design["subsets"]}
    require(set(report["schedules"]) == set(schedules))
    for record in report["schedules"].values():
        if record.get("report") is not None:
            validate_native(record["report"])
    people = [{"id": ident} for ident in design["allocation"]]
    require(
        report["coverage"]
        == coverage_counts(
            schedules,
            people,
            [v["id"] for v in plan["settings"]["variants"]],
            plan["settings"],
            report["schedules"],
            report["execution_status"],
        )
    )
    for key in ("visit_comparisons", "paired_comparisons", "assay_and_glucose_context"):
        require(isinstance(report.get(key), list))
    require(set(report["comparisons"]) == {"development", "evaluation"})
    return report
