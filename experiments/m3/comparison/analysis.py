"""All-candidate common support and participant-weighted saved-prediction arithmetic."""

from itertools import combinations

from experiments.m3.researcher.metrics import (
    MIN_PAIRED_SPAN_US,
    MIN_PAIRED_WINDOWS,
    _bootstrap,
    _mean,
    _rmse,
    summarize_case,
)

from .common import METHOD, finite, require


def method_metrics(rows, method):
    errors = [
        finite(row["predictions"][method] - row["target"], "common forecast error") for row in rows
    ]
    return {
        "mae": _mean([abs(error) for error in errors]),
        "rmse": _rmse(errors),
        "bias": _mean(errors),
    }


def summarize_common(people, candidate_order, cases):
    """Cases contain validated child status/trace data, never supplied algorithms."""
    require(len(candidate_order) >= 2, "At least two candidates required")
    require(len(set(candidate_order)) == len(candidate_order), "Repeated candidate identity")
    require(METHOD not in candidate_order, "Reserved persistence identity")
    require(set(cases) == set(candidate_order), "Missing frozen candidate")
    roster = {person["id"]: person for person in people}
    require(len(roster) == len(people) and bool(roster), "Invalid planned roster")
    methods = [*candidate_order, METHOD]
    contrasts = [(candidate, METHOD) for candidate in candidate_order]
    contrasts += list(combinations(candidate_order, 2))
    summaries = {}
    person_metrics, person_differences = {}, {}
    for pid in sorted(roster):
        person = roster[pid]
        planned = person["origins_us"]
        rows_by_candidate, status, counts = {}, {}, {}
        for candidate in candidate_order:
            require(set(cases[candidate]) == set(roster), "Candidate participant roster differs")
            case = cases[candidate][pid]
            require(
                isinstance(case, dict) and set(case) == {"status", "rows"},
                "Invalid validated comparison case",
            )
            original = summarize_case(
                planned,
                case["rows"],
                execution_status=case["status"],
                bounds_us=person["bounds_us"],
            )
            status[candidate] = case["status"]
            counts[candidate] = original["scored"]
            rows_by_candidate[candidate] = {row["origin_us"]: row for row in case["rows"]}
        # Host fields must agree wherever saved trace prefixes overlap, including excluded rows.
        for left, right in combinations(candidate_order, 2):
            for origin in set(rows_by_candidate[left]) & set(rows_by_candidate[right]):
                lhs, rhs = rows_by_candidate[left][origin], rows_by_candidate[right][origin]
                require(
                    all(
                        lhs[field] == rhs[field]
                        for field in ("features", "reason", "persistence", "target")
                    ),
                    "Common host history, target or persistence differs",
                )
        common_rows = []
        for origin in planned:
            if not all(origin in rows_by_candidate[candidate] for candidate in candidate_order):
                continue
            shared = rows_by_candidate[candidate_order[0]][origin]
            if shared["features"] is None or shared["target"]["status"] != "measured":
                continue
            common_rows.append(
                {
                    "origin": origin,
                    "target": shared["target"]["value"],
                    "predictions": {
                        METHOD: shared["persistence"],
                        **{
                            candidate: rows_by_candidate[candidate][origin]["candidate"]
                            for candidate in candidate_order
                        },
                    },
                }
            )
        span = common_rows[-1]["origin"] - common_rows[0]["origin"] if common_rows else None
        reasons = [
            "incomplete_candidate:" + candidate
            for candidate in candidate_order
            if status[candidate] != "completed"
        ]
        if len(common_rows) < MIN_PAIRED_WINDOWS:
            reasons.append("insufficient_common_windows")
        if span is None or span < MIN_PAIRED_SPAN_US:
            reasons.append("insufficient_common_span")
        metrics = {method: method_metrics(common_rows, method) for method in methods}
        differences = {
            (left, right): _mean(
                [
                    finite(
                        abs(row["predictions"][left] - row["target"])
                        - abs(row["predictions"][right] - row["target"]),
                        "common paired absolute-error difference",
                    )
                    for row in common_rows
                ]
            )
            for left, right in contrasts
        }
        summaries[pid] = {
            "planned_origins": len(planned),
            "candidate_statuses": status,
            "candidate_scored": counts,
            "common_scored": len(common_rows),
            "common_origins_us": [row["origin"] for row in common_rows],
            "common_span_us": span,
            "common_support_losses": {
                candidate: counts[candidate] - len(common_rows) for candidate in candidate_order
            },
            "eligible_for_primary": not reasons,
            "ineligibility_reasons": reasons,
            "diagnostic_error_metrics": metrics,
        }
        if not reasons:
            person_metrics[pid] = metrics
            person_differences[pid] = differences
    included = sorted(person_metrics)
    return {
        "support": "all frozen candidates and persistence; pairwise support deferred",
        "planned_people": len(roster),
        "contributing_people": len(included),
        "complete_cohort": len(included) == len(roster),
        "people": summaries,
        "equal_person_metrics": {
            method: {
                metric: _mean([person_metrics[pid][method][metric] for pid in included])
                for metric in ("mae", "rmse", "bias")
            }
            for method in methods
        },
        "contrasts": [
            {
                "left": left,
                "right": right,
                "person_differences": {
                    pid: person_differences[pid][left, right] for pid in included
                },
                "mean_person_mae_difference": _mean(
                    [person_differences[pid][left, right] for pid in included]
                ),
                "participant_bootstrap_95": _bootstrap(
                    [person_differences[pid][left, right] for pid in included]
                ),
            }
            for left, right in contrasts
        ],
        "null_reason": "no eligible people on all-candidate support" if not included else None,
    }
