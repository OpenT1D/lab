"""Independent linear-system oracle for the incremental BC-002 insulin ledger.

This file does not import or call simglucose. The matrix is assembled directly
from the pinned-source equations specified by BC-002. Two auxiliary states
represent the current forcing value and the constant 1, so a matrix exponential
integrates a linear input exactly within each declared segment.
"""

from bisect import bisect_right

import numpy as np
from scipy.linalg import expm


def kinetic_matrix(params):
    """Matrix for [Ip, Il, hepatic loss, peripheral loss, delivered amount]."""
    rates = {}
    for name in ("m1", "m2", "m30", "m4"):
        value = params[name]
        if isinstance(value, (bool, np.bool_)) or not np.isfinite(value) or value <= 0:
            raise ValueError(f"Oracle requires finite positive {name}")
        rates[name] = float(value)
    m1, m2, m30, m4 = (rates[name] for name in ("m1", "m2", "m30", "m4"))
    matrix = np.zeros((5, 5))
    matrix[0, 0], matrix[0, 1] = -(m2 + m4), m1
    matrix[1, 0], matrix[1, 1] = m2, -(m1 + m30)
    matrix[2, 1], matrix[3, 0] = m30, m4
    return matrix


def integral(forcing, start=0.0, stop=None):
    """Independently integrate the explicit segment ordinates over an interval."""
    stop = forcing.edges[-1] if stop is None else stop
    if (
        not np.isfinite(start)
        or not np.isfinite(stop)
        or not 0 <= start <= stop <= forcing.edges[-1]
    ):
        raise ValueError("Oracle integral outside forcing horizon")
    amounts = []
    for a, b, left, right in zip(
        forcing.edges[:-1], forcing.edges[1:], forcing.left, forcing.right, strict=True
    ):
        lo, hi = max(start, a), min(stop, b)
        if hi > lo:
            slope = (right - left) / (b - a)
            # Integral of the affine segment, independent of Forcing.integral().
            amounts.append(left * (hi - lo) + 0.5 * slope * ((hi - a) ** 2 - (lo - a) ** 2))
    return float(sum(amounts))


def simulate(times, params, forcing, route):
    """Zero-inventory solution on the requested complete grid; no numerical ODE."""
    if route not in ("liver", "peripheral"):
        raise ValueError("Oracle route must be liver or peripheral")
    grid = np.asarray(times, dtype=float)
    edges = np.asarray(forcing.edges, dtype=float)
    left = np.asarray(forcing.left, dtype=float)
    right = np.asarray(forcing.right, dtype=float)
    if (
        grid.ndim != 1
        or len(grid) < 2
        or not np.isfinite(grid).all()
        or grid[0] != 0
        or np.any(np.diff(grid) <= 0)
        or edges.ndim != 1
        or len(edges) < 2
        or not np.isfinite(edges).all()
        or edges[0] != 0
        or np.any(np.diff(edges) <= 0)
        or grid[-1] != edges[-1]
        or left.shape != (len(edges) - 1,)
        or right.shape != left.shape
        or not np.isfinite(left).all()
        or not np.isfinite(right).all()
        or np.any(left < 0)
        or np.any(right < 0)
        or forcing.units != "pmol/(kg min)"
    ):
        raise ValueError("Invalid oracle input or incomplete output grid")
    augmented = np.zeros((7, 7))
    augmented[:5, :5] = kinetic_matrix(params)
    augmented[1 if route == "liver" else 0, 5] = 1.0
    augmented[4, 5] = 1.0
    # Column 6 is the constant-one state; row 5 is set to the local input slope.
    state = np.zeros(5)
    result = np.empty((len(grid), 5))
    result[0] = state
    current = 0.0
    for row, target in enumerate(grid[1:], start=1):
        while current < target:
            segment = min(bisect_right(edges, current) - 1, len(left) - 1)
            end = min(float(target), float(edges[segment + 1]))
            slope = (right[segment] - left[segment]) / (edges[segment + 1] - edges[segment])
            input_now = left[segment] + slope * (current - edges[segment])
            augmented[5, 6] = slope
            propagated = expm(augmented * (end - current)) @ np.r_[state, input_now, 1.0]
            state = propagated[:5]
            current = end
        result[row] = state
    if not np.isfinite(result).all():
        raise RuntimeError("Nonfinite independent matrix-exponential solution")
    return result
