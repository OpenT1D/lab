# OT-027/0.2 — Islet graft function and later insulin burden

**Status:** source-aligned question and data-feasibility protocol, 25 September 2026;
source-specific study owner and external reviewers unassigned. This is not
an empirical analysis freeze or an implemented therapy experiment. The
[roadmap](../../ROADMAP.md#m5--one-defined-cell-or-immune-therapy-question) owns
the M5 acceptance criteria. The [data requirements](m5-cell-therapy-data.md)
and [CIT-07 public-source assessment](m5-cit07-feasibility.md) are part of
this preparation.

## Identity, question and intended use

The first M5 candidate is **islet cell replacement in people with T1D**. Its
bounded question is whether the level of measured post-graft secretory
function, and its persistence when repeated pre-outcome measurements exist,
adds useful prediction of **later documented external-insulin burden** beyond
a simpler baseline using prior insulin burden, glycemic status and time since
transplant. This is a prospective analysis design for researchers who obtain
their own permitted data; OpenT1D does not supply participant records.

The intended output is a reproducible comparison of prognostic models for a
named population and follow-up window. A positive result would support only
the prespecified predictive claim in that source. It would not establish that
the transplant caused the outcome, that graft cell mass was measured, that a
particular cell product works, or that anyone was cured. Insulin independence
is a separate clinical endpoint whose definition and complete treatment
ascertainment must be supplied and reviewed before use.

## Population, time origin and mechanism boundary

The candidate population is recipients of an islet transplant for established
T1D. The exact graft product, implantation site and drainage, number and dates
of infusions, concomitant therapies, eligibility criteria and renal context
must come from a versioned study release. Do not pool islet-alone,
islet-after-kidney, stem-cell-derived products or residual native secretion
without a prespecified, biologically reviewed reason. A source-specific
protocol will confirm or replace the source-aligned **landmark** and later
outcome window below before any participant-level fitting. Use the first
infusion as the provisional clock origin; do not retrospectively select the
final infusion as a baseline. Record every repeat infusion between landmark
and outcome as intervening treatment, including its decision process.

The measured signal is an observed, assay-qualified C-peptide response under
a named challenge, with its concurrent glucose and treatment context. It is
not automatically a secretion rate or a count of surviving graft cells. A
source-specific analysis may use a simpler observed-response summary; it may
use the M4 forward/inverse models only after their route, baseline, kinetics,
sampling and population assumptions are reviewed for that challenge.

Existing [BC-008 feedback](m4-feedback-results.md) varies a **hypothetical**
secretion gain in one virtual profile. Its portal source, matched basal
replacement and four-hour meal scenario do not model transplantation,
engraftment, immune protection, graft survival or treatment decisions. It
cannot currently estimate reduced insulin need. A future simulation of graft
capacity or persistence requires a separately justified intervention-to-
function rule, graft site/route, basal state, exogenous insulin policy and
longitudinal timescale. Changing the BC-008 gain alone is not that rule.

## Source-aligned candidate comparison, to freeze after release review

| Element | Proposed source-specific choice | Gate before execution |
| --- | --- | --- |
| Index | Provisional 75 ± 5-day visit-10 MMTT function assessment after the **first** infusion | Verify the first-infusion date, actual challenge date and pre-outcome information boundary; distinguish protocol-directed noncollection after confirmed graft failure |
| Primary outcome | Provisional seven-day diary-based mean insulin amount associated with the 365 ± 14-day **Y1 first-infusion** visit; normalize by contemporaneous weight only when verified | Distinguish Y1 from visit 15 after a later infusion; check actual seven-day coverage, diary semantics, visit linkage and units; this is not pump-measured delivery |
| Secondary outcomes | Source-supported glycemic and treatment-burden measures | Confirm assay/device semantics, observation windows and missingness |
| Simple comparator | Prior insulin burden, glycemic status and elapsed time, using only information available at the landmark | Specify exact variables and fitting budget before evaluation |
| Added-function candidate | The same comparator plus one prespecified observed MMTT C-peptide/glucose summary | Select the summary and assay rules on development material only; exclude the composite beta-score because it contains insulin use |
| Persistence extension | A repeated function assessment before a later, separately timed outcome, only if the release documents it | A day-365 function value cannot predict the simultaneous day-365 insulin outcome |
| Mechanistic extension | M4 secretion/kinetic features or a simulated persistence trajectory | Require the separate M4 biological and therapy-mechanism gates below |

The named visits are scheduled by the public [CIT-07 protocol v8](https://test.repository.niddk.nih.gov/media/studies/cit-07/Protocol.pdf),
not verified observations or clinical definitions of sustained benefit. If
the release lacks the linked measurements, amend this protocol before
participant-level analysis; do not search alternative windows on reserved
outcomes. The [source assessment](m5-cit07-feasibility.md) records the
repeat-infusion and beta-score predictor-contamination risks. The
[public-dictionary crosswalk](m5-cit07-dictionary-crosswalk.md) confirms that
the mean-insulin table's `NumDaysInitial` is its seven-day interval start,
not the outcome visit day; a native converter must establish that visit
separately. This table chooses the
**question and comparison structure**, not a final variable set, model,
threshold or dataset. The later empirical protocol must specify those
details, a meaningful minimum benefit,
acceptable degradation, uncertainty method and failure policy before the
reserved evaluation is read. It must compare added complexity with the
simple reference even when the added function is plausible biologically.

An observational recipient cohort can test prediction and association. A
causal treatment-effect claim additionally needs a defensible comparator or
intervention design and an analysis of selection, concomitant care and
time-varying confounding. Better prediction within treated recipients does
not substitute for that design.

## Data and calibration boundary

Use the [OT-027 data contract](m5-cell-therapy-data.md) to screen source
documentation before opening participant records. For a selected release,
record provider, exact version, rights, source bytes and variable-level
crosswalk. Obtain authorization under the source's terms. Keep raw and
participant-level derived data outside Git, public CI and public examples.

Before fitting, reserve participants or an independent study for evaluation;
group every visit and repeated graft event from a person together. Check
overlap with M4 development and any source used to choose the function
summary. Fit preprocessing, missingness rules, model parameters and
calibration only on development material. A new time window from the same
person answers a narrower generalization question than a new person or
study. Do not treat repeated observations as independent participants.

Missing insulin diary entries cannot become zero use. Below-assay-limit C-peptide,
unknown treatment timing, ambiguous challenge identity and missing outcomes
remain distinct states with planned denominators. If the release lacks a
valid same-challenge function measure, narrow the question or stop. Do not
infer graft function from CGM alone or relabel a meal challenge as the M4
IVGTT reference.
The [public form/laboratory audit](m5-cit07-form-lab-audit.md) adds a distinct
day-75 protocol-directed noncollection state after confirmed graft failure
and separates visit 15 from first-infusion Y1 at day 365. These source
facts do not establish the released table's visit codes or eligibility.

## Analysis and evidence gates

1. **Source feasibility:** verify the data contract and permitted outputs.
   Record supported, contradicted and unresolved requirements. A catalogue
   description is not an access grant or an observed cohort.
2. **Scientific review:** a transplant/T1D clinician, secretion/kinetics and
   assay specialists, and a statistician review the named population,
   landmark, measurement, endpoint and comparator using the
   [OT-027-P4 review packet](m5-domain-review-brief.md). Record each
   reviewer's scope and unresolved objections; no reviewer is currently
   assigned.
3. **Empirical freeze:** write a new version with source/release identity,
   participant allocation, confirmed or revised windows, variables, model specification,
   uncertainty, failure/exclusion accounting and success criteria. Freeze it
   before fitting or scoring reserved observations.
4. **Execution:** compare the simple and added-function models on the same
   eligible people and later windows. Report person-level uncertainty,
   calibration, missingness, censoring, failures, coverage and the change in
   predictive error. Preserve negative and incomplete results.
5. **Mechanistic extension, only if justified:** independently verify any
   new graft-to-secretion and secretion-to-metabolism coupling, simpler
   controls, units, initial conditions, mass balances, numerical refinement
   and observation fit. A synthetic run is labelled exploratory even if all
   checks pass.

No numerical performance threshold, human sample-size claim or treatment
effect is fixed by this feasibility protocol. The empirical gate cannot be
closed by the current synthetic M4 results or a software test.

## Reproduction, review and change control

A [synthetic visit-linkage preflight](../m5-release-preflight.md) now checks
the proposed first-infusion clock, MMTT sample availability, diary-day
coverage and intervening infusions on invented metadata. It does not open a
human release or compute the prognostic comparison. A separate
[fixed synthetic prognostic comparison](../m5-synthetic-prognosis.md) now
exercises the baseline-versus-observed-function analysis on invented values.
Its toy ridge specification does not freeze the future empirical model.
A future OpenT1D tool
workflow should accept a user-provided, authorized source through a
source-specific converter; preserve native bytes privately;
record code, locks, protocol, parameter/source ancestry and access history;
retain every planned case and failure; and rebuild permitted reports from
saved artifacts without the model runtime. Public examples should use
clearly labelled invented observations. The human-source workflow is
**planned**, not implemented by this document. It requires no
repository-held patient data.

The current public source assessment is limited. The [CIT-07 dictionary
crosswalk](m4-cit07-public-crosswalk.md) does not establish a same-challenge
dynamic glucose/insulin/C-peptide series; its core FSIGT schedule contradicts
the late C-peptide requirement for the current M4 kinetic question. An
early-only observed-response predictor would need its own verified challenge
linkage, assay and population review. The [alternate-source screen](m4-alternative-observation-screen.md)
finds only aggregate mixed-meal values in the inspected public trial result.
Neither supplies a ready empirical OT-027 cohort. The [M4 review brief](m4-collaboration-brief.md)
contains unsent questions about graft interpretation and suitable
measurements; it records no contact or endorsement.

Revisit the question if a source supports only sparse observed C-peptide,
cannot distinguish treatment burden from prescribed doses, lacks participant
linkage, changes graft route/population, or cannot support an independent
allocation. Preserve this version and record any narrowed replacement before
analysis. OT-026 biological assessment and M5 intervention evidence remain
open; this preparation closes neither milestone.

## Changes from 0.1

OT-027/0.1 proposed day 90 and a continuous days-270–365 insulin-burden
window without a source-specific schedule. The [public CIT-07 assessment](m5-cit07-feasibility.md)
found scheduled 75 ± 5-day MMTT assessments and a 365 ± 14-day follow-up
with a seven-day diary insulin summary. Version 0.2 aligns the candidate
clock and outcome to those documented visits, fixes the first infusion as
the provisional origin, and explicitly retains later infusions and
beta-score predictor contamination. No participant record or reserved outcome was
inspected when making this amendment. The empirical protocol remains
unfrozen.
