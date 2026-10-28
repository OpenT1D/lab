"""Failure-aware comparisons of native shared reports; no estimator here."""

from experiments.observation_analysis.report import safe

from .comparison import direction_comparison, endpoint_comparison

SCHEMA = "opent1d.mmtt-sampling/1"


class NativeReportLink(str):
    """Only generated relative links with validated schedule IDs bypass text escaping."""


def native_person(record, person):
    return (record.get("report") or {}).get("people", {}).get(person)


def point_value(person, variant, visit=None):
    if person is None:
        return None
    value = person["variants"][variant]
    point = value["point"]
    if visit is None:
        return value["paired_change_pmol"] if point["status"] == "completed" else None
    attempt = point["visits"][visit]
    return attempt["estimate"]["total_pmol"] if attempt["status"] == "completed" else None


def conditional_direction(person, variant):
    if person is None or person["variants"][variant]["status"] != "complete":
        return None
    return person["variants"][variant]["direction"]


def coverage_counts(schedules, people, variants, settings, records, status):
    pairs_per_schedule = len(people) * len(variants)
    draws_per_pair = settings["uncertainty"]["draws"]
    result = {
        "planned_schedules": len(schedules),
        "planned_people": len(people),
        "planned_visits_per_schedule": 2 * len(people),
        "planned_variant_pairs": len(schedules) * pairs_per_schedule,
        "planned_visit_points": 2 * len(schedules) * pairs_per_schedule,
        "planned_draw_pairs": len(schedules) * pairs_per_schedule * draws_per_pair,
        "completed_variant_pairs": 0,
        "unavailable_variant_pairs": 0,
        "attempted_draw_pairs": 0,
        "completed_draw_pairs": 0,
        "failed_draw_pairs": 0,
        "not_attempted_draw_pairs": 0,
        "unavailable_draw_pairs": 0,
    }
    for kind in ("pair_points", "visit_points"):
        for state in ("completed", "failed", "not_attempted", "unavailable"):
            result[state + "_" + kind] = 0
    for schedule in schedules:
        record = records.get(schedule, {})
        native = record.get("report") or {}
        known_unattempted = record.get("status") in ("not_attempted", "mask_failed", "plan_failed")
        for person in people:
            data = native.get("people", {}).get(person["id"])
            for variant in variants:
                value = None if data is None else data["variants"].get(variant)
                if value is None:
                    state = "not_attempted" if known_unattempted else "unavailable"
                    result[state + "_pair_points"] += 1
                    result[state + "_visit_points"] += 2
                    result[state + "_draw_pairs"] += draws_per_pair
                    result["unavailable_variant_pairs"] += state == "unavailable"
                    continue
                result["completed_variant_pairs"] += value["status"] == "complete"
                result["attempted_draw_pairs"] += value["attempted_draws"]
                result["completed_draw_pairs"] += value["completed_draws"]
                result["failed_draw_pairs"] += value["failed_draws"]
                result["not_attempted_draw_pairs"] += value["not_attempted_draws"]
                result[value["point"]["status"] + "_pair_points"] += 1
                for point in value["point"]["visits"].values():
                    result[point["status"] + "_visit_points"] += 1
    result["complete_cohort"] = (
        status == "completed"
        and len(records) == len(schedules)
        and all(
            (record.get("report") or {}).get("coverage", {}).get("complete_cohort") is True
            for record in records.values()
        )
    )
    return result


