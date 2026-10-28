"""Unconfigured, simulator-independent C1 two-sided feedback kernel.

All rates are U/h; glucose is mg/dL and controller time is minutes. These
engineering settings are not selected gains or treatment recommendations.
"""

from dataclasses import dataclass, replace

from experiments.c1.core import finite


def _bounded(value, lower, upper):
    return min(upper, max(lower, finite(value, "intermediate value")))


@dataclass(frozen=True)
class FeedbackSettings:
    target_mg_dl: float
    low_cutoff_mg_dl: float
    kp_u_h_per_mg_dl: float
    ki_u_h_per_mg_dl_min: float
    rise_gain_u_h_per_mg_dl_min: float
    max_rise_mg_dl_min: float
    max_fresh_gap_min: float
    max_abs_integral_mg_dl_min: float
    max_up_correction_step_u_h: float
    max_total_u_h: float

    def __post_init__(self):
        for name in self.__dataclass_fields__:
            finite(getattr(self, name), name, 0)
        if self.low_cutoff_mg_dl >= self.target_mg_dl:
            raise ValueError("Low cutoff must be below target")
        for name in (
            "max_rise_mg_dl_min",
            "max_fresh_gap_min",
            "max_abs_integral_mg_dl_min",
            "max_up_correction_step_u_h",
            "max_total_u_h",
        ):
            if getattr(self, name) <= 0:
                raise ValueError(f"{name} must be positive")


def without_rise(settings):
    """Matched engineering comparator: change only the rise gain."""
    if not isinstance(settings, FeedbackSettings):
        raise TypeError("Explicit FeedbackSettings required")
    return replace(settings, rise_gain_u_h_per_mg_dl_min=0.0)


@dataclass(frozen=True)
class FeedbackDecision:
    base_u_h: float
    raw_total_u_h: float
    requested_total_u_h: float
    final_u_h: float
    correction_u_h: float
    integral_mg_dl_min: float
    rise_mg_dl_min: float
    integral_frozen: bool
    total_clamped: bool
    slew_limited: bool
    reason: str


class FeedbackController:
    """Causal rate correction on a caller-owned native basal base action."""

    def __init__(self, settings):
        if not isinstance(settings, FeedbackSettings):
            raise TypeError("Explicit FeedbackSettings required")
        self.settings = settings
        self.reset()

    def reset(self):
        self._time = None
        self._fresh = None
        self._integral = 0.0
        self._correction = 0.0

    def command(self, *, time_min, glucose_mg_dl, source_time_min, available, base_u_h):
        s = self.settings
        if type(time_min) is not int or time_min < 0:
            raise ValueError("time_min must be a nonnegative integer")
        if type(source_time_min) is not int or not 0 <= source_time_min <= time_min:
            raise ValueError("Invalid observation source time")
        if type(available) is not bool or available != (source_time_min == time_min):
            raise ValueError("Availability must match observation source time")
        glucose = finite(glucose_mg_dl, "glucose_mg_dl", 0)
        base = finite(base_u_h, "base_u_h", 0)
        if base > s.max_total_u_h:
            raise ValueError("Base rate exceeds declared total action limit")
        if self._time is not None and time_min <= self._time:
            raise ValueError("Controller clock must increase")
        if not available and (self._fresh is None or (source_time_min, glucose) != self._fresh):
            raise ValueError("Held observation must equal the last fresh value and source time")

        if not available:
            decision = FeedbackDecision(
                base,
                base,
                base,
                base,
                0.0,
                self._integral,
                0.0,
                False,
                False,
                False,
                "held_base_fallback",
            )
            self._time = time_min
            self._correction = 0.0
            return decision

        dt = 0 if self._time is None else time_min - self._time
        error = finite(glucose - s.target_mg_dl, "glucose error")
        rise = 0.0
        if self._fresh is not None:
            gap = time_min - self._fresh[0]
            if gap <= s.max_fresh_gap_min:
                rise = _bounded((glucose - self._fresh[1]) / gap, 0.0, s.max_rise_mg_dl_min)

        # A fresh low reading removes positive memory, but keeps negative memory.
        prior_integral = (
            min(self._integral, 0.0) if glucose <= s.low_cutoff_mg_dl else self._integral
        )
        trial_integral = prior_integral
        if 0 < dt <= s.max_fresh_gap_min:
            trial_integral = _bounded(
                prior_integral + finite(error * dt, "elapsed glucose error"),
                -s.max_abs_integral_mg_dl_min,
                s.max_abs_integral_mg_dl_min,
            )

        def evaluate(integral):
            raw_correction = finite(
                finite(s.kp_u_h_per_mg_dl * error, "proportional term")
                + finite(s.ki_u_h_per_mg_dl_min * integral, "integral term")
                + finite(s.rise_gain_u_h_per_mg_dl_min * rise, "rise term"),
                "raw correction",
            )
            if glucose <= s.low_cutoff_mg_dl:
                raw_correction = min(raw_correction, 0.0)
            raw_total = finite(base + raw_correction, "raw total rate")
            requested = _bounded(raw_total, 0.0, s.max_total_u_h)
            requested_correction = requested - base
            up_limit = finite(self._correction + s.max_up_correction_step_u_h, "upward slew limit")
            slew_limited = requested_correction > up_limit
            final = _bounded(base + min(requested_correction, up_limit), 0.0, s.max_total_u_h)
            return raw_total, requested, final, slew_limited

        raw, requested, final, slew_limited = evaluate(trial_integral)
        # Conditional integration freezes only when error drives a binding limit
        # farther outward. An opposing error may unwind the stored integral.
        integral_frozen = trial_integral != prior_integral and (
            (raw > s.max_total_u_h and error > 0)
            or (raw < 0 and error < 0)
            or (slew_limited and error > 0)
        )
        integral = prior_integral if integral_frozen else trial_integral
        if integral_frozen:
            raw, requested, final, slew_limited = evaluate(integral)
        correction = finite(final - base, "actual correction")
        reason = "fresh_low_gate" if glucose <= s.low_cutoff_mg_dl else "fresh_feedback"
        decision = FeedbackDecision(
            base,
            raw,
            requested,
            final,
            correction,
            integral,
            rise,
            integral_frozen,
            raw != requested,
            slew_limited,
            reason,
        )
        self._time = time_min
        self._fresh = (time_min, glucose)
        self._integral = integral
        self._correction = correction
        return decision
