# AZT1D-M3/0.1 — Causal CGM forecast assessment

Specified 20 September 2026, after bounded source intake and before human model fitting or forecast evaluation. **Conditional human protocol and software specification; not an executable human-data freeze or a result.** [Decision 0008](../decisions/0008-azt1d-causal-forecast.md) records the separate AZT1D workflow. The existing OhioT1DM [M3/1 protocol](m3-protocol.md), its artifacts and decision 0007 remain unchanged.

The separate workflow implements conversion, frozen development fitting, diagnostic validation, evaluation-access logging and artifact reconstruction. Its checks use synthetic observations. The requirements below define the conditional human experiment; implemented software is not evidence of human predictive performance.

## Question and scope

During later observed-care periods of the same AZT1D participants, how does a prespecified shared Ridge predictor compare with persistence for CGM 30 minutes ahead? Report error, coverage and failures. A negative result can answer the question. This is retrospective prediction under the treatment actually given, not assessment of an alternative controller's effects.

The observations and target are CGM point values in mg/dL, not plasma glucose. The six past readings are the entire predictor input. This protocol cannot establish unseen-person generalization, physiological parameter identification, clinical benefit or dosing safety. It neither connects simglucose or Cambridge to actual people nor develops an original controller or physiological engine. A later B1 or controller question needs a separate protocol and suitable inputs and observations.

## Source, assignment and private provenance

