# M4 independent secretion-source compatibility preflight

**Verdict, 27 September 2026:** Mari et al. (2002) is an independent,
published secretion model, but its complete multiple-meal method cannot be
run faithfully through `M4-CAUSAL/1`. This is a source and interface audit,
not a model implementation, numerical comparison or biological assessment.
No participant data, published software or coefficients were imported.

## Inspected source and scope

The primary source is Andrea Mari, Andrea Tura, Amalia Gastaldelli and Ele
Ferrannini, *Assessing Insulin Secretion by Modeling in Multiple-Meal Tests:
Role of Potentiation*, **Diabetes** 51(Suppl. 1), S221–S226 (2002),
[DOI 10.2337/diabetes.51.2007.s221](https://doi.org/10.2337/diabetes.51.2007.s221),
[PubMed 11815483](https://pubmed.ncbi.nlm.nih.gov/11815483/). The original
article's [author-uploaded full text](https://www.researchgate.net/publication/11543470_Assessing_Insulin_Secretion_by_Modeling_in_Multiple-Meal_Tests_Role_of_Potentiation)
was inspected for equations 1–6 and Appendix A. The publisher PDF endpoint
returned HTTP 403 during this audit, so the mathematical transcription below
rests on the accessible full-text rendering. The paper studied nine
nondiabetic controls and nine people with type 2 diabetes during three meals;
it is not a residual type 1 diabetes calibration.

The related original [Mari et al. AJP paper](https://doi.org/10.1152/ajpendo.00093.2002)
uses the same static/dynamic/potentiation separation for normal-subject meal
and oral-glucose tests. It corroborates the structure and surface-area
reporting, but is not a second, independent model or a substitute for the
primary paper's equations.

## Equation and ownership inventory

| Original-paper locator | Published mathematical role | M4 boundary implication |
| --- | --- | --- |
| Eq. 1 | `dG/dt = -k G + R(t)`, with `k=0.012 min^-1`; piecewise-linear `R(t)` smooths sampled glucose | Observation preprocessing, not a second glucose physiology to add to BC-008. The host already supplies same-stage native `G` and `Gdot`. |
| Eq. 2, Appendix A | `Sg(t) = exp(Q(t)) f(G(t))`. `Q` is a zero-mean, piecewise-linear fitted function; `f` is a positive, four-parameter dose response in glucose | The potentiation trajectory is an additional time-varying input. A scalar gain or `Q=0` omits a named model component. |
| Eq. 3 | `Sd(t) = pd max(dG/dt, 0)` | The algebraic positive-slope term could use the callback's same-stage derivative after explicit unit conversion. |
| Eq. 4 | `S(t) = Sg(t) + Sd(t)` | This is pancreatic secretion, upstream of the host-owned portal transit and liver inlet. |
| Eq. 5 | `C(t) = h(t) * S(t)` with individual two-exponential C-peptide kinetics | Observation/deconvolution belongs outside the pancreatic callback; the complete fitted method needs this measured output. |
| Eq. 6 | Whole-trace glucose/C-peptide fit with regularization of `R` and `Q` and a `Q` penalty | Estimating `Q` from an entire challenge is an inverse problem, not a causal online rule specified by the paper. |

Appendix A specifies the dose response exactly as

```text
f(G) = p3*G + (p4-p3) *
       { [log(cosh(p1*(G-p2))) - log(cosh(p1*p2))]/p1
         + tanh(p1*p2)*G } / [1+tanh(p1*p2)]
```

Here `p1` sets transition curvature, `p2` its glucose location, and `p3`
and `p4` the limiting low/high slopes. This transcription identifies a future
implementation target; it has not been executed or numerically verified.
Glucose is in `mmol/L` in the paper. Its unnormalized secretion `S` is
described in `pmol/min`; reported secretion parameters and comparisons are
normalized by body surface area (`pmol/(min m²)`). Those are distinct unit
conventions and neither is the callback's `pmol/(kg min)`. Time is minutes;
`Q` and `exp(Q)` are dimensionless. A port must specify the glucose molar
conversion and whether its sourced coefficients are whole-body or
surface-area normalized, then justify any body-size transformation. The
present BC-008 virtual adult has mass but no height or body-surface-area
input to this callback. We do not infer it or reuse type 2 diabetes
coefficients as residual T1D values.

## Compatibility decision against the frozen intake

The [current contract](../../experiments/m4/causal_secretion/protocol.json)
passes current time, native glucose in `mg/dL`, its current derivative, one
rate-valued state `Z` initialized to host basal `Sb`, threshold and a small
flat numeric parameter map. It calls a pure function in arbitrary solver
order. It owns basal replacement, portal `Pdot = Spo - gamma*P` and liver
arrival. The [interface decision](../decisions/0048-m4-causal-secretion-intake.md)
deliberately excludes arbitrary extra states and future glucose.

| Requirement | Available now? | Disposition |
| --- | --- | --- |
| Same-stage `G`, positive `Gdot`, time | Yes, after declared molar conversion | Algebraic subcomponent only. |
| Four-parameter `f(G)` | Representable as numeric parameters | Needs independently verified code, source-specific parameters and basal handling. |
| Published `Q(t)` over the meal experiment | No sourced trajectory, causal evolution law or time-series input | **Blocking** for the complete method. Its zero-mean constraint and Eq. 6 fit use the full measured experiment. |
| `Z` as potentiation memory | No: `Z` is a rate, starts at `Sb`, and is the only source state | Reinterpreting it as dimensionless `Q` silently breaks the frozen contract. |
| Source output scale and basal | No established BSA/body-mass mapping or source-specific fasting equilibrium for BC-008 | **Blocking** for the declared output unit and preflight. |
| Source C-peptide observation and estimation | Separate BC-010 observation exists, but no Mari-specific fitted full-trace input | Fitting it inside feedback would use future measurements. |

The published secretion formula is algebraic **if** an externally established
`Q(t)` is supplied; it does not itself require another ODE state. The
blocking point is that the paper estimates `Q(t)` from a complete measured
challenge and gives no prospective causal law for it. Encoding a prerecorded
`Q` curve from the evaluated feedback trajectory would leak future
information. Setting `Q=0`, prescribing an invented curve or adding an
invented `Q` ODE may be useful synthetic variants, but none is a faithful
execution of the complete Mari 2002 method. A callback returning such a
variant must carry a new, explicit model identity and cannot be labeled a
Mari reproduction.

The paper provides an equation description, not a verified reusable software
license or participant-level data grant for this repository. Citation and
the original compatibility analysis above do not imply permission to vendor
the full text, code, figures or data. No such assets were copied.

## Bounded next implementation gate

The next internally testable step is **not** to run a fabricated Mari
adapter. First choose and source a genuinely prospective potentiation rule
or a published model whose complete pancreatic source is causal. For that
specific candidate:

1. Record exact equations and independently check source transcription at
   ordinary, threshold, falling-glucose and zero-gain points.
2. Decide whether it fits the unchanged one-rate-state signature. If it
   needs time-series inputs or additional source states, propose a versioned
   interface with their units, initialization, causality and source identity;
   keep `M4-CAUSAL/1` and BC-008 unchanged.
3. Record parameter ancestry, basal equilibrium, the glucose and secretion
   unit transformations, and host versus source ownership of portal transit
   and C-peptide observation. Assess code and data rights separately.
4. Only then run the fixed invented feedback scenarios, numerical refinement,
   mass accounting, fresh-process repetition and artifact reconstruction.

This gate is an internal software decision. It does not require external
human review or patient data before implementation. Any later empirical or
biological claim still requires its own authorized observations and review.
