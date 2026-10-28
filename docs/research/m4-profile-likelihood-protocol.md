# BC-013 — Conditional beta-cell likelihood profiles

Specified on 22 September 2026 before implementation or fitting, starting from `da5adbf41f370c6211db586537e101582436e28f` in the isolated `codex/beta-cell-reference` worktree. The [machine protocol](../../experiments/m4/profile_likelihood/protocol.json), BC-013/1, has canonical JSON SHA-256 `365b69343943e70175693aaa0abc14dd998c4a304dbce33b1760e2879c9167b6`. [Decision 0028](../decisions/0028-conditional-profile-likelihood.md) records the statistical and numerical boundary. This document specifies the experiment; it does not claim a completed execution.

The question follows [BC-012](m4-volume-sensitivity-results.md): how do reoptimized nuisance parameters and knowledge of C-peptide volume affect the within-bound profile geometry of evoked secretory gain and removal rates? Local sensitivity and agreement between fitted starts do not answer that question. The proposed profiles test the existing synthetic model without adding physiology.

## Preserved model and observations

Reuse the unchanged BC-012 model, its 24 states, exact basal glucose/insulin conditioning, known subcutaneous input, equilibrium reconditioning, 30 g initial gastric load and 240-minute horizon. The four positive multipliers are evoked gain, peripheral insulin removal m4, C-peptide removal k3 and central C-peptide volume. Every multiplier retains bounds [0.5,1.5]; these are engineering limits, not biological population limits. Hepatic structure, insulin action, meal kinetics, C-peptide exchange rates and equimolar appearance remain fixed. Volume changes only the observation `Cp=Q1/(0.0655*volume_scale)`; no amount or time constant changes through volume alone.

Generate the original BC-011/BC-012 observations afresh at all multipliers equal to one. Use the existing noiseless observations and noise seeds 117 and 221, with fixed SDs 5 mg/dL for glucose, 10 pmol/L for insulin and 30 pmol/L for C-peptide. These are known development examples, not held-out observations. This bounded follow-up uses **30-minute sampling only**; it cannot compare sampling schedules. The noiseless case examines weighted-objective geometry under the declared weights, not uncertainty coverage.

Exclude t=0 glucose and insulin from stochastic residuals because they are exact conditioning inputs. Retain t=0 C-peptide as an observation. This leaves 25 stochastic residuals for glucose/insulin/C-peptide (GIC), or 16 for glucose/insulin (GI), over 0–240 minutes. The noisy examples assume independent Gaussian errors with the declared fixed SDs. Do not estimate noise scales from fitted residuals or treat conditioned baseline values as additional independent measurements.

## Frozen comparison

| Design | Estimated parameters | Fixed or unobservable parameters | Profiled parameters per dataset |
| --- | --- | --- | --- |
| Free-volume GIC | gain, m4, k3, volume | None of these four | All four |
| Correct fixed-volume GIC | gain, m4, k3 | Volume fixed at one | gain, m4, k3 |
| GI | gain, m4 | k3 and volume unobservable | gain, m4 |

The three designs and three datasets give **nine design/dataset cases and 27 profile curves**, with unrestricted fits under both solvers and multiple starts for each optimization. GI supplies no estimates for k3 or volume. Their canonical internal values do not imply that these parameters were learned from GI.

