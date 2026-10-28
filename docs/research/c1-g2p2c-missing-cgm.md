# C1/1.9 — G2P2C missing-CGM callback boundary

**OT-019, 26 September 2026.** The [C1/1.6 source-actor callback](c1-g2p2c-actor-boundary.md)
rejects stale observations. [Decision 0043](../decisions/0043-c1-g2p2c-missing-cgm.md)
adds an explicit opt-in fallback for M1's masked-sensor condition D. This
package tests causal software behavior with random actor weights. It does
not run a native outcome case or qualify a trained comparator.

## Declared behavior

For a missing M1 `Observation`, the
[adapter](../../experiments/c1/g2p2c_policy_adapter.py) returns the selected
profile's pinned basal command and zero bolus. It validates that the call is
the next three-minute step, the held timestamp/glucose match the last fresh
sample, and the observation age is at most 30 minutes. No actor inference,
history append or sampling RNG advance occurs. At the first fresh sample,
the [causal state](../../experiments/c1/g2p2c_boundary.py) starts a new
zero-filled 12-sample window with that fresh glucose and the preceding
basal command. The actor RNG continues from before the gap. This permits
condition D's ten masked intervals without treating held CGM as fresh.

The basal values from the pinned simglucose parameter table and source pump
formula are `0.02112267499992533` U/min for adult#001 and
`0.022825539499994` U/min for adult#002. The selected value is an explicit
controller argument, bounded to 0–0.1 U/min. A study runner must bind it
to the frozen profile before native execution. The default adapter mode
continues to reject stale CGM, preserving the earlier source-parity
boundary.

## Executed synthetic check

The [probe](../../experiments/c1/g2p2c_fallback_probe.py) used the clean
pinned G2P2C source and random actor weights. It verified ten consecutive
profile-basal outputs, unchanged actor state/RNG during the gap, a
zero-filled recovery state with the first fresh CGM and prior basal,
reset replay, weights-only intake parity, and atomic rejection of a
changed held value or a gap beyond 30 minutes. Its ignored report
`results/c1-g2p2c-fallback-probe.json` has SHA-256
`ea908eae4b457642549f024e9c901db6348831f41786226229a839dc3156ffb4`;
a fresh process produced identical bytes. The [C1 evidence index](../../experiments/c1/evidence-index.json)
records it. Root tests cover state restart and clock validation.

## Remaining gate

Complete the [C1/1.8 training attempts](c1-g2p2c-training-freeze.md),
export and verify each actor, bind each profile's fallback basal, then
exercise native M1 A/B/C/D callbacks and stops before opening a separately
frozen matched development matrix. This synthetic fallback check does not
establish modeled benefit, safety or strong-comparator eligibility.
