# AZT1D workflow implementation acceptance

Recorded 20 September 2026. This record concerns self-authored synthetic data and software mechanics under [AZT1D-M3/0.1](m3-azt1d-protocol.md). No patient record was opened, converted, fitted or evaluated during this implementation step. The existing Ohio workflow and its protocol were retained.

## Implemented behavior

The separate `experiments.m3.azt1d` namespace now supplies phase-bound conversion, a metadata-only study freeze, explicit access-ledger initialization, isolated development fitting, diagnostic validation, a learned-model freeze, supervised evaluation and standard-library reconstruction. The [tutorial](../m3-azt1d-tutorial.md) provides the executable commands and private registry contract.

Development eligibility is assessed before fitting; both the scaler and fixed Ridge receive the existing equal-person sample weights. Every planned participant remains in the evaluation accounting, including unsupported streams and insufficient observations. Complete registered schedules, predictions, target status, exclusions, failure state and partial traces are retained. Paired errors and uncertainty use people as the aggregation and bootstrap units.

Each evaluation attempt records source/split/model-bound access before normalization and execution. The ledger preserves repeated access and rejects new fitting after recorded evaluation access. Direct worker entrypoints also check the relevant phase, learned artifacts, access evidence and private output boundary before opening glucose. An invalid deadline is rejected before evaluation access. Human input conversion still requires the reviewed source, authorization, retention and scientific assumptions.

## Verification performed

The locked tooling and estimator environments were synchronized. Repository checks, the native study tests and the independent verification command were executed locally. The bounded synthetic study produced `verification.json` with `complete_workflow`, `independent_reconstruction` and `kind: synthetic`; it explicitly records `human_evaluation: false`. Generated examples and full artifacts remain in ignored local results, not version control.

| Check | Evidence and result |
|---|---|
| Importer and causal time rules | Synthetic tests exercise exact microseconds, equal/conflicting duplicates, missing/unsupported readings, policy boundaries and future-value poisoning. |
| Gates before data access | Tests intercept glucose reads and reject incorrect phases/identities, incomplete reviews, reserved assignments, invalid deadlines and direct human worker output inside the repository. |
| Durable access history | Process-concurrency, complete-prefix snapshot, mutation, truncated-write and fsync-failure checks pass. Existing ledgers are never overwritten or silently repaired. |
| Numerical aggregation | Independent hand calculations check MAE, RMSE, bias, paired differences, equal-person weighting, censored lower bounds and whole-person resampling. |
| Full native study | Five tests pass: complete execution and offline reconstruction; unsupported participant and recorded reuse; failed unseen source with unaffected fitting; insufficient development preserving failure; altered model rejected before evaluation. |
| Report reconstruction | Saved forecasts are checked against their saved inputs and coefficients; reports reconstruct using `python -S`, with original input, fit and plan directories removed in the native test. |
| Historical behavior | The existing four native M3 estimator/workflow tests remain part of verification; no Ohio code or protocol was changed. |

The separate verification command completed with a two-person, ten-day invented example using the protocol's actual coverage floors. Synthetic error magnitudes are deliberately not presented as an accuracy result.

The implementation was checked as a working tree based on `5cc110710e8c521a08c0cc9a5e025c93523d2ab5`, with new sources fingerprinted in generated artifacts. That commit alone does not identify these uncommitted additions. Synthetic execution records the dirty state; a human freeze requires committed, reviewed sources. The existing M3 runtime lock supplies the native estimator dependency versions.

## Scientific and operational limits

This work does not demonstrate predictive improvement in people, physiological accuracy, a new controller, a dosing benefit or independent human reproduction. Validation remains diagnostic, and the final same-person period is not generalization to unseen participants. The five reserved people remain same-study material.

The public-source review in the [tutorial](../m3-azt1d-tutorial.md#conservative-boundary-policy-from-public-documentation) supports a conservative exclusion policy at and outside 40–400 mg/dL. It does not resolve the release's precise clipping, LOW/HIGH or availability semantics. Before a human run, bind the actual private release review, chosen policy, existing allocation and phase manifests, overlap review, prior inspection disclosure, rights and processing authorization. No research review flags were asserted on behalf of the operator during this task.

The local access ledger is not an external witness against deliberate replacement of every record and receipt. A saved report verifies the copied history, not any later live accesses. Reconstruction verifies saved model identity, training windows and forecast arithmetic; it does not repeat the regression fit or independently prove that an alternative training procedure could not produce the same artifact. Human processing, export and retention remain conditional on their recorded scope.
