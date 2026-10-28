# Internal verification

**Current public scope:** this native research route is outside the initial
two-task public exercise. Its pinned environments retain advisories and are
excluded from automatic public installation. Read the
[current runtime and CI policy](publication-security.md) before using the
historical setup commands below.

IV-001 probes numerical refinement, initialization, selected implementation faults and one-factor robustness using the existing locked engines. It is separate from the original [M1](m1-tutorial.md) and [M2](m2-tutorial.md) experiments. The [protocol](research/internal-verification-protocol.md) defines its scope; the [results record](research/internal-verification-results.md) separates measured behavior from remaining work. Sensitive results and native stops are retained, not repaired by changing a historical baseline.

## Install

Use a clean checkout, Python 3.12, uv 0.11.16 or newer, and Node.js 22.22.2 on macOS or Linux. Record `git rev-parse HEAD`. Numerical threshold freezing requires committed sources and an unmodified working tree. Repository outputs under `results/` are ignored by Git.

```sh
uv sync --locked
uv sync --locked --project experiments/m0/simglucose
npm --prefix experiments/m0/lt1 ci --ignore-scripts --no-audit --no-fund
node experiments/m0/lt1/setup.mjs
uv run --locked python scripts/check.py
```

The root environment contains tooling only. The simglucose runtime retains its documented setuptools 80.9.0 compatibility constraint and advisory; do not use it to build or publish source distributions. Native sources are downloaded at their pinned revisions, outside Git.

## Verify and execute

Every command below needs a new output path. Existing evidence is never overwritten by a simulation command. A first cold Matplotlib import may build a font cache; native execution has a bounded deadline.

```sh
uv run --locked python -m experiments.verification.verify --output results/iv/native
uv run --locked python -m experiments.verification.campaign pilot --output results/iv/pilot
uv run --locked python -m experiments.verification.campaign freeze \
  --study results/iv/pilot --criteria experiments/verification/criteria.json \
  --output results/iv/thresholds.json
uv run --locked python -m experiments.verification.campaign numerical \
  --thresholds results/iv/thresholds.json --output results/iv/numerical
```

The native verification checks reference equivalence, new processes, nominal fixed-input replay, a known native stop, timeout, cancellation, malformed initialization, changed bytes, false completion and propagation of injected worker failures. The pilot has 12 runs; the numerical matrix has 80. The existing M0/M1/M2 workflows remain separate regression requirements. Typical runtime depends on the machine; each native case is bounded at ten minutes.

The committed criteria were selected after the initial two-configuration pilot and before inspecting the full matrix. Repeating the pilot on another platform records that environment; it does not authorize changing the criteria. A source or lock change requires a new pilot/freeze record. These engineering limits do not replace historical exact comparisons or establish clinical accuracy.

## Check selected faults

```sh
uv run --locked python -m experiments.verification.mutations --output results/iv/mutations
```

This runs seven prespecified mutations in disposable source copies. Each has a passing unmodified control and a required assertion diagnostic. Import/syntax failures and timeouts do not count as detection. The original checkout remains unchanged. The output retains the exact patch, before/after source hashes, commands, environments, logs and status for every planned fault, including unattempted ones if interrupted.

The timing case also records that the earlier daily-total/once-only test survives a three-minute shift; the new pointwise check detects it. This does not imply that the entire historical suite missed that shift. The full synthetic Cambridge format fixture is a validation counterexample, not a native physiological result. A separate regression now requires M2 package provenance to match the recorded lockfile with JSON types preserved.

## Reconstruct and inspect

```sh
uv run --locked python -S -m experiments.verification.campaign report \
  --study results/iv/numerical --output results/iv/reconstructed.json
cmp results/iv/numerical/report.json results/iv/reconstructed.json
```

The reconstruction uses the standard library, not either simulator. Use the same implementation revision for identical report bytes: reports also identify the analysis source files. Each case records its configuration, protocol and locks, upstream source hashes, effective runtime settings, native diagnostic output, trace, logs and terminal status. `thresholds.json` binds the pilot input hashes, signal limits and planned matrix. Reports identify all bytes they read, including partial traces.

Glucose remains interval-mean subcutaneous glucose for simglucose and point plasma glucose for Cambridge. Insulin is actual modeled delivery, integrated over duration; terminal commands are excluded. No observed scored interval means an undefined insulin total, not zero. Replay retains its exact nominal command input and checks that delivered insulin and meals match over the common interval, including initialization.

