# 0069 — Re-estimate raw sampling subsets through the shared observation core

Date: 18 October 2026

Status: accepted for bounded synthetic OT-055; empirical assessment remains open.

## Decision

Keep one estimator and one conditional uncertainty procedure from
[decision 0068](0068-synthetic-observation-analysis-contract.md). Freeze Task 2's
original input bytes, identical fixed analysis settings, development evidence,
participant allocation and two or three actual-time subsets before execution.
The endpoint remains whole-body total secretion including basal over 0–120
minutes in pmol, with follow-up minus baseline. Full curves are references.

Mask raw CSV rows before analyte/status parsing, unit conversion, initialization
and estimation. Each full/reduced call gets its own frozen native plan and runs
through the same shared execution and report reader. Carry no full-curve state
or participant parameter into a reduced call. Keyed perturbations preserve the
same retained-time measurement errors and participant-shared visit offset.

Add optional `required_times_min` structural admission to shared settings.
A missing required time invalidates its visit before initial inventories,
perturbations or estimation; another visit's point result remains visible.
This changes input admission, not the numerical estimator, kinetics or error
procedure. Task 2 owns that field and varies only the required schedule across
otherwise identical shared settings. Native reconstruction enforces it too.

Preserve all planned attempts, failures, indeterminate directions, original
bytes and child archives. Report signed/absolute differences, descriptive bias
and precision separately for development and evaluation, alongside paired
conclusions, C-peptide AUC, glucose and assay/low-value context. Both unresolved
is indeterminate. No default empirical acceptance margin or cohort confidence
interval is introduced. Fewer times are not a prospective blood-draw approval.

## Alternatives and revisit conditions

A second inverse engine would duplicate scientific and maintenance work.
Deleting points after fitting or accepting fewer than the frozen requested
samples would answer a different question. Dropping failed references or draws
would inflate apparent agreement. None is selected. Revisit empirical margins,
kinetics and assay/censoring rules only with authorized observations and a
source-specific protocol frozen before held-out access.