def build(plan, package, records, execution_status):
    design, settings = plan["design"], plan["settings"]
    schedules = {"full": design["full_times_minutes"], **design["subsets"]}
    variants = [value["id"] for value in settings["variants"]]
    people = package["participants"] if package else []
    coverage = coverage_counts(schedules, people, variants, settings, records, execution_status)
    comparisons, case_rows, paired_rows, context = {}, [], [], []
    full = records.get("full", {})
    for allocation in ("development", "evaluation"):
        selected = [person for person in people if person["allocation"] == allocation]
        comparisons[allocation] = {}
        for schedule in design["subsets"]:
            reduced = records.get(schedule, {})
            by_variant = {}
            for variant in variants:
                totals, changes, directions = [], [], []
                for person in selected:
                    identity = person["id"]
                    a, b = native_person(full, identity), native_person(reduced, identity)
                    # Package-level import errors invalidate comparative acceptance.
                    if (full.get("report") or {}).get("import_errors"):
                        a = None
                    if (reduced.get("report") or {}).get("import_errors"):
                        b = None
                    for visit in settings["visit_order"]:
                        pair = (point_value(a, variant, visit), point_value(b, variant, visit))
                        totals.append(pair)
                        case_rows.append(
                            {
                                "participant_id": identity,
                                "allocation": allocation,
                                "schedule": schedule,
                                "variant": variant,
                                "visit": visit,
                                "reference_pmol": pair[0],
                                "reduced_pmol": pair[1],
                                "difference_pmol": None if None in pair else pair[1] - pair[0],
                                "absolute_difference_pmol": None
                                if None in pair
                                else abs(pair[1] - pair[0]),
                                "reference_attempt": None
                                if a is None
                                else a["variants"][variant]["point"]["visits"][visit],
                                "reduced_attempt": None
                                if b is None
                                else b["variants"][variant]["point"]["visits"][visit],
                            }
                        )
                    changes.append((point_value(a, variant), point_value(b, variant)))
                    paired_rows.append(
                        {
                            "participant_id": identity,
                            "allocation": allocation,
                            "schedule": schedule,
                            "variant": variant,
                            "reference_change_pmol": point_value(a, variant),
                            "reduced_change_pmol": point_value(b, variant),
                            "reference_interval_pmol": None
                            if a is None
                            else a["variants"][variant]["conditional_interval_pmol"],
                            "reduced_interval_pmol": None
                            if b is None
                            else b["variants"][variant]["conditional_interval_pmol"],
                            "reference_direction": conditional_direction(a, variant),
                            "reduced_direction": conditional_direction(b, variant),
                            "reference_classification": None if a is None else a["classification"],
                            "reduced_classification": None if b is None else b["classification"],
                        }
                    )
                    directions.append(
                        (conditional_direction(a, variant), conditional_direction(b, variant))
                    )
                by_variant[variant] = {
                    "visit_totals": endpoint_comparison(totals),
                    "paired_changes": endpoint_comparison(changes),
                    "directions": direction_comparison(directions),
                    "participant_order": [person["id"] for person in selected],
                    "visit_order": settings["visit_order"],
                    "reference_classifications": {
                        person["id"]: (native_person(full, person["id"]) or {}).get(
                            "classification"
                        )
                        for person in selected
                    },
                    "reduced_classifications": {
                        person["id"]: (native_person(reduced, person["id"]) or {}).get(
                            "classification"
                        )
                        for person in selected
                    },
                }
            comparisons[allocation][schedule] = by_variant
    for schedule, record in records.items():
        for person in people:
            native = native_person(record, person["id"])
            for visit in settings["visit_order"]:
                ref = None if native is None else native["references"][visit]
                observed = (
                    [] if ref is None else [x for x in ref["cpeptide_pmol_l"] if x is not None]
                )
                declared_visit = next(value for value in person["visits"] if value["id"] == visit)
                context.append(
                    {
                        "schedule": schedule,
                        "participant_id": person["id"],
                        "allocation": person["allocation"],
                        "visit": visit,
                        "minimum_observed_cpeptide_pmol_l": min(observed) if observed else None,
                        "assay_loq_pmol_l": 1000 * declared_visit["assay"]["cpeptide_loq_nmol_l"],
                        "censored_samples": None
                        if ref is None
                        else ref["cpeptide_status"].count("below_loq"),
                        "reference": ref,
                        "declared_metadata": declared_visit,
                    }
                )
    return {
        "schema": SCHEMA,
        "task": "mmtt-sampling",
        "kind": "synthetic",
        "human_evaluation": False,
        "input_provenance": package["provenance"],
        "execution_status": execution_status,
        "endpoint": "whole-body total secretion including basal over 0–120 minutes",
        "unit": "pmol",
        "paired_change": "followup minus baseline",
        "reference_scope": "full-curve analysis is a reference, not biological truth",
        "empirical_assessment": "not performed; no empirical margins or precision design frozen",
        "prospective_blood_draw_protocol_approved": False,
        "plan": plan,
        "coverage": coverage,
        "schedules": records,
        "comparisons": comparisons,
        "visit_comparisons": case_rows,
        "paired_comparisons": paired_rows,
        "assay_and_glucose_context": context,
    }


def cell(value):
    if isinstance(value, NativeReportLink):
        return str(value)
    if value is None:
        return "unavailable"
    if isinstance(value, float):
        return format(value, ".10g")
    return safe(value)


def table(lines, headers):
    lines.append(row(*headers))
    lines.append(row(*(["---"] * len(headers))))


def row(*values):
    return "| " + " | ".join(cell(value) for value in values) + " |"


