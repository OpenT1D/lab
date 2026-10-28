# C1/1.6 — G2P2C source actor and checkpoint boundary

**OT-019, 26 September 2026.** This package extends the
[C1/1.5 source-state replay](c1-g2p2c-state-parity.md) to the pinned G2P2C
actor's actual sampled-action path and a causal M1 controller callback. The
test actor has **random initial weights**. It is never run in a native glucose
case and is not a qualified comparator.

## Source-faithful callback

The [policy adapter](../../experiments/c1/g2p2c_policy_adapter.py) first
verifies the clean [G2P2C source](https://github.com/RL4H/G2P2C/tree/37f7b7e161e9c1e7b702c8eebdc5cc7eb4f81d70)
and pinned file hashes. It executes the source `FeatureExtractor`,
`ActionModule`, `GlucoseModel` and `ActorNetwork` definitions. Only their
referenced source scaling function and runtime libraries are supplied; the
source worker, simulator, reward and training code are not imported. The
adapter maps M1's released `Observation` and its own preceding U/min command
to the verified 12 × 2 `float32` source state, calls the source actor's
`forward` method, and applies the pinned exponential U/min pump transform.
It ignores permitted meal announcements because this selected policy variant
does not use them. It cannot read M1's private completed row, actual meals,
latent glucose or modeled delivery.

The source actor samples an action even in its testing path and also samples
its glucose-model output. The adapter maintains a per-controller CPU PyTorch
RNG state, restores it on reset, and preserves the caller's global RNG. A
rejected stale observation or nonfinite policy output leaves its causal
history, prior command and RNG unadvanced. This is a sequential CPU callback
boundary; no native outcome or parallel-worker reproducibility is claimed.

The source repository saves whole Python actor objects. [Decision
0040](../decisions/0040-c1-g2p2c-checkpoint-boundary.md) instead requires a
separately exported `state_dict` for OpenT1D intake. Its bytes must match a
declared SHA-256, `torch.load(..., weights_only=True)` is used, and every
tensor key and shape must match the source actor exactly. The probe tests a
temporary **untrained** `state_dict`; no trained weight file is present or
stored in Git. A checkpoint's hash proves identity, not its training quality
or fair comparator status.

## Executed software check

The separate [locked CPU environment](../../experiments/c1/g2p2c_policy_source/pyproject.toml)
uses NumPy 1.26.4 and PyTorch 2.2.0 on macOS arm64. The upstream requirements
specify PyTorch 2.2.0 with CUDA 11.8 packages; this CPU run verifies the
forward path under the same core PyTorch version, not upstream GPU training
parity. From the repository root with a clean external checkout:

```sh
uv sync --locked --project experiments/c1/g2p2c_policy_source
uv run --locked --project experiments/c1/g2p2c_policy_source python \
  -m experiments.c1.g2p2c_actor_source_probe \
  --source /path/to/external/G2P2C \
  --output results/c1-g2p2c-actor-source-probe.json
```

The [probe](../../experiments/c1/g2p2c_actor_source_probe.py) compares 16
sampled source actions with M1 callback outputs under the same RNG state,
including history wrap; an unused handcrafted feature does not affect them.
It checks reset replay, global RNG preservation, exact temporary
weights-only round-trip, changed-hash and wrong-shape rejection, stale CGM
and invalid-action failure atomicity. Its ignored report and byte-identical
fresh-process repeat are in the [C1 evidence index](../../experiments/c1/evidence-index.json).
These are source-software checks using invented CGM inputs and random weights.

## Remaining gate

No policy checkpoint is tracked in the pinned G2P2C repository or its
[official release list](https://github.com/RL4H/G2P2C/releases). Its default training uses a five-minute sensor and
cannot be called an M1 three-minute policy. The next substantive work is a
declared three-minute training or justified transfer protocol, a trained
actor `state_dict` with source and training provenance, and verification of
its actual inference under M1's causal inputs and condition D fallback. A
matched development budget and separately frozen known-case comparison must
follow before comparator eligibility. No new M1 matrix, efficacy result or
treatment claim is produced here.
