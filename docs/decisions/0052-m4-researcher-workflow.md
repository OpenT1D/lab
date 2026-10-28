# 0052 — Compose causal M4 intake with forward C-peptide observation

**Status:** Accepted for bounded internal implementation, 2 October 2026.

## Context

The [causal intake](../m4-causal-secretion.md) verifies a supplied secretion
source in BC-008 feedback, while [BC-010](../research/m4-feedback-observation-results.md)
observes pancreatic appearance through separate C-peptide kinetics. The
researcher task needs one configuration and report that joins these tools
without changing their historical experiments. The existing Dalla Man adapter
and [ultradian f1 component](../m4-ultradian-secretion.md) provide two already
attributed structures for internal verification.

## Decision

Add a separate **M4-RESEARCHER/1** workflow for one trusted, hash-declared
source under unchanged `M4-CAUSAL/1`. Run the fixed fasting and initial 30 g
gastric-load scenarios with the existing candidate, host constant-basal and
full BC-008 reference tracks. Create a fresh BC-008 archive by default, or
verify a supplied archive whose BC-008 source/reused snapshots and native
runtime lock/project match the current worktree byte for byte. Reject a
mismatch before creating output. Keep historical code, protocols, source
declarations and result records unchanged.

Observe saved total pancreatic appearance in a passive forward C-peptide
branch. Reuse BC-010's frozen molar boundary, initialization and numerical
settings for the new six-case matrix. The original BC-010 24-case hepatic
study is not rerun or relabeled. Do not add a second basal input, insulin
portal delay, extraction, body-weight conversion or pharmaceutical input to
C-peptide. Preserve one-way process ownership and the existing separate
locked numerical runtimes.

Archive every stage and attempted case, source/configuration identity,
protocols, runtime locks and fresh-process repeats. Accept complete-matrix
comparisons only when parent and observation checks pass. Generate a readable
report and trajectory figure from saved artifacts; reconstruct them without
running researcher code or importing numerical packages. No source or
criterion is selected from the resulting curves.

Own supervised subprocess groups through exit, timeout and interruption.
Terminate and reap a failed or interrupted worker before sealing its archive.
Temporarily bind this process supervisor during the inherited causal executor,
then restore the original binding. This adds process ownership to the new
orchestrator without editing historical numerical implementations.

## Alternatives

- Ask researchers to join the separate archives manually: makes inlet,
  initialization, case alignment and failure handling easier to misinterpret.
- Add C-peptide states to the native callback: introduces unnecessary
  feedback/runtime changes for a passive observation.
- Extend the model API immediately: no extra state or future-data input is
  needed for this bounded task; broader compatibility requires its own need
  and evidence.

## Consequences and revisit conditions

The workflow compares modeled glucose, insulin and C-peptide under fixed
synthetic conditions. It does not optimize SC infusion or supersede the
separate basal-equivalence search. Numerical verification is distinct from
whole-engine reproduction, human calibration, independent usability and
therapy evidence. M4 and P1 acceptance remain open.

Archived source sampling remains an explicit piecewise-linear approximation;
coarsening against the 0.25-minute grid does not establish convergence below
that grid. Revisit the composition for a concrete researcher model needing
more states, a different observation boundary, a different engine or
permitted dynamic observations. Each extension needs a scoped convention
and verification rather than an inferred general API promise.
