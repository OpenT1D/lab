# BC-015-P3 — Nearby public observation sources

This targeted source screen follows the [CIT-07 public-field crosswalk](m4-cit07-public-crosswalk.md).
It asks whether a nearby islet-transplant source removes the obstacle to the
[BC-004 paired IV-glucose measurement contract](m4-paired-protocol.md). It
does not assess participants, treatment efficacy, or model fit. No access
request, participant-data download, or external review occurred.

## Candidate comparison

| Source and population | Publicly documented measurements | Access and decision for the current IV protocol |
| --- | --- | --- |
| [CIT-07/08 Version 2](https://repository.niddk.nih.gov/study/92), islet-alone recipients with established T1D | Its [field audit](m4-cit07-public-crosswalk.md) establishes dynamic FSIGT glucose/insulin fields, but no C-peptide field in FSIGT Raw; C-peptide appears in separate sparse tables. The core protocol ends FSIGT C-peptide at 10 minutes. | Data are available **for request**, not licensed to this project. The same-challenge, late-C-peptide and actual-input questions remain unresolved or contradicted for the core schedule. |
| [CIT-02/08](https://test.repository.niddk.nih.gov/study/93), [CIT-03/08](https://test.repository.niddk.nih.gov/study/94), and [CIT-06/08](https://test.repository.niddk.nih.gov/study/97), related islet-transplant protocols | Their public catalogue descriptions likewise list FSIGT Raw as glucose/insulin and a separate fasting/stimulated C-peptide/glucose/creatinine dataset. The [CIT-02 analysis plan](https://repository.niddk.nih.gov/public/study_document/Documentation/CIT-02_SAP_Version_1.0.pdf) treats MMTT fasting/90-minute glucose/C-peptide and FSIGT-derived response as separate outcomes. CIT-06 is an islet-after-kidney population, which adds renal context for C-peptide clearance. | Catalogue-level screen only: no alternative same-test dynamic G/I/C-peptide crosswalk is documented there. We did **not** audit every dictionary or establish that additional data do not exist. Each release requires its own access and protocol check. |
| [NCT01817959](https://clinicaltrials.gov/study/NCT01817959?tab=results), randomized reparixin/placebo islet-transplant trial | The official registry reports group-level mixed-meal glucose, insulin and C-peptide summaries at basal, 15, 30, 60, 90 and 120 minutes for three post-transplant visit labels. This is a meal challenge, not IV glucose. | Public aggregate results are inspectable, but the registry record supplies no participant-linked triplets or individual-data grant. Its trajectory cannot validate the IVGTT-specific BC-004/OT-026 model. A meal model and a new protocol would be needed for a later, separate assessment. |

The last row is worth retaining as a **possible descriptive external context**,
not as a replacement development or held-out cohort. Means and standard
deviations of glucose, insulin and C-peptide by treatment arm do not reveal
within-person covariance, exact co-observation, censoring, exogenous insulin
timing or individual trajectories. The registry's missing IPD-sharing field
does not establish whether separately obtainable participant data exist or
what rights they would carry.

## Executable registry check

The [frozen protocol](../../experiments/m4/measurement_readiness/registry-aggregate-protocol.json)
pins the official [ClinicalTrials.gov API v2
record](https://clinicaltrials.gov/api/v2/studies/NCT01817959) by SHA-256. The
[standard-library auditor](../../experiments/m4/measurement_readiness/registry_aggregate.py)
checks the three published outcome titles, units, result labels, two arm IDs
and per-cell denominators. It reports only aggregate structure and sample
counts; it does not copy measured values into the report. The 25 September
2026 snapshot SHA-256 is
`8fc0882a095628215af1ef588f0b3fa1d08e62c7cd28bd04fb873cff91d054b5`.
The full public registry JSON remains in ignored local `results/`, not Git.

The completed [execution record](../../experiments/m4/measurement_readiness/execution-registry-aggregate.json)
shows 18 common published class labels across the three signals, but only
**17 of the 18 prespecified visit/time labels**. All three published outcomes
label the final 120-minute entry `day 365 - Transplant 2`, while the preceding
five entries are `day 365 - Last transplant`. The auditor preserves that
discrepancy; it neither corrects the registry nor silently calls the final
point a last-transplant sample. In **19 of 36** arm-by-label cells, the
published participant denominators differ across at least two analytes.
Even matching denominators would not establish person-level pairing.

To rerun against the *same public record bytes*, from the worktree root:

```sh
mkdir -p results/m4-measurement-readiness/registry-aggregate
curl -fsSL 'https://clinicaltrials.gov/api/v2/studies/NCT01817959' \
  -o results/m4-measurement-readiness/registry-aggregate/NCT01817959.json
python3 -m experiments.m4.measurement_readiness.registry_aggregate \
  --source-json results/m4-measurement-readiness/registry-aggregate/NCT01817959.json \
  --output results/m4-measurement-readiness/registry-aggregate/report-new.json
```

The byte check intentionally fails if the public registry record changes;
compare the new record with the pinned source before revising this screen.
Three focused tests cover a mismatched visit label, unequal denominators and
an incomplete group summary. This is a source-structure audit, not a
statistical test or a reproduction of a trial endpoint.

## Decision and next evidence gate

None of these public-source checks closes the current IV paired-observation
gate. Keep the existing IVGTT reference and conditional synthetic results
unchanged. The next empirical step remains a **versioned, authorized**
challenge-level source with linked glucose/insulin/C-peptide collection times,
early and late C-peptide, actual exogenous-insulin timing, assay/renal context
and a participant-disjoint allocation, followed by independent domain review
before fitting. The [unsent collaboration brief](m4-collaboration-brief.md)
now includes this alternate-source verdict and a precise request for whether
such a release exists. If only an MMTT series can be obtained, specify a new
meal-input biology and validation question first; do not rebrand it as the
published IVGTT reference.
