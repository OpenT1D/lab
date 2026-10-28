# Compare frozen CGM predictors on one synthetic task

The M3 comparison route runs at least two already frozen predictors on the
same invented observations, then compares every candidate and persistence
on shared support. It saves a readable parent report and each unchanged
single-candidate study. This is bounded software verification; it does not
fit models, choose a winner or establish performance in people.

The [frozen M3-COMPARISON/1 protocol](research/m3-candidate-comparison-protocol.md)
owns the comparison rules. The [single-candidate guide](m3-researcher-forecast.md)
owns predictor declarations, the callback and normalized observation format.
Use the [local workflow entry](local-workflow-entry.md) to discover supported
tasks and their installed runtime requirements.

## Run an invented example

From the repository root on macOS or Linux, install the locked root tooling
with `uv sync --locked`. Python 3.12 or later is required for worker supervision.
Each output directory must be new; retain unsuccessful attempts.

```sh
comparison_demo=/tmp/opent1d-m3-comparison-demo
uv run --locked python -m experiments.m3.comparison fixture --output "$comparison_demo/fixture"
uv run --locked python -m experiments.m3.comparison check --config "$comparison_demo/fixture/comparison.json"
uv run --locked python -m experiments.m3.comparison run --config "$comparison_demo/fixture/comparison.json" --output "$comparison_demo/study"
uv run --locked python -S -m experiments.m3.comparison reconstruct --study "$comparison_demo/study" --output "$comparison_demo/reconstruction"
```

`fixture` prepares invented CGM observations and two different prediction
structures: a bounded trend predictor and the existing portable Ridge
prediction arithmetic with invented settings. It performs no fitting or
assessment. Known fixtures and repetitions stay disclosed as prior access.
A genuine Ridge donor can be fitted and exported separately through the
[existing M3 verification workflow](m3-researcher-forecast.md#run-the-worked-example);
the comparison itself accepts only the frozen source and settings.

`check` reads configuration, declaration, source and settings bytes and
verifies their metadata and hashes. It does not import the predictor or open
observation contents. Its `observation_bytes_verified: false` is deliberate:
valid metadata alone does not establish usable inputs or a complete study.
Execution verifies observations through the original M3 runner.

## Freeze one comparison configuration

The generated `comparison.json` is the executable example. It has exactly
these fields:

| Field | Contract |
| --- | --- |
| `schema` / `kind` | `opent1d.m3.comparison/1` and `synthetic` |
| `source` / `prior_access` | Existing M3 source identity and truthful generation, development and inspection disclosure |
| `people` | Full ordered roster with original absolute input paths, exact hashes, bounds and all planned origins |
| `candidates` | Ordered list of at least two objects, each with `id` and absolute `declaration` path |
| `timeout_seconds` | Positive finite wall-time budget for each participant worker, identical for every candidate |

Candidate IDs must be unique and match their declarations. The ID
`persistence` is reserved for the shared reference. Predictor rights,
training origin, stateless callback, source and settings retain the
single-candidate contract. Do not put human observations into this route or
label them synthetic.

The coordinator saves every declaration, source and settings snapshot,
the shared roster, origins, phase, execution order, budget and source
provenance before starting a child study or opening assessment observations.
It executes candidates sequentially in that frozen order. Each child uses
the unchanged M3 supervisor and reader. Parent administration stays outside
the strict child archive inventories.

A valid causal history requires one finite forecast. The callback has no
successful per-origin abstention. Completed candidates on identical inputs
therefore have identical valid origins; legitimate unequal coverage comes
from failed, interrupted or unattempted workers. Supplied Python runs with
local user permissions; process supervision does not sandbox it or prove
that its output depends only on the permitted history.

## Read the parent report

Open `study/report.md` for candidate order, coordinator state, common-support
MAE, RMSE and bias, every contrast, participant coverage and exclusions.
`report.json` contains the same analysis and the original candidate reports.

The primary support is the intersection of **all frozen candidates and
persistence**. A participant contributes only if every candidate worker
completed, there are at least 288 shared scored origins, and the first and
last shared origins are at least 24 hours apart. Both coverage conditions
must hold. A long failed prefix remains diagnostic and never qualifies.

Each contributing participant receives equal weight. Contrasts use
left-minus-right absolute error on exactly the same origins, first for each
candidate versus persistence, then for each ordered candidate pair. Negative
values favor the left method within this declared task. The descriptive
bootstrap resamples whole participants 2,000 times with seed 301 and the
inherited exact empirical percentile ranks. Fewer than two contributors
produce a null interval; no contributors produce null primary metrics with
an explicit reason. These coverage floors are not accuracy thresholds or a
power calculation.

The report retains every planned participant and origin. Its
`complete_cohort` field is false when any planned participant is ineligible,
even if a partial aggregate exists. Original child reports keep their own
candidate-versus-persistence denominators; do not use those unmatched
subsets to rank candidates. Pairwise-support populations are deferred.

Worker failure or deadline preserves the child's completed trace prefix and
remaining scheduled origins and permits later candidates to run. A global
SIGINT, SIGTERM or SIGHUP stops the sequential comparison and preserves the
unattempted tail. SIGHUP is forwarded to the unchanged supervisor as SIGTERM
so it can clean up its worker; the parent retains the original signal.
Normal cleanup uses the existing supervisor's ownership rules. A bounded
fallback can terminate an unresponsive supervisor group; it does not prove
ownership or termination of arbitrary escaped descendants.

If an attempted child has no valid sealed archive, its coordinator remains
failed or interrupted and `missing_archive_reason` explains the loss.
Per-person `not_attempted` records in common analysis then mean zero
**validated** worker/origin records, not that no process was launched.
Retained raw artifacts remain diagnostic. An unavailable candidate stays in
the frozen roster, so it cannot be dropped to rescue a primary comparison.

The run command returns a failure status for coordinator or worker failures.
A successful process exit can still leave an ineligible cohort; read
`complete_cohort`, contributor counts and reasons separately.

## Reconstruct and preserve evidence

Keep the entire parent directory: `plan.json`, `state.json`, `frozen/`,
`logs/`, `children/`, `manifest.json` and both reports. Keep every child study
intact. Parent reconstruction verifies its inventory and frozen identities,
then invokes the unchanged reader for each sealed child and recomputes common
support and arithmetic from saved traces.

Reconstruction needs the recorded source checkout and matching protocol and
source hashes, but no original observation, declaration, source or settings
paths. It does not import candidate code or fit or re-execute a predictor.
It validates saved causal histories, measured targets, persistence and
analysis; arbitrary candidate outputs remain observed execution evidence.
Hashes establish saved consistency, not authenticated execution, independent
model reproduction or clinical validity.

Repository verification uses `uv run --locked python scripts/check.py`.
Independent scientific review and authorized human evaluation remain
separate evidence gates in the [roadmap](research/roadmap-history-2026-10-28.md#post-integration-internal-work-packages).
