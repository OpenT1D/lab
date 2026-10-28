# 0012 — Bounded human PhysioCGM conversion before evaluation

Status: accepted, 20 September 2026.

## Context

The separate authorized acquisition and private format audit inspected the ten
original PhysioCGM v1 CGM exports without model scores. The candidate importer now
supports the observed empty column and single-digit-hour spelling in synthetic
tests. [Decision 0011](0011-physiocgm-intake-preparation.md) remains the historical
record of that preparation. The [source assessment](../research/physiocgm-source-assessment.md)
distinguishes verified format evidence from unresolved physical-clock, receipt-time
and collection-context semantics.

The user has authorized the next concrete step: adopt the proposed period and
time assumptions and connect controlled local processing of the actual files.
This is authorization for conversion, not a model evaluation. Previous format
and data-opportunity inspection must remain disclosed.

## Decision

Adopt [PHYSIOCGM-CONVERSION/1.0](../research/physiocgm-conversion-protocol.md),
human workflow schema `opent1d.physiocgm.human/1`, as a separate conversion-only
boundary. Bind the ten original raw CGM exports from
`10.6084/m9.figshare.28136294.v1` to a durable private plan, source identities,
prior-access evidence, processing authorization and converter provenance before
the conversion reads. Keep all planned people and all failed attempts.

Use each complete raw CGM export, from the first EGV through the last EGV plus
300 seconds as a half-open administrative interval. Retain exact registered
times, including jitter, with one assumed naive local clock segment and
measurement time used as availability. These are declared retrospective
assumptions; they do not establish actual receipt time, continuous physical time,
sensor sessions or the publication's multimodal study period. Do not crop by
opportunity counts or wearable availability.

Preserve the candidate's conservative value policy: `Low` and `High` keep their
direction without a numeric bound; numeric values at or outside 40–400 mg/dL
receive parser status `invalid` and are excluded as measured points under this
conservative policy. Preserve missing and conflicting records,
original bytes, source-row lineage and format diagnostics. Do not infer timezone
corrections, round, interpolate, fill, smooth or repair records.

Conversion may produce private normalized observations and a descriptive intake
report. It does not open a model or scaler, export a donor model, create a human
external evaluation freeze, forecast or calculate error scores. The existing
Ohio, AZT1D and M3-EXTERNAL/0.1 protocols retain their meanings and the external
human execution gate remains closed.

## Alternatives

Keeping human conversion disabled would leave the tested parser disconnected
from the authorized release. Selecting an arbitrary seventeen-day crop would
invent a correspondence with the multimodal collection interval. Rounding
timestamps or including numeric endpoints would change the declared scientific
conventions. Neither alternative is adopted here.

## Consequences and conditions for revisiting

Source-bound local conversion can now establish whether the importer represents
all ten actual CGM files under the declared policy. It does not establish
forecast quality, biological validity, population independence or clinical use.
Retain private reconstruction evidence and failure accounting; publish no health
records or individual derived artifacts through this step.

A later external evaluation needs its own source/cohort/model-bound freeze and
verified bridge from the human conversion artifacts. Any period, clock,
availability, endpoint or matching-rule change requires an explicit versioned
amendment with prior access disclosed. Already inspected data cannot become an
untouched evaluation set by changing a directory or label.
