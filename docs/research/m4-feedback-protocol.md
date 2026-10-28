# BC-008: bounded glucose-feedback protocol

Version 2, specified on 20 September 2026 from `ac1e63f`. **This is the specification frozen before execution.** The subsequent [BC-008 implementation and results](m4-feedback-results.md) record the executed experiment without changing this protocol. The [machine protocol](../../experiments/m4/feedback/protocol.json) freezes the cases and limits. [Decision 0023](../decisions/0023-bounded-glucose-feedback-protocol.md) selects the composition; [BC-008-P1](m4-feedback-readiness.md) separately records executed arithmetic/native-derivative checks. The initial worktree and all BC-001 through BC-007 evidence remain unchanged.

## Question and permitted conclusion

Does a declared glucose-responsive liver input change simulated plasma glucose relative to controls with matched basal plasma insulin in one pinned virtual profile? Report direction, magnitude, sensitivity and failures. There is no required improvement, physiological plausibility threshold or clinical benefit criterion. This experiment cannot estimate reduced insulin need, residual cell count or a therapy effect.

Use [Dalla Man 2007 equations 23–26](models/dallaman2007-secretion.md) with its normal-column alpha, beta, K and gamma, adapting h and basal input explicitly below. BC-001 remains its original declining-IVGTT reference. This model selection provides source equations for rising/falling glucose; it does not establish T1D applicability. Exact source locators and code/data limitations are in the [source register](../../experiments/m4/feedback/sources.json).

## States, rates and feedback boundary

Retain native simglucose `a6f6777586c860457a2a1e6cce6d0bd3fd33d1cc`, profile `adult#001`, and the existing guarded derivative. Preserve all 13 native states and coefficients. Add source states Z=Y+Sb [pmol/(kg min)] and P [pmol/kg]. The source supplies pancreatic appearance Spo and liver arrival S=gamma*P, both [pmol/(kg min)]. Its exact equations and coefficients are in the model card. Time is minutes from the declared initial condition.

At each monolithic solver stage, calculate G=x[3]/Vg and Gdot=native_dx[3]/Vg. Evaluate the source at this same state and add S to guarded native_dx[9]. The instantaneous native glucose derivative does not contain S, so this creates no algebraic loop. Glucose affects source rates, and evolving insulin states subsequently affect glucose. Keep h=initial x[3]/Vg; do not move the threshold with subsequent glucose. Use plasma glucose, not the delayed subcutaneous observation x[12]/Vg. Preserve source transitions at Gdot=0 and the static lower bound; check convergence across them.

| Process | Owner and prohibition against duplicate counting |
| --- | --- |
| Static/dynamic glucose response | New source, with published alpha/beta/K and declared gain; no BC-001 pool or delay in parallel |
| Portal transit | P with gamma; only gamma*P enters the liver; Spo must not also enter native insulin |
| Liver/plasma distribution and clearance | Native m1, m2, fixed m30 and m4; no external first-pass survival factor |
| SC pharmaceutical absorption | Native two depots and native U/min conversion; secretion bypasses both depots |
| Glucose appearance, disposal and insulin action | Unchanged native derivative; no restoration of the full paper's direct portal EGP term or variable hepatic extraction |
| C-peptide, controller, pump and sensor | Outside this experiment; no implied coupled observation or treatment policy |

Unlike BC-007's mass-rate source, these equations already produce body-mass-normalized molar rates. Do not divide by body weight or convert micrograms again. The full paper's extra portal action and variable extraction remain absent. These differences limit biological interpretation of the hybrid model.

## Basal construction and initialization

Define u0=native u2ss, the original SC basal input in pmol/(kg min). For prescribed replacement fraction r:

```text
u_SC = (1-r)*u0
Sb   = r*u0*(m1+m30)/m1
Ip0  = native Ip0
Il0  = native Il0 + r*u0/m1
SC1_0, SC2_0 = (1-r)*(native SC1_0, native SC2_0)
Z0 = Sb; P0 = Sb/gamma
native action.insulin = u_SC*BW/6000   [U/min]
```

