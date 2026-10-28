# BC-004: executed paired-boundary preparation

The [paired protocol](m4-paired-protocol.md) is specified and its boundary preflight is implemented. It translates an explicit synthetic secretion signal into separate insulin and C-peptide inlet requests, keeps basal/evoked components separate, proposes consistent initial inventories and checks dimensional/accounting identities. **No paired ODE trajectory, empirical validation or therapy effect is computed.**

Work continues in `/private/tmp/opent1d-beta-cell-reference`, branch `codex/beta-cell-reference`, from `166da30`. Existing BC-001/002/003 code, source evidence and scientific runtime locks are unchanged. The [machine execution record](../../experiments/m4/paired_observation/execution.json) stores protocol/source/result hashes and actual check outcomes. Source snapshots identify the precommit implementation.

## Executed demonstration

Run `results/m4-paired/reference-01` passed all four frozen cases. Each branch receives the following integrated input:

| Case | Input amount (pmol/kg) | Initial-state convention |
| --- | --- | --- |
| Zero increment | 0 | All increments zero |
| Extra pulse | 180 | All increments zero |
| Pulse plus synthetic basal | 540 | Separate stationary insulin and C-peptide inventories |
| Mass-rate ramp | 293.1978107896794 | All increments zero |

Paired-rate and analytic input-accounting discrepancies are zero at recorded floating-point precision. The maximum stationary derivative residual is 2.220446049250313e-16 pmol/(kg min), below the frozen 1e-10 criterion. These checks concern boundary arithmetic and initialization; they are not numerical solver or biological validation.

A separate check in the existing locked simglucose environment verifies the actual pinned source/parameter hashes, compares the proposed coefficients/body mass/volume with the installed virtual profile, and evaluates its native insulin derivatives at the proposed baseline states. Its maximum residual is also 2.220446049250313e-16 pmol/(kg min). This checks the stationary algebra against the existing engine, without integrating a trajectory or interpreting its carrier glucose states. The execution record includes the probe source hash and native identity.

In the synthetic-total case the proposed initial plasma insulin is 48.56193640241637 pmol/L and C-peptide 440.39929536112743 pmol/L. Equal molar input does not produce equal concentrations. These are algebraic equilibria at a declared synthetic baseline, not observed participant values or a combined virtual patient's fitted physiology.

Separate-process repetition produces all eight deterministic artifacts byte-identically. A standard-library reconstruction with `python -S` reproduces `preflight.json` byte-identically, without a simulator or execution of saved Python. Tests exercise hand-calculated pulse/triangle amounts, mass conversion, one-time normalization, distinct stationary inventories, baseline duplication, wrong units/scope, mismatched body mass, nonfinite inputs, unsupported processing, failure preservation, interruption, overwrite refusal and tampered archives. Reconstruction repeats boundary arithmetic; the hand-calculated anchors are the independent checks.

## Run and reconstruct

From the worktree root, use a fresh output directory:

```bash
uv sync --locked
uv run --locked python -m experiments.m4.paired_observation.run \
  --output results/m4-paired/my-reference
uv run --locked python -S -m experiments.m4.paired_observation.run \
  --reconstruct results/m4-paired/my-reference \
  --output results/m4-paired/my-reconstructed.json
cmp results/m4-paired/my-reference/preflight.json results/m4-paired/my-reconstructed.json
uv run --locked python -m unittest discover -s tests -p test_m4_paired_observation.py -v
uv run --locked python scripts/check.py
```

The additional native derivative check uses the separate existing M0 environment:

```bash
uv sync --locked --project experiments/m0/simglucose
uv run --locked --project experiments/m0/simglucose \
  python -m experiments.m4.paired_observation.native_probe \
  results/m4-paired/my-reference --output results/m4-paired/my-native-probe.json
```

`--protocol experiments/m4/paired_observation/protocol.json` is the default explicit configuration. The frozen example is synthetic-only. Wrong units or unsupported source/baseline interpretations fail rather than being guessed. An existing output directory is refused. A failed attempt retains manifest, inputs, copied sources and any produced report. Hashes detect changes; they do not authenticate an intentionally rewritten archive. New configurations are new experiments and must not be presented as the frozen BC-004 result.

Executed verification: root and native `uv sync --locked` passed; `uv run --locked python scripts/check.py` passed 267 tests, including 21 new boundary/artifact tests, plus Ruff, Markdown/YAML/citation checks, navigation and the strict Sphinx build. The separate pinned native derivative probe passed. The CI workflow includes the preflight, reconstruction and native probe; remote CI was not run. Existing BC-001/002/003 trajectories were not rerun because their code and locks are unchanged.

## Findings and next executable work

The separately versioned [BC-005 follow-up](m4-paired-kinetics-results.md) now implements and verifies the kinetic-only runner described below. This BC-004 record and its original zero-initial implementation limitation remain historical evidence; biological review, source scale and human assessment are still unresolved.

The source recheck makes the measurement need more precise: CIT-07's posttransplant C-peptide baseline samples occur at -10/-5/-1 minutes, with postchallenge C-peptide ending at 10 minutes; later insulin/glucose sampling is not late C-peptide. The [candidate assessment](m4-cpeptide-measurements.md#paired-protocol-source-check) distinguishes these measurements from the longer oral Miami substudy and records current access failures. No ready authorized paired human dataset was established. No outreach, access application or patient download occurred.

The code review also establishes a concrete implementation dependency: BC-002 hardcodes zero incremental initial insulin state. Its existing execution cannot consume the synthetic-total initialization unchanged. The next bounded software step is a separately versioned paired **kinetic-only** runner: first verify nonzero initial insulin inventories and conservation, then run both observation branches under the same declared synthetic input with independent references. Preserve the existing zero/incremental regressions. Human interpretation still requires the [unsent domain-review packet](m4-collaboration-brief.md#paired-boundary-review-packet), resolved secretion scale and permitted observations; full glucose feedback remains outside BC-004.

OT-024 and the relevant OT-015 specification now include the concrete paired contract and measurement assessment. OT-025's exact cohort-reproduction gaps are unchanged. OT-026 is still partial: this completed preflight is additional preparation, not completion of biological coupling. OT-027 still needs a selected intervention/population/endpoint and independently supported treatment mechanisms.
