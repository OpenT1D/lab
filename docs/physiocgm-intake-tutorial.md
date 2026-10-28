# Convert PhysioCGM inputs with preserved source evidence

This workflow preserves native CGM bytes, normalized observations and conversion evidence. The original synthetic commands prepare invented inputs for the [external forecast route](m3-external-tutorial.md) and still refuse human inputs. The separate human commands implement authorized private conversion under [PHYSIOCGM-CONVERSION/1.0](research/physiocgm-conversion-protocol.md), with no model fitting, prediction or evaluation. [Decision 0011](decisions/0011-physiocgm-intake-preparation.md) records synthetic preparation and the `physiocgm-cgm-candidate/0.2` format correction; [decision 0012](decisions/0012-physiocgm-human-conversion.md) records the human boundary.

## Run synthetic preparation

From the repository root, choose new output directories:

```sh
uv sync --locked
uv run --locked python -m experiments.m3.physiocgm fixture --output /tmp/opent1d-physiocgm-fixture
uv run --locked python -m experiments.m3.physiocgm prepare --request /tmp/opent1d-physiocgm-fixture/request.json --output /tmp/opent1d-physiocgm-converted
uv run --locked python -S -m experiments.m3.physiocgm verify --bundle /tmp/opent1d-physiocgm-converted
```

The fixture creates two invented sources with gaps, missing readings, censor tokens, equal duplicates and conflicting duplicates. Its declared CSV header includes the four fields identified in author code plus an explicitly invented ignored field. The second source also exercises an empty unnamed column and space-separated timestamps with single-digit hours. These are self-authored format examples, not patient samples or a copied complete release header. No network or estimator installation is needed.

`prepare` checks the declared source hashes and header, records an attempted synthetic read, preserves the native bytes and creates normalized observations. It writes a compatible synthetic external registry only when every planned conversion succeeds. A failed conversion preserves status, safe error information and the full planned roster; it does not silently omit a person. Repeated attempts require new output directories. A failed bundle cannot pass the complete-conversion verifier.

## Read the artifacts

| Artifact | Purpose |
| --- | --- |
| `request.json` | Exact submitted metadata, complete cohort, input identities and declared headers |
| `state.json` | Status of every planned case, safe errors, converter/source hashes and provisional assumptions |
| Per-person `read-attempt.json` | Attempted synthetic source access recorded before its read |
| Per-person `native.csv` | Exact successfully hash-verified invented source bytes |
| Per-person `observations.json` | Normalized elapsed-time CGM, statuses and CSV record lineage |
| Per-person `audit.json` | Record counts, excluded non-EGV count, duplicate count, status counts, format-variant counts and assumptions |
| `registry.json` | Complete synthetic cohort, available only after all conversions succeed |
| `manifest.json` | Inventory connecting all saved artifact bytes |

`verify` checks inventories and provenance, then recomputes the conversion and audit from each saved native snapshot. It verifies complete-cohort registry construction. Original input paths need not exist. An edited normalized value fails even when its hash inventory has been updated. Replacing all source evidence and all trusted hashes is outside this consistency guarantee.

The generated registry retains absolute paths. Moving a bundle does not invalidate its offline conversion verification, but its original registry paths are not silently rewritten for execution. Its potential future evaluation ledger is a sibling of the conversion directory, keeping subsequent access history outside the sealed conversion inventory. No ledger is initialized by these commands.

## Conversion boundaries

The exact complete header must be declared. At most one column may have an empty name, and its field must be exactly empty in every CSV record, including non-EGV events. Whitespace or any other content is an error; a trailing separator is not silently discarded. Native snapshots retain that column and its original position. The audit records whether it was present and how many records were checked.

Only `Event Type` exactly equal to `EGV` contributes origins. Every such time remains represented even if its glucose cannot be used. Equal numerical duplicates merge with record lineage; conflicts remain unscored. `Low`/`High` are directional censoring with an unknown bound. Numeric endpoints 40 and 400 are excluded under the provisional conservative policy. Missing or invalid point readings are not repaired.

Times remain naive local timestamps with exact integer microseconds. In addition to existing two-digit-hour timestamps with a space or `T` and optional microseconds, the converter accepts precisely `YYYY-MM-DD H:mm:ss` with a space, one hour digit and mandatory whole seconds. It preserves the original timestamp string; adding a leading zero during parsing does not shift or round time. Other one-digit-hour spellings, timezone suffixes and unsupported precision are rejected. The audit counts single-digit-hour EGV records before duplicate merging.

The converter rejects backward EGV order. It does not implement daylight-saving corrections, online receipt times or sensor-session reconstruction. Availability equal to measurement time and one clock segment are explicit assumptions. The human protocol limits their interpretation to conditional retrospective analysis. Registered origins describe observed events, not all theoretically possible five-minute slots.

## Synthetic verification

