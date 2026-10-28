# 0040 — Keep G2P2C checkpoint identity separate from eligibility

**Status:** Accepted for C1/1.6 source-actor preparation, 26 September 2026.

## Context

The selected G2P2C source writes complete PyTorch actor objects containing
Python class references. C1 needs a source-traceable actor on M1's causal
callback, while training, three-minute fidelity and a fair development
budget are still unverified. A randomly initialized actor can exercise the
software boundary but cannot serve as a scientific comparator.

## Decision

Construct the actor only from hash-checked source definitions. Accept only a
separately exported actor `state_dict` whose bytes match a declared SHA-256;
load tensor weights with PyTorch's weights-only mode and strict key/shape
matching. Keep the sampling RNG local to each sequential controller and
reset it explicitly. Reject stale CGM and invalid actor output without
advancing controller state. Do not label a checkpoint eligible from file
identity or source-forward parity alone.

## Alternatives

- Loading upstream whole-object `.pth` files directly couples intake to
  Python pickle execution and ambient module paths; it is not selected.
- Treating the source's five-minute trained policy as a three-minute M1
  policy without transfer evidence is not selected.
- Using an untrained actor as a numerical comparator is not selected.

## Consequences and revisit condition

The [C1/1.6 probe](../research/c1-g2p2c-actor-boundary.md) can verify M1
callback, action and checkpoint mechanics without a simulator or a trained
policy. Existing source whole-object checkpoints need a trusted, separately
recorded state-dict export before intake. Revisit this boundary if the source
actor architecture, serialization format or a trained policy requires a
different mapping; reverify parity and the C1 information contract before
native development scoring.
