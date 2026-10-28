"""Verify one completed G2P2C training attempt and replay causal inference."""

import argparse
import csv
import hashlib
import json
import math
from pathlib import Path

from experiments.m1.contracts import Action, Observation

from .g2p2c_training_run import (
    PLAN,
    ROOT,
    _sha,
    _tensor_digest,
    source_args,
    validated_plan,
)

PROFILE_BASAL_U_MIN = {
    "adult#001": 0.02112267499992533,
    "adult#002": 0.022825539499994,
}


def _attempt_output(plan, profile_name):
    profile = next((p for p in plan["profiles"] if p["name"] == profile_name), None)
    if profile is None or profile_name not in PROFILE_BASAL_U_MIN:
        raise ValueError("Profile is not in the frozen C1 training roster")
    return ROOT / profile["output_directory"]


def validate_attempt(plan, profile_name, output):
    output = Path(output).resolve()
    if output != _attempt_output(plan, profile_name).resolve():
        raise ValueError("Checkpoint is outside the frozen profile attempt")
    attempt = json.loads((output / "attempt.json").read_text())
    required = {
        "schema": "opent1d.c1.g2p2c-training-attempt/1",
        "mode": "full",
        "profile": profile_name,
        "source_commit": plan["source_commit"],
        "simglucose_commit": plan["simglucose_commit"],
        "plan_sha256": _sha(PLAN),
        "training_lock_sha256": _sha(ROOT / "experiments/c1/g2p2c_training_source/uv.lock"),
        "seed_before_actor_initialization": True,
        "torch_deterministic_algorithms": True,
        "m1_development_matrix_run": False,
        "source_completed": True,
        "completed_interactions": plan["expected_completed_interactions"],
    }
    if any(attempt.get(key) != value for key, value in required.items()):
        raise ValueError("Training attempt does not match the frozen full-run contract")
    if _sha(output / "training-plan.json") != required["plan_sha256"]:
        raise ValueError("Saved training plan differs from the committed plan")
    preflight = json.loads((output / "source-preflight.json").read_text())
    if (
        _sha(output / "source-preflight.json") != attempt.get("source_preflight_sha256")
        or preflight.get("g2p2c_source_commit") != plan["source_commit"]
        or preflight.get("m1_simglucose_commit") != plan["simglucose_commit"]
        or preflight.get("training_engine_matches_m1_pin") is not True
    ):
        raise ValueError("Saved source preflight is missing or differs")
    profile = next(p for p in plan["profiles"] if p["name"] == profile_name)
    args = json.loads((output / "args.json").read_text())
    expected_args = {
        "debug": 0,
        "sensor": "Dexcom",
        "patient_id": profile["source_patient_id"],
        "seed": profile["seed"],
        "feature_history": plan["feature_history_steps"],
        "calibration": plan["calibration_steps"],
        "max_test_epi_len": plan["max_test_episode_steps"],
        "max_epi_length": plan["max_training_episode_steps"],
        "planning_n_step": plan["planning_horizon_steps"],
        "n_training_workers": plan["training_workers"],
        "n_testing_workers": plan["testing_workers"],
        "n_features": 2,
        "use_meal_announcement": False,
        "use_carb_announcement": False,
        "use_tod_announcement": False,
        "expert_bolus": False,
        "expert_cf": False,
        "experiment_dir": str(output),
    }
    if any(args.get(key) != value for key, value in expected_args.items()):
        raise ValueError("Saved source arguments differ from the frozen training plan")
    with (output / "experiment_summary.csv").open() as stream:
        rows = list(csv.DictReader(stream))
    if (
        len(rows) != plan["expected_final_rollout"] + 2
        or [int(row["rollout"]) for row in rows[1:]]
        != list(range(plan["expected_final_rollout"] + 1))
        or any(row["status"] != "1" for row in rows[:-1])
        or rows[-1]["status"] != "2"
        or int(rows[-1]["rollout"]) != plan["expected_final_rollout"]
    ):
        raise ValueError("Source training summary does not reach the frozen final rollout")
    if (
        len(attempt.get("checkpoint_sha256", "")) != 64
        or len(attempt.get("actor_tensor_sha256", "")) != 64
    ):
        raise ValueError("Full training lacks actor checkpoint identity")
    checkpoint = output / "actor-final-state-dict.pt"
    if not checkpoint.is_file() or _sha(checkpoint) != attempt["checkpoint_sha256"]:
        raise ValueError("Final actor checkpoint bytes changed")
    return attempt, checkpoint


