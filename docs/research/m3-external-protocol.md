# M3-EXTERNAL/0.1 — Frozen-model external CGM forecasts

Specified 20 September 2026. **Synthetic software preparation; human external intake is not implemented.** [Decision 0010](../decisions/0010-external-frozen-forecast.md) records the separate workflow. The [tutorial](../m3-external-tutorial.md) describes its commands. Existing Ohio and AZT1D protocols remain unchanged.

## Question and current scope

The intended human question is whether a previously frozen shared Ridge predictor transfers to people in an independent study, compared with persistence for CGM 30 minutes ahead, without refitting. The present implementation exercises that question's software mechanics with invented donor and external observations only. It does not establish that two actual human cohorts are independent or that any provider's release is supported.

Inputs and targets are CGM in mg/dL. Prediction uses six past CGM values under observed treatment. Good forecasts would not identify insulin-response mechanisms, validate a physiological engine or show what another controller would have caused. No human performance, statistical superiority, clinical benefit or dosing-safety claim follows from this preparation.

## Frozen donor model

Use a completed AZT1D learned freeze containing the existing shared `StandardScaler` and `Ridge(alpha=1.0, fit_intercept=True, solver="svd")`. Export verifies the original plan, learned artifacts, retained development/validation inputs and access history through the source workflow. It does not train another model or recompute the original regression fit.

The portable bundle contains unchanged `model.json` and `freeze.json`, an `origin.json` attestation and a `bundle.json` hash inventory. It binds the original plan, registry, study identity, model provenance and training aliases. No development observations, validation predictions or validation scores are copied. The external plan pins the bundle identity; all external predictions use those same scaler parameters and coefficients.

Export requires a checkout compatible with the original source fingerprints. Subsequent bundle loading checks its model contract, hashes and attested origin without reading the donor's original data or live ledger. It does not independently prove the training procedure or guard against an actor replacing every artifact and trusted hash. Original training package versions remain checked against the supported runtime lock; portability is bounded by this model contract, not guaranteed for arbitrary future estimators or runtimes.

The external workflow has no fitting endpoint. It must not fit a scaler, tune features or regularization, personalize coefficients, calibrate on external labels or clip forecasts. Persistence uses the latest eligible CGM reading. Synthetic donor fitting is permitted solely to construct the fixture used to check the export and transfer mechanics.

## Source and roster freeze

The workflow identities are schema `opent1d.m3.external/1`, protocol `M3-EXTERNAL/0.1` and metric `external-cgm-forecast/1`. Input format `normalized-cgm/1` uses the existing `opent1d.m3.azt1d/1` observation-document structure as an internal representation; that reuse does not turn external observations into AZT1D data.

The registry declares the source reference and format, an absolute ledger path, reviewed prior-access disclosure and every planned participant. Each participant has a local alias, absolute observation path and SHA-256, half-open elapsed-time bounds and a sorted unique list of all registered origins. There is no development or validation partition in this external cohort.

Freeze validates metadata and the model bundle without reading external observations. The plan binds the canonical JSON representation of the registry, rather than its original whitespace or key order. Missing or unusable observation files may therefore fail later, and must remain in the frozen cohort. Reject duplicate participant aliases, lexical input paths and input hashes, plus exact alias or byte-identity overlap with the donor source inventory. Lexical path comparison does not inspect files or prove that different paths have different filesystem targets. These checks cannot establish biological independence: re-encoding the same person's observations changes file hashes, and aliases are local labels. Actual human source/study/participant overlap would require a separate substantive review.

The initial registry requires `kind: synthetic` and `prior_access.status: present`, with a reference explaining generation or conversion of the normalized inputs. A supplied Boolean review statement cannot enable human execution. A candidate source such as PhysioCGM remains unverified for this route until its original release and native adapter have been assessed; no provider-specific schema is inferred from a publication.

## Causal time and measurement contract

Preserve integer microsecond elapsed timestamps, availability times, clock segments, raw timestamp lineage and source-row references. The internal representation declares `local_elapsed` and mg/dL. It does not infer a timezone, convert local times to UTC or establish native sensor semantics.

At each registered origin `t`, the ordered features are measured, unambiguous CGM at exactly `t−25`, `t−20`, `t−15`, `t−10`, `t−5` and `t` minutes. Every feature must be within the declared interval, available by `t` and in one clock segment. The first 60 minutes of origins are retained as warm-up exclusions. The target is the reading at exactly `t+30` minutes within the same interval and clock segment.

