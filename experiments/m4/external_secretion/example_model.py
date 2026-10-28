"""Invented interface example; this is not a biological secretion model."""


def secretion(times_min, glucose_mmol_l):
    """Return evoked pmol/(kg min), one value per prescribed glucose sample."""
    if len(times_min) != len(glucose_mmol_l):
        raise ValueError("Time and glucose grids differ")
    return [0.25 * max(glucose - 5.0, 0.0) for glucose in glucose_mmol_l]
