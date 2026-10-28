# PhysioCGM execution supplement

Accepted for software implementation, 20 September 2026, under
[Decision 0014](../decisions/0014-physiocgm-human-execution.md).
This technical supplement executes the unchanged scientific protocol
[M3-PHYSIOCGM-EXTERNAL/0.1](physiocgm-external-freeze-protocol.md).
It does not amend its cohort, predictor, observation interpretation, matching,
outcomes or uncertainty rules. Implementation and synthetic tests do not
constitute a human evaluation. No human predictions or scores are calculated
while building this route.

## Separate authorization and execution plan

The retained human preparation is historical evidence. Its schema remains
`opent1d.physiocgm.external-freeze/1`, its stage remains `pre-scoring`, and its
`evaluation_enabled` and `execution_supported` flags remain false. Neither
editing those flags nor submitting that bundle to the old synthetic evaluator
enables human execution.

The separate `experiments.m3.physiocgm_evaluation` namespace creates a new
execution plan with schema `opent1d.physiocgm.evaluation/1` and stage `execution`
from the unchanged preparation. A request must record explicit
authorization for local prediction, scoring and private reconstruction; the
earlier conversion or pre-scoring authorization does not supply it. The
request identifies the existing preparation by its inventory hash and retains
the earlier access disclosure. Creating a new plan does not make previously
inspected observations unseen. The request has exactly these fields:

| Field | Required content |
| --- | --- |
| `schema` / `kind` | `opent1d.physiocgm.evaluation/1` and `human` |
| `freeze` | Absolute `directory` of the completed pre-scoring bundle and its exact `manifest_sha256` |
| `authorization` | `confirmed: true`, scope `local-external-evaluation`, and a truthful `reference` to authorization for the concrete scoring step |
| `prior_access` | `reviewed: true`, status `present`, and a `reference` disclosing audit, conversion, preparation and any previous execution attempts |

Preparation validates and privately copies the existing bundle, including all
ten normalized inputs, complete origin schedules, donor model and the original
limited donor attestation. It verifies the retained conversion/reconstruction
evidence through that bundle without returning to the original native CGM
exports, AZT1D development/validation observations, reserve or original donor
ledger. The new plan binds the request, original preparation identity, exact
execution implementation and scientific rules before any prediction or score
is calculated. Record both the repository revision and dirty status; source
snapshots do not turn uncommitted work into a clean committed release.

The execution plan does not replace the historical freeze or imply a stronger
model provenance check. The donor seal still verifies consistency of the four
saved control files and unchanged model bytes. It does not independently
reconstruct training or validation arithmetic, or establish the historical
execution environment by itself.

## Prediction and analysis contract

