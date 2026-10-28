# Run and reconstruct the M1 demonstration

**Current public scope:** this native research route is outside the initial
two-task public exercise. Its pinned environments retain advisories and are
excluded from automatic public installation. Read the
[current runtime and CI policy](publication-security.md) before using the
historical setup commands below.

M1 provides a bounded, synthetic development comparison using the unchanged pinned simglucose engine, native basal-bolus and PID formulas, and the [OT-001 protocol](research/first-experiment.md). This is runnable software from a checkout, not a published package, a completed held-out evaluation or a clinical decision tool.

## Install and verify

Use Python 3.12.13 and uv 0.11.16 or newer on macOS or Linux. A first install needs network access to obtain the pinned public upstream code. Repository access is required while the repository remains private. Start from a clean checkout of an identified OpenT1D commit:

```sh
git clone https://github.com/OpenT1D/lab.git
cd lab
uv sync --locked
uv run --locked python scripts/check.py
uv sync --locked --project experiments/m0/simglucose
uv run --locked --project experiments/m0/simglucose python -m unittest discover -s experiments/m1 -p test_native.py -v
uv run --locked --project experiments/m0/simglucose python experiments/m0/simglucose/run.py --output results/m1/native-reference
```

The root environment remains repository tooling. The separate simglucose lock is deliberately reused without adding simulation packages to the root or patching upstream sources. Runtime setuptools 80.9.0 supplies the deprecated `pkg_resources` API; its known limitation and advisory remain documented in [maintenance](maintenance.md#m0-runtime-compatibility). Do not build or publish source distributions from that environment.

The native tests compare the original adolescent tutorial directly against the adapter and its reset, require a reviewed historical digest, exercise both reference controllers, validate native states and check randomization, announcements and masking. The standalone M0 command additionally checks the exact environment/source context against its historical baseline. No tolerance is introduced by M1.

## Run one configured case

The [example configuration](../experiments/m1/example.json) selects development profile `adult#001`, seed 101, basal-bolus and condition A:

```sh
uv run --locked --project experiments/m0/simglucose python -m experiments.m1 run \
  --config experiments/m1/example.json --output results/m1/example
```

Use a new output directory every time. Existing output, including failed attempts, is never overwritten. Missing configuration files and invalid JSON/configuration create a failed manifest rather than silently applying defaults. Unknown fields, evaluation profiles, seeds outside 101–110, unsupported controllers and unsupported conditions are rejected. All scenarios use the fixed two-day schedule, 48-hour horizon and second-day scoring from OT-001. There is no arbitrary engine, patient-data or parameter-tuning interface.

Supported configuration fields are `schema` (`opent1d.simglucose/1`), `profile` (`adult#001` or `adult#002`), integer `seed` (101–110), `controller` (`basal_bolus` or `pid`) and `condition` (`A`, `B`, `C` or `D`). Omitting a field uses the example's value. An invalid example is `{"profile": "adult#003", "seed": true}`: neither evaluation data nor a boolean seed is accepted.

Conditions A–D change only the scored day: full, absent or half meal announcements, or a 30-minute observation mask at noon. True meals remain identical. Masking occurs after native sensor generation; controllers hold the last available observation with its original time. Announcements still arrive once. Native insulin clipping and quantization are unchanged; both commanded fields are rates in U/min, including the native field called `bolus`.

## Build the comparison

```sh
uv run --locked --project experiments/m0/simglucose python -m experiments.m1 demo --output results/m1/demo
uv run --locked --project experiments/m0/simglucose python -m experiments.m1.verify \
  --study results/m1/demo --output results/m1/verification
```

The demo schedules 32 runs before executing any: two development profiles, seeds 101–102, two controllers and four conditions. This small development subset demonstrates the workflow and seed variability; it is not the protocol's full evaluation population or a powered study. No gains or profiles were selected based on comparative performance. Runtime is per-attempt wall time including initialization, provenance collection and recording; first-use imports/cache construction can make the first run slower. It is not an isolated solver benchmark.

The verification command first checks all 32 cases against the independently archived pre-review M1 collections in `experiments/m1/baseline.json`. Configuration, native source, locked packages, effective settings and initial/interval output must match a recorded collection exactly. Collections cannot be mixed, and an unfamiliar trajectory fails verification even if fresh replay would repeat it. Preserve and investigate a mismatch before proposing a baseline change; do not enroll new output to make CI pass. The [evidence record](research/m1-reproduction.md#critical-review-corrections) explains the three historical collections.

It then repeats both controllers with condition D in fresh processes, plus the seed-102 PID termination case. Initial observations, every completed interval and native diagnostic CSV must be byte-identical within the environment. It also reconstructs the report with Python's `-S` option, which removes installed third-party packages, and requires byte-identical report files. This demonstrates reconstruction without importing or rerunning the simulator.

Open `results/m1/demo/report/report.md` for the readable comparison and `report.json` for full metrics and provenance. The report retains all scheduled runs, warnings, errors, runtimes, exposure below 54 and 70, exposure in 70–180, upper-threshold exposure, weighted mean, population SD/CV, modeled delivered insulin and sensor coverage. Pair seed-matched complete runs, average within profiles and then summarize profiles equally. Excluded pairs and their statuses remain explicit. Seed ranges characterize simulator variability; they are not confidence intervals for people.

The local development demonstration produced 28 complete runs and four native terminations. For `adult#001`, seed 102, PID crosses the native lower stop boundary during initialization at minute 1077 in all four conditions, before their scored-day perturbations begin. Direct native and adapted execution agree exactly through this stop. These cases remain in the scheduled denominator; their unobserved scored day has undefined glucose statistics and zero observed coverage. The readable report also marks delivered insulin undefined when no scored interval exists, and displays observed minutes and the final simulation time. JSON retains the metric-version-1 sum over observed intervals together with its zero duration. Sign reversal across profiles is undefined when fewer than two profiles have complete pairs. Do not tune away, omit or fill these failures. A weak reference's low glucose is not a defect to conceal, and the much lower native terminal threshold is not the metric's hypoglycemia threshold.

## Reconstruct later

Keep the entire study directory and the recorded implementation revision. No engine execution is required:

```sh
uv run --locked python -m experiments.m1 report --study results/m1/demo --output results/m1/rebuilt-report
```

The command verifies the complete sealed artifact inventory, required provenance, finite numbers, warning records, the supported protocol, interval order, controller observation history, meals, masking and study/run status consistency. Symlink artifacts and files changing during reconstruction are rejected. A changed metric/contract implementation requires its recorded revision rather than silently applying a new analysis. Reports use `opent1d.report/2` and record current analysis source hashes and the hashes of the exact input bytes consumed, including unsealed traces. Thus two different partial traces cannot produce different statistics under an identical report input identity. Rebuilding with identical source and artifacts produces identical output. Missing or modified inventoried files fail reconstruction; hashes establish integrity against the manifest, not authenticity without a trusted external inventory.

Each run stores its requested configuration, initial snapshot, completed-interval JSONL trace, native diagnostic CSV, copied protocol/lock/baseline, effective controller/pump/solver settings, installed source hashes, dependency versions, platform, warnings, logs, runtime, implementation revision and dirty-tree flag. Native diagnostics may contain a failing interval beyond the validated trace and never contribute to metrics. A secondary diagnostic-export error is recorded separately and preserves the original simulation failure. Raw or private patient data are not used or requested.

## Failure and interruption semantics

A single `run` exits nonzero after a native termination or execution failure. The batch `demo` exits successfully when all scheduled attempts and their report are recorded, including faithfully recorded native terminations; it exits nonzero for execution exceptions. Always inspect `study.json` and report status counts. CI verifies preservation and replay of terminations, not that every controller completes.

SIGINT, SIGTERM and the default 300-second per-run deadline record `interrupted` and preserve completed trace records. Set `--timeout-seconds` for an individual run when needed. The batch stops after interruption and leaves unattempted cases visibly scheduled. A catchable interruption during a write can also retain an explicitly flagged trailing fragment. A hard kill cannot run cleanup: `started` remains unfinished, and reconstruction reads only complete newline-terminated checkpoints, explicitly recording any discarded trailing fragment. Ignore temporary `.tmp` files. This is process-interruption recovery, not a guarantee against filesystem loss, power failure or an interrupted manifest write. Never infer completion solely from a full-looking trace.

## Evidence and limits

The [M1 evidence record](research/m1-reproduction.md) maps acceptance criteria to tests and preserved artifacts. [Decision 0003](decisions/0003-m1-interval-contract.md) records time, units, process ownership and the deliberately bounded contract. The [roadmap](../ROADMAP.md) owns subsequent work.

This establishes software behavior for the documented synthetic workflow. It does not establish agreement with an independently published numerical reference, independent researcher reproduction, authorized patient-data access, external biological validity, a stronger controller comparator or clinical superiority. The separate [M2 workflow](m2-tutorial.md) now reassesses LT1/APS and integrates Cambridge; those additions do not change the scope or results of this M1 demonstration. M1 does not implement a general multi-engine host. No package release or public artifact distribution is claimed.
