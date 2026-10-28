"""Run a frozen, non-comparative M1 integration check for a trained G2P2C actor."""

import argparse
import json
from dataclasses import asdict
from pathlib import Path

from experiments.m1.artifacts import strict_json
from experiments.m1.contracts import HORIZON, Observation, Row, validate_rows
from experiments.m1.contracts import Config as M1Config

from .g2p2c_trained_preflight import PROFILE_BASAL_U_MIN
from .g2p2c_training_preflight import audit as engine_audit
from .g2p2c_training_run import PLAN as TRAINING_PLAN
from .g2p2c_training_run import ROOT, _sha

PLAN = ROOT / "experiments/c1/g2p2c-native-smoke.json"


def replay_commands(rows, controller):
    """Recreate every saved command from released M1 fields, without a simulator."""
    controller.reset()
    for row in rows:
        observation = Observation(
            row.start_min,
            row.controller_cgm_mg_dl,
            row.controller_source_min,
            row.controller_source_min == row.start_min,
        )
        action = controller.command(observation, row.announced_g)
        if (action.basal_u_min, action.bolus_u_min) != (row.basal_u_min, row.bolus_u_min):
            raise ValueError(f"Saved actor command differs at minute {row.start_min}")
    return len(rows)


def _output(plan, profile_name, *, repeat):
    case = next((item for item in plan["cases"] if item["profile"] == profile_name), None)
    if case is None:
        raise ValueError("Profile is not in the native smoke roster")
    output = (ROOT / case["output_directory"]).resolve()
    return case, output.with_name(output.name + "-repeat") if repeat else output


def validated_plan(path=PLAN):
    plan = json.loads(Path(path).read_text())
    training = json.loads(TRAINING_PLAN.read_text())
    expected = [("adult#001", 101, "D"), ("adult#002", 101, "D")]
    actual = [(case["profile"], case["seed"], case["condition"]) for case in plan["cases"]]
    if (
        plan["schema"] != "opent1d.c1.g2p2c-native-smoke-plan/1"
        or plan["training_plan_sha256"] != _sha(TRAINING_PLAN)
        or plan["source_commit"] != training["source_commit"]
        or plan["simglucose_commit"] != training["simglucose_commit"]
        or plan["actor_sampling_seed"] != 24
        or actual != expected
        or plan["planned_intervals_per_case"] != 960
        or plan["expected_masked_command_intervals"] != 10
        or plan["efficacy_metrics_authorized"] is not False
        or plan["comparative_matrix_authorized"] is not False
    ):
        raise ValueError("Native smoke plan changed or is not bounded")
    for case in plan["cases"]:
        M1Config(case["profile"], case["seed"], "pid", case["condition"])
        output = (ROOT / case["output_directory"]).resolve()
        if not output.is_relative_to(ROOT / "results"):
            raise ValueError("Native smoke output must remain under ignored results/")
    return plan


