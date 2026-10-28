"""Paired synthetic sensitivity using only the observations supplied to this call.

Task 2 must mask before calling this boundary. No full-curve state, inferred
kinetics or participant-specific smoothing value can be supplied to it.
"""

import hashlib
import math
import random

from .estimator import estimate, trapezoid
from .observations import parse_csv

SCHEMA = "opent1d.observation-analysis/1"
WORK_LIMIT = 500_000


def quantile(values, probability):
    ordered = sorted(values)
    if not ordered:
        raise ValueError("No values for interval")
    position = (len(ordered) - 1) * probability
    lower, upper = math.floor(position), math.ceil(position)
    return ordered[lower] + (position - lower) * (ordered[upper] - ordered[lower])


def direction(interval):
    if interval is None:
        return "unresolved"
    return "increase" if interval[0] > 0 else "decrease" if interval[1] < 0 else "unresolved"


def classify(variants, *, context_complete=True):
    if not context_complete or any(item["status"] != "complete" for item in variants):
        return "insufficiently determined"
    labels = {item["direction"] for item in variants}
    if labels == {"unresolved"}:
        return "insufficiently determined"
    if len(labels) == 1:
        return "consistent within investigated assumptions"
    return "assumption-dependent"


def reference(visit):
    rows = visit["rows"]
    times = [row["time_min"] for row in rows]
    cp = [None if row["cpeptide_nmol_l"] is None else 1000 * row["cpeptide_nmol_l"] for row in rows]
    glucose = [row["glucose_mmol_l"] for row in rows]
    complete = visit["valid"] and not visit["errors"]
    cp_auc = trapezoid(times, cp) if complete and all(x is not None for x in cp) else None
    glucose_auc = (
        trapezoid(times, glucose) if complete and all(x is not None for x in glucose) else None
    )
    return {
        "times_min": times,
        "cpeptide_pmol_l": cp,
        "glucose_mmol_l": glucose,
        "cpeptide_status": [row["cpeptide_status"] for row in rows],
        "glucose_status": [row["glucose_status"] for row in rows],
        "cpeptide_auc_pmol_min_l": cp_auc,
        "mean_cpeptide_pmol_l": None if cp_auc is None else cp_auc / 120,
        "fasting_glucose_mmol_l": glucose[0] if complete and glucose else None,
        "glucose_auc_mmol_min_l": glucose_auc,
        "metadata": visit["metadata"],
        "import_errors": visit["errors"],
    }


def visit_attempt(visit, variant, concentrations=None, *, compact=False):
    ref = reference(visit)
    if not visit["valid"]:
        return {"status": "failed", "reason": "invalid_visit", "estimate": None}
    if any(value is None for value in ref["cpeptide_pmol_l"]):
        return {"status": "failed", "reason": "missing_or_censored_cpeptide", "estimate": None}
    cp = ref["cpeptide_pmol_l"] if concentrations is None else concentrations
    loq = visit["metadata"]["assay"]["cpeptide_loq_nmol_l"] * 1000
    if any(x is None or not math.isfinite(x) or x < loq for x in cp):
        return {
            "status": "failed",
            "reason": "perturbed_cpeptide_below_loq_or_nonfinite",
            "estimate": None,
        }
    try:
        result = estimate(ref["times_min"], cp, variant)
    except (ValueError, OverflowError, ZeroDivisionError):
        return {"status": "failed", "reason": "numerical_failure", "estimate": None}
    if compact:
        result = {
            key: result[key]
            for key in ("total_pmol", "minimum_rate_pmol_min", "boundary_failures", "status")
        }
    reason = (
        "negative_inferred_secretion"
        if result["status"] != "completed"
        else "missing_glucose_context"
        if any(x is None for x in ref["glucose_mmol_l"])
        else None
    )
    return {
        "status": "completed" if reason is None else "failed",
        "reason": reason,
        "estimate": result,
    }


def gaussian(seed, *key):
    # Keyed solely by frozen IDs, draw, visit and retained time. Removing another
    # time cannot expose its observation or change this sample's random stream.
    material = repr((seed, *key)).encode("utf-8")
    return random.Random(int.from_bytes(hashlib.sha256(material).digest(), "big")).gauss(0, 1)


def perturbations(person, visits, settings):
    uncertainty = settings["uncertainty"]
    references = {visit["visit_id"]: reference(visit) for visit in visits}
    if any(not visit["valid"] for visit in visits) or any(
        value is None for ref in references.values() for value in ref["cpeptide_pmol_l"]
    ):
        return []
    output = []
    seed = uncertainty["seed"]
    for index in range(uncertainty["draws"]):
        shared = uncertainty["paired_offset_sd_pmol_l"] * gaussian(seed, person, index, "shared")
        values = {}
        for visit_id in settings["visit_order"]:
            ref = references[visit_id]
            values[visit_id] = [
                cp
                + shared
                + uncertainty["independent_sd_pmol_l"] * gaussian(seed, person, index, visit_id, t)
                for t, cp in zip(ref["times_min"], ref["cpeptide_pmol_l"], strict=True)
            ]
        bad = not math.isfinite(shared) or any(
            not math.isfinite(x) for row in values.values() for x in row
        )
        output.append(
            {
                "index": index,
                "shared_offset_pmol_l": shared if math.isfinite(shared) else None,
                "visits": {
                    key: [x if math.isfinite(x) else None for x in row]
                    for key, row in values.items()
                },
                "generation_errors": ["nonfinite_perturbation"] if bad else [],
            }
        )
    return output


