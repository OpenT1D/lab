# 0050 — Require source-faithful compatibility before M4 feedback intake

**Status:** Accepted for internal M4 development, 27 September 2026.

## Context

[Decision 0048](0048-m4-causal-secretion-intake.md) says to revisit the
one-state intake when an actual independent model cannot be expressed by it.
The [Mari 2002 source audit](../research/m4-independent-source-preflight.md)
is that test. Its positive-glucose-derivative term fits pointwise, but its
complete multiple-meal method estimates a time-varying potentiation function
from the whole glucose/C-peptide series. The source also reports
surface-area-normalized secretion parameters, whereas M4 requires a rate per
kilogram and a host-owned basal equilibrium.

## Decision

Do not present `Q=0`, a guessed potentiation curve, a hidden mutable fit or
a dimensionless reinterpretation of `Z` as Mari's published model. Record
`M4-CAUSAL/1` as incompatible with the complete method until a sourced
prospective potentiation input/rule and a justified unit and basal mapping
exist. A causal published alternative may still fit the unchanged intake;
assess its equations before implementing it. If a real candidate needs more
inputs or states, design a versioned successor contract with separate
ownership and verification; do not change the frozen BC-008 reference.

## Consequences

The source audit closes this internal compatibility question with a concrete
negative result, not a simulated outcome. The existing causal interface,
example adapter, synthetic basal task and archived references remain valid
within their documented scope. A future published-model intake has an
explicit source and numerical gate; human data and external review are
needed only for claims that depend on them.
