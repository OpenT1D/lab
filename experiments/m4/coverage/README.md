# BC-014 synthetic gain coverage

This experiment tests one conditional property of the unchanged BC-013 procedure:
whether its nominal pointwise evoked-gain profile includes the generating gain
on new synthetic noise draws. Read the [frozen protocol](../../../docs/research/m4-coverage-protocol.md)
before interpreting its output. These draws are not people or independent
clinical observations.

From the repository root, run the complete two-process campaign with the
separate locked simglucose environment:

```sh
uv sync --locked
uv sync --locked --project experiments/m0/simglucose
uv run --locked python -m experiments.m4.coverage.run \
  --output results/m4-coverage/reference-01
```

The output directory must not already exist. Its ignored local archive retains
the protocol and parent protocols, source and lock snapshots, runtime/native
identity, synthetic observations, every optimizer start and reference-solver
check, failures, an exact fresh-process repeat, `report.json` and `figure.svg`.
It is not added to version control. The top-level `manifest.json` records
file hashes and whether numerical acceptance completed. A failed campaign
keeps its partial checkpoints and planned denominators; inspect them before
selecting a *new* archive path for a rerun.

Reconstruct the report using only the root environment's standard library:

```sh
.venv/bin/python -S -m experiments.m4.coverage.report \
  results/m4-coverage/reference-01 \
  --output results/m4-coverage/reconstructed.json
```

For a completed archive, compare the reconstructed JSON with `report.json`.
The reader verifies file hashes, the complete roster, observation arithmetic,
all fit starts and weighted residuals, constrained/free objective differences,
native numerical-oracle records, exact repeat and Wilson intervals. The SVG is
also reconstructed from the report. The native numerical regression checks run
with:

```sh
uv run --locked --project experiments/m0/simglucose python \
  -m unittest experiments.m4.coverage.test_numerical -v
```

The primary proportion is true-gain inclusion divided by **all planned**
analyses; incomplete and failed analyses remain in that denominator as
noncoverage and are reported separately. The 32 exact gain-boundary draws
are a diagnostic without a nominal 95% target. The interior draws are paired
across three observation designs, so their marginal Wilson intervals do not
form an independent between-design comparison. No threshold is calibrated on
these assessment draws.
