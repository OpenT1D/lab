# Run the standalone beta-cell reference

**Current public scope:** this native research route is outside the initial
two-task public exercise. Its pinned environments retain advisories and are
excluded from automatic public installation. Read the
[current runtime and CI policy](publication-security.md) before using the
historical setup commands below.

BC-001 implements the published reduced IVGTT secretion equations of Pedersen and Cobelli (2013). It transforms a prescribed **synthetic declining plasma-glucose profile into evoked insulin release**, with explicit initialization and capacity scenarios. It does not run a metabolic engine. Read the [model card](research/models/pedersen-cobelli2013.md), [protocol](research/m4-protocol.md) and [results](research/m4-results.md) before interpreting the output.

## Execute

Run from the repository root, with `uv` installed. The separate runtime keeps numerical libraries out of repository tooling. Use a new output directory for each attempt:

```bash
uv sync --locked --project experiments/m4/beta_cell/runtime
uv run --locked --project experiments/m4/beta_cell/runtime \
  python experiments/m4/beta_cell/runtime/test_model.py
uv run --locked --project experiments/m4/beta_cell/runtime \
  python experiments/m4/beta_cell/runtime/run.py \
  --protocol experiments/m4/beta_cell/protocol.json \
  --output results/m4/my-reference
```

If your environment requires a writable cache location, set `UV_CACHE_DIR` to a permitted local directory before these commands. The reference protocol supplies source parameters, glucose in mmol/L, elapsed minutes, microgram pool units, numerical settings and capacity cases. It fits no parameters and uses no patient data. A changed input is a new synthetic scenario, not a recovered subject or transplant.

Each run archives the exact protocol, numerical/model/analysis sources and dependency lock, sampled input, full trace, theoretical response functions, verification and sensitivity results, manifest, JSON report and SVG figure. Source hashes identify the code even before commit. Existing directories are refused. Invalid configurations or incomplete calculations retain a failed manifest and errors; a failed run cannot masquerade as a completed report.

## Reconstruct

Recalculate primary report metrics without SciPy, the solver or either metabolic engine:

```bash
python3 -S experiments/m4/beta_cell/runtime/report.py \
  results/m4/my-reference \
  --output results/m4/my-reference/reconstructed.json
```

Recreate the figure from saved data only, using the locked plotting runtime:

```bash
uv run --locked --project experiments/m4/beta_cell/runtime \
  python experiments/m4/beta_cell/runtime/plot.py \
  results/m4/my-reference \
  --output results/m4/my-reference/reconstructed.svg
```

Both readers verify required artifacts and hashes. The figure displays synthetic input, scaled evoked release, the unresolved paper/code initialization difference, and the published provision/delay relationships. Numerical tolerances describe agreement of calculations, not uncertainty in human physiology.

## Interpret and continue

The literal reduced output omits basal secretion. It must not be fed to a pump, equated to a concentration, or called total endogenous output. The demonstrated capacity multiplier is not beta-cell mass or a treatment mechanism. Exact reproduction of the paper's dynamic figure remains unresolved because the measured input series is missing and the initial-state formula differs from the author's code.

The [evidence dossier](research/m4-evidence-dossier.md) assesses references and actual access to measurements. The [collaboration brief](research/m4-collaboration-brief.md) is a draft for domain review, not a sent message or an established partnership. The [OT-015 boundary](research/m4-coupling.md) prepares OT-026's next kinetic inlet experiment. No coupling or therapy model has been implemented.
