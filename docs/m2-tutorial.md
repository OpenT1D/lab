# M2 tutorial: separate native model tracks

**Current public scope:** this native research route is outside the initial
two-task public exercise. Its pinned environments retain advisories and are
excluded from automatic public installation. Read the
[current runtime and CI policy](publication-security.md) before using the
historical setup commands below.

This checkout-based workflow runs the [OT-014 protocol](research/m2-protocol.md) with intact simglucose and LT1 Cambridge engines. It adds controlled LT1 PID/MPC references, separate signal semantics, a frozen evaluation gate and reports rebuilt entirely from saved artifacts. The [M1 tutorial](m1-tutorial.md) remains canonical for the original demonstration. There is no general plugin API, published simulator package or clinical-use claim.

## Install the locked environments

Use macOS arm64 or Linux x86-64, Git, uv, Python 3.12 and **Node 22.22.2**. Network access and repository access are required for initial installation. From a clean checkout of the commit being reproduced:

```sh
uv sync --locked
uv sync --locked --project experiments/m0/simglucose
npm --prefix experiments/m0/lt1 ci --ignore-scripts --no-audit --no-fund
node experiments/m0/lt1/setup.mjs
uv run --locked python scripts/check.py
```

The root Python environment runs orchestration and analysis only. Physiology runs in separate native processes. Do not install simglucose into the root environment or vendor downloaded sources. The [legacy runtime advisory](maintenance.md#m0-runtime-compatibility) still applies: runtime setuptools 80.9.0 supplies upstream `pkg_resources`; the separate build constraint is 84.0.0. Do not build or publish source distributions from that runtime.

## Verify native behavior

Retain the original [M0 references](research/m0-reproduction.md) and M1 checks. M2 adds:

```sh
TS_NODE_PROJECT=experiments/m0/lt1/tsconfig.json node \
  --loader ./experiments/m0/lt1/node_modules/ts-node/esm.mjs \
  --test experiments/m2/test-native.mjs
uv run --locked python -m experiments.m2.verify --output results/m2/native-verification
```

The native suite compares direct and bounded LT1 execution under both controllers and A–D, native reset and the original historical M0 digest. Process verification checks exact fresh-process replay, SIGINT/SIGTERM/deadline retention and reconstruction with `python -S`. These checks reproduce software behavior, not a paper figure or independent biological evidence. Loader deprecation warnings remain in logs.

## Run and verify development

```sh
uv run --locked python -m experiments.m2 demo --output results/m2/development --workers 4
uv run --locked python -m experiments.m2 verify-study \
  --study results/m2/development --output results/m2/development-verification
```

All 40 runs are scheduled before any execution: 32 original simglucose development cases and eight Cambridge structural cases. Up to four independent run processes execute concurrently; `--workers 1` runs sequentially. This changes scheduling, not physiological cadence. Existing output paths are rejected. Preserve failed attempts and use new paths for retries.

The original four simglucose PID stops remain failures in the planned denominator; they must not be tuned away. Verification requires all 32 original initial/trace digests to match **one entire retained M1 collection**, with matching configuration, packages and native context. Cambridge's MPC/A case additionally matches the previously retained PR #14 native and point traces in [its historical baseline](../experiments/m2/baseline.json). That reference existed before study orchestration; no new run is automatically enrolled and no tolerance is applied.

Reports are written to `report/report.json` and `report/report.md`. They include each attempted/unattempted case, status, scored coverage, delivered amount, per-condition failures, paired changes, profile/seed ranges and conditional rank/sign reversals. Null means undefined or insufficient evidence. The direction table compares separately labeled complete systems, not matched patients or a pooled controller ranking.

## Freeze before evaluation

Commit and verify the final implementation first. The development cases must have been run from that exact clean commit. Evaluation profiles adult#003–010 cannot run without a frozen plan:

```sh
uv run --locked python -m experiments.m2 freeze \
  --development results/m2/development \
  --native-verification results/m2/native-verification \
  --output results/m2/evaluation-plan.json
uv run --locked python -m experiments.m2 evaluate \
  --plan results/m2/evaluation-plan.json --output results/m2/evaluation --workers 4
uv run --locked python -m experiments.m2 verify-study \
  --study results/m2/evaluation --output results/m2/evaluation-verification
```

The plan records the exact revision, protocol, source and lock hashes, verified development identity and all 648 scheduled configurations. Of these, **640 are simglucose evaluation cases** (eight unused adult profiles, ten evaluation seeds, two controllers, four conditions). The eight Cambridge cases remain a repeat of the single structural development parameterization. They are not an invented held-out cohort, and their ideal devices do not supply stochastic or population uncertainty.

Changed source, locks, protocol, an unclean checkout or a different commit blocks execution. No tuning is planned. If evaluation has been inspected and a later scientific/software correction changes its interpretation, preserve the original study, disclose evaluation reuse and version the protocol/gate instead of claiming an untouched evaluation again. Repeating identical frozen software for reproduction does not authorize tuning.

## Reconstruct without either simulator

From the recorded checkout, keep the entire study directory:

```sh
uv run --locked python -S -m experiments.m2 report \
  --study results/m2/development --output results/m2/reconstructed-development
```

No simulation package is imported by reconstruction. The report validates sealed inventories, required provenance, finite signals, timestamps, observation history, announcement delivery, planned counts and status consistency. It identifies the exact bytes consumed, including unsealed traces. Reconstructing unchanged artifacts with unchanged analysis produces identical report bytes. A different analysis revision must not silently reinterpret old results; use the recorded checkout. Raw histories, native source inventories, full effective settings, environment, warnings/logs and input/lock copies remain with each run.

## Supported combinations and conventions

| Track | Supported physiology/controller | Observation and action meaning |
| --- | --- | --- |
| simglucose | Pinned native engine with its basal-bolus or PID | Three-minute mean subcutaneous glucose; commands and modeled delivery in U/min |
| LT1 Cambridge | One native reference parameterization with LT1 PID or MPC_Hovorka2004 | Plasma Gp points; IdealCGM samples and native controllers every five minutes; commanded/modeled infusion in U/h |

Both tracks keep the same intended meals, information conditions and two-day horizon, but native ingestion, controllers, populations and compartments differ. Cambridge ingests meals over 15 minutes; its MPC predictor assumes that duration. A once-delivered announcement remains permissible history for that predictor. Native PID implementations are different formulas, targets and initializations. MPC is LT1's implementation of a published method, not a demonstrated exact reproduction of all Hovorka 2004 paper details; the original paper's fasting evidence does not validate this meal experiment.

Cambridge's native loop supplies one-minute callbacks for this fixed protocol. An internal fixture checks shortened fractional event intervals; the public reader deliberately accepts only the specified protocol grid. Point metrics use duration-weighted left endpoints and exclude terminal commands. Integrate modeled U/h over actual elapsed minutes divided by 60. Do not sum commands, add a bolus again, treat plasma as tissue glucose or reinterpret point threshold exposure as measured continuous time in range. Bolus-producing LT1 controllers and arbitrary device/profile substitutions are rejected because the selected pump's shortened-step bolus semantics are not established.

## Failures and independent reproduction

A native terminal flag, execution error or missing signal remains visible. A single non-complete case exits nonzero. The study completes all planned attempts despite case failures; it exits nonzero for execution errors while preserving its report. SIGINT/SIGTERM and a per-run 300-second deadline retain checkpoints and logs. A hard-killed supervisor remains `started`; its Node worker stops at the next callback when it detects the missing parent. A full-looking trace alone is never successful completion. This is process recovery, not a storage-loss guarantee.

Another person must execute this tutorial on the exact reported commit, including installation, native checks, development, frozen evaluation and simulator-free reconstruction, then record their environment, commands, status counts and deviations using [the result template](../experiments/m2/reproduction-result.example.json). Local tests, CI, another AI session or a subprocess do not satisfy independent human reproduction. Do not fill in a person or success that has not occurred.

Verify and transfer the preserved bundles with the [archive procedure](research/m0-reproduction.md#local-evidence-archive) and [M2 evidence index](../experiments/m2/evidence-index.json). New clones do not automatically obtain the maintained local archive. It is not a public release, offsite backup or independent reproduction. The [M2 evidence record](research/m2-reproduction.md) tracks attained acceptance and remaining limits.
