# BC-001: standalone beta-cell secretion reference

Version BC-001/1, specified before numerical implementation on 20 September 2026. This protocol implements the bounded OT-025 reference and the secretion boundary needed by OT-015. The [machine specification](../../experiments/m4/beta_cell/protocol.json) freezes parameters, cases and numerical criteria. The [evidence dossier](m4-evidence-dossier.md) explains selection and source limitations.

## Question and permissible conclusions

Can the reduced IVGTT equations of Pedersen and Cobelli (2013) reproducibly transform a prescribed post-bolus glucose decline into calculated **evoked insulin secretion**, with explicit initialization and capacity assumptions? Reconstruct the published glucose-dependent provision and delay functions (Figure 2c/d), and independently check the numerical implementation. This is an equation reference and synthetic demonstration, not an original patient/cohort reproduction or a test of T1D or graft physiology.

The reference is [Multiscale modelling of insulin secretion during an intravenous glucose tolerance test](https://doi.org/10.1098/rsfs.2012.0085). Published final equations 4.11–4.13 correspond to equations 20–22 in the [author preprint](https://www.dei.unipd.it/~pedersen/InterfaceFocus_preprint.pdf). The two states are releasable/fused insulin X (micrograms) and provision Y (micrograms/minute). Glucose is an imposed plasma concentration, not a glucose prediction or CGM signal. Time zero is immediately after a single idealized glucose bolus. No stochastic inputs, meals, controllers or metabolic engine are present.

## Equations and conventions

For glucose G in mmol/L, define P = max(G − Gb, 0)^3 / ((Kphi − Gb)^3 + max(G − Gb, 0)^3), M = M0 + c G^n/(KM^n + G^n), q = f pplus P/(pminus + f), rho = r + q and Yinf = q M/rho. Integrate dX/dt = Y − m X and dY/dt = rho (Yinf − Y). Report SR = m X in micrograms/minute. The rate constants are per minute. M0 and c are micrograms/minute, concentration parameters mmol/L, and n dimensionless.

All eleven nominal parameters come from Figure 2 and its caption; values and units are frozen in the JSON. No parameters are fitted. The exponent-three activation law is equation 3.5 (preprint 7); mobilization is equation 3.1 (preprint 3). Basal insulin is omitted because reduced equation 4.11c reports only mX; the added basal term of equation 3.7 is a separate process. M0 is basal **mobilization**, not basal secretion. No hepatic extraction, plasma clearance, C-peptide dynamics or arbitrary unit-to-mole factor is included.

The synthetic input is G(t) = 5 + (17.2 − 5) exp(−t/30), over 0–100 min. Equation 4.1 supplies the shape and approximately 30-minute time constant; 17.2 mmol/L comes from the author's surrogate, while 5 mmol/L is the paper's basal threshold. This deliberately combines declared reference values; it is not the author's unavailable cohort mean glucose file. A user may specify another positive, nonincreasing exponential of this form; this remains a scenario, not a validated arbitrary-input interface. The input baseline must not exceed the model activation threshold for this basal initialization. Oral, repeated-pulse and rising glucose cases are unsupported. Constant suprathreshold forcing is used only as an explicitly initialized numerical oracle.

Initialize Y0 = 0; calculate D0 = M(input basal)/r under the stated basal-equilibrium assumption and X0 = pplus P(Gmax) D0/(pminus + f), following printed equation 4.13. This is a documented source interpretation. The author's XPPAUT file instead assigns X0 = 92.7 micrograms. Preserve that value as a separate initialization sensitivity; neither silently correct the paper nor claim the initial burst is resolved. The source dossier records the inconsistency and missing measured glucose series.

OpenT1D's dimensionless capacity scenario multiplier scales M and X0 together, hence X, Y and SR; it leaves rho unchanged. It is an explicitly hypothetical common amplitude multiplier. It is neither anatomical beta-cell mass nor a model of therapy, death or engraftment. Compare 0, 0.25, 0.5 and 1 against the zero-capacity baseline. No endogenous insulin dose is sent to another model.

## Prespecified verification

Use separately locked Python 3.12, NumPy/SciPy and Matplotlib. Compare coarse RK45, tight RK45 and finer DOP853 settings in the JSON. Tight/reference secretion must agree within 1e-6 micrograms/minute. Use an independently derived constant-input closed form, including equal-rate limits, to detect incorrect rates, ordering and initialization. Check basal/zero-capacity limits, positivity within 1e-9, deterministic repetition and exact capacity scaling within 1e-8. Verify mmol/L versus mg/dL conversion using the author's stated factor 18 without silently changing the model's native units.

Reconstruct Figure 2c/d's algebraic functions on 0–20 mmol/L: delay must lie in 12.0–12.6 min with the nominal parameters. Verify against a separately written expression and check asymptotes and activation threshold. These are reproduced theoretical relationships, not digitized experimental observations. Do not use a good fit to these expressions as independent biological evidence.

Reject nonfinite/negative quantities, invalid thresholds, rising/invalid input, invalid time grids or solver tolerances. A failed or incomplete solve is a failed run and must remain visible. Retain requested configuration, code and dependency identities, actual runtime, inputs, outputs, settings, errors and artifact hashes. Refuse an existing output directory. Reconstruct metrics and figures from stored artifacts without model execution; verify completeness and hashes before accepting them.

## Sensitivity, identifiability and assessment

Perturb each listed parameter by ±1% separately and report normalized changes in the 0–100 min evoked-secretion AUC. This is a local exploratory calculation; it is not a prior distribution or clinical confidence interval. Compare the two initializations separately. Demonstrate the exact confounding between capacity and a common amplitude change in c/M0/X0. A numerically identifiable synthetic combination would still not establish identifiability from noisy human C-peptide observations. No human fit or empirical evaluation is performed.

OT-026 needs its own protocol and compatible kinetic inlet, plus a decision whether to retain this declining-IVGTT context or justify a different secretion reference. The [coupling specification](m4-coupling.md) defines the proposed route, owners, measurements and acceptance gates. M4 remains incomplete until the coupling, appropriate baseline comparison and domain review are actually achieved.
