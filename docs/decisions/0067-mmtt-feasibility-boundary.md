# 0067 — Narrow MMTT preparation to fixed-kinetic synthetic analysis

Date: 18 October 2026

Status: accepted for bounded OT-054/055 preparation; human protocol remains open.

## Context

[Decision 0066](0066-observation-analysis-tasks.md) selects two paired MMTT
tasks. The [OT-053 dossier](../research/ot053-mmtt-feasibility.md) finds candidate
sources but no authorized complete adult visit pairs or justified individual
kinetics. A WebAssembly R probe confirms a quadrature concern in the open
candidate's linear function; full-package/native/spline behavior remains
unverified. Existing forward C-peptide calculations provide
an independently checked source model, not a measured-data estimator.

## Decision

Narrow the next implementation to invented observations and explicit fixed
kinetics. Use whole-body total endogenous secretion, including basal, integrated
over observed 0–120 minutes in pmol, and follow-up minus baseline in pmol.
Use concentration in pmol/L, volume in L and elapsed minutes; preserve source
units. C-peptide AUC and glucose context remain separate. The synthetic nominal
initial state is fasting compartment equilibrium; no inferred secretion is
silently clipped. There is no automatic weight, BSA or glucose normalization.

One offline core may implement exact interval integration of the existing
two-compartment model under piecewise-linear concentration, with independent
numerical controls before acceptance. Task 2 removes observations before all
preprocessing/fitting and reuses that core. Existing causal M4 contracts and
historical experiments retain their scope. No upstream R dependency or GPL
source copy is selected by this decision.

## Alternatives

- Proceed with human fitting now: rejected because release access, complete adult
  pairs, assay context and justified kinetic inputs are unconfirmed.
- Adopt the R package immediately: rejected pending complete numerical/runtime
  verification and a documented licensing arrangement.
- Stop all preparation: unnecessary because the existing source-model equations
  and independent synthetic controls support a bounded offline implementation.

## Consequences and revisit conditions

Synthetic parameters, initial-state stresses and invented assay error are
engineering controls, not T1D uncertainty distributions. Human execution needs
verified release rights/linkage/coverage, assay/renal/kinetic justification and
a source-specific protocol frozen before evaluation. Empirical margins, cohort
inference and researcher value remain open. Revisit after those facts, a native
upstream audit if adopting that package, or a strong comparator demonstrating
similar quality and effort. An honest narrow decision completes OT-053 without
claiming completion of OT-054, OT-055 or OT-056.
