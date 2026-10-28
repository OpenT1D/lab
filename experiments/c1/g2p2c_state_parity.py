"""Replay pinned G2P2C StateSpace against the causal M1 state boundary.

Run with the separate NumPy-only C1 environment. This extracts the pinned
source class without importing its unrelated policy/training dependencies.
"""

import argparse
import ast
import hashlib
import json
from collections import deque
from pathlib import Path
from types import SimpleNamespace

import numpy as np

from experiments.m1.contracts import Action, Observation

from .comparator_route_preflight import _g2p2c_source, _source_function
from .g2p2c_boundary import CausalState


def _source_state_class(source):
    source = Path(source)
    path = source / "utils/statespace.py"
    tree = ast.parse(path.read_text())
    state_class = next(
        node for node in tree.body if isinstance(node, ast.ClassDef) and node.name == "StateSpace"
    )
    scale = _source_function(source / "utils/core.py", "linear_scaling")
    scope = {"np": np, "deque": deque, "core": SimpleNamespace(linear_scaling=scale)}
    exec(
        compile(
            ast.fix_missing_locations(ast.Module(body=[state_class], type_ignores=[])),
            str(path),
            "exec",
        ),
        scope,
    )
    return scope["StateSpace"]


def audit(source):
    source = Path(source).resolve()
    source_audit = _g2p2c_source(source)
    params = _source_function(source / "agents/g2p2c/parameters.py", "set_args")(
        SimpleNamespace(
            return_type="average",
            debug=0,
            glucose_min=39,
            glucose_max=600,
            insulin_min=0,
        )
    )
    source_type = _source_state_class(source)
    no_private = source_type(params)
    private_varied = source_type(params)
    local = CausalState()
    previous = None
    digest = hashlib.sha256()
    for index in range(16):
        minute = 3 * index
        glucose = 90 + (index * 37) % 180
        observation = Observation(minute, glucose, minute, True)
        insulin = 0 if previous is None else previous.basal_u_min
        local_float32 = np.asarray(
            local.update(observation, previous_action=previous), dtype=np.float32
        )
        from_source, _ = no_private.update(cgm=glucose, ins=insulin)
        varied, _ = private_varied.update(
            cgm=glucose,
            ins=insulin,
            meal=20,
            hour=23,
            meal_type=1,
            carbs=120,
        )
        if from_source.shape != (12, 2) or not np.array_equal(local_float32, from_source):
            raise ValueError(f"Source/local state mismatch at minute {minute}")
        if not np.array_equal(from_source, varied):
            raise ValueError(f"Private source fields changed two-feature state at minute {minute}")
        digest.update(from_source.tobytes())
        previous = Action(0.01 + (index % 5) * 0.03, 0)

    local.reset()
    fresh = source_type(params)
    reset_obs = Observation(0, 140, 0, True)
    local_reset = np.asarray(local.update(reset_obs), dtype=np.float32)
    source_reset, _ = fresh.update(cgm=140, ins=0)
    if not np.array_equal(local_reset, source_reset):
        raise ValueError("Source/local reset state mismatch")

    return {
        "schema": "opent1d.c1.g2p2c-state-parity/1",
        "source_commit": source_audit["commit"],
        "source_state_sha256": source_audit["source_sha256"]["utils/statespace.py"],
        "frames": 16,
        "source_state_shape": [12, 2],
        "source_state_sequence_sha256": digest.hexdigest(),
        "float32_exact_parity": True,
        "private_source_fields_inert_under_selected_flags": True,
        "reset_parity": True,
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
    print(f"{args.output}: float32_exact_parity={result['float32_exact_parity']}")


if __name__ == "__main__":
    main()
