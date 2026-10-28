"""Exercise pinned G2P2C actor inference on causal synthetic M1 inputs.

The actor is randomly initialized, deliberately never connected to a native
simulation. This verifies source tensor/action plumbing, not a comparator.
"""

import argparse
import hashlib
import json
import tempfile
from pathlib import Path

import numpy as np
import torch

from experiments.m1.contracts import Observation

from .g2p2c_boundary import pump_rate
from .g2p2c_policy_adapter import (
    CausalActorAdapter,
    load_source_state_dict,
    new_source_actor,
)
from .g2p2c_state_parity import _source_state_class


def audit(source):
    source = Path(source).resolve()
    torch.set_num_threads(1)
    torch.use_deterministic_algorithms(True)
    actor, source_audit = new_source_actor(source, initialization_seed=17)
    source_args = actor.args
    source_state = _source_state_class(source)(source_args)
    adapter = CausalActorAdapter(actor, seed=24)
    previous = None
    first_action = None
    actions = hashlib.sha256()
    global_rng_before = torch.get_rng_state().clone()
    for index in range(16):
        minute = 3 * index
        glucose = 90 + (index * 37) % 180
        observation = Observation(minute, glucose, minute, True)
        insulin = 0 if previous is None else previous.basal_u_min
        source_array, _ = source_state.update(cgm=glucose, ins=insulin)
        source_tensor = torch.as_tensor(source_array, dtype=torch.float32)
        with torch.no_grad(), torch.random.fork_rng(devices=[]):
            torch.set_rng_state(adapter._rng_state)
            source_action = actor(source_tensor, torch.tensor([23.0]), None, "forward")[2]
        previous = adapter.command(observation, 0)
        if not np.array_equal(source_array, np.asarray(adapter.state._history, dtype=np.float32)):
            raise ValueError(f"Source/local callback state changed at minute {minute}")
        if previous != pump_rate(float(source_action.item())):
            raise ValueError(f"Source/local actor action changed at minute {minute}")
        if index == 0:
            first_action = previous
        actions.update(source_action.detach().numpy().tobytes())
    if not torch.equal(global_rng_before, torch.get_rng_state()):
        raise ValueError("Source probe changed the caller's global PyTorch RNG")

    adapter.reset()
    first = adapter.command(Observation(0, 90, 0, True), 0)
    if first != first_action:
        raise ValueError("Actor action changed after callback reset")
    try:
        adapter.command(Observation(3, 90, 0, False), 0)
    except ValueError as error:
        if "stale-CGM" not in str(error):
            raise
    else:
        raise ValueError("Stale M1 observation was accepted")
    if adapter.state._time_min != 0 or adapter.previous != first:
        raise ValueError("Rejected stale observation changed controller state")

    class InvalidActor(torch.nn.Module):
        def forward(self, *_args):
            return None, None, torch.tensor([float("nan")])

    invalid = CausalActorAdapter(InvalidActor(), seed=24)
    try:
        invalid.command(Observation(0, 90, 0, True), 0)
    except ValueError as error:
        if "finite" not in str(error):
            raise
    else:
        raise ValueError("Nonfinite policy action was accepted")
    if invalid.state._time_min is not None or invalid.previous is not None:
        raise ValueError("Rejected policy action advanced controller state")
    with tempfile.TemporaryDirectory() as temporary:
        path = Path(temporary) / "untrained-state-dict.pt"
        torch.save(actor.state_dict(), path)
        sha256 = hashlib.sha256(path.read_bytes()).hexdigest()
        loaded = load_source_state_dict(source, path, sha256=sha256, seed=24)
        if loaded.command(Observation(0, 90, 0, True), 0) != first:
            raise ValueError("Weights-only checkpoint changed reset action")
        try:
            load_source_state_dict(source, path, sha256="0" * 64, seed=24)
        except ValueError as error:
            if "SHA-256 mismatch" not in str(error):
                raise
        else:
            raise ValueError("Changed checkpoint hash was accepted")
        malformed = Path(temporary) / "wrong-shape-state-dict.pt"
        weights = actor.state_dict()
        first_key = next(iter(weights))
        weights[first_key] = torch.zeros(1)
        torch.save(weights, malformed)
        malformed_sha = hashlib.sha256(malformed.read_bytes()).hexdigest()
        try:
            load_source_state_dict(source, malformed, sha256=malformed_sha, seed=24)
        except ValueError as error:
            if "shape differs" not in str(error):
                raise
        else:
            raise ValueError("Incompatible checkpoint tensor was accepted")
    return {
        "schema": "opent1d.c1.g2p2c-actor-source-probe/1",
        "source_commit": source_audit["commit"],
        "source_actor_sha256": source_audit["source_sha256"]["agents/g2p2c/models.py"],
        "torch_version": torch.__version__,
        "frames": 16,
        "source_local_action_exact_parity": True,
        "unused_handcrafted_feature_inert": True,
        "global_rng_preserved": True,
        "callback_reset_replay": True,
        "weights_only_state_dict_roundtrip": True,
        "checkpoint_hash_rejection": True,
        "checkpoint_shape_rejection": True,
        "stale_cgm_rejected_without_state_change": True,
        "invalid_action_rejected_without_state_change": True,
        "sampled_actions_sha256": actions.hexdigest(),
        "actor_weights": "random initialization, seed 17; no trained checkpoint",
        "eligible_m1_comparator": False,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = audit(args.source)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(f"{args.output}: source_local_action_exact_parity=True")


if __name__ == "__main__":
    main()
