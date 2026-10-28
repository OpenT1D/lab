# BC-009: hepatic assumptions, evidence and frozen comparison

This internal OT-026 assessment asks how BC-008's fixed hepatic insulin extraction and omitted direct portal signal affect its synthetic secretion contrast. The [machine protocol](../../experiments/m4/hepatic/protocol.json), specified before execution from `c6cb206`, defines a separate comparison. The [decision](../decisions/0024-hepatic-structure-sensitivity.md) preserves BC-008. This is sensitivity to two specified mathematical relations, not evidence that the more complex physiology is correct for residual T1D or a graft.

## Implementation and model scope

The [scalar relations](../../experiments/m4/hepatic/model.py), [numerical wrapper](../../experiments/m4/hepatic/numerical.py) and [artifact assessment](../../experiments/m4/hepatic/report.py) are original OpenT1D code under the repository license. They reuse the separately pinned BC-008 source/native implementation and its unchanged locked runtime. No author software, copied figure or restricted observations are included. The [source register](../../experiments/m4/hepatic/sources.json) records inspected material and access limits. The [execution and results](m4-hepatic-results.md) distinguish numerical evidence from this model specification.

Time is in minutes; G is mg/dL, plasma I is pmol/L, liver/plasma/portal insulin amounts are pmol/kg, S and Spo are pmol/(kg min), EGP is mg/(kg min), and HE is dimensionless. Parameters are fixed and no quantities are fitted. The 20-state layout, initial values, time origin and reporting grid inherit the [BC-008 contract](m4-feedback-protocol.md). The intended use is a structural comparison in one synthetic virtual profile; neither T1D prediction, deconvolution, transplantation nor treatment selection is supported.

## Source findings and model boundary

