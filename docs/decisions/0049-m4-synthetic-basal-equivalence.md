# 0049 — Compare fixed SC infusion on a frozen synthetic glucose task

**Status:** Accepted for bounded internal M4 implementation, 27 September 2026.

## Context

The [causal M4 intake](0048-m4-causal-secretion-intake.md) fixes the external
SC basal infusion at 75% of the BC-008 native rate. It can compare glucose
trajectories but cannot describe how that modeled outcome changes when the
external infusion is varied. The M4 roadmap includes exploration of external
insulin requirements, while no human dose or biological calibration exists.

## Decision

Add a separate, versioned synthetic equivalence task. Pin the first model to
the BC-008-equivalent example adapter and accept one other declared causal
source. Use the unchanged
BC-008 full-feedback 30 g gastric-load reference-solver AUC above initial
glucose over 240 minutes as the numerical target. For each hash-declared
causal source, keep its 25% replacement source basal, threshold, portal state,
all native initial states and parameters fixed. Vary only the constant SC
infusion delivered from time zero. Compare rates at 50, 62.5, 75, 87.5 and
100% of the native SC basal, then bisect an observed monotone bracket for at
most 18 steps. A solution needs a reference-solver AUC residual within
1 mg min/dL. Preserve unbracketed, nonmonotone and resolution-limited results
without extrapolation.

Retain the whole BC-008 reference, source declarations, numerical trajectories,
each attempted search point, two locked solver checks, fixed-basal control,
fresh-process repeat and source-free report reconstruction. A failed worker
keeps its attempted cases and cannot produce a completed equivalence claim.

## Alternatives

- Change the source basal with the SC infusion: this changes two causal
  inputs and loses the one-factor interpretation.
- Tune a bolus or controller: this answers a different control question.
- Expand the range after seeing a missed target: this changes the prespecified
  task and would require a new protocol version.

## Consequences and revisit condition

The changed SC infusion begins from the same initial depot and plasma state;
its first minutes are a defined transient, not a newly equilibrated person.
The matched scalar AUC is not a clinical glucose target or an insulin dose.
It may hide different peak, nadir and fasting behavior, so those remain visible
diagnostics. Revisit the range or objective only in a separately frozen study
with a stated reason and its own controls. Human interpretation remains gated
by suitable observations and domain review.
