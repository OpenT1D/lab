# Compare the ultradian response on the frozen SC-equivalence task

**Current public scope:** this native research route is outside the initial
two-task public exercise. Its pinned environments retain advisories and are
excluded from automatic public installation. Read the
[current runtime and CI policy](publication-security.md) before using the
historical setup commands below.

This worked example uses the structurally distinct
[ultradian f1 response](m4-ultradian-secretion.md) as the variant in the
existing [synthetic basal-equivalence workflow](m4-synthetic-basal-equivalence.md).
The original BC-008-equivalent Dalla Man adapter remains the reference slot.
The experiment checks source-component compatibility and describes modeled
glucose outcomes under a fixed external SC infusion.

## Frozen comparison

The [source-pinned plan](../experiments/m4/ultradian_basal_equivalence/plan.json),
`M4-ULTRADIAN-BASAL/1`, was fixed before this execution. It binds the exact
two source files and declarations, all three existing protocols and the
additional diagnostics. It leaves `M4-BASAL-EQUIVALENCE/1`, `M4-CAUSAL/1`,
BC-008 and their implementations unchanged.

The target remains BC-008's 240-minute baseline-relative glucose AUC after
an invented 30 g gastric load. The search varies only post-zero constant
SC infusion from 50 to 100% of native basal. Synthetic secretion basal,
source shape, normalization glucose, portal transit and every initial native
inventory remain fixed at the original 25% replacement boundary. No source
parameter is fitted. Unbracketed, nonmonotone and resolution-limited searches
remain explicit outcomes without extrapolation.

