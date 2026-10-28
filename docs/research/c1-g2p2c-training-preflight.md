# C1/1.7 — G2P2C training-engine preflight

**OT-019, 26 September 2026.** This package tests whether the source G2P2C
training loop can run with M1's three-minute sensor and exact physiological
engine. It produces no accepted policy, M1 development matrix or comparator
result. [Decision 0041](../decisions/0041-c1-g2p2c-training-engine.md)
records the engine convention.

## Physiological source boundary

The pinned [G2P2C source](https://github.com/RL4H/G2P2C/tree/37f7b7e161e9c1e7b702c8eebdc5cc7eb4f81d70)
bundles an older simglucose fork. The pinned
[M1 simglucose source](https://github.com/jxx123/simglucose/tree/a6f6777586c860457a2a1e6cce6d0bd3fd33d1cc)
has different equations and stop rules:

| Source | Stomach mass `Dbar` (mg) | Episode ends outside (mg/dL) |
| --- | --- | --- |
| G2P2C bundled fork | `last_Qsto + last_foodtaken` | 70–350 |
| M1 pinned engine | `last_Qsto + last_foodtaken * 1000` | 10–600 |

`last_foodtaken` is tracked in grams. The patient and sensor CSV tables have
matching SHA-256 hashes, but the meal equation and termination rules do not.
A policy trained with the bundled fork cannot be described as trained on M1
physiology. The [preflight](../../experiments/c1/g2p2c_training_preflight.py)
checks the clean G2P2C commit, both simglucose locks, imported package
location, six M1 package hashes, four fork hashes and both source equations.
Its ignored local report `results/c1-g2p2c-training-preflight.json` has
SHA-256 `4271116854d8a130b310e890823432ff942f0331f60a8a4f78bed0ce89de0f67`;
a fresh process produced byte-identical output.

## Executed technical smoke

The isolated [training lock](../../experiments/c1/g2p2c_training_source/pyproject.toml)
pins M1 simglucose, PyTorch 2.2.0 on CPU, NumPy 1.26.4 and the source
training dependencies. The lock's Python 3.12 environment is a compatibility
port of the upstream CUDA/Python package set, not a claim of upstream GPU
reproduction. The installed patient's model, environment, sensor, pump and
two parameter-table files have the same hashes as M1's installed package.

Using a clean external G2P2C checkout at the commit above, the preflight and
source debug command are:

```sh
uv sync --locked --project experiments/c1/g2p2c_training_source
uv run --locked --project experiments/c1/g2p2c_training_source python \
  -m experiments.c1.g2p2c_training_preflight \
  --source /path/to/external/G2P2C \
  --output results/c1-g2p2c-training-preflight.json

MAIN_PATH=/path/to/external/G2P2C \
PYTHONPATH=/path/to/external/G2P2C \
uv run --locked --project experiments/c1/g2p2c_training_source python \
  /path/to/external/G2P2C/experiments/run_RL_agent.py \
  --agent g2p2c --sensor Dexcom --device cpu --debug 1 \
  --patient_id 20 --folder_id UNIQUE-DEBUG-ID --seed 101
```

The source deletes an existing result directory with the same `folder_id`;
use a fresh ID for every run. We used `c1-debug-locked-m1-20260926`. Its
source debug loop completed eight rollouts and 4,096 training interactions,
then printed `Algo RAN Successfully`. The source's fixed debug stop is 4,000
interactions; the final 512-interaction rollout crosses it. We copied only
the args, source log and summary CSV into ignored `results/`, plus a small
provenance report `results/c1-g2p2c-training-debug-report.json` with SHA-256
`d49039ac1d5280ef6643e0b5191e154b5b172bc65f51565417cd867d7ff205c0`.
These values attest loop completion, not glucose-control quality. Debug
checkpoints were not accepted or scored.

## M1 numeric runtime parity

The separately executed [runtime check](../../experiments/c1/g2p2c_runtime_parity.py)
also compares both locked and installed versions of simglucose, NumPy,
SciPy, pandas, gym, pathos and python-dateutil between M0/M1 and the C1
training environment. Both use Python 3.12.13 and the same versions of
those seven packages; the installed simglucose files resolve inside their
respective locked environments. The engine preflight still checks the
exact M1 source revision and critical source-file hashes. The report in
`results/c1-g2p2c-runtime-parity.json` has SHA-256
`796bcb288595159ef89412c62ad2d92f0384abf032f5e32b009ef3ebd23bf20b`;
a fresh process produced byte-identical JSON. The [evidence index](../../experiments/c1/evidence-index.json)
records both files. This verifies the installed core runtime, not equality
of every optional package, a native trajectory or a trained controller.

## Fixed native trajectory cross-check

The [trajectory probe](../../experiments/c1/g2p2c_engine_trajectory_parity.py)
predeclares one actor-independent native engine input: adult#001, sensor
seed 101, 0.02 U/min basal, zero bolus, and 600 minutes on M1's existing
meal scenario. The window includes the first 45 g meal. It requires all
201 initial/three-minute snapshots to complete and writes their exact values
without an environment-dependent path. Run the same committed script in
the locked M0/M1 and C1 training environments, then compare output bytes:

```sh
uv run --locked --project experiments/m0/simglucose python \
  -m experiments.c1.g2p2c_engine_trajectory_parity \
  --output results/c1-g2p2c-engine-trajectory-m1.json
uv run --locked --project experiments/c1/g2p2c_training_source python \
  -m experiments.c1.g2p2c_engine_trajectory_parity \
  --output results/c1-g2p2c-engine-trajectory-training.json
cmp results/c1-g2p2c-engine-trajectory-m1.json \
  results/c1-g2p2c-engine-trajectory-training.json
```

Both locked environments completed the 201-snapshot replay. The files are
byte-identical, with SHA-256
`c88611181720744959d38cdceca75d4f658a8e66fe19e956db0d1ec32d393a59`.
The ignored outputs are indexed in the [C1 evidence index](../../experiments/c1/evidence-index.json).
This is a predeclared engine-software comparison, not G2P2C policy
inference or an M1 development outcome.

## Remaining training gate

The source parameter defaults remain in steps: 12 history and calibration
samples cover 36 minutes on Dexcom instead of 60 on GuardianRT; its
288-step test horizon covers 14.4 hours instead of 24; six planning steps
cover 18 instead of 30 minutes. The source uses random initial glucose and
random training meals, while M1 scores fixed cases. Before full training,
freeze how these physical durations are handled, the source profile and
seed roster, interaction budget, stopping/failure policy and checkpoint
selection without inspecting M1 outcomes. The source's 800,000-interaction
non-debug limit is a default, not an approved C1 budget. Then export a
weights-only actor state dict, verify causal inference and fallback on the
M1 interface, and separately freeze a matched development comparison.
Until then, G2P2C is a technically feasible source method, **not** a
qualified strong M1 comparator.
