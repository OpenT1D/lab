# 0048 — Bound causal secretion intake to the BC-008 feedback task

**Status:** Accepted for bounded internal M4 implementation, 27 September 2026.

## Context

The [BC-007 intake](0047-m4-external-secretion-boundary.md) supplies a full
secretion trace after a prescribed glucose curve is known. A full trace would
leak future glucose if reused inside a feedback simulation. BC-008 already
contains a verified synthetic glucose-feedback task and a distinct
pancreatic-to-portal-to-liver route. The M4 roadmap asks how a secretion
model changes modeled glucose, without making a clinical insulin-need claim.

## Decision

Create a separate one-state, trusted local Python intake for the unchanged
BC-008 fasting and initial gastric-load tasks. At each native solver stage,
pass only current time, plasma glucose, its same-stage native derivative,
the current secretion state `Z`, and host-owned basal and threshold values.
The source returns `dZ/dt` and pancreatic appearance `Spo`. The host owns
SC basal replacement, initial plasma insulin matching, portal amount `P`,
`Pdot=Spo−gamma P`, and guarded liver arrival `S=gamma P`. No candidate
callback sees future glucose or owns a mutable integration state.

Keep the BC-008 code, protocol and result archive unchanged. Compare the
candidate with BC-008's full feedback reference and with a host-generated
constant-basal control. Pin the single-file source hash and declaration,
run in the BC-008 locked environment, retain all primary and fresh-process
repeat attempts, and reconstruct numerical checks and contrasts from saved
artifacts without executing the candidate code. A source-equilibrium and
out-of-order preflight detects common interface mistakes before any coupled
case. Only numerical and synthetic claims can pass this gate.

## Alternatives

- Replay the BC-007 full trace into feedback: this would use future glucose.
- Modify BC-008's frozen source callback: that would change its historical
  reference implementation and source hashes.
- Accept arbitrary multi-state models or external runtimes immediately:
  those require an observed user need and a new state/environment contract.

## Consequences and revisit condition

The supported model has one explicit rate state and returns a continuous
nonnegative pancreatic rate. The supplied file is trusted code; source hashes
identify bytes but do not establish rights, scientific validity or purity
against intentionally stateful code. This task has no bolus/controller,
C-peptide output, human observations, therapy effect or optimized insulin
requirement. Revisit the interface after an actual researcher attempts a
model that cannot be expressed by this contract.
