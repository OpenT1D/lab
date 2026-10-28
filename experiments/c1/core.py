"""Unconfigured causal trend overlay for synthetic controller development.

All rates are U/h. No physiology, sensor, pump or patient object is imported.
"""

import math
from dataclasses import dataclass


def finite(value, name, minimum=None):
    if type(value) not in (int, float) or not math.isfinite(value):
        raise ValueError(f"{name} must be finite")
    if minimum is not None and value < minimum:
        raise ValueError(f"{name} must be >= {minimum}")
    return float(value)


@dataclass(frozen=True)
class Settings:
    """Explicit engineering parameters; none are patient recommendations."""

    target_mg_dl: float
    low_cutoff_mg_dl: float
    rise_gain_u_h_per_mg_dl_min: float
    max_rise_mg_dl_min: float
    max_fresh_gap_min: float
    inventory_half_life_min: float
    inventory_gain_per_h: float
    max_extra_u_h: float
    max_extra_step_u_h: float
    max_total_u_h: float

    def __post_init__(self):
        for name in self.__dataclass_fields__:
            finite(getattr(self, name), name, 0)
        if not self.low_cutoff_mg_dl < self.target_mg_dl:
            raise ValueError("Low cutoff must be below target")
        for name in (
            "max_rise_mg_dl_min",
            "max_fresh_gap_min",
            "inventory_half_life_min",
            "max_extra_u_h",
            "max_extra_step_u_h",
            "max_total_u_h",
        ):
            if getattr(self, name) <= 0:
                raise ValueError(f"{name} must be positive")


@dataclass(frozen=True)
class Decision:
    base_u_h: float
    extra_u_h: float
    final_u_h: float
    inventory_u: float
    rise_mg_dl_min: float
    reason: str


class TrendOverlay:
    """Add bounded basal rate only from a fresh causal glucose rise.

    The inventory is a proxy from own *commanded* extra rate,
    not a physiological insulin-on-board model or measured delivery.
    """

    def __init__(self, settings):
        if not isinstance(settings, Settings):
            raise TypeError("Explicit Settings required")
        self.settings = settings
        self.reset()

    def reset(self):
        self._time = None
        self._fresh = None
        self._extra = 0.0
        self._inventory = 0.0

    def command(self, *, time_min, glucose_mg_dl, source_time_min, available, base_u_h):
        if type(time_min) is not int or time_min < 0:
            raise ValueError("time_min must be a nonnegative integer")
        if type(source_time_min) is not int or source_time_min < 0 or source_time_min > time_min:
            raise ValueError("Invalid observation source time")
        if type(available) is not bool or available != (source_time_min == time_min):
            raise ValueError("Availability must match observation source time")
        glucose = finite(glucose_mg_dl, "glucose_mg_dl", 0)
        base = finite(base_u_h, "base_u_h", 0)
        if base > self.settings.max_total_u_h:
            raise ValueError("Base rate exceeds declared total action limit")
        if self._time is not None and time_min <= self._time:
            raise ValueError("Controller clock must increase")
        if not available and (self._fresh is None or (source_time_min, glucose) != self._fresh):
            raise ValueError("Unavailable observation must hold the last fresh value")

        inventory = self._inventory
        if self._time is not None:
            elapsed = time_min - self._time
            inventory = (
                inventory * 2 ** (-elapsed / self.settings.inventory_half_life_min)
                + self._extra * elapsed / 60
            )
        rise = 0.0
        if available:
            if self._fresh is not None:
                gap = time_min - self._fresh[0]
                if gap <= self.settings.max_fresh_gap_min:
                    rise = min(
                        self.settings.max_rise_mg_dl_min,
                        max(0.0, (glucose - self._fresh[1]) / gap),
                    )
            fresh = (time_min, glucose)
        else:
            fresh = self._fresh

        if not available:
            extra, reason = 0.0, "held_observation"
        elif glucose <= self.settings.low_cutoff_mg_dl:
            extra, reason = 0.0, "low_glucose_gate"
        elif rise == 0:
            extra, reason = 0.0, "no_recent_rise"
        else:
            activation = min(
                1.0,
                max(
                    0.0,
                    (glucose - self.settings.target_mg_dl)
                    / (self.settings.target_mg_dl - self.settings.low_cutoff_mg_dl),
                ),
            )
            proposed = max(
                0.0,
                self.settings.rise_gain_u_h_per_mg_dl_min * rise * activation
                - self.settings.inventory_gain_per_h * inventory,
            )
            extra = min(
                proposed,
                self.settings.max_extra_u_h,
                self.settings.max_total_u_h - base,
                self._extra + self.settings.max_extra_step_u_h,
            )
            reason = "bounded_rise" if extra else "suppressed_rise"

        self._time = time_min
        self._fresh = fresh
        self._extra = extra
        self._inventory = inventory
        return Decision(base, extra, base + extra, inventory, rise, reason)
