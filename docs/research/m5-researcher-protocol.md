# M5-RESEARCHER/1 — Frozen prognostic model intake

**Status:** bounded synthetic workflow protocol, 2 October 2026. Internal
verification results are recorded below when checks have been run. This
protocol supplies no human-data loader and does not freeze an empirical
OT-027 study. The [user guide](../m5-researcher-workflow.md) is the canonical
execution route; [decision 0054](../decisions/0054-m5-frozen-prognostic-intake.md)
records the intake conventions.

## Question and unchanged task

Can a researcher freeze a local prognostic model, compare its later-reported
insulin predictions with a simple reference, and reconstruct the comparison
without importing the model or fitting again?

Reuse the exact fixture, eligibility rules and participant split from the
[fixed synthetic M5 comparison](../m5-synthetic-prognosis.md). There are 32
invented participants: 24 development and eight evaluation, with each
participant's rows and infusion history retained in one split. Number
divisible by four assigns evaluation before fitting. Twenty development and
seven evaluation participants are eligible. Preserve all five excluded
records, their distinct reasons and all repeat infusions. Do not modify the
earlier fixture, outcome construction or historical route to improve a
candidate's metric.

The landmark is the invented V10 MMTT on day 70–80 after first infusion.
Its feature is 90-minute C-peptide divided by concurrent glucose/100, not
secretion rate or graft mass. The outcome is the mean of seven invented
daily reported insulin amounts at the first-infusion Y1 visit. V15 cannot
substitute for Y1. Missing diary entries never become zero insulin use.
Infusions after the landmark are report context, not predictor inputs.

The task checks an analysis boundary only. Its predetermined synthetic
associations are not CIT-07 participant observations and cannot establish
human prediction, treatment effect, graft survival or cure.

## Frozen source, state and provenance

Accept exactly `model.py`, `state.json` and `model.json` in a local bundle.
The declaration schema is `m5-prognostic-model/1`, with `model_id`,
`rights_basis`, `input_schema: m5-landmark-input/1`, `output_unit: U/day`,
exact source/state SHA-256 values, a runtime declaration containing current
CPython `python_major_minor` and empty `dependencies`, and training metadata.
The model ID is at most 128 characters from letters, digits and `._-`,
starting with a letter or digit.
The training metadata binds the exact fixed fixture hash,
`phase: development_only`, and the exact eligible 20-person development
alias list. This bounded contract supplies no third-party dependency host.

Hash binding proves byte identity only. Rights basis and development-only
training history are researcher attestations; matching metadata cannot
verify how model state was produced or adjudicate legal rights. Preserve the
declaration as such, with no claim of independent rights clearance or sealed
empirical evaluation. Any model adaptation after viewing held-out outputs
requires a new bundle identity and cannot be represented as untouched
held-out development.

Export an illustrative model by fitting the unchanged synthetic
added-function ridge on eligible development participants only. Save fitted
means, scales and coefficients as state. This demonstrates the interface;
it does not select an empirical model or beneficial function predictor.

## Prediction boundary and repeat rule

Expose only `predict(record, state)`. The record has exactly `schema`,
`prior_insulin_u_day`, `prior_glycemic_status_mg_dl`,
`landmark_day_after_first_infusion` and `observed_function_index`.
No participant alias, split, outcome, future visit or future infusion is
passed. The source uses frozen JSON state; prediction has no fitting phase.

Execute two separate fresh standard-library Python workers for every
eligible evaluation participant, with a default five-second budget for
each. The CLI `--timeout-seconds` permits a finite positive budget of at most
60 seconds, with the chosen value archived. Python's `random` generator is
seeded to zero per worker. Both attempts remain in the archive, including
status, prediction when valid and runtime identity. A successful pair
requires valid finite numeric values in inclusive `[0, 1000]` U/day and
exact prediction and runtime-identity agreement. Invalid types, non-finite
values, range violations, callback exceptions, worker failures, timeouts and
disagreement cannot silently disappear or become successful predictions.
A valid primary prediction remains saved if its repeat fails, but is
excluded from paired metrics. Ctrl-C, SIGTERM and SIGHUP preserve retained
records, mark the active attempt `interrupted` and show remaining attempts
as `not_attempted`. Worker process groups are cleaned up and signal handlers
restored. An uncatchable termination retains only the latest sealed
checkpoint.

