# 0039 — Select a causal rate-action comparator feasibility route

**Status:** Accepted for C1/1.4 source-feasibility preparation, 26 September 2026.

## Context

M1's controller receives released observations and announced meals and sends
U/min commands every three minutes. The [C1/1.3 adapter](../research/c1-oref0-adapter-boundary.md)
shows that unchanged five-minute `oref0` timing can split an M1 interval,
while its source IOB needs confirmed pump history absent from this callback.
A strong published reference is still needed for the C1 missing-meal study.

## Decision

Treat the unmodified `oref0` reference loop as a no-go on the current M1
interface. Retain its pinned source and negative evidence. Select the
published G2P2C method as the next **conditional feasibility candidate**
because its selected state can use CGM and previous commanded insulin and
its basal action is a U/min rate. Keep the M1 boundary restricted to causal
inputs. Do not call the method a qualified comparator without an identified
policy checkpoint, three-minute source fidelity or justified transfer,
matched budget and full verification.

## Alternatives

- Changing `oref0` decision times or assuming its pump receipts would change
  method timing or information; that requires a new named adaptation.
- The screened offline-RL source uses actual meal-on-board in its state and
  has no verified ready checkpoint for this task.
- Native Cambridge MPC uses another engine, controller interface and clock.
  It remains useful on its own track, but does not establish an M1 comparator.

## Consequences and revisit condition

The [C1/1.4 preflight](../research/c1-comparator-route.md) verifies only the
source and causal mapping boundary, and records missing weights and the
five-versus-three-minute training difference. No new native result, efficacy
claim or C1 evaluation freeze follows. Revisit this decision if a source
policy cannot be reproduced or the fair three-minute training and missing-CGM
requirements cannot be met under a declared budget.
