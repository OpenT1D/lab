"""Ultradian f1 law, Karamched et al. 2021, section II, p. 023142-3.

An original equation implementation with Sturis 1991 ancestry. Preserve the
published response shape; replace its whole-body mU/min amplitude with the
host's declared synthetic basal molar rate. This is a pancreatic-inlet
composition, not reproduction of the six-state ultradian metabolic model.
"""

import math


def response(glucose_mg_dl, a1, c1_mg_l):
    """Published dimensionless f1/Rm; concentration is converted once to mg/L."""
    for value in (glucose_mg_dl, a1, c1_mg_l):
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise ValueError("Response inputs must be finite numbers")
        if not math.isfinite(value):
            raise ValueError("Response inputs must be finite numbers")
    if glucose_mg_dl < 0 or not 0 <= a1 <= 50 or c1_mg_l <= 0:
        raise ValueError("Unsupported glucose or response parameter domain")
    x = 10.0 * glucose_mg_dl / c1_mg_l - a1
    # Algebraically identical sigmoid branches avoid overflow, without clipping.
    if x >= 0:
        return 1.0 / (1.0 + math.exp(-x))
    ex = math.exp(x)
    return ex / (1.0 + ex)


def evaluate(
    time_min,
    glucose_mg_dl,
    glucose_rate_mg_dl_min,
    z_pmol_kg_min,
    basal_pmol_kg_min,
    threshold_mg_dl,
    parameters,
):
    """Return zero bookkeeping-state derivative and total pancreatic rate.

    The published f1 law has no secretion state, derivative or fitted future
    input. Z stays at host basal and is unused, rather than repurposed.
    """
    for value in (basal_pmol_kg_min, threshold_mg_dl):
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise ValueError("Basal context must be finite numbers")
        if not math.isfinite(value):
            raise ValueError("Basal context must be finite numbers")
    if basal_pmol_kg_min < 0 or threshold_mg_dl <= 0:
        raise ValueError("Basal context outside the declared domain")
    a1, c1 = parameters["a1"], parameters["C1_mg_l"]
    current = response(glucose_mg_dl, a1, c1)
    initial = response(threshold_mg_dl, a1, c1)
    return [0.0, basal_pmol_kg_min * (current / initial)]
