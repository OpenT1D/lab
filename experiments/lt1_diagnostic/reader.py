"""Trusted fractional-grid data reader; neither native execution nor parity admission."""

import argparse
import hashlib
import json
import re
from decimal import Decimal
from fractions import Fraction
from pathlib import Path

from experiments.m1.artifacts import strict_json
from experiments.m3.researcher.intake import read_regular
from experiments.m4.initial_load.common import source_closure

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).parent
HORIZON, STEP, MINUTE = 1_800_000, 300_000, 60_000
REVISION = "9a6092065bd821f88691cd8d03b0550acd665573"
STATE = "Q1 Q2 S1 S2 I x1 x2 x3 D1 D2"
SCHEMA = "opent1d.lt1-diagnostic-trace/1"
RUNTIME_SHA256 = "c9e1dbc748b33ed2d14f42445191ecaf14c56259c7a9a26d0042c49ec2b66428"


def require(condition, reason):
    if not condition:
        raise ValueError(reason)


def fields(value, names):
    require(isinstance(value, dict) and set(value) == set(names.split()), "fields")


def number(value, low=0, high=None):
    require(type(value) in (int, float, Decimal), "number")
    value = Decimal(str(value))
    require(value.is_finite(), "number")
    require((low is None or value >= low) and (high is None or value <= high), "number")
    return value


def clock(value, high=HORIZON):
    require(type(value) is int and 0 <= value <= high, "clock")
    return value


def decode(raw):
    # Reuse strict duplicate-key/nonfinite/overflow rejection; preserve recorded
    # decimal values for independent exact interval integration below.
    strict_json(raw)
    return json.loads(raw, parse_float=Decimal)


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def implementation():
    paths = {
        "experiments/lt1_diagnostic/reader.py",
        "experiments/lt1_diagnostic/__init__.py",
        "experiments/lt1_diagnostic/protocol.mjs",
        "experiments/lt1_diagnostic/wrapped.mjs",
        "experiments/lt1_diagnostic/direct.mjs",
        "experiments/adapter_audit/lt1_sampled.mjs",
        "experiments/m0/lt1/record.mjs",
        "experiments/m0/lt1/package-lock.json",
        "experiments/adapter_audit/lt1-candidate-review.json",
    }
    while True:
        paths = set(source_closure(paths))
        parents = {
            (parent / "__init__.py").as_posix()
            for name in paths
            for parent in Path(name).parents
            if parent.parts and (ROOT / parent / "__init__.py").is_file()
        }
        if parents <= paths:
            break
        paths.update(parents)
    return {name: digest((ROOT / name).read_bytes()) for name in sorted(paths)}


def identity(plan_raw):
    return {
        "source_revision": REVISION,
        "runtime_candidate": "lt1-cambridge-audit1-node22.23.4-darwin-arm64-preparation-1",
        "selected_runtime_artifact_sha256": RUNTIME_SHA256,
        "plan_bytes_sha256": digest(plan_raw),
        "implementation_sha256": implementation(),
    }


def validate_plan(p):
    fields(
        p,
        "schema engine source_revision seed horizon_ms basal_u_h meals announcements release_rules",
    )
    require(
        p["schema"] == "opent1d.lt1-diagnostic-plan/1"
        and p["engine"] == "lt1_cambridge"
        and p["source_revision"] == REVISION
        and type(p["seed"]) is int
        and p["seed"] == 101
        and type(p["horizon_ms"]) is int
        and p["horizon_ms"] == HORIZON,
        "identity",
    )
    number(p["basal_u_h"], 0, 3)
    for name, maximum in (("meals", 1), ("announcements", 1), ("release_rules", 7)):
        require(isinstance(p[name], list) and len(p[name]) <= maximum, "scope")
    for item in p["meals"]:
        fields(item, "id start_ms duration_ms grams")
        identifier(item["id"])
        clock(item["start_ms"])
        duration = clock(item["duration_ms"])
        require(
            duration >= MINUTE
            and (duration / MINUTE) * MINUTE == duration
            and item["start_ms"] + duration <= HORIZON,
            "native-duration",
        )
        number(item["grams"])
    for a in p["announcements"]:
        fields(a, "id event_id start_ms available_ms grams")
        identifier(a["id"])
        require(any(m["id"] == a["event_id"] for m in p["meals"]), "announcement-event")
        clock(a["start_ms"])
        require(clock(a["available_ms"], HORIZON - STEP) % STEP == 0, "announcement-clock")
        number(a["grams"])
    seen = set()
    for rule in p["release_rules"]:
        fields(rule, "measured_ms available_ms")
        measured, available = rule["measured_ms"], rule["available_ms"]
        require(clock(measured) % STEP == 0 and measured not in seen, "release-clock")
        seen.add(measured)
        if available is not None:
            require(clock(available, HORIZON + STEP) >= measured, "release-clock")
        require(measured != 0 or available == 0, "initial-release")
    return p


