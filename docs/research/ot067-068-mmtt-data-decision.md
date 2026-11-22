# OT-067/068 — Paired MMTT question, source and method decision

**22 November 2026 · Conditional.** Select one within-person secretion question,
TrialNet TN05 v2 CSV as the preferred source route, and the existing OpenT1D
paired estimator for synthetic rehearsal. First resolve the export crosswalk.
The [18 October OT-053 NARROW decision](ot053-mmtt-feasibility.md) remains the
historical feasibility record and sets the synthetic evidence boundary.

## Research question and estimand

The intended analyst works on beta-cell preservation with a secretion modeller
and an assay specialist. Researcher participation and independent review are
unconfirmed. For an adult aged 18 or older at the pre-treatment baseline, with
recent-onset stage 3 type 1 diabetes and documented residual secretion, ask
whether the direction of change between the designated baseline and 12-month
standardized mixed-meal tolerance tests (MMTTs) holds across prespecified
assumptions. For TN05, propose adults assigned to placebo to keep one trial
context. Eligibility, visit windows and arm linkage require review before
freezing. Keep all screened people, intended visits and exclusion reasons in the
coverage report, including missing or unusable pairs.

For each visit and assumption set, estimate whole-body endogenous insulin
secretion rate `q(t)` in pmol/min from C-peptide, assuming equimolar appearance.
The visit total `S = integral of q(t) from 0 to 120 min` includes basal secretion.
The estimand is each person's `S_12_month - S_baseline` in pmol, with no body
size, glucose, duration or baseline normalization. Report C-peptide AUC and
AUC/120, measured traces, fasting glucose and glucose AUC as separate references
and context. The scope is a descriptive paired assessment of response under
the two meals. Cohort effects, treatment contrasts and clinical interpretation
are outside this question.

