"""P1 adapter for the pinned third-party simglucose PIDController.

The PID equation and state updates stay in the installed upstream package.
Only the P1 causal input, rate bounds, and clock are owned here.
"""

import hashlib
import math
from pathlib import Path
from types import SimpleNamespace

from simglucose.controller import pid_ctrller

UPSTREAM_PID_SHA256 = "1eb84cbf2485e2eb591d221cdbf2d276072794a95ff97825795fe1bfb2c2b5bf"
STEP_MINUTES = 3


class PinnedPID:
    def __init__(self):
        source = Path(pid_ctrller.__file__)
        if hashlib.sha256(source.read_bytes()).hexdigest() != UPSTREAM_PID_SHA256:
            raise ValueError("Installed simglucose PID source differs from the pinned revision")
        self.native = pid_ctrller.PIDController(P=0.001, I=0.00001, D=0.001, target=140)
        self.reset()

    def reset(self):
        self.native.reset()
        self.next_minute = 0

    def command(self, observation, announced_g):
        if observation["time_min"] != self.next_minute:
            raise ValueError("PID observation clock must advance by three minutes")
        self.next_minute += STEP_MINUTES
        # The upstream method consumes CGM alone. Announcements are unused.
        # A held CGM value is fed at every interval, as in M1's native PID route.
        action = self.native.policy(
            SimpleNamespace(CGM=observation["glucose_mg_dl"]),
            0,
            False,
            sample_time=STEP_MINUTES,
        )
        if not math.isfinite(action.basal) or action.bolus != 0:
            raise ValueError("Unexpected upstream PID action")
        return {"basal_u_min": min(0.2, max(0.0, action.basal)), "bolus_u_min": 0.0}


def make_controller(seed):
    if type(seed) is not int:
        raise ValueError("Expected an integer scenario seed")
    return PinnedPID()
