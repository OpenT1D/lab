# 0011 — PhysioCGM intake preparation from documented code expectations

Status: accepted for synthetic preparation, 20 September 2026. Format-only update below follows the authorized local CGM audit; human processing remains disabled.

## Context

The external forecast route consumes normalized observations. It does not establish that these observations faithfully represent a provider's native release. At the initial decision, [source review](../research/physiocgm-source-assessment.md) confirmed PhysioCGM v1 metadata and identified CGM field expectations in the authors' code; no patient archive had yet been inspected. The dataset's CC0 dedication does not license the authors' implementation.

## Decision

Add an independently written candidate converter in `experiments.m3.physiocgm`, contract `physiocgm-cgm-candidate/0.1`. It accepts explicitly declared synthetic inputs only. It has no download, model-fitting or evaluation command and does not relax the existing external human-input refusal. Preserve the Ohio, AZT1D and M3-EXTERNAL/0.1 protocols.

Select only exact `EGV` events using the documented column names. Require a declared complete header; never infer a whole native schema from the four known fields. Preserve every registered EGV time, missing values and censor directions. Keep exact naive local time and reject backward EGV clocks; do not sort, round or fill gaps. Merge only equivalent duplicates, preserving CSV record lineage; conflicting duplicates remain ambiguous. Do not treat device `Index` as unique lineage.

For this provisional synthetic contract, exclude numeric values at or outside 40–400 mg/dL and preserve `Low`/`High` without asserting numerical bounds. Measurement time as availability and a single local clock segment are explicit assumptions. Accepting exact microseconds is an internal preservation capability, not evidence that release timestamps contain them.

Bind native bytes, normalized observations, audits, request, complete cohort and converter provenance in a saved inventory. Recompute successful conversion from the saved source to verify it without original paths. A failed person prevents generating a partial-cohort external registry. Preserve the failed attempt and every planned case. Read-attempt records describe synthetic preparation; they are not a human first-access ledger.

## Consequences

The [tutorial](../physiocgm-intake-tutorial.md) exercises preparation on invented files. This is a tested candidate, not verified provider support. The external report remains independently reconstructible from normalized data; a human release would additionally need its native conversion evidence bound into the authorized freeze.

Before enabling human inputs, obtain the required acquisition/processing authorization, inspect the actual release locally, resolve file/clock/status discrepancies and record prior access. No predictive scores are needed for that format audit. Any resulting change to scientific conventions requires an explicit amendment before evaluation.

## Format-only update after local audit — 20 September 2026

The separately authorized acquisition and private CGM audit are complete. They identified an entirely empty unnamed column and timestamps using a space plus a single-digit hour. Contract `physiocgm-cgm-candidate/0.2` adds these two bounded syntactic forms, verified with self-authored fixtures. It requires an exact declared header, at most one empty name and an exactly empty field in every record, including excluded events. It accepts `YYYY-MM-DD H:mm:ss` exactly, preserving native strings and elapsed time. It neither drops unknown content nor changes the shared AZT1D timestamp parser.

Saved native bytes and CSV record lineage remain intact. Audits count the accepted variants, and converter provenance distinguishes old bundles from this implementation. Synthetic artifacts continue to report that they do not verify a human release. No actual patient files were processed by the updated candidate, and the human-input gates remain closed.

This is a format correction, not a change to period selection, availability, clock segments, censoring, exact-window matching, model or scoring rules. The [human-use proposal](../research/physiocgm-source-assessment.md#proposed-human-use-boundary-not-an-evaluation-freeze) records unresolved choices separately. It does not amend M3-EXTERNAL/0.1 or activate a human freeze. The private audit is prior access even though model scores remain unseen.
