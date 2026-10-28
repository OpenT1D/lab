"""Bounded outer loop for development conditions, with completed-step callbacks."""

from .adapter import Simglucose
from .contracts import HORIZON, Row
from .control import Controller, Information, available


def simulate(config, checkpoint, initial, *, engine=None, controller=None):
    engine = engine if engine is not None else Simglucose(config.profile, config.seed)
    controller = controller if controller is not None else Controller(config)
    information = Information(config.condition)
    controller.reset()
    snap = engine.reset()
    initial(snap)
    observation = information.observe(0, snap.cgm_mg_dl)
    while snap.time_min < HORIZON and not snap.terminal:
        announced = information.announce(snap.time_min)
        action = controller.command(observation, announced)
        next_snap = engine.step(action)
        row = Row(
            snap.time_min,
            next_snap.time_min,
            next_snap.glucose_mg_dl,
            next_snap.cgm_mg_dl,
            available(config.condition, next_snap.time_min),
            observation.glucose_mg_dl,
            observation.source_time_min,
            announced,
            next_snap.true_meal_g,
            action.basal_u_min,
            action.bolus_u_min,
            next_snap.delivered_u_min,
            next_snap.terminal,
        )
        checkpoint(row)
        snap = next_snap
        observation = information.observe(snap.time_min, snap.cgm_mg_dl)
    return "terminated" if snap.terminal else "completed"
