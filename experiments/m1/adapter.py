"""Thin, engine-specific boundary; no equations, solver or native device patches."""

from dataclasses import dataclass
from datetime import datetime

import numpy as np
from simglucose.actuator.pump import InsulinPump
from simglucose.controller.base import Action as NativeAction
from simglucose.patient.t1dpatient import T1DPatient
from simglucose.sensor.cgm import CGMSensor
from simglucose.simulation.env import T1DSimEnv
from simglucose.simulation.scenario import CustomScenario

from .contracts import MEALS, START, STEP, Action, number


def native_number(value, name, minimum=None):
    if isinstance(value, (np.floating, np.integer)):
        value = value.item()
    return number(value, name, minimum)


@dataclass(frozen=True)
class Snapshot:
    time_min: int
    glucose_mg_dl: float
    cgm_mg_dl: float
    true_meal_g: float
    delivered_u_min: float
    terminal: bool


class Simglucose:
    def __init__(self, profile, seed, meals=MEALS):
        self._start = datetime.fromisoformat(START)
        self._env = T1DSimEnv(
            T1DPatient.withName(profile),
            CGMSensor.withName("Dexcom", seed=seed),
            InsulinPump.withName("Insulet"),
            CustomScenario(self._start, [(t / 60, g) for t, g in meals]),
        )
        self._time = None
        self._terminal = False

    def _snapshot(self, result, expected):
        obs, reward, done, info = result
        if info["sample_time"] != STEP or info["time"] != self._env.time:
            raise ValueError("Unexpected native sampling/time")
        elapsed = (info["time"] - self._start).total_seconds() / 60
        if elapsed != expected:
            raise ValueError("Unexpected native time order")
        if not self._env.patient._odesolver.successful():
            raise ValueError("Native solver reported failure")
        state = np.asarray(info["patient_state"])
        if state.shape != (13,) or state.dtype.kind not in "fi" or not np.isfinite(state).all():
            raise ValueError("Invalid native patient state")
        for name in ("bg", "lbgi", "hbgi", "risk", "meal"):
            native_number(info[name], name)
        native_number(obs.CGM, "native CGM", 0)
        native_number(reward, "native reward")
        if not isinstance(done, (bool, np.bool_)):
            raise ValueError("Invalid native terminal flag")
        delivered = (
            native_number(self._env.insulin_hist[-1], "delivered insulin", 0) if expected else 0.0
        )
        number(delivered, "delivered insulin", 0)
        self._time, self._terminal = expected, bool(done)
        return Snapshot(
            expected,
            float(info["bg"]),
            float(obs.CGM),
            float(info["meal"]) * STEP,
            delivered,
            bool(done),
        )

    def reset(self):
        self._time = None
        self._terminal = False
        return self._snapshot(self._env.reset(), 0)

    def step(self, action):
        if self._time is None or self._terminal:
            raise ValueError("Reset before stepping; no steps after terminal state")
        if not isinstance(action, Action):
            raise ValueError("Expected rates in an Action record")
        return self._snapshot(
            self._env.step(NativeAction(action.basal_u_min, action.bolus_u_min)), self._time + STEP
        )

    def native_history(self):
        """Verification/export only; never passed to a controller."""
        return self._env.show_history().copy()