The 33 dedicated parser and service tests passed on 20 September 2026, including both format variants, exact timing and source lineage, refusal of nonempty unnamed fields even in excluded events, offline reconstruction, semantic tampering, refusal of human inputs before native reads in both preparation and verification, and preservation of incomplete cohorts. Run the full repository checks with `uv run --locked python scripts/check.py`. These tests establish conversion mechanics only.

Synthetic artifact fields `release_files_verified: false` and `native_release_verified: false` describe that execution boundary; they do not negate the separate private audit. Never label real inputs synthetic to bypass it. Old bundles remain bound to their original converter sources and contract, and cannot silently verify under a changed implementation.

## Authorized private human conversion

This is a separate source-bound route for the previously audited ten original raw CGM exports. It accepts only `kind: human`, an explicit conversion-only authorization and a disclosure of prior audit access. It does not open models, produce forecasts or create an executable external registry. Use fresh private directories outside every Git repository, with no group/other access. Source files must be regular, private and not symlinks or hardlinks.

First prepare a private JSON request using the retained audit metadata. Do not rediscover patient fields by passing real data to the synthetic commands. The request has these exact top-level fields:

| Field | Required content |
| --- | --- |
| `schema`, `kind`, `release` | `opent1d.physiocgm.human/1`, `human`, `10.6084/m9.figshare.28136294.v1` |
| `authorization` | `confirmed: true`, `scope: local-conversion-only`, a truthful user-authorization `reference`, `retention: private-local-reproducibility` |
| `prior_access` | `reviewed: true`, `status: present`, and a reference disclosing the format audit and earlier data-opportunity counts |
| `evidence` | Five named `{file, sha256}` references described below |
| `people` | Exactly ten entries: local `id`, `input: {file, sha256}`, exact `header`, `archive` and `audit_member` |

The five evidence roles are `acquisition` (`acquisition.json`), `audit_inventory` (`audit/format-check-03/evidence-manifest.json`), `prior_access` (`audit/format-check-03/access-snapshot.jsonl`), `rights_metadata` (`metadata/release-v1.json`) and `audit_report` (`audit/format-check-03/Bevindingen.md`), all under the same private release root. Their hashes, except the inventory's own identity, must also match that retained audit inventory. The ten archive aliases are `archive-01` through `archive-10`; their native members are `audit/format-check-01/cgm/<archive>.csv`. These are private audit aliases, not participant identifiers from the provider.

With `PHYSIO_PRIVATE` set to the authorized private release directory, run:

```sh
uv run --locked python -m experiments.m3.physiocgm human-freeze --request "$PHYSIO_PRIVATE/conversion-request.json" --output "$PHYSIO_PRIVATE/conversion-plan"
uv run --locked python -m experiments.m3.physiocgm human-prepare --plan "$PHYSIO_PRIVATE/conversion-plan/plan.json" --output "$PHYSIO_PRIVATE/conversion"
uv run --locked python -S -m experiments.m3.physiocgm human-verify --bundle "$PHYSIO_PRIVATE/conversion" --output "$PHYSIO_PRIVATE/conversion-verification"
```

`human-freeze` reads reviewed metadata only. It snapshots the request, code, protocol and audit evidence before any native read. Exact source hashes and copies identify the implementation even in a disclosed dirty working tree. Changed implementation/policy bytes require their corresponding recorded plan; code copies permit restoring the matching implementation.

`human-prepare` copies that plan and appends a durable hash-chained access receipt before each native file is read. It saves native bytes, normalized observations and conversion audits, retaining all ten planned statuses and failures. A source mismatch is retained as a failed attempt, not converted as a valid source. `cohort.json` appears only if all ten conversions succeed; its relative observation paths and intervals describe conversion output. It explicitly has `evaluation_enabled: false`, and is not an M3 external registry. `aggregate.json` contains technical counts without individual records.

`human-verify` records a new read in its own fresh output directory before hashing and replaying the conversion bundle. It rechecks source identities, code, policy, access history, roster, native-to-normalized conversion and artifact membership. It needs neither original source paths nor a model or live old ledger. Its fresh output retains success/failure state and the reconstruction aggregate. Replacing every source and trusted hash remains outside the local consistency guarantee.

The parser's legacy `release_files_verified: false` does not assert that no local audit occurred. Source identities are verified by the human service; this flag makes no blanket claim about all release contents, sensor semantics or actual online availability.

## Next gate

The authorized run on 20 September 2026 converted all ten bound native exports and passed a separate private reconstruction. The [source assessment](research/physiocgm-source-assessment.md#completed-bounded-human-conversion) identifies the private acceptance record and its limits. The full repository checks passed 259 tests, including 18 invented-data tests for the human route; this is separate from the actual-file conversion evidence.

Human conversion adopts the [full-export period and explicit assumptions](research/physiocgm-conversion-protocol.md). The [external forecast protocol](research/m3-external-protocol.md) still rejects human inputs. Its eventual bridge must bind verified conversion evidence, the complete cohort, prior access and the unchanged model to a separate evaluation freeze. Conversion success alone is not predictive evidence, and these commands authorize no new acquisition or data publication.