The report has per-case coverage and status, adjacent and native-to-finest refinement comparisons, initialization comparisons, signal differences and `stable_within_prespecified_limits`, `sensitive` or `inconclusive` classifications. A full-day stability claim requires two completed scored days. Initialization changes model, controller and sensor histories together; it is not an isolated physiological parameter estimate.

## Preserve and interpret

Archive the complete directory, including failures and temporary diagnostic experiments, outside Git:

```sh
uv run --locked python experiments/m0/archive.py \
  --source results/iv --destination results/iv-archive
uv run --locked python experiments/m0/archive.py --destination results/iv-archive
```

Local preservation is not an external backup or independent reproduction. The later human M2 reproduction criterion remains open. The wider meal/information/parameter robustness matrix is described below. Passing these selected mutations is not whole-program fault coverage. No human data, controller tuning, new cohort or biological extension is part of this workflow.

## Run the frozen robustness matrix

Use the same locked environments above. Commit the reviewed source before freezing. These commands read native parameters first and freeze all 170 cases before simulating the robustness matrix:

```sh
uv run --locked python -m experiments.verification.robustness freeze --output results/iv-robust-plan
uv run --locked python -m experiments.verification.robustness run \
  --plan results/iv-robust-plan --output results/iv-robust-matrix
uv run --locked python -m experiments.verification.verify_robustness \
  --study results/iv-robust-matrix --output results/iv-robust-verification
uv run --locked python -S -m experiments.verification.robustness report \
  --study results/iv-robust-matrix --output results/iv-robust-reconstructed.json
cmp results/iv-robust-matrix/report.json results/iv-robust-reconstructed.json
```

Always choose new output paths. The frozen directory contains the exact native parameter probes, their diagnostics, each case configuration and source/lock/protocol identities. A changed checkout invalidates execution of an old plan. Keep the frozen directory alongside the matrix and archive both, including failed attempts.

The 17 variants per development configuration comprise baseline, two meal amounts, two meal times, three announcement conditions, three observation gaps, four local parameter perturbations and two additional initialization histories. The new `iv001.robust-case/1` contract preserves the existing numerical contract. Only one factor changes per case. Parameters are simglucose `kabs` and `kd` (native minute-based rate constants), and Cambridge `SIT` and `tmaxG` (native units recorded in the plan). The 0.9/1.1 factors are engineering probes, not validated biological ranges. simglucose retains its native table initial state; Cambridge recomputes native equilibrium. Controller settings and the MPC predictor remain unchanged.

The sensor audit records every native call before filtering. simglucose makes two reset measurements at minute zero and then calls its sensor each native minute; native sample cadence remains three minutes. Cambridge calls its sensor at each outer minute and produces an ideal sample every five minutes. Held controller observations never replace the saved raw measurements.

`report.json` keeps all planned cases, errors, scored coverage and delivered insulin. It reports within-controller changes and second-minus-first controller differences within each engine/profile/seed. Ranges describe the available development pairs; they are not population confidence intervals. A strict sign change against baseline is a reversal, a zero difference is a tie, and missing complete pairs give an undefined comparison. There is no pooled cross-engine ranking or global robustness pass mark. Native Cambridge/MPC numerical sensitivity remains a limitation even where controller ordering is unchanged.

Verification compares all ten robustness baselines exactly to the existing numerical workflow and repeats all 17 conditions for simglucose adult#001/101/basal-bolus and Cambridge/PID, plus two Cambridge/MPC perturbations, in new processes. It also rejects omitted sensor generation, an extra parameter change and false study completion. These are internal checks, not independent human reproduction.

The two complete local matrices produced 151 successful runs and 19 native stops each, with all 170 traces and sensor audits exactly equal within that environment. See the [evidence record](research/internal-verification-results.md) for reversals and exclusions. A native stop at the final timestamp still excludes that run from successful-run controller comparisons. Use the producing analysis commit to reconstruct a historical report byte for byte; newer readers identify their own analysis hashes.

Input-hash keys are serialized in canonical order. Verification also reverses directory enumeration and requires identical report serialization, so filesystem ordering cannot change the reconstructed report.
