# 0021 — Execute paired kinetics in the existing isolated runtimes

Status: accepted on 20 September 2026 for the user-requested synthetic kinetic execution. Biological validity and glucose feedback remain outside this contribution.

## Decision

Implement [BC-005](../research/m4-paired-kinetics-protocol.md) using two explicit workers and a standard-library parent. Insulin uses the pinned M0 environment; C-peptide uses its existing numerical environment. Preserve both locks, all previous implementations and their historical protocols.

Extend nonzero insulin initialization in a new wrapper calling BC-002's unchanged native derivative/inlet. Compare its zero-initial behavior against the original function and its nonzero behavior against an independent matrix exponential. Reuse BC-003's explicit-initial-state solver. Feed both from a verified BC-004 artifact; keep source-rate assumptions and separate process ownership visible.

## Alternatives and consequences

Changing an old runner in place would blur its historical zero-increment contract. Combining environments would unnecessarily change tested dependency versions. Implementing a generic host or glucose-feedback loop would exceed the next bounded question. Neither is needed for this two-branch kinetic experiment.

Archive both workers' outputs, sources, runtime identities and failures; reconstruct their joint report independently of either scientific environment. Paired concentrations do not establish a jointly calibrated patient. Revisit the design if a reviewed biological question requires different kinetics, secretion scale, graft processing or feedback.
