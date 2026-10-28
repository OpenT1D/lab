"""Phase-isolated AZT1D CSV conversion; no rights gates or filesystem access."""

import csv
import datetime as dt
import io
import math
import re
from decimal import Decimal, InvalidOperation

from experiments.m3.common import ID, require

from .common import SCHEMA

HEADER = (
    "EventDateTime",
    "DeviceMode",
    "BolusType",
    "Basal",
    "CorrectionDelivered",
    "TotalBolusInsulinDelivered",
    "FoodDelivered",
    "CarbSize",
    "CGM",
)
MIXED_COLUMN = "Readings (CGM / BGM)"
_LOCAL = re.compile(r"[0-9]{4}-[0-9]{2}-[0-9]{2}[ T][0-9]{2}:[0-9]{2}:[0-9]{2}(?:\.[0-9]{1,6})?\Z")
_NUMBER = re.compile(r"[+-]?(?:[0-9]+(?:\.[0-9]*)?|\.[0-9]+)(?:[eE][+-]?[0-9]+)?\Z")
_MISSING = {"", "NA", "N/A"}


def local_time(text):
    """Accept naive local ISO seconds/microseconds, without rounding or timezone inference."""
    require(isinstance(text, str) and _LOCAL.fullmatch(text), "Invalid local timestamp")
    try:
        return dt.datetime.fromisoformat(text)
    except ValueError:
        raise ValueError("Invalid local timestamp") from None


def _elapsed_us(timestamp, origin):
    elapsed = timestamp - origin
    return (elapsed.days * 86400 + elapsed.seconds) * 1_000_000 + elapsed.microseconds


def _positive_bound(value):
    require(type(value) in (int, float), "Invalid status-policy bound")
    try:
        valid = math.isfinite(value) and value > 0
    except OverflowError:
        valid = False
    require(valid, "Invalid status-policy bound")
    return Decimal(str(value))


def _policy(policy):
    require(isinstance(policy, dict), "Explicit CGM status policy required")
    mode = policy.get("numeric_boundary")
    require(mode in ("exclude", "verified_exact"), "Explicit numeric boundary policy required")
    keys = {"numeric_boundary", "reference"}
    if mode == "exclude":
        keys |= {"lower", "upper"}
    require(set(policy) in (keys, keys | {"tokens"}), "Invalid status-policy fields")
    require(
        isinstance(policy.get("reference"), str) and policy["reference"].strip(),
        "Status-policy reference required",
    )
    lower = upper = None
    if mode == "exclude":
        lower, upper = _positive_bound(policy["lower"]), _positive_bound(policy["upper"])
        require(lower < upper, "Invalid status-policy interval")
    tokens = policy.get("tokens", {})
    require(isinstance(tokens, dict) and set(tokens) <= {"LOW", "HIGH"}, "Invalid token policy")
    parsed_tokens = {}
    for token, rule in tokens.items():
        require(
            isinstance(rule, dict) and set(rule) == {"status", "bound"},
            "Invalid token policy",
        )
        expected = "censored_low" if token == "LOW" else "censored_high"
        require(rule["status"] == expected, "Invalid token policy status")
        parsed_tokens[token] = (expected, float(_positive_bound(rule["bound"])))
    return mode, lower, upper, parsed_tokens


def _signal(text, policy):
    """Return status/value/bound plus an exact, transient duplicate-comparison key."""
    stripped = text.strip()
    token = stripped.upper()
    if token in _MISSING:
        return "missing", None, None, ("missing",)
    mode, lower, upper, tokens = policy
    if token in tokens:
        status, bound = tokens[token]
        return status, None, bound, (status, bound)
    if not _NUMBER.fullmatch(stripped):
        return "invalid", None, None, ("invalid_token", token)
    try:
        number = Decimal(stripped)
        value = float(number)
    except (InvalidOperation, ValueError, OverflowError):
        return "invalid", None, None, ("invalid_token", token)
    valid = number.is_finite() and math.isfinite(value) and number > 0 and value > 0
    if valid and mode == "exclude":
        valid = lower < number < upper
    if not valid:
        return "invalid", None, None, ("invalid_number", number)
    return "measured", value, None, ("measured", number)


