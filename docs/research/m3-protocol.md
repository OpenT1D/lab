# M3/1 — Causal CGM forecast assessment

Version 1.0, specified 19 September 2026 before fitting or evaluation. **Provisional human protocol; executable synthetic software specification.** OT-016/OT-017 are its roadmap work packages. OT-001, OT-014 and IV-001 are unchanged. [Feasibility](m3-data-feasibility.md) owns sources, rights and dataset selection; [decision 0007](../decisions/0007-m3-causal-forecast.md) owns the bounded architecture.

## Question and permitted conclusions

During later observed-care periods of the six original OhioT1DM adults, how does a prespecified CGM-only ridge predictor compare with persistence at 30 minutes? Measure errors, coverage and failure conditions; a worse ridge result can complete this question. Thirty minutes is six nominal sensor intervals and a bounded short-term forecasting question, not an established clinical decision horizon.

Reconstruction uses information from the period being described. Prediction uses only information available at the forecast origin. Intervention replay changes input and needs separate counterfactual evidence. Only prediction is assessed here. No dosing, clinical benefit, unseen-person generalization, physiological identification or alternative-controller effect is claimed.

## Data and execution gate

Conditional source: direct OhioT1DM distribution, original 2018 cohort, six participants' provider training/testing files. Exact current archive, license, dictionary, hashes and usable cohort are **pending**, not invented. No aggregate copies. Additional 2020 participants remain reserved and unopened; a later B1 question may need new material if these do not supply necessary physiology/inputs.

A human freeze requires authorized access, native-format verification, rights for processing and retaining derived artifacts, a reviewed identity/overlap map, and explicit sensor/timestamp/availability semantics. Preserve original and normalized meanings and actual consumed-byte hashes. Execution must reject absent provenance or changed bytes. A local attestation records a responsible person's review; it does not create legal permission. The public fixture freeze must say synthetic and cannot satisfy this human gate.

## Model and information

Model: scikit-learn `Ridge(alpha=1.0, fit_intercept=True, solver="svd")` after `StandardScaler`. Pin the concrete package and full runtime lock before execution; record actual installed versions. This standard statistical model is not an OpenT1D physiological engine. Reference: persistence, forecast equal to the latest eligible CGM value. No clipping of forecasts or retrospective target correction.

Six features in chronological order: CGM at origin minus 25, 20, 15, 10, 5 and 0 minutes. Target: CGM at origin plus 30 minutes. Point values in mg/dL; mmol/L conversion, when explicitly supplied, uses 18 mg/dL per mmol/L as the declared reporting convention. Require exact five-minute feature and target positions after verified time normalization. Irregular off-grid records remain accounted for, not interpolated or rounded. No insulin, meals, future annotations, future glucose, finger sticks or latent physiology enter features.

Require recorded availability no later than origin for all features. Where a release has only measurement timestamps, a human freeze must explicitly attest the assumption that these approximate availability; results are retrospective forecasts under that assumption, not verified online performance. Device clock shifts split segments; timezone-unknown local times are never relabeled UTC. No cross-segment history.

Fit one shared scaler and ridge on development windows only, with equal total training weight per person. The six correlated coefficients are regularized predictive associations, not identifiable biological parameters. Record feature rank and singular values as diagnostics, not proof of physiological identifiability. No patient-specific parameter fit, physiological state estimate, sensor fitting, hyperparameter search or structural modification. Initialization is solely the six observed features. Every window/person is stateless after the shared model is frozen.

## Splits and freeze

Use provider training/testing membership, not random timestamp splits. For each participant, split the training file by elapsed time: first 80% development, last 20% validation. Require all history and the target to lie in their own block. The final test file is evaluation; exclude origins in its first 60 minutes and require its history and targets within that file. This purges boundary-spanning windows; validation and test never supply training targets or scaling statistics. Reject training/testing overlap, repeated source persons disguised as different IDs and windows spanning clock segments.

The same people occur in all three phases by design: this tests later periods of known people, not new people. Report repeated observations within each person. Freeze source, protocol, data/rights/identity registry, split boundaries, window policy, model configuration and runtime locks before fitting. Fit on development, report validation diagnostically without tuning, then freeze the learned coefficients/scaler and exact development/validation artifact identities **before reading evaluation values**. Evaluation files may be byte-hashed by a custodian at intake; hashing is not fitting. Do not load evaluation values in the fit process. No automatic refit on development plus validation.

