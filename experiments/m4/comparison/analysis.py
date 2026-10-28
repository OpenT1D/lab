"""Frozen descriptive arithmetic on validated, complete saved M4 trajectories."""

import math
from itertools import combinations

SCENARIOS = ("fasting", "gastric_load_30g")
MODES = ("candidate", "host_constant_basal", "bc008_reference")
SIGNALS = {
    "glucose_mg_dl": "mg/dL",
    "insulin_pmol_l": "pmol/L",
    "cpeptide_pmol_l": "pmol/L",
}
TIMES = [i / 4 for i in range(961)]


def require(condition, message):
    if not condition:
        raise ValueError(message)


def finite(value):
    require(
        not isinstance(value, bool) and isinstance(value, (int, float)) and math.isfinite(value),
        "Trajectory and contrast values must be finite numbers",
    )
    return value


def validate_trajectories(report):
    """Never shorten or silently adapt an accepted complete native workflow."""
    expected = {f"{scenario}--{mode}" for scenario in SCENARIOS for mode in MODES}
    require(
        report.get("status") == "completed"
        and report.get("passed") is True
        and type(report.get("accepted_observation_cases")) is int
        and report["accepted_observation_cases"] == 6,
        "Whole native workflow must be accepted",
    )
    require(
        set(report.get("trajectories", {})) == expected,
        "Accepted workflow has missing or unexpected scenario/mode trajectories",
    )
    require(
        set(report.get("case_accounting", {})) == {"primary", "repeat"}
        and all(
            set(report["case_accounting"][label]) == expected
            and all(status == "completed" for status in report["case_accounting"][label].values())
            for label in ("primary", "repeat")
        ),
        "Whole primary/repeat scenario roster must be completed",
    )
    for case_id in sorted(expected):
        series = report["trajectories"][case_id]
        require(
            isinstance(series, dict) and set(series) == {"times_min", *SIGNALS},
            "Trajectory signal units or shape differ from the frozen comparison",
        )
        times = series["times_min"]
        require(isinstance(times, list), "Trajectory times must be a saved list")
        for value in times:
            finite(value)
        require(times == TIMES, "Trajectory grid must be all 961 exact fixed times")
        for signal in SIGNALS:
            values = series[signal]
            require(
                isinstance(values, list) and len(values) == len(TIMES),
                "Trajectory signal is incomplete or has a mismatched grid",
            )
            for value in values:
                finite(value)
    return report["trajectories"]


def contrast(left, right):
    """Signed trapezoidal separation, in left-minus-right roster order."""
    require(len(left) == len(right) == len(TIMES), "Contrast requires the complete fixed grid")
    differences = [finite(finite(a) - finite(b)) for a, b in zip(left, right, strict=True)]
    try:
        area = finite(
            math.fsum((a / 2 + b / 2) * 0.25 for a, b in zip(differences, differences[1:]))
        )
    except OverflowError as exc:
        raise ValueError("Nonfinite signed trajectory contrast") from exc
    return {
        "signed_auc_difference": area,
        "signed_time_mean_difference": finite(area / 240),
        "maximum_absolute_pointwise_difference": max(abs(value) for value in differences),
    }


def summarize(plan, state, children, reference_context):
    """Children are native-reader results or None, never executable supplied models."""
    order = [source["id"] for source in plan["config"]["sources"]]
    require(len(order) >= 2 and len(set(order)) == len(order), "Invalid frozen source roster")
    require(set(children) == set(order), "Missing or unexpected frozen source")
    accepted, sources = [], {}
    for identity in order:
        child = children[identity]
        attempt = state["sources"][identity]
        is_accepted = (
            attempt["status"] == "completed"
            and child is not None
            and child.get("passed") is True
            and reference_context["accepted"] is True
        )
        if is_accepted:
            validate_trajectories(child)
            accepted.append(identity)
        reason = None
        if not is_accepted:
            reason = (
                "common reference is not accepted"
                if not reference_context["accepted"]
                else "source was not attempted"
                if attempt["status"] == "not_attempted"
                else "source was interrupted"
                if attempt["status"] == "interrupted"
                else "no validated complete child archive; raw output is diagnostic only"
                if child is None
                else "entire source workflow did not complete and pass"
            )
        sources[identity] = {
            "accepted": is_accepted,
            "null_reason": reason,
            "attempt": attempt,
            "model": plan["sources"][identity]["declaration"],
            "scenarios": {
                scenario: {
                    "accepted": is_accepted,
                    "status": "completed" if is_accepted else attempt["status"],
                    "null_reason": reason,
                }
                for scenario in SCENARIOS
            },
            "single_source": child,
        }
    anchor = accepted[0] if accepted else None
    controls, disagreements = {}, []
    if anchor is not None:
        controls = {
            f"{scenario}--{mode}": children[anchor]["trajectories"][f"{scenario}--{mode}"]
            for scenario in SCENARIOS
            for mode in MODES[1:]
        }
        for identity in accepted[1:]:
            for case_id, expected in controls.items():
                for signal in ("times_min", *SIGNALS):
                    if children[identity]["trajectories"][case_id][signal] != expected[signal]:
                        disagreements.append(
                            {"source": identity, "case": case_id, "signal": signal}
                        )
    controls_status = (
        "mismatch" if disagreements else "matched" if len(accepted) >= 2 else "inconclusive"
    )
    common = {
        "status": controls_status,
        "anchor_source": anchor,
        "accepted_sources": accepted,
        "disagreements": disagreements,
        "null_reason": "shared control trajectories disagree"
        if disagreements
        else "fewer than two complete accepted sources"
        if len(accepted) < 2
        else None,
        "trajectories": controls,
    }
    pairs = []
    for left, right in combinations(order, 2):
        reason = (
            common["null_reason"]
            if disagreements
            else f"{left}: {sources[left]['null_reason']}"
            if not sources[left]["accepted"]
            else f"{right}: {sources[right]['null_reason']}"
            if not sources[right]["accepted"]
            else common["null_reason"]
        )
        scenarios = {}
        for scenario in SCENARIOS:
            values = {}
            for signal, unit in SIGNALS.items():
                metrics = None
                if reason is None:
                    case_id = f"{scenario}--candidate"
                    metrics = contrast(
                        children[left]["trajectories"][case_id][signal],
                        children[right]["trajectories"][case_id][signal],
                    )
                values[signal] = {"unit": unit, "auc_unit": unit + " min", "metrics": metrics}
            scenarios[scenario] = {
                "accepted": reason is None,
                "null_reason": reason,
                "signals": values,
            }
        pairs.append(
            {
                "left": left,
                "right": right,
                "accepted": reason is None,
                "null_reason": reason,
                "scenarios": scenarios,
            }
        )
    passed = (
        state["status"] == "completed"
        and reference_context["accepted"] is True
        and len(accepted) == len(order)
        and controls_status == "matched"
    )
    return {
        "status": "completed" if passed else "failed",
        "passed": passed,
        "source_order": order,
        "planned_source_count": len(order),
        "accepted_source_count": len(accepted),
        "planned_source_scenario_count": len(order) * len(SCENARIOS),
        "accepted_source_scenario_count": len(accepted) * len(SCENARIOS),
        "sources": sources,
        "common_controls": common,
        "pairs": pairs,
    }
