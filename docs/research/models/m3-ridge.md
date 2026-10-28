# M3 Ridge forecast model card

Status: existing estimator integrated for the synthetic [M3/1 workflow](../../m3-tutorial.md). Human predictive accuracy remains unmeasured. This is statistical CGM forecasting, not a new physiological model or an insulin controller.

## Identity and reuse

Use scikit-learn 1.7.2 `StandardScaler` and `Ridge`, pinned with NumPy 2.2.6, SciPy 1.15.3 and transitive dependencies in `experiments/m3/runtime/uv.lock`. Upstream code is installed separately, not vendored or modified. scikit-learn's [tagged license](https://github.com/scikit-learn/scikit-learn/blob/1.7.2/COPYING) is BSD-3-Clause; dependencies retain their own terms. OpenT1D adds the data boundary, temporal evaluation and artifact workflow, not the estimator equations. Source documentation and native-reference test evidence are retained locally.

GluPredKit's pinned Ridge/parser implementation was inspected as a reuse candidate; this integration calls the underlying estimator directly and does not reproduce that project's resampling, grouping or grid-search workflow. The [data assessment](../m3-data-feasibility.md) explains that choice and the exclusion of unsupported physiological engines.

## Inputs, fitting and prediction

Six measured CGM point values at five-minute spacing, from origin minus 25 minutes through origin, predict CGM at origin plus 30 minutes. No body weight, insulin, meals, finger sticks, future observations or latent state. Shared development-only weighted scaling and regression give each person's complete development windows total weight one. Alpha is fixed at the standard value 1.0; the SVD solver avoids selecting a tolerance-dependent iterative solver. No hyperparameter search or patient-specific calibration is performed.

Store means, scales, six coefficients and intercept as finite JSON numbers. Reconstruct each forecast from those values without unpickling objects or importing scikit-learn. Record feature rank and singular values: correlated lag coefficients describe regularized predictive associations, not identifiable physiology. No clipping of negative or extreme forecasts. Nonfinite prediction or error arithmetic fails visibly.

Persistence returns the most recent eligible measurement under the same complete-history policy for the paired comparison. The full report retains unavailable windows and each predictor's coverage. Both methods predict observed CGM, including its measurement limitations; neither output is a direct plasma-glucose estimate.

## Evidence and limitations

Native tests compare fitting with independent direct calls to the pinned estimator and check equal-person scaling, repeatability and saved-coefficient forecasts. Changing validation observations leaves fitting unchanged; fitting still runs with all evaluation files absent. The artifact suite checks explicit causal histories, split boundaries, strict signal categories, failed runs, byte identity and simulator-free reconstruction. See the [M3 evidence record](../m3-reproduction.md) for executed commits and results.

Scalar saved-coefficient accumulation and native BLAS may differ by floating-point rounding. The native test compares these using a stated operation-count rounding budget; this is unrelated to a clinical performance threshold. Full saved-report reconstruction remains exact. Runtime versions/platforms are recorded; no cross-platform bitwise fitting guarantee is made.

The selected human question concerns later periods of the same six people. Generalization, sensor bias, unrecorded treatment changes, uncertain availability timing and six-person uncertainty remain limitations. Neither good prediction under observed care nor a low synthetic error establishes a counterfactual treatment effect or a biological improvement. The initial maintainer owns this experimental integration; there is no stable API or released prediction package.