For observations y and model predictions f, minimize `Q=sum(((f-y)/SD)^2)`. This is twice the least-squares optimizer cost. With independent Gaussian observations and parameter-independent SDs, `Q=-2*log(L)+constant`; nuisance reoptimization follows [Raue et al. 2009](https://doi.org/10.1093/bioinformatics/btp358), section 2.1, equations 4–6, and section 4, equation 10. At each fixed interest-parameter value, minimize Q over every remaining estimated parameter within the same bounds. Also calculate the fixed-nuisance slice at that value, holding **all** nuisance parameters at the unrestricted solution. The slice is a comparator, not a profile.

When volume is a free nuisance parameter, its conditional minimization is analytic. Write `a=1/volume_scale` and let q be the predicted C-peptide concentrations at volume one for the candidate gain/m4/k3. The volume-dependent objective is `sum((a*q-y_Cp)^2/SD_Cp^2)`, so its bounded minimum is:

```text
a = clip(sum(q*y_Cp)/sum(q*q), 1/1.5, 1/0.5)
volume_scale = 1/a
```

The common fixed C-peptide SD cancels in this ratio; t=0 C-peptide remains included. This exact conditional optimization reduces the numerical search dimension without holding volume fixed. Preserve the resulting volume estimate and any bound hit. When volume is the interest parameter or is fixed by design, do not project it. Numerically reoptimize the other nuisance parameters in log coordinates.

Use three unrestricted starts: the two inherited off-truth starts and the generating parameter vector. Each profile point uses two deterministic starts: the unrestricted best solution and the inherited off-truth start farthest from it in nuisance log coordinates, with the first selected on a tie. Override fixed and interest coordinates; do not select sequential warm starts. Use bounded trust-region least squares with the frozen absolute log-difference step 0.001, at most 120 evaluations, and ftol/xtol/gtol each 1e-8. Retain all starts, including unsuccessful ones. Independently compare each free-volume unrestricted result with the unchanged BC-012 unprojected two-start implementation.

## Contour and endpoint verification

For each curve, subtract its own unrestricted minimum for the same design, dataset and solver: `DeltaQ=Q_profile-Q_minimum`. Never clip negative differences. Use `DeltaQ=3.841458820694124` as the **nominal asymptotic, pointwise, one-parameter chi-square reference contour**. Raue et al., section 2.2.2, equation 8, describes likelihood-threshold regions. This threshold is not simultaneous four-parameter coverage, verified finite-sample coverage or a human confidence interval. Boundary complications follow [Self and Liang 1987](https://doi.org/10.1080/01621459.1987.10478472), section 3, pp. 607–609, and section 4, p. 610. Active nuisance bounds must remain visible even when the interest parameter is interior.

Start with the grid 0.5, 0.75, 1, 1.25, 1.5, add midpoints 0.625, 0.875, 1.125, 1.375, and include the unrestricted parameter estimate. Retain coarse and refined sampled topology. Bisect **every** adjacent sampled contour-crossing bracket until its absolute multiplier width is at most 0.005, with at most 12 bisections. Preserve the complete refinement history, all crossing brackets and the intervals supported by sampled points. Finite sampling cannot establish that hidden disconnected components are absent.

Refit the unrestricted minimum with the reference solver using the same three starts. Under that solver, refit both final endpoints of every crossing and both imposed parameter bounds using the two profile starts. Also evaluate the fit-solver optimum at these locations with the reference solver. Require agreement of objective values and of contour sides at the checked endpoints and bounds. A region reaching an imposed bound is bound-limited; do not extrapolate it or report a forced closed uncertainty interval.

## Acceptance, provenance and failure handling

Execute unchanged BC-012 forward verification before biological profiling. Independently verify analytic volume minimization, including both active-bound cases, and test nuisance profiling against a hand-derived quadratic oracle that differs from a fixed-nuisance slice. The machine protocol fixes objective agreement at 0.001, allowed numerical profile-versus-baseline/slice discrepancies at 0.0001, endpoint width at 0.005, noiseless parameter recovery within 1%, and exact fresh-process repetition. It also specifies separate 1e-8 oracle objective and 1e-5 quadratic parameter limits.

Archive protocol and source snapshots, unchanged environment locks, native identity, generating observations, every start, interest values, nuisance estimates, projected volumes, predictions, residuals, objectives, bounds, numerical comparisons, errors and refinement histories. Keep numerical inference separate from a report reader that reconstructs arithmetic and completeness without numerical libraries. Repeat the complete adaptive campaign in a fresh process; do not substitute replay of saved fits for repeat execution.

Any optimizer/model failure, missing planned artifact, failed independent check, profile below its declared minimum, profile above its feasible slice or unresolved reference-solver contour-side mismatch prevents accepted completion under the frozen tolerances. Do not silently replace a baseline to hide a missed minimum. Preserve failed archives and document any protocol amendment before changing its rules.

## Permitted conclusions

The experiment can describe conditional objective geometry, nuisance compensation and the effect of assumed volume knowledge within the declared parameter box. It cannot establish global uniqueness, human identifiability, uncertainty coverage, an empirical volume distribution, a clinical sampling recommendation or therapy efficacy. Two reused noise realizations are not a coverage study. Each design has its own fitted minimum, so noisy normalized contours need not obey a universal widening rule when volume is freed.

No author software, paper figure or participant record is imported; this is an independent implementation of the stated profiling method, not reproduction of the authors' application or algorithm. OT-026 and M4 remain partial. Broader nuisance physiology, independently constrained kinetics, external domain review and authorized independent observations remain necessary before biological or clinical interpretation. Follow the [measurement assessment](m4-cpeptide-measurements.md) for those dependencies.
