# OT-027-P5 — CIT-07 public form and laboratory audit

**Reviewed 25 September 2026.** This is a document-level check of the
candidate day-75 function measure and one-year insulin-burden window in
[OT-027/0.2](m5-cell-therapy-protocol.md). The official
[CIT-07/08 Version 2 catalogue](https://repository.niddk.nih.gov/study/92)
lists the documents below and marks participant data available for request.
The cited public PDFs were read in a browser; no local source-byte hash is
claimed by this audit. Page numbers refer to the PDF viewer. No participant
tables, access grant or reviewer response were inspected.

| Public source | Pages used | What it can establish |
| --- | --- | --- |
| [CIT-07 protocol v8, 20 August 2012](https://repository.niddk.nih.gov/public/study_document/Documentation/CIT-07_Protocol_Version_8.0_20Aug12.pdf) | 19, 79–81 | Study definitions, diary reporting and MMTT method |
| [CIT-07 forms grid v8, 5 November 2012](https://repository.niddk.nih.gov/public/study_document/Documentation/CIT-07_Forms_Grid_V8.pdf) | 1 | Separate scheduled visit 15 and Y1 clocks |
| [CIT-07 annotated clinical forms](https://repository.niddk.nih.gov/public/study_document/Documentation/CIT-07_ClinicalCRFsAnnotated.pdf) | 1, 17 | Dated daily insulin entry and generic C-peptide form fields |
| [CIT-07 study-specific laboratory manual v8, 25 April 2013](https://repository.niddk.nih.gov/public/study_document/Documentation/CIT-07_SpecificLabManualv8.0.pdf) | 4, 6, 8, 10 | Central MMTT schedule, conditional 60-minute sample and specimen handling |

The catalogue description for the forms grid refers to CIT-01, but the
opened PDF itself is headed **CIT07** and labels version 8.0. This audit uses
the document's internal study identity; the catalogue description is not
evidence that CIT-01 visit rules apply here.

## Source findings and consequences

| Finding | Direct document evidence | OT-027 consequence |
| --- | --- | --- |
| Day-75 function visit | The forms grid labels visit 10 as day 75 ± 5 relative to transplant. The laboratory manual lists fasting serum glucose/C-peptide and an MMTT at visit 10. Its specimen schedule calls the fasting sample MMTT time zero and includes a 90-minute stimulated sample. | The proposed day-75 **observed MMTT** summary has a named scheduled source. The actual C-peptide table row still needs a verified visit/challenge mapping and complete same-person glucose values. |
| Conditional samples and selection | The manual says the 60-minute MMTT tube is used when graft failure is suspected; ordinarily only the 90-minute tube is filled. It also says not to collect the day-75 samples marked with a dagger for confirmed graft failure. | Do not require a 60-minute value for routine eligibility. Distinguish protocol-directed absence after confirmed graft failure from a missing or censored assay; a complete-case day-75 set may select on early outcome. |
| Two 365-day clocks | The forms grid and laboratory manual list **visit 15** at day 365 after a transplant and **Y1** at day 365 after the *initial* transplant as separate scheduled visits. Both have MMTT-related laboratory kits. | Keep the candidate outcome anchored to Y1. A numerical day near 365 or `EndDay` alone cannot prove a row is Y1; do not silently substitute visit 15 after a later infusion. |
| Daily insulin provenance | Protocol §9.1.2.1 says participants record total daily insulin dose in self-monitoring diaries. The annotated blood-sugar/insulin form (p. 1) has a date, total insulin administered in units and separate controls for unavailable dose or a date with no readings. | Interpret the source as *recorded administered insulin*, not direct pump-delivery telemetry. Zero reported dose and unavailable dose must remain distinct; verify how the released `Insulin` table represents the form's missingness controls. |
| Seven-day window | The protocol's insulin-independence definition (p. 19) requires seven consecutive days of blood-sugar and insulin readings in a specified range around a visit window. The catalogue calls `Mean Insulin` a seven-consecutive-day mean; the [dictionary](m5-cit07-dictionary-crosswalk.md) labels `NumDaysInitial` as interval start and `EndDay` as interval end. | The clinical independence rule does not prove the exact construction or visit assignment of every released mean-insulin row. Verify seven distinct daily records, interval arithmetic and the Y1 visit association in an authorized release. Do not assume the interval is exactly the seven days immediately before Y1. |
| Assay and treatment context | The laboratory manual assigns central serum glucose/C-peptide measurement to the University of Washington. Protocol §9.1.2.5 permits a pump basal rate during the MMTT and describes test-day insulin restrictions; the manual names specimen tubes and shipment conditions. | The source documents identify a standardized challenge and collection route, but not each released row's assay version, limits, below-limit coding, adherence, kidney status or exact exogenous insulin history. Keep those R4/R7 checks open. |

The annotated **core** C-peptide form on p. 17 describes dated fasting and
postprandial entries and selectable units. It does not by itself identify the
specific 90-minute MMTT row in the archived
`Cpeptide_Glucose_Creatinine` table. The study-specific protocol and laboratory
manual support the *planned measurement*; the record-level mapping remains
unverified. Likewise, the forms grid is a collection schedule, not a count
of completed visits.

## Updated release and review questions

1. Which released visit indicator or event key distinguishes visit 10,
   visit 15 and Y1, particularly when a second or third infusion creates
   overlapping day counts? Decode `pstintvst`, `pstfinvst` and `Flag08` before
   selecting rows; do not infer their values from their names.
2. Do the fasting and 90-minute fields in each candidate C-peptide row come
   from the same MMTT, and is absence at visit 10 due to confirmed graft
   failure, noncollection, assay censoring or another reason? What are the
   assay units, matrix, limits and processing rules in the released tables?
3. Which source fields preserve the form's unavailable-insulin and no-record
   states? For each candidate Y1 mean, do seven dated daily entries reproduce
   the summary and weight normalization, and what visit rule selected that
   interval?
4. Can the analysis report repeat infusions and changes in care between the
   day-75 landmark and Y1 without selecting on later treatment or outcomes?

These questions refine [R2, R4, R5 and R7](m5-cell-therapy-data.md) and the
[scientific review packet](m5-domain-review-brief.md). The
[native-shaped rehearsal](../m5-native-rehearsal.md) exercises five invented
tables but has no verified visit-10/visit-15/Y1 code map. Its structural
success cannot close these questions.

**Decision:** retain the first-infusion Y1 prognosis candidate, with a
protocol-directed day-75 missingness category and explicit visit-clock
verification. The public documents strengthen the collection rationale but
do not establish an eligible linked cohort, justify complete-case exclusion,
freeze a predictor or outcome, or support a treatment-effect claim.