def run(source, profile_name, *, repeat=False):
    from experiments.m1.simulation import simulate

    from .g2p2c_policy_adapter import load_source_state_dict
    from .g2p2c_trained_preflight import audit as trained_audit

    plan = validated_plan()
    case, output = _output(plan, profile_name, repeat=repeat)
    source_report = engine_audit(source)
    if (
        source_report["g2p2c_source_commit"] != plan["source_commit"]
        or source_report["m1_simglucose_commit"] != plan["simglucose_commit"]
    ):
        raise ValueError("Native smoke source differs from frozen source")
    trained_report = trained_audit(source, profile_name)
    if output.exists():
        raise FileExistsError(f"Native smoke output already exists: {output}")
    # Resolve the path from the frozen training roster, not the display name.
    training = json.loads(TRAINING_PLAN.read_text())
    training_case = next(p for p in training["profiles"] if p["name"] == profile_name)
    checkpoint = ROOT / training_case["output_directory"] / "actor-final-state-dict.pt"
    controller = load_source_state_dict(
        source,
        checkpoint,
        sha256=trained_report["checkpoint_sha256"],
        seed=plan["actor_sampling_seed"],
        missing_fallback_basal_u_min=PROFILE_BASAL_U_MIN[profile_name],
    )

    output.parent.mkdir(parents=True, exist_ok=True)
    output.mkdir(exist_ok=False)
    (output / "native-smoke-plan.json").write_bytes(PLAN.read_bytes())
    (output / "source-preflight.json").write_text(
        json.dumps(source_report, indent=2, sort_keys=True) + "\n"
    )
    (output / "trained-preflight.json").write_text(
        json.dumps(trained_report, indent=2, sort_keys=True) + "\n"
    )
    (output / "trace.jsonl").touch()
    rows = []
    initial_snapshot = []

    def initial(snapshot):
        initial_snapshot.append(asdict(snapshot))
        (output / "initial.json").write_text(
            json.dumps(asdict(snapshot), indent=2, sort_keys=True) + "\n"
        )

    def checkpoint(row):
        rows.append(row)
        with (output / "trace.jsonl").open("a") as stream:
            stream.write(json.dumps(asdict(row), sort_keys=True) + "\n")

    config = M1Config(profile_name, case["seed"], "pid", case["condition"])
    try:
        status = simulate(config, checkpoint, initial, controller=controller)
        endpoint = validate_rows(rows)
        if len(initial_snapshot) != 1:
            raise ValueError("Native case did not produce exactly one initial snapshot")
        replayed = replay_commands(rows, controller)
    except Exception as error:
        (output / "failure.json").write_text(
            json.dumps({"type": type(error).__name__, "message": str(error)}, sort_keys=True) + "\n"
        )
        raise
    masked = sum(row.controller_source_min < row.start_min for row in rows)
    fallback_exact = all(
        row.basal_u_min == PROFILE_BASAL_U_MIN[profile_name] and row.bolus_u_min == 0
        for row in rows
        if row.controller_source_min < row.start_min
    )
    max_basal = max((row.basal_u_min for row in rows), default=0.0)
    bounded = all(0 <= row.basal_u_min <= 5 and row.bolus_u_min == 0 for row in rows)
    complete = (
        status == "completed"
        and endpoint == 2880
        and len(rows) == plan["planned_intervals_per_case"]
        and masked == plan["expected_masked_command_intervals"]
        and fallback_exact
        and bounded
    )
    report = {
        "schema": "opent1d.c1.g2p2c-native-smoke/1",
        "profile": profile_name,
        "seed": case["seed"],
        "condition": case["condition"],
        "plan_sha256": _sha(PLAN),
        "source_preflight_sha256": _sha(output / "source-preflight.json"),
        "trained_preflight_sha256": _sha(output / "trained-preflight.json"),
        "checkpoint_sha256": trained_report["checkpoint_sha256"],
        "initial_snapshot_sha256": _sha(output / "initial.json"),
        "trace_sha256": _sha(output / "trace.jsonl"),
        "simulator_free_action_replay_intervals": replayed,
        "native_status": status,
        "intervals": len(rows),
        "endpoint_min": endpoint,
        "masked_command_intervals": masked,
        "masked_commands_equal_profile_basal": fallback_exact,
        "max_basal_u_min": max_basal,
        "actions_bounded": bounded,
        "integration_gate_pass": complete,
        "efficacy_metrics_computed": False,
        "eligible_m1_comparator": False,
    }
    (output / "report.json").write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    return report


