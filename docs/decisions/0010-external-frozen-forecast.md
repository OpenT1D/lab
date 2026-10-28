# 0010 — External evaluation of a frozen forecast model

Status: accepted for synthetic software preparation, 20 September 2026. Human external input is unsupported pending a reviewed native adapter and release-specific intake.

## Context

Evaluation in later periods of the people used for development answers a different question from transfer to people in an independent study. The [AZT1D workflow](../research/m3-azt1d-protocol.md) supplies a learned scaler and Ridge model, causal CGM windows and reconstructible artifacts. Its development qualification and same-person interpretation cannot simply be reused as external-study eligibility.

An external route must consume an already frozen model, preserve failures and disclose earlier access to its assessment material. Preparing that route with invented observations does not verify a candidate provider's actual release format.

## Decision

Add the separate `experiments.m3.external` namespace, schema `opent1d.m3.external/1`, protocol [M3-EXTERNAL/0.1](../research/m3-external-protocol.md) and metric `external-cgm-forecast/1`. Preserve the historical Ohio and AZT1D protocols and their artifact meanings.

Export the existing learned model only after the AZT1D workflow verifies the original plan, fit, retained inputs and access history. The portable bundle preserves the model bytes, learned freeze, origin attestation and file hashes. It excludes development observations and validation traces. Loading it for external prediction does not require those original observations or execute fitting. Portable verification checks the bundle and its attested origin; it is not an independent reproduction of training or a signature from an external authority.

Freeze the complete external participant roster, input hashes, registered origins, interval bounds, prior-access disclosure and model identity without opening external observation files. Reuse the exact six-history-value, 30-minute-ahead prediction contract, including the 60-minute warm-up. Do not introduce tolerance, interpolation, clipping, personalization or any scaler/model refit.

Define external reporting eligibility separately: complete execution and at least 288 paired scored origins spanning at least 24 hours. An external participant has no development-eligibility flag. Retain every planned participant, including failures and insufficient data, and label an incomplete cohort explicitly. Weight contributing participants equally and resample people for descriptive uncertainty.

Use a durable ledger before accepting normalized inputs and before worker execution. Existing normalized material necessarily has a generation or conversion history; disclose that earlier access. The reused ledger event name `before_normalization` denotes the forthcoming read and validation of already normalized input here, not first access to its native source.

The initial route accepts self-authored synthetic normalized observations only. Human input is refused even when review flags are supplied. A later native provider adapter needs verified units, status semantics, clocks, cadence, lineage, rights, overlap and actual-file checks, followed by its own explicit authorization and freeze.

## Consequences

The [tutorial](../m3-external-tutorial.md) provides a bounded way to exercise model transfer without acquiring patient records or evaluating a private human model. Synthetic checks can establish arithmetic, failure accounting, access gates and reconstruction; they cannot establish generalization, physiological validity, controller benefit or clinical safety.

Technical portability does not grant redistribution rights. A human model bundle would still contain learned parameters, participant aliases and private provenance and must remain protected. A local ledger and hashes provide auditable consistency, not proof against replacement of every artifact and receipt.

Changing timing tolerance, model settings, inclusion criteria or the scientific question requires a versioned amendment and disclosed prior access. A new output directory cannot make inspected evaluation material unseen.
