# Compare frozen M4 secretion sources

**Current public scope:** this native research route is outside the initial
two-task public exercise. Its pinned environments retain advisories and are
excluded from automatic public installation. Read the
[current runtime and CI policy](publication-security.md) before using the
historical setup commands below.

This guide owns **M4-COMPARISON/1**: compare two to eight frozen, trusted local
secretion sources on the same synthetic fasting and 30 g gastric-load task.
One configuration produces a joint glucose, insulin and C-peptide report.
The coordinator reuses the unchanged [single-source workflow](m4-researcher-workflow.md)
and its separate numerical environments. The
[comparison protocol](research/m4-source-comparison-protocol.md) and
[decision 0057](decisions/0057-m4-source-comparison.md) define the boundaries.
The [OT-031 verification record](research/ot031-verification.md) records the
observed native runs, repeats, failure handling and reconstruction checks.

## Prepare and execute

Run these commands from the same recorded checkout:

```console
uv sync --locked
uv sync --locked --project experiments/m0/simglucose
uv sync --locked --project experiments/m4/beta_cell/runtime
uv run --locked python -m experiments.workflows check m4-compare \
  --config experiments/m4/comparison/example.json
uv run --locked python -m experiments.workflows run m4-compare \
  --config experiments/m4/comparison/example.json \
  --output results/m4-comparison/example
```

Choose a fresh output directory. The passive check validates source and
declaration identities and installed runtime metadata without importing a
supplied source or running a simulation. Execution freezes the complete
source roster, creates one verified BC-008 reference, then runs each source
in roster order with the same reference. To reuse an existing complete
BC-008 archive, add `--reference /absolute/path/to/bc008`. Its archived sources
and native lock must match the current checkout; its numerical checks are
verified before dispatch.

The example compares the existing Dalla Man adapter and ultradian f1 source.
The latter retains its declared synthetic basal normalization and pancreatic
route adaptation; it is not the full ultradian metabolic model.

## Declare a comparison

The configuration has exactly these fields:

```json
{
  "schema": "m4-source-comparison-config/1",
  "sources": [
    {
      "id": "dalla-man",
      "model": "../causal_secretion/example_model.py",
      "declaration": "../causal_secretion/example_model.json"
    },
    {
      "id": "ultradian",
      "model": "../ultradian_secretion/model.py",
      "declaration": "../ultradian_secretion/model.json"
    }
  ],
  "timeout_seconds": 600,
  "source_timeout_seconds": 3600
}
```

Relative file paths resolve against the configuration directory. Each source
uses the existing [causal callback and declaration](m4-causal-secretion.md#model-contract),
including its source hash, ancestry, parameters and `pmol/(kg min)` output.
Sources are trusted local Python and execute with the user's permissions.
Their rights declarations remain supplier attestations.

`timeout_seconds` bounds each inherited supervised stage and must be an
integer from 1 to 1800. `source_timeout_seconds` bounds a complete source
workflow and must be an integer from 1 to 10800. Both budgets apply equally
to every source. A shorter budget may preserve an incomplete run; it does
not relax numerical acceptance or shorten the comparison interval.

The task fixes both scenarios, the 240-minute horizon, the 0.25-minute sample
grid, initial conditions, SC schedule, basal and portal ownership, solver
criteria and forward C-peptide observation boundary. These are inherited
synthetic conventions. Changes to them require a separately versioned task.

## Read the joint result

Open `report.md` and `figure.svg` in the output directory. `report.json`
contains the same reconstructed assessment. The report retains every
declared source and both planned scenarios, including failed, interrupted
and unattempted work.

Each accepted source has passed the complete single-source workflow:
causal numerical checks, both scenarios, forward observation checks and
fresh-process repeats. Its shared constant-basal and BC-008 controls must
agree with the other accepted sources on the exact sample grid.

Pairwise descriptive contrasts follow roster order, **left minus right**.
For glucose in `mg/dL` and insulin/C-peptide in `pmol/L`, they include signed
trapezoidal area differences, signed time-mean differences and maximum
absolute pointwise differences. A comparison requires two fully accepted
sources under identical conditions. Otherwise its metrics are null with an
explicit reason. Partial output remains diagnostic evidence.

The figures and differences describe model behavior conditional on this
synthetic composition. They do not select a biological winner, estimate a
human insulin requirement, or establish predictive quality or treatment
benefit. Independent usability and M4's empirical evidence requirements
remain separate.

## Reconstruct and preserve failures

Keep the complete archive: its frozen roster/source/configuration files,
shared `reference/`, per-source `children/`, logs, state, source snapshots
and hash inventory are all evidence.

```console
uv run --locked python -S -m experiments.workflows reconstruct m4-compare \
  --archive results/m4-comparison/example \
  --output results/m4-comparison/example-reconstructed
cmp results/m4-comparison/example/report.json \
  results/m4-comparison/example-reconstructed/report.json
cmp results/m4-comparison/example/report.md \
  results/m4-comparison/example-reconstructed/report.md
cmp results/m4-comparison/example/figure.svg \
  results/m4-comparison/example-reconstructed/figure.svg
```

Reconstruction uses the standard library and original native archive readers,
without executing a supplied source or importing numerical runtimes. It
verifies identities, complete evidence and report arithmetic. To reconstruct
a preserved incomplete comparison, add `--allow-failed`; its failure status
is retained. Use the recorded implementation checkout and a fresh output
directory. Reconstructing saved outputs does not independently reproduce an
arbitrary source algorithm.

The direct commands remain available as `python -m experiments.m4.comparison
check`, `run` and `reconstruct`, with the same configuration, reference and
archive options. Existing single-source commands and historical readers
remain unchanged.