Fresh processes isolate mutable Python memory between requests and repeats.
They are not a security sandbox. Candidate code must be trusted; causal
record projection is an interface guarantee, not filesystem or network
confinement. A candidate that independently reads outcomes violates the
protocol even if its JSON declaration passes structural validation.

## Reference and comparison

Use development-only standardized ridge on prior insulin amount, prior
glycemic status and landmark day, with slope penalty 1 and unpenalized
intercept. Save its preprocessing and coefficients. The candidate has the
same baseline fields plus the observed-function index and receives no
reserved outcomes. No task tuning, model selection, benefit threshold,
confidence-interval claim or empirical calibration follows from this run.

Preserve these separate metric denominators:

1. Baseline MAE over all seven eligible evaluation participants.
2. Baseline and candidate MAE over the same successful paired subset.
3. Candidate-minus-baseline paired MAE, paired coverage and all failed or
   inconsistent attempts.

Incomplete coverage explicitly limits the paired comparison. Zero paired
participants yield `null` paired metrics. A smaller error on a selected
successful subset is not an overall superiority result. Retain participant
predictions and observed outcomes in this invented report to make the
arithmetic inspectable, without sending those outcomes to workers.

## Archive and reconstruction

Preserve the declaration, source/state bytes and hashes, fixed fixture,
protocol and implementation source snapshots, saved baseline, request
records, both attempts per eligible evaluation participant, complete
roster and JSON/Markdown reports. Runtime identity (Python implementation
and version) must match across repeats; elapsed execution duration is not
a predictive score or an equality criterion. The Markdown report includes
per-attempt statuses plus model, Git revision, CPython, worker budget, lock
and source identities.

Reconstruction verifies hashes, the unchanged fixture, exact eligibility and
split, request projection, attempt accounting and metric denominators. It
checks saved development preprocessing and ridge coefficients against the
normal equations, then derives reports using saved candidate outputs and
saved baseline parameters. It neither imports candidate source nor calls
its callback, refits the baseline or executes a simulator. Archived source
identity and reconstructed arithmetic do not validate a candidate's
scientific assumptions or self-attested training history. Integrity hashes
verify saved consistency, not authenticated proof of execution. Rewriting
outputs, reports and the manifest together can produce a different
self-consistent archive; this route does not certify its execution history.

## Internal verification

On 2 October 2026, `uv sync --locked` and
`uv run --locked python scripts/check.py` passed: 760 tests and the
documentation build, including formatting, lint, Markdown, YAML, citation
and navigation checks. The 15 focused M5 tests also passed. They cover
callback projection, development-only reference arithmetic, fresh workers,
complete exclusions and repeat infusions, timeouts, exceptions, invalid
outputs, inconsistent repeats, partial/zero coverage, archive alteration
and reconstruction without candidate import or refitting. Interruption
checks include real SIGTERM, worker cleanup and restored handlers; an
interrupted atomic write retains a completed primary attempt. Saved ridge
normal equations use relative tolerance `1e-12` and absolute tolerance
`1e-10` for this fixed double-precision arithmetic, not a clinical tolerance.

The final exported bundle is `results/m5-final-example`; its two complete
archives, `results/m5-final-a` and `results/m5-final-b`, have all 17 files
byte-identical. The added-function ridge has seven successful reproducible
pairs out of seven eligible held-out participants. A distinct frozen
predictor returns the mean outcome over the same 20 eligible development
participants from its saved state; `results/m5-final-mean` also has seven
successful reproducible pairs. All three archives reconstruct without
importing candidate code or refitting. The source snapshots identify local
execution bytes beyond base Git revision `a0a10da`. A separate internal
code review left no unresolved material findings after corrections.

These are internal software and invented-data checks. No native M0, M1,
M2 or M4 experiment campaigns were rerun for this change. They provide no
human prediction, clinical, independent-user or treatment evidence.

## Later evidence gates

Human loading, release linkage, empirical model freezing and treatment
assessment remain outside this route. The
[OT-027 protocol](m5-cell-therapy-protocol.md),
[data requirements](m5-cell-therapy-data.md) and
[domain-review packet](m5-domain-review-brief.md) still require authorized
source/release identity, visit and infusion linkage, assay/renal/treatment
context, actual diary semantics, participant-disjoint allocation,
independent domain review and a separate empirical freeze before human
fitting or reserved scoring. This synthetic workflow closes none of those
criteria. Independent intended-user P1 execution remains the next external
product-acceptance step.
