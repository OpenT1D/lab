# 0046 — Bound P1 controller intake to one M1 rate-action task

**Status:** Accepted for P1/0.2 implementation, 26 September 2026.

## Context

P1/0.1 packages a fixed M1 task with basal-bolus and PID. The M1 loop can
already receive a controller object, and the C1 G2P2C smoke verifies one
source-specific callback. Neither supplies a declared intake that a
researcher can use for their own method. M1 action names are easy to
misread: both native basal and bolus fields are rates in U/min.

## Decision

Create a separate P1/0.2 workflow over the unchanged M1 synthetic scenario,
clock, physiology and metrics. Accept one trusted local two-file controller
bundle with a hash-bound source declaration, rights basis, dependency
versions, explicit held-CGM availability and U/min action contract. Reject
unsupported capabilities before native execution. Give the callback only
the released observation and newly announced meal amount. Bound requested
rates, retain source and environment identity, and save every planned case,
trace prefix, native failure and report input. Reconstruct reports from
saved artifacts without the simulator or controller; verify deterministic
commands by separate source-only replay.

The supplier controls and attests to its code and rights. This workflow
does not sandbox Python, adjudicate a license, accept human observations,
support discrete doses, expose a general model interface or qualify a
controller for a fair efficacy comparison. A third-party source example and
independent intended-user run remain separate product gates.

## Alternatives

- Expand M1's historical controller enum and artifact schema in place:
  this would change the meaning of existing M1/P1/0.1 records.
- Reuse the G2P2C checkpoint intake as the only P1 path: its PyTorch,
  training and missing-CGM conventions are source-specific.
- Design a universal cross-engine plugin interface first: no supported
  user task yet establishes those broader semantics.

## Consequences and revisit condition

P1/0.2 has its own output schema and guide. Its source bundle is copied
into user-selected local output, which must be handled according to the
supplier's rights and confidentiality needs. Source hashes identify bytes;
they do not establish authorship, permission or safety. Review wider
interfaces only after a researcher completes this bounded workflow and
records the incompatibilities that matter.
