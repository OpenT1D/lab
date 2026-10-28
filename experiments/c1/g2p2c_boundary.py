"""Causal, simulator-free M1 boundary for a source-pinned G2P2C feasibility test.

This prepares state and action units only. It does not include a trained
policy or qualify the published result as an M1 comparator.
"""

import math

from experiments.m1.contracts import STEP, Action, Observation

HISTORY = 12
GLUCOSE_RANGE = (39.0, 600.0)
INSULIN_RANGE = (0.0, 5.0)
ACTION_SCALE = 5.0


def _scale(value, lower, upper):
    """Pinned G2P2C utils/core.py linear_scaling, without clipping."""
    return (value - lower) * 2 / (upper - lower) - 1


def pump_rate(policy_action):
    """Pinned exponential action transform; output is an M1 U/min rate."""
    if type(policy_action) not in (int, float) or not math.isfinite(policy_action):
        raise ValueError("Policy output must be finite")
    if not -1 <= policy_action <= 1:
        raise ValueError("Policy output outside source action domain")
    rate = ACTION_SCALE * math.exp((policy_action - 1) * 4)
    return Action(min(ACTION_SCALE, max(0.0, rate)), 0.0)


class CausalState:
    """Twelve [CGM, commanded insulin] samples with the source normalization."""

    def __init__(self):
        self.reset()

    def reset(self):
        self._history = [(0.0, 0.0)] * HISTORY
        self._time_min = None

    def restart_after_gap(self, observation, *, previous_action):
        """Start a new causal history at the first fresh sample after a gap."""
        if not isinstance(observation, Observation) or observation.time_min < STEP:
            raise ValueError("Expected a later M1 observation after a sensor gap")
        candidate = CausalState()
        candidate._time_min = observation.time_min - STEP
        history = candidate.update(observation, previous_action=previous_action)
        self._history = candidate._history
        self._time_min = candidate._time_min
        return history

    def update(self, observation, *, previous_action=None):
        if not isinstance(observation, Observation):
            raise ValueError("Only the M1 released Observation is accepted")
        if not observation.available:
            raise ValueError("Source policy has no specified stale-CGM input behavior")
        if self._time_min is None:
            if observation.time_min != 0 or previous_action is not None:
                raise ValueError("Reset state requires time zero and no previous action")
            insulin = 0.0
        else:
            if observation.time_min != self._time_min + STEP:
                raise ValueError("Expected the next three-minute observation")
            if not isinstance(previous_action, Action) or previous_action.bolus_u_min != 0:
                raise ValueError("Expected the prior basal-only M1 command")
            insulin = previous_action.basal_u_min
        glucose = observation.glucose_mg_dl
        if not GLUCOSE_RANGE[0] <= glucose <= GLUCOSE_RANGE[1]:
            raise ValueError("CGM outside source sensor range")
        if not INSULIN_RANGE[0] <= insulin <= INSULIN_RANGE[1]:
            raise ValueError("Commanded insulin outside source action range")
        sample = (
            _scale(glucose, *GLUCOSE_RANGE),
            _scale(insulin, *INSULIN_RANGE),
        )
        self._history = self._history[1:] + [sample]
        self._time_min = observation.time_min
        return tuple(self._history)