def identifier(value):
    require(isinstance(value, str) and re.fullmatch(r"[a-z][a-z0-9-]{0,63}", value), "id")


def native_grid(plan):
    stops = [a["available_ms"] for a in plan["announcements"]]
    for meal in plan["meals"]:
        stops.extend((meal["start_ms"], meal["start_ms"] + meal["duration_ms"]))
    result = [0]
    while result[-1] < HORIZON:
        t = result[-1]
        result.append(min(t + MINUTE, (t // STEP + 1) * STEP, *[s for s in stops if s > t]))
    return result


def validate(packet, plan):
    fields(
        packet,
        "schema kind identity mode status primary_error diagnostic_error rows diagnostic_tail",
    )
    require(packet["schema"] == SCHEMA, "schema")
    require(packet["kind"] in ("invented", "native-unadmitted"), "unadmitted-data-only")
    require(packet["mode"] in ("direct", "wrapped"), "mode")
    status = packet["status"]
    require(status in ("completed", "failed", "interrupted", "started"), "status")
    errors = (packet["primary_error"], packet["diagnostic_error"])
    for error in errors:
        require(error is None or (isinstance(error, str) and 0 < len(error) <= 4096), "error")
    rows, tail = packet["rows"], packet["diagnostic_tail"]
    require(isinstance(rows, list) and len(rows) <= 128, "rows")
    require(isinstance(tail, list) and len(tail) <= 1, "diagnostic-tail")
    grid = native_grid(plan)
    if status == "completed":
        require(len(rows) == len(grid) and errors == (None, None) and not tail, "completion")
    elif status in ("failed", "interrupted"):
        require(any(error is not None for error in errors), "failure-reason")
    else:
        require(errors == (None, None), "unfinished")
    rules = {r["measured_ms"]: r["available_ms"] for r in plan["release_rules"]}
    generated, announced = [], set()
    previous, source, last, next_tick = Decimal(120), None, None, 0
    command, delivered, amount = number(plan["basal_u_h"]), None, Fraction(0)
    for index, row in enumerate(rows):
        fields(
            row,
            "time_ms state plasma_mg_dl raw_cgm_mg_dl command_u_h delivered_u_h "
            "intake_g_min meal_g transition memory",
        )
        time = clock(row["time_ms"])
        require(index < len(grid) and time == grid[index], "native-grid")
        fields(row["state"], STATE)
        for value in row["state"].values():
            number(value, None)
        number(row["plasma_mg_dl"])
        if time % STEP == 0:
            number(row["raw_cgm_mg_dl"])
            require(row["raw_cgm_mg_dl"] == row["plasma_mg_dl"], "raw-sensor")
            generated.append(
                {
                    "measured_ms": time,
                    "available_ms": rules.get(time, time),
                    "glucose_mg_dl": row["raw_cgm_mg_dl"],
                }
            )
        else:
            require(row["raw_cgm_mg_dl"] is None, "raw-cadence")
        if time % STEP == 0 and time < HORIZON:
            eligible = [
                s for s in generated if s["available_ms"] is not None and s["available_ms"] <= time
            ]
            require(bool(eligible), "initial-observation")
            selected = max(eligible, key=lambda s: s["measured_ms"])
            fresh = source is None or selected["measured_ms"] > source
            transition = row["transition"]
            fields(transition, "observation fresh memory_before_mg_dl new_announcements")
            fields(transition["observation"], "measured_ms available_ms glucose_mg_dl")
            clock(transition["observation"]["measured_ms"])
            clock(transition["observation"]["available_ms"], HORIZON + STEP)
            number(transition["observation"]["glucose_mg_dl"])
            require(
                type(transition["fresh"]) is bool
                and transition["fresh"] == fresh
                and transition["observation"] == selected,
                "causal-observation",
            )
            require(number(transition["memory_before_mg_dl"]) == previous, "controller-order")
            # Independent binary64 oracle matching the selected one-multiply/one-add order.
            command = (
                Decimal(
                    str(
                        min(
                            3.0, max(0.0, float(plan["basal_u_h"]) + 0.01 * (float(previous) - 120))
                        )
                    )
                )
                if fresh
                else number(plan["basal_u_h"])
            )
            ids = [
                a["id"]
                for a in plan["announcements"]
                if a["available_ms"] <= time and a["id"] not in announced
            ]
            require(transition["new_announcements"] == ids, "announcement-delivery")
            announced.update(ids)
            if fresh:
                previous, source, last = (
                    selected["glucose_mg_dl"],
                    selected["measured_ms"],
                    selected,
                )
            next_tick += STEP
        else:
            require(row["transition"] is None, "non-tick-transition")
        fields(row["memory"], "previous_mg_dl source_ms last_sample next_tick_ms")
        memory = row["memory"]
        number(memory["previous_mg_dl"])
        if memory["source_ms"] is not None:
            clock(memory["source_ms"])
        clock(memory["next_tick_ms"])
        if memory["last_sample"] is not None:
            fields(memory["last_sample"], "measured_ms available_ms glucose_mg_dl")
            clock(memory["last_sample"]["measured_ms"])
            clock(memory["last_sample"]["available_ms"], HORIZON + STEP)
            number(memory["last_sample"]["glucose_mg_dl"])
        require(
            memory
            == {
                "previous_mg_dl": previous,
                "source_ms": source,
                "last_sample": last,
                "next_tick_ms": next_tick,
            },
            "controller-state",
        )
        require(number(row["command_u_h"], 0, 3) == command, "controller-command")
        rate = number(row["delivered_u_h"], 0, 30)
        if index:
            amount += Fraction(delivered) * Fraction(time - rows[index - 1]["time_ms"], 3_600_000)
        delivered = rate
        expected_meal = sum(float(m["grams"]) for m in plan["meals"] if m["start_ms"] == time)
        intake = sum(
            float(m["grams"]) / (m["duration_ms"] / MINUTE)
            for m in plan["meals"]
            if m["start_ms"] <= time < m["start_ms"] + m["duration_ms"]
        )
        require(
            number(row["meal_g"]) == Decimal(str(expected_meal))
            and number(row["intake_g_min"]) == Decimal(str(intake)),
            "actual-meal",
        )
    return {
        "kind": packet["kind"],
        "mode": packet["mode"],
        "status": status,
        "native_acceptance": False,
        "native_execution_authorized": False,
        "native_callbacks": len(rows),
        "sampled_updates": next_tick // STEP,
        "completed_intervals": max(0, len(rows) - 1),
        "observed_duration_ms": rows[-1]["time_ms"] if rows else 0,
        "modeled_delivered_u": {"numerator": amount.numerator, "denominator": amount.denominator}
        if len(rows) >= 2
        else None,
        "diagnostic_tail_records": len(tail),
        "primary_error": errors[0],
        "diagnostic_error": errors[1],
    }


def _load(packet_path, plan_path, expected_sha256):
    """Expected packet hash must come from a trusted external inventory, not its producer."""
    raw = read_regular(packet_path, 16 * 1024 * 1024, "LT1 diagnostic packet")
    require(
        isinstance(expected_sha256, str)
        and re.fullmatch(r"[0-9a-f]{64}", expected_sha256)
        and digest(raw) == expected_sha256,
        "packet-identity",
    )
    plan_raw = read_regular(plan_path, 65536, "LT1 diagnostic plan")
    plan, packet = validate_plan(decode(plan_raw)), decode(raw)
    require(
        isinstance(packet, dict) and packet.get("identity") == identity(plan_raw), "source-identity"
    )
    result = validate(packet, plan)
    return packet, {
        **result,
        "packet_bytes_sha256": digest(raw),
        "plan_bytes_sha256": digest(plan_raw),
    }


def inspect(packet_path, plan_path, expected_sha256):
    return _load(packet_path, plan_path, expected_sha256)[1]


def compare(direct, wrapped, plan_path, direct_sha256, wrapped_sha256):
    """Exact scientific-value comparison of the same bytes each reader consumed."""
    a, left = _load(direct, plan_path, direct_sha256)
    b, right = _load(wrapped, plan_path, wrapped_sha256)
    require(a["mode"] == "direct" and b["mode"] == "wrapped", "pair-mode")
    require(a["kind"] == b["kind"], "pair-kind")
    require(a["identity"] == b["identity"], "pair-identity")
    require(a["rows"] == b["rows"] and a["status"] == b["status"], "scientific-difference")
    return {
        "exact_scientific_rows": True,
        "tolerance_applied": False,
        "native_acceptance": False,
        "direct": left,
        "wrapped": right,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("packet", type=Path)
    parser.add_argument("--plan", type=Path, required=True)
    parser.add_argument("--expected-sha256", required=True)
    args = parser.parse_args()
    print(json.dumps(inspect(args.packet, args.plan, args.expected_sha256), sort_keys=True))


if __name__ == "__main__":
    main()
