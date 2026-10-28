# Dalla Man 2007 secretion reference for BC-008

## Identity and evidence status

**Implemented with an independent analytic source reference and bounded synthetic metabolic feedback in [BC-008](../m4-feedback-results.md).** BC-008-P1 preserves the earlier algebra/initial-state preflight. Neither result reproduces a published human meal or validates this composition in T1D.

Scientific source: Chiara Dalla Man, Robert A. Rizza and Claudio Cobelli, *Meal Simulation Model of the Glucose–Insulin System*, IEEE TBME 54(10), 1740–1749 (2007), [doi:10.1109/TBME.2007.893506](https://doi.org/10.1109/TBME.2007.893506). Equations 23–26, p. 1745, define secretion; Table I, p. 1743, supplies the selected normal-column coefficients. Those pages were visually inspected in the [public PDF](https://isbgroup.eu/files/Dalla%20Man%202007.pdf). The [source register](../../../experiments/m4/feedback/sources.json) records hashes, locations, access and rights boundaries.

The original model was developed using aggregate observations from normal subjects, with a smaller type 2 diabetes extension. The companion [GIM article](https://pmc.ncbi.nlm.nih.gov/articles/PMC2769591/) distinguishes static/dynamic secretion and replaces endogenous secretion with subcutaneous insulin for its T1D configuration. Adding the secretion equations to a pinned T1D virtual profile is therefore a new exploratory composition, not restoration of a validated residual-T1D component.

## Intended use and selection

Question: can glucose-responsive endogenous input alter one simulated glucose trajectory after controlling initial plasma insulin and basal delivery? The candidate accepts continuous plasma glucose and its instantaneous rate of change, including rising and falling phases. It has two states and explicit nonnegative total input, with a delayed static response and a response to positive glucose slope.

| Candidate | Suitability for the proposed feedback question | Decision |
| --- | --- | --- |
| Existing BC-001 Pedersen–Cobelli reduced IVGTT equations | Declining post-bolus approximation; discarded derivative contributions and unresolved initialization cannot be silently generalized to a meal loop | Preserve unchanged as a separate reference |
| Full Pedersen–Cobelli granule-distribution model | Represents activation across glucose thresholds, including recruitment during rising glucose; requires the larger distribution/pool system and its own discretization/source verification | Scientifically relevant later alternative; exceeds this smallest feedback step |
| Dalla Man 2007 equations 23–26 | Explicit glucose-level and positive-slope control; two states; published coefficients; insulin liver inlet aligns with the selected engine's kinetic compartments | Select with explicit engine and population differences |

C-peptide deconvolution estimates a source from observations and is not a substitute for a glucose-driven source in this loop. The existing forward C-peptide branch remains separate.

## Equations and units

Time is minutes; G is plasma glucose in mg/dL and Gdot in mg/dL/min. The source's Y is a signed secretion-rate deviation (pmol/kg/min); P denotes its portal insulin state Ipo (pmol/kg). Define Z=Y+Sb so the implemented bookkeeping state is nonnegative. For fixed basal Sb and a declared hypothetical responsivity gain a:

```text
target = max(Sb + a*beta*(G-h), 0)
Zdot   = alpha*(target-Z)
Spo    = Z + a*K*max(Gdot, 0)
Pdot   = Spo-gamma*P
S      = gamma*P
```

Spo is pancreatic input into P; S is arrival at the liver. Both are pmol/(kg min). Equation 26 permits Y to approach -Sb below the glucose threshold. Clipping Y to zero would change the published lower branch. The max expression resolves the printed strict-inequality equality case by continuity. Z is a rate state, not an insulin amount; exclude it from physical insulin-inventory sums.

| Parameter | Value | Units and provenance |
| --- | --- | --- |
| alpha | 0.05 | 1/min; Table I normal column |
| beta | 0.11 | pmol/(kg min) per mg/dL; Table I normal column |
| K | 2.30 | pmol/kg per mg/dL; Table I normal column |
| gamma | 0.5 | 1/min; Table I normal column |
| h | Initial native plasma glucose, 138.56 | mg/dL; use source convention h=Gb with the selected virtual baseline, an explicit engineering adaptation |
| Sb | Derived by the BC-008 basal replacement rule | pmol/(kg min); synthetic balance choice, not the source's normal-subject estimate |
| a | 0, 0.25, 0.5 or 1 | Hypothetical common beta/K multiplier, not an estimated fraction of cells |

No parameters are fitted. Initialization is Z=Sb, P=Sb/gamma; this corresponds to Y=0 and stationary basal source. Gdot comes from the native plasma-glucose derivative at the same solver stage. It is not a derivative of CGM, sampled measurements or a prescribed exponential. No insulin molar-mass conversion or second body-mass normalization is needed for these equations.

## Composition and process ownership

The [BC-008 protocol](../m4-feedback-protocol.md) retains the pinned simglucose 13-state physiology and adds only S to its guarded liver-insulin derivative. The new source owns Z, P and portal transit. simglucose owns liver/plasma distribution, fixed m30 hepatic loss, peripheral loss, SC absorption and glucose/insulin action. The full 2007 model instead has time-varying hepatic extraction and an explicit portal-insulin term in glucose production. Neither is restored here; existing native coefficients are retained. The result is a hybrid exploratory model, not reproduction of the complete 2007 model or an inference about graft drainage.

C-peptide is excluded from the first feedback experiment. A subsequent equimolar observation extension must state whether its published input represents pancreatic secretion or post-transit arrival, and justify any separate transport assumption. Sending the new Spo or S into the old BC-007 contract without that decision would change its meaning.

## Execution, uncertainty and rights

The implemented feedback solver uses the existing simglucose lock, Python 3.12, NumPy 1.26.4 and SciPy 1.13.1. Solver settings, scenario/initial-state controls, failure rules and numerical tolerances are frozen in the [machine protocol](../../../experiments/m4/feedback/protocol.json). The [execution guide and results](../m4-feedback-results.md) document all checks, fresh-process repetition and reconstruction.

Common scaling of a and inverse scaling of beta/K leaves the source unchanged; their separate values are not identifiable from its output. Human glucose alone cannot separate this source from clearance, insulin action and glucose appearance without additional information. Population-specific responsivity, baseline, portal kinetics, assay behavior and endogenous versus administered insulin require observations. Numerical success cannot establish a treatment mechanism, anatomical cell mass or clinical insulin requirement.

The mathematical implementation, analytic reference and arithmetic checker are original OpenT1D work. No author code, figures, parameter table or participant records are vendored. GIM software is described in the primary article; a verified redistributable release was not obtained. BioModels BIOMD0000000379 was located as a possible later independent encoding, but its exact version, deviations and asset rights were not verified or used. The installed simglucose dependency retains its upstream license and source guards. No new collaboration or external review is claimed.
