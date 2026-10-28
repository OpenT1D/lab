# 0013 — PhysioCGM external cohort and model freeze before scoring

Status: accepted for private pre-scoring preparation, 20 September 2026.
Human prediction and evaluation remain disabled.

## Context

The ten authorized PhysioCGM raw CGM exports have been converted and
reconstructed under [Decision 0012](0012-physiocgm-human-conversion.md).
The user has authorized the proposed next step: connect this controlled input
to the unchanged existing predictor and freeze the external evaluation before
calculating scores. Earlier audit and conversion access must remain visible.

The existing [M3-EXTERNAL/0.1](../research/m3-external-protocol.md) workflow
accepts synthetic cohorts. Its model export verifies retained donor
development/validation inputs and access history. Reusing that export would
reopen material outside this narrowly scoped preparation; its attestation
cannot truthfully describe a metadata-only check.

## Decision

Adopt [M3-PHYSIOCGM-EXTERNAL/0.1](../research/physiocgm-external-freeze-protocol.md)
and preparation schema `opent1d.physiocgm.external-freeze/1` as a separate
human pre-scoring boundary. Bind all ten complete converted exports, original
release and conversion identities, every registered origin, intervals,
prior-access disclosure and the unchanged existing scaler/Ridge model. Keep
the full-export, exact-time, value, naive-clock and conditional availability
rules of PHYSIOCGM-CONVERSION/1.0 unchanged.

Use a metadata-only donor seal with origin-attestation schema
`opent1d.physiocgm.frozen-model-metadata/1`. It verifies the source
plan, completed fit state, learned freeze and model bytes, internal hashes,
model contract and recorded clean historical provenance. It does not read
development or validation records, replay validation arithmetic, access the
reserve, retrain, or claim the full origin verification of the existing model
export. Retain this weaker verification scope in the plan and any later use.
Model parameters and source-bound identities remain private.

Before binding normalized inputs, check the completed conversion and its
previously completed reconstruction evidence without reopening native files;
record a donor batch event, a conversion/reconstruction metadata batch event
and a new durable event before each normalized-input read. Reused
`before_bundle_read` receipts bind the exact pre-read request hash through
their `plan_sha256` field, not the later generated plan. Reject incomplete
or inconsistent conversion rather than silently selecting fewer people. Retain
private normalized snapshots, provenance and immutable identities in a fresh
attempt directory. Preserve failed attempts and verify saved preparation in a
separate fresh directory, with a bundle-wide receipt before snapshot reads
and verification of the original batch/per-file access receipts.

Freeze the M3-EXTERNAL/0.1 scientific rules before scoring: six exact CGM history
points, 30-minute horizon, 60-minute warm-up, no refitting, persistence,
completed execution plus 288 paired origins over at least 24 hours for
contribution, equal-person paired MAE difference and whole-person bootstrap
with 2,000 draws and seed 301. Preserve complete-cohort failure accounting.
No forecast, target error, eligibility outcome or bootstrap is calculated in
this step.

The saved plan has stage `pre-scoring`, `evaluation_enabled: false`,
`execution_supported: false` and its own schema. The existing
synthetic external worker must reject it independently of that flag. A later
human execution path and explicit scoring authorization are separate gates.
Different study sources support an external study comparison; participant
independence is not established by aliases, file hashes or institutional names.

## Alternatives

Reopening the full donor learning evidence would offer stronger origin
verification but expands this step's data-access scope. Pretending the
metadata-only seal provides that verification would misstate the evidence.
Passing human observations as synthetic input would bypass the established
boundary. None of these alternatives is adopted.

## Consequences and conditions for revisiting

The controlled human conversion and existing predictor can be bound to a
concrete, reviewable future comparison without computing scores. This prepares
evaluation; it establishes neither predictive quality nor correct training
history through independent reconstruction. Records and individual derived
artifacts remain outside Git and public outputs.

Any scientific rule or donor change requires a versioned amendment retaining
prior access. Later execution must verify the frozen identities, preserve
the donor seal's limited scope, record access before processing, retain every
planned case and reconstruct outcomes offline. The Ohio, AZT1D,
M3-EXTERNAL/0.1 and PHYSIOCGM-CONVERSION/1.0 protocols keep their historical
meanings. Forecast success would not establish physiological validity,
controller benefit or clinical safety.
