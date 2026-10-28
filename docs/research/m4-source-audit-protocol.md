# BC-006: secretion source reconciliation protocol

Specified on 20 September 2026, from `bb4ac19`, before numerical execution. The [machine protocol](../../experiments/m4/source_audit/protocol.json) freezes the source values, diagnostic cases, solver settings and checks. BC-006 audits the unresolved BC-001 initialization, basal and scale conventions; it changes none of BC-001 through BC-005.

## Question and evidence classes

Can the discrepancy between the printed initialization and the author's explicit value be explained by different granule-pool conventions? What basal and whole-pancreas interpretation is actually documented, and which conversion factors belong only to the author's C-peptide observation equation?

Keep literal source statements, OpenT1D mathematical deductions, synthetic numerical results and unresolved author intent separate. Reinspect final equation 4.13 and preprint equation 22 visually, the associated cellular equations and the public author file. Record asset hashes, exact locators, access attempts and correction-search limits. Public availability does not grant redistribution rights: do not vendor the source PDF, author code or missing cohort input.

## Prespecified calculations

For the continuum cellular equations at subthreshold basal glucose, derive `D_b=M(G_b)/r`, `R_b=p_plus*D_b/p_minus`. A rapid activation recruits `H_pre=Phi(G_max)*R_b`; the printed initializer instead uses `H_qss=p_plus*Phi(G_max)*D_b/(p_minus+f)`. Compare both at the same D, without conflating a pre-bolus inventory with a postactivation quasi-steady inventory. Compute the ratio symbolically. Examine the author's seed D=311 separately from the derived basal equilibrium; no fitting to its explicit X=92.7 is allowed. Use both the rounded caption and exact author threshold conventions.

Check an isolated fast-pool diagnostic: `H' = -(p_minus+f) H`, `F' = f H-m F`, release ledger `L'=m F`, return ledger `U'=p_minus H`, with `[H,F,L,U]=[1,0,0,0]` microgram. This deliberately excludes replenishment; it is an analytical diagnostic, not the complete cellular or reduced model. Compare numerical states with the independent two-exponential solution, including the equal-rate limit, and conserve all four inventories. Distinguish the pre-bolus amount from its finite-fusion fraction.

Under unchanged BC-001 synthetic glucose and coefficients, vary only X(0): printed value, source explicit value, and derived pre-bolus-pool hypothesis. Y(0) stays zero for this controlled comparison. Independently predict the between-run difference as `delta X(t)=delta X(0)*exp(-m*t)` and its secretion integral as `delta X(0)*(1-exp(-m*T))`. This quantifies consequences without selecting a corrected model.

From `Y=q(G)D`, independently differentiate the product and compare with a finite difference along a declared local `(G,D)` direction. Record `q'(G)*Gdot*D`, the term absent from the literal BC-001 reduction. Do not silently add it or treat it as a validation result. Record separately that using an algebraic post-bolus Y state is not identical to the paper's delayed Y(0)=0 convention.

Compute microgram-to-pmol conversion by the stated insulin molar mass, then the author's concentration-rate conversion using its declared volume. Show rounding and the separate dimensionless 0.5 multiplier explicitly. Never transfer concentration-rate conversion, an observational volume or an undocumented amplitude multiplier into a molar secretion inlet. Basal mobilization M0 and the separately coded basal secretion must remain distinct.

## Execution and acceptance

The parent audit uses the standard library; numerical verification uses the unchanged BC-001 environment. Save protocol, source-extraction record, code and lock snapshots, calculated hypotheses, both numerical trajectories, numerical checks and failure status in a new output directory. Reconstruct the report from saved inputs/results and hash-check artifacts, without running archived code. No random input or parameter estimation is used.

Frozen limits: isolated fast-pool state error 1e-8 microgram, mass error 1e-10 microgram, between-initialization state error 1e-7 microgram, solver difference 1e-6 microgram, chain-rule finite-difference relative error 1e-7, exact repeated output. These are numerical criteria only; no mismatch between source conventions is a numerical-test failure or justification to change a threshold.

Update the canonical model card, source dossier and unsent review packet with the actual verdict. External review remains unperformed until an identified qualified reviewer examines specified artifacts and supplies findings. No reviewer, endorsement, access right, cohort reproduction or therapy effect may be inferred from this audit.
