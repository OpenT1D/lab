# 0014 — Separate PhysioCGM human execution route

Status: accepted for software implementation, 20 September 2026.
Human execution is a separate authorized action; implementation tests use
invented observations.

## Context

[Decision 0013](0013-physiocgm-external-freeze.md) binds the ten converted
PhysioCGM inputs, an unchanged donor model and analysis rules in a private
pre-scoring bundle. The historical bundle deliberately cannot run predictions.
The next software step is to implement and test an executable route while
preserving the original freeze and its limited metadata-only donor seal.

Changing the old flags, labeling human observations synthetic or broadening
the original synthetic worker would blur the preparation and execution
boundaries. Modifying source files pinned by completed conversion and freeze
evidence would also make their original verification harder to reproduce.

## Decision

Add `experiments.m3.physiocgm_evaluation` and a separate execution plan with
schema `opent1d.physiocgm.evaluation/1` and stage `execution`.
The [execution supplement](../research/physiocgm-execution-protocol.md) defines
the technical route under the unchanged scientific protocol
[M3-PHYSIOCGM-EXTERNAL/0.1](../research/physiocgm-external-freeze-protocol.md).
Preserve existing conversion/freeze implementation and historical protocol
documents, schemas and disabled preparation flags.

Preparation requires explicit authorization for local scoring and private
reconstruction. It binds and validates the unchanged preparation, all ten
normalized inputs, original schedules, exact donor model, fixed rules and new
execution code in private snapshots. It does not reopen native CGM exports,
donor development/validation observations, donor reserve or the original donor
ledger. Retain prior access and the narrower donor-verification scope.

Use durable access records before protected reads, an exclusive execution
claim per prepared package and a separately claimed receipt for each participant
worker. The package claim is not global across new preparations: a new package
must record authorization covering that attempt and disclose previous attempts.
Existing authorization continues within its stated scope.
Reuse the existing evaluation-ledger mechanism with the correct PhysioCGM
identity. The supervisor owns process lifetimes and deadlines and preserves
all planned cases, partial work, failures and unattempted origins.

Private reconstruction rechecks saved identities, access history, process
states and numerical artifacts. It records access before reading payloads and
recalculates forecasts and summaries from retained observations and the frozen
model without fitting. Reports retain the complete roster and scientific and
provenance limitations.

Expose `prepare --request --output`, `evaluate --plan --output --timeout` and
`report --study --output`. Preparation does not calculate scores; evaluation
and reconstruction do. All outputs are fresh private directories, including
the report directory with its own access and verification evidence.

## Alternatives

Extending the synthetic evaluator in place would change an established human
refusal boundary. Editing completed preparation flags would imply that its
original authorization enabled scoring. Re-exporting the donor through full
training verification would reopen additional observations and change the
evidence scope. A separate execution namespace preserves each earlier stage
and makes the new authority and implementation explicit.

## Consequences and conditions for revisiting

The repository can supply an executable, testable path from the existing freeze
to a later authorized human comparison. This software step does not itself run
that comparison or establish predictive performance. It adds no new predictor,
physiological engine or controller and supplies no clinical evidence.

The scientific rules, unchanged model, full cohort, exact timing and limited
donor attestation remain binding. Any scientific change requires a versioned
amendment with earlier access disclosed. Later execution must use its concrete
authorization and retain private evidence; it cannot be inferred from passing
synthetic tests or completion of the pre-scoring freeze.
