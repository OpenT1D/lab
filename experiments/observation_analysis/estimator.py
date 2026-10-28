"""Original exact algebra for the published two-compartment source model.

Whole-body pmol, pmol/L, L and minutes. No GPL implementation is imported or
copied. This inverts declared piecewise-linear central concentrations; it does
not fit kinetics, a glucose-secretion law, or a patient-specific physiology.
"""

import math

from .observations import fields, identifier, number, text

VERSION = "polonsky1986-fixed-kinetic-linear-concentration-exact/1"
RATE_TOLERANCE = 1e-9  # Numerical boundary tolerance, never a clinical threshold.


def validate_variant(value):
    fields(
        value,
        (
            "id",
            "rationale",
            "k1_per_min",
            "k2_per_min",
            "k3_per_min",
            "volume_l",
            "initial_peripheral_factor",
        ),
        "variant",
    )
    identifier(value["id"], "variant id")
    text(value["rationale"], "variant rationale and engineering scope")
    number(value["k1_per_min"], "central-to-peripheral rate")
    for key in ("k2_per_min", "k3_per_min", "volume_l", "initial_peripheral_factor"):
        number(value[key], key, strict=True)
    return value


def exponential_integrals(rate, width):
    """u=int exp(-rate*t)dt, w=int (width-t)*exp(-rate*t)dt.

    w loses precision by subtraction near zero; its convergent series avoids
    that subtraction. These expressions also avoid positive-exponential overflow.
    """
    x = rate * width
    u = -math.expm1(-x) / rate
    if x < 1e-3:
        w = (
            width
            * width
            * (
                0.5
                + x
                * (
                    -1 / 6
                    + x * (1 / 24 + x * (-1 / 120 + x * (1 / 720 + x * (-1 / 5040 + x / 40320))))
                )
            )
        )
    else:
        w = (width - u) / rate
    return u, w


def interval(c0, c1, width, peripheral, variant):
    """Exact peripheral update, total secretion and continuous-interval minimum."""
    a, b, d, v = (variant[key] for key in ("k1_per_min", "k2_per_min", "k3_per_min", "volume_l"))
    slope = (c1 - c0) / width
    imbalance = a * v * c0 - b * peripheral
    u, w = exponential_integrals(b, width)
    delta_peripheral = u * imbalance + a * v * slope * w
    end_peripheral = peripheral + delta_peripheral
    eliminated = d * v * width * (c0 + c1) / 2
    total = math.fsum((v * (c1 - c0), delta_peripheral, eliminated))

    def rate_at(t):
        ut, _ = exponential_integrals(b, t)
        return math.fsum(
            (v * slope, d * v * (c0 + slope * t), imbalance * math.exp(-b * t), a * v * slope * ut)
        )

    candidates = [0.0, width]
    denominator = a * v * slope - b * imbalance
    if denominator:
        exponential = -d * v * slope / denominator
        if 0 < exponential < 1:
            stationary = -math.log(exponential) / b
            if 0 < stationary < width:
                candidates.append(stationary)
    minimum_time = min(candidates, key=rate_at)
    return {
        "width_min": width,
        "central_start_pmol": v * c0,
        "central_end_pmol": v * c1,
        "peripheral_start_pmol": peripheral,
        "peripheral_end_pmol": end_peripheral,
        "eliminated_pmol": eliminated,
        "secretion_pmol": total,
        "minimum_rate_pmol_min": rate_at(minimum_time),
        "minimum_time_in_interval_min": minimum_time,
        "start_rate_pmol_min": rate_at(0),
        "end_rate_pmol_min": rate_at(width),
    }


def estimate(times, concentrations, variant):
    """Return negative/boundary results explicitly; never silently constrain them."""
    validate_variant(variant)
    if len(times) != len(concentrations) or len(times) < 2 or times[0] != 0 or times[-1] != 120:
        raise ValueError("Matched observations with measured 0 and 120 minute endpoints required")
    for value in times:
        number(value, "observation time")
    for value in concentrations:
        number(value, "C-peptide concentration")
    if any(b <= a for a, b in zip(times, times[1:])):
        raise ValueError("Observation times must strictly increase")
    v = variant["volume_l"]
    initial_central = v * concentrations[0]
    initial_peripheral = (
        variant["initial_peripheral_factor"]
        * variant["k1_per_min"]
        / variant["k2_per_min"]
        * initial_central
    )
    peripheral = initial_peripheral
    intervals = []
    for index, (a, b) in enumerate(zip(times, times[1:])):
        result = interval(
            concentrations[index], concentrations[index + 1], b - a, peripheral, variant
        )
        intervals.append({"start_min": a, "end_min": b, **result})
        peripheral = result["peripheral_end_pmol"]
    total = math.fsum(item["secretion_pmol"] for item in intervals)
    minimum = min(item["minimum_rate_pmol_min"] for item in intervals)
    quantities = [total, minimum, initial_central, initial_peripheral, peripheral]
    quantities.extend(value for item in intervals for value in item.values())
    if not all(math.isfinite(value) for value in quantities):
        raise ValueError("Nonfinite analysis result")
    return {
        "method": VERSION,
        "status": "completed" if minimum >= -RATE_TOLERANCE else "boundary_failed",
        "total_pmol": total,
        "minimum_rate_pmol_min": minimum,
        "initial_central_pmol": initial_central,
        "initial_peripheral_pmol": initial_peripheral,
        "final_central_pmol": v * concentrations[-1],
        "final_peripheral_pmol": peripheral,
        "basal_equilibrium_reference_pmol_min": variant["k3_per_min"] * initial_central,
        "intervals": intervals,
        "boundary_failures": [] if minimum >= -RATE_TOLERANCE else ["negative_inferred_secretion"],
        "fit_scope": (
            "exact interpolation under fixed assumptions; no independent goodness-of-fit evidence"
        ),
    }


def trapezoid(times, values):
    if len(times) != len(values) or len(times) < 2:
        raise ValueError("Matched times and values required for AUC")
    return math.fsum(
        (b - a) * (x + y) / 2 for a, b, x, y in zip(times, times[1:], values, values[1:])
    )
