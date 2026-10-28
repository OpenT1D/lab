# PhysioCGM source and intake assessment

**Updated: 20 September 2026. Status: metadata/code review and a separate
authorized private raw-CGM audit and bounded human conversion/reconstruction complete
under [PHYSIOCGM-CONVERSION/1.0](physiocgm-conversion-protocol.md).**
PhysioCGM is a plausible external CGM source for the
[frozen-model forecast route](m3-external-protocol.md). The initial public-source
review opened no patient files. Subsequent user authorization covered acquisition
of the ten raw archives and a local CGM-only format audit, without model evaluation.
Processed archives and other sensor contents were not inspected. Subsequent
authorization covers the proposed next step of controlled local conversion
under [Decision 0012](../decisions/0012-physiocgm-human-conversion.md). The
synthetic preparation route retains its own input boundary; human conversion
has a separate source-bound workflow. External human evaluation remains blocked.

## Confirmed release metadata

The [version-specific Figshare API](https://api.figshare.com/v2/articles/28136294/versions/1)
identifies **10.6084/m9.figshare.28136294.v1**, published and last modified on
20 November 2025 at 08:02:24 UTC. The
[version list](https://api.figshare.com/v2/articles/28136294/versions) contains
only v1; the [current record](https://api.figshare.com/v2/articles/28136294)
agrees. Metadata were retrieved without requesting file payloads.

| Metadata | Confirmed value |
| --- | --- |
| Dataset licence | CC0, linked to the official dedication |
| Access flags | Not embargoed; not confidential |
| Raw archives | 10 ZIPs; 9,166,404,038 bytes |
| Processed archives | 10 ZIPs; 15,869,666,465 bytes |
| Total | 20 ZIPs; 25,036,070,503 bytes |
| Integrity metadata | File IDs, sizes, download URLs and supplied/computed MD5 |
| Separate documentation files | None in the published file inventory |

There is no demonstrated institutional application requirement. File checksums
identify downloads; they do not establish correct labels, clocks or clinical
quality. The raw and processed archives represent the same ten participants,
not twenty independent people. Non-CGM contents and documentation reportedly
inside archives remain unverified. Use the [versioned DOI](https://doi.org/10.6084/m9.figshare.28136294.v1)
when recording provenance.

## Study evidence and remaining uncertainty

The [original publication](https://www.nature.com/articles/s41597-025-06090-6)
describes Baylor College of Medicine recruitment in 2021–2022, IRB H-49867,
and consent to release demographics and deidentified sensor data. Ten people
with T1D wore Dexcom G6, Zephyr Bioharness and Empatica E4 devices for up to
seventeen days. CGM cadence is described as five minutes. Pump use is reported;
this does not establish that insulin deliveries or meal logs were released.

Methods says ages 29–41, whereas
[Table 2](https://www.nature.com/articles/s41597-025-06090-6/tables/2) and
Limitations support 24–41. This discrepancy must remain visible. No individual
demographic rows are reproduced here. Reported recruitment criteria and
limited cohort size constrain population generalization.

The described study differs from
[AZT1D's Mayo Clinic Arizona/Arizona State University source](https://arxiv.org/abs/2506.14789).
That supports investigating external transfer; different institutions and
aliases are not proof of no participant overlap. Future reuse through an
aggregator must retain the original study identity.

For M3, this source could assess an unchanged predictor on a separate cohort.
Wearables could support later questions, but CGM forecasts alone cannot identify
insulin dynamics, validate a physiological engine or establish what another
controller would have caused.

## Initial code-informed expectations

Author code was inspected at commit
[`6940f1d587f8f68b131cf129d5a9f65237f61fcc`](https://github.com/PSI-TAMU/PhysioCGM/tree/6940f1d587f8f68b131cf129d5a9f65237f61fcc).
Its [CGM reader](https://github.com/PSI-TAMU/PhysioCGM/blob/6940f1d587f8f68b131cf129d5a9f65237f61fcc/libs/combine_data.py#L84-L102)
expects comma-separated fields named `Index`, `Event Type`,
`Timestamp (YYYY-MM-DDThh:mm:ss)` and `Glucose Value (mg/dL)`, selecting `EGV`
events. It parses naive timestamps, replaces `Low`/`High` with 40/400 and sorts
records. These informed the initial candidate; they do not verify censoring
semantics. The later audit's separate format evidence is described below.

The [preprocessor](https://github.com/PSI-TAMU/PhysioCGM/blob/6940f1d587f8f68b131cf129d5a9f65237f61fcc/preprocess.py#L83-L103)
matches ECG to the next CGM within 330 seconds, drops missing merged rows,
then [deduplicates by Index](https://github.com/PSI-TAMU/PhysioCGM/blob/6940f1d587f8f68b131cf129d5a9f65237f61fcc/preprocess.py#L129)
before pickle output. Processed records can therefore be selected by another
sensor's availability. They are unsuitable as an assumed complete CGM-only
comparison input. Native raw CGM is the proposed route.

The [README](https://github.com/PSI-TAMU/PhysioCGM/blob/6940f1d587f8f68b131cf129d5a9f65237f61fcc/README.md#L46-L77)
and publication describe different directory layouts; the README also calls
processed contents JSON while code writes pickle. The subsequent audit located
the raw CGM members; processed packaging remains unverified.
[Empatica conversion](https://github.com/PSI-TAMU/PhysioCGM/blob/6940f1d587f8f68b131cf129d5a9f65237f61fcc/libs/combine_data.py#L106-L161)
uses local-time conversion without an explicit timezone, warranting separate
multimodal synchronization review.

## Completed private CGM format audit

The authorized local audit verified the raw archive sizes and provider MD5s,
retained SHA-256 identities and found one `cgm.csv` in each archive. It read only
those original CGM members and checked their ZIP CRCs. Versioned metadata,
authorization, access history, original bytes, failed diagnostic attempts and
the final evidence inventory remain outside Git. The private evidence index is
`audit/format-check-03/evidence-manifest.json` within the authorized PhysioCGM v1
directory; `Bevindingen.md` beside it records the aggregate findings. This is
local audit evidence, not an independently reproduced public result.

The ordinary header has 14 named columns including the expected EGV/time/mg/dL
fields. One layout adds an unnamed column verified empty across every CSV record;
some EGV timestamps use `YYYY-MM-DD H:mm:ss`. The synthetic candidate now supports
these two exact forms under contract `physiocgm-cgm-candidate/0.2`. It retains
original source text and record lineage, checks the unnamed field even on
non-EGV events and fails on unexpected content. These are syntax corrections;
no values, timestamps, gaps or scientific conventions are repaired.

The audit also found timing jitter, gaps, conflicting duplicates and raw CGM
export spans exceeding the publication's stated multimodal collection duration.
Transmitter-counter decreases and identifier changes do not by themselves prove
sensor sessions or measurement-clock resets. The audit did not establish online
receipt times, export clock corrections or retrospective signal processing.
No model, scaler, forecasts or error scores were used. Data-opportunity counts
remain conditional on provisional assumptions, not evidence of predictive quality.

The format audit counts as prior access. The candidate's subsequent synthetic
tests do not establish actual human conversion, period eligibility or continuous
real-world clock/availability semantics.

## Completed bounded human conversion

On 20 September 2026, all ten source-bound raw CGM exports were converted under
PHYSIOCGM-CONVERSION/1.0. A separate private reconstruction reproduced the saved
observations, record lineage, declared intervals, status counts and complete
cohort from the retained native snapshots. The full repository check passed
259 tests, including 18 new invented-data tests for human conversion controls.
No human forecasts, model/scaler operations or predictive scores were performed.

The private acceptance record is `human-conversion-01-resultaat.md` in the
authorized release directory. `human-conversion-01-evidence.json` binds it to
the plan, conversion and reconstruction inventories. Patient records and
individual derived artifacts remain outside Git. A metadata-builder TypeError
occurred before plan creation or native reads; its original script is retained.
The actual conversion and reconstruction both completed on their first attempts.

This establishes faithful conversion of the bound files under the adopted
policy. It does not establish physical-time continuity, actual availability,
independent population membership or model accuracy. The separate external
human-evaluation gate remains closed.

## Rights by intended use

The dataset's CC0 dedication differs from the article's **CC BY-NC-ND 4.0**
[publication licence](https://www.nature.com/articles/s41597-025-06090-6).
The author repository has no identified software licence; its
[GitHub metadata](https://api.github.com/repos/PSI-TAMU/PhysioCGM) reports
`license: null`. OpenT1D's candidate parser is independently written; dataset
rights do not authorize copying upstream implementation.

The following assessment concerns copyright/database permissions described by
[CC0](https://creativecommons.org/publicdomain/zero/1.0/), not a blanket ruling
on every intended use.

| Intended use | Assessment |
| --- | --- |
| Local research and aggregate analyses | Supported by CC0; retain source attribution and provenance |
| Raw-record redistribution | CC0 supports copying; privacy and third-party rights still require assessment; no redistribution is authorized in this task |
| Individual derived results | No separate CC0 restriction, but identifiability and third-party rights remain unresolved |
| Trained models or parameters | No CC0 non-commercial or share-alike condition; assess whether an artifact reveals individual information |
| Independent open-source software | No requirement to apply the article licence to independently written code |
| Commercial research/product use | Not excluded by CC0; not evidence of clinical fitness or resolution of other applicable obligations |

No dataset-specific retention deadline or deletion duty was found in the reviewed
metadata. CC0 does not clear all third-party rights, privacy rights, patents or
trademarks. Its [legal text, sections 2–4](https://creativecommons.org/publicdomain/zero/1.0/legalcode.en)
defines the scope and limitations. Absence of an identified restriction is not
proof that all release contents are appropriate for public redistribution.

## Conservative candidate and acquisition status

The synthetic parser makes explicit provisional choices: preserve registered
EGV origins; retain missing/censored/conflicting observations; reject backward
EGV clocks; avoid interpolation, rounding and implicit timezone correction.
`Low`/`High` retain direction without an asserted numeric bound. Excluding
numeric values at or outside 40–400 mg/dL is conservative candidate policy,
not a verified statement that all such values are censored. Measurement-time
availability, a single naive clock segment and the administrative final endpoint
are assumptions requiring review. Prepared software is not native validation.

1. **Completed:** explicit user authorization for the ten raw archives and a
   local CGM-only format audit. No account, institutional affiliation or contact
   was needed. That authorization did not enable model evaluation.
2. **Completed:** private acquisition outside Git with versioned metadata,
   archive checksums and CGM-member integrity checks. No processed copies were
   acquired.
3. **Completed within scope:** locally recorded CGM format, clock-order,
   duplicate, censor-token and cadence diagnostics, without patient rows in
   reports or model scores. Availability, clock/session interpretation, endpoint
   meaning and study-period delimitation remain unresolved by that inspection.
4. **Adopted for conversion:** explicitly bound the period, clock, availability
   and value-policy assumptions in [PHYSIOCGM-CONVERSION/1.0](physiocgm-conversion-protocol.md)
   and authorize controlled local conversion of the complete ten-file roster.
   The private conversion plan must bind native identities and prior-access
   evidence before conversion reads; actual execution outcomes belong in its
   private acceptance record.
5. **Still required before scoring:** review the verified conversion-to-external
   bridge and freeze the actual cohort, unchanged model/scaler and comparison.
   Human conversion alone neither enables nor performs that evaluation.

## Proposed human-use boundary, not an evaluation freeze

The following table preserves the initial preparation proposal and its evidence
limits. Its conversion assumptions have since been adopted by
[PHYSIOCGM-CONVERSION/1.0](physiocgm-conversion-protocol.md) under
[Decision 0012](../decisions/0012-physiocgm-human-conversion.md). That protocol is
the current authority for controlled human conversion. The historical proposal
was not an executable cohort or authorization to score, and its adoption does
not create an external evaluation freeze.

| Topic | Proposed choice and reason | Evidence boundary |
| --- | --- | --- |
| Planned cohort | Retain all ten release participants, including any later conversion or eligibility failures | Different study provenance supports external investigation but does not prove absence of participant overlap with the donor |
| Period | Use the complete published raw CGM export per person, from first EGV through last EGV plus 300 seconds as a half-open administrative bound | Call it the CGM export period, not the multimodal study period; the added bound creates no readings or physiological duration evidence |
| Period selection | Do not crop an arbitrary seventeen days or select periods/people by opportunity counts, wearable availability or later scores | A verified study-period alternative would require separate evidence and an explicit amendment before scoring |
| Cadence | Preserve exact native times, including jitter; retain the existing six exact history points and exact 30-minute target | No rounding, tolerance or interpolation to improve coverage; observed timing can leave many origins unscored |
| Clock | Provisionally use one naive local segment; reject backward EGV time; infer neither timezone/DST correction nor segments from transmitter counters | This is conditional elapsed-clock analysis, not verified continuous physical time or sensor-session reconstruction |
| Availability | Treat measurement time as availability only as an explicit retrospective assumption | Supports forecasts conditional on immediate availability; does not establish real online availability, device execution or absence of retrospective processing |
| Value statuses | Keep `Low`/`High` directional without a numerical bound and preserve the existing exclusion of numeric endpoints 40/400 | A conservative analysis choice, not proof that numeric endpoints are censored; changing it requires a separately documented policy |
| Prior access | Disclose the complete format-audit and conditional opportunity-count history before freeze | Scores remain unseen, but the data are no longer untouched |
| Model and outcomes | Keep the frozen model/scaler, matching rules, cohort accounting and outcome definitions unchanged | No refitting, personalization or performance-driven period choice |

The full-export proposal avoids an unsupported crop and keeps the intended task
CGM-only. It does not resolve whether every exported day is comparable in device
settings, collection context or clock continuity. Those limitations must constrain
the eventual claim. If the available evidence cannot support the assumed clock
or availability even for a clearly labeled retrospective comparison, keep human
execution blocked or specify a narrower question explicitly.

The adopted conversion step binds private native identities, access history,
period and policy decisions to the complete roster, preserving all failed
attempts and keeping records and individual derived artifacts outside Git.
Binding verified conversion to a model freeze remains a later external-evaluation
step. Neither the format correction nor the conversion protocol alters
M3-EXTERNAL/0.1 or turns the private audit into a human evaluation.
