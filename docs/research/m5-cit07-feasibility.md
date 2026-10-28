# OT-027-P2 — CIT-07/08 public-source feasibility

**Reviewed 25 September 2026.** This is a metadata-only assessment of the
NIDDK Central Repository [CIT-07/08 Version 2 catalogue](https://test.repository.niddk.nih.gov/study/92),
identified by [DOI 10.58020/qx8b-gk69](https://doi.org/10.58020/qx8b-gk69),
and the publicly posted [CIT-07 protocol v8](https://test.repository.niddk.nih.gov/media/studies/cit-07/Protocol.pdf).
The production catalogue and some production document URLs returned HTTP 403
in this review; the official test-domain rendering and the previously
[source-hashed public dictionary audit](m4-cit07-public-crosswalk.md) supplied
the inspectable material. No participant dataset, access request, contact or
external review is involved. The review narrows the
[OT-027 question](m5-cell-therapy-protocol.md); it does not freeze an empirical
analysis or verify actual release coverage.

## Source and clock findings

The catalogue describes 48 adult transplant participants and labels the
Version 2 data as **available for request**. Its dataset descriptions name a
`Cpeptide Glucose Creatinine` table, daily `Insulin` records, seven-day
`Mean Insulin`, `Weight`, `Patient Status`, `Endpoints`, `Beta Score` and
other relevant tables. These are **catalogue record counts and descriptions**,
not eligible-person counts, joined observations or permission to use the
records. The public dictionary audit confirms subject/day field names in
some tables but not an exact cross-table challenge or infusion-event join.

The protocol schedules a metabolic assessment **75 ± 5 days after the first
and subsequent infusions** and **365 ± 14 days after the first and final
infusion**. Both include fasting/90-minute mixed-meal glucose and C-peptide
and insulin-requirement assessment. These are different from the provisional
day-90 function and days-270–365 continuous-burden windows in OT-027/0.1.
The protocol says participants record total daily insulin dose in
self-monitoring diaries; the catalogue describes `Mean Insulin` as an average
over seven consecutive days, not measured pump delivery or a 96-day mean.
The [protocol, §§4.1 and 9.1.2.1](https://test.repository.niddk.nih.gov/media/studies/cit-07/Protocol.pdf)
and [catalogue dataset descriptions](https://test.repository.niddk.nih.gov/study/92)
support these source-level facts. Actual visit dates and completeness are
unknown.

The protocol resets follow-up clocks after additional infusions and permits
a second infusion after the 75-day assessment and before eight months in
specified circumstances. Thus an early graft-function signal and a later
insulin outcome may straddle an additional treatment selected partly on
earlier function. A source-specific analysis must retain those events and
describe prediction **under observed subsequent care**. It cannot interpret
their association as the effect or persistence of the first graft. The
[protocol, §§7.4–7.5](https://test.repository.niddk.nih.gov/media/studies/cit-07/Protocol.pdf)
documents the scheduling and eligibility; release-level event coverage is
unverified.

The protocol's `Beta Score` includes insulin requirements, HbA1c, fasting
glucose and stimulated C-peptide. It is therefore **ineligible as the added
function predictor** when later insulin burden is the outcome: it mixes the
candidate function signal with insulin-use information. The proposed added
feature remains an assay-qualified fasting or 90-minute **observed**
C-peptide/glucose summary at the landmark, chosen before reserved assessment.
It is neither a secretion rate nor a transplant-effect estimate. See the
[protocol, §9.1.2.6](https://test.repository.niddk.nih.gov/media/studies/cit-07/Protocol.pdf).

## R1–R8 gate against the OT-027 contract

The [data contract](m5-cell-therapy-data.md) distinguishes a documented
field from actual same-person coverage. `Unresolved` means the public packet
does not prove the complete requirement, even where a subfact is supported.

| Requirement | Public-source evidence | Verdict before a native release |
| --- | --- | --- |
| R1 — identity and rights | Version 2 and DOI are named; participant data are available for request | **Unresolved:** no OT-027 grant or output terms |
| R2 — person, infusion and visit linkage | Some dictionaries have `ACCESSION` and transplant-day fields; catalogue lists `Patient Status` | **Unresolved:** actual first/final infusion and same-visit MMTT/insulin crosswalk are unverified |
| R3 — treatment and population | Adult islet-transplant setting, immunosuppression and repeat-infusion rules are in the protocol | **Unresolved:** per-person graft site, dose, infusions and concurrent care are unverified |
| R4 — function measure | Fasting/90-minute MMTT glucose and C-peptide are scheduled at 75 and 365 days; a public dictionary names sparse fields | **Unresolved:** actual same-challenge values, assay details and pre-outcome repeat coverage are unverified |
| R5 — external insulin burden | Daily diaries and seven-day mean insulin are described; dictionary labels units/day and weight | **Unresolved:** diary versus delivery semantics, complete seven-day windows, visit linkage and weight matching are unverified |
| R6 — glycemic outcomes | Protocol and catalogue name HbA1c, severe hypoglycemia and CGM summaries | **Unresolved:** actual eligible-person/window coverage and compatible definitions are unverified |
| R7 — kinetics and confounding | Weight, GFR and drug tables are named | **Unresolved:** time-aligned renal, drug and treatment context has not been verified |
| R8 — independent assessment | Catalogue gives 48 enrolled participants | **Unresolved:** eligible linked participants, independent allocation and effective precision are unknown; 48 is not an analysis sample size |

The stricter [M4 paired dynamic IV question](m4-measurement-readiness.md)
remains separate. CIT-07's core FSIGT C-peptide schedule ends at ten minutes,
and the public dictionary crosswalk does not establish a same-challenge
dynamic glucose/insulin/C-peptide series. A sparse **mixed-meal prognostic**
feature does not repair that IV kinetic gap or authorize reuse of the M4
IVGTT/feedback equations.

## Source-aligned candidate and decision

Retain a **narrowed prognostic feasibility question**: among CIT-07
participants with a verified first-infusion date, actual 75 ± 5-day MMTT
glucose/C-peptide assessment and later follow-up, does an observed
landmark function summary add prediction of the **seven-day diary-based mean
insulin amount in the 365 ± 14-day first-infusion visit** beyond a simpler
landmark-only baseline? If the release supports a contemporaneous weight,
the candidate outcome is units/kg/day; otherwise report units/day and do
not invent a weight. Exact visit matching, eligible-person counts, function
summary, baseline inputs, missingness, repeat-infusion policy and performance
criteria remain for a new empirical freeze.

This is a **source-aligned candidate**, not a committed CIT-07 analysis. The
first-infusion clock avoids selecting a retrospectively known final infusion
as the index. Subsequent infusions must be reported as intervening treatment
and considered in the prespecified analysis; excluding them after seeing
outcomes would bias the question. A day-365 function measure cannot be used
to predict a day-365 burden outcome. Functional persistence needs an earlier
repeat before a still-later outcome and a separate verified design.

The [synthetic visit-linkage preflight](../m5-release-preflight.md) can now
rehearse the proposed join and window rules. Its invented counts do not
alter any R1–R8 verdict for CIT-07.

**Verdict:** the public packet supports a more concrete question and a
specific list of fields to verify. It does **not** pass R1–R8 or permit
participant-level fitting. The next executable gate is an authorized
release-level variable/visit/infusion crosswalk, followed by independent
transplant, assay and statistical review. If those fail, narrow the question
or select another source before writing a frozen study protocol. No
transplant model, therapy benefit or cure conclusion follows from this
metadata screen.

The subsequent [public-dictionary crosswalk](m5-cit07-dictionary-crosswalk.md)
documents relative repeat-infusion fields and a crucial clock distinction:
`Mean_Insulin.NumDaysInitial` denotes the start of its seven-day calculation
interval, whereas the MMTT table uses that name for days since the first
transplant. It still cannot verify an actual same-visit join.
The later [form and laboratory audit](m5-cit07-form-lab-audit.md) distinguishes
visit 15 from first-infusion Y1 and identifies conditional day-75 MMTT
collection. Those findings refine the release-stage join and missingness
questions without changing this metadata verdict.
