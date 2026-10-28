# 0020 — Paired observation contract before biological coupling

Status: accepted on 20 September 2026 for synthetic interface preparation; clinical/biological review remains pending.

## Context and decision

BC-002 verifies an incremental insulin inlet and BC-003 a forward C-peptide model. Their shared secretion scale, baseline, input semantics and measurement interpretation are not yet a single contract. The user requested the next paired measurement/coupling specification.

Freeze [BC-004](../research/m4-paired-protocol.md) as a small executable boundary preflight. One declared whole-body synthetic signal produces separate liver-insulin and central-C-peptide requests, using an explicit equimolar assumption and one body-mass conversion. Keep zero incremental and synthetic-total equilibrium conventions separate. Each existing model continues to own its own distribution and removal. No clearance fraction, basal pump inference or human-data estimate is inserted at the interface.

## Alternatives and consequences

Automatically combining BC-001 output with both models would conceal its unresolved whole-body scale and baseline. Jointly fitting all source and kinetic parameters would conceal known confounding. Reusing a clinical nominal basal value would not establish it for residual T1D or a graft. These options are rejected for this contribution.

The root environment may run dimensional/accounting preflight using the standard library; it remains tooling-only. This is not a coupled numerical solver or general plugin framework. Nonzero initial insulin states need a separately verified wrapper extension before synthetic-total kinetic execution. Existing sources, scientific locks and reference artifacts are unchanged.

The measurement protocol is conditional on usable release, assay, population and independent-evaluation information. Source review and explicit open questions are delivered now; human expert review and data authorization are not represented as completed. Revisit this contract when those observations or a different graft route require another model, scale or processing assumption.
