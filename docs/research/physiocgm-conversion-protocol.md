# PHYSIOCGM-CONVERSION/1.0 — Human raw-CGM conversion

Accepted 20 September 2026 under
[Decision 0012](../decisions/0012-physiocgm-human-conversion.md).
**Scope: authorized local conversion and reconstruction only; no model
evaluation.** The workflow schema is `opent1d.physiocgm.human/1`.
The [source assessment](physiocgm-source-assessment.md) records the release,
rights review, prior audit and unresolved semantics. The
[intake tutorial](../physiocgm-intake-tutorial.md) is the canonical command guide.

## Purpose and evidence boundary

Determine whether the reviewed importer can faithfully normalize the ten
original PhysioCGM v1 CGM exports under explicit, reproducible assumptions.
The user authorized local acquisition and a CGM-only audit first, then execution
of the proposed next conversion step. This protocol records the scope of that
processing; it is not a general authorization to acquire new sources, inspect
other sensor channels, publish records or evaluate a predictor.

The earlier audit has already inspected formats, statuses, timing, duplicates and
conditional data-opportunity counts. Those observations informed format fixes
and the full-export policy. They are prior access even though no model scores
were inspected. Conversion results establish technical representation under the
declared assumptions; they cannot establish predictive performance, actual
online availability or physiological validity.

## Source, roster and private plan

