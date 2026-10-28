# C1/1.8 — Three-minute G2P2C training freeze

**OT-019, 26 September 2026.** This record freezes two source-training
attempts before they run, following the [C1/1.7 engine preflight](c1-g2p2c-training-preflight.md).
It is a training configuration and executable short-run check, not a trained
comparator or an M1 development outcome. [Decision 0042](../decisions/0042-c1-g2p2c-training-freeze.md)
explains the source deviations.

## Fixed attempts

The committed [plan](../../experiments/c1/g2p2c-training.json) names the
pinned source and M1-engine commits, Dexcom/Insulet on a three-minute clock,
CPU execution, adult#001 and adult#002, source patient IDs 20 and 21, and
one seed-17 full attempt per profile. There is no best-of-seeds or
internal-test checkpoint selection. The source final actor at rollout 195
is the only planned checkpoint candidate. `G2P2C.run` stops after exceeding
800,000 training interactions; 16 × 256 steps per rollout yields 802,816
after 196 rollouts. Source tests and its final validation are diagnostics
and do not authorize an M1 outcome matrix.

The 12-sample CGM/command state remains the verified source architecture:
36 minutes of three-minute history. Calibration also remains 12 samples.
The 480-step diagnostic test episode restores 24 hours, the 4,800-step
maximum training episode restores 10 days, and the 10-step planning horizon
restores 30 minutes. One diagnostic testing worker reduces repeated source
tests without changing training-worker updates. These are explicit
three-minute method adaptations, not a reproduction of five-minute results.
The [pinned source loop](https://github.com/RL4H/G2P2C/blob/37f7b7e161e9c1e7b702c8eebdc5cc7eb4f81d70/agents/g2p2c/g2p2c.py#L455-L472)
writes its terminal status-2 row before running 500 final validation
rollouts. The launcher exports the final actor only after those source
diagnostics finish; the status-2 row alone is not a completed attempt.

## Non-destructive launcher

The [launcher](../../experiments/c1/g2p2c_training_run.py) verifies the
clean G2P2C checkout and exact installed M1 simglucose bytes before source
training imports. It checks the plan's physical-time arithmetic and
source-policy feature flags. It creates a new ignored `results/` directory,
records the plan, source preflight, arguments and dependency-lock hash, and
refuses an existing output directory. Unlike the upstream CLI, it seeds
PyTorch before actor construction. It fixes one CPU thread and deterministic
PyTorch operations, preserves failed partial attempts, and requires the
source's declared terminal rollout/status before marking completion. For a
full run it exports a weights-only actor `state_dict` from the live model,
without deserializing whole-object source checkpoints.

With the [locked training environment](../../experiments/c1/g2p2c_training_source/pyproject.toml)
and a clean external G2P2C checkout:

```sh
uv sync --locked --project experiments/c1/g2p2c_training_source
uv run --locked --project experiments/c1/g2p2c_training_source python \
  -m experiments.c1.g2p2c_training_run \
  --source /path/to/external/G2P2C --profile adult#001 \
  --mode full
```

The second planned attempt uses `--profile adult#002`. Full mode writes only
to the respective fixed `results/c1-g2p2c-training-adult00*` directory. Do
not remove a failed directory to turn a retry into the same recorded attempt.
The `--mode smoke --smoke-output results/UNIQUE-ID` route exercises the same
clock overrides with the source's 4,000-interaction debug stop.

## Short-run verification

An adult#001 smoke completed eight rollouts and 4,096 interactions with the
fixed 480-step diagnostic horizon, 4,800-step training episode and 10-step
planning horizon. Two further fresh-process smoke runs produced the same
final actor-tensor SHA-256
`14983bece04753ad40b6a21e803f19b715f2751ba1f3a1739f0a408243cac03c`.
Their source-preflight, plan and attempt metadata were byte-identical; the
arguments differed only in the distinct output path. This checks same-host
short-run determinism, not full-run reproducibility or glucose-control
quality. The local ignored logs and attempt records are indexed in the
[C1 evidence index](../../experiments/c1/evidence-index.json).

## Actor constructor parity

The [actor-constructor preflight](../../experiments/c1/g2p2c_architecture_preflight.py)
checks that the frozen training actor and the weights-only intake actor use
the same source settings, including the ten-step planning horizon. Source
`set_args` had restored a six-step default in the intake constructor; the
adapter now sets the frozen ten-step value after `set_args`. On both planned
profiles, all 20 initialized tensor names, shapes, dtypes and values match
under the same seed. Seven source/intake forward outputs match exactly on
each of 16 invented states with the same random stream. A weights-only
`state_dict` exported from each actual source actor also loads strictly
through the intake adapter with identical tensors and sampled outputs. The
ignored report `results/c1-g2p2c-architecture-preflight-roundtrip.json`
has SHA-256
`9c24fa23746556cb87d57ebaf7ce9a9d06842bc472e8d1c050ed64f4c9512a88`;
a second process produced identical bytes. The earlier actor-source and
sensor-fallback probe reports also retained their exact hashes after the
constructor correction. This verifies the constructor and untrained
forward/intake path, not the final learned weights or native behavior. The trained
checkpoint intake repeats this constructor check before loading weights.

## After full source training

Both frozen attempts completed 196 source rollouts, 802,816 training
interactions and all 500 final source validation rollouts per profile. The
weights-only actor checkpoint SHA-256 values are
`7b8f87cff41e2971c66cee4ca1ac0ce2fa56e263e0f45d96db4893e9d112e273`
for adult#001 and
`3fa5f9a12f43154d8aaacd82ff5854e5c9a9aa87710f8c1e84eeb97611fbdcc9`
for adult#002.
The [trained preflight](../../experiments/c1/g2p2c_trained_preflight.py)
strictly loaded each checkpoint, matched its tensor digest, matched all seven
source/intake actor forward outputs on 16 invented states for each profile,
and replayed 741 invented causal commands twice with reset and ten
missing-CGM intervals. Two fresh processes per profile wrote byte-identical
reports with SHA-256
`2331e4d8d61bd4f5b7312892850403b38aa861f7449da3e0264fc72e6877637f`
for adult#001 and
`58517ca934768e9b434e4417b8196ca2e85f6cab2d06b1eeb8c8d25c786a7e30`
for adult#002. The ignored attempt, checkpoint, summary and report hashes are
indexed in the [C1 evidence index](../../experiments/c1/evidence-index.json).
These are one full training attempt per profile, not full-run repeatability
across new seeds or a comparator qualification.

The [C1/1.10 native smoke](c1-g2p2c-native-smoke-plan.md) checks trained
condition-D inference, native completion, sensor fallback and action bounds.
Native A/B/C behavior and comparative performance remain untested. A matched
development roster needs its own freeze of the original candidate, reference
coverage, information and setting budgets before any new case execution.
No strong comparator qualification or efficacy claim is made here.
