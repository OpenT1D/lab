# Compare fixed external basal infusion in a synthetic M4 task

**Current public scope:** this native research route is outside the initial
two-task public exercise. Its pinned environments retain advisories and are
excluded from automatic public installation. Read the
[current runtime and CI policy](publication-security.md) before using the
historical setup commands below.

This workflow asks which **constant SC infusion** yields the same modeled
240-minute glucose AUC as the unchanged BC-008 full-feedback reference in its
synthetic 30 g gastric-load task. It compares the pinned BC-008-equivalent
adapter with one declared causal secretion source through the existing
[one-state intake](m4-causal-secretion.md).
There is no pump controller, bolus, patient record or clinical dose estimate.

## Frozen question and boundary

The target is the BC-008 reference-solver area above initial glucose, in
`mg min/dL`, for the 240-minute gastric-load scenario. The host holds the
source's synthetic basal secretion `Sb`, glucose threshold, portal transit,
initial native states and SC depot inventories fixed at the 25% replacement
boundary. Only the constant SC delivery **from time zero onward** changes.
The starting delivery is 75% of the native `u2ss`; the allowed search range
is 50–100%. Changing a rate from the same initial inventories creates a
transient. The result is an engineering equivalence for one invented task,
not a new steady-state or person-specific requirement.

The [frozen protocol](../experiments/m4/basal_equivalence/protocol.json)
evaluates five rates: 50, 62.5, 75, 87.5 and 100% of native `u2ss`. If the
recorded AUCs decrease monotonically and bracket the target, it bisects the
bracket for at most 18 steps. A match requires an absolute AUC error of at
most `1 mg min/dL` on the separate reference solver. Nonmonotone,
unbracketed and resolution-limited searches are preserved as **no solution
within this task**. No rate is inferred outside the tested range. The
host-owned constant-basal case at 75%, native BC-008 traces, solver agreement
including reference-solver checks of no-solution grid points,
glucose and insulin balances and an exact fresh-process repeat are controls.

## Run with the included declarations

Use the same checkout for the new BC-008 archive and this run, because the
native identity includes its installed source paths. From the repository
root:

```console
uv sync --locked
uv sync --locked --project experiments/m0/simglucose
uv run --locked python -m experiments.m4.feedback.run \
  --output /tmp/bc008-for-equivalence
uv run --locked python -m experiments.m4.basal_equivalence.run \
  --reference /tmp/bc008-for-equivalence \
  --reference-model experiments/m4/causal_secretion/example_model.py \
  --reference-declaration experiments/m4/causal_secretion/example_model.json \
  --variant-model experiments/m4/causal_secretion/example_model.py \
  --variant-declaration experiments/m4/causal_secretion/example_variant_model.json \
  --output /tmp/m4-basal-equivalence
```

The reference slot must use the pinned example declaration and matching
source file, because its anchor trajectory is checked against BC-008. The
variant slot can use another locally trusted one-file causal model with a
different model ID. Its contract, source hash, units, purity expectation and
locked dependencies are described in the
[causal intake guide](m4-causal-secretion.md). `--timeout` bounds each
worker in seconds (default 1800, maximum 3600). An existing output path is
refused. The output contains the verified full BC-008 reference, both source
files and declarations, code and lock snapshots, every search trajectory,
the failure record if needed and a repeat from a fresh worker process.

## Read and reconstruct the result

In the [internal execution record](../experiments/m4/basal_equivalence/execution.json),
the BC-008-equivalent example matches at the starting 75% SC rate. The
declared smaller-beta/K synthetic variant remains above the target even at
the 100% domain endpoint, so the result is `unbracketed`. That is a valid
bounded finding, not an estimated rate beyond 100%. The two declarations
share one source file and differ in parameters; they do not establish broad
compatibility with unrelated biological models.

The [ultradian response worked example](m4-ultradian-basal-equivalence.md)
uses a structurally different published response component in the variant
slot. Its source-pinned plan reuses the same search protocol and adds
artifact-derived glucose-shape diagnostics and a separate 75% SC fasting
comparison. Its synthetic amplitude and pancreatic route remain explicit.

Reconstruct the completed report without executing either supplied source or
the numerical solver:

```console
uv run --locked python -m experiments.m4.basal_equivalence.report \
  /tmp/m4-basal-equivalence --output /tmp/m4-basal-reconstructed.json
```

`report.json` records each tested factor and AUC, the target, each model's
search status, any confirmed match, fasting final glucose at a match,
numerical criteria and exact repeat checks. Matching one AUC does not match
the whole glucose curve, establish biological accuracy or specify a safe
insulin dose. Human observations and independent domain interpretation
remain separate evidence steps.
