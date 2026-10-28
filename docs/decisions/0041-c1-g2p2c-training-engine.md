# 0041 — Pin G2P2C training to M1's physiological engine

**Status:** Accepted for C1/1.7 training preparation, 26 September 2026.

## Context

The pinned G2P2C checkout bundles a modified simglucose 0.2.2 source. Its
patient meal equation adds accumulated food in grams to a stomach quantity in
milligrams, whereas M1's pinned simglucose revision converts the grams by
1,000. Its episode termination thresholds are also 70–350 mg/dL, compared
with M1's 10–600 mg/dL. Identical patient and sensor parameter tables do not
make these engines physiologically equivalent. The default G2P2C training
sensor is five-minute GuardianRT, while M1 uses three-minute Dexcom.

## Decision

Keep the pinned G2P2C agent, worker and training source, but import
`simglucose` from a separate locked environment at M1's exact revision
`a6f6777586c860457a2a1e6cce6d0bd3fd33d1cc`. Select Dexcom explicitly.
The executable preflight must reject a different imported engine, a changed
source file, a changed lock or an altered meal/termination equation. Treat a
debug training run only as an integration check. A training configuration and
selection rule must be frozen before any full training or M1 development
comparison; the existing historical matrices stay intact.

## Consequences

This route changes the G2P2C training environment relative to its bundled
reference and cannot inherit published or bundled-fork performance claims.
Its source random-scenario training distribution still differs from M1's
fixed case scenarios. Feature history, testing horizon, planning horizon,
training budget, profiles, seeds and checkpoint selection need explicit
three-minute decisions. The [C1/1.7 record](../research/c1-g2p2c-training-preflight.md)
documents the passing short debug run and remaining gate. A checkpoint still
requires the separate source-actor intake and causal-inference checks in
[decision 0040](0040-c1-g2p2c-checkpoint-boundary.md).
