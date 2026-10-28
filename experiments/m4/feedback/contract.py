"""BC-008 specification arithmetic only; no coupled trajectory or secretion solver."""

import hashlib
import json
import math

PROTOCOL_HASHES = {
    "BC-008/1": "ea938945eaf7c0e9642603f3aa0cc841b8a9419285bb982d126e46d09ae343b8",
    "BC-008/2": "f6446aa569018346cbfe901429f63f5898ddb21116ee3ea85e261803176b0547",
}


def validate(protocol):
    data = json.dumps(protocol, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
    if hashlib.sha256(data).hexdigest() != PROTOCOL_HASHES.get(protocol.get("id")):
        raise ValueError("BC-008 protocols are frozen; amend and version a changed protocol")


def number(value, *, signed=False, positive=False):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        raise ValueError("Finite numeric value required")
    if (positive and value <= 0) or (not signed and value < 0):
        raise ValueError("Invalid sign")
    return value


def baseline(params, initial, fraction, gamma):
    """Replace SC basal while preserving Ip; Il and SC inventories must change."""
    number(fraction)
    if fraction > 1 or len(initial) != 13:
        raise ValueError("Replacement must be in [0,1] with 13 native states")
    for key in ("u2ss", "m1", "m30", "BW", "Vi", "Vg"):
        number(params[key], positive=True)
    number(gamma, positive=True)
    state = [number(v, signed=(i == 6)) for i, v in enumerate(initial)]
    displaced = fraction * params["u2ss"]
    sb = displaced * (params["m1"] + params["m30"]) / params["m1"]
    state[9] += displaced / params["m1"]
    state[10] *= 1 - fraction
    state[11] *= 1 - fraction
    sc = (1 - fraction) * params["u2ss"]
    values = {
        "state": state,
        "u_sc_pmol_kg_min": sc,
        "action_insulin_u_min": sc * params["BW"] / 6000,
        "Sb_pmol_kg_min": sb,
        "Z_pmol_kg_min": sb,
        "P_pmol_kg": sb / gamma,
        "h_mg_dl": initial[3] / params["Vg"],
    }
    for key, value in values.items():
        if key != "state":
            number(value)
    return values


def secretion_terms(glucose, glucose_rate, z, portal, basal, threshold, gain, parameters):
    """Pointwise shifted equations 23-26; intended for a specification check only.

    Z=Y+Sb has a nonnegative target. Y itself may be negative below basal.
    Spo (pancreatic entry) and S (post-transit liver arrival) are distinct.
    """
    for value in (glucose, z, portal, basal, threshold, gain):
        number(value)
    number(glucose_rate, signed=True)
    for value in parameters.values():
        number(value, positive=True)
    target = max(basal + gain * parameters["beta_pmol_kg_min_per_mg_dl"] * (glucose - threshold), 0)
    pancreatic = z + gain * parameters["K_pmol_kg_per_mg_dl"] * max(glucose_rate, 0)
    liver = parameters["gamma_per_min"] * portal
    return {
        "target": target,
        "pancreatic": pancreatic,
        "liver": liver,
        "Z_dot": parameters["alpha_per_min"] * (target - z),
        "P_dot": pancreatic - liver,
    }