Dalla Man, Rizza and Cobelli (2007), [DOI 10.1109/TBME.2007.893506](https://doi.org/10.1109/TBME.2007.893506), supplies the relations in equations 4–7 (p. 1743) and 10–12 (p. 1744). Those pages and Table I were visually rechecked in the public PDF. The normal-column values used here are m5=0.0304 min kg/pmol and kp4=0.0618 mg/(pmol min). The literal m6=0.6471 is retained for an initialization diagnostic only. The source's P=Ipo is an insulin amount, not a measured portal blood concentration.

BC-008 uses m30 for hepatic loss and computes EGP from plasma glucose and a delayed systemic insulin signal. The pinned profile contains an unused m5 value, but this does not establish individual hepatic-extraction calibration. BC-009 records it without substituting it for the selected, traceable paper coefficient. Native m1/m2/m4, glucose effectiveness, insulin-action parameters and all other coefficients stay fixed; this remains a hybrid. A further calibration ambiguity is that the native delayed-insulin coefficient may already represent effects missing from its explicit equations. Adding a portal term without re-estimating the delayed term can therefore overlap effective biological action. Single ownership of the EGP calculation prevents code-level duplication; it does not prove a uniquely identified biological decomposition.

The published extraction fraction is `HE=m3/(m1+m3)`. This is a ratio of competing liver-compartment outflows, not hepatic removal divided by newly secreted insulin, and not the fraction of all whole-body clearance attributable to liver under every route. Recirculating plasma insulin also enters the liver. Multiplying the incoming secretion by a survival fraction in addition to m3 would double count removal. Similarly, the portal EGP signal acts through P, whereas extraction responds to liver arrival S=gamma*P; using Z or pancreatic appearance Spo changes the published model.

## Why additional terms are hypotheses

The paper cites [Meier, Veldhuis and Butler 2005](https://pubmed.ncbi.nlm.nih.gov/15919785/) for secretion-related extraction. That small healthy-human study measured hepatic/arterialized samples and flow, and associated pulsatile secretion with insulin removal. Its reported fractional extraction did not change significantly between the two conditions. This supports investigating extraction dynamics; it does not independently validate BC-009's negative linear relation between a smooth S and HE, its coefficient in residual T1D, or its extrapolation to a graft. The pulse pattern and removal amount must not be conflated with the mean extraction fraction.

[Edgerton et al. 2006](https://www.jci.org/articles/view/27073) experimentally varied portal versus peripheral insulin delivery in fasted dogs, with insulin/glucagon control and flux measurements. It provides mechanistic evidence that systemic insulin alone need not encode liver exposure. Species, stimulus and route prevent treating its numerical effects as human calibration for kp4. BC-009 has neither sinusoidal blood flow nor an anatomical graft-drainage model.

[Toffolo et al. 2006](https://www.research.unipd.it/retrieve/e14fb267-8bf5-3de1-e053-1705fe0ac030/E169.pdf), DOI 10.1152/ajpendo.00473.2004, illustrates separating secretion and posthepatic delivery with paired assays and independently informed insulin kinetics in an insulin-modified IVGTT. Its healthy participants and assumed population C-peptide kinetics do not establish validity in the target T1D population. No participant series, author program or external domain review has been obtained for this assessment.

## Equilibrium-preserving specification

Inherit the BC-008 baseline construction: source cases replace a prescribed quarter of SC basal appearance, preserving plasma insulin; initial Z=Sb and P0=Sb/gamma. Native-zero cases retain zero source and original SC input. Set Hb=m30/(m1+m30). For an enabled extraction relation:

```text
HE = Hb - m5*(S-Sb)
m6_effective = Hb + m5*Sb
m3 = m30 + m1*(HE-Hb)/((1-HE)*(1-Hb))
```

The m3 expression is algebraically the published `m1*HE/(1-HE)` and returns exactly native m30 at baseline. m6 is changed using the paper's equation 6; this is an explicit engineering intercept, not a new fit or a published T1D parameter. The native peripheral removal coefficient stays unchanged. At each solver stage replace the native hepatic loss in both the guarded liver derivative and its integrated-loss ledger.

For an enabled portal EGP relation:

```text
raw_EGP = native_kp1 - kp2*Gp - kp3*Id - kp4*(P-P0)
EGP = max(raw_EGP, 0)
kp1_effective = native_kp1 + kp4*P0
```

This changes the intercept using the paper's equation 12 so basal EGP is unchanged. Replace EGP in the guarded plasma-glucose derivative, then calculate Gdot for the secretion source from that corrected derivative in the same solver stage. Merely changing EGP in a report or using the previous native Gdot would break the coupled calculation. No algebraic loop occurs because P is an integrated state.

Using literal m6 while retaining BC-008's Sb, or subtracting absolute kp4*P without the intercept adjustment, changes the initial derivative. The executable audit quantifies those mismatches before trajectory interpretation; such unbalanced simulations are not mechanism comparators.

## Frozen experiment and evidence classification

Cross four variants (fixed, extraction only, portal only, both) with three source cases (native zero, constant basal, full responsivity), under fasting and the same 30 g initial gastric solid load. This yields 24 cases, each under all three unchanged BC-008 solvers. Initial conditions, 240-minute horizon, 0.25-minute output grid, SC schedule, source coefficients and native profile are identical across hepatic variants. No controller, bolus or observation model is added. Cases and thresholds are not selected using the resulting glucose response.

Measure full-response minus constant-basal contrasts within each variant, the change in that contrast relative to fixed, and the factorial interaction `both-extraction-portal+fixed`. Report signed glucose/insulin AUCs above baseline, sampled glucose peak/nadir, final concentrations, EGP and hepatic-loss integrals. A nonzero contrast is numerically resolved only above ten times its largest solver-dependent change, with the frozen floating-point floor. Zero, unresolved and opposite-direction outcomes are retained. There is no required improvement or clinically meaningful threshold.

Disabled equations and trajectories must match unchanged BC-008 exactly along the same numerical path. All variants must preserve the fasting baseline, native-zero behavior and constant-basal glucose within the frozen limits. Verify the source sees the corrected Gdot, independent literal-equation evaluations, insulin/portal balance and independently quadrature-integrated glucose flux balance. Repeat the worker in a fresh process. Record HE, m3, EGP, source rates, states, ledgers, transition roots, solver settings and all failures. The machine protocol specifies unit-labelled tolerances, independent quadrature targets and checks.

Stop at HE≤0 or HE≥0.999999 as explicit computational scope boundaries; the upper buffer avoids the singular rate at HE=1. These are not measured physiological limits. Also retain the BC-008 glucose envelope and negative-amount rule, exempting signed native insulin-action state x[6]. Do not clip HE or accept a shortened trajectory as a full result. Failed cases stay in the 24-case denominator and prevent accepting affected contrasts.

Turning a relation on/off is a structural diagnostic, not a plausible parameter range or confidence interval. Common gain/beta/K confounding remains. No human parameters are estimated, and a glucose fit cannot identify these mechanisms jointly with unknown absorption, clearance, secretion and counterregulatory action.

## Measurements and full-model comparison still required

| Question to distinguish | Required evidence beyond glucose alone | Main ambiguity |
| --- | --- | --- |
| Dynamic extraction versus changed secretion | Synchronized glucose, C-peptide and insulin assays, baseline and late kinetics, body mass, exogenous insulin identity/timing, assay cross-reactivity and independently justified kinetics | Secretion, hepatic extraction and peripheral insulin clearance can compensate for one another |
| Direct portal versus delayed systemic EGP action | Independently estimated endogenous glucose production, meal appearance and disposal with the tracer/model assumptions recorded; insulin/glucagon and relevant substrate context | Plasma glucose alone does not separate glucose production from utilization or meal appearance; P remains a model-derived quantity |
| Applicability to residual T1D | Defined residual-function population, treatment history, renal function, assay limits and repeated baseline observations | Healthy mean coefficients do not establish individual residual-function coefficients |
| Applicability to grafts | Defined graft site and drainage, actual secretory dynamics and treatment information | Neither source capacity nor P describes anatomy, engraftment, survival or immune protection |

A full-source reproduction would reconstruct the coherent normal-column Dalla Man model, including its own basal quantities, all unit processes and actual stimulus, and compare concentrations **and fluxes** with the corresponding published observations. Replacing the complete native virtual profile with that healthy model would mix many changes and cannot isolate the two BC-009 factors. The ablation therefore answers a narrower structural question; full-model reproduction and independent biological evaluation remain separate work with missing original dynamic inputs and participant-level access.

The immediate unsent review question is: “Are the smooth S-dependent extraction law, portal-state EGP term and our baseline-preserving intercepts defensible for a bounded residual-function T1D comparison? Which existing paired kinetic and tracer observations could distinguish these mechanisms without conflating secretion, clearance or peripheral action?” A secretion/kinetics modeller, endocrinologist, tracer-metabolism expert and statistician should review the scope; graft claims additionally need transplant expertise. The existing [measurement/access assessment](m4-cpeptide-measurements.md) remains the starting point. No contact, access application or restricted download is authorized by this document, and none is claimed.
