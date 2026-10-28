# Run and reconstruct an M4 secretion comparison

**Current public scope:** this native research route is outside the initial
two-task public exercise. Its pinned environments retain advisories and are
excluded from automatic public installation. Read the
[current runtime and CI policy](publication-security.md) before using the
historical setup commands below.

This guide owns the configured **M4-RESEARCHER/1** workflow: run one trusted
local causal secretion source on fixed synthetic fasting and gastric-load
scenarios, observe its pancreatic output through forward C-peptide kinetics,
and read one report containing glucose, insulin and C-peptide trajectories.
It composes the unchanged [causal intake](m4-causal-secretion.md),
[BC-008 feedback task](research/m4-feedback-results.md) and
[BC-010 observation boundary](research/m4-feedback-observation-results.md).
It does not replace their historical studies or protocols.

The research question is: **how does the selected secretion response change
modeled glucose, insulin and C-peptide under the same fixed conditions?**
The intended user brings a source and its declaration; two supplied
configurations exercise the existing Dalla Man adapter and the structurally
different [ultradian f1 component](m4-ultradian-secretion.md). Neither
configuration is calibrated to a person or establishes treatment benefit.
[Decision 0052](decisions/0052-m4-researcher-workflow.md) records the
composition and its limits.

## Prepare and run

Use the root of the same checkout or worktree for all commands. The root
environment owns tooling and orchestration; numerical execution uses the two
existing, separately locked environments.

```console
uv sync --locked
uv sync --locked --project experiments/m0/simglucose
uv sync --locked --project experiments/m4/beta_cell/runtime
uv run --locked python -m experiments.m4.researcher_workflow.run \
  --config experiments/m4/researcher_workflow/dalla_man.json \
  --output /tmp/m4-researcher-dalla-man
uv run --locked python -m experiments.m4.researcher_workflow.run \
  --config experiments/m4/researcher_workflow/ultradian.json \
  --output /tmp/m4-researcher-ultradian
```

Choose fresh output paths: an existing output directory is refused. Each
command creates and verifies a fresh BC-008 reference by default, executes
candidate and constant-basal cases in fresh processes, then runs the
C-peptide branch and its fresh-process repeat. To reuse an already verified
BC-008 archive, add `--reference /absolute/path/to/bc008`. Its archived BC-008
source snapshots, reused files and native runtime lock/project must match the
current worktree byte for byte. A mismatch is rejected before creating an
output directory. The workflow copies and verifies the accepted archive;
passing a reference does not skip its numerical or provenance checks.

Open `report.md` and `figure.svg` in the output directory. `report.json`
contains the same artifact-derived numerical assessment. The report compares
three source tracks for each 240-minute scenario:

| Track | Meaning |
| --- | --- |
| `candidate` | The configured source evaluated causally inside the native solver |
| `host_constant_basal` | Host-generated constant pancreatic appearance with the same initial state and fixed SC schedule |
| `bc008_reference` | The unchanged full BC-008 Dalla Man response from the verified reference archive |

The gastric-load scenario starts with 30 g in the gastric solid compartment
at time zero. It is not an announced meal, pump action or bolus. Output is
sampled every 0.25 minutes. The fixed 25% SC basal replacement and matched
initial plasma insulin are inherited experiment conventions; no external
insulin requirement is estimated. The earlier
[SC-equivalence workflow](m4-synthetic-basal-equivalence.md) remains a
separate task with its own bounded search and no-solution outcomes.

## Supply your own source

