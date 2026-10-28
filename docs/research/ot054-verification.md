# OT-054 bounded Task 1 verification

This record assesses the shared observation core and first paired meal-test
task within the [OT-053 narrow decision](ot053-mmtt-feasibility.md).
It covers invented observations, fixed explicit kinetics and engineering
uncertainty only. Human execution, empirical T1D validity, independent
researcher usability and comparative product value remain unestablished.
The [canonical guide](../observation-analysis.md) owns execution instructions;
the [roadmap](../../ROADMAP.md#planned-mixed-meal-analysis-tasks) owns scope.

## Contract and reuse

The controlled core is commit `23e1bc12bc52b2443dca4f6157c474df1e9188f8`,
with its handoff at `a8a85fe`. GUI integration preserves all shared estimator,
preprocessing, perturbation and report source hashes. Decision
[0068](../decisions/0068-synthetic-observation-analysis-contract.md) fixes the
observation/plan/report contracts. The initial `core-verification.json` is a
historical core-only checkpoint; this record owns integrated acceptance.

| Requirement | Implementation and evidence |
| --- | --- |
| Local observations and actionable validation | Strict synthetic metadata/CSV, explicit units, actual times, participant-owned allocation, two linked visits, original bytes and complete visit errors; absent/censored records remain explicit |
| Frozen method and assumptions | OT-053 endpoint: whole-body total including basal over measured 0–120 minutes; exact piecewise-linear concentration integration of the attributed two-compartment equations; explicit initial peripheral inventory; original inputs, protocol, settings, ancestry, source and runtime sealed before evaluation |
| Prespecified variants and uncertainty | Ordered required variants, frozen synthetic error SDs/seed/count and keyed shared perturbations; every draw repeats initialization and integration; failures never removed to calculate an interval |
| Full report and interpretation | Paired totals/change, per-visit and paired conditional intervals, minimum rates, measured references/glucose/context, all participant/variant/draw denominators; frozen three-way classification; zero-crossing intervals remain unresolved |
| Local GUI | Input inspection, editable fixed plan, readiness invalidation, saved-plan reuse, one owned operation, cancellation, complete/incomplete report rendering and original JSON/Markdown downloads |
| Saved analysis and library | Explicit common-entry/catalogue reader; reconstruction replays the same fixed variates/algebra, checks retained attempts and identical report bytes; GUI library uses that reader and the shared report renderer |
| Companion-task boundary | `evaluate(settings, package, csv_raw)` receives only supplied observations; OT-055 must mask before initialization/interpolation/uncertainty, with no full-curve learned state |

## Numerical and native controls

Core tests cover equilibrium totals, explicit initial inventory, independent
RK4 mass balance, high-precision small intervals, scale covariance, continuous
negative-rate minima, complete paired uncertainty and all required failures.
An independent one-compartment Gaussian calculation checks perturbation
variance, paired covariance and interval width under prespecified 15%/25%
engineering tolerances. It establishes no human interval coverage.

The separately locked BC-003 analytical and ODE paths agree with the inverse
implementation under the prespecified refinement check. Against a known
25,200 pmol synthetic input, errors are 197.7902, 1.13671, 0.0454334 and
0.00283950 pmol at 15, 5, 1 and 0.25 minutes. The coarse case has a negative
local rate and remains a boundary failure. The finest grid meets the declared
relative 1e-4 criterion. This is numerical agreement, not MMTT validity or a
sampling recommendation.

Real native CLI/common-entry/catalogue runs cover consistent increase,
assumption-dependent, unresolved and censored controls. Reports reconstruct
byte for byte after fresh-process execution and relocation. Resealed forged
attempts are rejected. Real SIGTERM and GUI cancellation preserve eight
declared participants as unavailable when the atomic calculation is unfinished;
no successful subset is fabricated.

## GUI and browser verification

Real HTTP jobs execute import, freeze, native check/run and reconstruction for
all four controls, with no fake worker or estimator. Separate archive copies
of complete and censored cases are indexed/reconstructed through the library.
Original JSON/Markdown downloads equal both source and reconstructed bytes.
Checks also cover human-declaration refusal before CSV access, changed input
hashes, path/symlink rejection, origin/token checks, invalid CSV retention,
single-operation ownership across tasks, cancellation cleanup and restart
verification labels. Changed report bytes withdraw both downloads; restoring
the original evidence allows explicit verification again.

Controlled frontend checks run shipped JavaScript against actual native reports.
They cover values/classifications, measured references, censored failures,
literal unsafe text, readiness invalidation, stale inspect/report responses,
download selection and preservation of expanded details across an unchanged
reconstruction. These are controlled DOM tests, distinct from the actual
local browser exercise.

The actual browser exercise uses the real loopback service and four supplied
synthetic controls. Its recorded artifacts and displayed-value audit live
under ignored `output/playwright/`; no participant records are used. The
machine-readable integration receipt binds the exact implementation and
verification outcome. The four reports have 252 displayed table cells matching
native values with documented rounding. Original JSON/Markdown downloads are
byte-identical. The 390-pixel viewport has no horizontal page overflow, and
manual saved-result selection survives passive polling after reconstruction.

## Verification commands and limits

The integration check uses the repository's locked workflow:

```sh
uv sync --locked
uv run --locked python scripts/check.py
```

The separate numerical reference uses the existing BC-003 lock:

```sh
uv sync --locked --project experiments/m4/beta_cell/runtime
uv run --locked --project experiments/m4/beta_cell/runtime python \
  -m unittest experiments.observation_analysis.test_numerical -v
```

The complete locked repository check passes: 1,320 tests run with 13 skips
for the separate C1 PyTorch runtime, and the strict Sphinx build succeeds. The
final GUI navigation/cancellation regression checks also pass separately.

See `experiments/gui/observation_verification.json` for the final command
outcomes, test counts, source hashes and browser evidence. A repository pass
does not establish model validity. No upstream R dependency/code is adopted;
the native R/full-package/spline route remains separately unqualified. Assay
precision, adult T1D kinetics, authorized complete paired observations, a held-out
empirical assessment and the independent six-researcher comparative pilot
remain separate gates. No clinical threshold, treatment claim or user-time
saving is inferred from these synthetic checks.
