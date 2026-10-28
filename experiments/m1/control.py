"""OT-001 information boundary around unchanged upstream BB and PID formulas."""

from simglucose.controller.basal_bolus_ctrller import BBController
from simglucose.controller.pid_ctrller import PIDController
from simglucose.simulation.env import Observation as NativeObservation

from .adapter import native_number
from .contracts import MEALS, STEP, WARMUP, Action, Observation, minute, number


def available(condition, time_min):
    return not (condition == "D" and 2160 <= time_min < 2190)


class Information:
    def __init__(self, condition):
        if condition not in ("A", "B", "C", "D"):
            raise ValueError("Unsupported condition")
        self.condition = condition
        self.reset()

    def reset(self):
        self._last = None
        self._last_time = -STEP
        self._announced = set()

    def observe(self, time_min, raw_cgm):
        minute(time_min, "time_min")
        number(raw_cgm, "raw_cgm", 0)  # validate even when masked
        if time_min != self._last_time + STEP:
            raise ValueError("Observation clock must advance once by three minutes")
        self._last_time = time_min
        present = available(self.condition, time_min)
        if present:
            self._last = (time_min, raw_cgm)
        if self._last is None:
            raise ValueError("No initial observation available")
        return Observation(time_min, self._last[1], self._last[0], present)

    def announce(self, time_min):
        if time_min != self._last_time:
            raise ValueError("Announcements must follow the current observation")
        if time_min in self._announced:
            return 0.0
        self._announced.add(time_min)
        fraction = 1 if time_min < WARMUP else {"A": 1, "B": 0, "C": 0.5, "D": 1}[self.condition]
        return float(dict(MEALS).get(time_min, 0) * fraction)


class Controller:
    def __init__(self, config):
        self.profile = config.profile
        self._native = (
            BBController(target=140)
            if config.controller == "basal_bolus"
            else PIDController(P=0.001, I=0.00001, D=0.001, target=140)
        )
        self.reset()

    def reset(self):
        self._native.reset()

    def command(self, observation, announced_g):
        if not isinstance(observation, Observation):
            raise ValueError("Only the allowlisted observation contract is accepted")
        number(announced_g, "announced_g", 0)
        # No latent state, raw masked sensor, reward, native info, or future scenario.
        action = self._native.policy(
            NativeObservation(observation.glucose_mg_dl),
            0,
            False,
            sample_time=STEP,
            patient_name=self.profile,
            meal=announced_g / STEP,
        )
        if isinstance(self._native, PIDController):
            native_number(self._native.integrated_state, "PID integral state")
            native_number(self._native.prev_state, "PID previous observation")
        return Action(
            native_number(action.basal, "basal command"),
            native_number(action.bolus, "bolus command"),
        )
