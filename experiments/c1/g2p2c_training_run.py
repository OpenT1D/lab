"""Launch a predeclared G2P2C source training with M1's pinned engine."""

import argparse
import csv
import hashlib
import json
import os
import random
import sys
from pathlib import Path

from .g2p2c_training_preflight import audit as source_audit

ROOT = Path(__file__).resolve().parents[2]
PLAN = ROOT / "experiments/c1/g2p2c-training.json"
HISTORICAL_TRAINING_LOCK_SHA256 = "7c9df6637d7078603395db9074ae9efcef5db7fe4d6911aa25ffb93a65901d70"


def _sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _tensor_digest(weights):
    """Stable value digest, independent of PyTorch's serialization container."""
    digest = hashlib.sha256()
    for name, tensor in sorted(weights.items()):
        value = tensor.detach().cpu().contiguous()
        digest.update(name.encode() + b"\0")
        digest.update(str(value.dtype).encode() + b"\0")
        digest.update(json.dumps(list(value.shape)).encode() + b"\0")
        digest.update(value.numpy().tobytes())
    return digest.hexdigest()


def validated_plan(path=PLAN):
    plan = json.loads(Path(path).read_text())
    batch = plan["n_step"] * plan["training_workers"]
    rollouts = plan["source_interaction_stop_threshold"] // batch + 1
    if (
        plan["schema"] != "opent1d.c1.g2p2c-training-plan/1"
        or plan["sensor"] != "Dexcom"
        or plan["sample_minutes"] != 3
        or plan["device"] != "cpu"
        or plan["feature_history_steps"] != 12
        or plan["calibration_steps"] != 12
        or plan["max_test_episode_steps"] * 3 != 1440
        or plan["max_training_episode_steps"] * 3 != 14400
        or plan["planning_horizon_steps"] * 3 != 30
        or plan["n_step"] != 256
        or plan["training_workers"] != 16
        or plan["testing_workers"] != 1
        or plan["source_interaction_stop_threshold"] != 800000
        or plan["expected_completed_interactions"] != rollouts * batch
        or plan["expected_final_rollout"] != rollouts - 1
        or plan["max_full_training_attempts_per_profile"] != 1
        or plan["evaluation_matrix_authorized"] is not False
        or plan["comparator_eligible"] is not False
        or [(p["name"], p["source_patient_id"], p["seed"]) for p in plan["profiles"]]
        != [("adult#001", 20, 17), ("adult#002", 21, 17)]
    ):
        raise ValueError("C1 training plan changed or physical-time mapping is invalid")
    for profile in plan["profiles"]:
        output = (ROOT / profile["output_directory"]).resolve()
        if not output.is_relative_to(ROOT / "results"):
            raise ValueError("C1 training output must stay under ignored results/")
    return plan


def source_args(source, plan, profile, *, debug, output):
    os.environ["MAIN_PATH"] = str(source)
    if str(source) not in sys.path:
        sys.path.insert(1, str(source))
    from agents.g2p2c.parameters import set_args
    from utils.options import Options

    options = Options()
    options._initial()
    args = options.parser.parse_args(
        [
            "--agent",
            "g2p2c",
            "--sensor",
            plan["sensor"],
            "--pump",
            plan["pump"],
            "--device",
            plan["device"],
            "--debug",
            str(int(debug)),
            "--patient_id",
            str(profile["source_patient_id"]),
            "--seed",
            str(profile["seed"]),
            "--folder_id",
            output.name,
        ]
    )
    Options.validate_args(args)
    args.aux_mode = "dual"
    args.use_planning = "yes"
    args = set_args(args)
    args.max_test_epi_len = plan["max_test_episode_steps"]
    args.max_epi_length = plan["max_training_episode_steps"]
    args.planning_n_step = plan["planning_horizon_steps"]
    args.n_testing_workers = plan["testing_workers"]
    if not debug:
        args.n_training_workers = plan["training_workers"]
    args.experiment_dir = str(output)
    if (
        args.feature_history != plan["feature_history_steps"]
        or args.calibration != plan["calibration_steps"]
        or args.n_step != plan["n_step"]
        or args.n_features != 2
        or args.use_meal_announcement
        or args.use_carb_announcement
        or args.use_tod_announcement
        or args.expert_bolus
        or args.expert_cf
    ):
        raise ValueError("Source policy configuration changed")
    return args


