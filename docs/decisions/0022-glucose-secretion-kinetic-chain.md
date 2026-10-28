# 0022 — Compose the existing glucose, secretion and kinetic references

Status: accepted on 20 September 2026 for the user-requested next bounded OT-026 implementation.

Implement [BC-007](../research/m4-chain-protocol.md) as one artifact-based chain: a fresh unchanged BC-001 experiment, explicit one-time molar transfer, and both existing kinetic solvers. A standard-library parent owns orchestration and evidence; the existing scientific runtimes own numerical execution. Preserve BC-001 through BC-006 and their frozen contracts.

Use a new small chain runner rather than reinterpret BC-005's fixed synthetic boundary cases. Reuse its numerical functions and independent calculations. Keep source-sampling refinement separate from solver accuracy. This adds a consumer of the existing modules, not a plugin framework or a new secretion equation.

Evoked scaling and the independent synthetic basal term must remain explicit. BC-006's hypotheses do not authorize silently changing initialization or importing the author's observation multiplier. Glucose feedback requires a subsequent reviewed model-scope decision and protocol; this chain can advance as synthetic engineering evidence without claiming that decision has been made.
