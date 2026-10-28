# Run a sourced ultradian secretion response in M4

**Current public scope:** this native research route is outside the initial
two-task public exercise. Its pinned environments retain advisories and are
excluded from automatic public installation. Read the
[current runtime and CI policy](publication-security.md) before using the
historical setup commands below.

This worked example connects a **different published pancreatic-response
structure** to the unchanged [causal M4 feedback task](m4-causal-secretion.md).
The complete algebraic `f1(G)` response specified by Karamched et al. (2021)
has a saturating sigmoid shape. It uses only current glucose and has no
secretion delay state, positive-slope term or whole-trace fitted potentiation.
The adapter uses an explicitly synthetic amplitude and host pancreatic route.
It does not reproduce the publication's full six-state ultradian physiology,
oscillations or chaos experiment.

## Source choice and compatibility

Scientific source: Bhargav Karamched, George Hripcsak, David Albers and
William Ott, *Delay-induced uncertainty for a paradigmatic glucose–insulin
model*, **Chaos** 31(2), 023142 (2021),
[doi:10.1063/5.0027682](https://doi.org/10.1063/5.0027682).
Section II, printed p. 023142-3, specifies `f1`; Table I, printed
p. 023142-12, specifies the selected nominal shape. The equation and table
were visually checked in the [author PDF](https://www.math.fsu.edu/~karamche/DIU_chaos.pdf).
The [source register](../experiments/m4/ultradian_secretion/sources.json)
pins that PDF's SHA-256, locators, ancestry, rights boundaries and selection.

This is a Sturis-derived ultradian response, as formulated in the inspected
2021 primary paper. It is structurally distinct from BC-008's Dalla Man
delayed-static/positive-slope source, rather than a parameter variant of its
example. Original 1991 parameter parity is not claimed. The earlier
[Mari audit](research/m4-independent-source-preflight.md) retains its negative
complete-method verdict. Topp's full beta-cell-mass model was screened but
not selected: its slow mass dynamics need a separate state/equilibrium scope.

| Requirement | Selected component |
| --- | --- |
| Glucose information | Current glucose concentration only; same-stage derivative is unused |
| Source states | None; required M4 `Z` stays at `Sb` with `Zdot=0` and is unused |
| Potentiation or fitted trajectory | None in `f1` |
| Output | Total normalized source rate, not an evoked increment plus a second basal |
| Host compatibility | Basal identity at `G=h`; pure, repeated/out-of-order callback; finite nonnegative rates |
| Software rights | Original OpenT1D equation implementation under Apache-2.0; no paper, author code, figures or data vendored |

## Exact response, units and adaptations

The published function is

```text
f1(Gamount) = Rm / (1 + exp(-Gamount/(Vg*C1) + a1))
```

`Gamount` is glucose amount in mg, `Vg` is glucose space in L and `f1` is
insulin production in `mU/min`. The selected table gives `Vg=10 L`,
`Rm=209 mU/min`, dimensionless `a1=6.6` and `C1=300 mg/L`. Because the
host supplies concentration `g` in mg/dL, `Gamount/Vg = 10*g` in mg/L.
The full source response component and its port are therefore

```text
r(g) = 1 / (1 + exp(a1 - 10*g/C1))
Spo  = Sb * r(g) / r(h)
Zdot = 0
```

`r` and its ratio are dimensionless; `Sb` and `Spo` are `pmol/(kg min)`.
Time remains minutes. The factor 10 is a concentration conversion, not
body-size or molar scaling. Normalization replaces the published amplitude
with a declared synthetic maximum `Sb/r(h)` in molar units. **We do not
convert or adopt 209 mU/min as a calibrated pancreatic rate.** No insulin
activity-to-mole factor, patient weight, secretion volume or anatomical
beta-cell mass is inferred. This preserves the entire published sigmoid
shape with an explicitly different amplitude.

The response has its inflection at `g=a1*C1/10=198 mg/dL`. It is positive
at zero glucose and saturates toward one; the implementation uses stable
exponential branches and does not clip the lower response to zero. Glucose
below `h` reduces the total rate below `Sb`, preserving the source shape.
`h` is a host normalization point, not the publication's sigmoid threshold.

There is a separate **route adaptation**: the original `f1` enters the
plasma-insulin equation (Eq. 1a). Here its normalized shape is assigned to
the M4 pancreatic inlet `Spo`. The host owns portal transit, liver arrival,
hepatic/peripheral losses, initial plasma insulin and fixed SC basal
replacement. This hybrid does not establish a human prehepatic secretion
rate, first-pass correction or equivalence to the original physiology.
[Decision 0051](decisions/0051-m4-ultradian-response-component.md) records
these conventions. `M4-CAUSAL/1` and BC-008 remain unchanged.

## Verify and execute

Use the repository root and fresh output paths:

```console
uv sync --locked
uv sync --locked --project experiments/m0/simglucose
uv run --locked python -m experiments.m4.ultradian_secretion.verify \
  --output /tmp/m4-ultradian-equations.json
uv run --locked python -m unittest tests.test_m4_ultradian_secretion -v
uv run --locked --project experiments/m0/simglucose \
  python -m unittest experiments.m4.ultradian_secretion.test_numerical -v
uv run --locked python -m experiments.m4.feedback.run \
  --output /tmp/m4-ultradian-bc008-reference
uv run --locked python -m experiments.m4.causal_secretion.run \
  --model experiments/m4/ultradian_secretion/model.py \
  --declaration experiments/m4/ultradian_secretion/model.json \
  --reference /tmp/m4-ultradian-bc008-reference \
  --output /tmp/m4-ultradian-feedback
uv run --locked python -S -m experiments.m4.causal_secretion.report \
  /tmp/m4-ultradian-feedback --output /tmp/m4-ultradian-reconstructed.json
cmp /tmp/m4-ultradian-feedback/report.json /tmp/m4-ultradian-reconstructed.json
uv run --locked python scripts/check.py
```

The [equation checker](../experiments/m4/ultradian_secretion/verify.py)
evaluates the direct published amount-space function with 60-digit Decimal
arithmetic and nominal `Rm`, `Vg`, `C1`, `a1`, then independently normalizes
its outputs. This checks conversion and equation transcription against the
single-file adapter at eight points, including basal, inflection and
saturation. It also executes the existing basal/purity preflight. Root tests
check the inflection derivative, monotonicity, zero amplitude, source-state
and glucose-slope independence, low branch and rejection of invalid inputs.
Three scientific-runtime tests check source-to-portal locality, the basal
derivative and a closed-form constant-glucose portal/amount response using
the actual host RHS.

The unchanged runner compares the candidate with constant basal and BC-008
in fasting and the initial 30 g gastric load, using both frozen solvers.
It retains model identity, code, runtime lock, trajectories, flux ledgers,
failures and a fresh-process repeat. Reconstruction verifies these artifacts
without importing the candidate or a numerical simulator. No shape or
criterion is selected from the coupled result.

## Internal execution, 28 September 2026

The isolated branch is `codex/m4-ultradian-secretion`, based on `fad2a4c`.
The [execution record](../experiments/m4/ultradian_secretion/execution.json)
records exact source/report hashes, actual checks and the ignored local
artifact paths. Both the fresh BC-008 reference and the candidate run pass.
All eight planned primary candidate/control/solver cases and their eight
fresh-process repeats completed, with byte-identical trajectory files.
`python -S` reconstructed a byte-identical report without numerical packages
or executing the supplied model. The five new root tests and three dedicated
scientific-runtime tests pass. Both locked environments synchronized, and
`uv run --locked python scripts/check.py` passed all repository gates,
including 741 root tests and the strict documentation build.

| Executed check | Maximum discrepancy | Frozen limit |
| --- | --- | --- |
| 60-digit equation oracle | 1.78e-15 pmol/(kg min) | 1e-12 |
| Coupled glucose solver difference, candidate and control | 2.73e-8 mg/dL | 0.01 |
| Coupled plasma-insulin solver difference | 5.50e-12 pmol/L | 0.01 |
| Coupled source-rate solver difference | 1.62e-12 pmol/(kg min) | 1e-5 |
| Insulin inventory balance | 1.61e-11 pmol/kg | 1e-6 |
| Glucose inventory balance | 3.67e-8 mg/kg | 1e-5 |
| Fasting glucose drift | 1.46e-10 mg/dL | 0.01 |
| Fasting plasma-insulin drift | 2.98e-10 pmol/L | 0.01 |
| Host-control parity and repeat difference | 0 | Exact control/repeat limits |

In fasting, all sources remain at their matched initial glucose to numerical
precision. The 30 g load gives the following descriptive glucose outcomes
over 240 minutes; AUC is the signed integral relative to initial glucose.

| Source | Peak (mg/dL) | Final (mg/dL) | Baseline-relative AUC (mg min/dL) |
| --- | --- | --- | --- |
| Basal-normalized ultradian f1 | 170.800 | 167.834 | 6087.737 |
| Host constant basal | 183.201 | 183.201 | 7578.454 |
| BC-008 Dalla Man response | 166.819 | 147.747 | 3378.091 |

The candidate's pancreatic total is 377.382 pmol/kg and liver arrival is
375.502 pmol/kg. Their difference remains in the host portal inventory;
it is not a second loss or a duplicate basal. These different responses
exercise model intake and preserved accounting. They do not rank biological
models or infer an insulin requirement. No parameter was adjusted after
inspecting these outcomes. The independent algebraic zero/10,000 mg/dL
stress points are outside the coupled scenario domain and are not new
physiological scenarios.

## Evidence scope

The [SC-equivalence worked example](m4-ultradian-basal-equivalence.md) uses
this same source declaration in the existing frozen SC search and displays
its glucose-shape diagnostics. No source shape or amplitude is retuned.

The result is an internally verified source-component intake on invented
scenarios. A glucose contrast describes this composition; it is not accuracy,
superiority, residual T1D calibration or a therapy effect. Fixed SC basal
replacement is not an insulin requirement or dosing recommendation. Source
rights, human applicability, whole-engine reproduction and external review
remain separate from these software checks.