def _invented_stream(controller):
    digest = hashlib.sha256()
    last_fresh = None
    for minute in range(0, 2223, 3):
        if 2160 <= minute < 2190:
            observation = Observation(minute, last_fresh.glucose_mg_dl, last_fresh.time_min, False)
        else:
            glucose = float(110 + ((minute // 3) * 17) % 100)
            observation = Observation(minute, glucose, minute, True)
            last_fresh = observation
        action = controller.command(observation, 0.0)
        if not isinstance(action, Action) or not math.isfinite(action.basal_u_min):
            raise ValueError("Nonfinite or malformed actor action")
        if not 0 <= action.basal_u_min <= 5 or action.bolus_u_min != 0:
            raise ValueError("Actor action outside source rate boundary")
        if (
            not observation.available
            and action.basal_u_min != controller.missing_fallback_basal_u_min
        ):
            raise ValueError("Missing CGM did not produce the frozen profile basal")
        digest.update(f"{minute}:{action.basal_u_min:.17g}\n".encode())
    return digest.hexdigest()


def validate_architecture(plan, attempt, profile_name, architecture):
    matching = next(
        (item for item in architecture["profiles"] if item["profile"] == profile_name), None
    )
    if (
        architecture["source_commit"] != plan["source_commit"]
        or architecture["training_plan_sha256"] != attempt["plan_sha256"]
        or matching is None
        or matching["actor_settings"]["planning_n_step"] != plan["planning_horizon_steps"]
        or matching["exact_constructor_tensor_and_forward_parity"] is not True
        or matching["source_state_dict_weights_only_roundtrip"] is not True
    ):
        raise ValueError("Trained checkpoint lacks source/intake actor constructor parity")
    return matching


def verify_trained_source_forward(source, plan, profile_name, checkpoint, intake_actor):
    """Compare final weights through the imported source and intake actor paths."""
    import torch

    from .g2p2c_architecture_preflight import actor_settings

    profile = next(p for p in plan["profiles"] if p["name"] == profile_name)
    args = source_args(
        source, plan, profile, debug=False, output=_attempt_output(plan, profile_name)
    )
    from agents.g2p2c.models import ActorNetwork

    with torch.random.fork_rng(devices=[]):
        torch.manual_seed(profile["seed"])
        source_actor = ActorNetwork(args, torch.device("cpu"))
    if actor_settings(source_actor.args) != actor_settings(intake_actor.args):
        raise ValueError("Trained source and intake actor settings differ")
    from .g2p2c_checkpoint import load_actor_weights

    weights = load_actor_weights(
        checkpoint, sha256=_sha(Path(checkpoint)), expected=source_actor.state_dict()
    )
    source_actor.load_state_dict(weights, strict=True)
    if _tensor_digest(source_actor.state_dict()) != _tensor_digest(intake_actor.state_dict()):
        raise ValueError("Trained source and intake actor tensors differ")
    states = [
        torch.clamp(torch.linspace(-1, 1, 24).reshape(12, 2) + index / 100, -1, 1)
        for index in range(16)
    ]
    feature = torch.tensor([0.0])
    with torch.no_grad(), torch.random.fork_rng(devices=[]):
        torch.manual_seed(24)
        source_outputs = [source_actor(state, feature, None, "forward") for state in states]
        torch.manual_seed(24)
        intake_outputs = [intake_actor(state, feature, None, "forward") for state in states]
    if any(
        len(left) != 7 or len(right) != 7 or not all(torch.equal(a, b) for a, b in zip(left, right))
        for left, right in zip(source_outputs, intake_outputs)
    ):
        raise ValueError("Trained source and intake actor forward paths differ")
    return len(states)


def audit(source, profile_name):
    import torch

    from .g2p2c_architecture_preflight import audit as architecture_audit
    from .g2p2c_policy_adapter import load_source_state_dict

    torch.set_num_threads(1)
    torch.use_deterministic_algorithms(True)
    plan = validated_plan()
    output = _attempt_output(plan, profile_name)
    attempt, checkpoint = validate_attempt(plan, profile_name, output)
    architecture = architecture_audit(source)
    matching = validate_architecture(plan, attempt, profile_name, architecture)
    controller = load_source_state_dict(
        source,
        checkpoint,
        sha256=attempt["checkpoint_sha256"],
        seed=24,
        missing_fallback_basal_u_min=PROFILE_BASAL_U_MIN[profile_name],
    )
    if _tensor_digest(controller.actor.state_dict()) != attempt["actor_tensor_sha256"]:
        raise ValueError("Loaded actor tensor values differ from trained actor")
    before = torch.get_rng_state().clone()
    forward_states = verify_trained_source_forward(
        source, plan, profile_name, checkpoint, controller.actor
    )
    first = _invented_stream(controller)
    controller.reset()
    if _invented_stream(controller) != first:
        raise ValueError("Trained actor did not replay after controller reset")
    if not torch.equal(before, torch.get_rng_state()):
        raise ValueError("Trained callback changed the caller's PyTorch RNG")
    return {
        "schema": "opent1d.c1.g2p2c-trained-preflight/1",
        "profile": profile_name,
        "source_commit": plan["source_commit"],
        "simglucose_commit": plan["simglucose_commit"],
        "plan_sha256": attempt["plan_sha256"],
        "checkpoint_sha256": attempt["checkpoint_sha256"],
        "actor_tensor_sha256": attempt["actor_tensor_sha256"],
        "synthetic_replay_actions_sha256": first,
        "synthetic_replay_intervals": 741,
        "condition_d_missing_intervals": 10,
        "causal_reset_repeat": True,
        "checkpoint_identity_and_values_match": True,
        "source_intake_actor_constructor_parity": True,
        "trained_source_intake_forward_parity": True,
        "trained_forward_states": forward_states,
        "source_intake_actor_initialized_tensor_sha256": matching[
            "initialized_actor_tensor_sha256"
        ],
        "m1_native_case_run": False,
        "eligible_m1_comparator": False,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--profile", choices=tuple(PROFILE_BASAL_U_MIN), required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = audit(args.source, args.profile)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(f"{args.output}: checkpoint_identity_and_values_match=True")


if __name__ == "__main__":
    main()
