"""Independent finite-fixture oracle; no consumer, queue, engine or native imports."""

from fractions import Fraction

from .contract import HORIZON, REPORT_SCHEMA, STEP, validate_config


def _rounded(value):
    return Fraction.from_float(float(value))


def _command(basal, previous):
    # Exact rational intermediates with binary64 rounding at each declared operation.
    delta = _rounded(Fraction.from_float(previous) - 120)
    correction = _rounded(Fraction.from_float(0.01) * delta)
    rate = _rounded(Fraction.from_float(float(basal)) + correction)
    return float(min(Fraction(3), max(Fraction(0), rate)))


def expected_fixture(config, identity, config_sha256):
    config = validate_config(config)
    fault, close_error = config["fault"], config["close_error"]
    rows, observations, tail = [], [], []
    status, primary, diagnostic, pending = "not_run", None, None, None
    calls = {"constructed": 0, "reset": 0, "step": 0, "close": 0, "sampled_observations": 0}
    actions = []
    cleanup = "not-needed"
    if fault == "cancel-before-reset":
        status, primary = "interrupted", "scripted-cancel-before-reset"
    else:
        calls.update(constructed=1, reset=1, close=1)
        cleanup = "failed" if close_error else "completed"
        if fault == "reset-error":
            status, primary = "failed", "scripted-reset-error"
        else:
            observations.append({"measured_ms": 0, "glucose_mg_dl": config["samples"][0]})
            calls["sampled_observations"] += 1
            previous, consumed = 120.0, -1
            for index in range(10):
                time_ms = index * STEP
                eligible = []
                for sample_index in range(index + 1):
                    measured = sample_index * STEP
                    available = measured
                    if config["variant"] in ("filtered", "future80"):
                        if sample_index in (4, 5):
                            continue
                        if sample_index == 3:
                            available = 900000
                    if available <= time_ms:
                        eligible.append(
                            (measured, available, float(config["samples"][sample_index]))
                        )
                measured, available, glucose = max(eligible)
                fresh = measured > consumed
                rate = (
                    _command(config["basal_u_h"], previous) if fresh else float(config["basal_u_h"])
                )
                pending = {
                    "time_ms": time_ms,
                    "observation": {
                        "measured_ms": measured,
                        "available_ms": available,
                        "glucose_mg_dl": glucose,
                    },
                    "new_announcements": (
                        ["synthetic-announcement"]
                        if index == 5 and config["variant"] != "fasting"
                        else []
                    ),
                    "previous_mg_dl": previous,
                    "fresh": fresh,
                    "command_u_h": rate,
                    "basal_u_min": float(Fraction.from_float(rate) / 60),
                    "bolus_u_min": 0.0,
                }
                if fresh:
                    previous, consumed = glucose, measured
                calls["step"] += 1
                actions.append({"basal_u_min": pending["basal_u_min"], "bolus_u_min": 0.0})
                if index == 2 and fault in ("after-two", "cancel-after-two"):
                    status = "interrupted" if fault == "cancel-after-two" else "failed"
                    primary = (
                        "scripted-cancel-after-two"
                        if status == "interrupted"
                        else "scripted-after-two"
                    )
                    break
                rows.append(
                    {
                        **pending,
                        "interval_end_ms": time_ms + STEP,
                        "delivered_rate_u_min": float(config["delivered_rates_u_min"][index]),
                    }
                )
                pending = None
                observations.append(
                    {"measured_ms": time_ms + STEP, "glucose_mg_dl": config["samples"][index + 1]}
                )
                calls["sampled_observations"] += 1
                if fault == "early-done" and index == 1:
                    status = "fixture-terminal"
                    break
                if fault == "terminal-tail" and index == 9:
                    status, primary = "failed", "scripted-terminal-diagnostic"
                    tail.append(
                        {"time_ms": HORIZON, "error": "scripted-nonfinite-terminal-command"}
                    )
                    break
            else:
                status = "completed"
        if close_error:
            status, diagnostic = "failed", "scripted-close-error"
    amount = None
    if rows:
        total = sum((Fraction(str(row["delivered_rate_u_min"])) * 3 for row in rows), Fraction(0))
        amount = {"numerator": str(total.numerator), "denominator": str(total.denominator)}
    return {
        "schema": REPORT_SCHEMA,
        "kind": "invented",
        "source_identity": identity,
        "config_sha256": config_sha256,
        "status": status,
        "primary_error": primary,
        "diagnostic_error": diagnostic,
        "rows": rows,
        "observations": observations,
        "pending_command": pending,
        "diagnostic_tail": tail,
        "delivered_u_exact": amount,
        "calls": calls,
        "scripted_actions_received": actions,
        "scripted_observation_cursor": len(rows),
        "initial_history_cgm": config["initial_history_cgm"],
        "fixture_cleanup": cleanup,
        "native_call_counts_observed": False,
        "native_execution": False,
        "native_acceptance": False,
        "host_or_process_qualified": False,
        "new_authority_granted": False,
        "native_execution_deferred": True,
    }