In the synthetic rehearsal, a direction is consistent if every required
variant's conditional interval is wholly on the same side of zero. Complete
variants that disagree with at least one resolved direction are assumption-dependent.
An all-unresolved result or any required failure is insufficiently determined.
Before empirical evaluation, justify clearance, distribution volume, fasting
initial state, assay error, censoring and within-person error dependence across
visits. Freeze interpretation and any meaningful-change margin with domain
review. Glucose exposure, medication and renal changes can affect interpretation.
The rehearsal uses fixed supplied kinetics and invented measurement error.
[Endpoint conventions and synthetic decision rule](../observation-analysis.md#conditional-uncertainty-and-interpretation)

## Source and minimum crosswalk

The [TN05 v2 CSV field mapping](tn05-v2-csv-field-mapping.md) records the
follow-up audit of linkage, timing, units and censoring metadata.

The production NIDDK-CR catalogue was retrieved on 22 November 2026. TN05
Version 2 (DOI `10.58020/1bv7-0y43`) is available for controlled request for
T1D and related complications. The trial enrolled across pediatric and adult
ages soon after diagnosis. Its paper describes four-hour MMTTs at baseline
and one year, with a C-peptide concentration AUC mean over the first two hours
as the primary outcome. The protocol places the screening MMTT before
randomization. The historical integrity script uses `Screening` and
`52 weeks` for `PEP120`, which is a lead for locating the two tests.
Confirm that the pre-randomization test supplies the analytic baseline and
verify both visit windows against the release. Published totals and catalogue
counts supply no usable adult placebo-pair count.
[Production catalogue](https://repository.niddk.nih.gov/study/76),
[DataCite DOI metadata](https://api.datacite.org/dois/10.58020/1bv7-0y43),
[trial paper, Methods](https://pmc.ncbi.nlm.nih.gov/articles/PMC6410357/),
[TN05 protocol, §5.6 and Appendix A](https://repository.niddk.nih.gov/media/studies/tn05-anticd20/tn05_protocol.pdf),
[integrity check, pp. 17–18](https://repository.niddk.nih.gov/media/studies/tn05-anticd20/tn05_dataset_integrity_check.pdf)

The catalogue lists both CSV and SAS exports. Its CSV column metadata for
Research Labs agrees with the 12 variables in the public SAS dictionary on
page 67. The public lab workbook describes labels across three TrialNet
studies. The catalogue, dictionary and workbook document a candidate structure
and code meanings. The crosswalk below records what remains to establish for
the requestable CSV.
[TN05 dictionary](https://repository.niddk.nih.gov/public/study_document/TN05_V2/TN-05%20Documentation/TN05_Data%20Dictionary.pdf),
[lab label workbook](https://repository.niddk.nih.gov/public/study_document/TN05_V2/TN-05%20Documentation/TrialNet%20Lab%20Value%20Labels-TN01_TN02_TN05%2020120202.xlsx)

| Required mapping | Public metadata | Evidence still needed |
| --- | --- | --- |
| Participant, arm and ordered visit | `MaskID`, `Visit`, `Date_of_Draw`; RIT01 screening age and MMTT date; participant treatment table lists `TreatmentName` and `Randomization_Date`; RIT12 has four-hour MMTT flags and dates. | Verify pseudonym scope and join cardinality, randomized assignment versus received treatment, pre-treatment baseline and 12-month labels and windows. Retain intended visits and missed-visit reasons from RIT16 where linked. |
| Challenge, specimen and analyte | Research Labs lists `event_title`, `SPEC_NAME`, `SampleMaskID` and `TEST_NAME`. The workbook labels four-hour MMTT `PEP0`/`GLU0` through `PEP120`/`GLU120`; codes recur across different challenge types. | Identify one challenge instance per selected visit, unique specimen/result keys and the documented link for glucose and C-peptide from that test. A shared analyte code or date cannot establish the match. |
| Actual collection time | `Date_of_Draw` is date-formatted. The labels encode nominal minutes. The published sampling design includes −10, 0, 15, 30, 60, 90 and 120 minutes. | Find actual elapsed minutes or meal-start and sample clocks and keep nominal times and result-report dates separate. The synthetic importer requires measured 0 and 120 minutes without relabeling, rounding or extrapolation. An empirical timing rule needs separate review. Use −10 for fasting context and keep samples after 120 outside the endpoint. |
| Result, units, assay and status | `RESULT` and `OUTCOME` are character fields in the SAS dictionary. The paper reports its AUC mean in pmol/mL. A related TN05 analysis reports substituting the assay LOQ for non-measurable values when computing AUC. | Verify raw result syntax, per-analyte units, specimen matrix, platform/calibration, assay era or batch, LOD/LOQ, precision and how noncollection, missingness, censoring and any prior substitution are encoded. Preserve original tokens and use versioned conversions to glucose mmol/L and C-peptide nmol/L at synthetic import (pmol/L in the estimator). |
| Visit and measurement context | RIT01/RIT02 cover demographics and diagnosis; RIT11/RIT12 list body size; RIT09/RIT10 and RIT21 cover diabetes management, medication and deviations. The lab workbook includes chemistry creatinine `CREA`. | Verify age at baseline, sex, visit-specific body size and dated renal measurements with units. Link meal formulation, dose, completion and fasting, peri-test insulin/medications and deviations to each test. General management summaries alone cannot establish insulin timing. |

[TN05 catalogue field metadata](https://repository.niddk.nih.gov/study/76),
[Lachin et al., Methods and Procedures](https://pmc.ncbi.nlm.nih.gov/articles/PMC3213096/)

Dataset access, a project-specific ethics determination, an executed use
agreement and an approved storage/execution location are unconfirmed. A future
authorized custodian would need to verify the delivered release identity,
tables and immutable references, linkage permissions, retention and permitted
derived outputs. They would audit the adult placebo roster and paired coverage
by visit, required time, analyte, assay, context and exclusion reason. Precision
and feasible participant-disjoint development/evaluation allocations depend on
that audit. This decision uses public documentation only.
[NIDDK-CR requestor FAQ](https://repository.niddk.nih.gov/faq),
[project data and provenance guide](data.md)

## Reuse and next step

Use the repository-provided CSV with a standard CSV reader once the export's
encoding, headers, keys and value codes are documented. R's `haven::read_sas`
is an existing extraction option if SAS is needed to check formats or labels
lost in CSV. Select a bridge to CDISC SDTM only if a consuming workflow needs
it and the source semantics are established.
[Python CSV reader](https://docs.python.org/3.12/library/csv.html),
[haven SAS reader](https://haven.tidyverse.org/reference/read_sas.html),
[CDISC SDTM](https://www.cdisc.org/standards/foundational/sdtm)

Reuse the OT-054 fixed-kinetic, two-compartment estimator with piecewise-linear
concentration and full interval mass balance, plus its frozen plans, retained
failures and report reconstruction. Use the existing OT-056 paired
same-estimator notebook as the product baseline. Give it the same source
mapping, cases, variants and reporting requirements. Compare correctness,
preparation and repeat effort, assistance and whether a second analyst can
reopen the report. The OT-053 pinned R `insulin.secretion` audit remains a
method comparator lead pending independent full-window, native execution and
licensing review. Its midpoint linear output needs endpoint reconciliation
before numerical comparison.
[Estimator and synthetic input contract](../observation-analysis.md),
[OT-056 notebook and rehearsal](ot056-researcher-pilot.md#controlled-task-1-execution),
[OT-053 method audit](ot053-mmtt-feasibility.md#method-and-reuse-audit)

**Proceed with the crosswalk and defer conversion.** A first converter needs a
versioned CSV schema supported by authoritative metadata or a permitted
metadata-only example. Confirm the table set, join and rejection rules,
challenge and actual-time encoding, value/censor codes, unit mappings and
permission to publish the fixture. If only nominal times are documented,
record the timing gap and leave that export ineligible for this estimand.
The first acceptance case should use invented TN05-shaped CSVs with one clean
pair, known totals and an independent expected mapping. Include counterexamples
for duplicate or conflicting results, ambiguous
challenge/visit matches, missing visits or endpoints, censored values and wrong
or undeclared scales. Preserve source rows and dispositions. Require explicit
replicate handling, visible exclusions, no silent zero/LOQ substitution, and
exact unit checks with scale-equivalent controls such as 1 pmol/mL = 1 nmol/L.
Rerunning the same frozen export and mapping must regenerate the same normalized
observations and result payload. A row-reordered export with equivalent
observations must preserve the scientific payload while retaining its own
byte digest. Version mapping changes separately.

Technical acceptance is repeatable synthetic intake, analysis and reconstruction
through the existing project and result services. Empirical acceptance requires
authorized access, usable pairs and a separately qualified, scientifically
reviewed measured-data protocol and method. Independent user acceptance requires
observed sessions with an intended analyst and a separate result recipient.
Each remains open for this source-to-study route.
