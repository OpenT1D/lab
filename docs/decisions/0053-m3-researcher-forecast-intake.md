# 0053 — Bound researcher forecast intake to a synthetic causal CGM task

**Status:** Accepted for bounded internal M3 implementation, 2 October 2026.

## Context

The [external M3 route](0010-external-frozen-forecast.md) evaluates a portable
existing Ridge model under verified causal timing and participant-level
analysis. Its model-specific arithmetic contract does not supply a callback
for a researcher's different forecast method. The
[tool-first direction](0045-tool-first-research-platform.md) favors one
usable integration task while preserving established protocol meanings
and independent evidence gates.

## Decision

Add a separate `experiments.m3.researcher` route under
[M3-RESEARCHER/0.1](../research/m3-researcher-protocol.md). Accept one
hash-bound trusted local Python source and frozen JSON settings, with
identity, attribution, rights and synthetic training disclosure. Its
stateless callback predicts a finite mg/dL scalar from six exact causal
five-minute CGM values for a fixed 30-minute horizon. The host owns history,
availability, 60-minute warm-up, exact target matching and persistence.

Freeze the full synthetic roster and schedule before input reads. Retain
failed workers, valid trace prefixes and unattempted origins. Reuse the
external route's 288-pair/24-hour contributor floors, equal-person outcomes
and descriptive person-level bootstrap. Reconstruct hashes, windows,
persistence and metrics without original inputs or predictor execution.
Verify the workflow with the existing synthetic Ridge reference and a
structurally different invented predictor. Preserve Ohio, AZT1D, external
Ridge and authorized PhysioCGM contracts unchanged.

## Alternatives

- Extend the portable Ridge schema to arbitrary callbacks: that would
  obscure its independent model-specific arithmetic replay.
- Offer a general stateful or multi-runtime forecasting API now: those
  contracts need a concrete additional user task and separate environment,
  state, covariate and timing decisions.
- Enable human inputs through a review flag: source-specific rights,
  units, clocks, status semantics and explicit authorization remain
  necessary before a separately frozen human extension.

## Consequences and revisit condition

This route establishes a bounded synthetic research workflow. Its source
is trusted code running with the user's permissions; process supervision
does not sandbox it or prove statelessness. Synthetic input and training
references are attestations. An arbitrary candidate's recorded forecasts
cannot be independently rederived by artifact-only reconstruction, unlike
the historical portable Ridge arithmetic. Checksums establish consistency,
not signatures or scientific validity.

Revisit the interface after an intended researcher identifies a model that
needs a richer contract. Human predictive accuracy, biological validity,
independent usability and broader compatibility retain separate evidence
criteria.