All other native baseline states stay unchanged. This follows by balancing the plasma and liver equations: changing route while preserving plasma input requires compensating hepatic loss. At r=0 it reduces exactly to the original native baseline. The separate source rate-state and transit inventory are initially stationary. Do not copy BC-007's 153.48 pmol/min synthetic basal into this experiment.

The design fixes r=0.25 for responsive cases and their constant-basal control. It is a prescribed route-replacement fraction, not a result about insulin requirements. Responsivity gain a separately scales beta and K; it does not alter r, Sb or initial states. A=1 means the chosen coefficients are used unchanged, not complete beta-cell function in this virtual person. Static secretion may decrease below basal as glucose falls, following the published lower branch.

## Scenarios and controls

Run the five machine-listed cases under both fasting and a 30 g initial gastric solid load, from 0 to 240 minutes, sampled every 0.25 minute. For the load case, set only x[0]=30000 mg after constructing the baseline. Fix last_Qsto=30000 mg, last_foodtaken=0 and Action.CHO=0; fasting uses zero for those values. This is an idealized initial stomach load, not native meal announcement or a constant 30 g/min ingestion. Native `T1DPatient` reference initialization sets the same stomach-history value through its reset path. SC basal is constant, without meal bolus or controller.

| Case | Basal replacement r | Responsivity gain a | Purpose |
| --- | --- | --- | --- |
| Native zero extension | 0 | 0 | Intact native reference and exact same-solver equivalence |
| Constant basal | 0.25 | 0 | Matched plasma exposure and route/initialization control |
| Responsive quarter, half, full | 0.25 | 0.25, 0.5, 1 | Exploratory common beta/K scaling, compared with constant basal |

For each scenario, derive two additional diagnostic controls from the completed full-gain reference. Replay its archived liver-arrival S(t) with the same initial native states and SC schedule, but no responsive source, to check closure. Separately use a constant equal to its integrated liver arrival divided by 240. That constant retains the parent's initial states and matches delivered amount; it is intentionally not initialized to its own equilibrium. It tests delivery timing conditional on known total exposure, not prospective predictive performance. For these two controls, native insulin balance starts at their own native inventories, without an unused P inventory.

No changes may be chosen after seeing a favorable glucose effect. If cases leave the declared domain or fail verification, preserve the failure and narrow or amend the experiment explicitly.

## Numerical implementation and acceptance

Before adding feedback, implement the source separately and compare constant-glucose clamps and continuous piecewise-affine rising/falling inputs with independently derived exponential solutions, including the alpha=gamma limit, the lower target boundary, zero gain, stationary basal and nonzero P inventory. A clamp starts at t=0 with declared source inventories; do not silently ignore the impulsive dynamic response of an instantaneous glucose jump. Finite ramps have explicit breakpoints. These checks must distinguish Spo from S. Compare literal signed Y equations with the shifted Z form. The source rate state Z and mass state P require separate unit-labelled discrepancies; use the separate machine limits 1e-7 pmol/(kg min) for Z and 1e-7 pmol/kg for P. No reference result is claimed yet.

Use the existing locked native runtime. Integrate native+source+insulin-ledger states together with the three frozen settings: RK45 (rtol 1e-7, atol 1e-9, max step 0.5 min), RK45 (1e-9, 1e-11, 0.125 min), DOP853 (1e-11, 1e-13, 0.0625 min). Split explicit input changes; verify finite full output and solver completion. The reporting grid is not the solver step. Zero extension must agree exactly with an unchanged native derivative run under the same numerical path, and separately agree with native `T1DPatient` one-minute execution within 0.05 mg/dL glucose and 0.01 pmol/L insulin. Record any difference from native solver choice rather than calling those different paths bit-identical.

For a responsive case, insulin conservation includes portal P, liver Il, plasma Ip and both SC amounts, but excludes Z:

