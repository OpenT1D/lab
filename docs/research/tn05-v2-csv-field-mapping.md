# TN05 v2 CSV field mapping for paired MMTTs

**Public metadata audit · 22 November 2026.** The
[OT-067/068 decision](ot067-068-mmtt-data-decision.md) selects the screening
and 12-month four-hour mixed-meal tolerance tests (MMTTs) as the candidate route
for a paired 0–120-minute secretion analysis in adults assigned to placebo.
The trial manual identifies where actual draw times were to be recorded.
Their presence and linkage in the TN05 v2 CSV release are unconfirmed.
Participant-level joins, result units and censoring are also unconfirmed.
The converter remains deferred.

## Release evidence

NIDDK-CR lists TN05 Version 2, DOI `10.58020/1bv7-0y43`, under controlled
access. We inspected the production catalogue's CSV column metadata for all
31 listed tables and the inventory of 35 public documents. Research Labs has
the same 12 columns in the same order as the public SAS dictionary, p. 67.
The dictionary documents SAS types and display formats. CSV filenames,
encoding, delimiters, date rendering, raw tokens and row grain still need
release-specific evidence. The audit used public documentation and metadata.
[Production catalogue](https://repository.niddk.nih.gov/study/76),
[DataCite release metadata](https://api.datacite.org/dois/10.58020/1bv7-0y43),
[TN05 data dictionary](https://repository.niddk.nih.gov/public/study_document/TN05_V2/TN-05%20Documentation/TN05_Data%20Dictionary.pdf)

| Research Labs columns in catalogue order | Documented role | Proposed use |
| --- | --- | --- |
| `event_title`, `MaskID` | Specimen collection form label and masked participant identifier | Retain both. Confirm the exact MMTT form labels and the scope of the masked participant key. |
| `SPEC_NAME`, `SampleMaskID`, `TEST_NAME` | Specimen label, character masked sample identifier and laboratory test label | Use the specimen and test labels together for challenge type, analyte and nominal minute. Preserve `SampleMaskID` as text and verify its grain and linkage. |
| `RESULT`, `OUTCOME` | Character result and outcome fields | Retain both original tokens. Parse a value, unit and status only under a documented, analyte-specific rule. |
| `Visit`, `Date_of_Draw` | Visit label and SAS calendar date (`MMDDYY10.`) | Use as visit and specimen-date evidence. Confirm visit aliases, date serialization and alignment across files. |
| `Date_at_Test_Results_Reported`, `Date_Received`, `Date_Shipped` | SAS calendar dates for lab reporting, receipt and shipment | Preserve separately from the collection date and meal-relative clock. |

## Participant, visit and specimen links

The 2007 draft Manual of Operations places four-hour tests at screening,
month 12 and month 24. Screening MMTT and the week-0 randomization visit are
distinct events. The manual lists Week 52 as Month 12 and gives different
visit windows according to the associated procedures. The participant-specific
schedule in the manual uses the randomization date for follow-up targets.
The trial article describes its one-year outcome relative to the first infusion.
Preserve both dates and verify the applicable scheduling anchor and window for
the released test. The pretreatment MMTT supplies the candidate analytic baseline.
The historical data integrity check (DSIC) selects `Screening` and `52 weeks`
among the visits it processes for `PEP120`. That selection supports the
candidate labels. Coverage of the full paired series and its linkage remain
unverified.
[Manual of Operations, §§7.2.5, 12.3 and 14.3 and Appendix G](https://repository.niddk.nih.gov/public/study_document/TN05_V2/TN-05%20Documentation/TN05_Manual_of_Operations.pdf),
[TN05 trial article](https://pmc.ncbi.nlm.nih.gov/articles/PMC6410357/),
[DSIC, Appendix 1, pp. 17–18](https://repository.niddk.nih.gov/public/study_document/TN05_V2/TN-05%20DSIC/DSIC_TrialNet-05%20Rituximab_final.pdf)

| Link or context | Verified public metadata | Needed to admit a pair |
| --- | --- | --- |
| Participant and assigned arm | Participant Registration and Participant Treatment Table expose `MaskID`. Treatment Table includes `TreatmentName`, `RegistrationGroup`, `Randomization_Date`, `Treatment_Start_Date` and `SequenceNumber`. The DSIC uses `TreatmentName` on rows with a randomization date and presents placebo and rituximab groups. | Confirm one masked person across the required tables and a documented rule that identifies one randomized assignment per person. Retain repeat treatment rows and exclusions until resolved. Confirm the assigned arm independently of received treatments. |
| Analytic baseline | Screening Form RIT01 exposes `MaskID`, `Visit`, `Date_of_Visit`, `Date_At_MMTT`, `Age` and `sex`. The form has a field for the four-hour collection date. The public RIT06 form records age and randomization date at week 0. Its CSV export was not identified. | Link the qualifying pretreatment test to its screening record and assignment. Establish age at the selected baseline, especially near the adult cutoff. Treat clinic, test and randomization dates as separate fields. |
| Month 12 and missing visits | RIT12 labels a Month 12 visit and exposes `MaskID`, `Visit`, `Date_of_Visit`, `_4HourMMTT` and `Date_At_4HrMMTT`. The RIT16 dictionary labels `VistMissed` as the missed visit and `ReasonForMissedVisit` as the reason. | Confirm the completed and missed visit code mappings and one qualifying four-hour test per intended visit. Use the dedicated missed-visit field after decoding it. Reconcile reschedules, conflicting dates and absent visits. |
| Challenge and specimen | The manual specifies four-hour form `RIT99M4` and a separate `MMT4` barcode block per test. The block's labels associate the transmittal form and its timed specimen tubes. Research Labs exposes `event_title`, `SPEC_NAME`, `TEST_NAME`, `SampleMaskID`, `MaskID`, `Visit` and `Date_of_Draw`. | Verify how the form event and barcode block were carried through masking. Establish a unique test instance and a traceable link from each analyte result to its specimen and timed draw. A participant/date or label alone cannot separate repeated tests. Distinct glucose and C-peptide tubes may have distinct masked specimen identifiers. |
| Eligibility and visit context | RIT02 lists `Date_At_T1DDiag`. RIT03 and RIT12 document body size (`WeightInKgs`/`HeightInCm` and `WeightKG`/`HeightCM`). RIT09/RIT10 cover insulin or medications and RIT21 covers deviations. The lab workbook labels `CREA` as creatinine in the chemistry panel. | Link dated renal measures and units, body size and relevant medication, fasting, meal dose/completion and deviation records to each test. Validate timing relative to the challenge before use. |

The DSIC's historical treatment-table filter and joins are evidence of how its
authors explored the release. For example, its screening join on `MaskID`
allows many-to-many records. The future mapping must check cardinality at each
link and retain orphaned, repeated and conflicting records for review.
The DSIC supplies no count of eligible complete adult placebo pairs.
[TN05 dictionary, especially pp. 40–41, 44, 66–69 and 74](https://repository.niddk.nih.gov/public/study_document/TN05_V2/TN-05%20Documentation/TN05_Data%20Dictionary.pdf),
[RIT01 screening form](https://repository.niddk.nih.gov/public/study_document/TN05_V2/TN-05%20Forms/RIT01%20-%20Screening031506.pdf),
[RIT06 randomization form](https://repository.niddk.nih.gov/public/study_document/TN05_V2/TN-05%20Forms/RIT06%20-%20Rand031506.pdf),
[RIT12 follow-up form](https://repository.niddk.nih.gov/public/study_document/TN05_V2/TN-05%20Forms/RIT12%20-%20FollowUp090506NEW.pdf),
[DSIC, Appendix 1](https://repository.niddk.nih.gov/public/study_document/TN05_V2/TN-05%20DSIC/DSIC_TrialNet-05%20Rituximab_final.pdf)

After aligning `MaskID` and the visit labels, compare Research Labs
`Date_of_Draw` with RIT01 `Date_At_MMTT` for screening and RIT12
`Date_At_4HrMMTT` for month 12. Date agreement corroborates the proposed
link. Multiple matches or conflicting dates require adjudication against
the test and specimen identifiers.

Retain each source result with its source row reference, participant, ordered
visit, challenge instance, specimen/result identity, analyte, nominal slot,
actual minutes, value, unit and status. Form a paired-analyte observation only
after both tubes are linked to the same timed draw. Preserve analyte-specific
clocks where supplied and resolve discordances under an explicit timing rule.
Keep the intended visits and expected sampling slots in coverage even when
one or both analytes are absent. A single linked result retains its value and
clock. Record absent results, unsuccessful linkage and censoring separately,
with unknown draw times left unset.

## Nominal schedule and measured time

The shared TN01/TN02/TN05 lab workbook pairs four-hour MMTT specimen labels for
glucose and C-peptide with `GLU<n>` and `PEP<n>`, where `<n>` is one of
−10, 0, 15, 30, 60, 90, 120, 150, 180, 210 or 240. For example, `PEP120`
also occurs for two-hour MMTT and OGTT specimens, and plain `GLU` occurs in
chemistries. Require a consistent four-hour specimen label and analyte code
and an independently resolved test instance. Keep the −10 sample as fasting
context and observations after 120 outside the selected analysis window.
[Lab label workbook](https://repository.niddk.nih.gov/public/study_document/TN05_V2/TN-05%20Documentation/TrialNet%20Lab%20Value%20Labels-TN01_TN02_TN05%2020120202.xlsx)

Appendix G of the manual calls the draw just before drinking the nominal
zero sample, starts the study clock at the beginning of the drink and directs
staff to record each draw's actual start time on the transmittal form. Form
comments were intended to capture missed draws and procedural deviations.
The catalogue has no standalone RIT99M4 document or named RIT99M4 dataset.
The Research Labs, RIT01 and RIT12 schemas expose dates for
collections or visits. The public metadata reviewed supplies no field or
crosswalk for actual draw times, a recorded meal-start anchor or a documented
elapsed-time value in the CSV. A form requirement is evidence of intended
collection. Filled form values, field precision and release coverage remain
unknown.
[Manual of Operations, Appendix G, printed pp. 19–23](https://repository.niddk.nih.gov/public/study_document/TN05_V2/TN-05%20Documentation/TN05_Manual_of_Operations.pdf#page=227),
[production catalogue](https://repository.niddk.nih.gov/study/76)

To derive actual minutes, obtain either documented elapsed times with their
anchor or link the recorded meal-start and draw clocks for the same test.
Preserve clock precision, nominal slot, actual time and deviations
independently for each result. An analyst must justify any boundary rule for
the empirical study, including the pre-drink draw. A future synthetic
rehearsal through the current importer requires measured 0 and 120 minutes.
A specimen label or date cannot supply elapsed minutes or justify rounding or
extrapolating a missing endpoint.
[Current observation contract](../observation-analysis.md#local-observation-contract)

## Units, assay and censoring

| Item | Verified public evidence | Release-level decision pending |
| --- | --- | --- |
| C-peptide unit | The trial reports the 0–120-minute time-averaged C-peptide concentration (AUC divided by duration) in pmol/mL. The dictionary defines `RESULT` as text and the lab workbook has no unit column. | Confirm the raw `PEP` result unit by assay and era. With a documented molar unit, 1 pmol/mL equals 1 nmol/L and 1,000 pmol/L. The synthetic CSV contract uses nmol/L and the estimator uses pmol/L. |
| Glucose unit | The manual uses mg/dL for the home-meter screening criterion. The label workbook identifies timed `GLU` samples by analyte and nominal slot. | Establish the laboratory `GLU` unit separately from meter values and diabetes management summaries. Map to mmol/L only after confirming the unit and a versioned conversion. |
| Specimen and assay | The manual's collection section specifies plasma for both analytes, with EDTA for C-peptide. Appendix G's preparation text says serum, and the primary article describes serum C-peptide. | Reconcile matrix wording against lab method documentation linked to the delivered records. Establish platform, batch or era, calibration, limits and precision. |
| Non-measurable C-peptide | Lachin et al. describe replacing non-measurable timed results with the assay LOQ before computing AUC in a pooled analysis including TN05 controls. The DSIC converts selected `RESULT` strings to numbers for its tabulation. | Obtain the permitted raw `RESULT`/`OUTCOME` value vocabulary, the applicable detection and quantification limits, and evidence of whether substitutions were already applied in the CSV. The trial's eligibility threshold is a separate quantity. |

Keep observed numbers, below-limit results with their applicable bound, samples
missed or unsuitable, blanks of unknown meaning and source-substituted values
distinct. A number matching a limit can be a measured value or a substitution.
Evidence for the source encoding is required to classify it. Carry the
original token, status reason, original unit and conversion identity. Reject
unknown scales and ambiguous censoring from estimation and retain them in
coverage. The published AUC and DSIC tabulation are separate from the row-level
encoding and the modeled secretion endpoint.
[TN05 trial article, Methods](https://pmc.ncbi.nlm.nih.gov/articles/PMC6410357/),
[Lachin et al., Methods and Procedures](https://pmc.ncbi.nlm.nih.gov/articles/PMC3213096/),
[Manual of Operations, §21 and Appendix G](https://repository.niddk.nih.gov/public/study_document/TN05_V2/TN-05%20Documentation/TN05_Manual_of_Operations.pdf),
[DSIC, pp. 7 and 17–18](https://repository.niddk.nih.gov/public/study_document/TN05_V2/TN-05%20DSIC/DSIC_TrialNet-05%20Rituximab_final.pdf)

## Evidence needed before implementation

1. An authoritative, versioned CSV schema or permitted metadata-only example
   with the physical file format and participant, visit, assignment,
   challenge, specimen and result keys. Include the RIT99M4 or equivalent
   clock fields and their link, precision and meal-start semantics.
2. A release-specific lab mapping for `PEP` and `GLU` values and units, matrix
   and assay, and the complete status and limit vocabulary, including any
   numeric substitution, missing sample and replicate rules.
3. Once that metadata supports the mapping, a publishable invented example
   with independently expected rows and outcomes for one clean pair.
   Preserve unresolved and rejected rows and test duplicate, mismatched
   challenge, missing endpoint, censoring, wrong-scale and reordered-export
   cases. Usable-pair counts require an authorized audit in an approved
   environment.

The timing fields are the first unresolved dependency. If the format supplies
only nominal labels, the selected actual-time route stays ineligible. Project
access, scientific review and independent user acceptance retain the separate
gates in the [paired-study decision](ot067-068-mmtt-data-decision.md#reuse-and-next-step).
