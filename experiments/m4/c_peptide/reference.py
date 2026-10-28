"""Independent analytical concentration reference from Polonsky p100.

No import of the ODE model or its derivative. The printed bolus response and
its integrated kernel provide an independent constant-segment convolution.
"""

import numpy as np


def components(params):
    total = params.k1 + params.k2 + params.k3
    # Algebraic equivalent avoids cancellation around repeated decay rates.
    discriminant = np.sqrt((params.k1 + params.k2 - params.k3) ** 2 + 4 * params.k1 * params.k3)
    alpha = (total + discriminant) / 2
    beta = 2 * params.k2 * params.k3 / (total + discriminant)
    return alpha, beta


def kernel(times, params, *, integral=False):
    """Central amount response per unit central bolus, or its time integral."""
    times = np.asarray(times, dtype=float)
    if not np.isfinite(times).all() or np.any(times < 0):
        raise ValueError("Analytical response needs finite nonnegative times")
    if params.k1 == 0:
        return -np.expm1(-params.k3 * times) / params.k3 if integral else np.exp(-params.k3 * times)
    alpha, beta = components(params)
    fast = (alpha - params.k2) / (alpha - beta)
    slow = (params.k2 - beta) / (alpha - beta)
    if integral:
        return fast * -np.expm1(-alpha * times) / alpha + slow * -np.expm1(-beta * times) / beta
    return fast * np.exp(-alpha * times) + slow * np.exp(-beta * times)


def bolus(times, params, dose):
    return dose * kernel(times, params) / params.volume_l_kg


def constant_schedule(times, params, forcing, initial):
    """Exact convolution of the printed kernel for explicit constant segments."""
    if forcing.left != forcing.right:
        raise ValueError("Analytical schedule reference supports constant segments only")
    times = np.asarray(times, dtype=float)
    if np.any(times < 0) or np.any(times > forcing.horizon):
        raise ValueError("Reference cannot extrapolate beyond declared input")
    alpha, beta = components(params)
    if alpha == beta:
        return_from_periphery = params.k2 * times * np.exp(-alpha * times)
    else:
        return_from_periphery = (
            params.k2 * np.exp(-beta * times) * -np.expm1(-(alpha - beta) * times) / (alpha - beta)
        )
    amount = initial[0] * kernel(times, params) + initial[1] * return_from_periphery
    for a, b, q in zip(forcing.edges[:-1], forcing.edges[1:], forcing.left, strict=True):
        amount += q * (
            kernel(np.maximum(times - a, 0), params, integral=True)
            - kernel(np.maximum(times - b, 0), params, integral=True)
        )
    return amount / params.volume_l_kg


def one_compartment(times, params, forcing, initial_central):
    """Simpler comparator: same central loss and volume, with no exchange pool."""
    times = np.asarray(times, dtype=float)
    if forcing.left != forcing.right:
        raise ValueError("Comparator supports constant segments only")
    amount = initial_central * np.exp(-params.k3 * times)
    for a, b, q in zip(forcing.edges[:-1], forcing.edges[1:], forcing.left, strict=True):
        amount += (
            q
            / params.k3
            * (
                np.exp(-params.k3 * np.maximum(times - b, 0))
                - np.exp(-params.k3 * np.maximum(times - a, 0))
            )
        )
    return amount / params.volume_l_kg
