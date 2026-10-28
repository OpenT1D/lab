# 0017 — A bounded standalone beta-cell reference

Status: accepted for the maintainer-requested standalone implementation on 20 September 2026. Biological interpretation remains exploratory and awaits domain review.

## Context

[Decision 0016](0016-parallel-control-cure-research.md) starts M4 preparation alongside glucose-control research. Existing engines have no endogenous-secretion inlet; importing a release function as a pump command would duplicate absorption and misrepresent its route. OT-024 needs a concrete evidence assessment and OT-025 needs executable science before OT-026 coupling.

## Decision

Implement only the two-state reduced IVGTT equations 4.11–4.13 from [Pedersen and Cobelli (2013)](https://doi.org/10.1098/rsfs.2012.0085), with Figure 2 parameters, in a separately locked runtime. Use native mmol/L, micrograms and minutes. Preserve the distinction between evoked release and total secretion. The [protocol](../research/m4-protocol.md) specifies the synthetic declining glucose challenge before implementation; the [model card](../research/models/pedersen-cobelli2013.md) defines its limits.

Select this reference because its small dynamic system, source parameters and theoretical glucose-response functions are inspectable. The [candidate comparison](../research/m4-evidence-dossier.md) distinguishes glucose-driven secretion from C-peptide deconvolution and records data/code access. Published equations support an original implementation, while public visibility alone does not grant permission to redistribute author code. Inspect the XPPAUT reference without vendoring or claiming its execution.

Reproduce the stated algebraic provision/delay relationships and verify dynamic equations numerically. Preserve the paper/code initialization discrepancy as an explicit alternative-initialization sensitivity. Missing original glucose samples and the unresolved burst initialization prevent an exact Figure 2b or cohort reproduction. Treat the changing-glucose reduction as an approximation, not an exact coordinate transformation of the full granule model.

Keep a hypothetical functional-capacity multiplier separate from cell mass and therapy. Do not add C-peptide kinetics with borrowed clearance constants or the author's illustrative scaling adjustment. Do not integrate an engine in this change. The [OT-015 specification](../research/m4-coupling.md) prepares a later simglucose liver-inlet kinetic test and records the missing direct portal effect on glucose production.

## Alternatives and consequences

An oral minimal model is attractive for meal tests but needs its own complete reference and observations. A C-peptide kinetic reference would establish an observation/reconstruction method rather than this glucose-to-release capability. The full granule or organ model adds unneeded states and parameters for the present question. None is interchangeable solely because it relates to insulin.

Reuse existing provenance, failure preservation and artifact-reconstruction patterns, with a new bounded schema appropriate to secretion units. No shared plugin framework or upstream physiological changes are needed. OT-024 and the relevant OT-015 specification can be delivered while empirical evaluation and OT-026 remain open. OT-025 is partial when exact published dynamic reproduction is unresolved. M4/M5 milestones remain incomplete.

Revisit when domain review resolves the source discrepancy, available measurements favor a different challenge/model, or a broader glucose regime becomes the intended task. New therapy or real-data claims require their own frozen assessment and authorized observations.
