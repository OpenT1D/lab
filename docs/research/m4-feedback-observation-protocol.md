# BC-010: forward C-peptide observation of the feedback source

Protocol BC-010/1 was specified before new implementation or output inspection on 22 September 2026, starting from `9393fb1`. The [machine protocol](../../experiments/m4/feedback_observation/protocol.json) freezes cases, inputs, parameters, numerical checks and limitations. [Decision 0025](../decisions/0025-feedback-cpeptide-observation.md) records the one-way boundary. This is a bounded OT-026 observation experiment, not a human estimator or treatment evaluation.

## Model and source assessment

The [Polonsky 1986 model card](models/polonsky1986-cpeptide.md) remains canonical for C-peptide equations, units, nominal parameters and population limits. The [primary paper](https://www.jci.org/articles/view/112308/files/pdf), DOI 10.1172/JCI112308, describes equimolar cosecretion and negligible hepatic C-peptide extraction in its introduction, the two-compartment scheme on p. 99, bolus response on p. 100 and kinetic coefficients in Table I on p. 103. Relevant text and the table were reread for this boundary; no new coefficient is introduced. The existing code and nominal T1D mean profile are reused unchanged. That profile came from exogenous C-peptide studies in insulin-deficient participants; it is not a calibration for residual secretion, renal impairment or graft recipients.

The [Dalla Man 2007 paper](https://isbgroup.eu/files/Dalla%20Man%202007.pdf), DOI 10.1109/TBME.2007.893506, pp. 1744–1745, distinguishes pancreatic appearance and post-transit insulin delivery. BC-008/009 already implement that distinction. BC-010 attaches the C-peptide observation to pancreatic **Spo**, before the insulin-specific state P and liver arrival S=gamma*P. Equimolar processing and immediate appearance at the C-peptide model boundary are explicit composition assumptions. Negligible hepatic extraction does not establish zero anatomical transit time. A separately justified C-peptide transport delay would require new evidence; this experiment does not borrow the insulin delay as if it were measured C-peptide physiology.

No new author code, participant series or restricted material is imported. The factual parameter transcription and original OpenT1D code retain their existing provenance/licenses. Public paper access does not grant rights to its figures or participant data. The existing [measurement/access specification](m4-cpeptide-measurements.md) remains conditional and no contact or access request is made.

## Input, state and ownership contract

Use all 24 completed BC-009 cases: native zero, constant basal and full feedback, each under fasting and a 30 g gastric load, across four hepatic variants. Require the entire parent archive to pass reconstruction before using its source. The source samples already include basal secretion and use pmol/(kg min). Preserve their time origin and 0.25-minute grid over 240 minutes. Do not divide by body weight again, convert insulin mass, apply HE, add basal a second time or convert exogenous SC insulin to C-peptide.

The new input is the continuous piecewise-linear interpolant through Spo samples. This declares a finite input, not unobserved continuous-source curvature. C-peptide states are central Q1, peripheral Q2, eliminated E and delivered U, all in pmol/kg; time is minutes. The existing equations are:

```text
Q1' = q - (k1+k3)*Q1 + k2*Q2
Q2' = k1*Q1 - k2*Q2
E' = k3*Q1; U' = q
C = Q1/Vp in pmol/L
Q1 + Q2 + E = Q1(0) + Q2(0) + U
```

Fix k1=0.037, k2=0.031, k3=0.052 min^-1 and Vp=0.0655 L/kg. For basal rate Sb from the parent's explicit baseline construction, set Q1(0)=Sb/k3 and Q2(0)=k1*Q1(0)/k2; ledgers start at zero. Native-zero source therefore gives zero C-peptide despite positive pharmaceutical insulin. C-peptide has no glucose/insulin feedback in this experiment. The preserved parent concentration series are paired **synthetic model outputs**, not measured assay records or equal insulin/C-peptide concentrations.

## Verification and diagnostics

Run the unchanged C-peptide solver in its separate locked runtime, at both frozen tight/reference settings. Compare every case against the existing independent matrix-exponential propagation with the same finite interpolant and initial inventories. Tests also compare a constant-input case to the independently derived published bolus-kernel convolution. Check nonnegative inventories, total mass/input accounting, exact zero, basal stability, invalid boundaries and incomplete output.

Repeat the observation worker in a new process, requiring byte-identical numerical artifacts. Preserve parent hashes before/after use and verify the copied archive. Rebuild reports without numerical packages, from checked inputs and arrays, and figures without rerunning kinetics. Failures remain explicit and prevent acceptance of a complete result matrix.

The three error questions are separate:

1. **Kinetic calculation:** ODE versus matrix exponential and tight versus reference for the same Spo interpolant.
2. **Parent integration:** propagate the parent's tight Spo rather than reference Spo, holding the C-peptide solver fixed.
3. **Source sampling:** coarsen the reference samples to 1 and 0.5 min and compare against the available 0.25-min interpolant. Require the 0.5-min discrepancy below 0.05 pmol/L and a discrepancy ratio at most 0.6 when the coarse discrepancy exceeds 1e-8 pmol/L. This measures coarsening sensitivity, not convergence of unarchived inputs below 0.25 min. Compare the finest interpolant's total amount with the original integrated pancreatic ledger; require relative error below 1e-4, using max(1, absolute parent amount) as denominator. No numerical error criterion is a clinical accuracy threshold.

A deliberately incorrect S-driven C-peptide curve quantifies the consequence of importing the insulin portal delay. Preserve its sign, maximum absolute concentration difference, peak/time, final concentration and AUC; no minimum fault-effect size is required. Any endpoint dose difference also contains the terminal portal inventory change and is not pure timing.

As a conditional scale diagnostic, multiply only the C-peptide appearance, both initial amounts and Vp by 0.5 or 2. Linearity makes the concentration unchanged. This exposes an appearance/volume ambiguity at the observation boundary if equimolar appearance or volume were unknown. The primary runs retain ratio one. This transformation leaves saved glucose/insulin fixed and is **not** an alternative common insulin-secretory capacity or proof of nonidentifiability of every joint parameter. No kinetics are fitted, no secretion is deconvolved, and no human parameter recovery is claimed.

## What this can establish

The experiment can establish that one explicit pancreatic source drives separately owned, mass-consistent C-peptide kinetics and that a post-portal inlet changes the synthetic observation. It cannot identify hepatic extraction or direct EGP action from C-peptide alone: these affect C-peptide indirectly through the feedback source, while the branch itself has no hepatic coefficient. Unknown kinetics, processing, assay noise and glucose-production/utilization confounding still need a prespecified observation study, independent information and domain review. A good synthetic numerical fit supplies no evidence of cell count, graft survival or treatment benefit.