The scientific definitions remain canonical in the original
[freeze protocol](physiocgm-external-freeze-protocol.md#frozen-prediction-and-analysis-rules).
The execution route must enforce the saved rules, including:

- All ten planned exports, with the full-export intervals and every registered
  origin retained; no outcome-dependent participant or period selection.
- Exact measured CGM history at `t−25`, `t−20`, `t−15`, `t−10`, `t−5` and `t`
  minutes, a 30-minute horizon, the 60-minute warm-up and unchanged
  `StandardScaler`/Ridge parameters.
- Feature availability by the forecast origin, a common clock segment and
  exact timestamp matching. No tolerance, interpolation, rounding, clipping,
  personalization or refitting is introduced.
- Causal prediction eligibility decided before inspecting the future target.
  Missing or unusable targets affect scoring coverage, not whether an otherwise
  eligible forecast is made.
- Persistence as the paired comparator; only measured point targets enter
  ordinary MAE/RMSE. Preserved censor directions without numeric bounds do not
  supply point scores or numeric error lower bounds.
- Contribution requires completed execution, at least 288 jointly scored
  origins and at least 24 hours between the first and last paired origin.
  A noncontributing planned person makes the cohort incomplete.
- Equal-person primary MAE difference, Ridge minus persistence, with the frozen
  secondary outcomes and whole-person bootstrap: 2,000 draws, seed 301 and
  one-based order statistics 50 and 1,950; uncertainty is undefined with fewer
  than two contributors.

The naive local clock, one-segment and measurement-time-as-availability
assumptions remain explicit. The comparison is retrospective prediction under
observed treatment. Different source studies support a study-level contrast;
aliases and hashes do not establish participant independence.

## Access order, process ownership and failures

Keep inputs, individual predictions, targets, error traces, model parameters,
private source paths and derived reports outside Git and public services. Use
fresh private output directories and retain every attempt. Standard output and
routine error messages must not expose health records or individual results.

Durable access evidence must precede the corresponding health-artifact read.
Fixed request, plan and inventory metadata may be read first to establish the
identity that the receipt binds. A failed receipt permits no protected read.
Preparation, evaluation and report reconstruction are separate accesses; a
receipt for an earlier conversion or freeze does not stand in for them.

Reuse the existing durable evaluation ledger with the new PhysioCGM execution
identity. Its historical `before_normalization` event denotes reading and
validating already normalized input, not first-ever access to native data.
Record the execution receipt before launching a participant worker. The worker
checks the bound receipt and claims it exclusively before reading observations.
An exclusive study claim in the prepared package prevents concurrent or
accidental duplicate execution using that package; individual claims prevent
reuse of a worker authorization. This is not a global ban across newly prepared
packages. A new preparation creates a new ledger and must record authorization
covering that attempt and disclose prior attempts. Existing authorization remains
valid within its stated scope; a technical retry does not by itself require a
new permission request. Retain existing claims and
failed attempts rather than deleting them for a retry.

The supervisor owns process lifetime, deadlines and the complete planned roster.
Workers retain predictions and scoring evidence in private artifacts. Missing
or altered files, invalid observations, timeouts, process failures and
interruption must remain visible in the saved state. Preserve the unattempted
remainder of the schedule; a partial run is not a completed participant, and a
partially contributing cohort is not complete. A later aggregate may describe
contributing participants only if the report also retains all planned cases
and their exclusion or failure reasons.

Local hashes, inventories and chained receipts provide consistency checks
against retained identities. They are not external signatures and cannot prove
integrity if all artifacts and history are replaced together.

## Commands and retained artifacts

After authorization for actual evaluation, set `private_execution_request`,
`private_execution`, `private_study` and `private_report` to the private request
and three fresh directories outside all Git repositories. The commands are:

```sh
uv run --locked python -m experiments.m3.physiocgm_evaluation prepare --request "$private_execution_request" --output "$private_execution"
uv run --locked python -m experiments.m3.physiocgm_evaluation evaluate --plan "$private_execution/plan.json" --output "$private_study" --timeout 120
uv run --locked python -S -m experiments.m3.physiocgm_evaluation report --study "$private_study" --output "$private_report"
```

`prepare` validates the original freeze, retains a byte-preserving private
copy, snapshots the execution code and writes the new plan, inventory,
verification evidence and access ledger. It does not forecast or score.
`evaluate` claims that prepared package, verifies the copy used by its workers,
records access and supervises each participant process. The timeout is in
seconds per worker. It retains `study.json`, a ledger snapshot, the prepared
bundle and participant artifacts even when execution fails.

`report --output` names a fresh directory, not a JSON file. It contains
`report.json`, the reconstruction read log, verification evidence, state and
inventory. The CLI prints only command status; inspect any permitted aggregate
findings through a separately reviewed private report. No command downloads
records or fits the donor model.

## Private reconstruction and acceptance

Report reconstruction records a new read receipt before opening retained input,
model, trace or result payloads. It checks source/code bindings, authorization,
access evidence, schedules, worker status and the complete roster. It
reconstructs forecasts and paired numerical summaries from the saved model and
observations, comparing them with the retained execution artifacts. This
arithmetic is evaluation access even though it does not fit an estimator.

Reconstruction uses retained private snapshots and the frozen arithmetic. It
does not need original source folders, a live donor ledger, simulator or
scikit-learn fitting environment. Report output is private and retains the
limited donor-verification scope, prior access, clock/availability assumptions,
participant-independence uncertainty and failures alongside any numerical
results. The same privacy rules apply to individual derived results as to the
inputs.

Software acceptance uses invented fixtures for successful arithmetic,
causality, source/model/rule tampering, read-before-access refusal, receipt
reuse, exclusive execution, deadline/failure preservation and reconstruction.
These checks demonstrate the route's mechanics only. The separate human-use
step still requires its concrete authorization, a source-bound execution plan,
private execution evidence and reconstructed outcomes. Passing repository
checks does not close M3's human-evaluation criterion.

Changing a scientific definition requires a versioned amendment with prior
access disclosed. A fixed-model forecast result can identify a useful or
unsuccessful prediction baseline; it cannot by itself validate a physiological
engine, identify insulin response, demonstrate another controller's effect or
establish clinical safety. This route adds reproducible evaluation software,
not a new predictor, physiological model or controller.