There is no timestamp tolerance, nearest-neighbor search, interpolation, carry-forward filling or rounding. This preserves the frozen donor's input convention. A future target's availability for scoring must not decide whether a causal forecast is produced. Missing, invalid, ambiguous, unsupported and known censored observations remain distinct. Only measured point targets enter ordinary MAE/RMSE; verified censor bounds may support descriptive one-sided error lower bounds.

Every registered origin stays in the denominator, including origins with unusable glucose or history. Prediction coverage and scoring coverage are separate. The denominator describes registered observations, not all possible five-minute positions or the fraction of elapsed time observed. The declaration of availability is an input assumption; synthetic fixtures cannot establish real online availability.

## Access and supervised execution

After the metadata freeze, explicitly initialize a durable access ledger. Before opening each normalized observation file, append a source/cohort/plan-bound access event and retain its receipt. After input validation, append a separate event before supervised worker execution. Direct workers must verify these same gates and create an exclusive claim for that execution receipt before reading observations. A second invocation cannot reuse the same claim. A failed ledger operation authorizes no corresponding read.

The shared ledger calls the first event `before_normalization`; in this route it means before reading and validating material that has already been normalized. Its prior generation/conversion is disclosed and is not made unseen by freezing the file. Repeated runs append access history rather than replacing it. A ledger snapshot verifies the saved history, not the absence of later live access or manipulation of all local receipts.

Use a fresh output directory for each attempt. Retain the complete planned roster and schedules, model bundle, input snapshots, access receipts, causal traces, worker state, elapsed execution time and errors. Worker deadlines and interruption preserve the completed trace prefix; unfinished origins remain unattempted. Changing a deadline cannot change the scientific rules or justify an undisclosed re-evaluation.

## Outcomes and participant accounting

The primary outcome is the equal-person mean of each contributing person's paired MAE difference, Ridge minus persistence. Negative values favor Ridge for the declared forecast task. An external participant contributes only after completed execution with at least 288 jointly scored origins spanning at least 24 hours. These are operational coverage floors, not a power calculation or an accuracy standard. There is no development-eligibility condition and the external outcome never changes the frozen model.

Report every planned participant, execution status, exclusions, prediction/scoring counts and coverage. Any planned person not contributing makes the planned external cohort incomplete; a partial aggregate must be labeled accordingly. Secondary summaries include equal-person MAE, RMSE and bias, and errors by glucose at the forecast origin: below 70, 70–180 inclusive, above 180 mg/dL or unknown. These are prediction strata, not duration-weighted clinical exposure or treatment outcomes.

Resample whole contributing people with replacement, 2,000 draws with seed 301, to obtain the descriptive empirical 95% interval for the mean paired difference. Use the 50th and 1,950th one-based order statistics. Fewer than two contributing people leave this interval undefined. Correlated timestamps are not independent subjects.

## Reconstruction and evidence boundary

Reconstruct the report with the standard library from saved artifacts, without original source files, donor fit folders, the live ledger, scikit-learn or a simulator. Validate the frozen rules and model identity, artifact inventory, source/schedule identity, saved access history, exclusive worker claims and exact forecast arithmetic. Retain failures, unattempted participants and valid prefixes from interrupted traces. Check the original failure type for failed or interrupted work and the finite, nonnegative elapsed execution time of saved runs. Reject changed artifacts and invalid completed traces rather than silently repairing them.

Synthetic acceptance should exercise export identity, absence of refitting, metadata-only freeze, causal history and target-independent forecasts, exact timestamp matching, access ordering, repeat access, failure preservation, tampering and offline reconstruction. Passing checks demonstrates only these software mechanics. It is not independent human reproduction or evidence of performance on an external population.

Before human use, implement and verify a release-specific native adapter; review rights for processing, derived retention and learned artifacts; resolve units, sensor/status meaning, clocks, availability, lineage and participant overlap; disclose prior access; freeze the actual cohort and model; and obtain explicit authorization for the concrete acquisition and processing. Keep all health records and individual derived material private, outside Git and public services. This protocol itself authorizes none of those external actions.

Any change to matching tolerance, model, eligibility or scientific scope requires a separately versioned amendment recording its reason and already inspected material. Preserve earlier artifacts and historical protocol meanings. Known evaluation material cannot become an untouched test set through another directory, label or ledger.
