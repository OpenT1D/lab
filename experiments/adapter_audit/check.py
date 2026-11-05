"""Check invented audit transcripts against a Decimal oracle, without native code."""

import hashlib
import json
from decimal import Decimal
from pathlib import Path

HERE = Path(__file__).parent
ENGINES = {
    "simglucose": (3, "U/min", "a6f6777586c860457a2a1e6cce6d0bd3fd33d1cc"),
    "lt1_cambridge": (5, "U/h", "9a6092065bd821f88691cd8d03b0550acd665573"),
}


def require(condition, reason):
    if not condition:
        raise ValueError(reason)


def fields(value, names, reason):
    require(isinstance(value, dict) and set(value) == set(names.split()), reason)


def number(value, reason, minimum=None):
    require(type(value) in (int, float), reason)
    result = Decimal(str(value))
    require(result.is_finite() and (minimum is None or result >= minimum), reason)
    return result


def digest(value):
    """Identity of declared fixture inputs, not an authentication mechanism."""
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
    ).hexdigest()


def check_case(case, pins):
    fields(case, "input identity status error rows delivered_u", "case-fields")
    plan = case["input"]
    fields(
        plan,
        "engine step_min horizon_min seed basal_u_h target_mg_dl gain max_u_h "
        "samples actual_events announcements",
        "input-fields",
    )
    require(plan["engine"] in ENGINES, "engine")
    step, unit, revision = ENGINES[plan["engine"]]
    require(type(plan["step_min"]) is int and plan["step_min"] == step, "clock")
    horizon = plan["horizon_min"]
    require(type(horizon) is int and horizon > 0 and horizon % step == 0, "horizon")
    require(type(plan["seed"]) is int and plan["seed"] > 0, "seed")
    require(
        case["identity"]
        == {
            "input_sha256": digest(plan),
            "upstream_revision": revision,
            "runtime_lock_sha256": pins[plan["engine"]]["sha256"],
        },
        "identity",
    )
    basal = number(plan["basal_u_h"], "basal", 0)
    target = number(plan["target_mg_dl"], "target", 0)
    gain = number(plan["gain"], "gain", 0)
    maximum = number(plan["max_u_h"], "maximum", 0)
    require(target == 120 and gain == Decimal("0.01") and maximum == 3, "controller-settings")
    require(basal <= maximum, "basal")
    samples = plan["samples"]
    require(isinstance(samples, list) and samples, "samples")
    last_time = -1
    for sample in samples:
        fields(sample, "measured_min available_min glucose_mg_dl", "sample-fields")
        measured = number(sample["measured_min"], "measurement-time", 0)
        released = number(sample["available_min"], "availability-time", 0)
        require(measured > last_time and measured % step == 0, "measurement-time")
        require(released >= measured, "availability-time")
        number(sample["glucose_mg_dl"], "sample-value", 0)
        last_time = measured
    require(samples[0]["measured_min"] == samples[0]["available_min"] == 0, "initial")
    events = plan["actual_events"]
    require(isinstance(events, list), "events")
    ids = set()
    for event in events:
        fields(event, "id start_min grams", "event-fields")
        require(isinstance(event["id"], str) and event["id"] not in ids, "event-id")
        ids.add(event["id"])
        number(event["start_min"], "event-time", 0)
        number(event["grams"], "event-amount", 0)
    announcements = plan["announcements"]
    require(isinstance(announcements, list), "announcements")
    ids = set()
    for announcement in announcements:
        fields(announcement, "id event_id start_min available_min grams", "announcement-fields")
        require(
            isinstance(announcement["id"], str) and announcement["id"] not in ids,
            "announcement-id",
        )
        ids.add(announcement["id"])
        require(any(e["id"] == announcement["event_id"] for e in events), "announcement-event")
        number(announcement["start_min"], "announcement-time", 0)
        number(announcement["available_min"], "announcement-time", 0)
        number(announcement["grams"], "announcement-amount", 0)

    rows = case["rows"]
    require(isinstance(rows, list) and len(rows) <= horizon // step, "rows")
    status = case["status"]
    require(status in ("completed", "failed", "interrupted", "started"), "status")
    if status == "completed":
        require(len(rows) == horizon // step and case["error"] is None, "completion")
    elif status in ("failed", "interrupted"):
        require(isinstance(case["error"], str) and bool(case["error"]), "failure-reason")
    else:
        require(case["error"] is None, "unfinished")

    previous = target
    source_time = -1
    seen = set()
    total = Decimal(0)
    for index, row in enumerate(rows):
        fields(
            row,
            "time_min observation new_announcements previous_mg_dl command_u_h "
            "native_action delivered_rate interval_end_min",
            "row-fields",
        )
        time = index * step
        require(type(row["time_min"]) is int and row["time_min"] == time, "update-clock")
        released = [s for s in samples if s["available_min"] <= time]
        sample = max(released, key=lambda s: s["measured_min"])
        fresh = sample["measured_min"] > source_time
        observation = row["observation"]
        fields(observation, "measured_min available_min glucose_mg_dl fresh", "causal-observation")
        for key in ("measured_min", "available_min", "glucose_mg_dl"):
            number(observation[key], "causal-observation", 0)
        require(
            type(observation["fresh"]) is bool and observation == {**sample, "fresh": fresh},
            "causal-observation",
        )
        new = [a["id"] for a in announcements if a["available_min"] <= time and a["id"] not in seen]
        require(row["new_announcements"] == new, "announcement-delivery")
        seen.update(new)
        require(number(row["previous_mg_dl"], "controller-state") == previous, "controller-state")
        expected = (
            min(maximum, max(Decimal(0), basal + gain * (previous - target))) if fresh else basal
        )
        require(number(row["command_u_h"], "command", 0) == expected, "controller-order")
        if fresh:
            previous = number(sample["glucose_mg_dl"], "observation", 0)
            source_time = sample["measured_min"]
        action = row["native_action"]
        fields(action, "kind unit rate", "unsupported-action")
        require(action["kind"] == "basal_rate" and action["unit"] == unit, "action-unit")
        require(
            number(action["rate"], "action-rate", 0) * (60 if unit == "U/min" else 1) == expected,
            "rate-conversion",
        )
        end = row["interval_end_min"]
        require(type(end) is int and end == time + step, "interval")
        # These invented controls prescribe delivery separately; this is not a pump model.
        delivered = number(row["delivered_rate"], "delivery", 0)
        total += delivered * step / (60 if unit == "U/h" else 1)
    if rows:
        require(number(case["delivered_u"], "amount", 0) == total, "delivery-amount")
    else:
        require(case["delivered_u"] is None, "undefined-amount")
    return {
        "status": status,
        "completed_intervals": len(rows),
        "observed_minutes": len(rows) * step,
    }


def main():
    raw = (HERE / "cases.json").read_bytes()
    packet = json.loads(raw)
    pins = json.loads((HERE / "pins.json").read_bytes())
    results = {name: check_case(case, pins) for name, case in packet.items()}
    print(json.dumps({"fixture_bytes_sha256": hashlib.sha256(raw).hexdigest(), "cases": results}))


if __name__ == "__main__":
    main()