def pair_attempt(visits, variant, order, perturbation=None, *, compact=False):
    results = {
        visit["visit_id"]: visit_attempt(
            visit,
            variant,
            None if perturbation is None else perturbation[visit["visit_id"]],
            compact=compact,
        )
        for visit in visits
    }
    estimates = [results[visit_id]["estimate"] for visit_id in order]
    difference = (
        estimates[1]["total_pmol"] - estimates[0]["total_pmol"]
        if all(item is not None for item in estimates)
        else None
    )
    return {
        "status": "completed"
        if all(item["status"] == "completed" for item in results.values())
        else "failed",
        "change_pmol": difference,
        "visits": results,
    }


def summarize_variant(record, planned):
    point, draws = record["point"], record["draws"]
    accepted = [draw for draw in draws if draw["status"] == "completed"]
    complete = point["status"] == "completed" and len(accepted) == planned
    interval = (
        [quantile([draw["change_pmol"] for draw in accepted], p) for p in (0.025, 0.975)]
        if complete
        else None
    )
    visit_intervals = {
        visit: (
            [
                quantile([draw["visits"][visit]["estimate"]["total_pmol"] for draw in accepted], p)
                for p in (0.025, 0.975)
            ]
            if complete
            else None
        )
        for visit in point["visits"]
    }
    return {
        "status": "complete" if complete else "incomplete",
        "point": point,
        "paired_change_pmol": point["change_pmol"],
        "conditional_interval_pmol": interval,
        "visit_intervals_pmol": visit_intervals,
        "interval_scope": "nominal 95% synthetic perturbation interval; no human coverage claim",
        "direction": direction(interval),
        "planned_draws": planned,
        "attempted_draws": len(draws),
        "completed_draws": len(accepted),
        "failed_draws": len(draws) - len(accepted),
        "not_attempted_draws": planned - len(draws),
        "not_attempted_reason": record["not_attempted_reason"],
        "draws": draws,
    }


def evaluate(settings, package, csv_raw):
    """Entire preprocessing-to-estimation boundary, usable after independent masking."""
    from .plan import validate_settings

    validate_settings(settings, package)
    imported = parse_csv(csv_raw, package)
    if "required_times_min" in settings:
        for visit in imported["visits"]:
            actual = {row["time_min"] for row in visit["rows"]}
            missing = [time for time in settings["required_times_min"] if time not in actual]
            if missing:
                visit["errors"].append(
                    {
                        "row": None,
                        "reason": "Required sample times unavailable",
                        "times_min": missing,
                    }
                )
                visit["valid"] = False
        imported["valid"] = not imported["errors"] and all(
            visit["valid"] for visit in imported["visits"]
        )
    variants, order = settings["variants"], settings["visit_order"]
    work = sum(max(0, len(visit["rows"]) - 1) for visit in imported["visits"])
    work *= len(variants) * (settings["uncertainty"]["draws"] + 1)
    work_refused = work > WORK_LIMIT
    people = {}
    for person in package["participants"]:
        visits = [visit for visit in imported["visits"] if visit["participant_id"] == person["id"]]
        draws = [] if work_refused else perturbations(person["id"], visits, settings)
        variant_records = {}
        for variant in variants:
            if work_refused:
                point = {
                    "status": "not_attempted",
                    "change_pmol": None,
                    "visits": {
                        visit["visit_id"]: {
                            "status": "not_attempted",
                            "reason": "work_limit",
                            "estimate": None,
                        }
                        for visit in visits
                    },
                }
            else:
                point = pair_attempt(visits, variant, order)
            variant_records[variant["id"]] = {
                "point": point,
                "draws": [
                    {
                        "index": draw["index"],
                        **pair_attempt(visits, variant, order, draw["visits"], compact=True),
                    }
                    for draw in draws
                ],
                "not_attempted_reason": (
                    "work_limit"
                    if work_refused
                    else "invalid_or_censored_observations"
                    if not draws
                    else None
                ),
            }
        people[person["id"]] = {
            "allocation": person["allocation"],
            "context": person["context"],
            "references": {visit["visit_id"]: reference(visit) for visit in visits},
            "perturbations": draws,
            "variants": variant_records,
        }
    return {
        "schema": SCHEMA,
        "import_errors": imported["errors"],
        "import_valid": imported["valid"],
        "work_limit_refused": work_refused,
        "planned_interval_evaluations": work,
        "people": people,
    }


def report_from_attempts(plan, attempts):
    settings = plan["settings"]
    output = {
        "schema": SCHEMA,
        "task": "mmtt-sensitivity",
        "kind": "synthetic",
        "human_evaluation": False,
        "plan": plan,
        "import_errors": attempts["import_errors"],
        "work_limit_refused": attempts["work_limit_refused"],
        "people": {},
    }
    for person, record in attempts["people"].items():
        variants = {
            key: summarize_variant(value, settings["uncertainty"]["draws"])
            for key, value in record["variants"].items()
        }
        complete = not attempts["import_errors"] and all(
            value["status"] == "complete" for value in variants.values()
        )
        output["people"][person] = {
            "allocation": record["allocation"],
            "context": record["context"],
            "references": record["references"],
            "status": "complete" if complete else "incomplete",
            "classification": classify(list(variants.values()), context_complete=complete),
            "variants": variants,
        }
    people = output["people"]
    output["coverage"] = {
        "planned_people": len(people),
        "planned_visits": 2 * len(people),
        "planned_variant_pairs": len(people) * len(settings["variants"]),
        "completed_variant_pairs": sum(
            value["status"] == "complete"
            for record in people.values()
            for value in record["variants"].values()
        ),
        "complete_people": sum(record["status"] == "complete" for record in people.values()),
        "complete_cohort": all(record["status"] == "complete" for record in people.values()),
    }
    return output
