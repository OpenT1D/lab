# M4 scientific-review and collaboration brief

**Draft for maintainer review; not sent.** No group has agreed to collaborate. This document does not authorize contact, an access application or patient-data transfer. See the [evidence dossier](m4-evidence-dossier.md) for the sources, inspected assets and access limitations.

## Proposed scientific conversation

OpenT1D is developing reproducible, modular computational experiments for T1D research. Its first standalone beta-cell reference implements the two-state IVGTT reduction in Pedersen and Cobelli (2013), [DOI 10.1098/rsfs.2012.0085](https://doi.org/10.1098/rsfs.2012.0085). The supplied declining glucose curve is synthetic. The output is glucose-evoked insulin secretion in micrograms per minute, not a prediction of transplant efficacy or a clinical dosing recommendation.

We would value a bounded review of the equations, initialization, output interpretation and conditions under which the reduction may be used. In particular:

- Does the BC-006 pre-bolus-pool explanation reconcile the published initializer with the explicit 92.7-microgram value, and which exact warmup state, initialization clock and revised or confirmed equations should be used? See the focused packet below; no correction is assumed.
- Is a versioned, permitted numerical reference available for Figure 2, including glucose input, initial states and expected output? Which author-code license applies?
- Which assumptions fail first in residual T1D secretion or intrahepatic grafts? Does a capacity multiplier conceal changes in recruitment, basal release or delayed secretion?
- What C-peptide kinetic model and independent measurements would support separating secretion from clearance in the intended population?
- Which aggregate/dynamic parameter combinations could be identified from the available test schedule, and which should remain fixed?

We can provide the executable protocol, independent numerical checks, parameter/source record and report. Review of software correctness and review of biological applicability would be recorded separately, with the reviewer's agreed scope.

## Specific data-feasibility question

For a future authorized study, are paired laboratory glucose/C-peptide measurements available across the early **and later** phases of a standardized IV glucose test, with sample times, assay limits, renal function and exogenous-insulin timing? Could a participant- or study-disjoint subset be reserved before estimation? What use, storage, analysis and derived-output permissions would apply?

For CIT-07 specifically, the public protocol schedules post-transplant C-peptide through 10 minutes, while insulin/glucose continue to 180 minutes. Clarification of any additional late C-peptide measurements is more useful than assuming the catalogue contains a complete secretion-identification dataset. Sparse mixed-meal endpoints or the Miami oral-test substudy would need a separately specified analysis.

[BC-015-P1](m4-measurement-readiness.md) now supplies an unsent,
source-specific follow-up: “For the CIT-07/08 Version 2 release, do the FSIGT
glucose/insulin records link by participant, visit and actual collection time
to any early **and late** C-peptide records? If not, is there a separately
documented challenge series that does? Which versioned dictionaries specify
assay matrix, units, limits, precision, insulin cross-reactivity, renal/body
mass and exogenous-insulin timing? What access and derived-output terms apply,
and can a participant-disjoint assessment subset be reserved before model
selection?” This asks for feasibility metadata and scientific interpretation,
not a data transfer. No inquiry has been sent or answered.

The [BC-015-P2 public-dictionary crosswalk](m4-cit07-public-crosswalk.md)
sharpens the unsent questions: the released FSIGT Raw dictionary has no
C-peptide field; the separate C-peptide/glucose/creatinine dictionary has
fasting, 60- and 90-minute fields without an FSIGT sample clock; Rudbeck
sample labels have no documented FSIGT identity or glucose/insulin fields.
Does a separately released FSIGT C-peptide table exist, with an exact
challenge/visit identifier and actual sample times beyond 10 minutes? If not,
which *other* named challenge and population, if any, has paired dynamic
glucose, insulin and C-peptide suitable for a new protocol? Please also
clarify the dictionary's creatinine `ng/mL` label versus the protocol ratio's
`mg/dL`, per-test exogenous insulin timestamps, assay matrix/limits/precision
and permitted analysis/derived-output terms. This remains a draft; no inquiry
has been sent.

The [BC-015-P3 alternate-source screen](m4-alternative-observation-screen.md)
does not identify a substitute IVGTT packet in nearby CIT catalogue entries.
NCT01817959 publishes three-analyte **aggregate MMTT** summaries, not
participant-linked IV challenge observations; its final 120-minute visit
label and analyte denominators also need clarification before any separate
meal-series design. An unsent, narrow follow-up would ask the custodian
whether a versioned challenge-level IV release with late C-peptide and exact
sample/input times exists, or whether only a separate meal-series protocol is
feasible. It would also ask the permitted use and output terms. No source
contact or application has been made.

The [BC-015-P4 synthetic window stress](m4-sampling-window-results.md) uses a
known C-peptide appearance pulse and fixed exchange/volume to show why the
late decay portion may help distinguish pulse gain from removal. It is not an
analysis of the CIT-07 IVGTT or proof of a clinical schedule. A reviewer
should therefore answer two distinct questions: whether any permitted
same-challenge late samples exist and, if only the documented early window
exists, whether a narrower first-phase question with externally fixed
kinetics and explicit basal uncertainty would be biologically meaningful.

## Later cell-therapy question

The concrete BC-004 review packet follows below; this candidate therapy question remains separate.

A possible OT-027 question is whether change in measured graft secretory function predicts later external-insulin burden and glycemic outcomes after accounting for insulin sensitivity, graft site, immunosuppression and treatment practice. This is a candidate question, not a frozen protocol. A clinician and statistician should define the target population, observation windows, meaningful endpoints and independent assessment design before implementation.

The present reference supplies no graft survival, immune protection, engraftment or treatment-response mechanism. Changes in functional capacity cannot be translated into cell counts or therapeutic benefit without additional evidence.

## Paired boundary review packet

Prepared on 20 September 2026; **unsent, no external review performed**. Reviewable artifacts are the [paired protocol](m4-paired-protocol.md), [executable preflight/results](m4-paired-results.md), [measurement/source inventory](m4-cpeptide-measurements.md) and [C-peptide model card](models/polonsky1986-cpeptide.md). The numerical deliverable uses synthetic profiles and is distinct from biological approval.

| Review role | Concrete question | Evidence needed to close the question |
| --- | --- | --- |
| Secretion/kinetics modeller | Can equimolar instantaneous appearance and these fixed kinetic structures support the named population, and which scale/clearance combinations must remain fixed? | Written population/assumption scope, identifiability critique, references and corrections; reconcile BC-001 initialization/scale if used |
| Endocrinologist; transplant specialist for graft work | Which basal convention, challenge, renal conditions and delivery site make the question defensible? | Defined population and exclusions, route rationale and distinction between endogenous, graft and administered insulin |
| Laboratory/assay specialist | Can the actual sample matrices, assays and treatment history distinguish insulin/C-peptide concentrations with known limits and cross-reactivity? | Versioned assay metadata, units, LOD/LLOQ, precision, processing and batch rules |
| Statistician | Does the participant-level split, actual sampling and censoring/noise model support a held-out comparison? | Frozen allocation, analysis/uncertainty plan and evidence-based success criteria before evaluation |
| Data custodian, only if contact authorized | Does an existing permitted release contain the early/late paired measurements and metadata, and what reuse/output terms apply? | Actual dictionary and release coverage plus explicit access/use conditions; catalogue description alone is insufficient |

Suggested unsent inquiry: “Could you review this bounded paired insulin/C-peptide specification and advise whether existing data can support it? We particularly need to distinguish known-input kinetics from endogenous secretion, establish baseline/whole-body scale, and verify early and late paired samples with assay, renal and exogenous-insulin metadata. We are seeking a feasibility and methods review first; no collaboration or data access is assumed.”

For any eventual review record reviewer identity/discipline, date, exact protocol/code hashes, material inspected, population and claim scope, findings, conflicts and changes made. Leave those fields unassigned until review occurs. Software tests do not close these review items.

## Source reconciliation review packet

Prepared after [BC-006](m4-source-audit-results.md), 20 September 2026. **Unsent; external review not performed.** Attach the [protocol](m4-source-audit-protocol.md), [source locators/hashes](../../experiments/m4/source_audit/sources.json), [execution record](../../experiments/m4/source_audit/execution.json) and immutable commit identity when requesting review. The internal audit keeps literal BC-001 behavior unchanged.

| Priority and reviewer | Specific question | Resolution needed |
| --- | --- | --- |
| 1 — Original authors or secretion modeller | Which inventory and clock does X(0) represent: pre-bolus recruitment, finite-fusion transfer, or an active quasi-steady pool? The seed calculation gives 92.739536 micrograms; the printed denominator gives 0.149339 for the same seed. | Confirmed equations and initialization, correction reference if any, saved post-warmup state and stimulus; distinguish numerical resemblance from intended derivation |
| 2 — Original authors or secretion modeller | How should the delayed Y(0)=0 be reconciled with the post-bolus algebraic definition, and when may the omitted product-rule term be neglected? | Explicit approximation scope, timescale/error argument and whether a different model should be used |
| 3 — Authors and kinetic/assay specialist | Does the separate 0.5 C-peptide multiplier represent calibration, effective volume, secretion scaling or another convention? How was the separate basal value selected? | Parameter provenance, units and evidence; no automatic transfer to the BC-003 observation branch |
| 4 — Endocrinologist, transplant specialist where relevant | Which basal, mass-normalization, renal and delivery-route assumptions can be defended for one named T1D or graft population? | Population-specific applicability and exclusions; measurements required to separate scale from clearance |
| 5 — Authors/data custodian, after contact authorization | Is a permitted versioned glucose input, expected output, exact XPPAUT procedure and code license available? | Reproducible source package and explicit rights; no participant records needed for an initial methods clarification |

Suggested short inquiry: “We independently implemented the published reduced IVGTT equations and found an initialization discrepancy. Our source audit shows that recruitment from the pre-bolus pool at the code's docked seed predicts 92.7395 micrograms, close to the explicit 92.7, whereas the printed denominator gives 0.1493. We also distinguish the delayed Y state from its glucose-dependent algebraic definition, and note the separate basal term and C-peptide multiplier. Could you confirm the intended initialization/warmup procedure and model scope, explain the observation scale, and identify any corrected specification or permitted reference example? Our reproducible calculations are internal hypotheses; we have not changed the reference model or claimed clinical validity.”

Review record awaiting actual review:

- Reviewer identity, discipline, affiliation and conflicts: **unassigned**.
- Date, exact commit/protocol/source hashes inspected and review scope: **pending**.
- Each question: **unreviewed**; record confirmed, rejected or unresolved with reasoning and references.
- Required changes, responsible person and verification of their implementation: **pending findings**.
- Permission to attribute or publish the review: **not obtained**.

A filled internal test report does not fill these fields. A later supported model revision should receive its own version/protocol and preserve the literal reference and this audit. No outreach or access application has been made.