def run(source, profile_name, *, mode, smoke_output=None):
    source = Path(source).resolve()
    plan = validated_plan()
    profile = next((p for p in plan["profiles"] if p["name"] == profile_name), None)
    if profile is None:
        raise ValueError("Profile is not in the declared training roster")
    preflight = source_audit(source)
    if plan["source_commit"] != preflight["g2p2c_source_commit"]:
        raise ValueError("G2P2C source commit changed")
    if plan["simglucose_commit"] != preflight["m1_simglucose_commit"]:
        raise ValueError("M1 simglucose commit changed")
    full_output = (ROOT / profile["output_directory"]).resolve()
    if mode == "smoke":
        if smoke_output is None:
            raise ValueError("Smoke mode requires a distinct output directory")
        output = Path(smoke_output).resolve()
        if output == full_output or not output.is_relative_to(ROOT / "results"):
            raise ValueError("Smoke output must be a separate ignored results/ directory")
    elif mode == "full":
        output = full_output
    else:
        raise ValueError("Expected smoke or full mode")
    if output.exists():
        raise FileExistsError(f"Training output already exists: {output}")
    if (
        _sha(ROOT / "experiments/c1/g2p2c_training_source/uv.lock")
        != HISTORICAL_TRAINING_LOCK_SHA256
    ):
        raise ValueError(
            "Historical C1 training requires its recorded Torch 2.2 lock/checkout; "
            "the patched runtime does not authorize retraining under the old freeze"
        )
    args = source_args(source, plan, profile, debug=mode == "smoke", output=output)

    import numpy as np
    import torch
    from agents.g2p2c.g2p2c import G2P2C
    from utils.core import get_patient_env, set_logger

    # Upstream run_RL_agent.py seeds *after* constructing the actor. Seed first
    # so the initial weights and subsequent sampling are reproducible.
    torch.set_num_threads(1)
    torch.use_deterministic_algorithms(True)
    torch.manual_seed(profile["seed"])
    np.random.seed(profile["seed"])
    random.seed(profile["seed"])

    output.parent.mkdir(parents=True, exist_ok=True)
    output.mkdir(exist_ok=False)
    for relative in (
        "checkpoints",
        "training/data",
        "training/plots",
        "testing/data",
        "testing/plots",
        "code",
    ):
        (output / relative).mkdir(parents=True)
    set_logger(str(output))
    (output / "args.json").write_text(json.dumps(vars(args), indent=4) + "\n")
    (output / "training-plan.json").write_bytes(PLAN.read_bytes())
    (output / "source-preflight.json").write_text(
        json.dumps(preflight, indent=2, sort_keys=True) + "\n"
    )
    metadata = {
        "schema": "opent1d.c1.g2p2c-training-attempt/1",
        "mode": mode,
        "profile": profile_name,
        "source_commit": plan["source_commit"],
        "simglucose_commit": plan["simglucose_commit"],
        "plan_sha256": _sha(PLAN),
        "source_preflight_sha256": _sha(output / "source-preflight.json"),
        "training_lock_sha256": _sha(ROOT / "experiments/c1/g2p2c_training_source/uv.lock"),
        "seed_before_actor_initialization": True,
        "torch_deterministic_algorithms": True,
        "m1_development_matrix_run": False,
    }
    (output / "attempt.json").write_text(json.dumps(metadata, indent=2, sort_keys=True) + "\n")
    agent = G2P2C(args, args.device, False, "", "")
    patients, env_ids = get_patient_env()
    if patients[profile["source_patient_id"]] != profile_name:
        raise ValueError("Source patient ID changed")
    try:
        agent.run(args, patients, env_ids, profile["seed"])
    except SystemExit as error:
        if error.code not in (None, 0):
            raise
    with (output / "experiment_summary.csv").open() as stream:
        rows = list(csv.DictReader(stream))
    expected_rollout = 7 if mode == "smoke" else plan["expected_final_rollout"]
    if not rows or rows[-1]["status"] != "2" or int(rows[-1]["rollout"]) != expected_rollout:
        raise RuntimeError("Source run did not reach the declared final rollout")
    metadata["actor_tensor_sha256"] = _tensor_digest(agent.policy.Actor.state_dict())
    if mode == "full":
        checkpoint = output / "actor-final-state-dict.pt"
        temporary = output / "actor-final-state-dict.pt.tmp"
        torch.save(agent.policy.Actor.state_dict(), temporary)
        temporary.replace(checkpoint)
        metadata["checkpoint_sha256"] = _sha(checkpoint)
        metadata["completed_interactions"] = plan["expected_completed_interactions"]
    else:
        metadata["completed_interactions"] = 4096
    metadata["source_completed"] = True
    (output / "attempt.json").write_text(json.dumps(metadata, indent=2, sort_keys=True) + "\n")
    return metadata


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--profile", required=True)
    parser.add_argument("--mode", choices=("smoke", "full"), required=True)
    parser.add_argument("--smoke-output", type=Path)
    args = parser.parse_args()
    result = run(args.source, args.profile, mode=args.mode, smoke_output=args.smoke_output)
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
