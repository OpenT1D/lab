"""Presentation checks for the one registered synthetic observation report."""

import math

from experiments.observation_analysis.analysis import SCHEMA, classify, direction

TASK = "mmtt-sensitivity"
ARTIFACTS = ("report.json", "report.md")


def require(value, message="Malformed synthetic observation report"):
    if not value:
        raise ValueError(message)


def numeric(value, *, nullable=False):
    require(value is None and nullable or type(value) in (int, float) and math.isfinite(value))


def interval(value):
    if value is not None:
        require(isinstance(value, list) and len(value) == 2)
        for item in value:
            numeric(item)
        require(value[0] <= value[1])


def validate_report(report):
    """Validate display shape; fixed native reconstruction owns numeric verification."""
    require(
        isinstance(report, dict)
        and report.get("schema") == SCHEMA
        and report.get("task") == TASK
        and report.get("kind") == "synthetic"
        and report.get("human_evaluation") is False
        and report.get("execution_status") in ("completed", "failed", "interrupted")
    )
    coverage = report.get("coverage")
    people = report.get("people")
    require(
        isinstance(coverage, dict)
        and type(coverage.get("complete_cohort")) is bool
        and isinstance(people, dict)
        and isinstance(report.get("import_errors"), list)
    )
    if report["execution_status"] != "completed":
        require(
            not people
            and coverage["complete_cohort"] is False
            and coverage.get("complete_people") == 0
            and coverage.get("completed_variant_pairs") == 0
        )
        count = coverage.get("planned_people")
        if count is not None:
            require(
                type(count) is int
                and 0 < count <= 256
                and len(report.get("unavailable_participants", [])) == count
            )
        return report
    plan = report.get("plan")
    require(
        isinstance(plan, dict)
        and plan.get("schema") == "opent1d.observation-analysis-plan/1"
        and plan.get("human_execution_authorized") is False
    )
    settings = plan["settings"]
    order = settings["visit_order"]
    variants = [value["id"] for value in settings["variants"]]
    planned = settings["uncertainty"]["draws"]
    require(
        len(order) == 2
        and len(set(order)) == 2
        and 2 <= len(variants) <= 8
        and len(set(variants)) == len(variants)
        and type(planned) is int
        and planned >= 32
    )
    require(
        1 <= len(people) <= 256
        and coverage.get("planned_people") == len(people)
        and coverage.get("planned_visits") == 2 * len(people)
        and coverage.get("planned_variant_pairs") == len(people) * len(variants)
    )
    for key in (
        "planned_people",
        "planned_visits",
        "planned_variant_pairs",
        "complete_people",
        "completed_variant_pairs",
    ):
        require(type(coverage.get(key)) is int)
    completed_people = completed_pairs = 0
    for person in people.values():
        require(
            isinstance(person, dict)
            and person.get("allocation") in ("development", "evaluation")
            and isinstance(person.get("context"), dict)
            and set(person.get("references", {})) == set(order)
            and set(person.get("variants", {})) == set(variants)
        )
        for reference in person["references"].values():
            times = reference.get("times_min")
            require(
                isinstance(times, list)
                and isinstance(reference.get("metadata"), dict)
                and isinstance(reference.get("import_errors"), list)
            )
            for key in ("cpeptide_pmol_l", "glucose_mmol_l", "cpeptide_status", "glucose_status"):
                require(isinstance(reference.get(key), list) and len(reference[key]) == len(times))
            for value in times:
                numeric(value)
            for key in ("cpeptide_pmol_l", "glucose_mmol_l"):
                for value in reference[key]:
                    numeric(value, nullable=True)
            for key in (
                "cpeptide_auc_pmol_min_l",
                "mean_cpeptide_pmol_l",
                "fasting_glucose_mmol_l",
                "glucose_auc_mmol_min_l",
            ):
                numeric(reference.get(key), nullable=True)
        for variant in person["variants"].values():
            require(
                variant.get("status") in ("complete", "incomplete")
                and variant.get("planned_draws") == planned
            )
            for key in (
                "attempted_draws",
                "completed_draws",
                "failed_draws",
                "not_attempted_draws",
            ):
                require(type(variant.get(key)) is int and 0 <= variant[key] <= planned)
            require(
                variant["completed_draws"] + variant["failed_draws"] == variant["attempted_draws"]
                and variant["attempted_draws"] + variant["not_attempted_draws"] == planned
                and isinstance(variant.get("draws"), list)
                and len(variant["draws"]) == variant["attempted_draws"]
                and [draw["index"] for draw in variant["draws"]]
                == list(range(variant["attempted_draws"]))
            )
            require(
                variant["completed_draws"]
                == sum(draw["status"] == "completed" for draw in variant["draws"])
            )
            numeric(variant.get("paired_change_pmol"), nullable=True)
            interval(variant.get("conditional_interval_pmol"))
            require(
                variant.get("direction") == direction(variant["conditional_interval_pmol"])
                and set(variant.get("visit_intervals_pmol", {})) == set(order)
            )
            for value in variant["visit_intervals_pmol"].values():
                interval(value)
            point = variant.get("point")
            require(isinstance(point, dict))
            for attempt in [point, *variant["draws"]]:
                require(
                    attempt.get("status") in ("completed", "failed", "not_attempted")
                    and set(attempt.get("visits", {})) == set(order)
                )
                numeric(attempt.get("change_pmol"), nullable=True)
                for visit in attempt["visits"].values():
                    require(visit.get("status") in ("completed", "failed", "not_attempted"))
                    estimate = visit.get("estimate")
                    if estimate is not None:
                        require(isinstance(estimate, dict))
                        numeric(estimate.get("total_pmol"))
                        numeric(estimate.get("minimum_rate_pmol_min"))
            complete = point["status"] == "completed" and variant["completed_draws"] == planned
            require(
                (variant["status"] == "complete") == complete
                and (variant["conditional_interval_pmol"] is not None) == complete
            )
            completed_pairs += complete
        complete = not report["import_errors"] and all(
            value["status"] == "complete" for value in person["variants"].values()
        )
        require(
            person.get("status") == ("complete" if complete else "incomplete")
            and person.get("classification")
            == classify(list(person["variants"].values()), context_complete=complete)
        )
        completed_people += complete
    require(
        coverage.get("complete_people") == completed_people
        and coverage.get("completed_variant_pairs") == completed_pairs
        and coverage["complete_cohort"] == (completed_people == len(people))
    )
    return report
