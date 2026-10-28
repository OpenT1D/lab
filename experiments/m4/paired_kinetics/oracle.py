"""Independent nonzero-inventory propagation; no numerical ODE derivative imports."""

from bisect import bisect_right

import numpy as np
from scipy.linalg import expm


def insulin(times, params, forcing, initial):
    from experiments.m4.kinetic_inlet.oracle import kinetic_matrix, simulate

    forced = simulate(times, params, forcing, "liver")
    matrix = kinetic_matrix(params)
    return forced + np.array([expm(matrix * t) @ initial for t in times])


def cpeptide(times, params, forcing, initial):
    """State [central, peripheral, eliminated, input], affine forcing per segment."""
    matrix = np.zeros((6, 6))
    matrix[0, 0], matrix[0, 1] = -params.k1 - params.k3, params.k2
    matrix[1, 0], matrix[1, 1] = params.k1, -params.k2
    matrix[2, 0] = params.k3
    matrix[0, 4] = matrix[3, 4] = 1
    state = np.array(initial, dtype=float)
    result = [state.copy()]
    current = 0.0
    for target in times[1:]:
        while current < target:
            j = min(bisect_right(forcing.edges, current) - 1, forcing.segments - 1)
            a, b = forcing.edges[j : j + 2]
            end = min(target, b)
            slope = (forcing.right[j] - forcing.left[j]) / (b - a)
            value = forcing.left[j] + slope * (current - a)
            matrix[4, 5] = slope
            state = (expm(matrix * (end - current)) @ np.r_[state, value, 1])[:4]
            current = end
        result.append(state.copy())
    return np.asarray(result)
