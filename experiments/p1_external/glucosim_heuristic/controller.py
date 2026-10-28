"""P1 adapter for GlucoSim's pinned proportional basal-rate agent.

The control law remains in the installed upstream package. This adapter
supplies released CGM and converts the upstream U/hour action to P1 U/minute.
"""

import hashlib
import math
from pathlib import Path

import numpy as np
from glucosim.agents import heuristic

UPSTREAM_HEURISTIC_SHA256 = "8528202b65e2068f5520e066add8293c944136f5d936dc2e30d5e9512878e6aa"
STEP_MINUTES = 3
MINUTES_PER_HOUR = 60


class PinnedHeuristic:
    def __init__(self):
        source = Path(heuristic.__file__)
        if hashlib.sha256(source.read_bytes()).hexdigest() != UPSTREAM_HEURISTIC_SHA256:
            raise ValueError("Installed GlucoSim heuristic source differs from the pinned revision")
        self.native = heuristic.HeuristicBasalAgent(target_glucose=120.0, base_rate=1.0, gain=0.005)
        self.reset()

    def reset(self):
        self.native.reset()
        self.next_minute = 0

    def command(self, observation, announced_g):
        if observation["time_min"] != self.next_minute:
            raise ValueError("Heuristic observation clock must advance by three minutes")
        self.next_minute += STEP_MINUTES
        # Upstream predict() reads only obs[0], the released CGM value.
        # During a mask P1 passes the last released CGM again.
        action = self.native.predict(np.asarray([observation["glucose_mg_dl"]], dtype=float))
        if action.shape != (1,) or not math.isfinite(float(action[0])):
            raise ValueError("Unexpected upstream heuristic action")
        basal_u_hour = float(action[0])
        if not 0.0 <= basal_u_hour <= 3.0:
            raise ValueError("Upstream heuristic rate exceeds its declared U/hour range")
        return {"basal_u_min": basal_u_hour / MINUTES_PER_HOUR, "bolus_u_min": 0.0}


def make_controller(seed):
    if type(seed) is not int:
        raise ValueError("Expected an integer scenario seed")
    return PinnedHeuristic()
