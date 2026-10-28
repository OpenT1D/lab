# 0068 — Freeze synthetic observation analysis before paired evaluation

Date: 18 October 2026

Status: accepted for the bounded OT-054/055 synthetic route; implementation
acceptance and external evidence are recorded separately.

## Context

[Decision 0067](0067-mmtt-feasibility-boundary.md) permits one independently
expressed fixed-kinetic estimator. The source equations support exact interval
integration of piecewise-linear central C-peptide, with explicit whole-body
amounts and initial inventories. Historical causal M4 callbacks and numerical
experiments have different contracts. A paired report must preserve every
required variant and failure without overstating a nonsignificant result.

## Decision

Keep `experiments.observation_analysis` as the separate offline core. Freeze
original metadata/CSV/settings bytes, their hashes, the versioned OT-054
protocol, trusted implementation/ancestry identities and runtime before
evaluation. Supply kinetic rates and whole-body volume explicitly. Preserve
the fixed 0–120-minute total including basal and follow-up minus baseline;
do not derive normalization from participant demographics.

The initial examples use the reviewed BC-003 nominal coefficients as synthetic
controls, plus declared volume and initial-peripheral-inventory stresses.
These are engineering cases, not plausible human ranges or a T1D prior.
Use an independent Gaussian perturbation per retained C-peptide measurement
and one shared participant offset per draw across both visits; scales are
explicit invented settings. Recalculate baseline, initial states and the
entire estimator for each draw. Use the same perturbed observations across
variants. Retain every attempted draw; a failed required draw makes its
variant's interval unavailable. Do not clip values, replace censoring or
silently select successful draws for an interval.

Use nominal central 95% perturbation intervals to exercise the OT-053 direction
and classification rules. They carry no human coverage claim. Retain glucose
traces/AUC, C-peptide AUC, test/assay/medication context, interval inventories
and boundary diagnostics. Report individual pairs and complete denominators;
no default cohort significance test is introduced.

Use explicit task and trusted-reader registrations. Source snapshots are opaque
provenance; readers execute installed trusted code. Reconstruction checks saved
inputs, attempts and exact algebra before rebuilding reports; it does not draw
new noise, optimize kinetics, run R, or import archived Python. Task 2 must mask
observations before this same preprocessing/initialization/estimation boundary.

## Alternatives and revisit conditions

Reject unrestricted secretion/kinetics fitting, implicit normalization,
averaging variant disagreement and treating unresolved change as no change.
A permissive successful-draw filter would conceal boundary failures and is not
selected. Revisit error/censoring/covariance rules only through a new protocol,
supported by actual authorized observations and domain review. The fixed
synthetic route does not authorize empirical analysis or establish researcher
value; those gates remain separate in the roadmap.