def convert_csv(
    raw: bytes,
    *,
    person: str,
    origin_local: str,
    start_us: int,
    end_us: int,
    row_start: int,
    row_stop: int,
    policy: dict,
):
    """Convert exactly one frozen half-open block of a native CSV.

    Data-row numbers are 1-based, excluding the header. ``row_stop`` is exclusive.
    Outside this slice only row widths and timestamps are inspected. Every timestamp
    must be nondecreasing and the slice must contain exactly the rows in the declared
    time block, so duplicate groups cannot straddle a slice boundary.

    Policy requires a nonempty ``reference`` and either ``numeric_boundary=exclude``
    with positive ``lower < upper`` (boundary values become invalid), or an explicitly
    reviewed ``numeric_boundary=verified_exact``. Optional ``tokens`` maps ``LOW`` or
    ``HIGH`` to ``{"status": "censored_low"/"censored_high", "bound": number}``.
    Empty/NA/N/A are missing; other unsupported tokens and nonfinite values are invalid.
    No other source columns are interpreted, and mixed CGM/BGM input is unsupported.
    """
    require(type(raw) is bytes, "Native CSV bytes required")
    require(isinstance(person, str) and ID.fullmatch(person), "Invalid person alias")
    require(
        type(start_us) is int and type(end_us) is int and 0 <= start_us < end_us,
        "Invalid elapsed-time bounds",
    )
    require(
        type(row_start) is int and type(row_stop) is int and 1 <= row_start <= row_stop,
        "Invalid native row slice",
    )
    parsed_policy = _policy(policy)
    origin = local_time(origin_local)
    try:
        reader = csv.reader(io.StringIO(raw.decode("utf-8-sig"), newline=""), strict=True)
        header = next(reader, None)
        require(header is not None, "Native CSV header required")
        supported = tuple(header) == HEADER
        mixed = len(header) == len(HEADER) and set(header) == (
            set(HEADER) - {"CGM"} | {MIXED_COLUMN}
        )
        require(supported or mixed, "Unreviewed native CSV schema")
        time_column = header.index("EventDateTime")
        cgm_column = header.index("CGM") if supported else None
        selected = []
        previous = None
        first_in_block = first_after_block = None
        count = 0
        for count, source in enumerate(reader, 1):
            require(len(source) == len(header), "Invalid native CSV row width")
            raw_time = source[time_column]
            time_us = _elapsed_us(local_time(raw_time), origin)
            require(count != 1 or time_us == 0, "Declared origin is not first native timestamp")
            require(time_us >= 0, "Native timestamp precedes declared origin")
            require(previous is None or time_us >= previous, "Native timestamps run backwards")
            previous = time_us
            if first_in_block is None and time_us >= start_us:
                first_in_block = count
            if first_after_block is None and time_us >= end_us:
                first_after_block = count
            if row_start <= count < row_stop:
                # Do not even select the glucose field outside the declared phase.
                selected.append(
                    (count, time_us, raw_time, source[cgm_column] if supported else None)
                )
        require(count > 0, "Native CSV observations required")
        require(row_stop <= count + 1, "Native row slice exceeds input")
        require(
            row_start == (first_in_block if first_in_block is not None else count + 1)
            and row_stop == (first_after_block if first_after_block is not None else count + 1),
            "Native row slice does not match complete time block",
        )
    except (UnicodeError, csv.Error):
        raise ValueError("Invalid native CSV encoding or structure") from None

    rows = []
    prior_key = None
    for source_row, time_us, raw_time, reading in selected:
        if supported:
            status, value, bound, key = _signal(reading, parsed_policy)
        else:
            status, value, bound, key = "unsupported", None, None, ("unsupported",)
        if rows and time_us == rows[-1]["time_us"]:
            rows[-1]["source_rows"].append(source_row)
            if key != prior_key:
                rows[-1].update(status="ambiguous", value=None, bound=None)
        else:
            rows.append(
                {
                    "time_us": time_us,
                    "available_us": time_us,
                    "segment": "local",
                    "raw_time": raw_time,
                    "status": status,
                    "value": value,
                    "bound": bound,
                    "source_rows": [source_row],
                }
            )
            prior_key = key
    return {
        "schema": SCHEMA,
        "person": person,
        "clock": "local_elapsed",
        "unit": "mg/dL",
        "bounds_us": [start_us, end_us],
        "rows": rows,
    }
