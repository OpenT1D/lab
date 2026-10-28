# 0031 — C1 missing-meal controller study

Status: accepted locally on 25 September 2026.

## Context

The roadmap calls for an original controller study with a falsifiable
benefit and strong references. M2 and IV-001 already inspected missing-meal
conditions, uneven reference coverage, Cambridge MPC numerical sensitivity
and a single Cambridge parameterization. They cannot serve as a fresh C1
evaluation. M3 human CGM forecasting has a different task and does not
validate insulin actions.

## Decision

Select missing scored-day meal announcements as C1's first controller
question, with within-engine time in 70–180 mg/dL as primary simulated
benefit and explicit low-glucose, high-extreme, full-information and stop
constraints. Keep both native model families and their original controllers
as anchors, but require an eligible strong comparator with equivalent causal
information and development budget for a superiority claim. Use the
[C1/0.1 protocol](../research/c1-controller-protocol.md) as the design
contract. Select the algorithm and seal the exact evaluation roster and
remaining numerical/statistical criteria before OT-019 implementation and
held-out scoring. Do not treat inspected M2/IV cases or fresh seeds on known
profiles as new-population evidence.

## Alternatives and consequences

A controller architecture selected now would preempt the method assessment.
A general improvement claim across unmatched engines would hide different
glucose signals, references and populations. A fixed basal-bolus comparison
alone would give a weak feedback benchmark; Cambridge's single MPC case does
not fix that cross-engine problem. The selected question supports bounded
simulation development while leaving human benefit, device use and C1
superiority open. Revisit the question if no strong comparator or feasible
evaluation material can be verified; retain negative and incomplete results.
