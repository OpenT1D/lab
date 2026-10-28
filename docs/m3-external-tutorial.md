# External CGM forecasts: synthetic evaluation and human preparation

The synthetic workflow exports an already frozen AZT1D-format model, freezes a separate external roster, evaluates that model and persistence, and reconstructs the report from artifacts without retraining. Its runnable end-to-end examples use self-authored observations. A separate human preparation route binds the completed private PhysioCGM conversion to an unchanged donor model and freezes the analysis rules before scoring. A new execution namespace can consume that unchanged freeze after explicit scoring authorization. Its implementation is tested with invented observations; actual human scoring is a separate step.

Read [M3-EXTERNAL/0.1](research/m3-external-protocol.md) and [decision 0010](decisions/0010-external-frozen-forecast.md) for the historical synthetic route. [M3-PHYSIOCGM-EXTERNAL/0.1](research/physiocgm-external-freeze-protocol.md) and [decision 0013](decisions/0013-physiocgm-external-freeze.md) define the separate human pre-scoring boundary. Its [execution supplement](research/physiocgm-execution-protocol.md) and [decision 0014](decisions/0014-physiocgm-human-execution.md) add executable software under the same scientific rules. There is no new timestamp tolerance: history and target positions must match exactly.

## Run the synthetic verification

From the repository root, prepare the locked environments and choose a new output location:

```sh
uv sync --locked
uv sync --locked --project experiments/m3/runtime
uv run --locked python -m experiments.m3.external.verify --output /tmp/opent1d-m3-external-check
```

The verification creates a synthetic donor study through the existing AZT1D workflow, fits that donor model, exports it, and evaluates it on separately invented external people. The estimator runtime is needed only for this donor-fixture fitting. The external evaluation and report commands do not fit a model or require scikit-learn. Synthetic errors are software checks, not estimates of accuracy on people.

Each attempt needs a new output directory. Preserve an unsuccessful attempt and its access history rather than deleting it to present a repeated run as unseen. Repository checks are separate:

```sh
uv run --locked python scripts/check.py
```

### Verification record — 20 September 2026

The complete synthetic verification passed locally: a native donor fit was exported unchanged, used for two separately invented external people, and reconstructed byte-for-byte with `python -S` after deleting the verification's original inputs, donor fit, plans and live ledgers. Its `verification.json` records no external refit, unchanged model/scaler bytes and no human evaluation. Generated evidence remains local and is not committed.

The 37 external unit checks cover causal and exact-time behavior, hand-calculated metrics, portable model integrity, metadata-only freezing, access ordering and repeat disclosure, human-input refusal, full-cohort failure accounting, deadline/interruption preservation, semantic tampering and reconstruction. The existing four M3 and five AZT1D native tests also passed. Repository checks, including the documentation build, passed. The new CI step repeats the synthetic transfer verification; a remote CI execution is not claimed here.

These are historical software verification results from self-authored fixtures. No patient observations, private human predictor or reserved human evaluation period were opened for that synthetic verification. It did not verify provider-native import, actual participant independence or human predictive performance. The separate PhysioCGM conversion and preparation described below have their own scope and evidence.

## Run the synthetic stages explicitly

The following shell variable is an example location for invented artifacts, not a location for human records. It must not already exist.

```sh
external_demo=/tmp/opent1d-external-demo
uv run --locked python -m experiments.m3.azt1d study-fixture --output "$external_demo/donor-input"
uv run --locked python -m experiments.m3.azt1d freeze --registry "$external_demo/donor-input/registry.json" --output "$external_demo/donor-plan"
uv run --locked python -m experiments.m3.azt1d init-ledger --plan "$external_demo/donor-plan/plan.json"
uv run --locked python -m experiments.m3.azt1d fit --plan "$external_demo/donor-plan/plan.json" --output "$external_demo/donor-fit"
uv run --locked python -m experiments.m3.external export-model --plan "$external_demo/donor-plan/plan.json" --fit "$external_demo/donor-fit" --output "$external_demo/model"
uv run --locked python -m experiments.m3.external fixture --output "$external_demo/external-input"
uv run --locked python -m experiments.m3.external freeze --registry "$external_demo/external-input/registry.json" --model "$external_demo/model" --output "$external_demo/plan"
uv run --locked python -m experiments.m3.external init-ledger --plan "$external_demo/plan/plan.json"
uv run --locked python -m experiments.m3.external evaluate --plan "$external_demo/plan/plan.json" --output "$external_demo/study" --timeout 120
uv run --locked python -S -m experiments.m3.external report --study "$external_demo/study" --output "$external_demo/reconstructed.json"
```

The donor fitting above is fixture setup in the existing AZT1D route. The external namespace has no `fit` command. Once exported, the model's scaler and coefficients remain unchanged for every external person.

Export checks the original learned freeze and its retained inputs/access history, so it requires a compatible source checkout. It copies the original model, freeze, origin attestation and hash inventory. External loading thereafter needs this bundle, not the donor source observations. Its checks establish consistency with the attested origin; they do not independently repeat fitting or grant permission to publish a model.

