# BC-002: reproduce the bounded insulin-kinetic inlet

BC-002 connects a declared incremental insulin input to the **actual pinned simglucose insulin derivatives**. It checks liver and peripheral inlets against an independently assembled matrix exponential and conserves insulin inventories plus hepatic/peripheral losses. Nonzero runs advance insulin kinetics only. They do not simulate a person's glucose or show reduced external-insulin requirements.

Read the [protocol](../../../docs/research/m4-kinetic-protocol.md), [boundary assessment](../../../docs/research/m4-kinetic-boundary.md) and [execution results](../../../docs/research/m4-kinetic-results.md). The original BC-002/1 protocol is preserved: its finest 0.125-minute communication interval misses the peripheral concentration criterion. The separate refined protocol adds 0.0625 minutes and retains the same thresholds; it is a numerical follow-up after that observed failure.

## Install and generate the secretion source

Run all commands from the repository root. The root environment is repository tooling; simulations use the existing locked environments. Use fresh result-directory names for every attempt.

```bash
uv sync --locked --project experiments/m4/beta_cell/runtime
uv run --locked --project experiments/m4/beta_cell/runtime \
  python experiments/m4/beta_cell/runtime/run.py \
  --protocol experiments/m4/beta_cell/protocol.json \
  --output results/m4/my-secretion-reference

uv sync --locked --project experiments/m0/simglucose
uv run --locked --project experiments/m0/simglucose \
  python -m experiments.m4.kinetic_inlet.test_native
```

An existing completed BC-001/1 archive may be supplied instead. The runner verifies its model/protocol identity, complete state, required source/data files and hashes before copying the used archive into the new run. Failed or unfinalized BC-001 attempts are rejected. This workflow uses synthetic public-reference output and needs no patient data.

## Execute and inspect

```bash
uv run --locked --project experiments/m0/simglucose \
  python -m experiments.m4.kinetic_inlet.run \
  --protocol experiments/m4/kinetic_inlet/refined-protocol.json \
  --secretion-run results/m4/my-secretion-reference \
  --output results/m4/my-kinetic-reference
```

To reproduce the original negative numerical result, use `experiments/m4/kinetic_inlet/protocol.json` with another fresh output directory. Its nonzero exit and failed manifest are the expected response to its missed criterion; inspect `verification.json` and the preserved case traces. Do not discard that result or relax its threshold.

Outputs include the native revision/parameter identity, exact configuration, source-code and environment snapshots, the used BC-001 archive, converted source input, explicit input segments, liver/peripheral/constant/zero traces, numerical verification, JSON report and SVG. All amounts are incremental pmol/kg and plasma output is pmol/L. Time is elapsed minutes. Initial insulin inventories and the additional basal rate are zero. BC-001 micrograms receive an explicit nominal whole-body conversion using 5808 g/mol and the native virtual profile's body weight; this is an uncalibrated synthetic scale.

Completed status is assigned only after report and figure generation. Incomplete calculations, rejected inputs and interruptions retain a failed manifest. Existing output directories are refused.

## Reconstruct without a metabolic engine

The JSON reader uses only the standard library and archived artifacts:

```bash
python3 -S -m experiments.m4.kinetic_inlet.report \
  results/m4/my-kinetic-reference \
  --output results/m4/my-kinetic-reference/reconstructed.json
```

Figure reconstruction uses the saved data and the plotting environment, without model execution:

```bash
uv run --locked --project experiments/m0/simglucose \
  python -m experiments.m4.kinetic_inlet.plot \
  results/m4/my-kinetic-reference \
  --output results/m4/my-kinetic-reference/reconstructed.svg
```

Readers reject missing, altered or nonfinal artifacts and failed numerical verdicts. Reconstruction is not an independent biological validation. The observed differences between liver and peripheral delivery reflect the fixed native kinetic coefficients; simglucose's missing direct portal-insulin action and BC-001's unresolved initialization remain limits. M4/OT-026 still needs a suitable glucose-regime model, basal/scale conventions, identifiability and domain review before a glucose-outcome or cell-therapy study.
