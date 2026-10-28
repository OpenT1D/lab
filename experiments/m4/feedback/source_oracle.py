"""Closed-form affine-target propagation; no numerical source derivative imports."""

import math


def advance(initial, duration, intercept, slope, dynamic, alpha, gamma):
    """Solve Z'=alpha*(a+b*t-Z), P'=Z+d-gamma*P, with two flux ledgers."""
    if duration == 0:
        return list(initial)
    z0, p0, qp0, ql0 = initial
    t = duration
    ea, eg = math.exp(-alpha * t), math.exp(-gamma * t)
    fa, fg = -math.expm1(-alpha * t) / alpha, -math.expm1(-gamma * t) / gamma
    c = z0 - intercept + slope / alpha
    convolution = t * eg if alpha == gamma else (ea - eg) / (gamma - alpha)
    z = intercept + slope * (t - 1 / alpha) + c * ea
    portal = (
        p0 * eg
        + (intercept - slope / alpha + dynamic) * fg
        + slope * (t - fg) / gamma
        + c * convolution
    )
    pancreatic = (intercept - slope / alpha + dynamic) * t + slope * t * t / 2 + c * fa
    return [z, portal, qp0 + pancreatic, ql0 + pancreatic - (portal - p0)]


def simulate(times, glucose, initial, params):
    """Split at every ramp corner and at the published static target floor."""
    from bisect import bisect_right

    state = list(initial) + [0.0, 0.0]
    output = [state.copy()]
    current = 0.0
    for target in times[1:]:
        while current < target:
            j = min(bisect_right(glucose.edges, current) - 1, glucose.segments - 1)
            start, end = glucose.edges[j : j + 2]
            gradient = (glucose.right[j] - glucose.left[j]) / (end - start)
            a0 = params.basal + params.gain * params.beta * (glucose.left[j] - params.threshold)
            b = params.gain * params.beta * gradient
            stop = min(float(target), end)
            crossing = start - a0 / b if b else math.inf
            if current < crossing < stop:
                stop = crossing
            middle = (current + stop) / 2
            if a0 + b * (middle - start) > 0:
                a = a0 + b * (current - start)
            else:
                a, b = 0.0, 0.0
            state = advance(
                state,
                stop - current,
                a,
                b,
                params.gain * params.K * max(gradient, 0),
                params.alpha,
                params.gamma,
            )
            current = stop
        output.append(state.copy())
    return output
