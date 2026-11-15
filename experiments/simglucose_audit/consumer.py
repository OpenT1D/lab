"""Sampled audit-1 orchestration exercised only through the fixed invented engine."""

from fractions import Fraction

from ._fixture import ScriptedEngine
from .contract import (
    HORIZON,
    REPORT_SCHEMA,
    STEP,
    availability,
    fields,
    integer,
    number,
    require,
    validate_config,
)


class ReleaseQueue:
    def __init__(self, variant):
        require(variant in ("filtered", "unfiltered", "future80", "fasting"), "variant")
        self.variant = variant
        self.samples = []
        self.last_measurement = -STEP
        self.next_tick = 0
        self.announced = False

    def offer(self, raw):
        fields(raw, "measured_ms glucose_mg_dl", "raw-observation-fields")
        measured = integer(raw["measured_ms"], "measurement-time")
        require(
            measured == self.last_measurement + STEP and measured <= HORIZON,
            "measurement-grid",
        )
        glucose = number(raw["glucose_mg_dl"], "glucose")
        self.samples.append(
            {
                "measured_ms": measured,
                "available_ms": availability(measured, self.variant),
                "glucose_mg_dl": glucose,
            }
        )
        self.last_measurement = measured

    def release(self, time_ms):
        integer(time_ms, "tick-time")
        require(time_ms == self.next_tick and time_ms < HORIZON, "release-tick")
        candidates = [
            sample
            for sample in self.samples
            if sample["available_ms"] is not None and sample["available_ms"] <= time_ms
        ]
        require(candidates, "no-released-observation")
        self.next_tick += STEP
        observation = dict(max(candidates, key=lambda sample: sample["measured_ms"]))
        announcements = []
        if self.variant != "fasting" and not self.announced and time_ms >= 900000:
            announcements = ["synthetic-announcement"]
            self.announced = True
        return observation, announcements


class SampledAudit1:
    def __init__(self, basal_u_h):
        self.basal = number(basal_u_h, "basal")
        require(self.basal <= 3, "basal")
        self.previous = 120.0
        self.source = -1
        self.last = None
        self.next_tick = 0

    def update(self, time_ms, observation):
        integer(time_ms, "tick-time")
        require(time_ms == self.next_tick and time_ms < HORIZON, "controller-tick")
        fields(observation, "measured_ms available_ms glucose_mg_dl", "observation-fields")
        measured = integer(observation["measured_ms"], "measurement-time")
        available = integer(observation["available_ms"], "availability-time")
        glucose = number(observation["glucose_mg_dl"], "glucose")
        require(
            measured % STEP == 0 and self.source <= measured <= available <= time_ms,
            "causal-observation",
        )
        require(time_ms != 0 or measured == available == 0, "initial-observation")
        require(measured != self.source or observation == self.last, "changed-held-observation")
        previous, fresh = self.previous, measured > self.source
        # Ordered binary64 operations, matching the declared sampled policy.
        command = (
            min(3.0, max(0.0, self.basal + 0.01 * (previous - 120.0))) if fresh else self.basal
        )
        if fresh:
            self.previous, self.source, self.last = glucose, measured, dict(observation)
        self.next_tick += STEP
        return {"previous_mg_dl": previous, "fresh": fresh, "command_u_h": command}


def run_invented(config, identity, config_sha256):
    """Data-only fixture input. No caller-supplied engine, factory, callback or path."""
    config = validate_config(config)
    result = {
        "schema": REPORT_SCHEMA,
        "kind": "invented",
        "source_identity": identity,
        "config_sha256": config_sha256,
        "status": "not_run",
        "primary_error": None,
        "diagnostic_error": None,
        "rows": [],
        "observations": [],
        "pending_command": None,
        "diagnostic_tail": [],
        "delivered_u_exact": None,
        "calls": {"constructed": 0, "reset": 0, "step": 0, "close": 0, "sampled_observations": 0},
        "scripted_actions_received": [],
        "scripted_observation_cursor": 0,
        "initial_history_cgm": config["initial_history_cgm"],
        "fixture_cleanup": "not-needed",
        "native_call_counts_observed": False,
        "native_execution": False,
        "native_acceptance": False,
        "host_or_process_qualified": False,
        "new_authority_granted": False,
        "native_execution_deferred": True,
    }
    if config["fault"] == "cancel-before-reset":
        result["status"], result["primary_error"] = "interrupted", "scripted-cancel-before-reset"
        return result
    engine = ScriptedEngine(config)
    require(type(engine) is ScriptedEngine, "fixed-scripted-engine")
    queue, controller = ReleaseQueue(config["variant"]), SampledAudit1(config["basal_u_h"])
    total = Fraction(0)
    try:
        raw = engine.reset()
        result["observations"].append(dict(raw))
        queue.offer(raw)
        result["status"] = "started"
        for time_ms in range(0, HORIZON, STEP):
            observation, announcements = queue.release(time_ms)
            transition = controller.update(time_ms, observation)
            command = {
                "time_ms": time_ms,
                "observation": observation,
                "new_announcements": announcements,
                **transition,
                "basal_u_min": transition["command_u_h"] / 60,
                "bolus_u_min": 0.0,
            }
            result["pending_command"] = command
            reply = engine.step(command["basal_u_min"], command["bolus_u_min"])
            # Commit only an actually returned scripted interval; pending has no delivery.
            delivered = number(reply["delivered_rate_u_min"], "modeled-delivery")
            result["rows"].append(
                {**command, "interval_end_ms": time_ms + STEP, "delivered_rate_u_min": delivered}
            )
            total += Fraction(str(delivered)) * 3
            result["pending_command"] = None
            result["observations"].append(dict(reply["observation"]))
            queue.offer(reply["observation"])
            if reply["diagnostic_tail"] is not None:
                result["diagnostic_tail"].append(reply["diagnostic_tail"])
                raise ValueError("scripted-terminal-diagnostic")
            if reply["done"]:
                result["status"] = "fixture-terminal"
                break
        else:
            result["status"] = "completed"
    except (ValueError, RuntimeError, InterruptedError) as error:
        result["status"] = "interrupted" if isinstance(error, InterruptedError) else "failed"
        result["primary_error"] = str(error)
    finally:
        try:
            engine.close()
            result["fixture_cleanup"] = "completed"
        except RuntimeError as error:
            result["diagnostic_error"] = str(error)
            result["fixture_cleanup"] = "failed"
            result["status"] = "failed"
        result["calls"] = dict(engine.calls)
        result["scripted_actions_received"] = list(engine.actions)
        result["scripted_observation_cursor"] = engine.index
    if result["rows"]:
        result["delivered_u_exact"] = {
            "numerator": str(total.numerator),
            "denominator": str(total.denominator),
        }
    return result