def verify_saved(source, profile_name, *, repeat=False):
    """Check a saved native trace and replay its actor commands without simglucose."""
    from .g2p2c_policy_adapter import load_source_state_dict
    from .g2p2c_trained_preflight import audit as trained_audit

    plan = validated_plan()
    case, output = _output(plan, profile_name, repeat=repeat)
    report = strict_json((output / "report.json").read_bytes())
    if (
        report.get("schema") != "opent1d.c1.g2p2c-native-smoke/1"
        or report.get("profile") != profile_name
        or report.get("plan_sha256") != _sha(PLAN)
        or (output / "native-smoke-plan.json").read_bytes() != PLAN.read_bytes()
    ):
        raise ValueError("Saved native smoke identity differs from the frozen plan")
    source_report = strict_json((output / "source-preflight.json").read_bytes())
    trained_report = strict_json((output / "trained-preflight.json").read_bytes())
    if source_report != engine_audit(source) or trained_report != trained_audit(
        source, profile_name
    ):
        raise ValueError("Saved native smoke source or trained checkpoint differs")
    initial = strict_json((output / "initial.json").read_bytes())
    if (
        set(initial)
        != {
            "time_min",
            "glucose_mg_dl",
            "cgm_mg_dl",
            "true_meal_g",
            "delivered_u_min",
            "terminal",
        }
        or initial["time_min"] != 0
        or initial["terminal"] is not False
    ):
        raise ValueError("Invalid saved initial native snapshot")
    trace = (output / "trace.jsonl").read_bytes()
    if not trace or not trace.endswith(b"\n"):
        raise ValueError("Missing or truncated saved native trace")
    rows = [Row(**strict_json(line)) for line in trace.splitlines()]
    endpoint = validate_rows(rows)
    status = "terminated" if rows[-1].terminal else "completed"
    if status == "completed" and endpoint != HORIZON:
        raise ValueError("Saved trace has no native terminal or completed horizon")
    training = strict_json(TRAINING_PLAN.read_bytes())
    training_case = next(p for p in training["profiles"] if p["name"] == profile_name)
    checkpoint = ROOT / training_case["output_directory"] / "actor-final-state-dict.pt"
    controller = load_source_state_dict(
        source,
        checkpoint,
        sha256=trained_report["checkpoint_sha256"],
        seed=plan["actor_sampling_seed"],
        missing_fallback_basal_u_min=PROFILE_BASAL_U_MIN[profile_name],
    )
    replayed = replay_commands(rows, controller)
    masked = sum(row.controller_source_min < row.start_min for row in rows)
    fallback_exact = all(
        row.basal_u_min == PROFILE_BASAL_U_MIN[profile_name] and row.bolus_u_min == 0
        for row in rows
        if row.controller_source_min < row.start_min
    )
    bounded = all(0 <= row.basal_u_min <= 5 and row.bolus_u_min == 0 for row in rows)
    expected = {
        "schema": "opent1d.c1.g2p2c-native-smoke/1",
        "profile": profile_name,
        "seed": case["seed"],
        "condition": case["condition"],
        "plan_sha256": _sha(PLAN),
        "source_preflight_sha256": _sha(output / "source-preflight.json"),
        "trained_preflight_sha256": _sha(output / "trained-preflight.json"),
        "checkpoint_sha256": trained_report["checkpoint_sha256"],
        "initial_snapshot_sha256": _sha(output / "initial.json"),
        "trace_sha256": _sha(output / "trace.jsonl"),
        "simulator_free_action_replay_intervals": replayed,
        "native_status": status,
        "intervals": len(rows),
        "endpoint_min": endpoint,
        "masked_command_intervals": masked,
        "masked_commands_equal_profile_basal": fallback_exact,
        "max_basal_u_min": max(row.basal_u_min for row in rows),
        "actions_bounded": bounded,
        "integration_gate_pass": (
            status == "completed"
            and endpoint == HORIZON
            and len(rows) == plan["planned_intervals_per_case"]
            and masked == plan["expected_masked_command_intervals"]
            and fallback_exact
            and bounded
        ),
        "efficacy_metrics_computed": False,
        "eligible_m1_comparator": False,
    }
    if report != expected:
        raise ValueError("Saved native smoke report differs from independent reconstruction")
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--profile", choices=tuple(PROFILE_BASAL_U_MIN), required=True)
    parser.add_argument("--repeat", action="store_true")
    parser.add_argument("--verify", action="store_true")
    args = parser.parse_args()
    result = (
        verify_saved(args.source, args.profile, repeat=args.repeat)
        if args.verify
        else run(args.source, args.profile, repeat=args.repeat)
    )
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
