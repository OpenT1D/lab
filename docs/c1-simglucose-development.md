# C1/0.3 simglucose development route

This route connects the [selected C1 trend overlay](research/c1-method-feasibility.md)
to the existing M1 simglucose development loop without changing M1 or M2.
It also provides an adapted **bounded PID comparator**. This is a software
and development preflight on already inspected adult profiles; it is not a
held-out test, a strong-comparator eligibility verdict or an insulin dosing
tool. The [C1/0.1 protocol](research/c1-controller-protocol.md) retains the
benefit and non-degradation criteria for later assessment.

## What runs

The M1 native simglucose engine still owns the patient, sensor, pump, meal
schedule, three-minute steps and stop condition. Its information boundary
releases the same held/fresh CGM and event-time announcements to both C1
methods. The native basal-bolus controller computes a base basal rate and
bolus from those permitted inputs. The candidate adds the C1 trend overlay
to the **basal rate only**, converting U/min to U/h for the shared kernel and
back. It never changes the native bolus. Its proxy remembers commanded C1
extra rate, not actual insulin-on-board.

The comparator uses the same basal-bolus base action plus the pinned M1
native PID formula as a feedback correction. It clamps the resulting basal
rate to zero and the declared maximum, and limits upward changes. This is
an **adapted** PID, not a reproduction of the unchanged native PID or a
verified strong comparator. Both methods keep the base bolus unchanged.
The common `max_total_u_h` limits the **basal rate**, not a simultaneous
meal bolus. Command, modeled delivery and actual patient state remain
different concepts. None of these development limits is a clinical limit.

The example JSON files contain invented engineering settings for a smoke
test. They are not tuned gains or a recommended dose. The route accepts
only adult#001–002, seeds 101–110, conditions A–D and one of its two
original C1/0.3 methods. The later
[C1/0.7 route](research/c1-feedback-development.md) adds two feedback
methods with a separate setting contract. C1 evaluation profiles and new
meal rosters are rejected.

## Run and reconstruct

From the repository root, after the locked M0 simglucose setup described in
the [M1 tutorial](m1-tutorial.md), run separate native processes:

```sh
experiments/m0/simglucose/.venv/bin/python -m experiments.c1.simglucose_dev \
  --config experiments/c1/simglucose-overlay.example.json \
  --output results/c1-overlay-dev
experiments/m0/simglucose/.venv/bin/python -m experiments.c1.simglucose_dev \
  --config experiments/c1/simglucose-pid.example.json \
  --output results/c1-pid-dev
```

Each output directory must be new. `manifest.json` identifies the method,
source/lock context, status, exact file hashes and partial row counts.
`trace.jsonl` records completed M1 intervals; `commands.jsonl` separately
records base, correction, final action and observation origin. The initial
sensor, native diagnostic and runtime source inventory are retained. A
captured warning list and process log accompany the run. A
native stop or interrupted/error run remains visible, with no filled tail.
The standard-library reader checks file hashes, row continuity, meal and
sensor boundaries, independently replays the C1/PID state updates, and
checks the action/trace relationship:

```sh
uv run --locked python - <<'PY'
from experiments.c1.report import read_case
for name in ('overlay', 'pid'):
    report = read_case(f'results/c1-{name}-dev')
    print(name, report['status'], report['completed_rows'], report['metrics'])
PY
```

`read_case` does not import simglucose. It can reconstruct a partial report
after a failure, but a started/unsealed hard-kill artifact cannot be called
complete. A changed command with a recomputed file digest still fails the
command/trace consistency check.

A separate zero-gain overlay authoring run on the same adult#001/101/B case
matched the unchanged M1 basal-bolus `initial.json`, all 960 `trace.jsonl`
rows and `native-diagnostic.csv` **byte for byte**. This verifies the
adapter's native base path for that configuration; it does not prove
equivalence for all profiles, settings or platforms.

## Local development finding

The initial authoring attempts are retained separately. The following
development runs use clean exact commit `95342bc` on known adult#001/seed
101, condition B, with the example settings. They are **not** held-out
evaluation. The unchanged M1 basal-bolus run and both C1 routes completed
all 960 intervals. The
scored-day M1 interval summaries were:

| Method | 70–180 mg/dL exposure | Below 70 mg/dL | Below 54 mg/dL | Above 250 mg/dL |
| --- | ---: | ---: | ---: | ---: |
| Unchanged basal-bolus | 35.833% | 16.667% | 0% | 22.292% |
| Example C1 trend overlay | 35.625% | 16.875% | 0% | 22.292% |
| Example bounded PID | 46.875% | 0% | 0% | 34.583% |

The example overlay worsened the in-range and below-70 measures relative to
its base in this one known case. The bounded PID traded away high-extreme
exposure. Both show adverse directions under the proposed C1 constraints;
neither is a frozen C1 verdict. These numbers are
development diagnostics for one synthetic profile/seed, not estimates of
population performance, method superiority or patient benefit. They must
remain visible if settings are changed later.

Separate clean D-condition runs for both methods also completed 960
intervals. The overlay added zero extra basal rate at all ten masked
controller updates, while the native sensor stream continued. These runs
verify this selected boundary only; they do not assess a new scenario.

All six C1 clean runs were read with the simulator-free reader, and their
recorded revision and source hashes match commit `95342bc` with a clean
worktree. The overlay B run was repeated in a fresh process: initial,
trace, command-audit and native-diagnostic bytes all matched. The zero-gain
run also matched the unchanged M1 B run on initial, trace and diagnostic
bytes. The [local evidence index](../experiments/c1/evidence-index.json)
identifies all seven clean directories by manifest hash. Each C1 manifest
also inventories every output file; the index identifies a local ignored
store, not an external backup.

## Remaining gates

The [C1/0.4 known-case matrix](research/c1-known-development-matrix.md)
now preserves all 64 planned base, overlay, adjusted-overlay and PID
development attempts. Its targeted adjustment removes the one observed
B low-boundary regression but adds no B in-range gain; the bounded PID
completes the matrix but shows major outcome reversals. These are negative
development findings, not an evaluation verdict.
The [C1/0.5 audit and method revision](research/c1-method-revision.md)
retire this first overlay as the lead while preserving its code and results.
The [C1/0.7 matrix](research/c1-feedback-development.md) subsequently
adds the redesigned feedback adapter, a matched zero-rise comparison and
48 completed known-case native runs, with mixed candidate/base outcomes.

The C1 route does not yet implement Cambridge, a sealed new-scenario roster,
profile-level uncertainty, a full comparable development budget or a
verified strong simglucose feedback comparator. Before any held-out claim,
record all development attempts, settle comparator eligibility and coverage,
verify both native adapters and freeze the exact code, settings, cases,
statistics, failure policy and numerical criteria. The inspected M1/M2/IV
cases cannot become untouched C1 evidence.
