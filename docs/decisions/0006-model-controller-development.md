# 0006 — Evidence-led model and controller development

Status: superseded for future priorities and mandatory original-method objectives by [decision 0045](0045-tool-first-research-platform.md) on 26 September 2026. [Decision 0016](0016-parallel-control-cure-research.md) had earlier amended the priority ordering. Historical protocols and the evidence and evaluation requirements below remain in force for any such study.

## Context

M2 software and the bounded IV-001 internal verification campaign are complete. The original independent human M2 reproduction remains open under [decision 0005](0005-internal-verification-and-external-review.md). The maintainer's next ambition includes both an original controller and an improved physiological model, with a usable product built on the laboratory.

## Decision

Keep the [roadmap](../../ROADMAP.md#development-sequence-after-m2) canonical. Prioritize M3 human-observation evaluation and C1 controller specification. Add B1 for a targeted physiological improvement informed by measured limitations, V1 for cross-evaluation, and P1 for a usable research product. Retain M4–M6 names and aims as question-dependent longer-term paths.

Separate completion of an implementation/evaluation from a successful improvement claim. Prespecify benefits, non-degradation limits, uncertainty, coverage and failure handling before tuning. Preserve untouched assessment material for each new claim: inspected M2/IV-001 cases and M3 data used to choose model changes cannot be presented as fresh evaluation. Evaluate physiology against observations separately from controller performance in simulation; historical treatment traces do not establish counterfactual treatment effects.

The first product target is a bounded research/development workflow. Original methods and physiology are objectives; rights, usability, independent execution and commercial demand require their own evidence. No dataset, control algorithm, general engine rewrite or release is selected by this decision.

## Alternatives

- Continue only general laboratory infrastructure: retains useful tools but leaves original model/controller development without explicit deliverables.
- Replace both engine and controller immediately: lacks a measured limitation and risks assessing two mutually adapted components only against each other.
- Require all human-data evaluation before controller development: unnecessarily blocks bounded simulation work. C1 can proceed with explicit simulation-only claims while M3 dependencies are resolved.

## Consequences and revisit conditions

Add separate versioned protocols and artifacts for new experiments. Preserve all M0/M1/M2 and IV-001 evidence, baselines and native references. Independent M2 reproduction remains a later open gate; P1 requires its own actual user execution. No data access, invitations, clinical use or publication is authorized by a planning entry alone.

Revisit priorities when data feasibility prevents the intended M3 question, candidate comparisons are scientifically unsupported, a model change fails held-out assessment, or intended-user evidence changes the product task. Record the revised scope before a new evaluation; retain negative results and previously inspected data identities.
