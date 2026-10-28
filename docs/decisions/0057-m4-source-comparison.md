# 0057 — Compare frozen M4 sources under one synthetic task

**Status:** Accepted for bounded internal implementation, 3 October 2026.

## Context

The configured [M4 researcher workflow](../m4-researcher-workflow.md) runs one
causal secretion source through the fixed glucose/insulin task and passive
C-peptide observation. Comparing its separate Dalla Man and ultradian reports
requires researchers to check the common conditions, reference, controls and
failure status themselves. [OT-031](../../ROADMAP.md#proposed-internal-follow-up--ot-031-multiple-m4-secretion-sources)
selects one combined comparison without adding secretion physiology or data.

## Decision

Add a separate **M4-COMPARISON/1** coordinator outside the source inventories
required by historical readers. Freeze the [comparison protocol](../research/m4-source-comparison-protocol.md)
before implementation and new comparison execution. Reuse unchanged
`M4-RESEARCHER/1` for an ordered roster of two to eight trusted, hash-declared
single-file sources. Retain its two scenarios, causal boundary, native initial
state, fixed SC schedule, passive C-peptide inlet, solver criteria and separate
locked runtimes. Do not adapt incompatible settings.

Generate one complete verified BC-008 reference, or check a supplied reference
against its archived numerical evidence and the current fixed source/lock
snapshots before dispatch. Every child receives the same reference. Freeze the
configuration, source/declaration/parameter identities, protocol and runtime
identities before executing supplied source code. Dispatch sequentially in
roster order with both the inherited per-stage budget and an explicit outer
source-workflow budget. Own, terminate and reap workers on deadline or
interruption; retain failed and unattempted source/scenario entries.

Accept a source only when its entire inherited workflow and fresh-process
repeat pass. Compare sources directly only when both are fully accepted,
conditions and all saved sample times match, and their verified common
reference/control trajectories agree exactly. Preserve null pairwise results
with reasons when evidence is incomplete or incompatible. Report descriptive
left-minus-right trajectory contrasts in roster order; no winner, fitted
source, biological ranking or post-outcome exclusion is introduced.

Preserve complete child archives and give the coordinator its own source
inventory and hashes. Produce one report and trajectory figure from archived
evidence. Reconstruct them with the standard library without numerical
runtimes, supplied-source imports or source execution. Expose this separate
task through the common local entry only after its native run and
reconstruction are checked. Keep single-source commands and historical
reconstruction available unchanged.

## Alternatives

- Join the existing reports manually: leaves common-reference identity,
  control consistency and failed-source accounting to each researcher.
- Merge the sources into one native simulation: changes process ownership
  and numerical scope without a task requirement.
- Rank sources or tune them to match curves: needs a separate scientific
  objective, data and protocol and is outside this fixed software comparison.

## Consequences and revisit conditions

This provides a reproducible comparison of modeled glucose, insulin and
C-peptide for a declared synthetic task. It does not complete M4's biological
acceptance or P1's independent usability exercise. Trusted local source code
retains the existing rights, purity and scientific assessment limitations.
The fixed sampling checks do not prove convergence below 0.25 minutes.

Revisit the contract when a concrete source needs another state, runtime,
stimulus, initial state, observation boundary or authorized empirical task.
Such an extension requires versioned settings and verification rather than
silent adaptation of this comparison.
