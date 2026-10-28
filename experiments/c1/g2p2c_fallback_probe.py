"""Check a declared basal fallback across synthetic missing-CGM intervals."""

import argparse
import hashlib
import json
import tempfile
from pathlib import Path

import numpy as np
import torch

from experiments.m1.contracts import Action, Observation

from .g2p2c_policy_adapter import CausalActorAdapter, load_source_state_dict, new_source_actor


def _run_gap(adapter):
    first = adapter.command(Observation(0, 90, 0, True), 0)
    before_gap_rng = adapter._rng_state.clone()
    for minute in range(3, 31, 3):
        held = adapter.command(Observation(minute, 90, 0, False), 0)
        if held != Action(0.02112267499992533, 0.0):
            raise ValueError("Missing CGM did not use the declared profile basal")
        if adapter.state._time_min != 0 or not torch.equal(adapter._rng_state, before_gap_rng):
            raise ValueError("Missing CGM advanced actor state or RNG")
    recovered = adapter.command(Observation(33, 150, 33, True), 0)
    state = np.asarray(adapter.state._history, dtype=np.float32)
    if not np.array_equal(state[:-1], np.zeros((11, 2), dtype=np.float32)):
        raise ValueError("A gap leaked stale CGM into restarted actor history")
    expected_last = np.asarray(
        [((150 - 39) * 2 / (600 - 39)) - 1, (0.02112267499992533 * 2 / 5) - 1],
        dtype=np.float32,
    )
    if not np.array_equal(state[-1], expected_last):
        raise ValueError("Restart lost the new CGM or the preceding basal command")
    return first, recovered


def audit(source):
    source = Path(source).resolve()
    torch.set_num_threads(1)
    torch.use_deterministic_algorithms(True)
    actor, source_audit = new_source_actor(source, initialization_seed=17)
    basal = 0.02112267499992533
    adapter = CausalActorAdapter(actor, seed=24, missing_fallback_basal_u_min=basal)
    global_before = torch.get_rng_state().clone()
    first, recovered = _run_gap(adapter)
    adapter.reset()
    if _run_gap(adapter) != (first, recovered):
        raise ValueError("Fallback and recovery changed after reset")
    if not torch.equal(global_before, torch.get_rng_state()):
        raise ValueError("Fallback changed the caller's PyTorch RNG")

    adapter.reset()
    adapter.command(Observation(0, 90, 0, True), 0)
    before = (adapter._last_time, adapter.previous, adapter._rng_state.clone())
    try:
        adapter.command(Observation(3, 91, 0, False), 0)
    except ValueError:
        pass
    else:
        raise ValueError("Changed held CGM was accepted")
    if (adapter._last_time, adapter.previous) != before[:2] or not torch.equal(
        adapter._rng_state, before[2]
    ):
        raise ValueError("Rejected held observation changed state")
    adapter.command(Observation(3, 90, 0, False), 0)
    before = (adapter._last_time, adapter.previous, adapter._rng_state.clone())
    try:
        adapter.command(Observation(6, 90, 3, False), 0)
    except ValueError:
        pass
    else:
        raise ValueError("Changed held source timestamp was accepted")
    if (adapter._last_time, adapter.previous) != before[:2] or not torch.equal(
        adapter._rng_state, before[2]
    ):
        raise ValueError("Rejected source timestamp changed state")
    for minute in range(6, 31, 3):
        adapter.command(Observation(minute, 90, 0, False), 0)
    before = (adapter._last_time, adapter.previous, adapter._rng_state.clone())
    try:
        adapter.command(Observation(33, 90, 0, False), 0)
    except ValueError:
        pass
    else:
        raise ValueError("Missing CGM beyond 30 minutes was accepted")
    if (adapter._last_time, adapter.previous) != before[:2] or not torch.equal(
        adapter._rng_state, before[2]
    ):
        raise ValueError("Rejected overlong gap changed state")

    with tempfile.TemporaryDirectory() as temporary:
        weights = Path(temporary) / "random-state-dict.pt"
        torch.save(actor.state_dict(), weights)
        loaded = load_source_state_dict(
            source,
            weights,
            sha256=hashlib.sha256(weights.read_bytes()).hexdigest(),
            seed=24,
            missing_fallback_basal_u_min=basal,
        )
        if _run_gap(loaded) != (first, recovered):
            raise ValueError("Weights-only intake changed fallback or recovery")

    return {
        "schema": "opent1d.c1.g2p2c-fallback-probe/1",
        "source_commit": source_audit["commit"],
        "profile": "adult#001",
        "profile_basal_u_min": basal,
        "missing_intervals": 10,
        "maximum_gap_minutes": 30,
        "actor_rng_unchanged_during_gap": True,
        "last_command_is_profile_basal": True,
        "history_restarted_on_recovery": True,
        "invalid_held_or_overlong_gap_rejected_atomically": True,
        "reset_replay": True,
        "weights_only_intake_parity": True,
        "actor_weights": "random initialization; no trained policy evaluated",
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
    print(f"{args.output}: history_restarted_on_recovery=True")


if __name__ == "__main__":
    main()
