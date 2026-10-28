# 0042 — Freeze the three-minute G2P2C source-training attempt

**Status:** Accepted for C1/1.8 source training, 26 September 2026.

## Context

Decision [0041](0041-c1-g2p2c-training-engine.md) pins M1 physiology and
Dexcom to a feasible source loop. The upstream G2P2C CLI sets its seed only
after constructing the actor, so that seed does not fix initial actor
weights. Its default episode and planning lengths are step counts written
for a five-minute sensor; unchanged counts shorten their physical duration
on M1's three-minute clock. The source output setup also deletes an existing
directory with the selected name.

## Decision

Use the committed [training plan](../../experiments/c1/g2p2c-training.json)
and [launcher](../../experiments/c1/g2p2c_training_run.py) for at most one
full attempt on each known C1 profile, adult#001 and adult#002. Retain the
source actor's 12 × 2 CGM/command history and 12-step calibration, each now
36 minutes, so the previously verified actor and callback shapes remain
unchanged. Set the diagnostic test horizon to 480 steps (24 hours), maximum
training episode to 4,800 steps (10 days) and planning horizon to 10 steps
(30 minutes). Preserve 16 training workers, 256 steps per worker and the
source 800,000-interaction stop threshold: 196 rollouts reach 802,816
interactions, ending at rollout 195. Use one testing worker for source
diagnostics only; its outcomes cannot select a checkpoint.

Seed Python, NumPy and PyTorch **before** source actor construction, use one
CPU thread and deterministic PyTorch algorithms. Use source seed 17 for each
profile. Select only the last scheduled actor and export its `state_dict`
directly from the live model after source completion. Do not load the
source's whole-object checkpoint to export it. The launcher fails if an
output directory already exists; a failed attempt stays visible and any new
attempt needs an explicit amended record. No M1 case is scored by this
training plan.

## Consequences and remaining gate

The three-minute variant has a shorter 36-minute observation history than
the source's five-minute, 60-minute default. Its physical-time adaptations
and early seeding are declared deviations, so original published performance
cannot be transferred to this policy. Source training uses random scenarios
and initial glucose, while M1 has fixed case scenarios. The source worker's
random environment seeds are worker-derived and do not change with the
declared actor seed. The source's testing episodes are diagnostics, not a
selection set or evidence of comparable information at M1 inference.

The [C1/1.8 record](../research/c1-g2p2c-training-freeze.md) verifies the
launcher on short runs. A full trained policy must still pass checkpoint,
causal-input, missing-sensor and native-stop checks. A separate matched M1
development freeze must specify comparator and candidate budgets before any
new matrix. This decision does not qualify G2P2C as a strong comparator.
