# Configurable synthetic M4 initial gastric-load study

**Current public scope:** this native research route is outside the initial
two-task public exercise. Its pinned environments retain advisories and are
excluded from automatic public installation. Read the
[current runtime and CI policy](publication-security.md) before using the
historical setup commands below.

This route compares two to eight frozen local one-state secretion sources
under a predeclared subset of three synthetic gastric solid initial loads:
0, 15 and 30 grams. It produces complete glucose, plasma insulin and passive
C-peptide trajectories, numerical diagnostics and descriptive source-pair
contrasts. This is research software verification; it provides no personal
calibration, source ranking, insulin dose or treatment-effect estimate.

The [M4-STUDY/2 protocol](research/m4-configurable-study-protocol.md) fixes
adult#001, the existing basal replacement and SC input, a 240-minute horizon,
the 0.25-minute output grid and separate numerical environments. The machine
protocol is [protocol.json](../experiments/m4/initial_load/protocol.json).
Changing meal timing, load values, physiological states or these conditions
requires a separately specified contract.

## Freeze a configuration

The [example](../experiments/m4/initial_load/example.json) selects the existing
Dalla Man adapter and isolated ultradian response component, with all three
loads. Its exact keys are `schema`, `sources`, `scenarios`, `timeout_seconds`
and `source_timeout_seconds`.

Each ordered source entry has exactly `id`, `model` and `declaration`.
Relative paths resolve against the configuration file. The declaration uses
the unchanged [causal intake](m4-causal-secretion.md), including source hash,
ancestry, rights basis, output units and frozen numeric parameters. Metadata
checking reads bytes without importing or executing a supplied source:

```sh
uv run --locked python -B -S -m experiments.m4.initial_load check \
  --config experiments/m4/initial_load/example.json
```

`scenarios` is a nonempty ordered subset of unique IDs: `fasting`,
`gastric_load_15g`, `gastric_load_30g`. The load initializes gastric solid mass
and `last_Qsto` at time zero. `last_foodtaken` is zero and `Action.CHO` stays
zero throughout. This is an initial condition, not an announced meal or
event schedule.

The stage budget is an integer from 1 to 1800 seconds; the entire-source
budget is an integer from 1 to 10800 seconds. The latter spans all selected
loads, refinement, observation, repeats and verification for that source.
The example uses 600 and 3600 seconds. Neither bounds total study duration.

## Run and reconstruct

Install the declared native and C-peptide locks through the repository's
setup instructions. Use a fresh output directory:

```sh
uv run --locked python -B -S -m experiments.m4.initial_load run \
  --config experiments/m4/initial_load/example.json \
  --output results/m4-study/example

uv run --locked python -B -S -m experiments.m4.initial_load reconstruct \
  --archive results/m4-study/example \
  --output results/m4-study/example-reconstructed
```

An optional `--reference PATH` on `run` supplies an unchanged complete,
source-matched BC-008 archive as the historical baseline and parity anchor.
It is verified before output creation. Every selected load still receives
fresh scenario-specific native, constant-basal and active BC-008 reference
trajectories. A 30 g archive cannot substitute for a new 15 g reference.

The archive retains the exact raw configuration, source/declaration snapshots,
protocol, numerical locks and implementation ancestry before callback
execution. The host owns source initialization, portal transit and liver
arrival. C-peptide observes total pancreatic appearance once: pmol/(kg min)
to pmol/kg, divided by L/kg to pmol/L. It adds no second body-weight factor,
SC input, hepatic extraction or insulin transit.

The report shows complete planned source/load and pair denominators.
Descriptive left-minus-right signed AUC, time mean and maximum absolute
pointwise separation require both entire source workflows to pass, identical
full grids and common controls. A failed source remains visible, and its
completed prefixes cannot support accepted pair contrasts. Ordinary source
failure allows later sources to run; interruption stops the active group and
leaves later sources unattempted. Deadline and interruption terminate and
reap owned numerical workers.

Use `--allow-failed` with reconstruction to retain a failed/interrupted
archive's diagnostic status and null unsupported contrasts. Reconstruction
uses only the standard library, executes no callback or simulator, checks
saved report bytes and writes a separate fresh directory. Altered reports
are rejected rather than repaired.

## Numerical interpretation

The original protocol/1's new coarse source gate failed at 15 g. Its protocol
and independent probe remain archived. Protocol/2 halves only the coarse
maximum step from 0.5 to 0.25 minutes, retaining the 1e-5 pmol/(kg min) source
limit, all other criteria and all physiology. Tight/reference and observer
settings retain historical 0/30 g parity; refined coarse results have no
claim of historical byte identity.

Historical and current native identity records retain their original installation
paths as provenance. Reusing a reference from another checkout compares all
scientific identity fields, parameters and runtime exactly; only `patient_file`
and `parameter_file` locations may differ. Each current worker still binds its
full identity record, including paths, and fresh-process repeats must match.

Three parent solvers, independent flux/inventory checks, reference source
replay, the unchanged passive observer/oracle diagnostics and exact
fresh-process repeats assess numerical behavior. Observer coarsening does
not establish continuous-source convergence below the archived 0.25-minute
grid. Artifact reconstruction establishes report consistency, not human
validity or independent execution of an arbitrary callback. The ultradian
example remains a sourced response component, not a complete ultradian
physiology engine.
