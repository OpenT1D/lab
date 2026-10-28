# M3-PHYSIOCGM-EXTERNAL/0.1 — Human external forecast freeze

Accepted 20 September 2026 under
[Decision 0013](../decisions/0013-physiocgm-external-freeze.md).
**Current scope: connect a verified private human conversion to an unchanged
donor model and freeze the external assessment before scoring. No human
prediction or evaluation is enabled.** The preparation schema is
`opent1d.physiocgm.external-freeze/1`.

## Question and authorization boundary

The intended assessment asks whether the existing AZT1D-trained shared Ridge
predictor improves 30-minute CGM forecasts over persistence in the separate
PhysioCGM study, without refitting. This is a study-level external comparison
under observed treatment. The reviewed study descriptions support a source
contrast; they do not verify the absence of participant overlap. Do not label the
cohort biologically independent on the strength of aliases or file hashes.

The user authorized the next step after the completed human conversion:
connect its controlled input to the unchanged predictor and freeze the external
evaluation before calculating scores. This step may verify conversion, inspect
saved model metadata and parameters, and bind the complete cohort and analysis
rules. It does not authorize prediction, scoring, new acquisition, access to the
AZT1D reserve, publication of records or further model development.

The previous format audit, data-opportunity inspection, conversion and
reconstruction are prior access. Preserve them in the freeze disclosure.
Assessment scores remain unseen in this step; the observations themselves are
already inspected material. Neither a fresh directory nor a new protocol
restores an untouched dataset.

## Source, complete cohort and conversion

