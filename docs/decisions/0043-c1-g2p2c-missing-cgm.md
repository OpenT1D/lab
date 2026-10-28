# 0043 — Use declared profile basal during a missing-CGM interval

**Status:** Accepted for C1/1.9 comparator-interface preparation, 26 September 2026.

## Context

The pinned G2P2C actor consumes current CGM and its preceding commanded
insulin. It has no source-defined missing-CGM input. M1 condition D masks
ten three-minute observations on the scored day (12:00–12:30). Passing the
last sensor value to the actor as if it were fresh would change its causal
state without a measurement; rejecting every masked step would prevent
the planned condition from running.

## Decision

For an explicitly configured profile basal, command that basal and zero
bolus at each missing observation for at most 30 minutes. The pinned
simglucose parameter table and G2P2C pump formula
`u2ss * BW / 6000` give adult#001
`0.02112267499992533` U/min and adult#002 `0.022825539499994` U/min.
The controller must receive the selected value as frozen profile
configuration; it cannot inspect the private native patient object.

During the gap, leave actor history and sampling RNG unchanged. Check
the three-minute clock and that the held observation still identifies the
last fresh CGM. Reject a longer gap, a changed held value or an unavailable
first observation. At the first fresh reading after the gap, clear the
12-sample source history, insert that reading and the preceding basal
command, then resume source-actor inference without resetting its RNG.
Keep the existing strict rejection mode as the default for source-parity
checks; opt into this fallback for M1 condition D.

## Consequences

The policy's A/B/C actor path stays as previously checked. Condition D now
has a separately declared interface adaptation, not exact upstream
missing-CGM behavior. Holding profile basal and restarting history may
change modeled outcomes; it is a research comparator convention, not a
clinical safety guarantee. [C1/1.9](../research/c1-g2p2c-missing-cgm.md)
checks synthetic callback behavior with random weights. A trained actor
must still pass actual M1 native execution, action/stop checks and a
separately frozen matched development comparison before eligibility.
