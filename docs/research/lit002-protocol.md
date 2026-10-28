# LIT-002 — Experimental insulin-absorption comparison

Version 1.0, 20 September 2026. The [machine protocol](../../experiments/literature/lit002/protocol.json) records its freeze time before the main experiment. This implements the literature extension proposed after [LIT-001](lit001-results.md), under [decision 0009](../decisions/0009-experimental-insulin-absorption.md).

## Question and permitted conclusion

How much does a source-derived change in subcutaneous insulin absorption alter insulin appearance and native Cambridge glucose trajectories under identical predefined delivered insulin and meals?

This is an exploratory synthetic sensitivity experiment. It evaluates a code implementation and consequences of assumptions. It does not estimate clinical accuracy, identify personalized physiology, reproduce the full source population model or demonstrate a better treatment. All source values and the Cambridge reference parameterization are known development material.

## Model arms and process ownership

| Arm | Subcutaneous model | Systemic/action/glucose model |
| --- | --- | --- |
| `cambridge_native` | Intact serial Cambridge depots, native `tmaxI=55 min` | Intact pinned Cambridge |
| `cambridge_mean_matched` | Same serial equations; `tmaxI` matches the source model's mean appearance time | Same native parameters and equations |
| `faggionato_sc` | Two source-derived depots, parallel appearance and 5.62-minute input delay | Same native parameters and equations |

Use LT1 commit `9a6092065bd821f88691cd8d03b0550acd665573` and Node 22.22.2, with the existing locked M0 TypeScript loader. The actual native patient and solver execute the glucose, insulin-action and meal dynamics. The new experiment supplies explicitly timed open-loop inputs and the hybrid derivative override; it is not a port of the full engine.

The hybrid takes only the subcutaneous equations from [Faggionato et al., 2021](https://doi.org/10.3390/metabo11040235), Equation 3/Figure 3 and fixed effects in Table 2: `ka1=0.000134/min`, `ka2=0.0128/min`, `kd=ka2+alpha=0.0283/min`, delay `5.62 min`. The [checked LIT-001 parameter record](../../experiments/literature/lit001/parameters.json) is bound by hash. The source's volume, systemic clearance, covariates, random effects and residual observation model are not transplanted. Its printed `ka1(t)` is interpreted as constant, as documented in the source dossier.

For an input impulse, mean appearance time is:

```text
mean_time = delay + 1/(ka1+kd) + kd/((ka1+kd)*ka2)
matched_tmaxI = mean_time/2
```

The source-derived mean is approximately 118.546 minutes and the matched Cambridge parameter is approximately 59.273 minutes. This is an analytical comparator, not a fit, and does not make the full shapes equivalent. It helps distinguish changing overall timing from changing the structure of the appearance curve. No virtual cohort or independent parameter-origin evidence is inferred from software defaults.

## Inputs, clocks and initialization

The common native basal infusion and equilibrium are computed from the intact Cambridge parameterization at its established reference equilibrium glucose, 124.91784824923789 mg/dL. All arms preserve the same body weight and systemic/action/glucose/gut state. Their subcutaneous steady states differ consistently with their own absorption equations. For the hybrid, constant basal prehistory applies at every time before the start, filling the delay queue.

Native subcutaneous amounts are whole-body mU and delivery is U/h. The analytical comparison normalizes amounts to mU/kg and rates to mU/kg/min using the recorded native body weight. Native plasma insulin remains mU/L. The delay queue contains the delivered insulin over the preceding delay interval, including prehistory. Total unabsorbed insulin is `S1+S2+queue`; queue insulin must not disappear from the mass accounting.

A finite pulse represents an already-delivered extra rate, not a native pump bolus callback. Input intervals are left-closed and right-open. The native driver splits at every sample, meal/pulse boundary and delay-shifted pulse boundary, using the same event union for all arms. The solver receives the left interval's constant input, including during its endpoint derivative evaluation.

## Frozen scenarios

All cases run for 720 minutes with one-minute reported samples plus exact event boundaries. Each case runs with maximum integration steps of 0.25 and 0.125 minutes at relative tolerance 0.001.

| Case | Extra delivered insulin above common basal | Carbohydrate input |
| --- | --- | --- |
| `basal` | None | None |
| `pulse` | 24 U/h during minutes 120–125, totaling 2 U | None |
| `meal_pulse` | The same finite pulse | 40 g over minutes 120–135 |

These values are synthetic engineering fixtures and were selected before inspecting experiment results. They are not dosing guidance or a calibrated clinical scenario. The matrix has three arms, three scenarios and two numerical resolutions: 18 planned runs. Every attempt and failure remains in the result denominator.

A separate ideal-impulse illustration uses 200 mU/kg, zero prior input and zero states over 720 minutes. It reports appearance, cumulative absorbed fraction, remaining insulin and times to 50% and 90% appearance. It is distinct from the basal-plus-finite-pulse coupled experiment, and its timing measures are not clinical duration-of-action estimates.

## Checks and outcomes

Before interpreting differences, check direct native-baseline equivalence, source identity, unchanged systemic/action/glucose derivatives, correct initial equilibrium, exact delivered amounts, delayed boundaries and complete finite outputs. Compare native subcutaneous states against an independent analytic calculation. Check zero input, linearity for fixed parameters, equal-rate limits, positive state and conservation including the delay queue.

Prespecified numerical resolutions are 0.005 mU/kg for subcutaneous state agreement, 0.001 mU/kg/min for appearance agreement, 0.1 mg/dL for glucose refinement and 0.01 mU/L for plasma-insulin refinement. Apply the glucose/insulin limits to both individual trajectories and between-arm contrasts. Basal invariance is checked within 0.00001 concentration units; mass and input consistency use relative limits recorded in the machine protocol. These are engineering thresholds, not clinical agreement thresholds. No criterion requires a large or favorable model difference.

Report sampled extrema, appearance and remaining amount, and paired curve differences. Keep their sign and units; do not rank a lower glucose result as a better model. Report numerical change relative to the size of the modeled effect when defined. No clinical time-in-range or treatment scoring is used.

If a run fails or ends early, preserve its configuration, partial trace and diagnostic status. Do not tune away a failed scenario or silently replace frozen values. Reconstruction validates the saved inputs, traces, runtime/source identity and artifact hashes without running a simulator or estimator. Known development evidence is not relabeled held-out validation.

## Acceptance

The capability is complete when the three selectable code paths, identical-input native experiment, meaningful checks and reconstructible report work for the declared matrix. The resulting physiological sensitivity is reported separately from numerical success. Human evidence remains necessary for any claim of improved real-world accuracy.

See the [usage and result guide](../lit002-tutorial.md) for actual execution, limitations and commands.