Any inspection of evaluation makes it known material. Persist an evaluation-access marker before reading it. Corrections preserve prior artifacts and explicitly record reuse. Filesystem controls and the responsible researcher, not a hash alone, enforce blinding. New-person assessment requires a separately frozen participant/study split and linkage audit; M3/1 does not make that claim.

## Preprocessing and coverage

Keep measured, missing, invalid, censored-low and censored-high categories separate. Censored values are bounds, never exact boundary measurements. No interpolation, carry-forward imputation, zero meals or inferred absent insulin. Invalid input types (including bool, numeric strings, null for required numbers, NaN, infinity and exponent overflow) are rejected by the normalized contract. Native textual numeric fields require explicit parsing before that contract.

Every scheduled five-minute origin in each declared block remains in the denominator, even when its history or target is absent. Retain exclusions by reason and origin, with separate prediction availability and score availability. A missing future target must not suppress a forecast that was possible at origin. Censoring yields a one-sided absolute-error lower bound only; it does not contribute to ordinary MAE/RMSE. Unknown censor thresholds cannot yield that bound.

Record supplemental insulin/meal provenance if present but never use it as a predictor in this question. Represent basal commands and recorded delivery separately, bolus amounts separately from rates, and interval durations explicitly. A missing stream has unknown coverage; integrating known basal commands does not establish delivery.

## Outcomes and uncertainty

Metric version `m3-cgm-forecast/1`. Primary: equal-person mean of each person's MAE difference (ridge minus persistence), on identical measured-target windows with both forecasts. Negative means lower ridge MAE. Also report each predictor's own coverage and all exclusions, so common-window selection cannot hide failures.

Secondary: equal-person MAE and RMSE, bias, per-person errors, and errors by **origin** glucose below 70, 70–180 inclusive and above 180 mg/dL. These strata use available information, not future outcome selection. Report target categories, censored error lower bounds and insufficient-history/gap exclusions. They are CGM prediction errors, not physiological time-in-range or clinical accuracy scores.

For the primary paired difference, resample whole participants with replacement (2,000 draws, seed 301); report the empirical 2.5%/97.5% order-statistic interval and all individual differences. Do not resample timestamps as independent people. Six participants support only a fragile descriptive interval; it is not a powered population claim. If fewer than two participants contribute paired errors, the interval is undefined. No significance or superiority threshold is prespecified; report direction and uncertainty without promoting a favorable mean to clinical benefit.

Point forecast errors are not duration-weighted exposure. Any auxiliary rate total or availability-duration summary uses actual interval lengths with half-open intervals and no extrapolated last interval. Check independent irregular-interval examples. Never describe an event-count average as time exposure.

## Minimum evidence, failure and interpretation

Software mechanics may use shorter synthetic blocks. A human analysis needs all six participants accounted for, at least one complete day of eligible development origins and one complete day of eligible evaluation origins per contributing participant, and at least two contributing participants for the paired descriptive aggregate. Report participants below these requirements and label the planned six-person evaluation inconclusive if any is absent or insufficient. These are operational coverage floors, not power calculations or numerical model-accuracy thresholds. Report observed percentage coverage regardless of the floor.

Save the full schedule before running. Use exclusive new output paths, bounded subprocesses and durable per-window checkpoints. Preserve setup failure, primary errors even if diagnostics fail, partial traces, timeout, cancellation and not-attempted windows. A study cannot be completed when a planned case failed or was unattempted. Excluded observations are accounted-for scientific missingness, not silently successful predictions. Reconstruct reports from frozen metadata, saved forecasts/targets and statuses without importing the estimator or any simulator.

Acceptance requires checked amount/time/type examples, causal and split leakage tests, native estimator equivalence, reset/isolation, freeze/tamper rejection, failure lifecycle tests, full denominator accounting and exact saved-report reconstruction. Preserve M0/M1/M2/IV-001 regressions and the setuptools advisory. Synthetic scores verify mechanics only. Human evaluation remains open until actually authorized and executed on the verified release. No human result, stable API, new controller, physiological extension or release is implied.

## Deviations

Version 1.0 is the initial specification. Record later amendments before their affected fitting/evaluation, including why, what was already inspected, and whether an evaluation is reused. A synthetic implementation correction is not permission to tune human evaluation rules.
