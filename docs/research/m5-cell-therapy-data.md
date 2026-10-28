# OT-027/0.2 — Data requirements for the islet-function question

This is the source-screening companion to the [OT-027 feasibility
protocol](m5-cell-therapy-protocol.md) and [CIT-07 public-source assessment](m5-cit07-feasibility.md).
It states what a researcher must
verify in a **versioned, permitted release** before an empirical analysis can
be frozen. OpenT1D supplies software and synthetic examples, not participant
data, access rights or a clinical endpoint definition. The [data guide](data.md)
sets the repository-wide provenance and privacy rules.

## Two evidence stages

The [synthetic visit-linkage preflight](../m5-release-preflight.md) exercises
parts of R2, R4 and R5 on invented availability records. It is separate from
both stages below and does not establish any actual release coverage.
The [CIT-07 public-dictionary crosswalk](m5-cit07-dictionary-crosswalk.md)
records the native field roles that a later private converter must respect.
The [source-shaped CSV rehearsal](../m5-native-rehearsal.md) tests those
roles with invented rows only.
The [scientific review packet](m5-domain-review-brief.md) turns the R1–R8
gates into specific decisions and a blank record; no review has occurred.
The [public form and laboratory audit](m5-cit07-form-lab-audit.md) identifies
two separate 365-day visit clocks, conditional MMTT samples and diary
missingness controls. Their representation in a released participant table
still needs verification.

The **metadata stage** uses public or separately authorized dictionaries,
protocols and rights documents. It checks whether a proposed release might
support the question without inspecting participant values. The **record
stage**, only after authorization, verifies actual linkage, units, clock,
coverage, missingness and split feasibility. Passing metadata screening does
not imply that the records pass. A missing field is unresolved until its
absence is verified; a protocol-scheduled sample is not proof that it was
collected for each person.

| ID | Requirement | Metadata evidence | Record-stage check and consequence if absent |
| --- | --- | --- | --- |
| R1 | Source identity and rights | Provider, study/release version, use, storage, analysis, publication and derived-output terms | Bind exact native bytes and permitted purpose; without rights, do not access or execute |
| R2 | Person, event and visit linkage | Pseudonymous person key; transplant and challenge event keys; repeat-infusion rules | Verify one person's events and visits stay linked; without linkage, no longitudinal prediction or person-disjoint split |
| R3 | Treatment and population | T1D stage, product/source, graft site and drainage, infusion dates/amounts, immunosuppression and other relevant therapies | Check actual treatment histories and source-defined subgroups; without mechanism/site information, no graft-specific coupling claim |
| R4 | Post-graft function measure | Named challenge, glucose/C-peptide assay fields and planned sample times, basal definition, units, matrix, limits and precision; repeated challenge availability for persistence | Verify same-challenge times, glucose context, censoring and repeats before the outcome window; without a defensible signal, do not add a graft-function predictor |
| R5 | Exogenous insulin burden | Amount unit, observation interval, route/formulation and whether each value is prescribed, reported, dispensed or delivered | Check completeness, duplicate/conflicting entries and body mass; without an interpretable amount, no primary burden outcome |
| R6 | Later glycemic and clinical context | Laboratory/CGM/HbA1c semantics where available; outcome definitions and observation windows | Check actual coverage, sensor/assay changes and treatment-context overlap; unsupported outcomes remain absent, not zero |
| R7 | Kinetic and confounding context | Renal function, body mass, insulin sensitivity proxies, concomitant drugs, illness/rejection and care changes where relevant | Quantify availability by person/window; unknown clearance or care changes limit mechanistic and causal interpretation |
| R8 | Independent assessment | Number of people, visits, studies and follow-up coverage; restrictions on split and export | Freeze a person- or study-disjoint allocation before fitting; if infeasible, report development-only evidence |

R1, R2, R4, R5 and R8 are required for the proposed **prognostic** comparison.
R3 and R7 are required to interpret its population and limitations; absent
details may force narrowing even if prediction is technically possible. R6
determines which secondary outcomes can be evaluated. A claim about graft
mechanism or treatment benefit needs stronger R3/R7 evidence and a separate
comparison design; this table does not grant one.

## Additional gate for M4-derived features or simulation

