# 0063 — Reliable recorded digests and native M3 archive browsing

Date: 5 October 2026

Status: accepted for implementation; execution evidence is recorded separately.

## Context

The general archive library indexes eight task types but verifies only maintained
M4 reports. M3 forecast/comparison reports are already supported by their native
CLI, execution view and durable readers. A retained M4 archive produced 34
catalogue missing-path diagnostics despite successful native reconstruction:
its `m4-initial-load-reference-seal/1` claims are relative to `reference/`, while
the catalogue interpreted them beside the manifest. All 34 correct files agree
with their claims. This is a reader defect; existing scientific bytes and seal
conventions remain authoritative.

## Decision

Catalogue recorded-digest checking selects a fixed path base and claim structure
from explicitly supported manifest schemas. The M4 reference seal uses its
native `reference/` base; ordinary native seals retain their documented base.
Unsafe paths, malformed claims and missing or changed claimed bytes remain
explicit failures. Unknown schemas receive an explicit unsupported status and
are never relabeled as checked matches. Match status covers supported recorded
claims only, not all bytes, source authenticity or scientific validity. No
archive rewriting or filename/path guessing is permitted.

The general library adds exactly `m3-forecast` and `m3-compare` to its fixed
native-verification whitelist beside `m4-study-secure`. Its owned worker uses
existing report/reconstruct commands without predictor imports or execution.
Metadata reading remains passive. Fixed task-specific artifacts are JSON and
Markdown for M3, with the existing SVG additionally available for M4. Preserve
source inventories before/after operations, safe roots/opaque pointers, fixed
argv, bounded deadlines, one active operation and snapshot withdrawal on changes.
Unsealed archives may remain visible as metadata/raw evidence but receive no
verified report claim. A sealed incomplete parent can retain diagnostic children
according to its unchanged native reader. If a sealed M3 archive lacks its
original top-level report, preserve the separate metadata error and use the
same fixed native reconstruction command for explicit verification. Validate
the resulting task/schema, synthetic declaration and strict completeness flag;
never synthesize source members or infer successful completion from metadata.

For M3, the report API returns `task`, the original native `schema`,
`native_report`, `verification`, `verification_scope`, `source_freshness`,
`report_completeness` and `report_sha256`. The browser renders native coverage,
errors and common-support fields without computing new scientific metrics.
Original JSON/Markdown downloads are native reader bytes. Existing M4 response
fields remain compatible. Recorded cohort completeness is not prediction quality.
Saved metadata, record checks, native verification and completeness stay separate.
Durable packages still require their separately recorded exact trusted checkout;
this library does not execute saved readers, install runtimes, resume experiments
or adopt recorded process identities.

## Alternatives

Rewriting retained archives or guessing roots from existing files would conceal
wrong claims and change historical evidence. Leaving M3 exclusively in its
execution/durable views preserves the current gap in general archive browsing.
Neither alternative meets this bounded task.

## Consequences and verification

Separate branches own catalogue checks, the library adapter and presentation;
integration owns canonical documentation and actual acceptance, with independent
combined review. Verify the retained M4 discrepancy, real tampering and unknown
schemas; verify full/failed/partial M3 archives via CLI and browser with exact
downloads and unavailable original inputs. Preserve scientific sources, native
seals, models, locks, archive bytes and exact historical reader checkouts. Full
locked repository checks remain software evidence. Main/publication, independent
human use and empirical/biological acceptance remain separate.

## Revisit conditions

Add another manifest schema or task only when its native claim/reader contract
and representative accepted/failed archives are available. Broader human-data
intake, empirical ranking or executable saved readers require separate scope.
