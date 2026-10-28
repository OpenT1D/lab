# 0058 — Configurable synthetic studies and local research tools

**Status:** Accepted for bounded internal implementation, 3 October 2026.

## Context

The six implemented task routes offer frozen individual experiments and
comparisons. Researchers still need to manage configuration changes, repeated
attempts, archive discovery and separate locked runtime installation manually.
The [roadmap](../research/roadmap-history-2026-10-28.md#functional-development-after-ot-031) selects
OT-032, OT-033, OT-034 and OT-037 as the next internal software increments.

## Decision

Add one separately versioned **M4-STUDY/2** task. Vary only an initial gastric
solid load at time zero within the predeclared set 0, 15 and 30 grams. Zero and
30 grams are historical parity cases; 15 grams is a synthetic midpoint that
exercises configuration without selecting its value from observed results.
Retain adult#001, the existing native initial/basal replacement conventions,
constant SC input, causal one-state secretion boundary, passive C-peptide
observer, 240-minute horizon and 0.25-minute output grid. This is an initial
condition, with CHO zero throughout; it introduces no meal event or timing API.
The separate [protocol](../research/m4-configurable-study-protocol.md) freezes
the numerical controls, refinement, failure accounting and comparison rules.

Keep new implementation outside historical source inventories. Reuse existing
equations and locks through explicit wrappers; do not change their historical
protocols or infer that an old 30-gram reference applies to another load.
Generate and verify scenario-specific native references and constant-basal
controls. Report descriptive trajectory differences only on identical accepted
conditions. There is no source tuning, ranking or biological assessment.

Native installation paths remain recorded provenance. Reusing a verified
historical reference in another checkout compares every native identity field
except the two installed-file locations (`patient_file` and `parameter_file`).
Revision, package version, profile, source/table hashes, body weight, kinetic
parameters, runtime and complete parameter records remain exact. Each new
worker binds its full current identity, and its fresh-process repeat retains
exact identity and numerical bytes. Relocation does not substitute another
native model.

Add a small local campaign layer initially supporting this task. A frozen plan
declares configurations, repetitions, budgets and complete denominators.
Every attempt has a fresh directory and retained outcome. Explicit resume
links additional attempts; it may reuse a completed attempt only after checking
its frozen identities and authoritative reconstruction. Interrupted, failed
and unattempted cases remain visible; no outcome-driven plan modification or
automatic winner selection is introduced.

Add a local catalogue of pointers to authoritative archives, with explicit
task, protocol, model, configuration and status metadata. Metadata reading and
verified reconstruction are separate states. Compatibility must be justified
by the task's full scientific conditions; unrelated tasks do not acquire a
common quality ranking by being indexed together. Catalogue verification uses
only registered standard-library readers, never an arbitrary archived module.

Add explicit task-directed setup assistance using declared existing locked
projects. Planning/checking is passive; installation is a separate requested
operation using `uv sync --locked`. Root tooling and numerical runtimes remain
isolated. Execution never silently installs a runtime. Preserve lock identities
and report setup success separately from numerical or scientific acceptance.

## Consequences

Develop the study, campaign layer and researcher tools on separate managed
worktrees and `codex/` branches, then review their integration in a fourth
worktree. The [execution plan](../research/ot032-ot037-execution-plan.md)
assigns file ownership, dependencies and actual acceptance work. Main remains
the published baseline until a separately requested integration.

GUI work (OT-035), a new model type (OT-036), empirical observations and therapy
mechanisms remain conditional follow-ups. Existing independent human-use and
scientific evidence criteria remain open and do not block internal development.

## Revisit conditions

A later load range, event time, profile, model state, runtime or empirical input
requires a newly bounded contract and appropriate verification. General model
hosting, public packaging and a graphical interface need their own selected
user problem and acceptance scope.

## Numerical refinement record

The frozen version 1 development probe failed the newly added coarse source
criterion at 15 grams. Version 2 keeps that criterion and halves only the coarse
maximum integration step, before new execution. Preserve the original protocol
and failed [probe receipt](../../experiments/integration/ot032-midpoint-v1-probe.json).
Historical exact parity is restricted to unchanged tight/reference and observer
settings; the refined coarse setting has separate numerical verification.
No physiological/source parameter or result target is selected from this probe.