The ultradian adapter preserves the full published sigmoid shape using a
synthetic molar amplitude and an exploratory pancreatic/portal route. It
does not reproduce the full six-state ultradian physiology or a calibrated
prehepatic human secretion rate. The source equations, ancestry, rights and
these adaptations stay in the canonical
[response guide](m4-ultradian-secretion.md#exact-response-units-and-adaptations).

## Additional glucose diagnostics

The search archive already retains trajectories for every attempted factor.
The new standard-library report reconstructs their AUC, peak, nadir and
final glucose after validating the complete parent report. It also displays
every reference-solver confirmation and, if a solution exists, the meal and
fasting outcomes at that confirmed factor.

The frozen search runs fasting only at a confirmed solution. Independently
of its result, this example therefore runs the unchanged causal intake at
the existing **75% SC starting factor** to record fasting behavior.
It uses the same fresh BC-008 archive as the search. Their shared 75% meal
trajectory must have exactly equal states and source rates under the tight
solver. This check binds the two workflows at the same initial conditions.
Fasting at 75% is a starting-factor diagnostic; it is not fasting behavior
at an unresolved equivalent rate. Fasting at the other grid factors is not
part of this plan.

## Execute and reconstruct

Run from one checkout with fresh output directories. Native BC-008 identity
includes installed source paths, so references from another worktree cannot
be substituted. The example below creates only invented simulation artifacts.

```console
uv sync --locked
uv sync --locked --project experiments/m0/simglucose
mkdir -p /tmp/m4-ultradian-basal
uv run --locked python -m experiments.m4.ultradian_secretion.verify \
  --output /tmp/m4-ultradian-basal/equations.json
uv run --locked python -m experiments.m4.feedback.run \
  --output /tmp/m4-ultradian-basal/bc008-reference
uv run --locked python -m experiments.m4.basal_equivalence.run \
  --reference /tmp/m4-ultradian-basal/bc008-reference \
  --reference-model experiments/m4/causal_secretion/example_model.py \
  --reference-declaration experiments/m4/causal_secretion/example_model.json \
  --variant-model experiments/m4/ultradian_secretion/model.py \
  --variant-declaration experiments/m4/ultradian_secretion/model.json \
  --output /tmp/m4-ultradian-basal/search
uv run --locked python -m experiments.m4.causal_secretion.run \
  --reference /tmp/m4-ultradian-basal/bc008-reference \
  --model experiments/m4/ultradian_secretion/model.py \
  --declaration experiments/m4/ultradian_secretion/model.json \
  --output /tmp/m4-ultradian-basal/causal
uv run --locked python -S -m experiments.m4.basal_equivalence.report \
  /tmp/m4-ultradian-basal/search \
  --output /tmp/m4-ultradian-basal/search-reconstructed.json
cmp /tmp/m4-ultradian-basal/search/report.json \
  /tmp/m4-ultradian-basal/search-reconstructed.json
uv run --locked python -S -m experiments.m4.causal_secretion.report \
  /tmp/m4-ultradian-basal/causal \
  --output /tmp/m4-ultradian-basal/causal-reconstructed.json
cmp /tmp/m4-ultradian-basal/causal/report.json \
  /tmp/m4-ultradian-basal/causal-reconstructed.json
uv run --locked python -S -m experiments.m4.ultradian_basal_equivalence.report \
  --search /tmp/m4-ultradian-basal/search \
  --causal /tmp/m4-ultradian-basal/causal \
  --output /tmp/m4-ultradian-basal/diagnostics.json
uv run --locked python scripts/check.py
```

Each original runner archives source/declaration identities, code, runtime
locks, every numerical attempt, failure status and a fresh-process repeat.
The diagnostic report verifies both complete parent archives without
importing supplied models or numerical packages. Its exact source pairing
rejects the older parameter-only variant, edited protocols and mixed BC-008
reference identities. Four root tests exercise those provenance boundaries.

## Internal execution, 29 September 2026

The isolated branch is `codex/m4-ultradian-basal-equivalence`, based on
`144f6db`. The [execution record](../experiments/m4/ultradian_basal_equivalence/execution.json)
records the exact plan, source and artifact hashes and the retained local
paths. A fresh BC-008 reference passes. The search completes all 19 primary
attempts and their 19 fresh-process repeats; the separate causal diagnostic
completes eight cases and their eight repeats. Both parent reports have zero
repeat discrepancy and byte-identical `python -S` reconstructions. The shared
75% tight-solver meal states and source rates are exactly equal between the
two workflows. The diagnostic report also repeats byte-identically.

The unchanged target is **3378.091 mg min/dL**. The Dalla Man reference slot
matches at 75% native SC infusion, with a reference-solver residual of zero.
The ultradian source's complete grid decreases monotonically but remains
above the target, including at 100%. Both solvers confirm all five grid
points. Its status is **`unbracketed`**, with no equivalent rate reported.
No bisection is appropriate without a bracket; the range is not expanded.

| Ultradian SC factor | Reference-solver AUC (mg min/dL) | Peak (mg/dL) | Final (mg/dL) |
| --- | --- | --- | --- |
| 50% | 6445.123 | 172.642 | 172.625 |
| 62.5% | 6265.883 | 170.916 | 170.219 |
| 75% | 6087.737 | 170.800 | 167.834 |
| 87.5% | 5910.696 | 170.689 | 165.469 |
| 100% | 5734.769 | 170.582 | 163.124 |

All meal nadirs are the initial 138.56 mg/dL. At the shared 75% starting
factor, the reference adapter's meal peak is 166.819 mg/dL and final glucose
is 147.747 mg/dL. The ultradian meal response therefore differs in both
integral and shape. Its separate fasting trace stays at 138.56 mg/dL within
1.46e-10 mg/dL. That fasting result uses the original starting factor;
there is no fasting-at-solution result for the unbracketed source.

| Search verification | Maximum discrepancy | Frozen limit |
| --- | --- | --- |
| Glucose solver agreement | 2.21e-8 mg/dL | 0.01 |
| Plasma-insulin solver agreement | 7.09e-7 pmol/L | 0.01 |
| AUC solver agreement | 2.28e-6 mg min/dL | 0.1 |
| Insulin inventory balance | 2.01e-11 pmol/kg | 1e-6 |
| Glucose inventory balance | 3.67e-8 mg/kg | 1e-5 |
| Reference/control anchors and fresh-process repeat | 0 | Existing frozen limits |

The equation oracle again passes with maximum rate error
1.78e-15 pmol/(kg min). The additional causal run passes its own frozen
solver, balance, fasting and repeat limits. These checks validate this
software composition and the negative bounded search outcome; they do not
rank biological models or imply delivery beyond the search domain.

## Evidence boundary

These are source-component and numerical workflow checks on invented
scenarios. Matching a scalar AUC would not match a full glucose curve or
establish a person's insulin requirement. A bounded no-solution outcome does
not justify a rate outside the prescribed range. Initial SC depots stay fixed,
so changed delivery causes a defined transient. Human calibration, model
validity, population applicability and treatment interpretation retain their
own evidence requirements.
