# OT-027-P4 — Scientific review packet for the islet-function question

**Prepared 25 September 2026; unsent and unreviewed.** This packet requests a
bounded methods review of [OT-027/0.2](m5-cell-therapy-protocol.md). It is not
an empirical protocol freeze, a data-access application, a clinical
recommendation or evidence that an islet intervention caused reduced insulin
use. No reviewer has been assigned or contacted.

## Decision to be reviewed

The candidate comparison asks whether an observed post-infusion
C-peptide/glucose measure improves prediction of *later documented external
insulin burden* over a simpler, landmark-available baseline in a named
recipient population. The provisional first-infusion clock places a function
assessment at day 75 ± 5 and a seven-day diary insulin summary at the
day 365 ± 14 first-infusion visit. These are **scheduled source windows**,
not verified participant observations. A repeat infusion may occur between
them. The model comparison would be prognostic under observed subsequent
care, not a treatment-effect or cure analysis.

The [NIDDK CIT-07/08 Version 2 catalogue](https://test.repository.niddk.nih.gov/study/92)
marks the data package available for request and describes up to three islet
infusions; it does not establish a linked analysis cohort. The
[public-dictionary crosswalk](m5-cit07-dictionary-crosswalk.md) verifies that
`Mean_Insulin.NumDaysInitial` denotes the *start* of its seven-day interval,
while similarly named fields in the C-peptide and daily-insulin tables refer
to days since first transplant. The interval start cannot serve as an outcome
visit identifier. The [data requirements](m5-cell-therapy-data.md) label the
release-level checks R1–R8. A [source-shaped rehearsal](../m5-native-rehearsal.md)
tests only invented rows and supplies no cohort evidence.

## Material for a reviewer

| Item | Purpose | Current evidence limit |
| --- | --- | --- |
| [OT-027/0.2 protocol](m5-cell-therapy-protocol.md) | Question, provisional windows, simple comparator and claim boundary | No empirical variable/model freeze |
| [CIT-07 public-source assessment](m5-cit07-feasibility.md) | Protocol schedule, repeat-infusion and beta-score issues | Scheduled visits do not prove record coverage |
| [Five-dictionary crosswalk](m5-cit07-dictionary-crosswalk.md) and its [hash manifest](../../experiments/m5/source_crosswalk/public-dictionaries.json) | Native field labels and source identities | Challenge identity, visit linkage and diary completeness unverified |
| [Data requirements](m5-cell-therapy-data.md) | R1–R8 evidence gates | Record-stage fields and rights unverified |
| [Synthetic preflight](../m5-release-preflight.md) and [native-shaped rehearsal](../m5-native-rehearsal.md) | Software handling of invented missing and repeat-event cases | No human data or biological assessment |

The source review can resolve the *scientific design* provisionally now.
Final eligibility, assay interpretation, endpoint construction and split
feasibility require an authorized, versioned release and its permitted
documentation. Reviewers should identify changes to the proposed question
before records or reserved outcomes are examined.

## Questions and required disposition

For every ID, record **accept**, **revise**, **reject** or **unresolved**, a
reason, the evidence inspected and the effect on the proposed claim. An
unresolved item is not tacit acceptance.

| ID / reviewer | Concrete decision question | Evidence needed for final disposition |
| --- | --- | --- |
| T1 — T1D/transplant clinician | Is first infusion the appropriate origin for the *prognostic* question when second or third infusions can precede or follow the day-75 assessment? Which recipient/product/site or CIT-07/CIT-08 groups must be separated? | Explicit target population, index and repeat-infusion handling tied to verified treatment histories (R2, R3) |
| T2 — T1D/transplant clinician | Does a seven-day reported insulin amount at the one-year visit represent a useful burden outcome under changes in insulin prescribing, adherence, immunosuppression and follow-up care? Which care changes must be reported? | Defined outcome interpretation, clinical exclusions or strata and care-context requirements (R3, R5, R7) |
| A1 — challenge/assay specialist | Do the actual fasting and 90-minute C-peptide/glucose fields belong to the same named mixed-meal challenge and visit? Can protocol-directed day-75 noncollection after confirmed graft failure be distinguished from assay missingness? Are matrix, units, assay version, lower limits and concurrent glucose adequate for one observed-response summary? | Challenge-level linkage and assay documentation for the permitted release (R2, R4); see the [public form/lab audit](m5-cit07-form-lab-audit.md) |
| K1 — secretion/kinetics specialist | Can that *observed* response be called post-graft function in this population, given residual native secretion, renal clearance, graft site and exogenous treatment? If an M4-derived feature is proposed later, what independent kinetic information is indispensable? | A scoped interpretation and explicit assumptions; no conversion of concentration to graft mass or secretion rate by label alone (R3, R4, R7) |
| S1 — statistician | How is first-infusion Y1 distinguished from visit 15 after a later infusion, independently of `Mean_Insulin.NumDaysInitial`? What validates seven distinct consecutive daily entries, `EndDay`, the reported mean and contemporaneous weight? | Release-level visit-code join and arithmetic audit, duplicate/missing rules and denominator accounting (R2, R5) |
| S2 — statistician with clinician | What is the primary estimand when an additional infusion or care change occurs after the landmark? Is a descriptive repeat-infusion stratum feasible, and what claims remain if it is not? | Prespecified intervening-event rule and interpretation under observed care (R2, R3, R7) |
| S3 — statistician | Is a person-disjoint reserved assessment possible after verified eligibility and missingness? What is the exact simple comparator, added feature, metric, uncertainty method, minimum useful gain and acceptable harm? | Source-specific allocation and complete empirical freeze **before** fitting or reserved scoring (R8) |
| S4 — statistician | How will missing challenge values, incomplete diaries, loss to follow-up and a simultaneous day-365 function measure be handled without outcome leakage or complete-case overclaiming? | Prespecified missingness/censoring and temporal-information rules with all planned cases accounted for (R2, R4, R5, R8) |

The NIDDK catalogue's participant total is a study inventory, not an eligible
paired count or proof that a held-out split is feasible. Do not infer
predictive performance or select a numerical success threshold from the
invented rehearsal.

## Gate decisions

1. **Rights and source (R1):** do not inspect a request-only participant
   package until its version and use, storage and output terms are verified.
2. **Structural feasibility (R2, R4, R5):** if the release cannot identify
   a pre-outcome function challenge and a defensible later insulin interval
   for the same person, stop this comparison or publish a separately scoped
   replacement protocol. Do not substitute the mean interval start for a
   visit date or fill missing diary days with zero.
3. **Clinical interpretation (R3, R7):** preserve every repeat infusion and
   relevant care change. If their timing or population context is too
   ambiguous, narrow the claim; no first-graft persistence or causal
   transplant claim follows from a prognostic association.
4. **Assessment (R8):** if eligible people cannot support a participant-
   disjoint reserved evaluation, report development-only feasibility. Do
   not present resubstitution or visit-wise splitting as independent evidence.
5. **Freeze:** require all applicable reviewers' written dispositions,
   resolved changes and a source-specific empirical protocol before fitting.
   A conceptual review completed before data access remains provisional
   until the record-stage evidence is checked.

## Review record to complete after actual review

Copy this block for each reviewer. Keep the original packet and later
responses versioned; do not replace unresolved answers with assumptions.

```text
Reviewer name / discipline / affiliation:
Relevant experience and conflicts:
Date and agreed scope:
Protocol revision and repository commit inspected:
Source documents, versions and hashes inspected:
Authorized release identity, if any; permitted inspection scope:
Question IDs and disposition (accept / revise / reject / unresolved):
Reasons, references and exact required changes:
Claim and population limits after review:
Follow-up owner and evidence needed to close unresolved items:
Permission to attribute or publish this review:
```

**Current record:** all reviewer identities, question dispositions,
release-stage evidence and attribution permissions are pending. No outreach,
data transfer, cohort construction, model fit or independent assessment has
occurred through this packet.
