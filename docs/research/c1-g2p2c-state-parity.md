# C1/1.5 — G2P2C source-state parity

**OT-019, 26 September 2026.** This simulator-free replay follows the
[C1/1.4 comparator-route decision](c1-comparator-route.md). It executes the
`StateSpace` class extracted from pinned G2P2C source and compares its
two-feature `float32` state directly with the causal M1 boundary. This closes
one source-mapping question; it does not supply a trained policy or qualify
the method as an M1 comparator.

## Reference and replay

The external [G2P2C source](https://github.com/RL4H/G2P2C/tree/37f7b7e161e9c1e7b702c8eebdc5cc7eb4f81d70)
is pinned to commit `37f7b7e161e9c1e7b702c8eebdc5cc7eb4f81d70` and
verified clean with the C1 source-file hashes before execution. The
[source-state probe](../../experiments/c1/g2p2c_state_parity.py) loads only
the source `StateSpace` class and pure scaling function in a separate
[NumPy-only locked environment](../../experiments/c1/g2p2c_source/pyproject.toml).
It does not import or modify the source worker, policy or simulator. A
16-frame synthetic sequence spans and wraps the 12-sample history at the M1
three-minute cadence. Each source state has shape 12 × 2 and exactly matches
the local state after conversion to source `float32`; a fresh reset also
matches. Changing source meal, carb, meal-type and hour arguments leaves this
selected state unchanged. The selected source setting disables handcrafted
policy features; its worker still reads private simulator fields elsewhere,
so direct worker reuse remains outside the causal contract.

From the OpenT1D root with a clean external G2P2C checkout:

```sh
uv sync --locked --project experiments/c1/g2p2c_source
uv run --locked --project experiments/c1/g2p2c_source python \
  -m experiments.c1.g2p2c_state_parity \
  --source /path/to/external/G2P2C \
  --output results/c1-g2p2c-state-parity.json
```

The ignored report and fresh-process byte-identical repeat are recorded in
the [C1 evidence index](../../experiments/c1/evidence-index.json). It records
16/16 exact state frames, reset parity and selected-state private-field
invariance. These are synthetic source-software checks, not CGM or insulin
outcomes.

## Policy route remains open

The pinned G2P2C repository tracks no actor checkpoint. The source's default
training sensor is GuardianRT at five minutes; M1 uses three-minute Dexcom.
The official [RL4T1D successor source](https://github.com/RL4H/RL4T1D/tree/ea9e1723b1d0961474887af3de2f683c941881bd)
was screened at commit `ea9e1723b1d0961474887af3de2f683c941881bd`:
it likewise tracks no policy checkpoint, defaults to GuardianRT and lists
CUDA-specific PyTorch wheels in its requirements. This does not resolve the
three-minute policy gap. Its published configuration is a useful later
training-plan reference, not an already qualified M1 comparator.

The next gate is a separately locked, source-traceable three-minute policy
training or justified transfer with a checkpoint hash, profile/seed and
development-budget declaration. Then verify the actual policy tensor and
sampled-action path, RNG/reset behavior, stale-CGM response and failure
accounting on M1's causal callback before a separately frozen known-case
development comparison. This package runs no new M1 evaluation matrix and
supports no comparator-effectiveness or treatment claim.
