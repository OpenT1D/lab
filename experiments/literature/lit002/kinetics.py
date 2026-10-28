"""Synthetic SC appearance comparison; amounts mU/kg, rates mU/kg/min, time min.

Original implementation of conserved linear depot equations, without systemic
volume, elimination, glucose or an insulin controller. Faggionato et al. (2021),
DOI 10.3390/metabo11040235, Eq. (3), Figure 3 and Table 2 supply the fixed-effect
SC specification transcribed in ../lit001/parameters.json. As in LIT-001, ka1 is
constant and all amounts use an explicitly declared body-weight normalization.
The Cambridge serial form/default 55 min comes from the pinned source audited
in docs/research/lit001-engine-audit.md. Neither constant set defines a patient
or establishes clinical performance. Prior infusion and delay inventory are
explicit, including delivery that has not yet entered the first model depot.
"""

from __future__ import annotations

from bisect import bisect_right
from collections.abc import Sequence
from dataclasses import dataclass
from math import exp, expm1, factorial, fsum, isfinite

State = tuple[float, float]
Schedule = Sequence[tuple[float, float]]


def _nonnegative(value: float, name: str, *, positive: bool = False) -> None:
    if isinstance(value, bool) or not isfinite(value) or value < 0 or (positive and value == 0):
        raise ValueError(f"{name} must be finite and {'positive' if positive else 'nonnegative'}")


@dataclass(frozen=True)
class SCParameters:
    """First-depot appearance, depot transfer, second appearance and input delay."""

    ka1: float
    kd: float
    ka2: float
    delay_min: float = 0.0

    def __post_init__(self) -> None:
        _nonnegative(self.ka1, "ka1")
        _nonnegative(self.kd, "kd", positive=True)
        _nonnegative(self.ka2, "ka2", positive=True)
        _nonnegative(self.delay_min, "delay_min")

    @property
    def mean_appearance_min(self) -> float:
        """Mean time from an ideal delivered impulse to systemic appearance."""
        a = self.ka1 + self.kd
        return self.delay_min + 1 / a + self.kd / (a * self.ka2)


CAMBRIDGE = SCParameters(0.0, 1 / 55.0, 1 / 55.0)
FAGGIONATO = SCParameters(0.000134, 0.0128 + 0.0155, 0.0128, 5.62)


def matched_cambridge(reference: SCParameters = FAGGIONATO) -> SCParameters:
    """Serial-only comparator matching the reference impulse's first moment.

    This is an equation-derived comparator, not a fit to observations. Its two
    serial waiting times total 2*tmaxI; the source delay is included in that match.
    """
    rate = 2 / reference.mean_appearance_min
    return SCParameters(0.0, rate, rate)


def _state(state: State) -> None:
    if len(state) != 2:
        raise ValueError("Exactly two SC depot amounts are required")
    for value in state:
        _nonnegative(value, "depot amount")


def appearance(state: State, p: SCParameters) -> float:
    """Instantaneous systemic entry rate, with no systemic process applied."""
    _state(state)
    return p.ka1 * state[0] + p.ka2 * state[1]


def steady_state(rate: float, p: SCParameters) -> State:
    """Equilibrium depots under constant prior infusion extending to -infinity."""
    _nonnegative(rate, "rate")
    first = rate / (p.ka1 + p.kd)
    return first, p.kd * first / p.ka2


def _transfer(a: float, b: float, duration: float) -> float:
    """Integral exp(-a*s) exp(-b*(t-s)) ds, including coincident rates."""
    difference = abs(a - b)
    if difference == 0:
        return duration * exp(-a * duration)
    return exp(-min(a, b) * duration) * -expm1(-difference * duration) / difference


def _integrated_transfer(a: float, b: float, duration: float) -> float:
    """Integral of _transfer; small-time series avoids subtracting near equals."""
    x, y = a * duration, b * duration
    if max(x, y) < 0.1:
        previous, current = 0.0, 1.0
        terms = []
        for n in range(16):
            terms.append((-1) ** n * current / factorial(n + 2))
            previous, current = current, (x + y) * current - x * y * previous
        return duration**2 * fsum(terms)
    # Symmetry permits division by the larger rate, avoiding small-a cancellation.
    larger, smaller = max(a, b), min(a, b)
    return (-expm1(-smaller * duration) / smaller - _transfer(a, b, duration)) / larger


