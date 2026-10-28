# M3-RESEARCHER/0.1 — Frozen researcher forecasts on synthetic CGM

**Status:** bounded synthetic software protocol, 2 October 2026.

## Question and scope

How does one frozen researcher-supplied forecast compare with persistence
for 30-minute-ahead CGM prediction on the same permitted observations?
This protocol defines a local integration and analysis task. It does not
authorize acquiring or evaluating human records, establish a provider's
native release semantics or assess treatment actions. The
[guide](../m3-researcher-forecast.md) owns executable instructions;
[decision 0053](../decisions/0053-m3-researcher-forecast-intake.md) records
the interface choice. Historical Ohio, AZT1D, external Ridge and PhysioCGM
protocols retain their existing meanings.

The first implementation accepts `kind: synthetic` only, with normalized
observations and synthetic model-training provenance. Reviewed disclosure
does not enable human input. The input author's synthetic attestation is
required but cannot detect mislabeled records. A future human extension
needs release-specific rights, native-file and clock/status checks, explicit
authorization, prior-access disclosure and a separately frozen protocol.

## Freeze and ancestry

Before opening assessment observations, bind the complete roster, interval
bounds, registered origins, input hashes, source identity, reviewed prior
access, predictor declaration, source and settings. The versioned study
schema is `opent1d.m3.researcher/1`; the predictor schema is
`opent1d.m3.forecaster/1`. The predictor records its ID, source reference,
rights (`self-authored` or `licensed`) and synthetic training reference.
Preserve exact bytes and hashes in the study artifacts. A training reference
is a disclosure, not an independently reproduced fit or rights decision.

Register every input row timestamp as an origin, including unusable rows.
The observation timestamps must exactly equal the sorted unique configured
origin schedule; selective removal of difficult origins is refused.

The quick fixture's alternate Ridge configuration uses invented settings
to exercise the established M3 arithmetic; it does not fit a model. The
complete verification separately fits and exports the existing Ridge
reference on synthetic donor material, then transfers its unchanged model
and scaler through this intake. A distinct invented bounded trend predictor
exercises another structure under the same contract. Neither example
establishes a generally useful forecast or an original biological model.
Do not refit, calibrate, choose settings or select participant inclusion
after inspecting assessment errors. Disclose input generation and prior
inspection. Repeating known observations in another directory does not
create an untouched evaluation.

## Causal predictor boundary

Supply exactly six CGM values at offsets −25, −20, −15, −10, −5 and 0 minutes
relative to the registered origin. Inputs and output use mg/dL; the forecast
horizon is exactly 30 minutes. The predictor exposes
`predict(request, settings)` and returns one finite scalar. Its declared
contract is stateless. Settings remain fixed for every origin and person;
evaluation contains no fitting stage.

The request contains exactly `origin_us`, six integer microsecond
`times_us` ending at the origin and six positive finite `values_mg_dl`.
Every invocation receives independent copies of its request and settings.
Return a finite Python `int` or `float`, excluding Boolean values. Retain
negative forecasts without clipping. Workers use `python -S` and the
standard library; this route does not install model dependencies.

The host supplies only permitted current/history fields and frozen
settings. It does not supply the future target, full observation series or
participant input path. A complete exact-time history must lie within the
declared interval, use measured rows from one clock segment and be available
at the forecast origin. Require 60 minutes of warm-up from the interval
start. Preserve unavailable, missing, censored and invalid histories as
explicit exclusions. Do not impute history, substitute censor bounds,
interpolate, clip predictions or introduce timestamp tolerance.

Scoring requires a measured target exactly 30 minutes after the origin,
within the declared interval and compatible with the history's clock
segment. Distinguish a possible forecast from one with a scoreable target.
Persistence uses the last history value under precisely the same windows.
The target is used only after the candidate callback has returned.

The predictor is trusted Python with the user's filesystem and execution
permissions. Separate processes and deadlines provide supervision, not
sandboxing. The declaration and host payload cannot enforce intentional
purity, prohibit external reads or prove absence of hidden state. Source
and dependency review remain necessary. This bounded callback does not
promise arbitrary stateful models, richer covariates, model servers or
runtime installation.

## Execution and complete accounting

Use a fresh output directory for every attempt. Retain the full planned
roster, registered schedules, frozen model/configuration, input snapshots,
implementation provenance, worker states, elapsed execution times and
errors. Each participant runs in a separately supervised worker with a
declared finite positive wall-time limit. A failed or interrupted worker
keeps the completed trace prefix. Remaining origins are unattempted;
they must not disappear from the denominator.

Input rejection, missing files, model exceptions, nonfinite output,
deadline expiry and incomplete work remain failures or exclusions with
their recorded reason. Do not silently replace a failed prediction with
persistence or discard a failed participant. Valid prefixes from failed
workers may support coverage diagnostics but do not qualify that person
for the primary aggregate.

## Outcomes

The primary outcome is the equal-person mean of each contributing person's
paired MAE difference, candidate minus persistence. Negative values favor
the candidate for the declared prediction task. Compare methods on exactly
the same jointly scored origins.

A person contributes only after complete execution, at least 288 paired
scored origins and at least 24 hours between the first and last paired
origin. These operational coverage floors preserve the external forecast
convention; they are not a statistical power calculation or clinical
accuracy criterion. There is no development-eligibility requirement.
Report every planned person, status, total origins, forecasts, paired
scores, exclusions and coverage. Any planned noncontributor leaves the
cohort incomplete. Label a partial aggregate accordingly; do not report
the contributing subset as the complete cohort.

Secondary summaries include equal-person MAE, RMSE and bias. Prediction
counts and coverage refer to registered origins, not duration-weighted
clinical exposure or treatment outcomes.

Resample whole contributing people with replacement, 2,000 draws with
seed 301. Use the 50th and 1,950th one-based order statistics for the
descriptive empirical 95% interval of the mean paired difference. Fewer
than two contributing people leave that interval undefined. Timestamps
within a person are correlated observations, not independent subjects.

## Reconstruction and evidence

Reconstruct using the standard library and retained artifacts, without
opening original source inputs, executing the predictor or fitting a model.
Verify hashes, frozen contracts, complete roster/schedules, causal windows,
target pairing, persistence, execution/failure accounting and all derived
metrics. Reject inconsistent retained evidence; do not silently repair it.
Retain the original worker failure type and a valid finite nonnegative
elapsed time for attempted work.

An arbitrary predictor's recorded output is an observed execution result.
Reconstruction validates its inclusion and analysis, but cannot
independently rederive the candidate's algorithm without executing its
source. Model-specific synthetic checks may verify a declared example's
arithmetic separately. The historical portable Ridge route's arithmetic
replay remains a stronger and narrower model-specific check. Hashes and
local snapshots establish internal consistency; they are not signatures
or protection against replacement of the entire evidence bundle.

Bounded acceptance exercises both supplied model structures, causal and
target-independent host inputs, exact matching, bad declarations,
nonfinite/failed predictions, timeouts, retained prefixes, semantic
tampering and reconstruction after removal of original inputs. Record
actual checks and generated evidence locations in the local verification
record. Passing establishes software mechanics only. Independent
researcher usability, general model compatibility, human prediction and
biological validity remain open.

Any change to horizon, causal history, units, eligibility, weighting,
matching or scientific scope requires a versioned amendment and disclosure
of already inspected material. Preserve this protocol and earlier artifacts.
