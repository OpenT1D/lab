# BC-011 — Conditional joint sensitivity and synthetic recovery

Specified on 22 September 2026 before numerical implementation or fitting, from `b0bd514` in the existing isolated `codex/beta-cell-reference` worktree. The [machine protocol](../../experiments/m4/joint_identifiability/protocol.json) freezes the matrix, seeds, bounds, methods and numerical gates. This is the next bounded OT-026 experiment after [BC-010](m4-feedback-observation-results.md), not completion of M4.

## Question and permitted claim

Under a known model, exact basal glucose/insulin and known subcutaneous input, how does adding dynamic plasma insulin and C-peptide change local sensitivity and recovery of evoked secretion responsivity and two removal rates? Compare G, G+I and G+I+C-peptide, known versus unknown clearance, and 10- versus 30-minute sampling. All data are invented. No human accuracy, practical human identifiability, optimal clinical schedule, treatment effect or cell count can follow.

## Model and initialization

Reuse the BC-008 fixed-hepatic hybrid: pinned native `adult#001`, a 30 g initial gastric solid load, constant SC basal at 75% of the original native basal, 240 elapsed minutes, no controller or sensor. Dalla Man et al. ([2007](https://doi.org/10.1109/TBME.2007.893506), equations 23–26, Table I) provides static/dynamic secretion; the [model card](models/dallaman2007-secretion.md) records ancestry and the engineering adaptation. C-peptide uses the unchanged Polonsky et al. ([1986](https://doi.org/10.1172/JCI112308), process scheme and Table I) two-compartment equations and nominal T1D mean parameters from the [C-peptide card](models/polonsky1986-cpeptide.md). These mixed nominal sources do not define a calibrated person.

Vary three positive dimensionless parameters: common evoked `gain` multiplying beta and K, native peripheral insulin-removal `m4_scale`, and central C-peptide-removal `k3_scale`. The truth is (1,1,1); all bounds are [0.5,1.5], selected as engineering ranges, not physiological confidence limits. Other native parameters, hepatic m30, beta/K ratio, alpha, gamma, C-peptide k1/k2/volume and equimolar appearance remain fixed. Gain does not multiply basal secretion and is not a total-capacity or cell-mass parameter.

Every modality conditions on the same exact nominal basal G and plasma insulin amount Ip and known SC input. Thus “G only” means **dynamic glucose only with this baseline knowledge**, not inference without any insulin information. At each candidate m4, recompute equilibrium:

```text
Rsc = ka1*Isc1 + ka2*Isc2
Il = ((m2+m4)*Ip - Rsc)/m1
Sb = (m1+m30)*Il - m2*Ip
Z = Sb; P = Sb/gamma
Q1 = Sb/k3; Q2 = k1*Q1/k2
```

Keep other native states and SC depots fixed at the BC-008 nominal baseline. Check positive amounts and derivatives before adding the gastric load. Basal secretion is determined by this constraint; it is not a fourth independent estimate. This prevents a spurious startup transient from supplying parameter information.

Append passive C-peptide amounts and elimination/input ledgers to the existing RHS. Its input is pancreatic Spo in pmol/(kg min), without insulin portal transit, extraction or SC input. G is plasma mg/dL; I and C-peptide are pmol/L using their separate L/kg volumes; internal amounts are pmol/kg. One monolithic solve removes interpolation from repeated fitting. The existing native locked environment contains all required numerical libraries; a separate matrix-exponential comparison and original BC-008 comparison check this new execution wrapper. Historical code and locks stay unchanged.

## Observation and inference matrix

Use 0–240 minutes inclusive at 10 and 30 minute intervals. Generate one noiseless reference and two independent additive Gaussian realizations with seeds 117 and 221, on a shared one-minute grid. Select nested subsets for each schedule/modality. Synthetic channel SDs are 5 mg/dL, 10 pmol/L insulin and 30 pmol/L C-peptide. They are illustrative engineering noise, not claims about assays or CGM. Basal G/I noise is zero because these are exact conditioning values; C-peptide at time zero remains an observation. Retain any negative noisy value without clipping.

The full matrix has 36 analyses: two kinetic assumptions × three modalities × two schedules × three noise cases, each with two fixed starts. With known kinetics estimate only gain. With unknown clearance declare all three parameters unknown, but omit k3 from G/GI optimization and report it as **unobservable**, since a passive C-peptide rate cannot affect those channels. It must not receive a numerical “estimate”. GIC attempts all three.

Minimize the sum of ((prediction − observation)/channel SD) squared in log-parameter coordinates, using bounded `least_squares`, fixed absolute log-coordinate central differences (one-sided three-point differences near bounds), two starts and the exact settings in the machine protocol. Save every start, termination reason, residual and prediction. Truth is used only for generating observations, declared fixed kinetics and assessing recovery; initialization uses the two prespecified off-truth starts. This is a deliberately favorable same-model recovery exercise, not an independent validation split.

At truth, form the weighted log-parameter Jacobian at two central-difference steps and compare fit/reference solvers. Report singular values, a declared relative numerical rank cutoff, weakest directions and rank-deficient columns. Also compare each design’s singular directions with its Jacobian discrepancy under the checked solver/difference refinements; a direction smaller than that discrepancy remains numerically unresolved. This discrepancy is not a rigorous bound on total derivative error. Do not infer global uniqueness from full local rank or optimizer convergence. [Raue et al. 2009](https://doi.org/10.1093/bioinformatics/btp358), sections 2–4, motivates log-space weighted fitting and distinguishes structural from data-limited identifiability. This experiment does not implement their profile-likelihood method or claim confidence intervals. The gain/beta/K scaling redundancy is removed by fixing beta/K; verify the exact alternative parameterization. Verify that k3 changes no G/I equation. A C-peptide-only appearance/volume ambiguity from BC-010 is not a proof of the same symmetry in the joint model.

## Acceptance, failures and interpretation

Numerical gates precede inference: equilibrium and mass balances, original BC-008 agreement, independent Cp calculation, solver refinement at truth and both bound corners, derivative refinement and exact-symmetry diagnostics. Dimensionless concentration differences divide each channel by its fixed SD. Gates and limits are frozen in the machine protocol. Failed/incomplete or nonfinite ODE output cannot become a fitting residual or accepted short trajectory.

Noiseless active parameters must recover within 1%; missing k3 for G/GI is an expected exact limitation. Report noisy truth errors, start disagreement and bound hits without requiring accurate recovery. An inaccurate completed noisy fit is a finding; optimizer nonconvergence or model failure fails the experiment’s completion gate and is retained. Two noise realizations do not estimate uncertainty coverage or a recovery success rate. Bounds truncating uncertainty cannot establish identifiability. Every planned analysis and both starts remain in the denominator. A new process repeats the complete matrix, and reports reconstruct from archived data without a solver.

The intended deliverable is a conditional comparison of information and failures, identifying which additional measurements or independently measured kinetics merit a later study. External domain review and authorized human observations remain necessary. Follow the [measurement requirements](m4-cpeptide-measurements.md); no outreach or human-data access is authorized by this protocol.

## Pre-execution amendment

BC-011/2 supersedes /1 before numerical fitting. Review identified that SciPy relative differences can approach machine-sized steps near log(1)=0. The optimizer now uses a fixed absolute log step of 0.001, with bounded three-point differences. This also clarifies SD-squared weighting and the exclusion of hepatic-clearance identification. No results, bounds, matrix or acceptance thresholds were changed.