Use the ten full original raw CGM exports pinned to
[10.6084/m9.figshare.28136294.v1](https://doi.org/10.6084/m9.figshare.28136294.v1)
and their completed [PHYSIOCGM-CONVERSION/1.0](physiocgm-conversion-protocol.md)
bundle. The [source assessment](physiocgm-source-assessment.md) retains the
release, rights review, prior access and semantic limitations. No processed
archive, other sensor channel or participant subgroup enters this freeze.

Require the saved human conversion and its separately completed reconstruction
under PHYSIOCGM-CONVERSION/1.0. Check their bound plans, manifests, complete
statuses and matching reconstruction evidence before binding inputs. This
step checks the retained evidence; it does not rerun native conversion or
reopen native CGM files. A failed, tampered or incomplete conversion does not
yield a smaller evaluable cohort. Record a new durable event before reading
each normalized file, bind its exact bytes, retain a private snapshot and
collect every registered origin. This read establishes the schedule, not
model scores or final eligibility.

Preserve the conversion policy unchanged:

| Topic | Frozen rule and limitation |
| --- | --- |
| Period | Each full export, first EGV through last EGV plus 300 seconds, half-open; this is an administrative interval, not the publication's multimodal collection period |
| Time | Exact registered naive local timestamps and elapsed integer microseconds; no UTC, DST or physical-time continuity is inferred |
| Clock | One assumed segment per export, with backward EGV time refused; transmitter counters do not establish sessions |
| Availability | Measurement time used as availability, as a retrospective hypothesis; actual receipt and backfill remain unknown |
| Cadence | Preserve jitter and gaps; no rounding, tolerance, interpolation, carry-forward filling or smoothing |
| Values | Only numeric values strictly between 40 and 400 mg/dL are measured-point candidates; excluding numeric endpoints is a conservative policy |
| Censoring and conflict | Retain `Low`/`High` direction without assigning a measured value or numeric bound; preserve missing, invalid and ambiguous records and native record lineage |

The freeze binds the conversion plan, inventory, reconstruction evidence,
source identities, all normalized input identities, actual intervals and every
registered origin. Preserve every planned person, even if later execution
fails or yields insufficient paired targets. This preparation does not infer
eligibility from earlier opportunity counts.

## Unchanged donor model and limited origin verification

Use the already learned shared `StandardScaler` and
`Ridge(alpha=1.0, fit_intercept=True, solver="svd")`. Preserve model and learned
freeze bytes exactly. There is no scaler fitting, regression fitting,
personalization, calibration, feature selection, regularization search,
forecast clipping or examination of external performance.

The donor preparation is a **metadata-only seal**, distinct from the stronger
export in [M3-EXTERNAL/0.1](m3-external-protocol.md). Its origin attestation uses
schema `opent1d.physiocgm.frozen-model-metadata/1`. Read only the original source
`plan.json`, completed fit `state.json`, learned `freeze.json` and `model.json`.
Check their internal hash
bindings, model shape and settings, participant/source inventory and recorded
clean historical human-fit provenance. Bind the exact permitted files and
retained source identities into a separately identified attestation. Learned
parameters, participant aliases and source-bound provenance remain private.

This operation deliberately does not call `learned_read` or the existing
`external.export_model` verification path. It does not open retained development
or validation observations, validation traces/results, the original live donor
ledger or reserve material; it does not repeat fitting or validation arithmetic.
Hashes referring to those unopened artifacts remain recorded claims, not newly
verified artifact contents. The seal therefore checks the consistency of the
retained model metadata and bytes, not the correctness of the original learning
procedure or a complete source-data/access-history reconstruction. A recorded
clean commit does not independently establish that training was executed there.

Do not label the seal a fully verified historical export or pass it off as the
existing portable model bundle. Local hashes and attestations detect changes
relative to retained identities; they are not external signatures and cannot
defend against replacement of all evidence together. Changing the donor model
or upgrading the verification scope requires explicit new evidence and a new
freeze, with prior access retained.

## Frozen prediction and analysis rules

Adopt the matching and reporting semantics of M3-EXTERNAL/0.1 without executing
them. The frozen plan must contain the following rules, including uncertainty
settings, so a later implementation cannot select them after seeing scores.

| Item | Rule |
| --- | --- |
| Inputs and horizon | CGM in mg/dL at exactly `t−25`, `t−20`, `t−15`, `t−10`, `t−5` and `t` minutes; predict exactly `t+30` minutes |
| Causal history | All six measured, unambiguous features within the interval, available by `t`, in the same clock segment |
| Warm-up | Retain the first 60 minutes of origins as exclusions |
| Comparator | Persistence: the latest eligible observed CGM at `t` |
| Matching | Exact timestamps only; no tolerance, interpolation or rounding |
| Forecast denominator | Every registered origin, including origins with unusable current glucose or history; not a regular five-minute grid |
| Forecast versus score | Future-target availability may not decide whether a causal forecast is made; report prediction and scoring coverage separately |
| Contributor floor | Completed execution, at least 288 jointly scored origins spanning at least 24 hours; no donor-development eligibility condition |
| Primary outcome | Equal-person mean of paired participant MAE differences, Ridge minus persistence; negative favors Ridge |
| Secondary outcomes | Equal-person MAE, RMSE and bias; error by CGM at the origin: below 70, 70–180 inclusive, above 180 mg/dL or unknown |
| Uncertainty | Resample whole contributing people with replacement, 2,000 draws, seed 301; descriptive 95% interval uses one-based order statistics 50 and 1,950; undefined with fewer than two contributors |

Only measured point targets enter ordinary MAE/RMSE. The preserved PhysioCGM
censor statuses have no verified numeric bound and therefore supply neither
point scores nor a numeric error lower bound. Coverage floors are operational
rules, not a power calculation. Correlated timestamps are not independent
people, and glucose strata are not duration-weighted clinical exposure.

A later report must retain every planned person, failure, exclusion and
unattempted origin. Any planned person not contributing makes the cohort
incomplete, even if a partial aggregate can be computed. No single-person
result or aggregate is calculated during this preparation.

## Access, artifacts and preparation acceptance

Keep all health records, schedules, private source paths, individual derived
artifacts and model parameters outside Git and public services. Use a fresh
private directory for every attempt, retain failed attempts, and write durable
access evidence before each corresponding read. An access-ledger failure
permits no read. Earlier conversion/reconstruction and current normalized-input
binding are disclosed accesses, not first-ever access to the cohort.

The preparation reuses the durable conversion-ledger event `before_bundle_read`
with explicit subjects and source identities:

| Event subject | Permitted read after the receipt |
| --- | --- |
| `donor` | The four request-bound donor control files as a batch |
| `conversion` | Bound conversion control metadata and completed reconstruction evidence as a batch, excluding native and normalized observation payloads |
| Each participant alias | That participant's hash-bound normalized file, with a separate receipt before each file read |
| `freeze` in later verification | The saved freeze bundle, including all private normalized snapshots, under one bundle-wide verification receipt |

In these reused receipts, `plan_sha256` binds the exact pre-read request bytes.
It does not refer to the later generated plan: that plan cannot exist until
the authorized normalized reads establish its schedule. Verification validates
the original batch/per-file receipts as well as recording its own new
bundle-wide access. Fixed request/inventory metadata may be read first to
identify the bundle for that receipt; health snapshots may not.

Retain the authorization and prior-access disclosure, sealed donor sources,
conversion and reconstruction identities, full cohort schedule, normalized
input identities and snapshots, scientific rules, implementation/protocol provenance and
hash inventory. Record the current revision and dirty status alongside exact
source identities; an uncommitted implementation must not be represented as
a clean committed release. The plan has stage `pre-scoring`,
`evaluation_enabled: false` and `execution_supported: false`.

The separate `human-freeze --request --output` operation in the
[external workflow](../m3-external-tutorial.md#prepare-the-private-human-physiocgm-freeze)
creates this bundle. `human-verify-freeze --bundle --output` records
access before checking retained normalized snapshots and verifies the saved
evidence, donor seal, full roster, schedule, rules and provenance without
forecasting or returning to the native sources. It creates its own fresh
private verification output and preserves failures. This verifies preparation
consistency; it does not repeat the historical donor learning verification.

Acceptance requires synthetic checks of permitted donor reads, model identity,
complete-roster binding, source tampering, access ordering, failure retention
and the separation from evaluation. In the private human preparation, verify
that all ten converted exports and the unchanged donor are bound to the saved
plan. Report only preparation completion and permitted aggregate technical
counts. Passing these checks establishes the preparatory mechanics and their
use on the bound sources; it is not independent human reproduction or
predictive evidence.

## Separate execution gate and interpretation

The existing synthetic external worker must refuse this distinct human
pre-scoring schema. Changing a Boolean must not enable prediction. A later
human execution route needs a reviewed bridge that validates this freeze,
retains its limited donor-verification scope, establishes access-before-worker
ordering and exclusive execution claims, preserves failures and supports
offline reconstruction under these same scientific rules. Explicit user
authorization for that scoring step remains required.

Any change to period, clock, availability, value interpretation, matching,
donor model, inclusion, outcomes or uncertainty rules requires a versioned
amendment with reasons and already inspected material disclosed. A later
implementation may strengthen technical verification without quietly altering
the research question or concealing the original verification scope.

Even a successful external forecast comparison would support only this
retrospective CGM prediction task under its assumptions. It would not identify
insulin response, validate simglucose or Cambridge as a person's physiology,
show the counterfactual effect of another controller, establish clinical
safety or demonstrate broad population generalization.
