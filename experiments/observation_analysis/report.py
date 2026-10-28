"""Readable paired results, separate measured references and all failures."""

import html
import json

from experiments.catalogue.storage import text


def safe(value):
    if isinstance(value, (dict, list)):
        value = json.dumps(value, sort_keys=True, ensure_ascii=False)
    return text(html.escape(str(value))).replace("[", r"\[").replace("]", r"\]")


def formatted(value):
    return "unavailable" if value is None else f"{value:.8g}"


def render(report):
    coverage = report["coverage"]
    lines = [
        "# Synthetic paired secretion assumption analysis",
        "",
        "Endpoint: whole-body total endogenous secretion, including basal, over measured "
        "0–120 minutes (pmol). Change is follow-up minus baseline. No normalization.",
        "",
        "All inputs and error/kinetic assumptions are invented engineering controls. "
        "Human validity, uncertainty coverage, treatment effects and usability are untested.",
        "",
        f"Execution: **{safe(report.get('execution_status', 'completed'))}**. "
        f"Complete analyses: **{coverage['complete_people']}/"
        f"{coverage['planned_people']}** people. "
        f"Required variant pairs: **{coverage['completed_variant_pairs']}/"
        f"{coverage['planned_variant_pairs']}** complete.",
        "",
        "A complete calculation can still be insufficiently determined. An unresolved "
        "interval does not establish absence of change. Variants are shown separately.",
        "",
    ]
    if report.get("fatal_error"):
        lines.extend(["## Execution failure", "", safe(report["fatal_error"]), ""])
        if report.get("unavailable_participants"):
            lines.extend(
                ["| Declared participant | Allocation | Attempt status |", "| --- | --- | --- |"]
            )
            for person in report["unavailable_participants"]:
                lines.append(
                    f"| {safe(person['id'])} | {safe(person['allocation'])} | "
                    f"{safe(person['status'])} |"
                )
            lines.append("")
    if report["import_errors"]:
        lines.extend(["## Package import failures", "", "| CSV record | Reason |", "| --- | --- |"])
        for problem in report["import_errors"]:
            lines.append(f"| {safe(problem['row'])} | {safe(problem['reason'])} |")
        lines.append("")
    order = report["plan"]["settings"]["visit_order"] if report.get("plan") else []
    variant_order = (
        [value["id"] for value in report["plan"]["settings"]["variants"]] if order else []
    )
    if order:
        settings = report["plan"]["settings"]
        noise = settings["uncertainty"]
        lines.extend(
            [
                "## Frozen engineering assumptions",
                "",
                "| Variant | Volume (L) | Initial peripheral factor | "
                "k1 / k2 / k3 (min⁻¹) | Rationale |",
                "| --- | --- | --- | --- | --- |",
            ]
        )
        for variant in settings["variants"]:
            rates = " / ".join(
                formatted(variant[key]) for key in ("k1_per_min", "k2_per_min", "k3_per_min")
            )
            lines.append(
                f"| {safe(variant['id'])} | {formatted(variant['volume_l'])} | "
                f"{formatted(variant['initial_peripheral_factor'])} | {rates} | "
                f"{safe(variant['rationale'])} |"
            )
        lines.extend(
            [
                "",
                f"{noise['draws']} frozen perturbations; independent measurement SD "
                f"{formatted(noise['independent_sd_pmol_l'])} pmol/L and shared paired offset SD "
                f"{formatted(noise['paired_offset_sd_pmol_l'])} pmol/L. "
                "These scales and stress variants are invented engineering controls.",
                "",
            ]
        )
    labels = {
        "age_years": "Age (years)",
        "height_cm": "Height (cm)",
        "weight_kg": "Weight (kg)",
        "sex": "Declared sex",
        "population": "Population context",
        "renal_context": "Renal context",
        "id": "Visit",
        "challenge_id": "Challenge identity",
        "protocol": "Test protocol",
        "meal": "Meal challenge",
        "medication_context": "Medication and insulin context",
        "assay": "Assay / declared LOD and LOQ (nmol/L)",
    }
    for person, detail in sorted(report["people"].items()):
        lines.extend(
            [
                f"## {safe(person)}",
                "",
                f"**{safe(detail['classification'])}**. "
                f"Analysis {safe(detail['status'])}; allocation {safe(detail['allocation'])}.",
                "",
                "| Context | Declared value |",
                "| --- | --- |",
            ]
        )
        lines.extend(
            f"| {safe(labels[key])} | {safe(value)} |"
            for key, value in sorted(detail["context"].items())
        )
        lines.extend(
            [
                "",
                "| Variant | Baseline total (pmol) | Follow-up total (pmol) | "
                "Change (pmol) | Conditional interval (pmol) | Direction | Analysis |",
                "| --- | --- | --- | --- | --- | --- | --- |",
            ]
        )
        for variant in variant_order:
            result = detail["variants"][variant]
            point = result["point"]
            totals = [point["visits"][visit]["estimate"] for visit in order]
            values = [None if value is None else value["total_pmol"] for value in totals]
            interval = result["conditional_interval_pmol"]
            label = "unavailable" if interval is None else " to ".join(map(formatted, interval))
            lines.append(
                f"| {safe(variant)} | {formatted(values[0])} | {formatted(values[1])} | "
                f"{formatted(result['paired_change_pmol'])} | {label} | "
                f"{safe(result['direction'])} | {safe(result['status'])} |"
            )
        lines.extend(
            [
                "",
                "Intervals are nominal central 95% synthetic perturbation intervals, "
                "conditional on each frozen variant. They have no established human coverage. "
                "Do not pool variants into a probability distribution.",
                "",
                "| Variant | Visit | Total-secretion interval (pmol) | "
                "Minimum inferred rate (pmol/min) |",
                "| --- | --- | --- | --- |",
            ]
        )
        for variant in variant_order:
            result = detail["variants"][variant]
            for visit in order:
                interval = result["visit_intervals_pmol"][visit]
                label = "unavailable" if interval is None else " to ".join(map(formatted, interval))
                estimate = result["point"]["visits"][visit]["estimate"]
                minimum = None if estimate is None else estimate["minimum_rate_pmol_min"]
                lines.append(
                    f"| {safe(variant)} | {safe(visit)} | {label} | {formatted(minimum)} |"
                )
        lines.extend(
            [
                "",
                "### Observations and test context",
                "",
                "A different glucose stimulus can accompany a secretion difference. "
                "C-peptide AUC is a separate concentration reference, not secreted amount.",
                "",
            ]
        )
        for visit in order:
            ref = detail["references"][visit]
            lines.extend(
                [
                    f"#### {safe(visit)}",
                    "",
                    f"C-peptide AUC: "
                    f"**{formatted(ref['cpeptide_auc_pmol_min_l'])} pmol·min/L**; "
                    f"mean C-peptide: {formatted(ref['mean_cpeptide_pmol_l'])} pmol/L. "
                    f"Fasting glucose: {formatted(ref['fasting_glucose_mmol_l'])} mmol/L; "
                    f"glucose AUC: {formatted(ref['glucose_auc_mmol_min_l'])} mmol·min/L.",
                    "",
                    "| Test field | Declaration |",
                    "| --- | --- |",
                ]
            )
            lines.extend(
                f"| {safe(labels[key])} | {safe(value)} |"
                for key, value in sorted(ref["metadata"].items())
            )
            lines.extend(
                [
                    "",
                    "| Time (min) | C-peptide (pmol/L) | Status | Glucose (mmol/L) | Status |",
                    "| --- | --- | --- | --- | --- |",
                ]
            )
            for index, time in enumerate(ref["times_min"]):
                lines.append(
                    f"| {formatted(time)} | {formatted(ref['cpeptide_pmol_l'][index])} | "
                    f"{safe(ref['cpeptide_status'][index])} | "
                    f"{formatted(ref['glucose_mmol_l'][index])} | "
                    f"{safe(ref['glucose_status'][index])} |"
                )
            for error in ref["import_errors"]:
                lines.extend(["", f"Import record {safe(error['row'])}: {safe(error['reason'])}."])
            lines.append("")
        lines.extend(
            [
                "### Attempts and failures",
                "",
                "| Variant | Planned draws | Attempted | Completed | Failed | Not attempted |",
                "| --- | --- | --- | --- | --- | --- |",
            ]
        )
        for variant in variant_order:
            result = detail["variants"][variant]
            lines.append(
                f"| {safe(variant)} | {result['planned_draws']} | {result['attempted_draws']} | "
                f"{result['completed_draws']} | {result['failed_draws']} | "
                f"{result['not_attempted_draws']} |"
            )
        lines.extend(
            [
                "",
                "| Variant | Attempt | Visit | Failure or unavailable status |",
                "| --- | --- | --- | --- |",
            ]
        )
        failures = 0
        for variant in variant_order:
            result = detail["variants"][variant]
            for label, attempt in [
                ("point", result["point"]),
                *[(str(draw["index"]), draw) for draw in result["draws"]],
            ]:
                for visit in order:
                    record = attempt["visits"][visit]
                    if record["status"] != "completed":
                        failures += 1
                        lines.append(
                            f"| {safe(variant)} | {label} | {safe(visit)} | "
                            f"{safe(record['reason'])} |"
                        )
            if result["not_attempted_draws"]:
                failures += 1
                lines.append(
                    f"| {safe(variant)} | {result['not_attempted_draws']} draws | both | "
                    f"{safe(result['not_attempted_reason'])} |"
                )
        if not failures:
            lines.append("| all | all required | both | none |")
        lines.append("")
    lines.extend(
        [
            "## Saved evidence",
            "",
            "`report.json` retains full-precision outcomes, every uncertainty attempt and "
            "point interval inventories. `attempts.json` also retains the shared perturbed "
            "observations. `frozen/` retains original bytes, protocol, settings and opaque "
            "source snapshots. These snapshots are never executed by the reader.",
            "",
            "The source model is Polonsky et al. (1986), DOI 10.1172/JCI112308, with "
            "BC-003 numerical ancestry and the OT-053 narrow boundary. No upstream R "
            "package or code copy is used. See the bound plan for identities.",
            "",
        ]
    )
    return "\n".join(lines).encode("utf-8")
