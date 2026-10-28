# M5 researcher prognostic workflow

This bounded workflow connects a researcher's frozen Python prognostic model
to the unchanged [32-person invented M5 task](m5-synthetic-prognosis.md).
The question is: **how do its predictions of later reported insulin use
compare with a simpler development-only reference under the same eligibility
and participant split?** It has no human-data loader. Its inputs, associations
and outcomes are invented; this is software verification, not a transplant
model, human prediction study or treatment-effect estimate.

The [protocol](research/m5-researcher-protocol.md) defines the task and
failure rules. [Decision 0054](decisions/0054-m5-frozen-prognostic-intake.md)
records the bounded intake. The earlier fixed synthetic comparison remains
unchanged and independently runnable.

## Run an example

From the repository root, choose new directories:

```sh
uv sync --locked
uv run --locked python -m experiments.m5.researcher_workflow.run export-example \
  results/m5-example
uv run --locked python -m experiments.m5.researcher_workflow.run run \
  results/m5-example results/m5-researcher
uv run --locked python -m experiments.m5.researcher_workflow.run reconstruct \
  results/m5-researcher
```

The export command creates an illustrative frozen model using the earlier
development-only ridge plus observed-function feature. It fits on the same
20 eligible development participants and writes its preprocessing and
coefficients as state. The example is a compatibility check; it is not a
recommended empirical model. Inspect `report.md` for the readable comparison
and `report.json` for complete machine-readable accounting.

## Supply your model

The intake is exactly three local files:

| File | Role |
| --- | --- |
| `model.py` | Trusted Python source exposing `predict(record, state)` |
| `state.json` | Frozen JSON object, such as development-fitted preprocessing and coefficients |
| `model.json` | Versioned declaration binding source, state, runtime and training provenance |

Start from the exported example to inspect the exact declaration. Replace
the source and state with your method, then update both SHA-256 fields and
the model identity, rights basis and training declaration. Freeze this bundle
before running held-out requests. The declaration uses these fields:

| Field | Required meaning |
| --- | --- |
| `schema` | `m5-prognostic-model/1` |
| `model_id` | Identifier of at most 128 letters/digits/`._-`, starting with a letter or digit |
| `rights_basis` | Researcher's statement of their basis to use the source and state |
| `input_schema` | `m5-landmark-input/1` |
| `output_unit` | `U/day` |
| `source_sha256`, `state_sha256` | Hashes of the exact `model.py` and `state.json` bytes |
| `runtime` | Current CPython `python_major_minor` and `dependencies: []` |
| `training` | Exact invented `fixture_sha256`, `phase: development_only`, and `participant_aliases` equal to the 20 eligible development aliases |

Source and state hashes detect changed bytes. They do not establish rights,
prove the declared training history or show that outcomes were never
inspected. Those statements are self-attested provenance and remain visible
in the archive. The supported runtime uses Python's standard library; no
additional model dependency environment is provided by this contract.

The callback receives a JSON record with exactly these fields:

| Key | Information available to the callback |
| --- | --- |
| `schema` | `m5-landmark-input/1` |
| `prior_insulin_u_day` | Prior reported insulin amount, U/day |
| `prior_glycemic_status_mg_dl` | Prior glycemic status, mg/dL |
| `landmark_day_after_first_infusion` | Landmark day relative to the first infusion |
| `observed_function_index` | Invented 90-minute C-peptide divided by concurrent glucose/100 |

Return one finite numeric prediction in U/day. The engineering range is
inclusive `[0, 1000]`; it is an output-validation limit, not a clinical
threshold or dosing recommendation. The host gives the callback no alias,
split label, outcome, outcome visit or later infusion information. All
preprocessing and coefficients must already be in the frozen state; do not
fit, tune or update state during prediction.

Each eligible held-out participant is predicted twice, in separate fresh
Python workers, with a default five-second budget per worker. Set
`--timeout-seconds` on `run` to a finite positive budget of at most 60 seconds
when needed; the chosen budget remains in the archive. Python's `random`
generator is seeded to zero in each worker. Paired scoring requires exact
prediction and runtime-identity agreement across both attempts. Failures,
timeouts, invalid outputs and disagreement remain recorded. A valid primary
prediction remains saved even if the repeat fails, but it cannot enter the
paired metric. Ctrl-C, SIGTERM and SIGHUP preserve saved records, mark the
active attempt `interrupted` and show remaining attempts as `not_attempted`.
The runner cleans up the worker process group and restores its signal
handlers. Process isolation resets in-memory model state; **it is not a
security sandbox**.
Run only source you trust. Input projection describes the callback contract;
it does not prevent trusted Python from accessing files or other resources
available to your account.

## Read the comparison

Every report retains the complete 32-person roster: 24 assigned development
and eight assigned evaluation before fitting. The unchanged eligibility
rules leave 20 development and seven evaluation participants. The five
excluded records distinguish protocol-directed day-75 noncollection after
confirmed graft failure, unavailable challenge, below-limit C-peptide,
missing first-infusion Y1 despite a V15 record, and incomplete seven-day
diary. Later infusions remain visible even for eligible participants.

The baseline uses prior insulin amount, prior glycemic status and landmark
day. Development-only means, scales and coefficients define standardized
ridge regression with penalty 1 on slopes and an unpenalized intercept.
The report gives baseline MAE across all seven eligible held-out
participants, alongside candidate and baseline MAE on the same successfully
paired subset and candidate-minus-baseline paired MAE. Negative difference
means lower synthetic error on that subset; there is no advancement or
success threshold. Incomplete prediction coverage limits the comparison,
and zero pairs yield `null` paired metrics rather than an invented score.

Do not compare a candidate's subset MAE with baseline MAE over all seven
people. The paired baseline is the appropriate same-participant comparison;
the full baseline and complete roster preserve the denominator and show
what the candidate did not cover.

## Reconstruct the archive

The archive preserves the model source, state and declaration, their hashes,
the fixed fixture, protocol/implementation source snapshots, saved baseline,
causal requests, both prediction attempts and their statuses/runtime, and
both reports. The Markdown report shows both attempt statuses for each
eligible evaluation participant, alongside model, Git revision, CPython,
worker budget, lock and source identities. Reconstruction verifies archived
identities and task rules,
checks the saved baseline against development normal equations and rebuilds
the reports from stored predictions. It imports neither the candidate nor
its state as executable code, and it does not refit a model or run a
simulator. Integrity hashes check saved consistency; they are not an
authenticated execution record. Someone who rewrites outputs, reports and
the manifest can create a different self-consistent archive. Reconstruction
also does not prove the researcher's training or rights statements.

## Verification and evidence limits

Implementation checks are described in the
[protocol verification record](research/m5-researcher-protocol.md#internal-verification).
This route adds a local model intake and reconstructible synthetic
comparison. It does not close independent usability, human prognostic
quality, biological validity, source rights review, an empirical freeze or
treatment effectiveness. An empirical M5 study still requires the
[OT-027 data contract](research/m5-cell-therapy-data.md), authorized
release/participant linkage, independent domain review and a separately
frozen empirical protocol before fitting or held-out scoring.
