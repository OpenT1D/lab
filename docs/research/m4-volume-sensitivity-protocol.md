# BC-012 — C-peptide volume knowledge and joint recovery

Specified on 22 September 2026 before numerical implementation or fits, starting from `959d1d1` in the isolated `codex/beta-cell-reference` worktree. The [machine protocol](../../experiments/m4/volume_sensitivity/protocol.json) freezes the comparison. The question follows the measured information limitation in [BC-011](m4-joint-identifiability-results.md): does joint G/I/C-peptide separation survive an incorrect or estimated C-peptide central volume?

## Composition and scope

Preserve the entire BC-011 dynamical model, initial-state rules, 30 g gastric load, exact basal G/I, known SC input, 240-minute horizon, nominal profile, solvers, parameter bounds, noise realizations and observation units. Reuse its locked native environment and original source files. Volume is a fourth positive multiplier: `Cp=Q1/(0.0655*volume_scale)` in pmol/L. It changes the observation mapping only; all 24 amounts/rate states and ledgers remain those of the unchanged three-parameter parent. Do not scale the initial amounts to hide a baseline concentration change.

The underlying [Polonsky model card](models/polonsky1986-cpeptide.md) traces [Polonsky et al. 1986](https://doi.org/10.1172/JCI112308), p.99 process scheme, p.100 response and p.103 Table I. Its nominal central volume is 65.5 mL/kg = 0.0655 L/kg. The source does not justify a ±20% uncertainty distribution; the card preserves the source's volume-SEM discrepancy. The low/high stress values and fitting bounds here are explicitly engineering choices. No paper figures, author software or participant records are copied.

Compare known versus estimated **removal-rate multipliers**, not “all kinetics known”: when V changes, the dimensional C-peptide clearance `k3*V` changes even with fixed k3. k1/k2, appearance ratio, hepatic extraction, insulin action, meal kinetics and basal G/I stay fixed. This is a conditional observation-parameter stress experiment, not a physical model of population covariance between volumes and rate constants, nor a model of therapy or cell counts.

## Frozen matrix

Use the original reference observations at volume=1, with the same noiseless case and seeds 117/221, SDs 5 mg/dL, 10 pmol/L and 30 pmol/L, and nested 10/30-minute schedules. All arms use identical observations; changing the assumed volume must never regenerate the data or rescale measurement noise. Exact basal G/I remain conditioning information, including in the GI control; basal Cp remains observed/noisy.

| Arm | Assumed Cp volume multiplier | Fitted parameters with known rates | Fitted parameters with estimated rates |
| --- | ---: | --- | --- |
| Correct, GIC | 1 | gain | gain, m4, k3 |
| Low, GIC | 0.8 | gain | gain, m4, k3 |
| High, GIC | 1.2 | gain | gain, m4, k3 |
| Estimated, GIC | Free in [0.5,1.5] | gain, volume | gain, m4, k3, volume |
| GI control | No volume information | gain | gain, m4 |

Each row has two rate assumptions × two schedules × three noise cases: **60 analyses, 120 starts**. GI is not repeated across irrelevant volume arms. It has no volume estimate, and no k3 estimate when k3 is declared unknown. The previous glucose-only comparison remains in BC-011; GI is the matched control for this narrower volume question.

Keep the original first-three-parameter starts and append volume 0.8/1.2. Fix m4/k3 at one in the known-rate arm, with null estimates for fixed or unobservable parameters. Minimize the same sum of squared SD-standardized residuals in log coordinates, with the unchanged optimizer settings and bounds. Archive every start, failure, objective, per-channel residual, estimate, true-value error and bound hit. Wrong-volume fits are not expected to recover the generating parameters; their bias is a scientific result rather than a failed 1% recovery test.

## Structural and numerical checks

At fixed rate parameters, volume must leave G/I, all states and every mass ledger **exactly unchanged**. Multiplying volume by v divides Cp by v. Independently check `dCp/dlog(V)=-Cp` and zero G/I volume derivatives. Basal Cp is `Sb(m4)/(k3*V)`; volume and k3 are confounded in this single steady measurement. Dynamic k3 changes time constants, while volume scales concentration, so this basal identity is not a general dynamic symmetry. Gain does not scale basal secretion and affects glucose feedback; the earlier appearance/volume symmetry does not automatically become a gain/volume symmetry.

Execute the parent forward verification, preserve exact volume-one equivalence and check volume extrema under all inherited solvers. Form full weighted four-column log-parameter Jacobians at volume anchors 0.8,1,1.2 and first-three parameters one; the estimated-volume arm is assessed at truth. Refine difference steps and solvers as in BC-011. Bind each selected sensitivity matrix to its exact anchor, rows and fitted/declared parameter columns. Check singular directions against per-design numerical discrepancies; numerical rank remains a local diagnostic.

Retain the 1% noiseless recovery gate for correct- and estimated-volume active parameters and GI controls. There is no truth-recovery gate for fixed-wrong volume; noisy inaccuracies and bound hits are findings. Any optimizer nonconvergence, invalid model solve or missing analysis fails completion without erasing that attempt. Repeat the complete numerical matrix in a new process; reconstruct the report from verified files without a numerical runtime. The machine protocol defines all numerical limits before fitting.

## Interpretation and remaining work

Compare parameter bias, objectives, residuals by channel, starts, bounds and local information across volume assumptions and the matched GI control. Lower fitted residuals from an additional free parameter do not by themselves establish correct biology. Two fixed noise draws cannot estimate confidence coverage or an optimal clinical sampling schedule. The distinction between local numerical diagnostics and data-limited/global identifiability follows [Raue et al. 2009](https://doi.org/10.1093/bioinformatics/btp358), sections 2–4; no profile-likelihood or confidence-interval implementation is claimed here.

The result can refine the need for independent kinetic/volume information and later measurement design. It cannot establish human parameter recovery, transplant applicability or efficacy. OT-026 and M4 remain partial; follow the [measurement requirements](m4-cpeptide-measurements.md) before any human application. No outreach, data-access request, patient-data download or external review is implied.
