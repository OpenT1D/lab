# 0051 — Evaluate the complete ultradian f1 response component

**Status:** Accepted for bounded synthetic M4 implementation, 28 September 2026.

## Context

The [Mari audit](../research/m4-independent-source-preflight.md) found a
whole-trace fitted potentiation input. A different primary publication,
[Karamched et al. 2021](https://doi.org/10.1063/5.0027682), section II,
specifies the ultradian model's insulin-production function `f1(G)` as a
complete algebraic sigmoid. It has Sturis 1991 ancestry and no secretion
memory, derivative term or fitted future trajectory. Its shape differs from
BC-008's delayed static and positive-slope source.

## Decision

Implement this complete response component as an original single-file
adapter on unchanged `M4-CAUSAL/1`. Retain the published `a1=6.6` and
`C1=300 mg/L`; convert host glucose concentration from mg/dL to mg/L once.
Normalize the shape by its value at host initial glucose `h`, so
`Spo=Sb*r(G)/r(h)` and `Zdot=0`. The unused host bookkeeping state `Z`
remains at `Sb`. There is no extra delayed or potentiating source process.

Amplitude is a declared synthetic basal match, not conversion or reproduction
of the source's `Rm=209 mU/min`. The original `f1` enters a plasma-insulin
equation. Assigning the normalized response to the host pancreatic/portal
route is an explicit exploratory composition; no prehepatic human rate or
hepatic-correction equivalence is inferred. The host retains its existing
SC basal replacement, portal transit, liver inlet and physiology.

## Verification and limits

Before coupled outcomes, check the single-file source against a high-precision
amount-space equation oracle, its inflection, monotonic saturation,
low-glucose branch, basal identity, zero amplitude and causal repeatability.
Use the existing frozen feedback task, constant-basal control, BC-008
comparison, solver/balance limits, new-process repeat and artifact-only
reconstruction. Add a closed-form portal diagnostic using the actual host
RHS. Do not tune the shape or criteria from the resulting glucose curve.

This is a sourced pancreatic-response component and a synthetic hybrid,
not reproduction of the six-state ultradian physiology, its oscillations,
chaos study, population calibration or a therapy. Whole-engine reuse remains
a separate possible workflow. This step needs no new interface version,
external observations or human sign-off.
