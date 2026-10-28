"""BC-006 source hypotheses and analytical diagnostics; standard library only."""

import math


def number(value, *, positive=False):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        raise ValueError("Finite real value required")
    if value <= 0 if positive else value < 0:
        raise ValueError("Invalid numeric sign")
    return value


def phi(g, threshold, half):
    x = max(0, g - threshold)
    return x**3 / ((half - threshold) ** 3 + x**3)


def mobilization(g, p):
    return p["m0"] + p["c"] * g ** p["n"] / (p["k_m"] ** p["n"] + g ** p["n"])


def inventories(docked, activation, p):
    """Distinct preactivation and active quasi-steady pools at the SAME D."""
    number(docked)
    number(activation)
    if activation > 1:
        raise ValueError("Activation must be a fraction")
    number(p["p_minus"], positive=True)
    number(p["p_plus"])
    number(p["f"])
    pre = p["p_plus"] * docked * activation / p["p_minus"]
    qss = p["p_plus"] * docked * activation / (p["p_minus"] + p["f"])
    return {
        "docked_ug": docked,
        "pre_bolus_recruited_ug": pre,
        "printed_qss_ug": qss,
        "finite_fusion_delivered_limit_ug": pre * p["f"] / (p["p_minus"] + p["f"]),
        "pre_to_qss_factor": (p["p_minus"] + p["f"]) / p["p_minus"],
    }


def burst(time, h0, f, unprime, release):
    """Isolated H -> F -> released, with H -> returned; no replenishment."""
    for value in (time, h0, f, unprime):
        number(value)
    number(release, positive=True)
    k = f + unprime
    number(k, positive=True)
    h = h0 * math.exp(-k * time)
    # expm1 avoids cancellation near equal rates; the exact limit is explicit.
    if k == release:
        fused = f * h0 * time * math.exp(-k * time)
    elif k > release:
        fused = f * h0 * math.exp(-release * time) * -math.expm1(-(k - release) * time)
        fused /= k - release
    else:
        fused = f * h0 * math.exp(-k * time) * -math.expm1(-(release - k) * time)
        fused /= release - k
    gone = -h0 * math.expm1(-k * time)
    returned = unprime / k * gone
    released = f / k * gone - fused
    return [h, fused, released, returned]


def calculate(protocol):
    p, s = protocol["parameters"], protocol["source_values"]
    a_paper = phi(s["g_max_mmol_l"], p["g_b"], p["k_phi"])
    a_author = phi(
        s["g_max_mmol_l"],
        s["author_threshold_mg_dl"] / s["glucose_mg_dl_per_mmol_l"],
        s["author_k_phi_mg_dl"] / s["glucose_mg_dl_per_mmol_l"],
    )
    d_paper = mobilization(p["g_b"], p) / p["r"]
    d_author = mobilization(s["author_glucose_basal_mmol_l"], p) / p["r"]
    pools = {
        "caption_basal_equilibrium": inventories(d_paper, a_paper, p),
        "author_seed_exact_threshold": inventories(s["author_docked_seed_ug"], a_author, p),
        "author_glucose_continuum_equilibrium": inventories(d_author, a_author, p),
    }
    pmol_per_ug = 1e6 / s["insulin_molar_mass_g_mol"]
    exact_concentration = pmol_per_ug / s["author_cp_volume_l"]
    chain = []
    coefficient = p["f"] * p["p_plus"] / (p["p_minus"] + p["f"])
    for g in (6.0, 8.0, 12.0):
        d = s["author_docked_seed_ug"]
        q = coefficient * phi(g, p["g_b"], p["k_phi"])
        x, scale = g - p["g_b"], p["k_phi"] - p["g_b"]
        dq = coefficient * 3 * x**2 * scale**3 / (scale**3 + x**3) ** 2
        gd = -(g - p["g_b"]) / s["tau_min"]
        dd = mobilization(g, p) - (p["r"] + q) * d
        omitted, retained = dq * gd * d, q * dd
        dt = 1e-4
        forward = coefficient * phi(g + gd * dt, p["g_b"], p["k_phi"]) * (d + dd * dt)
        backward = coefficient * phi(g - gd * dt, p["g_b"], p["k_phi"]) * (d - dd * dt)
        fd = (forward - backward) / (2 * dt)
        chain.append(
            {
                "glucose_mmol_l": g,
                "docked_ug": d,
                "retained_ug_min2": retained,
                "omitted_ug_min2": omitted,
                "full_product_derivative_ug_min2": retained + omitted,
                "finite_difference_ug_min2": fd,
                "relative_error": abs(fd - retained - omitted)
                / max(abs(retained + omitted), 1e-15),
            }
        )
    return {
        "pools": pools,
        "author_explicit_x0_ug": s["author_x0_ug"],
        "seed_pre_bolus_minus_explicit_ug": pools["author_seed_exact_threshold"][
            "pre_bolus_recruited_ug"
        ]
        - s["author_x0_ug"],
        "seed_is_not_continuum_equilibrium_residual_ug_min": mobilization(
            s["author_glucose_basal_mmol_l"], p
        )
        - p["r"] * s["author_docked_seed_ug"],
        "algebraic_post_bolus_y_ug_min": p["f"]
        * pools["caption_basal_equilibrium"]["printed_qss_ug"],
        "source_reduced_y0_ug_min": 0.0,
        "scale": {
            "pmol_per_ug_insulin": pmol_per_ug,
            "author_basal_pmol_min": s["author_basal_ug_min"] * pmol_per_ug,
            "exact_pmol_l_per_ug_at_author_volume": exact_concentration,
            "rounded_conversion_relative_error": s["author_cp_conversion"] / exact_concentration
            - 1,
            "coded_cp_pmol_l_min_per_ug_min": s["author_cp_conversion"]
            * s["author_cp_extra_scale"],
            "coded_to_unscaled_molar_volume_ratio": s["author_cp_conversion"]
            * s["author_cp_extra_scale"]
            / exact_concentration,
        },
        "chain_rule": chain,
        "verdict": (
            "pre-bolus pool is a candidate explanation, not an author-confirmed correction; "
            "basal and observation scale are source-specific, not calibrated T1D quantities"
        ),
    }
