"""Source-pinned G2P2C actor and causal M1 callback for checkpoint intake.

The adapter verifies source code and weight bytes. Training provenance,
three-minute policy fidelity and comparator eligibility are separate gates.
"""

import ast
import copy
import math
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as functional

from experiments.m1.contracts import STEP, Action, Observation

from .comparator_route_preflight import _g2p2c_source, _source_function
from .g2p2c_boundary import CausalState, pump_rate
from .g2p2c_checkpoint import load_actor_weights, require_runtime


def _source_actor_class(source):
    path = source / "agents/g2p2c/models.py"
    names = {
        "FeatureExtractor",
        "GlucoseModel",
        "ActionModule",
        "ActorNetwork",
        "NormedLinear",
    }
    nodes = [
        node
        for node in ast.parse(path.read_text()).body
        if isinstance(node, (ast.ClassDef, ast.FunctionDef)) and node.name in names
    ]
    if {node.name for node in nodes} != names:
        raise ValueError("Pinned actor source definitions are incomplete")
    scale = _source_function(source / "utils/core.py", "linear_scaling")
    scope = {
        "math": math,
        "np": np,
        "torch": torch,
        "nn": nn,
        "F": functional,
        "core": SimpleNamespace(linear_scaling=scale),
    }
    exec(
        compile(
            ast.fix_missing_locations(ast.Module(body=nodes, type_ignores=[])),
            str(path),
            "exec",
        ),
        scope,
    )
    return scope["ActorNetwork"]


def new_source_actor(source, *, initialization_seed):
    source = Path(source).resolve()
    source_audit = _g2p2c_source(source)
    if type(initialization_seed) is not int or not 0 <= initialization_seed < 2**63:
        raise ValueError("Invalid actor initialization seed")
    args = _source_function(source / "agents/g2p2c/parameters.py", "set_args")(
        SimpleNamespace(
            return_type="average",
            debug=0,
            glucose_min=39,
            glucose_max=600,
            insulin_min=0,
            n_action=1,
            planning_n_step=3,
            n_planning_simulations=5,
        )
    )
    # set_args replaces the caller's planning value with its five-minute
    # default. Match the frozen C1/1.8 three-minute training constructor.
    args.planning_n_step = 10
    with torch.random.fork_rng(devices=[]):
        torch.manual_seed(initialization_seed)
        actor = _source_actor_class(source)(args, torch.device("cpu"))
    return actor, source_audit


class CausalActorAdapter:
    """M1 callback using a supplied source actor; no qualification implied."""

    def __init__(self, actor, *, seed, missing_fallback_basal_u_min=None):
        if type(seed) is not int or not 0 <= seed < 2**63:
            raise ValueError("Invalid policy sampling seed")
        if not isinstance(actor, nn.Module):
            raise ValueError("Expected a pinned source actor module")
        if missing_fallback_basal_u_min is not None and (
            type(missing_fallback_basal_u_min) not in (int, float)
            or not math.isfinite(missing_fallback_basal_u_min)
            or not 0 <= missing_fallback_basal_u_min <= 0.1
        ):
            raise ValueError("Expected an explicit bounded profile basal for missing CGM")
        self.actor = actor.cpu()
        self.actor.requires_grad_(False)
        self.seed = seed
        self.missing_fallback_basal_u_min = missing_fallback_basal_u_min
        self.reset()

    def reset(self):
        self.state = CausalState()
        self.previous = None
        with torch.random.fork_rng(devices=[]):
            torch.manual_seed(self.seed)
            self._rng_state = torch.get_rng_state().clone()
        self._last_time = None
        self._last_fresh_time = None
        self._last_fresh_cgm = None
        self._in_gap = False

    def command(self, observation, announced_g):
        if not isinstance(observation, Observation):
            raise ValueError("Only the released M1 observation is accepted")
        if type(announced_g) not in (int, float) or not math.isfinite(announced_g):
            raise ValueError("Invalid announced meal amount")
        if announced_g < 0:
            raise ValueError("Announced meal amount must be nonnegative")
        if self._last_time is not None and observation.time_min != self._last_time + STEP:
            raise ValueError("Expected the next three-minute observation")
        if not observation.available and self.missing_fallback_basal_u_min is not None:
            if (
                self.previous is None
                or observation.source_time_min != self._last_fresh_time
                or observation.glucose_mg_dl != self._last_fresh_cgm
                or observation.age_min > 30
            ):
                raise ValueError(
                    "Missing-CGM fallback requires the last fresh sample within 30 min"
                )
            fallback = Action(self.missing_fallback_basal_u_min, 0.0)
            self.previous = fallback
            self._last_time = observation.time_min
            self._in_gap = True
            return fallback
        proposed_state = copy.deepcopy(self.state)
        history = (
            proposed_state.restart_after_gap(observation, previous_action=self.previous)
            if self._in_gap and observation.available
            else proposed_state.update(observation, previous_action=self.previous)
        )
        tensor = torch.as_tensor(history, dtype=torch.float32)
        feature = torch.tensor([0.0], dtype=torch.float32)
        with torch.no_grad(), torch.random.fork_rng(devices=[]):
            torch.set_rng_state(self._rng_state)
            sampled = self.actor(tensor, feature, None, "forward")[2]
            next_rng = torch.get_rng_state().clone()
        if not isinstance(sampled, torch.Tensor) or sampled.shape != (1,):
            raise ValueError("Source actor must return one scalar action")
        action = pump_rate(float(sampled.item()))
        self.state = proposed_state
        self._rng_state = next_rng
        self.previous = action
        self._last_time = observation.time_min
        self._last_fresh_time = observation.time_min
        self._last_fresh_cgm = observation.glucose_mg_dl
        self._in_gap = False
        return action


def load_source_state_dict(source, checkpoint, *, sha256, seed, missing_fallback_basal_u_min=None):
    """Load only matching tensor weights from the exact supplied bytes."""
    require_runtime()
    actor, _ = new_source_actor(source, initialization_seed=0)
    weights = load_actor_weights(checkpoint, sha256=sha256, expected=actor.state_dict())
    actor.load_state_dict(weights, strict=True)
    return CausalActorAdapter(
        actor, seed=seed, missing_fallback_basal_u_min=missing_fallback_basal_u_min
    )
