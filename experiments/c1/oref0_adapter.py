"""Simulator-free boundaries for an oref0 temp-only M1 feasibility probe.

Pump receipts are deliberately separate from M1 controller actions.  The
current C1 information contract exposes the latter, not confirmed delivery.
"""

import math
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from experiments.m1.contracts import START, STEP, Action


def _nonnegative(value, name):
    if type(value) not in (int, float) or not math.isfinite(value) or value < 0:
        raise ValueError(f"{name} must be a finite nonnegative number")
    return float(value)


def _minute(value, name):
    if type(value) is not int or value < 0:
        raise ValueError(f"{name} must be a nonnegative integer minute")


def _timestamp(minute):
    _minute(minute, "minute")
    start = datetime.fromisoformat(START).replace(tzinfo=UTC)
    return (start + timedelta(minutes=minute)).isoformat()


@dataclass(frozen=True)
class PriorCommand:
    """Known M1 command for a completed three-minute interval, not delivery."""

    start_min: int
    action: Action

    def __post_init__(self):
        _minute(self.start_min, "start_min")
        if self.start_min % STEP or not isinstance(self.action, Action):
            raise ValueError("Expected an M1-grid start and Action")


class CommandHistory:
    def __init__(self):
        self._commands = []

    def append(self, command, *, decision_min):
        if not isinstance(command, PriorCommand):
            raise ValueError("Expected PriorCommand, not native Row or delivery")
        _minute(decision_min, "decision_min")
        if decision_min != command.start_min + STEP:
            raise ValueError("The command must be completed before its receipt is visible")
        if self._commands and command.start_min != self._commands[-1].start_min + STEP:
            raise ValueError("Command history must be contiguous")
        if not self._commands and command.start_min != 0:
            raise ValueError("Command history must start at reset")
        self._commands.append(command)

    def prior(self, decision_min):
        _minute(decision_min, "decision_min")
        if decision_min % STEP:
            raise ValueError("M1 decision must be on its three-minute grid")
        if any(item.start_min + STEP > decision_min for item in self._commands):
            raise ValueError("Future command in history")
        return tuple(self._commands)

    def reset(self):
        self._commands.clear()


@dataclass(frozen=True)
class PumpBolusReceipt:
    """Confirmed historical amount; no M1 controller route supplies this yet."""

    minute: int
    amount_u: float

    def __post_init__(self):
        _minute(self.minute, "minute")
        _nonnegative(self.amount_u, "amount_u")


@dataclass(frozen=True)
class PumpTempReceipt:
    """Confirmed historical absolute temp rate and duration, not a request."""

    minute: int
    rate_u_h: float
    duration_min: int

    def __post_init__(self):
        _minute(self.minute, "minute")
        _nonnegative(self.rate_u_h, "rate_u_h")
        if type(self.duration_min) is not int or self.duration_min <= 0:
            raise ValueError("duration_min must be a positive integer")


def pump_history(receipts, *, decision_min):
    """Serialize only explicit past pump receipts for source-native IOB.

    `oref0` expects newest-first pump events and a zoned clock. A temp basal
    is paired with its duration event as required by lib/iob/history.js.
    """
    _minute(decision_min, "decision_min")
    events = []
    seen = set()
    for receipt in receipts:
        if isinstance(receipt, PumpBolusReceipt):
            if receipt.minute > decision_min:
                raise ValueError("Future pump bolus")
            key = ("bolus", receipt.minute)
            records = [
                {
                    "_type": "Bolus",
                    "amount": receipt.amount_u,
                    "timestamp": _timestamp(receipt.minute),
                }
            ]
        elif isinstance(receipt, PumpTempReceipt):
            if receipt.minute + receipt.duration_min > decision_min:
                raise ValueError("Uncompleted pump temp is not a historical receipt")
            key = ("temp", receipt.minute)
            stamp = _timestamp(receipt.minute)
            records = [
                {
                    "_type": "TempBasalDuration",
                    "duration (min)": receipt.duration_min,
                    "timestamp": stamp,
                },
                {
                    "_type": "TempBasal",
                    "rate": receipt.rate_u_h,
                    "temp": "absolute",
                    "timestamp": stamp,
                },
            ]
        else:
            raise ValueError("Expected explicit pump receipt; M1 command is not delivery")
        if key in seen:
            raise ValueError("Duplicate pump receipt")
        seen.add(key)
        events.extend((receipt.minute, record) for record in records)
    return [record for _, record in sorted(events, key=lambda item: item[0], reverse=True)]


class TempBasalProjection:
    """Exact rate projection only where no source transition splits an M1 step."""

    def __init__(self, scheduled_u_h):
        self.scheduled_u_h = _nonnegative(scheduled_u_h, "scheduled_u_h")
        self._temp = None
        self._changes = []
        self._last_decision = -1

    def reset(self):
        self._temp = None
        self._changes.clear()
        self._last_decision = -1

    def currenttemp(self, minute):
        _minute(minute, "minute")
        if minute < self._last_decision:
            raise ValueError("Cannot query a past temp state after a later decision")
        if self._temp is None or minute >= self._temp[2]:
            return {"duration": 0, "rate": 0}
        return {"duration": self._temp[2] - minute, "rate": self._temp[0]}

    def accept(self, minute, suggestion):
        """Apply a source suggestion (set, cancel, or omitted/no-op)."""
        _minute(minute, "minute")
        if minute <= self._last_decision:
            raise ValueError("Source decisions must advance in time")
        if type(suggestion) is not dict:
            raise ValueError("Expected source suggestion object")
        has_duration = "duration" in suggestion
        has_rate = "rate" in suggestion
        if has_duration != has_rate:
            raise ValueError("Duration and rate must be provided together")
        if has_duration:
            duration = suggestion["duration"]
            if type(duration) is not int or duration < 0:
                raise ValueError("Invalid temp duration")
            rate = _nonnegative(suggestion["rate"], "rate")
            if minute % STEP:
                raise ValueError("Source temp change inside an M1 interval")
            if duration == 0:
                if rate != 0:
                    raise ValueError("Cancellation must use zero rate")
                self._temp = None
            else:
                self._temp = (rate, minute, minute + duration)
            self._changes.append(minute)
        self._last_decision = minute

    def action_for_m1(self, start_min):
        """Translate U/hour to U/min, rejecting split intervals."""
        _minute(start_min, "start_min")
        if start_min % STEP:
            raise ValueError("M1 command must start on a three-minute grid")
        end = start_min + STEP
        if any(start_min < change < end for change in self._changes):
            raise ValueError("Source decision inside an M1 interval")
        if start_min < self._last_decision:
            raise ValueError("Cannot project an interval before the latest decision")
        if self._temp is not None and start_min < self._temp[2] < end:
            raise ValueError("Temp expiration inside an M1 interval")
        current = self.currenttemp(start_min)
        rate = current["rate"] if current["duration"] else self.scheduled_u_h
        return Action(rate / 60, 0.0)


def source_decision_on_m1_grid(minute):
    """A five-minute oref0 decision is directly representable only every 15m."""
    _minute(minute, "minute")
    if minute % 5:
        raise ValueError("Expected a five-minute source decision")
    return minute % STEP == 0