```text
d(P+Il+Ip+SC1+SC2)/dt = u_SC + Spo - m30*Il - m4*Ip
P(t)-P(0) = integral(Spo)-integral(S)
d(Gp+Gt)/dt = EGP + Ra - Uii - Uid - renal_loss
```

Keep separate integrated SC input, pancreatic input, liver arrival and losses. Liver arrival is an internal transfer in the first identity. Audit systemic glucose balance independently using native fluxes; gastric mass and bioavailability remain upstream of Ra. Integrate those glucose fluxes by independent adaptive quadrature of the dense solution (absolute/relative target 1e-9, split at recorded regime transitions); archive integral values, quadrature errors and settings. Do not claim balance from a coarse trapezoid alone or force equality by defining a residual flux. Compare tighter quadrature if the estimated error exceeds one tenth of the 1e-5 mg/kg glucose-balance limit.

Frozen tight/reference limits are 0.01 mg/dL glucose, 0.01 pmol/L insulin, 1e-5 pmol/(kg min) source output, 1e-6 pmol/kg insulin balance and 1e-5 mg/kg glucose balance. Fasting glucose/insulin drift and constant-basal/native glucose discrepancy must each meet their 0.01 native-concentration-unit limits. Preserve exact fresh-process repetition within a declared runtime. Test derivative locality, signs and initialization independently of concentration fits.

For the replay control, transfer piecewise-linear S samples at 0.25, 0.125 and 0.0625 min, splitting at knots and retaining their independently computed trapezoidal amounts. Require finest replay discrepancies from monolithic feedback at most 0.01 mg/dL glucose and 0.01 pmol/L insulin; report every level and remaining error. Use the finest transferred amount for the equal-arrival constant control and report its difference from the integrated feedback ledger. Verify equal delivered amount within 1e-10 relative. This separates input communication from solver error.

Evaluate signed baseline-relative glucose AUC, sampled peak/nadir, final glucose and paired differences against constant basal. A nonzero scalar contrast is numerically resolved only if its magnitude is at least ten times the largest absolute change in that same contrast under the declared solver/refinement comparisons; use machine epsilon times (1+absolute reference value) as the nonzero denominator floor. Use consistent units separately for AUC and concentrations. Zero effects are reported as zero, without a ratio-based superiority label. Numerically resolved effects still describe this synthetic model only.

Terminate and label incomplete any run leaving the declared computational glucose envelope 40–500 mg/dL, returning nonfinite/incomplete output, or producing physical negative amounts below -1e-8 in their native units. The envelope is a research scope choice, not a clinical safety criterion. Native x[6] is a signed insulin-action deviation and is exempt from an amount-positivity rule. Preserve native derivative guards; do not clip states to hide failure. Z must stay nonnegative as well. Stop reasons, time and last valid state must remain available; never report a shorter run as a completed 240-minute case.

## Artifacts, evidence and remaining dependencies

Every attempt must record protocol and source identities, code/lock hashes, selected native parameters, baseline derivation, stimulus/history state, exact output times, all native/source states and ledgers, flux integrals, solver/replay comparisons and durable error status. Preserve failing scenarios alongside complete ones. Reconstruct reports/figures from checked artifacts without executing saved code. Repeat the full experiment in a fresh process. Do not overwrite prior results or edit historical reference outputs.

No human fitting, parameter recovery or independent observation evaluation occurs in BC-008. Gain and the common scale of beta/K are exactly confounded; baseline fraction is prescribed independently. Glucose alone cannot identify secretion, clearance and insulin action jointly. A biological follow-up needs justified plasma glucose, C-peptide/insulin assays, stimulus and exogenous-insulin histories, renal information and population-specific kinetics; use the existing [measurement assessment](m4-cpeptide-measurements.md) and [review brief](m4-collaboration-brief.md). No access or collaboration is assumed.

The next implementation deliverable is the separate source reference and then this bounded monolithic coupling, conditional on its own verification checks. BC-008-P1 passing does not close those checks, OT-026 or M4. A cell-therapy experiment additionally requires a specified site and supported intervention-to-function mechanism; changing a gain is not such a mechanism.
