# OT-055 held-out empirical evaluation preparation

Status: **prepared requirements, not an authorized empirical protocol**.
No suitable participant observations, access rights, investigator, clinical
margin, sample size or empirical result is established. Public fixtures are
invented. This document does not approve prospective clinical sampling.

The [canonical task plan](roadmap-history-2026-10-28.md#planned-mixed-meal-analysis-tasks)
and [decision 0066](../decisions/0066-observation-analysis-tasks.md) govern this
work. [Decision 0067](../decisions/0067-mmtt-feasibility-boundary.md) freezes
the separate synthetic endpoint as whole-body total secretion including basal
in pmol and follow-up minus baseline; it does not qualify human kinetics or
authorize observations. The [sampling guide](../mmtt-sampling.md) describes current software and
its technical dependencies. Do not execute held-out human analysis until the
following source-specific items have been resolved and recorded before access.

## Required source-specific freeze

| Item | Required record before evaluation | Current state |
| --- | --- | --- |
| Authority and rights | Local data owner, permitted analyses, storage/export restrictions and access evidence | Unconfirmed |
| Observations | Adult T1D scope, two linked standardized MMTT visits, actual 0–120-minute times, glucose and C-peptide, completeness audit | Unconfirmed |
| Assay and context | Units, LOD/LOQ, censoring, laboratory error, renal and medication/insulin context, challenge and visit comparability | Unconfirmed |
| Shared method | Checked OT-054 source/runtime, physical endpoint units/normalization, initial/basal conventions, assumptions and diagnostics | Synthetic core checked; human domain qualification open |
| Conditional uncertainty | Method justified for actual assay/missingness and kinetics; separate assumption sensitivity | Unconfirmed for human measurements |
| Participant allocation | Immutable development and evaluation identities, all visits together; access history and selection rationale | Synthetic fixture only |
| Schedules | Full observed schedule and two or three actual-time subsets selected on development participants | Synthetic fixture only |
| Interpretation | Shared paired-change rules and uncertainty treatment; glucose-context interpretation | Needs domain freeze |
| Agreement margins | Absolute endpoint and paired-change differences, allowed bias, precision, uncertainty and failure requirements | Must be chosen with researchers; no default clinical percentage |
| Low values | Assay-informed low-C-peptide stratum, censoring rule and minimum subgroup precision | No invented clinical cutoff |
| Size and precision | Participant number justified for agreement/paired-change uncertainty and low-value coverage | Open; six product users do not determine clinical sample size |
| Oversight | Named responsible investigators/reviewers and signed plan identity before evaluation | Unconfirmed |

Record each resolved choice, source, rationale, date and plan hash. If a margin
or method cannot be justified, report descriptive agreement as exploratory and
leave empirical acceptance unresolved. Amendments after evaluation access must
be explicitly post hoc and cannot retroactively validate the original freeze.

## Evaluation procedure to finalize

1. Audit development observations and protocol requirements. Choose two or three
   schedule subsets supported by actual times. Record why each can answer the
   scientific question; omission of another analyte's required sample does not
   automatically reduce blood draws.
2. Freeze participant allocation, schedules, shared analysis and uncertainty
   plan, scientific margins, low-value definition and missing/failure rules.
   Hold all visits of an individual in one allocation. Freeze independently
   sourced kinetics; prohibit participant parameters learned from removed data.
3. Check the software on permitted synthetic known cases and selected failures,
   including perturbed omitted observations and fresh isolated estimator calls.
   Review numerical correctness separately from population applicability.
4. Record authorization and evaluation access. Run every planned full/subset and
   assumption attempt. Remove observations before interpolation, basal estimation,
   fitting, initialization and uncertainty calculation; rerun the same method.
5. Compare reference and subset results on each planned evaluation visit and
   paired participant. A full-reference failure precludes a reference difference;
   a subset failure remains a failed attempt. Neither disappears from coverage.
6. Report signed differences, absolute differences, bias, precision and their
   participant-based uncertainty; show paired-change conclusions and disagreement
   including indeterminate results. Account for correlation between visits within
   a person and between nested schedules. Select interval procedures before
   access; do not report a standard deviation as uncertainty in the mean bias.
7. Show all participants, glucose context, low-value subgroup, censored/missing
   measurements, failure categories and uncertainty. Apply frozen margins only
   with their intended units and scope. Insufficient precision is indeterminate.
8. Retain negative results: **no reduced schedule meets the criteria** is valid.
   Preserve the complete archive and reconstruct reports independently of fitting.
   An independent domain reviewer assesses interpretation; independent users
   assess usability separately in OT-056.

## Handoff cases for OT-056

Use invented cases to test whether a researcher recognizes: compatible full and
reduced estimates with unresolved empirical margins; a subset that loses an
interior response; low/censored C-peptide; a missing requested time; full-reference
failure; failure in only one paired visit; changed glucose exposure; and a design
that attempts to select schedules using evaluation participants. The scoring
rubric must require correct units, visit pairing, failure denominators and
explicit uncertainty. These are case requirements, not observed user outcomes.

The [OT-055 verification and handoff](ot055-verification.md) now supplies a
reproducible four-case software packet with native archives and expected answers,
plus checks for missing requests, omitted-value poisoning, invalid references
and evaluation-based selection refusal. These cases prepare the independent
exercise; no researcher sessions or empirical assessment have been performed.
