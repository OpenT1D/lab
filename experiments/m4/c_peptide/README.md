# Standalone forward C-peptide reference (BC-003)

This experiment propagates a declared C-peptide appearance rate through the two-compartment model of [Polonsky et al. (1986)](https://doi.org/10.1172/JCI112308). It includes independent analytical comparisons and noiseless known-input parameter recovery. It does not infer arbitrary secretion from C-peptide or validate a patient or therapy model.

Read the [model card](../../../docs/research/models/polonsky1986-cpeptide.md), [frozen protocol](../../../docs/research/m4-cpeptide-protocol.md), [results](../../../docs/research/m4-cpeptide-results.md) and [measurement specification](../../../docs/research/m4-cpeptide-measurements.md).

## Run from the repository root

The existing BC-001 locked scientific environment supplies Python 3.12, NumPy, SciPy and Matplotlib. The root environment remains tooling-only. No additional runtime or upstream code is required.

```bash
uv sync --locked --project experiments/m4/beta_cell/runtime
uv run --locked --project experiments/m4/beta_cell/runtime \
  python -m unittest discover -s experiments/m4/c_peptide -p test_model.py -v
uv run --locked --project experiments/m4/beta_cell/runtime \
  python -m experiments.m4.c_peptide.run --output results/m4-cpeptide/my-reference
```

Use a new output directory each time. The runner refuses existing directories and retains failed attempts. `--protocol experiments/m4/c_peptide/protocol.json` makes the default protocol explicit. Configuration changes are new experiments, not reproduction of the frozen result. The unchanged `experiments/m4/kinetic_inlet/forcing.py` supplies finite molar-rate input, including explicit discontinuities.

## Reconstruct without executing the model

```bash
uv run --locked python -S -m experiments.m4.c_peptide.report \
  results/m4-cpeptide/my-reference --output results/m4-cpeptide/reconstructed.json
cmp results/m4-cpeptide/my-reference/report.json results/m4-cpeptide/reconstructed.json
uv run --locked --project experiments/m4/beta_cell/runtime \
  python -m experiments.m4.c_peptide.plot results/m4-cpeptide/my-reference \
  --output results/m4-cpeptide/reconstructed.svg
cmp results/m4-cpeptide/my-reference/figure.svg results/m4-cpeptide/reconstructed.svg
```

Reconstruction requires a completed manifest, checks hashes and completeness, recalculates mass/input/concentration and recovery summaries, and rechecks declared thresholds. The standard-library report does not rerun integration, analytical kernels, fitting or SVD, and does not execute archived source. Native verification establishes those computations. Hashes detect changed artifacts; they are not signatures against a deliberately rewritten archive. Figure generation uses validated saved traces only.

`manifest.json` records runtime versions, git base/dirty status, artifact hashes and failure details. The archive contains the exact protocol, forcing/initial states, eight traces, solver/analytical/comparator outputs, identification observations/predictions/sensitivities, verification, report, SVG, code snapshots and runtime lock. Numerical source snapshots are authoritative when the run is made with uncommitted changes. Generated results remain ignored; the compact versioned execution record and public results page preserve the evidence.

## Code boundaries

`model.py` contains states, conversions and ODE integration; `reference.py` implements the independent published kernel; `identify.py` runs the bounded synthetic study; `verify.py` applies the frozen numerical criteria. `run.py` owns execution and failures. `report.py` and `plot.py` reconstruct artifacts. Native tests exercise numerical limits and solver/recorder failure paths; repository tests check incomplete, altered and inconsistent archives.
