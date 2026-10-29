# Researcher-supplied CGM forecasts on synthetic observations

This bounded M3 workflow runs a frozen, researcher-supplied Python predictor
and persistence on the same invented CGM observations. It retains every
planned participant and forecast origin, produces a readable comparison and
reconstructs that comparison without executing the predictor or opening the
original input files. The task is **30-minute-ahead prediction from six exact,
causally available five-minute CGM values**.

Read [M3-RESEARCHER/0.1](research/m3-researcher-protocol.md) and
[decision 0053](decisions/0053-m3-researcher-forecast-intake.md) for the fixed
scientific rules and evidence limits. This route accepts synthetic inputs
only. It provides no human-data authorization, release-specific importer,
general model API or clinical prediction claim. The existing
[Ohio](m3-tutorial.md), [AZT1D](m3-azt1d-tutorial.md),
[external Ridge](m3-external-tutorial.md) and separately authorized PhysioCGM
workflows retain their original contracts.

## Run the worked example

The supervised runner requires a POSIX host (macOS or Linux) and Python 3.12
or later. Windows worker supervision is outside this bounded route.

From the repository root, install the locked tooling:

```sh
uv sync --locked
```

Choose a new location for synthetic artifacts. Each output directory must be
new; preserve unsuccessful attempts.

```sh
forecast_demo=/tmp/opent1d-m3-researcher-demo
uv run --locked python -m experiments.m3.researcher fixture --output "$forecast_demo/fixture"
uv run --locked python -m experiments.m3.researcher run --config "$forecast_demo/fixture/config.json" --output "$forecast_demo/study" --timeout 120
uv run --locked python -S -m experiments.m3.researcher report --study "$forecast_demo/study" --output "$forecast_demo/reconstruction"
```

The fixture supplies invented observations, a predictor declaration and a
complete study configuration. Its default `config.json` uses an invented
bounded trend predictor. `ridge-config.json` instead exercises the existing
M3 Ridge prediction arithmetic with invented settings; this fixture does
not fit a model. To run that second structural example, use a new study
output directory:

```sh
uv run --locked python -m experiments.m3.researcher run --config "$forecast_demo/fixture/ridge-config.json" --output "$forecast_demo/ridge-study" --timeout 120
```

Evaluation has no fitting stage: source and settings are fixed before any
assessment observations are read. Both fixture examples provide software
evidence, not estimates of performance in people.

The `--timeout` value is the maximum wall time in seconds for each participant
worker. A failed or timed-out worker keeps its completed trace prefix and
remaining unattempted origins in the report. A different deadline does not
create an unseen assessment or change the comparison rules.

Run the complete bounded verification separately, in another new directory:

```sh
uv sync --locked --project experiments/m3/runtime
uv run --locked python -m experiments.m3.researcher verify --output /tmp/opent1d-m3-researcher-verification
uv run --locked python scripts/check.py
```

The separately locked M3 runtime is needed for fitting the verification's
genuine synthetic donor. The self-authored fixture, run and report commands
above need only the root tooling environment.

The complete verification separately fits the existing Ridge reference on
synthetic donor material in the locked M3 runtime, verifies its portable
export, and supplies that unchanged model and scaler through the researcher
intake. It also exercises the structurally different invented predictor,
causal timing, reference arithmetic, fresh-process repetition and
reconstruction. Focused tests cover declaration errors and failure accounting.
Repository checks
verify software and documentation; they do not establish model validity
or independent researcher usability.

## Declare a frozen predictor

The predictor declaration has exactly these fields:

| Field | Required content |
| --- | --- |
| `schema` | `opent1d.m3.forecaster/1` |
| `id` / `reference` | Model ID of 1–64 letters, digits, underscores or hyphens; nonempty attribution reference |
| `rights` | `self-authored` or `licensed`, accurately describing the supplied material |
| `source` / `settings` | Absolute `file` path and lowercase, 64-character `sha256` of one Python source file or JSON settings file |
| `training` | `kind: synthetic` and nonempty `reference` explaining model/settings selection |
| `contract` | `history_minutes: [-25, -20, -15, -10, -5, 0]`, `horizon_minutes: 30`, `unit: mg/dL`, `stateless: true` |

Settings must be a JSON object with finite numbers. A declared training or
rights reference is an attestation; the software does not independently
repeat training or establish licensing.
The declaration is limited to 64 KiB; source and settings files are each
limited to 1 MiB. They must be regular files; direct file and immediate-parent
directory symlinks are refused.

The contract fixes the following supported behavior:

| Convention | Supported value |
| --- | --- |
| History | Six exact CGM measurements, at −25, −20, −15, −10, −5 and 0 minutes relative to the forecast origin |
| Availability | Each history row must already be available at the origin |
| Horizon | Exactly 30 minutes |
| Input and output unit | mg/dL |
| Output | One finite numerical forecast |
| State | Stateless prediction from the supplied request and frozen settings |
| Model adaptation | No evaluation-time fit, calibration or settings change |

The source exposes `predict(request, settings)`. The request has exactly
`origin_us`, `times_us` (six integer microsecond timestamps ending at the
origin) and `values_mg_dl` (six positive finite measurements). Each call gets
fresh copies of the request and settings. The result must be a finite Python
`int` or `float`; Boolean values are refused. Negative forecasts are retained
without clipping. The host withholds the future target, participant input
path and full observation series. The source cannot request extra history
or change target-matching and contributor rules through this contract.

