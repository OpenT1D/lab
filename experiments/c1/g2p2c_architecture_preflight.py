"""Compare frozen source-training actors with weights-only intake actors."""

import argparse
import hashlib
import json
import tempfile
from pathlib import Path

from .g2p2c_training_run import PLAN, ROOT, _sha, _tensor_digest, source_args, validated_plan

ACTOR_FIELDS = (
    "n_features",
    "feature_history",
    "planning_n_step",
    "n_planning_simulations",
    "n_hidden",
    "n_rnn_layers",
    "bidirectional",
    "rnn_directions",
    "use_handcraft",
    "n_handcrafted_features",
    "glucose_min",
    "glucose_max",
    "insulin_min",
    "insulin_max",
    "n_action",
    "return_type",
    "gamma",
    "t_meal",
)


def actor_settings(args):
    return {field: getattr(args, field) for field in ACTOR_FIELDS}


def audit(source):
    import torch

    from .g2p2c_policy_adapter import load_source_state_dict, new_source_actor

    source = Path(source).resolve()
    plan = validated_plan()
    torch.set_num_threads(1)
    torch.use_deterministic_algorithms(True)
    global_before = torch.get_rng_state().clone()
    profiles = []
    for profile in plan["profiles"]:
        training_args = source_args(
            source, plan, profile, debug=False, output=ROOT / profile["output_directory"]
        )
        from agents.g2p2c.models import ActorNetwork

        with torch.random.fork_rng(devices=[]):
            torch.manual_seed(profile["seed"])
            training_actor = ActorNetwork(training_args, torch.device("cpu"))
        intake_actor, source_report = new_source_actor(source, initialization_seed=profile["seed"])
        if actor_settings(training_args) != actor_settings(intake_actor.args):
            raise ValueError("Training and intake actor constructors differ")
        training_tensors = training_actor.state_dict()
        intake_tensors = intake_actor.state_dict()
        if (
            set(training_tensors) != set(intake_tensors)
            or any(
                training_tensors[name].shape != intake_tensors[name].shape
                or training_tensors[name].dtype != intake_tensors[name].dtype
                for name in training_tensors
            )
            or _tensor_digest(training_tensors) != _tensor_digest(intake_tensors)
        ):
            raise ValueError("Source-training and intake actor tensors differ")
        states = [
            torch.clamp(torch.linspace(-1, 1, 24).reshape(12, 2) + index / 100, -1, 1)
            for index in range(16)
        ]
        feature = torch.tensor([0.0])
        with torch.no_grad(), torch.random.fork_rng(devices=[]):
            torch.manual_seed(24)
            source_outputs = [training_actor(state, feature, None, "forward") for state in states]
            torch.manual_seed(24)
            intake_outputs = [intake_actor(state, feature, None, "forward") for state in states]
        if any(
            len(left) != 7
            or len(right) != 7
            or not all(torch.equal(a, b) for a, b in zip(left, right))
            for left, right in zip(source_outputs, intake_outputs)
        ):
            raise ValueError("Source-training and intake actor forward paths differ")
        with tempfile.TemporaryDirectory() as temporary:
            checkpoint = Path(temporary) / "untrained-source-state-dict.pt"
            torch.save(training_tensors, checkpoint)
            loaded = load_source_state_dict(
                source,
                checkpoint,
                sha256=hashlib.sha256(checkpoint.read_bytes()).hexdigest(),
                seed=24,
            )
            if _tensor_digest(loaded.actor.state_dict()) != _tensor_digest(training_tensors):
                raise ValueError("Weights-only intake changed source-training tensors")
            with torch.no_grad(), torch.random.fork_rng(devices=[]):
                torch.manual_seed(24)
                loaded_outputs = [loaded.actor(state, feature, None, "forward") for state in states]
            if any(
                not all(torch.equal(a, b) for a, b in zip(left, right))
                for left, right in zip(source_outputs, loaded_outputs)
            ):
                raise ValueError("Weights-only intake changed source-training actor outputs")
        profiles.append(
            {
                "profile": profile["name"],
                "training_seed": profile["seed"],
                "tensor_count": len(training_tensors),
                "initialized_actor_tensor_sha256": _tensor_digest(training_tensors),
                "actor_settings": actor_settings(training_args),
                "exact_constructor_tensor_and_forward_parity": True,
                "source_state_dict_weights_only_roundtrip": True,
                "invented_forward_states": len(states),
            }
        )
    if not torch.equal(global_before, torch.get_rng_state()):
        raise ValueError("Architecture preflight changed global PyTorch RNG")
    return {
        "schema": "opent1d.c1.g2p2c-architecture-preflight/1",
        "source_commit": source_report["commit"],
        "training_plan_sha256": _sha(PLAN),
        "profiles": profiles,
        "weights": "identically seeded initial weights; no trained checkpoint read",
        "native_m1_case_run": False,
        "eligible_m1_comparator": False,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise FileExistsError(f"Architecture report already exists: {args.output}")
    result = audit(args.source)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
