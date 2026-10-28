# Run a supplied secretion model in the M4 synthetic feedback task

**Current public scope:** this native research route is outside the initial
two-task public exercise. Its pinned environments retain advisories and are
excluded from automatic public installation. Read the
[current runtime and CI policy](publication-security.md) before using the
historical setup commands below.

This bounded workflow evaluates a trusted local secretion source on the
unchanged [BC-008 synthetic feedback task](research/m4-feedback-results.md).
It runs one fasting and one initial 30 g gastric-load scenario in the pinned
adult#001 metabolic route. The report compares modeled glucose and plasma
insulin with the verified BC-008 source and a host-generated constant-basal
control. The fixed SC basal schedule is the same in both candidate and
control. No bolus, controller, sensor, data fitting or patient record is used.

The earlier [prescribed-glucose intake](m4-external-secretion.md) accepts a
complete secretion array. This feedback task needs a separate **causal**
contract because future glucose values do not exist when the solver calls the
model.

## Model contract

Provide one regular Python source file defining:

```python
def evaluate(
    time_min,
    glucose_mg_dl,
    glucose_rate_mg_dl_min,
    z_pmol_kg_min,
    basal_pmol_kg_min,
    threshold_mg_dl,
    parameters,
):
    return [z_derivative_pmol_kg_min2, pancreatic_rate_pmol_kg_min]
```

`glucose_mg_dl` and its rate come from the same native solver state and
derivative. `Z` is the one source-owned state, in `pmol/(kg min)`; the host
initializes it at the declared synthetic basal rate `Sb`. The source returns
its derivative and nonnegative **pancreatic appearance** `Spo` in
`pmol/(kg min)`. The host integrates portal amount `P` with
`Pdot = Spo − gamma·P` and sends only `S = gamma·P` into the guarded native
liver inlet. The host also owns the fixed 25% synthetic SC basal replacement
and matches initial plasma insulin. Do not add a second basal or portal
transit inside the model.

The callback must be a pure function of its arguments. An adaptive ODE
solver may call it more than once at a time or in nonmonotonic order. It
cannot keep hidden state, use future glucose, or emit impulses. The bounded
contract requires a basal equilibrium at the initial glucose and zero
glucose rate, for every time in the 240-minute horizon. Rates must be finite
and between 0 and 1000 `pmol/(kg min)`; the absolute state derivative must
not exceed 1000 `pmol/(kg min²)`. These are engineering limits, not
physiological ranges.

Supply a JSON declaration with model ID, ancestry, source SHA-256, rights
basis, dependencies, a small flat numeric `parameters` mapping, and exact
output unit. See the included
[`example_model.json`](../experiments/m4/causal_secretion/example_model.json)
and [`example_model.py`](../experiments/m4/causal_secretion/example_model.py).
That adapter restates the already attributed BC-008 secretion equations; it
is an interface example, not a new model or independent reference. A
researcher's source and dependencies must be legally and scientifically
assessed for their intended use. The workflow checks the declared source
hash, not authorship or rights. It runs trusted source in the locked BC-008
Python environment; arbitrary separate packages or a custom interpreter
are not supported by this version.

The [synthetic parameter variant](../experiments/m4/causal_secretion/example_variant_model.json)
uses the same example code with smaller declared beta and K values. It
exercises a nonzero meal-scenario contrast; it is not another sourced biological
method.

An [independent published-source compatibility audit](research/m4-independent-source-preflight.md)
tested the complete Mari et al. (2002) multiple-meal secretion method against
this signature. Its positive-glucose-derivative component can be expressed
pointwise, but the published potentiation trajectory is estimated from a
complete glucose/C-peptide experiment. The audit therefore does not supply
a Mari adapter or a synthetic Mari result. It records the exact interface,
unit and basal gaps before any versioned extension is considered.

The [ultradian f1 worked example](m4-ultradian-secretion.md) supplies a
different published response structure: a complete stateless glucose
sigmoid, with explicit synthetic basal amplitude and pancreatic route
adaptation. Its unused `Z` remains at basal; no interface extension is needed.
This is a sourced component, not reproduction of the full ultradian engine.

## Execute

From the repository root, prepare the locked environments and create a new
BC-008 reference archive:

```console
uv sync --locked
uv sync --locked --project experiments/m0/simglucose
uv run --locked python -m experiments.m4.feedback.run \
  --output /tmp/bc008-reference
```

Run the included adapter, or substitute your own source and matching
declaration:

```console
uv run --locked python -m experiments.m4.causal_secretion.run \
  --model experiments/m4/causal_secretion/example_model.py \
  --declaration experiments/m4/causal_secretion/example_model.json \
  --reference /tmp/bc008-reference \
  --output /tmp/m4-causal-result
```

`--timeout` bounds each numerical worker in seconds (default 600, allowed
1–1800). An existing output path is refused. The output copies the whole
verified BC-008 reference, model source and declaration, code snapshots,
runtime lock, every numerical case, logs and a fresh-process repeat.
`manifest.json` and `failure-report.json` preserve a failed attempt without
fabricating a completed scenario comparison.

## Interpret and reconstruct

`report.json` records solver differences, insulin and glucose balances,
nonnegative inventories, basal-control parity, repeat equality, glucose
peak/nadir/final value, baseline-relative AUC, and pancreatic and liver
amounts. The comparison with BC-008 is descriptive: a numerical difference
does not establish biological accuracy or superiority. The included
BC-008-equivalent adapter should match the reference; a different source
can produce a nonzero synthetic contrast. This workflow does **not**
calculate an optimized external insulin requirement. The 25% basal
replacement is a fixed experiment setting, not a treatment or dose result.
The [internal execution record](../experiments/m4/causal_secretion/execution.json)
captures the exact source and report hashes, numerical criteria, zero
reference contrast for the adapter, nonzero meal-scenario contrast, reconstruction
and preserved failure check. These are software checks on invented scenarios.

Reconstruct the completed report without running the supplied source or
either numerical solver:

```console
uv run --locked python -m experiments.m4.causal_secretion.report \
  /tmp/m4-causal-result --output /tmp/m4-causal-reconstruction.json
```

Reconstruction verifies the full BC-008 archive, source identity, case and
runtime identities, saved numerical ledgers, control parity and exact
fresh-process case repetition. It cannot independently prove that an
arbitrary Python callback was pure or that its biological assumptions fit
people with type 1 diabetes. C-peptide observation and human assessment
remain separate.
