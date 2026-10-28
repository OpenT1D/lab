"""Invented development-only ridge example, original OpenT1D Apache-2.0 code."""


def predict(record, state):
    """Apply frozen preprocessing and weights without fitting or future information."""
    values = [record[name] for name in state["feature_names"]]
    standardized = [
        (value - mean) / scale
        for value, mean, scale in zip(values, state["means"], state["scales"], strict=True)
    ]
    return state["coefficients"][0] + sum(
        coefficient * value
        for coefficient, value in zip(state["coefficients"][1:], standardized, strict=True)
    )