Pin the original raw release
[10.6084/m9.figshare.28136294.v1](https://doi.org/10.6084/m9.figshare.28136294.v1),
using the retained [versioned metadata](https://api.figshare.com/v2/articles/28136294/versions/1)
and private acquisition evidence. Use only the ten original `cgm.csv` members
already retained by the authorized audit. Processed archives, wearable channels,
demographics and other event values are outside this conversion's input scope.
The input CSV necessarily includes non-EGV rows; inspect their CSV structure and
any unnamed-column emptiness, but do not normalize their clinical contents.

Before reading native observations for conversion, persist a private plan that
binds:

- the protocol and human schema, fixed conversion policy and converter source
  identity;
- the pinned release and all ten planned local participant aliases;
- each original archive/member identity, retained native CSV identity and exact
  declared header, using the existing acquisition/audit evidence;
- the processing authorization and prior-access disclosure, with identities of
  the retained audit and access-history evidence;
- the fixed access-order contract requiring durable evidence before native reads.

Each conversion or verification attempt receives its own explicit private output
directory through the command line and maintains its own durable ledger there.
The attempt's output and ledger identities are recorded in its artifacts; their
paths are not predetermined by the source-bound plan.

This fixes the complete roster and full-export rule before conversion. Exact
first/last EGV bounds are derived mechanically from each bound source file and
retained with the output; they are not chosen using model performance or coverage.
Duplicate source identities or a missing planned person must not silently produce
a smaller cohort. Local hashes provide integrity and consistency; they do not
prove biological identity, absence of overlap with AZT1D or authenticity against
replacement of every local evidence artifact.

The separate `human-freeze` operation snapshots the request, reviewed evidence,
converter code and protocol into a fresh private plan directory without reading
native observations. Record the Git revision and dirty status alongside exact
source hashes and retained source copies. An uncommitted working tree is disclosed
rather than represented as a clean commit. The conversion is tied to those bytes.
A different code or policy version
requires a new explicit plan, not silent reuse of the old identity.

## Adopted time and period rules

| Topic | Fixed rule | Interpretation limit |
| --- | --- | --- |
| Cohort | All ten original raw CGM exports, including conversion failures | Ten planned people are not ten verified external-evaluation contributors |
| Period | Complete export: first EGV through last EGV plus 300 seconds, half-open | This is an administrative CGM export interval, not the publication's multimodal collection period; the final 300 seconds add no observation |
| Period selection | No crop based on wearable availability, opportunity counts, later scores or an assumed seventeen-day duration | Exported days may differ in collection context or device settings |
| Time preservation | Preserve exact registered naive local timestamps and elapsed integer microseconds | No timezone, UTC, DST or physical-time continuity is inferred |
| Clock segment | One assumed segment per export; reject backward EGV times | Transmitter counter decreases and identifier changes are not validated segment boundaries |
| Availability | Set availability equal to measurement time as a retrospective hypothesis | No claim of actual receipt, lack of backfill, device execution or absence of retrospective processing |
| Cadence | Preserve native jitter and gaps without rounding, tolerance, interpolation or filling | A nominal five-minute source cadence does not establish exact five-minute observations |

The eventual external forecast contract continues to require six exact past
values and an exact 30-minute target, with a 60-minute warm-up. This conversion
does not execute that forecast contract or choose periods to increase its
coverage. No window-opportunity count constitutes a predictive result or final
external eligibility decision.

## Observation and lineage rules

Use the independently written `physiocgm-cgm-candidate/0.2` parsing rules for
the declared native headers. Normalize only exact `EGV` events, in original file
order. An empty unnamed column is accepted only when every record has an empty
field at that position. Accept the observed space-separated single-digit-hour
syntax exactly while preserving the original source timestamp string. Retain
native bytes unchanged and fail on unexpected header, width, syntax or unnamed
content rather than silently discard it.

Retain each registered EGV origin. Missing, invalid, censored and ambiguous
observations remain distinguishable. Equivalent duplicate timestamps
may share one normalized observation with all contributing CSV record numbers;
conflicting duplicates remain ambiguous. Device `Index` is not the record
lineage identifier. Preserve normalized-to-native references even when records
are unusable for future scoring.

CGM units are mg/dL as declared by the release column. Numeric values strictly
between 40 and 400 are measured-point candidates. Numeric values at or outside
those limits receive parser status `invalid` and are excluded as measured points;
excluding 40 and 400 is a conservative analysis choice, not proof they are censor
codes or intrinsically invalid measurements. `Low` and `High` preserve censor
direction without assigning 40/400 as observed values or asserting a numerical
censor bound. This protocol does not establish a complete historical Dexcom CSV
dictionary or repair uncertain sensor semantics.

The reused parser audit retains `release_files_verified: false`: the candidate
does not verify the release's broader sensor and clinical semantics. The human
workflow separately verifies the actual source SHA-256 identities and conversion
evidence. Byte-identity verification does not turn this flag into a clinical
validation claim.

## Access ordering, retention and failures

Keep all source records, individual derived artifacts, source-bound plans and
access evidence private and outside any Git repository. `human-prepare` copies
the bound plan into its fresh output directory. Append a hash-chained, fsynced
plan/source-bound access event before each native conversion read and retain its
receipt. A failed ledger write permits no corresponding read. Earlier audit
access remains part of the history; this event is not the first-ever access to
the source.

Use a fresh output directory for every attempt. Retain the plan, policy,
authorization and prior-access references, converter provenance, native snapshots,
normalized observations, diagnostics, access receipts and artifact identities.
Keep every planned case in the status record, including failed and unattempted
cases, and preserve failed attempts. Descriptive output may summarize counts and
conversion statuses without exposing individual health values, native dates,
device identifiers or arbitrary source text in terminal logs or public reports.

Fail closed on source identity mismatches, unsupported formats or inconsistent
saved evidence. Do not repair the source, silently exclude a person or label a
partial conversion complete. Write the complete `cohort.json` only after every
planned conversion succeeds; it is a descriptive conversion artifact, not an
executable external registry. Keep `evaluation_enabled: false`. Any downstream
human-evaluation adapter must refuse an incomplete conversion cohort until the
handling of those failures is explicitly specified under that later protocol.

## Reconstruction and acceptance

The separate `human-verify` operation uses a fresh private output directory and
records access before hashing and replaying the saved conversion bundle.
Reconstruct successful conversion from saved native snapshots and compare the
normalized observations, diagnostics, intervals and lineage with the saved
outputs. Verify plan/policy/source identities, retained access evidence and
artifact inventory without relying on the original source location or opening a
model or live access log. Human reconstruction is itself local processing of
retained health records; retain it within the same authorized private boundary
and access history.

Check the implementation with invented fixtures before actual human execution,
including accepted native syntactic variants, source changes, exact-time
preservation, conservative statuses, duplicate conflicts, ledger ordering,
complete-roster failures, tampering and reconstruction. Synthetic checks establish
mechanics. Actual conversion and reconstruction establish support for these
specific source files under this protocol, without validating broader provider
exports or biological conclusions.

The conversion acceptance record states all ten planned statuses, any failure,
the reconstruction outcome and remaining clock/availability assumptions. It
contains no forecasts, MAE/RMSE, superiority conclusion, learned parameters,
model/scaler load or model/scaler export. No AZT1D reserve material is needed.

## Separate next gate: external evaluation

The human-input gate in [M3-EXTERNAL/0.1](m3-external-protocol.md) remains closed.
This conversion protocol does not amend its model, matching, outcome or eligibility
rules and does not create an external cohort/model freeze. A later bridge must
bind the verified human conversion, complete roster, actual intervals and prior
access to the unchanged donor model and the authorized external comparison.

Period, clock, availability, value-policy or matching-rule changes require an
explicit versioned amendment recording the reason and already inspected material
before scoring. Good forecasts under observed treatment would still not identify
insulin dynamics, validate a physiological engine, or establish what a different
controller would have caused. Independent human reproduction remains separate.
