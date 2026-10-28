# 0008 — Separate AZT1D causal forecast workflow

Status: accepted for software preparation, 20 September 2026; human execution conditional on resolved scientific gates, a verified private freeze and explicit authorization.

## Context

The authorized AZT1D intake supports specifying a source-specific next software step. It does not establish human forecast performance, complete CGM semantics or permission to run an evaluation. The existing [Ohio M3/1 protocol](../research/m3-protocol.md) uses provider training/testing membership and nominal five-minute origins. Applying those rules unchanged would conceal important differences in AZT1D's source structure and registered timestamps.

## Decision

Specify [AZT1D-M3/0.1](../research/m3-azt1d-protocol.md) and isolate its workflow under `experiments.m3.azt1d`. Use schema `opent1d.m3.azt1d/1` and metric `azt1d-cgm-forecast/1`; preserve Ohio M3/1, decision 0007 and historical artifact meanings. Reuse the existing estimator where its contract matches: development-only `StandardScaler` and fixed Ridge with identical equal-person sample weights, compared with persistence.

Bind the planned 20-study/five-reserve allocation and per-person elapsed 60/20/20 splits to the existing private intake assignment. Use exact registered-time origins and exact feature/target offsets, without interpolation or timestamp rounding. Collapse numerically equal same-time CGM observations while retaining source-row lineage; conflicting values remain ambiguous. A combined CGM/BGM stream is unsupported until its semantics are resolved. Keep every planned participant and registered origin in accounting, including unsupported or insufficient sources, without reserve substitution.

Preserve forecasts that are possible from causal history even when a future target is unavailable. Separate development qualification from final reporting eligibility so evaluation coverage cannot change the fitted model. Freeze status/censoring policy and availability assumptions before human fitting. Keep a persistent source/allocation/split-bound access ledger that records evaluation normalization and execution before values are read. Freeze learned artifacts after diagnostic validation and before evaluation access; disclose any earlier inspection.

## Alternatives and consequences

Silently extending Ohio's protocol would change historical conventions. A generic parser that renames mixed readings, rounds irregular timestamps or averages conflicts would hide scientific choices. These alternatives are rejected in favor of a small explicit source boundary and a separate versioned protocol.

This work prepares one same-person, CGM-only observed-care forecast question. It does not identify a physiological improvement, validate a controller or establish a product-performance claim. The reserved participants remain same-study material, with later use requiring another protocol. Human records, individual derived results and private provenance stay outside Git and public services; synthetic fixtures support implementation checks only.

Revisit through a recorded protocol amendment if modality/status semantics require different inclusion rules, exact windows prove unsuitable, clocks need correction, or a new population, physiology or intervention question is proposed. Preserve previous artifacts and disclose affected holdout access rather than restarting the claim of an unseen evaluation.