The [M4 paired-measurement contract](m4-paired-protocol.md) is stricter than
the prognostic minimum above. Any use of a modeled secretion rate or the
BC-008/BC-010 glucose-feedback and C-peptide branches must establish the
actual challenge route and stimulus, time-linked glucose, insulin and
C-peptide, exogenous insulin timing, basal and body-mass conventions,
assay/censoring details, renal/kinetic information and graft site/drainage.
Early and sufficiently informative later C-peptide observations or an
explicitly reviewed narrower kinetic question are needed. Keep secretion,
clearance, volume and capacity ambiguities visible. A favorable synthetic
sampling result does not prove that a release contains those observations.

An intervention-to-function law would need independently justified evidence
for engraftment, persistence or loss and treatment exposure. The current
M4 dimensionless gain is a sensitivity parameter, not graft survival,
cell mass or a therapy dose. If these facts are unavailable, the OT-027
prognostic question may still be evaluated from a defensible observed
function measure; the mechanistic simulation must remain unexecuted or
explicitly hypothetical.

## Present source-feasibility verdict

| Candidate public evidence | What it supports | What it does not establish |
| --- | --- | --- |
| [CIT-07/08 public dictionaries](m4-cit07-public-crosswalk.md) | Potential subject/day keys and separate dynamic glucose/insulin and sparse C-peptide fields | Same challenge/event C-peptide linkage, late core-FSIGT C-peptide, actual per-visit treatment timing, access rights or person-level outcome coverage |
| [Nearby CIT and trial-result screen](m4-alternative-observation-screen.md) | Other transplant-source leads and aggregate mixed-meal result structure | A participant-linked three-analyte IV series or individual longitudinal burden/outcome data |
| [BC-015 synthetic sampling study](m4-sampling-window-results.md) | Conditional numerical value of hypothetical later C-peptide samples under a known pulse | A real collection schedule, human identifiability or permission to use a dataset |

For CIT-07/08 Version 2, the current **metadata-only** screen against this
new question is:

| Requirement | Status | Reason still open |
| --- | --- | --- |
| R1 | Unresolved | The catalogue offers data by request; OT-027 has no access or use grant |
| R2 | Unresolved | Subject/day fields exist, but a transplant/challenge/event crosswalk has not been verified |
| R3 | Unresolved | The protocol identifies an islet-transplant setting; actual product, site, infusion and concomitant-treatment coverage has not been audited |
| R4 | Unresolved | Early C-peptide is scheduled, but linked collected values, assay semantics and repeated pre-outcome tests are unverified; late core-FSIGT C-peptide is contradicted for the stricter M4 question |
| R5 | Unresolved | The protocol describes daily self-monitoring diaries and a seven-day mean; actual diary coverage, visit linkage and use semantics are unverified, and no measured delivery is established |
| R6 | Unresolved | Later glycemic outcomes and their person/window linkage have not been verified for this question |
| R7 | Unresolved | Weight and GFR field names occur in separate dictionaries; temporal coverage and treatment context are unverified |
| R8 | Unresolved | Participant/visit coverage and a disjoint allocation have not been inspected |

No inspected public packet has been assessed at the **record stage**, so none
is ready for OT-027 execution. CIT-07 data are described as available for
request, and no OT-027 request, native release review, participant-level
analysis or external scientific review has been performed. This is a gap
assessment, not a conclusion that no suitable study exists.

The source-specific P2 review supports a candidate 75 ± 5-day MMTT function
landmark and 365 ± 14-day seven-day insulin summary after the **first**
infusion. It replaces 0.1's unsupported day-90 and days-270–365 planning
windows. These are scheduled visits, not verified observed coverage. A
second infusion can occur between them and must remain in the analysis.

## Source-specific handoff

Before implementation, complete a source matrix with each R1–R8 status
(`supported`, `contradicted` or `unresolved`), exact document/release identity,
variable name and unit, observed-vs-scheduled distinction, reviewer and
permitted-use evidence. Then write the empirical protocol's landmark,
windows, function summary, burden semantics, exclusions, comparator,
uncertainty and split. Record who reviewed assay, transplant mechanism and
statistical design and what remained unresolved. Public outputs may contain
only what the source terms permit; private records and sensitive derived
values stay outside the repository.
