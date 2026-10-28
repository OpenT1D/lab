"""Independent SC oracle checks for saved LIT-002 native cases (standard library).

Native whole-body amounts are divided by the recorded body weight before being
compared with independently propagated normalized SC equations. The native
balance-derived absorbed field is an algebraic diagnostic, not an independent
conservation measurement or an independently integrated solver state.
"""

from __future__ import annotations

import json
from math import fsum, isfinite
from pathlib import Path

from experiments.literature.lit002.kinetics import SCParameters, simulate, steady_state

STATE_KEYS = {"Q1", "Q2", "S1", "S2", "I", "x1", "x2", "x3", "D1", "D2"}
ROW_KEYS = {
    "time_min",
    "glucose_mg_dl",
    "insulin_mU_L",
    "appearance_mU_min",
    "delivered_u_h",
    "delayed_delivered_u_h",
    "intake_g_min",
    "depot_mU",
    "delay_queue_mU",
    "total_subcutaneous_mU",
    "cumulative_delivered_mU",
    "cumulative_delayed_delivered_mU",
    "cumulative_carbohydrates_g",
    "balance_derived_absorbed_mU",
    "state",
}


def _number(value: object, name: str, *, positive: bool = False) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not isfinite(value):
        raise ValueError(f"{name} must be a finite number")
    if positive and value <= 0:
        raise ValueError(f"{name} must be positive")
    return float(value)


def _read(path: Path) -> dict:
    value = json.loads(path.read_text())
    if not isinstance(value, dict):
        raise ValueError(f"Expected an object: {path.name}")
    return value


def _milliseconds(value: float) -> int:
    value = _number(value, "time")
    result = round(value * 60000)
    if value < 0 or abs(result - value * 60000) > 1e-7:
        raise ValueError("Times must be nonnegative and exactly representable in milliseconds")
    return result


def _expected_times(config: dict) -> list[float]:
    horizon = _milliseconds(config["horizon_min"])
    step = _milliseconds(config["sample_step_min"])
    if not step or not horizon:
        raise ValueError("Horizon and output step must be positive")
    delay = _milliseconds(config["absorption"]["tau_min"])
    times = {0, horizon, *range(0, horizon + 1, step)}
    # The same union of events is recorded for every arm, including source delay.
    for segment in config["insulin_segments"]:
        for key in ("start_min", "end_min"):
            time = _milliseconds(segment[key])
            times.add(time)
            if time + delay <= horizon:
                times.add(time + delay)
    for meal in config["meals"]:
        times.add(_milliseconds(meal["start_min"]))
        times.add(_milliseconds(meal["start_min"] + meal["duration_min"]))
    if min(times) < 0 or max(times) > horizon:
        raise ValueError("A scheduled event lies outside the horizon")
    return [time / 60000 for time in sorted(times)]


def _schedule(config: dict, basal_u_h: float, weight: float) -> list[tuple[float, float]]:
    knots = {0.0}
    for segment in config["insulin_segments"]:
        start, end, extra = (segment[key] for key in ("start_min", "end_min", "extra_u_h"))
        for value in (start, end, extra):
            if _number(value, "insulin segment") < 0:
                raise ValueError("Insulin segments must be nonnegative")
        if end <= start or end > config["horizon_min"]:
            raise ValueError("Invalid insulin segment interval")
        knots.update((start, end))
    return [
        (
            time,
            (
                basal_u_h
                + fsum(
                    segment["extra_u_h"]
                    for segment in config["insulin_segments"]
                    if segment["start_min"] <= time < segment["end_min"]
                )
            )
            * 1000
            / 60
            / weight,
        )
        for time in sorted(knots)
    ]


def _amount(config: dict, basal_u_h: float, start: float, end: float) -> float:
    return (
        (
            basal_u_h * (end - start)
            + fsum(
                max(0, min(end, segment["end_min"]) - max(start, segment["start_min"]))
                * segment["extra_u_h"]
                for segment in config["insulin_segments"]
            )
        )
        * 1000
        / 60
    )