Use the original [AZT1D version 1](https://data.mendeley.com/datasets/gk9m674wcx/1), DOI [10.17632/gk9m674wcx.1](https://doi.org/10.17632/gk9m674wcx.1), published 27 May 2025. The owner's metadata describes 25 people with T1D using automated insulin delivery, approximately six to eight weeks each, and a CC BY 4.0 license; checked 20 September 2026. These are release-level descriptions, not a claim that every released file provides every advertised variable or equal usable coverage.

The planned allocation is 20 study participants and five reserved participants. Bind the workflow to the assignment already recorded in the private intake manifest; do not redraw it after examining glucose or replace an unsuitable study participant with a reserved one. All 20 study participants remain in the accounting, including unsupported sources and participants without sufficient usable windows. Source participant codes alone do not prove that distinct files represent distinct people: record the identity and overlap review and remaining uncertainty.

The reserve is material from the same study, not an independent external dataset or an established B1 resource. Do not normalize, inspect, fit on or evaluate reserved participant records in this workflow. Later use requires a separate question, rights review and freeze. Copying known material to a reserve directory does not restore blinding.

Bind source files to their exact authorized local byte hashes, the release identity, the allocation and the private intake record. A DOI identifies a release but does not replace a byte inventory. Record processing, retention, publication and redistribution rights separately, including unresolved rights for individual derived records or learned artifacts. CC BY attribution obligations and privacy responsibilities remain relevant. An attestation documents a review; it does not create permission.

Human source records, individual predictions and errors, participant identities, lineage and private provenance remain outside Git, public CI, chat and public reports. Public examples use self-authored synthetic fixtures. This document contains the planned design, not private participant identifiers, intake findings, source paths or observed cohort counts.

## Time and phase boundaries

Preserve native timestamps and source order in private provenance. Do not relabel timezone-unknown local times as UTC or infer a timezone from the recruiting institution. Use relative elapsed time; the normalized interface represents elapsed timestamps and availability as integer microseconds (`time_us` and `available_us`). Reject unparseable or backward source clocks pending an explicit correction or segmentation policy. Sorting must not conceal a clock reversal.

For each study participant, the declared span starts at the first registered timestamp and ends 300 seconds after the last timestamp. This final offset defines an administrative boundary; it is not a final observation or an assertion of continuous coverage. Partition the span by elapsed time into 60% development, 20% validation and 20% evaluation. Use exact half-open intervals; a timestamp exactly on a boundary belongs to the next phase. Duplicate timestamps have the same phase membership. Preserve the already assigned boundaries in the private manifest rather than recalculating them after exclusions.

All six history positions must be inside their origin's phase and supported clock segment. A scored target must be inside that phase and the same segment. The first 60 minutes of evaluation origins are warm-up exclusions, retained in the denominator. No history crosses a split or clock discontinuity. If a verified clock correction changes boundaries or membership, version the amendment before fitting and preserve the prior manifest.

The same participants intentionally appear in all three phases. This assesses later periods of known people. The partition does not constitute a participant holdout, and the five-person reserve does not by itself establish external validity.

## Glucose semantics and normalization

The native importer must preserve the following distinctions before any human execution freeze:

- A source column explicitly named `CGM` is the candidate CGM stream. Its unit, status conventions, availability and bounds still require verification.
- A source column named `Readings (CGM / BGM)` is unsupported as a CGM stream until its measurement semantics are established. Do not silently rename it, infer a modality from cadence or score mixed readings as CGM. Keep the participant and registered origins in accounting.
- Parse textual numeric fields explicitly. At an identical timestamp, numerically equal CGM values collapse to one observation with lineage to every contributing source row. This does not authorize aggregation of meals, insulin or other events.
- Different numeric glucose values at one timestamp make that timestamp ambiguous. Do not average, select the first or last value, or choose by plausibility. Preserve the conflict and its lineage; it cannot supply an exact feature or target.
- Preserve missing, invalid, ambiguous and censored meanings. No interpolation, carry-forward filling, timestamp rounding or conversion of absent meals or insulin to zero is permitted. The normalized contract rejects nonfinite numbers and malformed required types.

Numerical positivity does not establish that a glucose value is an uncensored measurement. Before human fitting, freeze a referenced policy for sensor status, sentinel values and numerical boundaries. Either verify that the relevant values represent exact measurements, or use a conservative exclusion rule at and outside documented bounds. Do not guess automatic 40/400 mg/dL thresholds or interpret an undocumented boundary value as exact. Known censored values remain bounds and do not enter ordinary MAE or RMSE; a one-sided absolute-error lower bound is possible only with a verified bound. Unresolved status semantics block the human freeze.

A measurement must have been available by the forecast origin to supply a feature. Where the source does not provide independent availability timestamps, explicitly record the assumption that measurement time approximates availability. Results then concern retrospective forecasts under that assumption, not demonstrated online performance. Target availability must also satisfy the development cutoff before the target can enter fitting. Missing insulin and meal context does not prevent this narrowly specified CGM-only experiment, but limits physiological interpretation.

## Origins, windows and coverage

Unlike Ohio M3/1's nominal five-minute schedule, an AZT1D origin is **each unique registered timestamp within a declared phase**. Include registered timestamps whose glucose is missing, ambiguous, invalid or unsupported. Collapse equal-time source rows only for origin counting; preserve their lineage. Do not round the origin to a nominal grid.

The ordered features are measured, unambiguous CGM at exactly `t−25`, `t−20`, `t−15`, `t−10`, `t−5` and `t` minutes. The target is CGM at exactly `t+30` minutes. There is no matching tolerance or nearest-neighbor search. A future target's absence or unsuitability must not suppress a forecast otherwise possible at origin. Save prediction availability and scoring eligibility separately, including targets outside the phase, missing targets and ambiguous targets.

The denominator is registered origins, not every possible five-minute position in elapsed time. Report registered timestamp density, interval distribution, long gaps and elapsed span alongside prediction and scoring counts. A high fraction of eligible registered origins is not evidence of continuous clinical coverage. An auxiliary nominal-grid availability summary may describe gaps, but must not create observations or enter this experiment's denominator.

Strict exact-position requirements may leave little usable data. That is a feasibility result, not permission to tune a tolerance after seeing evaluation coverage. A tolerant or interpolated method needs its own amended protocol, development justification and untouched evaluation material.

## Estimator and development eligibility

Use scikit-learn `StandardScaler` followed by `Ridge(alpha=1.0, fit_intercept=True, solver="svd")`. Fit a single shared scaler and model using development windows only. Persistence predicts the latest eligible CGM value. Neither predictor clips its output. Pin the actual runtime lock, package versions, source/configuration hashes and model settings before execution.

A participant qualifies for fitting only from their development data: at least 288 valid development windows whose origins span at least 24 hours. Do not let later validation or evaluation availability select the training cohort. Record unqualified or unsupported participants and their reasons; do not replace them with reserved people. If no participant qualifies, preserve the setup failure rather than fitting a substitute model.

For qualifying participant `i` with `n_i` development windows, assign each window weight `1 / n_i`. Pass these same weights to both the scaler and Ridge. Every contributing participant therefore has total weight one; preserve this absolute weight convention because its scale affects Ridge regularization. A participant with more readings does not receive more total training weight.

Validation is diagnostic only. No hyperparameter search, participant-specific fit, clipping calibration, additional channels, validation-based feature selection or refitting on development plus validation is allowed. Correlated regression coefficients are predictive associations, not physiological parameters. Record rank and singular values as diagnostics without claiming biological identifiability. Each forecast is stateless after the shared model is frozen.

## Freeze and access separation

The source/allocation/split freeze precedes fitting. Record source identity and byte hashes, rights review, overlap review, normalized contract and policy identities, exact phase boundaries, supported modalities, status/boundary policy, availability assumption, window rules, estimator settings and runtime locks. The workflow namespace is `experiments.m3.azt1d`, with normalized schema `opent1d.m3.azt1d/1`, protocol `AZT1D-M3/0.1` and metric `azt1d-cgm-forecast/1`. These identities keep the AZT1D conventions separate from historical Ohio artifacts.

Use separate development, validation and evaluation descriptors. The fitting process must not load evaluation values. Maintain a persistent external access ledger bound to the source, allocation and split identity. Record an evaluation-access event **before evaluation normalization as well as before evaluation execution**; an apparently preparatory import must not invisibly consume the holdout. Byte hashing by a custodian is distinct from inspecting measurement values.

After development fitting and diagnostic validation, freeze the learned scaler and coefficients together with the exact development/validation artifact identities before evaluation values are made available to the execution process. Actual prior inspection remains disclosed: a freeze or directory copy cannot make inspected values unseen. Preserve the bounded intake's access history and state precisely which evaluation material was already known. Any later correction retains previous artifacts and records holdout reuse.

Human fitting and evaluation require completed scientific and provenance gates plus explicit authorization to process the relevant records. A synthetic run cannot satisfy those gates. This specification does not itself authorize a download, access application, new data collection or human evaluation. Until the actual implementation and the private freeze satisfy these conditions, human execution remains blocked; software checks demonstrate only the paths exercised with fixtures.

## Outcomes and uncertainty

Primary outcome: each participant's MAE difference, Ridge minus persistence, on identical measured-target origins with both forecasts, followed by an equal-person mean of those differences. Negative values favor Ridge for this forecast task. Report each predictor's separate prediction and scoring coverage and all excluded origins; common-window comparison must not conceal failures.

Secondary outcomes are equal-person MAE, RMSE and bias, private per-person errors, and errors grouped by **origin** glucose below 70, 70–180 inclusive, or above 180 mg/dL. Report target categories, known censored-error lower bounds and exclusion reasons. These are forecast errors, not physiological time-in-range, clinical accuracy or treatment effects. Event-count summaries are not duration-weighted exposure. Any separate duration summary uses actual interval lengths and does not extrapolate a final observation.

For the primary paired difference, bootstrap whole contributing participants with replacement, 2,000 draws with seed 301, and report the empirical 2.5% and 97.5% order-statistic limits. Repeated timestamps are not independent people. Fewer than two contributing participants make this descriptive interval undefined. No powered population, statistical superiority or clinical-benefit threshold is specified.

A participant contributes to the final paired aggregate only with the development floor above and at least 288 jointly scored evaluation windows whose origins span at least 24 hours. Keep all planned participants in the report regardless of contribution. If any planned participant is unsupported, absent or below the relevant floor, label the full planned cohort incomplete and report any permitted partial analysis explicitly. These are operational feasibility floors, not sample-size or accuracy claims. Evaluation eligibility changes reporting, never the already frozen model.

## Failure preservation and acceptance

Save the complete registered-origin schedule before prediction, use new output locations, preserve per-origin eligibility and outcomes, and retain setup failures, partial traces, cancellation, timeout and unattempted work. A failed or unattempted planned case cannot be described as a completed cohort. Scientific exclusions are accounted-for missingness, not successful forecasts. Reconstruct reports from frozen metadata and saved forecasts, targets and statuses without importing an estimator or simulator.

Synthetic preparation acceptance needs meaningful checks for equal and conflicting duplicates with lineage, unsupported mixed modality, exact elapsed splits and event offsets, clock segments, boundary/status policy, causal availability, target-independent prediction eligibility, evaluation-access gates and tamper rejection. The study implementation must gate human evaluation conversion on a verified learned freeze and a durable access ledger; direct conversion remains refused. Execution acceptance additionally requires access-ledger persistence, equal-person fitting, training/evaluation separation, saved target-independent forecasts, failure accounting and exact reconstruction. Preserve historical Ohio and simulation behavior. Test results belong in an implementation acceptance record; this protocol is not evidence that a check or human evaluation has run.

## Amendments

Version 0.1 is specified after source intake and before fitting or human forecast evaluation. Preserve the distinction between already inspected intake information and unseen assessment material. Amendments must state their reason, changed rules, inspected material and affected artifact identities before the affected fitting or evaluation. Do not reinterpret older artifacts under a new policy, silently change the existing Ohio protocol, or use a software correction as permission to tune on human evaluation results.