## Understand the synthetic external registry

The generated `registry.json` is an executable synthetic example. It declares:

| Field | Meaning |
| --- | --- |
| `schema` / `kind` | `opent1d.m3.external/1` and `synthetic`; human input is refused. |
| `source` | Source ID, reference and `normalized-cgm/1` input format. |
| `ledger` | Absolute path for the persistent evaluation-access ledger. |
| `prior_access` | Reviewed disclosure with status `present`, explaining prior generation/conversion of the normalized inputs. |
| `people` | Every planned external person, including those whose data later prove unusable. |
| Per-person `input` | Absolute normalized observation path and exact SHA-256. |
| Per-person `bounds_us` / `origins_us` | Half-open elapsed interval and sorted unique registered origins in integer microseconds. |

Normalized observations reuse the existing AZT1D observation-document structure: local elapsed times, mg/dL, availability, clock segments, status, value or censor bound, and source-row lineage. This is an internal interchange contract, not an importer for PhysioCGM or another provider. A converted file's existence is not evidence of correct units or native status interpretation.

Freeze reads this metadata and the model bundle but does not open the external observations. It binds a canonical JSON hash of the registry, independent of its original formatting. Duplicate lexical input paths, aliases and input hashes are rejected, along with exact alias/hash overlap with the donor inventory. Lexical paths are compared without opening the files or resolving their filesystem targets. These technical checks cannot prove that differently named or re-encoded records describe independent people.

## Interpret the synthetic saved report

Each planned origin remains accounted for. The report separates forecasts that could be made from forecasts with measurable targets, and shows exclusions and execution failures. Both methods use identical paired target origins for the primary comparison.

An external person needs completed execution, at least 288 scored pairs and an origin span of at least 24 hours to enter the primary aggregate. There is no development-eligibility flag for external people. Each contributing person has equal weight. The primary difference is Ridge MAE minus persistence MAE, so a negative value favors Ridge within the declared comparison. An incomplete planned cohort remains labeled incomplete.

The standard-library `report` command verifies saved model arithmetic, observations, schedules, access receipts, exclusive worker claims, failure accounting and artifact hashes. Failed and interrupted work must retain its original failure type; saved runs must retain a valid elapsed execution time. Reconstruction does not need original inputs, donor fit artifacts, the live ledger or an estimator installation. A saved ledger snapshot cannot establish whether later live access occurred. Repeated `evaluate` calls append access history; they do not create another unseen evaluation.

The ledger's reused event name `before_normalization` means before reading and validating the already normalized external input in this route. Prior generation/conversion is disclosed separately. The supervisor records another event before execution; the worker checks it and exclusively claims that receipt before reading observations. Reusing the same worker claim is refused. Missing files, rejected measurements and interrupted workers remain in the accounting.

## Prepare the private human PhysioCGM freeze

This separate route accepts only the source-bound ten-person conversion and its
completed reconstruction under
[PHYSIOCGM-CONVERSION/1.0](research/physiocgm-conversion-protocol.md), together
with the four original donor control files. It can create and verify a private
pre-scoring bundle; it cannot evaluate it. The earlier audit and conversion
remain disclosed prior access. Different source studies support an external
study comparison, while actual participant overlap remains unverified.

Prepare the request privately, outside every Git repository, using only
authorized retained evidence and original metadata. Its fields are:

| Field | Required content |
| --- | --- |
| `schema` / `kind` | `opent1d.physiocgm.external-freeze/1` and `human` |
| `authorization` | `confirmed: true`, scope `local-external-freeze-only`, and a reference to the user's concrete preparation authorization |
| `donor` | Exactly `plan`, `model`, `freeze` and `state`, each with absolute `file` and `sha256`; the filenames are `plan.json`, `model.json`, `freeze.json` and `state.json`, with the last three from one completed fit directory |
| `conversion` / `reconstruction` | Absolute `directory` and `manifest_sha256` for the completed private conversion and its matching completed reconstruction |
| `prior_access` | `reviewed: true`, status `present`, and a reference disclosing earlier audit, conversion and reconstruction |
| `overlap` | Assessment `different-source-studies-person-overlap-unverified`, with a source-review reference |

After setting `private_request`, `private_freeze` and `private_verification` to
the authorized private request and two fresh output directories, the preparation
commands are:

```sh
uv run --locked python -m experiments.m3.external human-freeze --request "$private_request" --output "$private_freeze"
uv run --locked python -m experiments.m3.external human-verify-freeze --bundle "$private_freeze" --output "$private_verification"
```

Do not point these commands at the synthetic tutorial output or label human
observations synthetic. Original source paths, health records, schedules,
learned parameters and individual derived artifacts stay private. There is no
download or donor-fit command in this preparation, and no reserve access is
needed.

