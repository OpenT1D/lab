# BC-008 readiness: source choice and basal preflight

This historical BC-008-P1 report describes the completed preflight. The subsequent [feedback implementation and results](m4-feedback-results.md) are recorded separately.

The next OT-026 step has produced a [glucose-feedback protocol](m4-feedback-protocol.md), a [selected source model card](models/dallaman2007-secretion.md) and an executable preflight. **Only pointwise algebra and native derivatives have been evaluated. No new coupled glucose trajectories or insulin-requirement result are claimed.**

Work continues in `/private/tmp/opent1d-beta-cell-reference`, branch `codex/beta-cell-reference`, from `ac1e63f`. [Decision 0023](../decisions/0023-bounded-glucose-feedback-protocol.md) and the [source register](../../experiments/m4/feedback/sources.json) document the choice. BC-001 through BC-007, upstream physiology, scientific locks and the original working directory remain unchanged.

## Decisions now concrete

The proposed source is Dalla Man 2007 equations 23–26, with static and positive-glucose-slope control plus portal transit. Its small published system covers the rising/falling input structure needed for a meal-loop experiment. Its coefficients and source population do not establish residual T1D or graft validity. BC-001's reduced declining-IVGTT model remains a separate, unchanged reference. The full granule-distribution model would require a larger separate implementation.

The protocol fixes the native profile, a fasting and initial-gastric-load scenario, basal replacement, two source states, same-stage feedback, five primary cases, replay and equal-arrival controls, solvers, numerical tolerances, stopping rules and reconstructible outputs. The selected gain is a hypothetical coefficient scale. No new parameters or thresholds were estimated from coupled glucose results.

At the published lower branch the signed Y state can be negative, while total pancreatic appearance remains nonnegative. The proposed Z=Y+Sb change of variable preserves this behavior. It also separates pancreatic appearance Spo from delayed liver arrival S. A clamp on Y or a second liver injection of Spo would change the model.

## Executed preflight

The [contract arithmetic](../../experiments/m4/feedback/contract.py) constructs initial conditions and evaluates source equations at individual points. The [preflight runner](../../experiments/m4/feedback/preflight.py) verifies the installed upstream revision and file hashes, evaluates the existing native derivative, records evidence and reconstructs the checks without numerical packages. It does not integrate the source or glucose feedback.

For the native virtual profile, r=0.25 replaces a declared quarter of SC basal appearance. Matching plasma insulin requires a liver input 2.5 times the displaced SC appearance because of the fixed native hepatic loss. This factor follows from native `(m1+m30)/m1`; it is not a measured universal first-pass fraction or transplant coefficient.

| Quantity | Native baseline | Replacement baseline |
| --- | --- | --- |
| Plasma glucose (mg/dL) | 138.56 | 138.56 |
| Plasma insulin (pmol/L) | 100.25 | 100.25 |
| SC basal input (pmol/(kg min)) | 1.238624414 | 0.928968310 |
| Endogenous liver arrival (pmol/(kg min)) | 0 | 0.774140259 |
| Liver inventory (pmol/kg) | 3.207625051 | 5.212390709 |
| Portal inventory (pmol/kg) | 0 | 1.548280517 |

The SC depots are also reduced by a quarter; native plasma insulin and all other baseline states are retained. This is a checked initialization construction. No simulation has shown what follows after a gastric load.

| Executed check | Maximum discrepancy | Prespecified limit |
| --- | --- | --- |
| Change in full native basal derivative | 1.20493e-12, each component's native unit/min | 1e-8 |
| Basal plasma glucose/insulin change | 0 | Exactly zero |
| Insulin inventory derivative balance (pmol/(kg min)) | 1.11023e-16 | 1e-10 |
| Shifted versus signed source equation, pointwise | 5.55112e-17 in rate-derivative/source-rate units | 1e-12 |
| Native zero extension and inlet locality, including negative-liver guard probe | 0 | Zero and 1e-12 respectively |

The original native initial derivative is not mathematically zero to every stored decimal: its largest component is 3.84884e-11 in that state's native unit/min. The preflight tests preservation of this baseline, rather than silently recalibrating the profile. A later fasting trajectory has its own drift criterion.

## Reproduce

Run from the worktree root with fresh output paths:

```bash
uv sync --locked
uv sync --locked --project experiments/m0/simglucose
uv run --locked python -m experiments.m4.feedback.preflight \
  --output results/m4-feedback-preflight/my-reference
uv run --locked python -S -m experiments.m4.feedback.preflight \
  --reconstruct results/m4-feedback-preflight/my-reference \
  --output results/m4-feedback-preflight/my-reconstructed.json
cmp results/m4-feedback-preflight/my-reference/report.json \
  results/m4-feedback-preflight/my-reconstructed.json
```

The archive includes the future protocol, source register, code and lock snapshots, native identity/parameters, initial states, original/modified derivatives, guard probes, report, logs and complete/failed status. Existing directories are refused; an interrupted or failed native check stays failed and cannot be reconstructed as complete. Reconstruction verifies hashes and recomputes checks from saved derivative values; reevaluating the native derivative requires the full preflight command. Hashes do not authenticate a deliberately rewritten archive.

Root and native locked synchronization passed. Thirteen new root tests independently check a hand-balanced two-compartment example, the route conversion, below-basal behavior, source/arrival distinction, threshold continuity, zero gain, invalid inputs, changed protocol/pin, missing cases, incorrect derivative/locality, interruption and overwrite refusal. The preflight passed in the pinned native environment. A fresh-process repeat and `python -S` report reconstruction match exactly except for run-specific manifest metadata. The [execution record](../../experiments/m4/feedback/execution.json) supplies file hashes and final repository-check results. Commands:

```bash
uv run --locked python -m unittest tests.test_m4_feedback -v
uv run --locked python scripts/check.py
```

Protocol `/1` preflight attempts are retained. Before any feedback implementation, protocol `/2` separated the prospective closed-form tolerance for rate state Z from the tolerance for amount state P; both remain 1e-7 in their respective units. No preflight criterion or scientific parameter changed. The current implementation also reconstructs those earlier preflight archives. Final evidence is `reference-02`, repeated as `repeat-02`. There were no failed scientific preflight attempts and no numerical threshold relaxations.

## Roadmap handoff

This completes the requested protocol and compatibility-preflight step. The next implementable work is a standalone Dalla Man source reference with independent analytical checks, then the frozen BC-008 monolithic feedback experiment. Its zero-extension, fasting, replay, conservation and refinement checks remain unexecuted; passing preflight is not a substitute.

OT-026 and M4 remain partial. Source/biological review, population-specific baseline/responsivity, human identifiability and independent observations remain open. OT-024/OT-015 and the previous OT-025 results retain their scope. Later OT-027 requires a concrete graft/site or other intervention mechanism with evidence linking treatment to function. No messages, data-access applications, participant-data downloads, push or publication occurred.