Use the unchanged [M4-CAUSAL/1 callback and declaration](m4-causal-secretion.md#model-contract).
One regular Python file defines `evaluate(time, glucose, glucose_rate, Z,
Sb, h, parameters)` and returns the state derivative and nonnegative total
pancreatic appearance. The callback receives only current native solver
inputs. It must preserve the declared basal equilibrium and give repeatable
results when the solver evaluates time repeatedly or out of order.

The host owns the one-state initialization, SC basal replacement, portal
transit and liver arrival. No supplied source may add another basal input,
portal compartment, hidden mutable state or future glucose trajectory.
The source is trusted local code: hash verification records its bytes and
does not establish its rights, purity or scientific validity.

Create a JSON configuration with exactly these four fields:

```json
{
  "schema": "m4-researcher-config/1",
  "model": "../causal_secretion/example_model.py",
  "declaration": "../causal_secretion/example_model.json",
  "timeout_seconds": 600
}
```

Relative model and declaration paths resolve against the configuration's
directory, rather than the shell's working directory. Absolute file paths
are also supported. The example above is relative to
`experiments/m4/researcher_workflow/`. Copying this configuration elsewhere
requires updating those paths. The declaration records ancestry, rights
basis, dependencies, numerical parameters, exact output unit
`pmol/(kg min)` and the source SHA-256. The existing
[example declaration](../experiments/m4/causal_secretion/example_model.json)
is the canonical declaration example.

`timeout_seconds` bounds supervised subprocesses rather than the total
orchestration time. Use an integer from 1 to 1800. On a timeout or interruption,
the workflow terminates and reaps its worker process group before sealing the
failure archive. The inherited causal executor uses this supervisor only
inside a scoped binding that is restored afterward; historical numerical
source files remain unchanged. This version supports the existing single-file,
one-state intake and locked environment; arbitrary runtimes and multi-state
models require a separately scoped contract.

The Dalla Man configuration exercises parity with BC-008. The ultradian
configuration keeps its original nominal sigmoid shape and declared
synthetic basal normalization. Its assignment to the host pancreatic route
remains the explicit exploratory adaptation recorded in
[decision 0051](decisions/0051-m4-ultradian-response-component.md). The
workflow does not reproduce the complete ultradian physiology.

## C-peptide boundary and checks

C-peptide is a one-way observation of saved **pancreatic appearance** `Spo`,
not post-portal liver arrival `S`. The total pancreatic rate already contains
basal secretion. It enters the unchanged
[Polonsky forward model](research/models/polonsky1986-cpeptide.md) directly
in `pmol/(kg min)`, with the inherited equimolar working assumption. No
second basal, SC contribution, molecular conversion, body-weight division,
hepatic extraction factor or insulin portal delay is applied.

For fixed inherited rate constants, central and peripheral initial amounts
are `Q1 = Sb/k3` and `Q2 = k1*Q1/k2` in `pmol/kg`. Input and eliminated-amount
ledgers start at zero. Central concentration is `Q1/volume` in `pmol/L`.
C-peptide cannot change the parent's glucose, insulin or source trajectory.

The new frozen protocol composes six observation cases: three tracks in
each of two scenarios. It reuses BC-010's frozen boundary and numerical
settings, not its original 24-case hepatic study. For each new case it checks:

- Two numerical solvers against an independent matrix-exponential oracle,
  complete finite output, mass/input ledgers and nonnegative inventories.
- Basal equilibrium in fasting and constant-source cases, and agreement
  between interpolated source dose and the parent's integrated amount.
- Propagation of the tight-parent source and separate 0.5/1-minute
  coarsenings against the saved 0.25-minute source grid.
- A named liver-arrival fault diagnostic and the inherited appearance/volume
  scaling ambiguity, both kept separate from the valid observation inlet.
- Exact numerical artifact equality in a fresh-process repeat.

A continuous piecewise-linear interpolant represents the archived source;
it does not infer unobserved curvature. Coarsening checks characterize this
saved grid and do not prove continuous-source convergence below 0.25 minutes.
The scale diagnostic does not establish full coupled capacity identifiability.

## Preserve and reconstruct the evidence

The archive includes `reference/`, `causal/`,
`observations/primary/` and `observations/repeat/`, together with the frozen
configuration and protocols, source snapshots, both runtime locks, logs,
case attempts and file hashes. Keep the entire directory. The report needs
these artifacts to verify provenance and complete numerical evidence.

Rebuild the three report files from saved artifacts without importing the
supplied source, NumPy, SciPy or a numerical simulator:

```console
uv run --locked python -S -m experiments.m4.researcher_workflow.report \
  /tmp/m4-researcher-dalla-man \
  --output /tmp/m4-researcher-dalla-man-reconstructed
cmp /tmp/m4-researcher-dalla-man/report.json \
  /tmp/m4-researcher-dalla-man-reconstructed/report.json
cmp /tmp/m4-researcher-dalla-man/report.md \
  /tmp/m4-researcher-dalla-man-reconstructed/report.md
cmp /tmp/m4-researcher-dalla-man/figure.svg \
  /tmp/m4-researcher-dalla-man-reconstructed/figure.svg
```

The reconstruction output directory must be new. Reconstruction checks saved
parent reports, identities, complete case matrices, kinetic inventories,
controls and repeats. It verifies the evidence in the archive; it does not
independently establish that arbitrary supplied Python code followed all
scientific assumptions.

Every attempted run is retained. A failed or incomplete parent cannot support
accepted observation contrasts. Missing cases, failed numerical criteria,
changed hashes and shortened trajectories must not be reported as a
successful complete comparison. To inspect a preserved failed archive, run
the same reconstruction command with `--allow-failed` and a fresh output
path. Read its failure and missing-evidence accounting before interpreting
any trajectories. Do not edit an archive to make its checks pass.

## Internal verification and limits

The bounded workflow was executed internally on 2 October 2026 from clean
implementation commit `ca09264274621eae86c2b732e4179af1e4053287`.
The [execution record](../experiments/m4/researcher_workflow/execution.json)
pins source/report hashes, commands, local artifact locations and verification.
Both final source runs reused the same freshly executed, verified BC-008
reference after its source and lock snapshots matched the worktree.

Each source configuration completed all eight inherited causal
candidate/control/solver cases and eight byte-identical fresh-process
repeats. All six forward-observation cases and six fresh-process repeats
completed, with every inherited numerical criterion passing and no changed
repeat artifacts. `python -S` reconstruction reproduced `report.json`,
`report.md` and `figure.svg` byte for byte for both sources. The Dalla Man
adapter has exactly zero glucose, insulin and C-peptide contrast against
BC-008 at the saved times. The ultradian component produces a nonzero
modeled contrast; this does not rank the biological models.

| Observer check, maximum across both runs | Discrepancy | Frozen limit |
| --- | --- | --- |
| Independent oracle concentration error | 2.59e-10 pmol/L | 1e-5 pmol/L |
| Two-solver concentration difference | 2.59e-10 pmol/L | 1e-5 pmol/L |
| Finest source coarsening difference | 0.029852 pmol/L | 0.05 pmol/L |
| Parent-dose relative difference | 1.63e-7 | 1e-4 |

A separate real invalid-negative-rate source failed in the causal stage from
the same clean commit. It retained the failure evidence and complete planned
observer roster as `not_attempted`, accepted zero of six observation cases,
and produced three byte-identical reconstructed report artifacts. Four
lightweight process tests verify worker kill/reap on deadline and interruption,
scoped restoration and nonzero-exit logging. The full focused root suite has
16 passing tests, and the isolated C-peptide numerical suite has five.
A subsequent input-path guard resolves the reused reference before checking
output overlap; its regression test rejects a hidden nested output through
`..` path components. This changes no numerical equations or report
computations. The execution record distinguishes these targeted checks from the comprehensive
repository check: all 761 root tests and the documentation build passed.

This is an internal synthetic research-tool increment. It neither completes
M4 nor grants P1 product acceptance. Independent researcher execution,
authorized paired observations, population-specific calibration and domain
review remain open. The report describes this particular composition; it
does not rank biological models, predict a human C-peptide curve, identify
functional cell mass or demonstrate treatment efficacy.