`human-freeze` records a durable donor-batch receipt before opening the four
donor control files. It records a conversion/reconstruction metadata-batch
receipt before checking the saved evidence, then a separate receipt before
each normalized observation read. These `before_bundle_read` events use
subjects `donor`, `conversion` and the participant alias, respectively. Their
reused `plan_sha256` field binds the exact pre-read request hash, not the plan
generated afterwards. A failed receipt permits no corresponding read.

The command privately snapshots the ten normalized files, unchanged donor
control files, saved evidence, complete origin schedule, source identities,
scientific rules and implementation provenance. It does not reopen native CGM
files. The plan fixes the full-export period, exact six-value history,
30-minute horizon, 60-minute warm-up, contributor floors and participant-level
analysis, including the 2,000-draw bootstrap and seed 301. It does not calculate
eligibility, predictions, errors or uncertainty results.

The donor seal uses `opent1d.physiocgm.frozen-model-metadata/1`. It validates
saved model shape, internal hash bindings and recorded clean historical
provenance from those four files. It does **not** execute `export-model`, reopen
development/validation observations or traces, reconstruct validation
arithmetic, fit again or claim complete historical training verification.
This limited attestation remains part of any later interpretation.

`human-verify-freeze` first reads fixed request/inventory metadata to identify
the retained bundle. It records one bundle-wide `before_bundle_read` receipt
with subject `freeze` before opening snapshots, then checks the saved
identities, model seal, cohort, rules and original batch/per-file receipts.
Verification uses retained snapshots and evidence without the original native
sources or original donor folders. Fresh output directories and failed
attempts remain part of the history.

Invented fixtures exercise these controls, source tampering, complete-roster
failures, access ordering, donor read boundaries and refusal by the synthetic
worker. Those tests establish software mechanics, not a completed human freeze
or predictive accuracy; private execution requires its own retained evidence.

## Prepare and execute the separate human assessment

The human bundle has stage `pre-scoring`, `evaluation_enabled: false` and
`execution_supported: false`. The existing `evaluate` command rejects its
distinct schema even if someone changes a Boolean. Keep that original bundle
unchanged. The new `experiments.m3.physiocgm_evaluation` namespace creates a
separate execution plan with schema `opent1d.physiocgm.evaluation/1`; it verifies
the original preparation, preserves its limited donor attestation and binds
the implementation before any scores are calculated.

Actual use requires a private request with exactly these fields:

| Field | Required content |
| --- | --- |
| `schema` / `kind` | `opent1d.physiocgm.evaluation/1` and `human` |
| `freeze` | Absolute `directory` of the completed pre-scoring bundle and its exact `manifest_sha256` |
| `authorization` | `confirmed: true`, scope `local-external-evaluation`, and a truthful `reference` to the user's concrete scoring authorization |
| `prior_access` | `reviewed: true`, status `present`, and a `reference` disclosing audit, conversion, preparation and any previous execution attempts |

The pre-scoring request is not this scoring authorization. Building and testing
the execution software does not supply it either. After the concrete human
execution step is authorized, set `private_execution_request` to that request
and use three fresh private directories for the following commands:

```sh
uv run --locked python -m experiments.m3.physiocgm_evaluation prepare --request "$private_execution_request" --output "$private_execution"
uv run --locked python -m experiments.m3.physiocgm_evaluation evaluate --plan "$private_execution/plan.json" --output "$private_study" --timeout 120
uv run --locked python -S -m experiments.m3.physiocgm_evaluation report --study "$private_study" --output "$private_report"
```

`prepare` verifies and copies the existing freeze/model/ten inputs, saves the
new code and plan and creates the execution ledger. It calculates no forecasts.
`evaluate` claims that prepared package, verifies the worker input copy, records
source and execution access and supervises each participant in a separate
process. The timeout is seconds per worker. It preserves partial work, failures
and unattempted cases in the complete cohort accounting.

Only one evaluation can claim a prepared package, even if it uses another
output directory. A new preparation has a new ledger; this is not a global
cohort lock. Such a new attempt must record authorization covering that attempt
and disclose earlier attempts. Existing authorization remains valid within its
stated scope; technical retries do not automatically require another permission
request. Never delete claims or failed artifacts to conceal repetition.

`report --output` requires a fresh directory, not a JSON filename. Before
opening health payloads it records a reconstruction read receipt. It verifies
retained identities, access evidence and process states, then recomputes
predictions and summaries from private snapshots to check the recorded
artifacts. The directory contains `report.json` plus state, inventory, read log
and freeze-verification evidence. It does not need the original donor/source
folders, live donor ledger, simulator or estimator fitting environment.
Reconstruction still counts as evaluation access.

All model parameters, observations, schedules, individual results and error
artifacts remain outside Git and public services. The commands print status
without patient values or scores. Their synthetic tests exercise the software
mechanics; the implementation step does not open the actual human bundle or
establish human predictive accuracy.

Changing scientific assumptions or the model requires a versioned amendment
with prior access disclosed. Preparation does not establish a better predictor,
physiological model, controller or clinical product. Any eventual score would
apply to retrospective CGM forecasting under the stated clock and availability
assumptions, not establish effects of another treatment or controller.
