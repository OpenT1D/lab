# 0066 — Develop shared observation analysis through two related MMTT tasks

Date: 18 October 2026

Status: accepted for planning OT-053–056; implementation and empirical protocol
selection remain open.

## Context

The maintainer selected a concrete two-task proposal for the roadmap: assess
the sensitivity of a paired secretion-change conclusion to analysis assumptions,
then assess information loss from fewer measurements in the same test window.
OpenT1D already has bounded synthetic M4 workflows, numerical inference
prototypes and shared execution/archive infrastructure. These do not constitute
a general measured-data fitting route. The [Mari source audit](../research/m4-independent-source-preflight.md)
also establishes that whole-trace inference cannot simply be placed in the
current causal secretion callback.

## Decision

Apply [decision 0045](0045-tool-first-research-platform.md) through one shared
offline observation-analysis core and two bounded tasks. The [roadmap plan](../research/roadmap-history-2026-10-28.md#planned-mixed-meal-analysis-tasks)
is canonical for scope, sequence, deliverables and proposed product criteria.

Start with retrospective standardized MMTTs in adults with T1D and measurable
endogenous secretion, with linked visits. Both tasks use estimated total
endogenous secretion over the same observed 0–120-minute window and its paired
change. Freeze units, normalization, initial/basal conventions, justified
kinetics and interpretation in a later source-specific protocol. C-peptide AUC
remains a separate reference. A secretion change under a different glucose
stimulus is not automatically functional recovery or a treatment effect.

Task 1 compares one suitable estimation method under prespecified defensible
variants. Task 2 reuses that method and core while removing observed sample
times before fitting. Keep all visits of a person in one development/evaluation
allocation; never reuse removed observations or estimates learned from them in
the reduced analysis. Retain failures and indeterminate conclusions. Full-curve
analysis is a reference, not biological truth, and shorter test durations need
a separate endpoint decision.

Reuse existing execution, numerical verification and archive components where
their assumptions fit. Add explicit task contracts/readers rather than changing
historical synthetic contracts or claiming a universal plugin interface. Assess
existing source implementations and strong researcher-tool/notebook baselines
before building new numerical methods. No dependency, external API, dataset,
clinical margin or population parameter set is frozen by this decision.

## Alternatives

- Build a universal model platform first: the needed boundaries are not yet
  established by these concrete tasks.
- Feed MMTT observations into the existing causal M4 experiment: this conflates
  prospective simulation and whole-trace estimation conventions.
- Build two separate analysis applications: this duplicates the shared data,
  estimator, uncertainty and provenance work that Task 2 should test for reuse.

## Consequences and revisit conditions

OT-053 starts with task/data/model/comparator feasibility. Suitable observations,
researcher participation, licensed tool access and comparative benefit are not
established. Internal checks with permitted synthetic inputs may proceed while
external evidence is unresolved; restricted access and empirical claims retain
their own gates. The existing Windows/P1/GUI and scientific acceptance items
remain open within their original scope.

Revisit scope if usable observations or defensible kinetics cannot be found,
researchers lack a meaningful decision, the strong baseline performs similarly
with comparable effort, or actual implementation shows that the proposed shared
core does not support both tasks. Any source-specific protocol change must
precede its evaluation, with earlier evidence and negative results preserved.
