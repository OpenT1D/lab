"""Single-file adapter of the already attributed BC-008 secretion equations.

This source is an interface example, not a new model or independent evidence.
"""


def evaluate(
    time_min,
    glucose_mg_dl,
    glucose_rate_mg_dl_min,
    z_pmol_kg_min,
    basal_pmol_kg_min,
    threshold_mg_dl,
    parameters,
):
    """Return (dZ/dt, pancreatic Spo) in the declared molar units."""
    target = max(
        basal_pmol_kg_min
        + parameters["beta_pmol_kg_min_per_mg_dl"] * (glucose_mg_dl - threshold_mg_dl),
        0.0,
    )
    zdot = parameters["alpha_per_min"] * (target - z_pmol_kg_min)
    pancreatic = z_pmol_kg_min + parameters["K_pmol_kg_per_mg_dl"] * max(
        glucose_rate_mg_dl_min, 0.0
    )
    return [zdot, pancreatic]