def propagate(state: State, rate: float, duration: float, p: SCParameters) -> tuple[State, float]:
    """Exact constant-input propagation and absorbed amount during the interval.

    `rate` is the input already arriving at depot 1: callers apply delivery delay
    before this function. This distinction prevents delay being counted twice.
    Conservation computes the absorbed integral; floating-point roundoff can leave
    an amount within machine precision of zero on an extremely short interval.
    """
    _state(state)
    _nonnegative(rate, "rate")
    _nonnegative(duration, "duration")
    if duration == 0:
        return state, 0.0
    a, b = p.ka1 + p.kd, p.ka2
    first, second = state
    next_first = first * exp(-a * duration) + rate * -expm1(-a * duration) / a
    next_second = fsum(
        (
            second * exp(-b * duration),
            p.kd * first * _transfer(a, b, duration),
            p.kd * rate * _integrated_transfer(a, b, duration),
        )
    )
    absorbed = fsum((first, second, rate * duration, -next_first, -next_second))
    return (next_first, next_second), absorbed


@dataclass(frozen=True)
class SCSample:
    time_min: float
    sc1: float
    sc2: float
    appearance: float
    delay_inventory: float
    cumulative_delivered: float
    cumulative_absorbed: float
    balance_residual: float


def _validated_schedule(schedule: Schedule, prior_basal: float) -> tuple[list, list, list]:
    _nonnegative(prior_basal, "prior_basal")
    if not schedule or schedule[0][0] != 0:
        raise ValueError("The right-continuous delivery schedule must begin at time zero")
    knots, rates, prefix = [], [], [0.0]
    for time, rate in schedule:
        _nonnegative(time, "schedule time")
        _nonnegative(rate, "delivered rate")
        if knots and time <= knots[-1]:
            raise ValueError("Schedule times must be strictly increasing")
        if knots:
            prefix.append(prefix[-1] + rates[-1] * (time - knots[-1]))
        knots.append(time)
        rates.append(rate)
    return knots, rates, prefix


def simulate(
    times: Sequence[float],
    schedule: Schedule,
    prior_basal: float,
    p: SCParameters,
    *,
    initial_state: State | None = None,
) -> list[SCSample]:
    """Exact response to right-continuous piecewise-constant delivered rates.

    The last scheduled rate continues indefinitely. For t<0 the delivered rate is
    `prior_basal`; default initial depots are its equilibrium. The initial delay
    inventory is prior_basal*delay_min even when custom depots are supplied. All
    shifted rate switches are integrated exactly, independently of the output grid.
    Cumulative delivered/absorbed quantities start at zero, excluding prior totals.
    """
    knots, rates, prefix = _validated_schedule(schedule, prior_basal)
    if not times:
        raise ValueError("At least one output time is required")
    for i, time in enumerate(times):
        _nonnegative(time, "output time")
        if i and time <= times[i - 1]:
            raise ValueError("Output times must be strictly increasing")
    state = steady_state(prior_basal, p) if initial_state is None else initial_state
    _state(state)
    initial_inventory = fsum((*state, prior_basal * p.delay_min))

    def total_at(time: float) -> float:
        if time < 0:
            return prior_basal * time
        index = bisect_right(knots, time) - 1
        return prefix[index] + rates[index] * (time - knots[index])

    shifted = [k + p.delay_min for k in knots]
    cuts = sorted({0.0, *times, *(t for t in shifted if t <= times[-1])})
    output_times = set(times)
    result, absorbed_steps = [], []
    previous = 0.0
    for time in cuts:
        # Identify the input by the already shifted switch times. Subtracting
        # delay from a floating-point boundary can put it just before its knot.
        rate_index = bisect_right(shifted, previous) - 1
        rate = prior_basal if rate_index < 0 else rates[rate_index]
        state, absorbed = propagate(state, rate, time - previous, p)
        absorbed_steps.append(absorbed)
        previous = time
        if time not in output_times:
            continue
        delivered = total_at(time)
        queue = total_at(time) - total_at(time - p.delay_min)
        cumulative_absorbed = fsum(absorbed_steps)
        result.append(
            SCSample(
                time,
                *state,
                appearance(state, p),
                queue,
                delivered,
                cumulative_absorbed,
                fsum((initial_inventory, delivered, -sum(state), -queue, -cumulative_absorbed)),
            )
        )
    return result


def impulse(time: float, dose: float, p: SCParameters) -> SCSample:
    """Ideal delivered impulse at zero with zero prior history; a synthetic case.

    At t=delay the sample is after the depot jump. `dose` is mU/kg, not a rate.
    The finite-rate schedule interface never treats a pump command as an impulse.
    """
    _nonnegative(time, "time")
    _nonnegative(dose, "dose")
    if time < p.delay_min:
        state, absorbed, queue = (0.0, 0.0), 0.0, dose
    else:
        state, absorbed = propagate((dose, 0.0), 0.0, time - p.delay_min, p)
        queue = 0.0
    return SCSample(
        time,
        *state,
        appearance(state, p),
        queue,
        dose,
        absorbed,
        fsum((dose, -sum(state), -absorbed, -queue)),
    )