This is trusted local Python running with the user's permissions. A worker
process and timeout supervise execution; they do not sandbox supplied code
or prove that it is stateless, target-independent or unable to read other
local files. Hashes identify the retained source and settings bytes. Review
the source before supplying it. Workers run with `python -S` and the standard
library. The intake does not install dependencies or manage an arbitrary
model runtime.

## Configure one synthetic study

The generated `config.json` is the canonical executable example. Adapt it
after freezing the predictor; do not use this route with human observations
or mark such observations synthetic.

| Field | Meaning |
| --- | --- |
| `schema` / `kind` | `opent1d.m3.researcher/1` and `synthetic` |
| `source` | Synthetic source ID, reference and format `normalized-cgm/1` |
| `prior_access` | `reviewed: true`, status `present`, and a reference disclosing input generation, development and any earlier inspection |
| `predictor` | Absolute path to the frozen predictor declaration JSON |
| `people` | Full planned participant roster, including participants whose input later fails |
| Per-person `id` | Unique participant alias |
| Per-person `input` | Absolute `file` path and exact `sha256` of normalized observations |
| Per-person `bounds_us` | Half-open elapsed study interval in integer microseconds |
| Per-person `origins_us` | Sorted, unique registered forecast origins in integer microseconds, exactly all input row timestamps |

Normalized inputs reuse M3's existing AZT1D observation document. Each row
preserves registered elapsed time, availability time, clock segment,
measurement status, measured value or censor bound and source-row lineage.
The interchange format is not a provider-native importer. A synthetic
declaration cannot detect human records mislabeled as invented data, verify
that different aliases are independent people or establish correct upstream
clock and status interpretation.
Each observation input is limited to 64 MiB. A missing, oversized or invalid
input leaves its participant and full scheduled origins in the report.

Freeze the full roster, origins, bounds and model before running. Input
generation and inspection are prior access and remain disclosed. Repeating
known material in a fresh output directory does not make it untouched.
Every input row is a planned origin, including unusable measurements; the
route refuses a selectively shortened schedule.

## Read the comparison

Every scheduled origin is accounted for, including unattempted origins
after a worker failure. A forecast requires 60 minutes of warm-up within
the declared interval and all six exact, measured, available history rows
in one clock segment. There is no interpolation, history imputation,
censor-bound substitution or timestamp tolerance. A measured target must
exist exactly 30 minutes after the origin under the same timing rules.
Forecast availability and target measurement status are reported separately.

The primary comparison uses only origins scored for both the candidate and
persistence. Persistence repeats the last permitted CGM measurement.
Candidate MAE minus persistence MAE is calculated per person; negative
values favor the candidate within this declared synthetic task. The primary
aggregate weights each contributing person equally.

A person contributes only after complete execution with at least 288
jointly scored origins spanning at least 24 hours. These are operational
coverage floors inherited from the external forecast route, not a power
calculation or accuracy threshold. All planned people remain in the report.
Any noncontributor makes the planned cohort incomplete; a partial aggregate
keeps that label. MAE, RMSE, bias and a descriptive
person-level bootstrap supplement the paired outcome. The
[protocol](research/m3-researcher-protocol.md) fixes their definitions.

## Reconstruct and retain the evidence

Keep the entire study directory. It contains `plan.json`, the snapshots in
`predictor/`, each participant's `cases/<id>/` input, worker state and
`trace.jsonl`, the artifact inventory in `manifest.json`, and the readable
`report.md` and numerical `report.json`. The saved plan includes configuration,
provenance and the full schedule; failed workers retain their error evidence
and completed trace prefix. If failed or interrupted work ends with a partial
JSONL record, its raw bytes remain in the artifact inventory; only complete
preceding records enter the metrics. An interrupted claim before execution
and uncommitted worker metadata also remain as raw evidence; they cannot
establish completed predictions. Supervisor and worker failure types are
retained separately when both exist. `report` verifies the retained hashes, causal
windows, persistence values and report metrics
without the original input paths or predictor execution. Its use of
`python -S` demonstrates the standard-library reconstruction boundary.
Use the recorded implementation checkout: source, lock and protocol hashes
must match the saved provenance.

The verification receipt's historical `independent_reconstruction` field means
that the saved-analysis implementation was run in a fresh process. It does not
mean a second implementation or an external researcher reproduced the result.
The receipt field and historical archive identities retain their original names.

For an arbitrary supplied predictor, this reconstruction checks the recorded
candidate outputs and their analysis; it cannot independently derive those
outputs from the model without executing its source. The existing portable
Ridge route has a stronger, model-specific arithmetic replay. Keep those
verification scopes distinct. Checksums detect inconsistency against the
saved inventory; they are not signatures and do not prevent someone from
replacing every artifact and hash.

## Verification record — 2 October 2026

The complete synthetic verification passed locally for both model
structures. Each comparison retained two planned synthetic people, with
1,516 paired targets and 1,550 forecasts checked against its corresponding
reference arithmetic. Fresh-process forecast traces were byte-identical.
The existing fitted donor model and scaler values remained unchanged;
evaluation did not refit them.

After deleting the verification's original observation files, donor folders
and original predictor source/settings, `python -S` reconstructed both
`report.json` and `report.md` byte-for-byte from the retained studies.
The local `verification.json` records these checks. These counts describe
software verification on invented observations, not predictive performance
in people. Independent intended-user execution, human predictive performance
and biological validity remain separate evidence gates.
