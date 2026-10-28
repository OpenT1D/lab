# 0038 — Keep OpenAPS receipts distinct from M1 commands

**Status:** Accepted for C1/1.3 simulator-free preparation, 26 September 2026.

## Context

Pinned `oref0` computes IOB from pump-history delivery events and maintains
temporary basal commands over time. M1's causal controller interface offers
previous rate commands, not pump-confirmed delivery. M1 takes U/min actions
every three minutes; the upstream reference uses five-minute decision
timing and U/hour temps. Treating M1 commands as delivered boluses or moving
source decisions silently would change the meaning of the comparison.

## Decision

Keep prior M1 commands and explicit pump receipts as separate types. Only
the latter may enter a source-native IOB replay. Project a source temp onto
M1 only when its state is constant over the entire three-minute interval;
otherwise reject it. Preserve no-op, cancel, expiry and reset explicitly.
The prototype does not grant controllers access to M1's modeled delivery
field or change M1's historical protocol.

## Consequences

Source-native synthetic IOB and aligned temp projection can be verified
without a simulator. An unmodified five-minute `oref0` comparator remains
ineligible on the current M1 interface. Adding a causally justified receipt
channel or an altered timing method requires a separate review and method
label before any native development matrix. The original C1 study gates and
the earlier failed upstream example parity remain open.
