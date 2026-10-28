"""Published hepatic relations with explicit BC-009 baseline anchors.

Pure scalar arithmetic. This is a conditional structural comparison, not a
fitted residual-T1D or graft model. No clinical parameter defaults are exposed.
"""

import math

from experiments.m4.feedback.contract import number


def anchors(params, basal, source):
    hb = params["m30"] / (params["m1"] + params["m30"])
    return {
        "HEb": hb,
        "m6_effective": hb + source["m5_min_kg_pmol"] * basal["Sb_pmol_kg_min"],
        "kp1_effective": params["kp1"] + source["kp4_mg_pmol_min"] * basal["P_pmol_kg"],
        "m5": source["m5_min_kg_pmol"],
        "kp4": source["kp4_mg_pmol_min"],
    }


def terms(state, params, basal, source, variant, *, check_domain=True):
    """S drives extraction, P drives EGP; neither Z nor Spo substitutes for S."""
    if len(state) != 20 or any(not math.isfinite(v) for v in state):
        raise ValueError("Twenty finite native/source/ledger states required")
    if any(type(variant[k]) is not bool for k in ("extraction", "portal")):
        raise ValueError("Explicit Boolean mechanism switches required")
    a = anchors(params, basal, source)
    gamma = source["gamma"]
    liver = gamma * state[14]
    he = a["HEb"] - (a["m5"] * (liver - basal["Sb_pmol_kg_min"]) if variant["extraction"] else 0.0)
    if not math.isfinite(he) or he == 1 or (check_domain and not 0 < he < 0.999999):
        raise ValueError("Extraction outside BC-009 computational domain")
    delta_m3 = params["m1"] * (he - a["HEb"]) / ((1 - he) * (1 - a["HEb"]))
    m3 = params["m30"] + delta_m3
    native_raw = params["kp1"] - params["kp2"] * state[3] - params["kp3"] * state[8]
    portal_term = a["kp4"] * (state[14] - basal["P_pmol_kg"]) if variant["portal"] else 0.0
    raw = native_raw - portal_term
    return {
        "HE": he,
        "m3": m3,
        "EGP": max(raw, 0),
        "raw_EGP": raw,
        "delta_EGP": max(raw, 0) - max(native_raw, 0),
        "delta_hepatic_loss": delta_m3 * state[9],
        "portal_term": portal_term,
    }


def literal_mismatch(params, basal, source):
    """Original coefficients are assessed at BC-008 baseline, never silently used."""
    hb = params["m30"] / (params["m1"] + params["m30"])
    he = source["m6_published"] - source["m5_min_kg_pmol"] * basal["Sb_pmol_kg_min"]
    number(he, positive=True)
    if he >= 1:
        raise ValueError("Invalid literal extraction fraction")
    rate = params["m1"] * he / (1 - he)
    raw = params["kp1"] - params["kp2"] * basal["state"][3] - params["kp3"] * basal["state"][8]
    absolute_portal = source["kp4_mg_pmol_min"] * basal["P_pmol_kg"]
    return {
        "HE_native": hb,
        "HE_literal": he,
        "m3_literal_per_min": rate,
        "liver_derivative_shift_pmol_kg_min": -(rate - params["m30"]) * basal["state"][9],
        "glucose_derivative_shift_mg_dl_min": (max(raw - absolute_portal, 0) - max(raw, 0))
        / params["Vg"],
        "implied_published_Sb_pmol_kg_min": (source["m6_published"] - source["HEb_published"])
        / source["m5_min_kg_pmol"],
        "native_unused_m5": params["m5"],
        **anchors(params, basal, source),
    }
