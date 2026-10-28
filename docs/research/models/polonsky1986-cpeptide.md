# Model card: Polonsky 1986 forward C-peptide kinetics

## Identity and ancestry

`polonsky1986-forward-cpeptide/1` is an original OpenT1D implementation of the two-compartment process scheme and analytical response in Polonsky KS et al., *Use of biosynthetic human C-peptide in the measurement of insulin secretion rates in normal volunteers and type I diabetic patients*, Journal of Clinical Investigation 77 (1986), 98–105. [DOI: 10.1172/JCI112308](https://doi.org/10.1172/JCI112308); [publisher full text](https://www.jci.org/articles/view/112308/files/pdf).

The complete primary paper was read, and its equation and parameter table visually checked on 20 September 2026. Source locations: p. 99 compartment scheme, transfer definitions, sampling and infusion protocol; p. 100 unnumbered analytical bolus equation; p. 103 Table I. The inspected PDF SHA-256 is `f6b13cffc7ca9fc628372edb174e8a4e6e4ea6746dda10334a2578348a9f2fae`. Targeted publisher/title searches found no correction or supplementary code; this is a search result, not proof that none exists.

No original runnable author code or raw participant concentration table was located. The publicly readable paper is not redistributed. This implementation transcribes factual parameters and independently expresses the equations under the repository's code license. Public access to the paper does not establish a license to redistribute its figures or participant records. [Decision 0019](../../decisions/0019-cpeptide-observation-reference.md) compares alternatives and records why no third-party inverse-estimation code was reused.

## Question and applicability

The module maps a specified molar C-peptide appearance rate to plasma concentration. It neither predicts secretion from glucose nor reconstructs arbitrary secretion from measured C-peptide. The bounded synthetic parameter-recovery experiment uses a **known bolus**, not unknown endogenous secretion. [BC-001](pedersen-cobelli2013.md) is the separate glucose-driven secretion reference.

The original study included ten normal volunteers and seven insulin-deficient people with T1D. They were young, near ideal body weight and without clinically significant renal or other stated diabetic complications. Experiments used exogenous biosynthetic human C-peptide. This directly informs kinetic feasibility, but does not establish residual beta-cell function, transplant kinetics, pediatric or renal-impairment applicability. Individual parameter estimation and original inverse-estimation results belong to the publication; they are not OpenT1D validation outcomes.

## States, equations and units

Let `Q1` and `Q2` be central and peripheral C-peptide amounts in pmol/kg, `q` the appearance rate in pmol/(kg min), `E` eliminated amount and `U` delivered amount since time zero. Time is in minutes. The source calls central amount C in the scheme, but also uses C(t) for concentration in the dose/volume expression; this implementation distinguishes them.

```text
dQ1/dt = q - (K1 + K3) Q1 + K2 Q2
dQ2/dt = K1 Q1 - K2 Q2
dE/dt  = K3 Q1
dU/dt  = q
plasma concentration = Q1 / Vp
Q1 + Q2 + E = Q1(0) + Q2(0) + U
```

All three rates have units min^-1. K1 transfers central to peripheral; K2 transfers back; K3 is irreversible central removal. `Vp` is in L/kg, so concentration is pmol/L. The source volume unit mL/kg is divided by 1000. The source's rounded C-peptide molecular weight is 3021 g/mol (p. 99 footnote): 3.021 ng/mL converts to 1000 pmol/L. Unsupported units are rejected. No insulin hepatic extraction or subcutaneous absorption is applied to C-peptide.

The independent analytical reference implements the printed bolus expression:

```text
S = K1 + K2 + K3
alpha, beta = (S +/- sqrt(S^2 - 4 K2 K3)) / 2
C(t) = D / [Vp (alpha-beta)] *
       [(alpha-K2) exp(-alpha t) - (beta-K2) exp(-beta t)]
```

For a dose `D` in pmol/kg this yields pmol/L. Its time integral supplies an exact constant-input convolution. Equivalent stable expressions and the repeated-rate limit avoid cancellation; they do not alter the scientific equation. A matrix exponential provides a third implementation for synthetic fitting. The ODE solver splits at each forcing boundary.

## Parameters and initialization

| Profile | K1 (min^-1) | K2 (min^-1) | K3 (min^-1) | Vp (L/kg) | Origin |
| --- | --- | --- | --- | --- | --- |
| `normal_mean` | 0.057 | 0.054 | 0.060 | 0.0655 | Printed Table I group means |
| `t1d_mean` | 0.037 | 0.031 | 0.052 | 0.0655 | Printed Table I group means |

These are fixed nominal profiles, not a demographic population model. A trajectory at mean coefficients is not the mean of individual trajectories. Likewise, a product of printed mean rate and volume need not equal the paper's mean individual clearance. No SEM is used as a parameter distribution. The source's volume SEM differs between its text and Table I; uncertainty estimation would need resolution and individual information.

Zero-input and infusion cases start at zero incremental inventory. A bolus starts with a declared central dose and zero peripheral amount. The synthetic basal case starts at `Q1=q/K3`, `Q2=(K1/K2) Q1`, with both cumulative ledgers reset to zero. Its baseline 1.5 pmol/(kg min) is a demonstration choice, not inferred human secretion.

The original 50 nmol bolus cannot be mapped to individual per-kg parameters without weights. BC-003 therefore uses an explicitly synthetic 100 pmol/kg bolus. The 3 then 30 pmol/(kg min), 120 minutes per stage, infusion schedule is from p. 99. Its nominal-profile replay is not a reconstruction of cohort measurements.

## Evidence and limitations

The [frozen protocol](../m4-cpeptide-protocol.md) and [executed results](../m4-cpeptide-results.md) separate analytical agreement, numerical limits, synthetic parameter recovery and absent human validation. A single-compartment comparator uses the same central volume and removal rate without peripheral exchange; its transient difference is not an accuracy ranking without observations.

With a known dose and ideal noiseless full-window data, four kinetic parameters can be recovered in this experiment. With dose unknown, scaling dose and volume equally leaves concentrations identical. At equilibrium, only `q/(K3 Vp)` is observed. Early-only sampling worsens conditioning; three samples cannot identify four parameters. Neither successful synthetic recovery nor a good glucose fit establishes biological identifiability.

Assumed equimolar release can relate molar insulin secretion and C-peptide appearance, but does not establish correct processing in a graft or resolve BC-001's basal/whole-body scale. C-peptide belongs on an observation branch beside insulin kinetics, never downstream of insulin hepatic loss. [Measurement and review requirements](../m4-cpeptide-measurements.md) must be addressed before a human-data or transplant interpretation. Functional capacity is not cell count, and changing its amplitude is not a treatment model.