def render(report):
    lines = [
        "# Synthetic MMTT sampling information loss",
        "",
        "Whole-body total endogenous secretion including basal over **0–120 minutes**, "
        "in **pmol**.",
        "Paired change is follow-up minus baseline. Full curves are reference analyses, "
        "not biological truth.",
        "",
        "**Empirical acceptance is not assessed.** No clinical margin or prospective "
        "blood-draw protocol is approved.",
        "Synthetic engineering cases do not establish human uncertainty, treatment effects "
        "or product value.",
        "Synthetic allocation exercises software; it is not a blinded empirical evaluation.",
        "",
        cell(report["input_provenance"]),
        "",
        "## Coverage",
        "",
    ]
    c = report["coverage"]
    if (report.get("execution") or {}).get("error"):
        lines += ["", "Execution issue: " + cell(report["execution"]["error"]), ""]
    lines += [
        f"Execution: {cell(report['execution_status'])}. All requested computations complete: "
        f"{c['complete_cohort']}.",
        f"Planned schedules: {c['planned_schedules']}; people: {c['planned_people']}; "
        f"required variant pairs: {c['planned_variant_pairs']}; "
        f"complete variant pairs: {c['completed_variant_pairs']}.",
        f"Perturbation pairs: {c['planned_draw_pairs']} planned, "
        f"{c['attempted_draw_pairs']} attempted, {c['failed_draw_pairs']} failed, "
        f"{c['not_attempted_draw_pairs']} not attempted, "
        f"{c['unavailable_draw_pairs']} with unavailable atomic status.",
        "",
        "## Schedules and shared native reports",
        "",
    ]
    table(
        lines,
        [
            "Schedule",
            "Required minutes",
            "Omitted times per complete source visit",
            "State",
            "Complete variant pairs",
            "Native report",
        ],
    )
    full_count = len(report["plan"]["design"]["full_times_minutes"])
    for schedule, record in report["schedules"].items():
        native = record.get("report")
        count = None if native is None else native["coverage"]["completed_variant_pairs"]
        link = (
            NativeReportLink(f"[all attempts, intervals and context](studies/{schedule}/report.md)")
            if native
            else "unavailable"
        )
        lines.append(
            row(
                schedule,
                record["times_min"],
                full_count - len(record["times_min"]),
                record["status"],
                count,
                link,
            )
        )
        if record.get("error"):
            lines += ["", f"{cell(schedule)}: {cell(record['error'])}"]
    lines += [
        "",
        "## Frozen engineering assumptions",
        "",
        "Every schedule uses the same shared method settings; only required times differ. "
        "Initialization and every perturbation are recalculated from retained "
        "observations.",
        "",
    ]
    table(
        lines,
        [
            "Variant",
            "Volume (L)",
            "Initial peripheral factor",
            "k1 / k2 / k3 (min^-1)",
            "Engineering rationale",
        ],
    )
    for variant in report["plan"]["settings"]["variants"]:
        rates = " / ".join(cell(variant[key]) for key in ("k1_per_min", "k2_per_min", "k3_per_min"))
        lines.append(
            row(
                variant["id"],
                variant["volume_l"],
                variant["initial_peripheral_factor"],
                rates,
                variant["rationale"],
            )
        )
    noise = report["plan"]["settings"]["uncertainty"]
    lines += [
        "",
        f"{noise['draws']} frozen draws; independent measurement SD "
        f"{cell(noise['independent_sd_pmol_l'])} pmol/L; shared paired offset SD "
        f"{cell(noise['paired_offset_sd_pmol_l'])} pmol/L; seed {noise['seed']}. "
        "These are invented error scales, not measured assay precision or human ranges.",
        "",
    ]
    for allocation, schedules in report["comparisons"].items():
        lines += [
            "",
            f"## {allocation.capitalize()} comparisons",
            "",
            "Differences are reduced minus full-reference. Precision is the sample SD "
            "of differences, not a confidence interval for mean bias. Visits from the "
            "same person are not independent subjects.",
            "",
        ]
        table(
            lines,
            [
                "Schedule / variant",
                "Quantity",
                "Compared / planned",
                "Bias (pmol)",
                "Mean absolute difference (pmol)",
                "Precision SD (pmol)",
                "RMS difference (pmol)",
            ],
        )
        for schedule, variants in schedules.items():
            for variant, value in variants.items():
                for name in ("visit_totals", "paired_changes"):
                    m = value[name]
                    lines.append(
                        row(
                            schedule + " / " + variant,
                            name.replace("_", " "),
                            f"{m['compared_count']} / {m['planned_count']}",
                            m["bias_pmol"],
                            m["mean_absolute_difference_pmol"],
                            m["precision_sample_sd_pmol"],
                            m["root_mean_square_difference_pmol"],
                        )
                    )
        lines += [
            "",
            "### Paired conclusions",
            "",
            "Both unresolved is indeterminate. Failed required uncertainty is "
            "unavailable. The shared core supplies all intervals and "
            "across-assumption classifications.",
            "",
        ]
        table(
            lines,
            [
                "Schedule / variant",
                "Same resolved direction",
                "Direction reversal",
                "Indeterminate",
                "Unavailable",
                "Planned people",
            ],
        )
        for schedule, variants in schedules.items():
            for variant, value in variants.items():
                d = value["directions"]
                lines.append(
                    row(
                        schedule + " / " + variant,
                        d["same_resolved_direction"],
                        d["direction_reversal"],
                        d["indeterminate"],
                        d["unavailable"],
                        d["planned_count"],
                    )
                )
    lines += [
        "",
        "## Every planned paired comparison",
        "",
        "Intervals are nominal 95% conditional synthetic perturbation intervals "
        "in pmol; they have no claimed human coverage.",
        "",
    ]
    table(
        lines,
        [
            "Person / allocation",
            "Schedule / variant",
            "Full change (pmol)",
            "Full interval (pmol)",
            "Reduced change (pmol)",
            "Reduced interval (pmol)",
            "Full / reduced direction",
            "Full / reduced classification",
        ],
    )
    for value in report["paired_comparisons"]:
        lines.append(
            row(
                value["participant_id"] + " / " + value["allocation"],
                value["schedule"] + " / " + value["variant"],
                value["reference_change_pmol"],
                value["reference_interval_pmol"],
                value["reduced_change_pmol"],
                value["reduced_interval_pmol"],
                cell(value["reference_direction"]) + " / " + cell(value["reduced_direction"]),
                cell(value["reference_classification"])
                + " / "
                + cell(value["reduced_classification"]),
            )
        )
    lines += [
        "",
        "## Every planned visit comparison",
        "",
        "Unavailable estimates stay in planned denominators. Raw failed estimates, "
        "boundary diagnostics, every perturbation and conditional visit intervals "
        "remain in the shared native child reports and JSON.",
        "",
    ]
    table(
        lines,
        [
            "Person / allocation",
            "Schedule / variant",
            "Visit",
            "Full (pmol)",
            "Reduced (pmol)",
            "Signed difference (pmol)",
            "Absolute difference (pmol)",
            "Reference / reduced status",
        ],
    )
    for value in report["visit_comparisons"]:
        states = []
        for attempt in (value["reference_attempt"], value["reduced_attempt"]):
            states.append(
                "unavailable"
                if attempt is None
                else attempt["status"]
                + (": " + str(attempt["reason"]) if attempt["reason"] else "")
            )
        lines.append(
            row(
                value["participant_id"] + " / " + value["allocation"],
                value["schedule"] + " / " + value["variant"],
                value["visit"],
                value["reference_pmol"],
                value["reduced_pmol"],
                value["difference_pmol"],
                value["absolute_difference_pmol"],
                " / ".join(states),
            )
        )
    lines += [
        "",
        "## Low values, assay and glucose context",
        "",
        "Every visit is shown without an automatic low-value exclusion or clinical "
        "cutoff. AUC is a separate measured reference, not secretion. Glucose exposure "
        "and medication/test context do not establish treatment effects.",
        "",
    ]
    table(
        lines,
        [
            "Schedule / person / visit",
            "Minimum observed C-peptide (pmol/L)",
            "Assay LOQ (pmol/L)",
            "Censored",
            "C-peptide AUC (pmol min/L)",
            "Glucose AUC (mmol min/L)",
            "Fasting glucose (mmol/L)",
        ],
    )
    for value in report["assay_and_glucose_context"]:
        ref = value["reference"] or {}
        lines.append(
            row(
                value["schedule"] + " / " + value["participant_id"] + " / " + value["visit"],
                value["minimum_observed_cpeptide_pmol_l"],
                value["assay_loq_pmol_l"],
                value["censored_samples"],
                ref.get("cpeptide_auc_pmol_min_l"),
                ref.get("glucose_auc_mmol_min_l"),
                ref.get("fasting_glucose_mmol_l"),
            )
        )
    lines += [
        "",
        "Complete measured traces, renal/demographic/assay/meal/medication context, "
        "initialization and failed-draw diagnostics are retained in each native report "
        "and the comparison JSON.",
        "No reduced schedule meeting eventual empirical criteria is a valid research "
        "outcome; retrospective agreement does not approve a prospective sampling protocol.",
        "",
    ]
    return "\n".join(lines).encode("utf-8")
