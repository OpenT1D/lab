"""Descriptive Task 2 comparisons, independent of estimator implementation.

The full-curve value is a reference analysis, never biological truth. None means
an unavailable/failed result; no missing pair is silently converted to zero.
"""

import math
import statistics


def finite_or_missing(value):
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("Use finite numeric endpoints or None for unavailable results")
    try:
        value = float(value)
    except OverflowError as error:
        raise ValueError("Use finite numeric endpoints") from error
    if not math.isfinite(value):
        raise ValueError("Use finite numeric endpoints")
    return value


def endpoint_comparison(pairs):
    """Compare (full-reference, reduced) pmol pairs in their planned order.

    Works for visit totals or participant paired changes, reported separately.
    Precision is the sample SD of differences, not an interval for mean bias.
    These descriptive statistics provide no participant-cluster uncertainty,
    empirical equivalence decision or cohort confidence interval.
    """
    rows, differences = [], []
    reference_missing = reduced_missing = both_missing = 0
    for index, pair in enumerate(pairs):
        if not isinstance(pair, (tuple, list)) or len(pair) != 2:
            raise ValueError("Supply every planned reference/reduced endpoint pair")
        reference, reduced = map(finite_or_missing, pair)
        reference_missing += reference is None
        reduced_missing += reduced is None
        both_missing += reference is None and reduced is None
        difference = None
        if reference is not None and reduced is not None:
            difference = reduced - reference
            if not math.isfinite(difference):
                raise ValueError("Endpoint difference is not finite")
            differences.append(difference)
        rows.append(
            {
                "planned_index": index,
                "reference_pmol": reference,
                "reduced_pmol": reduced,
                "difference_pmol": difference,
                "absolute_difference_pmol": None if difference is None else abs(difference),
                "status": "compared" if difference is not None else "unavailable",
            }
        )
    absolute = [abs(difference) for difference in differences]
    # hypot avoids overflow from squaring large but finite values.
    rms = (
        math.hypot(*(value / math.sqrt(len(differences)) for value in differences))
        if differences
        else None
    )
    low = statistics.median_low(absolute) if absolute else None
    high = statistics.median_high(absolute) if absolute else None
    median = low + (high - low) / 2 if absolute else None
    try:
        precision = statistics.stdev(differences) if len(differences) > 1 else None
    except OverflowError as error:
        raise ValueError("Comparison precision cannot be represented as a finite float") from error
    result = {
        "difference_convention": "reduced minus full-reference; reference is not biological truth",
        "planned_count": len(rows),
        "compared_count": len(differences),
        "reference_unavailable_count": reference_missing,
        "reduced_unavailable_count": reduced_missing,
        "both_unavailable_count": both_missing,
        "bias_pmol": statistics.mean(differences) if differences else None,
        "precision_sample_sd_pmol": precision,
        "mean_absolute_difference_pmol": statistics.mean(absolute) if absolute else None,
        "median_absolute_difference_pmol": median,
        "root_mean_square_difference_pmol": rms,
        "maximum_absolute_difference_pmol": max(absolute) if absolute else None,
        "rows": rows,
    }
    if any(isinstance(value, float) and not math.isfinite(value) for value in result.values()):
        raise ValueError("Comparison statistic cannot be represented as a finite float")
    return result


def direction_comparison(pairs):
    """Compare the source-frozen conditional change directions, retaining failures.

    Both unresolved is still an indeterminate comparison. This helper does not
    classify uncertainty intervals or Task 1's across-assumption conclusion;
    both remain owned by the shared analysis core.
    """
    allowed = {"increase", "decrease", "unresolved", None}
    counts = dict.fromkeys(
        ("same_resolved_direction", "direction_reversal", "indeterminate", "unavailable"), 0
    )
    rows = []
    for index, pair in enumerate(pairs):
        if not isinstance(pair, (tuple, list)) or len(pair) != 2:
            raise ValueError("Supply every planned reference/reduced direction pair")
        reference, reduced = pair
        if not all(value is None or isinstance(value, str) for value in pair) or any(
            value not in allowed for value in pair
        ):
            raise ValueError("Use source-frozen directions or None for unavailable conclusions")
        if reference is None or reduced is None:
            status = "unavailable"
        elif "unresolved" in pair:
            status = "indeterminate"
        elif reference == reduced:
            status = "same_resolved_direction"
        else:
            status = "direction_reversal"
        counts[status] += 1
        rows.append(
            {"planned_index": index, "reference": reference, "reduced": reduced, "status": status}
        )
    return {"planned_count": len(rows), **counts, "rows": rows}