def verify_case(case_dir: Path, protocol: dict) -> dict:
    """Verify a complete saved case; malformed or incomplete artifacts fail closed.

    Tolerance failures return metrics and false checks. Structural/finite-value
    errors raise ValueError so the enclosing runner can preserve the failure.
    No upstream runtime, native simulator or scientific Python package is used.
    """
    config, runtime, result = (
        _read(case_dir / name) for name in ("config.json", "runtime.json", "result.json")
    )
    if result.get("status") != "completed":
        raise ValueError("Native result is not completed; partial traces cannot pass verification")
    settings = runtime["settings"]
    weight = _number(settings["native_parameters"]["BW"], "native BW", positive=True)
    basal = _number(settings["basal_u_h"], "basal_u_h", positive=True)
    arm = config["arm"]
    if arm not in protocol["arms"] or settings["arm"] != arm:
        raise ValueError("Unsupported or inconsistent native arm")
    for key in (
        "horizon_min",
        "sample_step_min",
        "relative_tolerance",
        "equilibrium_glucose_mg_dl",
    ):
        if config[key] != protocol[key]:
            raise ValueError(f"Configuration differs from frozen protocol: {key}")
    if config["max_step_min"] not in (
        protocol["max_step_min"],
        protocol["refinement_max_step_min"],
    ):
        raise ValueError("Unregistered numerical resolution")
    if config["absorption"] != protocol["absorption"]:
        raise ValueError("Absorption parameters differ from the frozen specification")
    if settings["absorption_parameters"] != config["absorption"]:
        raise ValueError("Runtime absorption parameters differ from the saved configuration")
    if runtime["upstream_revision"] != protocol["native_revision"]:
        raise ValueError("Unregistered native revision")
    if not any(
        config["insulin_segments"] == scenario["insulin_segments"]
        and config["meals"] == scenario["meals"]
        for scenario in protocol["scenarios"]
    ):
        raise ValueError("Unregistered input scenario")
    a = config["absorption"]
    source = SCParameters(a["ka1_per_min"], a["kd_per_min"], a["ka2_per_min"], a["tau_min"])
    if arm == "faggionato_sc":
        parameters = source
    else:
        tmax = _number(settings["native_parameters"]["tmaxI"], "native tmaxI", positive=True)
        parameters = SCParameters(0, 1 / tmax, 1 / tmax)
        if arm == "cambridge_mean_matched" and abs(2 * tmax - source.mean_appearance_min) > 1e-10:
            raise ValueError("Serial comparator does not match the frozen mean appearance time")
    rows = []
    for line in (case_dir / "trace.jsonl").read_text().splitlines():
        row = json.loads(line)
        if not isinstance(row, dict) or set(row) != ROW_KEYS:
            raise ValueError("Unexpected native trace row shape")
        if not isinstance(row["state"], dict) or set(row["state"]) != STATE_KEYS:
            raise ValueError("Unexpected native state shape")
        for key, value in row.items():
            if key != "state":
                _number(value, key)
        for key, value in row["state"].items():
            _number(value, f"state.{key}")
        rows.append(row)
    times = [row["time_min"] for row in rows]
    if times != _expected_times(config):
        raise ValueError("Trace timestamps differ from the complete frozen sample/event grid")
    if result.get("rows") != len(rows) or result.get("final_minute") != config["horizon_min"]:
        raise ValueError("Result row count or horizon disagrees with the completed trace")
    schedule = _schedule(config, basal, weight)
    prior = basal * 1000 / 60 / weight
    oracle = simulate(times, schedule, prior, parameters)
    initial_sc = steady_state(prior, parameters)
    initial_total = fsum((*initial_sc, prior * parameters.delay_min))
    criteria = protocol["criteria"]
    input_tol = criteria["input_amount_relative_tolerance"]
    errors = {"state": [], "appearance": [], "mass": [], "input": [], "absorbed": []}
    nonnegative = True
    derived_consistent = True
    input_rates_consistent = True
    for row, expected in zip(rows, oracle):
        state, time = row["state"], row["time_min"]
        errors["state"].extend(
            (
                abs(state["S1"] / weight - expected.sc1),
                abs(state["S2"] / weight - expected.sc2),
                abs(row["delay_queue_mU"] / weight - expected.delay_inventory),
            )
        )
        errors["appearance"].append(abs(row["appearance_mU_min"] / weight - expected.appearance))
        errors["mass"].append(
            abs(expected.balance_residual) / max(1.0, initial_total + expected.cumulative_delivered)
        )
        errors["input"].append(
            abs(row["cumulative_delivered_mU"] / weight - expected.cumulative_delivered)
            / max(1.0, expected.cumulative_delivered)
        )
        errors["absorbed"].append(
            abs(row["balance_derived_absorbed_mU"] / weight - expected.cumulative_absorbed)
        )
        nonnegative &= (
            min((*state.values(), *(value for key, value in row.items() if key != "state")))
            >= -criteria["negative_state_tolerance"]
        )
        minute_ms = _milliseconds(time)
        delay_ms = _milliseconds(parameters.delay_min)

        def delivered_rate(at_ms: int) -> float:
            return basal + fsum(
                segment["extra_u_h"]
                for segment in config["insulin_segments"]
                if _milliseconds(segment["start_min"]) <= at_ms < _milliseconds(segment["end_min"])
            )

        declared = {
            "delivered_u_h": delivered_rate(minute_ms),
            "delayed_delivered_u_h": delivered_rate(minute_ms - delay_ms),
            "intake_g_min": fsum(
                meal["grams"] / meal["duration_min"]
                for meal in config["meals"]
                if _milliseconds(meal["start_min"])
                <= minute_ms
                < _milliseconds(meal["start_min"] + meal["duration_min"])
            ),
            "cumulative_carbohydrates_g": fsum(
                max(0, min(time, meal["start_min"] + meal["duration_min"]) - meal["start_min"])
                * meal["grams"]
                / meal["duration_min"]
                for meal in config["meals"]
            ),
        }
        input_rates_consistent &= all(
            abs(row[key] - value) <= input_tol * max(1.0, abs(value))
            for key, value in declared.items()
        )
        delayed_total = _amount(config, basal, -parameters.delay_min, time - parameters.delay_min)
        derived = {
            "depot_mU": state["S1"] + state["S2"],
            "total_subcutaneous_mU": state["S1"] + state["S2"] + row["delay_queue_mU"],
            "insulin_mU_L": state["I"],
            "cumulative_delayed_delivered_mU": delayed_total,
            "balance_derived_absorbed_mU": delayed_total
            - state["S1"]
            - state["S2"]
            + settings["initial_state"]["S1"]
            + settings["initial_state"]["S2"],
        }
        derived_consistent &= all(
            abs(row[key] - value) <= input_tol * max(1.0, abs(value))
            for key, value in derived.items()
        )
    max_state = max(errors["state"])
    max_appearance = max(errors["appearance"])
    max_relative_mass = max(errors["mass"])
    checks = {
        "native_completed": True,
        "complete_sample_and_event_grid": True,
        "finite_native_states_and_outputs": True,
        "nonnegative_native_states_and_outputs": nonnegative,
        "sc_states_and_delay_inventory_match_independent_oracle": max_state
        <= criteria["max_sc_state_error_mU_per_kg"],
        "appearance_matches_independent_oracle": max_appearance
        <= criteria["max_appearance_error_mU_per_kg_min"],
        "oracle_mass_accounting_including_prior_delay_inventory": max_relative_mass
        <= criteria["relative_mass_tolerance"],
        "delivered_amount_matches_declared_schedule": max(errors["input"]) <= input_tol,
        "instantaneous_inputs_and_cumulative_carbs_match_schedule": input_rates_consistent,
        "native_derived_columns_are_algebraically_consistent": derived_consistent,
    }
    return {
        "checks": checks,
        "max_sc_state_error_mU_per_kg": max_state,
        "max_appearance_error_mU_per_kg_min": max_appearance,
        "max_mass_residual_mU_per_kg": max(abs(sample.balance_residual) for sample in oracle),
        "max_relative_mass_residual": max_relative_mass,
        "max_relative_delivered_amount_error": max(errors["input"]),
        "max_balance_derived_absorbed_error_mU_per_kg": max(errors["absorbed"]),
        "row_count": len(rows),
        "body_weight_kg": weight,
        "oracle": (
            "Independent stdlib exact two-depot propagation with exact delay boundaries "
            "and basal prehistory"
        ),
        "mass_scope": (
            "Oracle accounting is independent of native states; native absorbed amount "
            "is balance-derived, not independently integrated"
        ),
        "all_passed": all(checks.values()),
    }
