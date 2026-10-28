"""Version 1 contracts for the bounded OT-001 simglucose experiment."""

import math
from dataclasses import asdict, dataclass

SCHEMA = "opent1d.simglucose/1"
START = "2024-07-20T00:00:00"
STEP = 3
HORIZON = 2880
WARMUP = 1440
MEALS = tuple(
    (day * 1440 + hour * 60, grams)
    for day in range(2)
    for hour, grams in ((7, 45), (12, 70), (16, 15), (18, 80), (23, 10))
)


def number(value, name, minimum=None):
    if type(value) not in (int, float) or not math.isfinite(value):
        raise ValueError(f"{name} must be a finite number")
    if minimum is not None and value < minimum:
        raise ValueError(f"{name} must be >= {minimum}")
    return value


def minute(value, name):
    if type(value) is not int or value < 0 or value % STEP:
        raise ValueError(f"{name} must be a nonnegative integer multiple of {STEP} minutes")


@dataclass(frozen=True)
class Config:
    profile: str = "adult#001"
    seed: int = 101
    controller: str = "basal_bolus"
    condition: str = "A"
    schema: str = SCHEMA

    def __post_init__(self):
        if self.schema != SCHEMA:
            raise ValueError("Unsupported schema")
        if self.profile not in ("adult#001", "adult#002"):
            raise ValueError("This development demonstration does not enable evaluation profiles")
        if type(self.seed) is not int or self.seed not in range(101, 111):
            raise ValueError("Development seeds must be 101–110")
        if self.controller not in ("basal_bolus", "pid") or self.condition not in (
            "A",
            "B",
            "C",
            "D",
        ):
            raise ValueError("Unsupported controller or condition")

    def to_dict(self):
        return asdict(self)


@dataclass(frozen=True)
class Observation:
    time_min: int
    glucose_mg_dl: float
    source_time_min: int
    available: bool

    def __post_init__(self):
        minute(self.time_min, "time_min")
        minute(self.source_time_min, "source_time_min")
        number(self.glucose_mg_dl, "glucose_mg_dl", 0)
        if self.source_time_min > self.time_min or type(self.available) is not bool:
            raise ValueError("Invalid observation time or availability")
        if self.available != (self.source_time_min == self.time_min):
            raise ValueError("Availability must agree with source time")

    @property
    def age_min(self):
        return self.time_min - self.source_time_min


@dataclass(frozen=True)
class Action:
    """Both fields are rates, including native simglucose's misleading 'bolus'."""

    basal_u_min: float
    bolus_u_min: float

    def __post_init__(self):
        number(self.basal_u_min, "basal_u_min")
        number(self.bolus_u_min, "bolus_u_min")


@dataclass(frozen=True)
class Row:
    """One completed interval; glucose describes (start,end], actions [start,end)."""

    start_min: int
    end_min: int
    glucose_mg_dl: float
    raw_cgm_mg_dl: float
    sensor_available: bool
    controller_cgm_mg_dl: float
    controller_source_min: int
    announced_g: float
    true_meal_g: float
    basal_u_min: float
    bolus_u_min: float
    delivered_u_min: float
    terminal: bool

    def __post_init__(self):
        minute(self.start_min, "start_min")
        minute(self.end_min, "end_min")
        minute(self.controller_source_min, "controller_source_min")
        if self.end_min != self.start_min + STEP or self.end_min > HORIZON:
            raise ValueError("Invalid interval")
        if self.controller_source_min > self.start_min:
            raise ValueError("Future controller observation")
        for key in (
            "glucose_mg_dl",
            "raw_cgm_mg_dl",
            "controller_cgm_mg_dl",
            "announced_g",
            "true_meal_g",
            "delivered_u_min",
        ):
            number(getattr(self, key), key, 0)
        Action(self.basal_u_min, self.bolus_u_min)
        if type(self.sensor_available) is not bool or type(self.terminal) is not bool:
            raise ValueError("Flags must be booleans")


def validate_rows(rows):
    previous = 0
    terminal = False
    for row in rows:
        if not isinstance(row, Row):
            raise ValueError("Expected Row")
        if row.start_min != previous or terminal:
            raise ValueError("Noncontiguous intervals or output after terminal flag")
        previous, terminal = row.end_min, row.terminal
    return previous
